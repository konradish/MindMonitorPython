# /// script
# dependencies = ["numpy", "scipy", "pandas", "pyperclip", "colorama", "keyboard"]
# ///

import numpy as np
import pandas as pd
from scipy import signal
import time
import os
import argparse
from datetime import datetime
import threading
import queue
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False
try:
    import colorama
    from colorama import Fore, Style
    colorama.init()
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Fallback color definitions
    class Fore:
        RED = YELLOW = GREEN = CYAN = MAGENTA = WHITE = ""
    class Style:
        RESET_ALL = ""
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
import select
import sys

class ConsciousnessMonitor:
    def __init__(self, csv_file="mind_monitor_data.csv", window_seconds=0.75, 
                 update_interval=1.0, channels=['TP9', 'AF7', 'AF8', 'TP10'],
                 show_bands=True, show_insights=True, use_precomputed=True, 
                 force_output=False, output_interval=None, debug=False):
        
        self.csv_file = csv_file
        self.window_seconds = window_seconds
        self.update_interval = update_interval
        self.channels = channels
        self.show_bands = show_bands
        self.show_insights = show_insights
        self.use_precomputed = use_precomputed
        self.force_output = force_output
        self.output_interval = output_interval or (30 if not force_output else update_interval)
        self.debug = debug
        
        # Auto-detect sample rate from data, default to Muse standard
        self.sample_rate = self._detect_sample_rate()
        self.window_samples = int(window_seconds * self.sample_rate)  # Ensure integer
        
        # EEG frequency bands (clinical standards)
        self.bands = {
            'delta': (0.5, 4),    # Not 0-4, starts at 0.5
            'theta': (4, 8),      
            'alpha': (8, 13),     # Wider alpha band
            'beta': (13, 30),     
            'gamma': (30, 50)     # Clinical gamma, not 30-100
        }
        
        # Mind Monitor CSV column mapping
        self.eeg_columns = ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']
        self.abs_band_columns = ['abs_delta', 'abs_theta', 'abs_alpha', 'abs_beta', 'abs_gamma']
        self.rel_band_columns = ['rel_delta', 'rel_theta', 'rel_alpha', 'rel_beta', 'rel_gamma']
        self.quality_columns = ['touching_forehead', 'horseshoe_tp9', 'horseshoe_af7', 'horseshoe_af8', 'horseshoe_tp10']
        self.sensor_columns = ['accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z']
        self.feature_columns = ['jaw_clench', 'blink']
        
        # Design filters once during initialization (for raw signal processing if needed)
        self.highpass_filter = signal.butter(4, 0.5, btype='high', fs=self.sample_rate)
        self.lowpass_filter = signal.butter(4, 50, btype='low', fs=self.sample_rate)
        self.notch_filter = signal.iirnotch(60, 30, fs=self.sample_rate)  # 60Hz notch
        
        self.last_file_size = 0
        
        # Session tracking for smart output
        self.session_start = time.time()
        self.last_output_time = 0
        self.last_state = None
        self.last_alpha = 0
        self.last_fnirs = 0
        self.session_states = {}
        self.session_events = []
        self.security_guard_count = 0
        self.peak_alpha = 0
        self.peak_fnirs = 0
        self.peak_times = {}
        
        # Event detection thresholds
        self.alpha_threshold = 10  # % change
        self.fnirs_threshold = 0.05
        self.gamma_spike_threshold = 15  # %
        
        # Initialize command interface
        self.clipboard_queue = queue.Queue()
        self.command_interface_active = True
        
        mode = "Pre-computed Features" if use_precomputed else "Raw Signal Processing"
        color_prefix = f"{Fore.CYAN}" if COLORS_AVAILABLE else ""
        color_suffix = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
        print(f"{color_prefix}🧠 Consciousness Monitor v4 Enhanced{color_suffix}")
        print(f"Mode: {mode} | Window: {window_seconds}s | Update: {update_interval}s")
        hotkey_msg = " | Commands: 'c' (copy), 's' (summary), 'n' (now), 'q' (quit)"
        print(f"Sample Rate: {self.sample_rate}Hz{hotkey_msg}")
        print("=" * 70)
    
    def _detect_sample_rate(self):
        """Auto-detect effective sample rate from existing data"""
        try:
            if os.path.exists(self.csv_file):
                # Read more data for better statistics
                df = pd.read_csv(self.csv_file, nrows=5000)  
                
                # Try timestamp_utc first, then timestamp_local, then TimeStamp
                timestamp_col = None
                for col in ['timestamp_utc', 'timestamp_local', 'TimeStamp']:
                    if col in df.columns:
                        timestamp_col = col
                        break
                
                if timestamp_col and len(df) > 100:
                    # Parse timestamps and calculate EFFECTIVE sample rate
                    timestamps = pd.to_datetime(df[timestamp_col], errors='coerce').dropna()
                    if len(timestamps) > 100:
                        # Calculate effective rate over total duration (not average of intervals)
                        total_duration = (timestamps.iloc[-1] - timestamps.iloc[0]).total_seconds()
                        if total_duration > 0:
                            effective_rate = len(timestamps) / total_duration
                            
                            # Cap at reasonable EEG rates (Mind Monitor bursts can look like 6kHz)
                            if effective_rate > 512:
                                print(f"📊 Detected bursted data ({effective_rate:.0f}Hz), using standard 256Hz")
                                return 256
                            elif effective_rate > 128:
                                print(f"📊 Detected effective rate: {effective_rate:.1f}Hz")
                                return effective_rate
                            else:
                                print(f"📊 Low rate detected ({effective_rate:.1f}Hz), using 256Hz default")
                                return 256
        except Exception as e:
            print(f"⚠️  Could not detect sample rate: {e}")
        
        # Default fallback
        print("📊 Using default sample rate: 256Hz")
        return 256
    
    def _check_for_commands(self):
        """Check for user commands in a non-blocking way"""
        try:
            # Simple non-blocking input check
            if hasattr(select, 'select') and hasattr(sys.stdin, 'fileno'):
                # Unix/Linux/WSL
                ready, _, _ = select.select([sys.stdin], [], [], 0)
                if ready:
                    command = sys.stdin.readline().strip().lower()
                    self._process_command(command)
                    if command == 'q':
                        return False
            return True
        except:
            # Fallback for Windows or other platforms - just continue
            return True
    
    def _process_command(self, command):
        """Process user commands"""
        if command == 'c':
            self.clipboard_queue.put('copy_recent')
            print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}📋 Copying recent events...{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
        elif command == 's':
            self.clipboard_queue.put('copy_summary')
            print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}📋 Copying session summary...{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
        elif command == 'n' or command == 'now':
            self.clipboard_queue.put('show_now')
            print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}🔄 Showing current state...{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
        elif command == 'q':
            print(f"{Fore.YELLOW if COLORS_AVAILABLE else ''}👋 Quit command received{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
        elif command:
            print(f"{Fore.YELLOW if COLORS_AVAILABLE else ''}❓ Unknown command '{command}'. Use 'c' (copy), 's' (summary), 'n' (now), or 'q' (quit).{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
    
    def _handle_clipboard_requests(self):
        """Handle clipboard copy requests"""
        try:
            while not self.clipboard_queue.empty():
                request = self.clipboard_queue.get_nowait()
                if request == 'copy_recent':
                    self._copy_recent_events()
                elif request == 'copy_summary':
                    self._copy_session_summary()
                elif request == 'show_now':
                    return 'force_show'  # Signal to force display current state
        except:
            pass
        return None
    
    def _copy_recent_events(self):
        """Copy last 30 seconds of events to clipboard"""
        try:
            current_time = time.time()
            recent_events = [event for event in self.session_events 
                           if current_time - event['time'] <= 30]
            
            if recent_events:
                clipboard_text = "\n".join([event['text'] for event in recent_events])
                
                if CLIPBOARD_AVAILABLE:
                    pyperclip.copy(clipboard_text)
                    print(f"{Fore.GREEN if COLORS_AVAILABLE else ''}📋 Copied {len(recent_events)} recent events to clipboard{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
                else:
                    # Fallback: print to console for manual copy
                    print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}📋 Recent events (clipboard not available, copy manually):{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
                    print("=" * 50)
                    print(clipboard_text)
                    print("=" * 50)
            else:
                print(f"{Fore.YELLOW if COLORS_AVAILABLE else ''}📋 No recent events to copy{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
        except Exception as e:
            print(f"{Fore.RED if COLORS_AVAILABLE else ''}❌ Clipboard error: {e}{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
    
    def _copy_session_summary(self):
        """Copy session summary to clipboard"""
        try:
            summary = self._generate_session_summary()
            
            if CLIPBOARD_AVAILABLE:
                pyperclip.copy(summary)
                print(f"{Fore.GREEN if COLORS_AVAILABLE else ''}📋 Session summary copied to clipboard{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
            else:
                # Fallback: print to console for manual copy
                print(f"{Fore.CYAN if COLORS_AVAILABLE else ''}📋 Session summary (clipboard not available, copy manually):{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
                print("=" * 50)
                print(summary)
                print("=" * 50)
        except Exception as e:
            print(f"{Fore.RED if COLORS_AVAILABLE else ''}❌ Clipboard error: {e}{Style.RESET_ALL if COLORS_AVAILABLE else ''}")
    
    def _generate_session_summary(self):
        """Generate session summary for clipboard"""
        try:
            session_duration = time.time() - self.session_start
            duration_min = int(session_duration / 60)
            
            # Calculate state percentages
            total_events = sum(self.session_states.values())
            if total_events > 0:
                state_percentages = {state: (count/total_events)*100 
                                   for state, count in self.session_states.items()}
                top_states = sorted(state_percentages.items(), key=lambda x: x[1], reverse=True)[:3]
                states_str = " ".join([f"{state}({pct:.0f}%)" for state, pct in top_states])
            else:
                states_str = "No data"
            
            summary = f"SESSION: {duration_min}min | States: {states_str}\n"
            summary += f"Peaks: Alpha={self.peak_alpha:.0f}% @{self.peak_times.get('alpha', 'N/A')} | "
            summary += f"fNIRS={self.peak_fnirs:+.3f} @{self.peak_times.get('fnirs', 'N/A')} | "
            summary += f"Security Guard: {self.security_guard_count} activations"
            
            return summary
        except Exception as e:
            return f"Error generating summary: {e}"
    
    def preprocess_signal(self, raw_data):
        """Mind Monitor style: minimal preprocessing to preserve alpha"""
        if len(raw_data) < 50:
            return raw_data
            
        # Based on analysis: Mind Monitor uses raw signal or minimal DC removal
        # No aggressive filtering that kills alpha waves!
        
        # Option 1: Raw signal (works great for 0.5-1s windows)
        # return raw_data
        
        # Option 2: DC removal only (also works great)
        filtered = raw_data - np.mean(raw_data)
        
        # NO detrending, NO high-pass, NO low-pass filtering
        # These kill alpha waves and inflate delta artificially
        
        return filtered
    
    def get_band_power(self, data, low_freq, high_freq):
        """Calculate power in specific frequency band using proper signal processing"""
        if len(data) < 100:
            return 0
            
        try:
            # Preprocess the signal first!
            clean_data = self.preprocess_signal(data)
            
            # Apply Hanning window to reduce spectral leakage
            windowed = clean_data * np.hanning(len(clean_data))
            
            # Use Welch's method for better spectral estimation
            nperseg = min(256, len(windowed))
            noverlap = nperseg // 2  # Overlap must be less than nperseg
            freqs, psd = signal.welch(windowed, fs=self.sample_rate, 
                                      nperseg=nperseg, 
                                      noverlap=noverlap)
            
            # Find frequency indices for the band
            freq_mask = (freqs >= low_freq) & (freqs <= high_freq)
            
            # Calculate power in band
            power = np.trapz(psd[freq_mask], freqs[freq_mask])
            
            return max(0, power)  # Ensure non-negative
        except Exception as e:
            error_color = f"{Fore.RED}" if COLORS_AVAILABLE else ""
            reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
            print(f"{error_color}⚠️ Band power calculation error: {e}{reset_color}")
            return 0
    
    def analyze_eeg_window_precomputed(self, eeg_data):
        """Analyze using Mind Monitor's pre-computed band powers with enhanced error handling"""
        if eeg_data is None or len(eeg_data) < 10:
            return None
            
        try:
            # Get the latest data (most recent values in window)
            window_samples = max(10, int(self.window_seconds * self.sample_rate))
            latest_data = eeg_data.tail(window_samples)
            
            if latest_data.empty:
                return None
            
            # Check data quality first with null safety
            quality_data = {}
            if 'touching_forehead' in latest_data.columns:
                forehead_col = latest_data['touching_forehead']
                if not forehead_col.isna().all() and len(forehead_col.dropna()) > 0:
                    quality_data['touching_forehead'] = forehead_col.iloc[-1]
                else:
                    quality_data['touching_forehead'] = 0
            
            for col in self.quality_columns[1:]:  # Skip touching_forehead, already handled
                if col in latest_data.columns:
                    col_data = latest_data[col]
                    if not col_data.isna().all() and len(col_data.dropna()) > 0:
                        quality_data[col] = col_data.iloc[-1]
                    else:
                        quality_data[col] = 0
            
            # Calculate band powers with enhanced validation
            band_powers = {}
            
            for i, band in enumerate(['delta', 'theta', 'alpha', 'beta', 'gamma']):
                try:
                    abs_col = self.abs_band_columns[i]
                    if abs_col in latest_data.columns:
                        valid_data = latest_data[abs_col].dropna()
                        if len(valid_data) > 0:
                            # Convert to numeric and handle any conversion errors
                            numeric_data = pd.to_numeric(valid_data, errors='coerce').dropna()
                            if len(numeric_data) > 0:
                                band_powers[band] = max(0, numeric_data.mean())  # Ensure non-negative
                            else:
                                band_powers[band] = 0
                        else:
                            band_powers[band] = 0
                    else:
                        band_powers[band] = 0
                except Exception as e:
                    warning_color = f"{Fore.YELLOW}" if COLORS_AVAILABLE else ""
                    reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
                    print(f"{warning_color}⚠️ Error processing {band} band: {e}{reset_color}")
                    band_powers[band] = 0
            
            # Calculate relative band powers with validation
            rel_powers = {}
            for i, band in enumerate(['delta', 'theta', 'alpha', 'beta', 'gamma']):
                try:
                    rel_col = self.rel_band_columns[i]
                    if rel_col in latest_data.columns:
                        valid_data = latest_data[rel_col].dropna()
                        if len(valid_data) > 0:
                            # Handle empty strings and convert to numeric
                            numeric_data = pd.to_numeric(valid_data, errors='coerce').dropna()
                            if len(numeric_data) > 0:
                                rel_powers[band] = max(0, numeric_data.mean())  # Ensure non-negative
                            else:
                                rel_powers[band] = 0
                        else:
                            rel_powers[band] = 0
                    else:
                        rel_powers[band] = 0
                except Exception as e:
                    warning_color = f"{Fore.YELLOW}" if COLORS_AVAILABLE else ""
                    reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
                    print(f"{warning_color}⚠️ Error processing relative {band}: {e}{reset_color}")
                    rel_powers[band] = 0
            
            # Handle empty relative powers (compute from absolute if needed)
            total_rel_power = sum(rel_powers.values())
            if total_rel_power == 0 and sum(band_powers.values()) > 0:
                total_abs_power = sum(band_powers.values())
                if total_abs_power > 0:
                    rel_powers = {band: power/total_abs_power for band, power in band_powers.items()}
                else:
                    rel_powers = {band: 0 for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']}
            
            # Calculate fNIRS equivalent (average of EEG channels as proxy)
            fnirs_value = 0
            if 'eeg_tp9' in latest_data.columns and 'eeg_af7' in latest_data.columns:
                try:
                    tp9_data = pd.to_numeric(latest_data['eeg_tp9'], errors='coerce').dropna()
                    af7_data = pd.to_numeric(latest_data['eeg_af7'], errors='coerce').dropna()
                    af8_data = pd.to_numeric(latest_data.get('eeg_af8', []), errors='coerce').dropna()
                    tp10_data = pd.to_numeric(latest_data.get('eeg_tp10', []), errors='coerce').dropna()
                    
                    channels = [tp9_data, af7_data, af8_data, tp10_data]
                    valid_channels = [ch for ch in channels if len(ch) > 0]
                    
                    if valid_channels:
                        channel_means = [ch.mean() for ch in valid_channels]
                        fnirs_value = np.mean(channel_means) / 1000.0  # Convert to mV range
                except:
                    fnirs_value = 0
            
            # Store results for averaged analysis
            results = {
                'averaged': {
                    'band_powers': band_powers,
                    'rel_powers': rel_powers,
                    'quality': quality_data,
                    'fnirs': fnirs_value
                }
            }
            
            return results
            
        except Exception as e:
            error_color = f"{Fore.RED}" if COLORS_AVAILABLE else ""
            reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
            print(f"{error_color}❌ Error in precomputed analysis: {e}{reset_color}")
            return None
    
    def analyze_eeg_window_raw(self, eeg_data):
        """Analyze EEG window using raw signal processing (fallback method)"""
        if len(eeg_data) < 50:
            return None
            
        # Clean data - remove NaN values from EEG channels only
        eeg_columns_present = [col for col in self.eeg_columns if col in eeg_data.columns]
        if not eeg_columns_present:
            return None
            
        clean_eeg = eeg_data[eeg_columns_present].dropna()
        if len(clean_eeg) < 50:
            return None
            
        # Calculate band powers for each channel
        results = {}
        
        for i, channel in enumerate(['TP9', 'AF7', 'AF8', 'TP10']):
            eeg_col = self.eeg_columns[i]
            if eeg_col not in eeg_data.columns:
                continue
                
            channel_data = clean_eeg[eeg_col].values
            
            # Skip channels with NaN values or too much noise
            if np.isnan(channel_data).any():
                continue
            if len(channel_data) < 50:
                continue
            if np.std(channel_data) > 1000 or np.std(channel_data) < 1:
                continue
            
            band_powers = {}
            for band_name, (low, high) in self.bands.items():
                power = self.get_band_power(channel_data, low, high)
                band_powers[band_name] = power
            
            results[channel] = band_powers
        
        return results
    
    def interpret_mental_state(self, powers, use_relative=False):
        """Convert band powers to psychological insights with enhanced error handling"""
        try:
            # Choose which powers to use with null safety
            if powers is None:
                return self._get_no_signal_result()
            
            if use_relative and 'rel_powers' in powers and powers['rel_powers']:
                band_powers = powers['rel_powers']
            else:
                band_powers = powers.get('band_powers', powers)
            
            if not band_powers:
                return self._get_no_signal_result()
            
            # Handle invalid values with better validation
            valid_powers = {}
            for band, power in band_powers.items():
                if power is not None and not np.isnan(float(power)) and not np.isinf(float(power)):
                    valid_powers[band] = max(0, float(power))  # Ensure non-negative
            
            if not valid_powers:
                return self._get_no_signal_result()
            
            # Normalize powers to percentages
            total_power = sum(valid_powers.values())
            if total_power == 0:
                return self._get_no_signal_result()
            
            ratios = {band: (power / total_power) * 100 for band, power in valid_powers.items()}
            
            # Fill in missing bands with 0
            for band in self.bands.keys():
                if band not in ratios:
                    ratios[band] = 0
            
            # Determine dominant state
            state_indicators = []
            confidence = "MODERATE"
            
            # Enhanced state detection
            if ratios['alpha'] > 30:
                state_indicators.append("RELAXED")
                confidence = "HIGH"
            
            if ratios['beta'] > 35:
                if ratios['alpha'] > 25:
                    state_indicators.append("FOCUSED")
                else:
                    state_indicators.append("ALERT/TENSE")
                    confidence = "HIGH"
            
            if ratios['theta'] > 30:
                if ratios['alpha'] > 20:
                    state_indicators.append("CREATIVE/FLOW")
                else:
                    state_indicators.append("MEDITATIVE")
                confidence = "HIGH"
            
            if ratios['delta'] > 40:
                state_indicators.append("DROWSY")
                confidence = "HIGH"
            
            if ratios['gamma'] > 15:
                state_indicators.append("PEAK FOCUS")
                confidence = "HIGH"
            
            if not state_indicators:
                state_indicators = ["NEUTRAL"]
            
            state = " + ".join(state_indicators)
            
            # Generate insights with validation
            insights = []
            try:
                if ratios.get('beta', 0) > ratios.get('alpha', 0) * 2:
                    insights.append("🚨 Security guard might be active")
                if ratios.get('theta', 0) > 15 and ratios.get('alpha', 0) > 15:
                    insights.append("🌊 Good emotional terrain navigation")
                if ratios.get('alpha', 0) > 35:
                    insights.append("😌 Excellent regulation state")
                if ratios.get('gamma', 0) > 20:
                    insights.append("⚡ Intense cognitive processing")
                if ratios.get('delta', 0) > 45:
                    insights.append("😴 Very relaxed/tired state")
                if ratios.get('theta', 0) > 30:
                    insights.append("🎨 Creative/flow state active")
            except Exception as e:
                warning_color = f"{Fore.YELLOW}" if COLORS_AVAILABLE else ""
                reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
                print(f"{warning_color}⚠️ Insight generation error: {e}{reset_color}")
            
            return {
                'state': state,
                'confidence': confidence,
                'insights': insights,
                'ratios': ratios,
                'quality': powers.get('quality', {}),
                'fnirs': powers.get('fnirs', 0)
            }
        
        except Exception as e:
            error_color = f"{Fore.RED}" if COLORS_AVAILABLE else ""
            reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
            print(f"{error_color}❌ Mental state interpretation error: {e}{reset_color}")
            return self._get_no_signal_result()
    
    def _get_no_signal_result(self):
        """Return standard no signal result"""
        return {
            "state": "No signal", 
            "confidence": "LOW", 
            "insights": [], 
            "ratios": {band: 0 for band in self.bands.keys()}, 
            "quality": {},
            "fnirs": 0
        }
    
    def display_results(self, interpretation, timestamp=None):
        """Display analysis results in compact, smart format"""
        try:
            current_time = time.time()
            
            # Extract key metrics
            ratios = interpretation.get('ratios', {})
            state = interpretation.get('state', 'UNKNOWN')
            fnirs = interpretation.get('fnirs', 0)
            
            # Determine dominant band
            if ratios:
                dominant_band = max(ratios.keys(), key=lambda k: ratios.get(k, 0))
                dominant_value = ratios.get(dominant_band, 0)
            else:
                dominant_band = 'unknown'
                dominant_value = 0
            
            # Determine when to output based on mode
            should_output = False
            alpha_change = abs(ratios.get('alpha', 0) - self.last_alpha)
            fnirs_change = abs(fnirs - self.last_fnirs)
            state_changed = state != self.last_state
            gamma_spike = ratios.get('gamma', 0) > self.gamma_spike_threshold
            time_elapsed = current_time - self.last_output_time
            
            # Check for forced interval first (overrides everything)
            if time_elapsed >= self.output_interval:
                should_output = True
            elif self.force_output:
                # Force output mode: show every update
                should_output = True
            else:
                # Smart mode: only on significant changes
                if (alpha_change > self.alpha_threshold or 
                    fnirs_change > self.fnirs_threshold or 
                    state_changed or gamma_spike):
                    should_output = True
            
            # Handle clipboard requests and commands
            command_result = self._handle_clipboard_requests()
            if command_result == 'force_show':
                should_output = True  # Force output for 'now' command
            
            if should_output:
                # Generate compact output
                timestamp_str = datetime.now().strftime("%H:%M:%S")
                
                # Format main output line
                if dominant_value > 50:  # Show single dominant band
                    band_str = f"{dominant_band.upper()}: {dominant_value:.0f}%"
                    emoji = self._get_band_emoji(dominant_band)
                else:  # Show multiple bands if balanced
                    significant_bands = [(band, value) for band, value in ratios.items() if value > 20]
                    band_str = " ".join([f"{band.capitalize()}: {value:.0f}%" for band, value in significant_bands[:2]])
                    emoji = self._get_state_emoji(state)
                
                fnirs_str = f"fNIRS: {fnirs:+.3f}"
                
                # Color coding
                if "ALERT" in state or "TENSE" in state:
                    color = f"{Fore.RED}" if COLORS_AVAILABLE else ""
                elif "RELAXED" in state or "MEDITATIVE" in state:
                    color = f"{Fore.GREEN}" if COLORS_AVAILABLE else ""
                elif "FOCUSED" in state or "PEAK" in state:
                    color = f"{Fore.CYAN}" if COLORS_AVAILABLE else ""
                elif "CREATIVE" in state or "FLOW" in state:
                    color = f"{Fore.MAGENTA}" if COLORS_AVAILABLE else ""
                else:
                    color = f"{Fore.WHITE}" if COLORS_AVAILABLE else ""
                
                reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
                
                output_line = f"[{timestamp_str}] {band_str} | {fnirs_str} | {color}{state}{reset_color} | {emoji}"
                print(output_line)
                
                # Track for session summary
                self._track_session_event(current_time, output_line, state, ratios)
                
                # Update tracking variables
                self.last_alpha = ratios.get('alpha', 0)
                self.last_fnirs = fnirs
                self.last_state = state
                self.last_output_time = current_time
                
                # Track peaks
                if ratios.get('alpha', 0) > self.peak_alpha:
                    self.peak_alpha = ratios.get('alpha', 0)
                    self.peak_times['alpha'] = timestamp_str
                
                if abs(fnirs) > abs(self.peak_fnirs):
                    self.peak_fnirs = fnirs
                    self.peak_times['fnirs'] = timestamp_str
                
                # Track security guard activations
                if "Security guard" in str(interpretation.get('insights', [])):
                    self.security_guard_count += 1
        
        except Exception as e:
            error_color = f"{Fore.RED}" if COLORS_AVAILABLE else ""
            reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
            print(f"{error_color}❌ Display error: {e}{reset_color}")
    
    def _get_band_emoji(self, band):
        """Get emoji for dominant band"""
        emojis = {
            'alpha': '🌊',
            'beta': '⚡',
            'theta': '🎨', 
            'delta': '😴',
            'gamma': '🔴'
        }
        return emojis.get(band, '🧠')
    
    def _get_state_emoji(self, state):
        """Get emoji for mental state"""
        if "ALERT" in state or "TENSE" in state:
            return "🔴"
        elif "RELAXED" in state:
            return "🌊"
        elif "FOCUSED" in state:
            return "🎯"
        elif "PEAK" in state:
            return "⚡"
        elif "CREATIVE" in state or "FLOW" in state:
            return "🎨"
        elif "MEDITATIVE" in state:
            return "🧘"
        elif "DROWSY" in state:
            return "😴"
        else:
            return "🧠"
    
    def _track_session_event(self, timestamp, text, state, ratios):
        """Track events for session analysis"""
        self.session_events.append({
            'time': timestamp,
            'text': text,
            'state': state,
            'ratios': ratios.copy()
        })
        
        # Track state durations
        if state in self.session_states:
            self.session_states[state] += 1
        else:
            self.session_states[state] = 1
        
        # Keep only last 100 events to manage memory
        if len(self.session_events) > 100:
            self.session_events = self.session_events[-100:]
    
    def get_latest_data(self):
        """Get the latest EEG data from CSV file"""
        try:
            if not os.path.exists(self.csv_file):
                return None
                
            # Check if file has new data
            current_size = os.path.getsize(self.csv_file)
            if current_size <= self.last_file_size:
                return None
            
            # Read the CSV file
            try:
                df = pd.read_csv(self.csv_file)
            except pd.errors.EmptyDataError:
                return None
            except Exception as e:
                print(f"Error reading CSV: {e}")
                return None
            
            if len(df) == 0:
                return None
            
            # Update file size
            self.last_file_size = current_size
            
            # Get window of recent data
            window_rows = int(self.window_seconds * self.sample_rate)
            recent_data = df.tail(window_rows)
            
            return recent_data
            
        except Exception as e:
            print(f"Error getting latest data: {e}")
            return None
    
    def analyze_file(self, filename=None):
        """Analyze entire CSV file for patterns and trends"""
        file_to_analyze = filename or self.csv_file
        
        if not os.path.exists(file_to_analyze):
            print(f"❌ File not found: {file_to_analyze}")
            return
        
        print(f"📊 Analyzing entire file: {file_to_analyze}")
        
        try:
            df = pd.read_csv(file_to_analyze)
            
            if len(df) == 0:
                print("❌ Empty file")
                return
            
            print(f"📈 Total samples: {len(df)}")
            
            # Determine analysis method
            has_precomputed = all(col in df.columns for col in self.abs_band_columns[:3])  # Check first 3 bands
            
            if has_precomputed and self.use_precomputed:
                print("🎯 Using pre-computed band powers from Mind Monitor")
                self._analyze_file_precomputed(df)
            else:
                print("🔧 Using raw signal processing")
                self._analyze_file_raw(df)
                
        except Exception as e:
            print(f"❌ Error analyzing file: {e}")
    
    def _analyze_file_precomputed(self, df):
        """Analyze file using pre-computed band powers"""
        # Calculate average band powers across entire session
        band_averages = {}
        rel_averages = {}
        
        for i, band in enumerate(['delta', 'theta', 'alpha', 'beta', 'gamma']):
            abs_col = self.abs_band_columns[i]
            rel_col = self.rel_band_columns[i]
            
            if abs_col in df.columns:
                valid_data = df[abs_col].dropna()
                band_averages[band] = valid_data.mean() if len(valid_data) > 0 else 0
            
            if rel_col in df.columns:
                valid_data = df[rel_col].dropna()
                # Check if column has actual numeric data (not empty strings)
                if len(valid_data) > 0:
                    try:
                        # Try to convert to numeric to check for empty strings
                        numeric_data = pd.to_numeric(valid_data, errors='coerce').dropna()
                        rel_averages[band] = numeric_data.mean() if len(numeric_data) > 0 else 0
                    except:
                        rel_averages[band] = 0
                else:
                    rel_averages[band] = 0
        
        # If relative powers are empty, compute them from absolute powers
        total_rel_power = sum(rel_averages.values())
        if total_rel_power == 0 and sum(band_averages.values()) > 0:
            total_abs_power = sum(band_averages.values())
            rel_averages = {band: power/total_abs_power for band, power in band_averages.items()}
        
        # Analyze using both absolute and relative powers
        abs_interpretation = self.interpret_mental_state({'band_powers': band_averages}, use_relative=False)
        rel_interpretation = self.interpret_mental_state({'rel_powers': rel_averages}, use_relative=True)
        
        print(f"\n📊 SESSION ANALYSIS (Absolute Powers)")
        self.display_results(abs_interpretation)
        
        print(f"\n📊 SESSION ANALYSIS (Relative Powers)")
        self.display_results(rel_interpretation)
        
        # Additional Mind Monitor specific analysis
        if 'jaw_clench' in df.columns:
            jaw_events = df['jaw_clench'].dropna().sum()
            print(f"😬 Jaw clenching events: {jaw_events}")
        
        if 'blink' in df.columns:
            blink_events = df['blink'].dropna().sum()
            print(f"👁️  Blink events: {blink_events}")
        
        # Quality metrics
        if 'touching_forehead' in df.columns:
            forehead_quality = df['touching_forehead'].dropna().mean()
            print(f"📊 Average forehead contact: {forehead_quality:.1%}")
    
    def _analyze_file_raw(self, df):
        """Analyze file using raw EEG signal processing"""
        # Process in chunks to avoid memory issues
        chunk_size = 1000
        all_results = []
        
        for i in range(0, len(df), chunk_size):
            chunk = df.iloc[i:i+chunk_size]
            result = self.analyze_eeg_window_raw(chunk)
            if result:
                all_results.append(result)
        
        if not all_results:
            print("❌ No valid data found for analysis")
            return
        
        # Average results across all chunks
        print(f"📈 Processed {len(all_results)} chunks")
        # Implementation would average band powers across chunks and interpret
    
    def monitor_realtime(self):
        """Monitor consciousness in real-time"""
        print("🔄 Starting real-time monitoring...")
        print("Commands: 'c' + Enter (copy recent), 's' + Enter (summary), 'n' + Enter (show now), 'q' + Enter (quit)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                # Check for user commands
                if not self._check_for_commands():
                    print("\n👋 Monitoring stopped by user command")
                    break
                    
                data = self.get_latest_data()
                
                if self.debug:
                    if data is not None:
                        print(f"🔍 Debug: Got {len(data)} samples, file size: {os.path.getsize(self.csv_file) if os.path.exists(self.csv_file) else 'N/A'}")
                    else:
                        print(f"🔍 Debug: No new data, file size: {os.path.getsize(self.csv_file) if os.path.exists(self.csv_file) else 'N/A'}")
                
                if data is not None:
                    # Determine analysis method based on available data
                    has_precomputed = all(col in data.columns for col in self.abs_band_columns[:3])
                    
                    if has_precomputed and self.use_precomputed:
                        results = self.analyze_eeg_window_precomputed(data)
                        if results and 'averaged' in results:
                            # Check if we have valid relative powers, otherwise use absolute
                            use_rel = sum(results['averaged']['rel_powers'].values()) > 0
                            interpretation = self.interpret_mental_state(results['averaged'], use_relative=use_rel)
                            
                            # Handle different timestamp column names
                            timestamp_col = None
                            for col in ['timestamp_local', 'timestamp_utc', 'TimeStamp']:
                                if col in data.columns:
                                    timestamp_col = col
                                    break
                            
                            if timestamp_col:
                                timestamp = data[timestamp_col].iloc[-1]
                            else:
                                timestamp = datetime.now().strftime("%H:%M:%S")
                            
                            self.display_results(interpretation, timestamp)
                    else:
                        results = self.analyze_eeg_window_raw(data)
                        if results:
                            # Use first available channel for display
                            first_channel = list(results.keys())[0]
                            interpretation = self.interpret_mental_state(results[first_channel])
                            self.display_results(interpretation)
                
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Error in real-time monitoring: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

def main():
    parser = argparse.ArgumentParser(description="Consciousness Monitor v3 - Mind Monitor Data Analysis")
    parser.add_argument("--file", "-f", help="CSV file to monitor or analyze", default="mind_monitor_data.csv")
    parser.add_argument("--window", "-w", type=float, default=0.75, help="Analysis window in seconds (default: 0.75)")
    parser.add_argument("--update", "-u", type=float, default=1.0, help="Update interval in seconds (default: 1.0)")
    parser.add_argument("--analyze", "-a", action="store_true", help="Analyze entire file instead of real-time monitoring")
    parser.add_argument("--no-bands", action="store_true", help="Hide band power visualization")
    parser.add_argument("--no-insights", action="store_true", help="Hide psychological insights")
    parser.add_argument("--channels", nargs='+', default=['TP9', 'AF7', 'AF8', 'TP10'], help="EEG channels to analyze")
    parser.add_argument("--raw", action="store_true", help="Use raw signal processing instead of pre-computed bands")
    parser.add_argument("--force-output", action="store_true", help="Force output every update (disable smart event detection)")
    parser.add_argument("--output-interval", type=float, help="Force output every N seconds (overrides smart detection)")
    parser.add_argument("--demo", action="store_true", help="Demo mode with simulated live data changes")
    parser.add_argument("--debug", action="store_true", help="Show debug information about data updates")
    
    args = parser.parse_args()
    
    # Create monitor instance
    monitor = ConsciousnessMonitor(
        csv_file=args.file,
        window_seconds=args.window,
        update_interval=args.update,
        channels=args.channels,
        show_bands=not args.no_bands,
        show_insights=not args.no_insights,
        use_precomputed=not args.raw,
        force_output=args.force_output,
        output_interval=args.output_interval,
        debug=args.debug
    )
    
    if args.analyze:
        monitor.analyze_file()
    else:
        monitor.monitor_realtime()

if __name__ == "__main__":
    main()