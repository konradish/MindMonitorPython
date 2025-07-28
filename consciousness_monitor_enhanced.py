#!/usr/bin/env python3
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

class EnhancedConsciousnessMonitor:
    def __init__(self, csv_file="mind_monitor_complete.csv", window_seconds=0.75, 
                 update_interval=1.0, show_bands=True, show_insights=True, 
                 show_optics=True, use_precomputed=True, force_output=False, 
                 output_interval=None, debug=False, konrad_mode=False, 
                 tune_rules=None, load_rules=None):
        
        self.csv_file = csv_file
        self.window_seconds = window_seconds
        self.update_interval = update_interval
        self.show_bands = show_bands
        self.show_insights = show_insights
        self.show_optics = show_optics
        self.use_precomputed = use_precomputed
        self.force_output = force_output
        self.output_interval = output_interval or (30 if not force_output else update_interval)
        self.debug = debug
        self.konrad_mode = konrad_mode
        
        # Auto-detect sample rate from data
        self.sample_rate = self._detect_sample_rate()
        self.window_samples = int(window_seconds * self.sample_rate)
        
        # Detect data format
        self.data_format = self._detect_data_format()
        
        # EEG frequency bands (clinical standards)
        self.bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),      
            'alpha': (8, 13),     
            'beta': (13, 30),     
            'gamma': (30, 50)
        }
        
        # Mind Monitor CSV column mapping
        self.eeg_columns = ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']
        self.abs_band_columns = ['abs_delta', 'abs_theta', 'abs_alpha', 'abs_beta', 'abs_gamma']
        self.rel_band_columns = ['rel_delta', 'rel_theta', 'rel_alpha', 'rel_beta', 'rel_gamma']
        self.quality_columns = ['touching_forehead', 'horseshoe_tp9', 'horseshoe_af7', 'horseshoe_af8', 'horseshoe_tp10']
        
        # Design filters once during initialization
        self.highpass_filter = signal.butter(4, 0.5, btype='high', fs=self.sample_rate)
        self.lowpass_filter = signal.butter(4, 50, btype='low', fs=self.sample_rate)
        self.notch_filter = signal.iirnotch(60, 30, fs=self.sample_rate)
        
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
        
        # dB tracking for before→after display and change detection
        self.previous_db_values = {}
        self.current_db_values = {}
        self.db_changes = {}
        
        # Configuration-driven detection rules with version tracking
        self.RULE_VERSION = "2025-07-28-v4"
        self.CHANGELOG = {
            "2025-07-27-v1": "Initial therapeutic patterns", 
            "2025-07-27-v2": "Fixed jhana detection, added meditation exemption, configuration-driven rules",
            "2025-07-27-v3": "Added Startled state detection - healthy startle response with beta spike + maintained alpha",
            "2025-07-28-v4": "Distinguished Flow State from Jhana - Added Flow State (70-89% alpha, 10-30% beta), refined Jhana to 90%+ alpha for pure consciousness"
        }
        
        # Maintainable detection rules as configuration
        self.DETECTION_RULES = {
            "security_guard": {
                "priority": 1,
                "conditions": {
                    "db_spike": {"delta": 6.0, "beta": 6.0, "alpha_drop": -2.0},
                    "alpha_exemption": 80,  # Don't trigger if alpha > 80% (meditation)
                    "percentage_fallback": {"beta_min": 25, "gamma_min": 25, "delta_max": 15}
                },
                "emoji": "🚨",
                "insights": ["🚨 Neural threat response detected", "⚡ Hypervigilance mode active"]
            },
            "jhana": {
                "priority": 2,
                "conditions": {"alpha_min": 90, "beta_max": 10, "gamma_max": 15, "delta_max": 20},
                "emoji": "🧘",
                "insights": ["🧘 Authentic jhana state - pure consciousness", "✨ Thinking mind completely dissolved", "🕉️ Transcendent absorption achieved"]
            },
            "flow_state": {
                "priority": 3,
                "conditions": {"alpha_min": 70, "alpha_max": 89, "beta_min": 10, "beta_max": 30, "gamma_max": 50},
                "emoji": "🌊",
                "insights": ["🌊 Deep flow state - engaged concentration", "🎯 Optimal performance zone activated", "⚡ Mind fully absorbed in task"]
            },
            "young_part": {
                "priority": 4,
                "conditions": {"delta_min": 35, "alpha_min": 30, "alpha_max": 40, "theta_min": 15},
                "emoji": "💝",
                "insights": ["💝 Young part present - vulnerable, childlike state", "🤗 Delta dominance indicates soft, trusting energy"]
            },
            "hopeful_part": {
                "priority": 5,
                "conditions": {"alpha_min": 75, "alpha_max": 80, "beta_max": 15, "delta_max": 20},
                "emoji": "🌟",
                "insights": ["🌟 Hopeful part engaged - optimistic consciousness"]
            },
            "startled": {
                "priority": 6,
                "conditions": {"beta_min": 40, "beta_max": 55, "alpha_min": 35, "alpha_max": 55, "beta_db_change_min": 2.0},
                "emoji": "😲",
                "insights": ["😲 Healthy startle response - alert but regulated", "🛡️ Nervous system responding appropriately to surprise"]
            },
            "cautious_part": {
                "priority": 7,
                "conditions": {"alpha_min": 50, "alpha_max": 70, "delta_min": 15, "beta_min": 15},
                "emoji": "🛡️",
                "insights": ["🛡️ Cautious part assessing - protective awareness"]
            },
            "recovery": {
                "priority": 8,
                "conditions": {"delta_min": 40, "requires_previous_state": "SECURITY GUARD"},
                "emoji": "🛡️",
                "insights": ["😮‍💨 Nervous system recovering from hypervigilance", "🛡️ Security guard standing down"]
            },
            "relaxed": {
                "priority": 9,
                "conditions": {"alpha_min": 40},  # Konrad's personalized threshold
                "emoji": "🌊",
                "insights": ["😌 Excellent regulation state"]
            },
            "focused": {
                "priority": 10,
                "conditions": {"beta_min": 35, "alpha_min": 25},
                "emoji": "🎯",
                "insights": []
            },
            "alert_tense": {
                "priority": 11,
                "conditions": {"beta_min": 35, "alpha_max": 25},
                "emoji": "🔴",
                "insights": []
            },
            "creative_flow": {
                "priority": 12,
                "conditions": {"theta_min": 30, "alpha_min": 20},
                "emoji": "🎨",
                "insights": ["🎨 Creative/flow state active"]
            },
            "meditative": {
                "priority": 13,
                "conditions": {"theta_min": 30, "alpha_max": 20},
                "emoji": "🧘",
                "insights": []
            },
            "drowsy": {
                "priority": 14,
                "conditions": {"delta_min": 40},
                "emoji": "😴",
                "insights": ["😴 Very relaxed/tired state"]
            },
            "peak_focus": {
                "priority": 15,
                "conditions": {"gamma_min": 25, "alpha_min": 20},
                "emoji": "⚡",
                "insights": ["⚡ Peak focus - productive concentration"]
            }
        }
        
        # Legacy rules for backwards compatibility
        self.KONRAD_RULES = {
            'security_guard': {
                'delta_spike_db': 6.0,
                'beta_spike_db': 6.0,   
                'alpha_drop_db': -2.0,
            },
            'excellent_regulation': {
                'alpha_percent': 50.0,
            },
            'relaxed': {
                'alpha_percent': 40.0,
            }
        }
        
        # Initialize command interface
        self.clipboard_queue = queue.Queue()
        self.command_interface_active = True
        
        # Rule tuning and loading
        self.tune_rules = tune_rules or {}
        if load_rules:
            self._load_rules_from_file(load_rules)
        if tune_rules:
            self._apply_rule_tuning(tune_rules)
        
        mode = "Pre-computed Features" if use_precomputed else "Raw Signal Processing"
        konrad_suffix = " | KONRAD MODE" if konrad_mode else ""
        color_prefix = f"{Fore.CYAN}" if COLORS_AVAILABLE else ""
        color_suffix = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
        print(f"{color_prefix}🧠 Enhanced Consciousness Monitor v4 - Therapeutic Edition{color_suffix}")
        print(f"Mode: {mode}{konrad_suffix} | Data format: {self.data_format}")
        print(f"Window: {window_seconds}s | Update: {update_interval}s | Sample Rate: {self.sample_rate}Hz")
        hotkey_msg = " | Commands: 'c' (copy), 's' (summary), 'n' (now), 'q' (quit)"
        print(f"Features: EEG + fNIRS + Therapeutic Pattern Detection{hotkey_msg}")
        if konrad_mode:
            print(f"🎯 Rule Version: {self.RULE_VERSION} - dB-based Security Guard with Meditation Exemption")
        if debug:
            print(f"🔍 Debug Mode: Rule testing enabled | Available rules: {len(self.DETECTION_RULES)}")
        print("🧠 Therapeutic Patterns: Jhana States, Parts Work (Young/Hopeful/Cautious), Startled Response, Safety Visualization")
        print("=" * 70)
    
    def _detect_sample_rate(self):
        """Auto-detect effective sample rate from existing data"""
        try:
            if os.path.exists(self.csv_file):
                # Try different CSV reading strategies for different formats
                df = None
                
                # First try: Standard CSV reading
                try:
                    df = pd.read_csv(self.csv_file, nrows=5000)
                except pd.errors.ParserError:
                    # Second try: Flexible CSV reading for muse-player format
                    try:
                        df = pd.read_csv(self.csv_file, nrows=5000, on_bad_lines='skip')
                    except:
                        print("📊 Could not parse CSV for sample rate detection, using 256Hz default")
                        return 256
                
                if df is not None and len(df) > 0:
                    # Try timestamp_utc first, then timestamp_local, then TimeStamp
                    timestamp_col = None
                    for col in ['timestamp_utc', 'timestamp_local', 'TimeStamp', 'timestamp']:
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

    def _detect_data_format(self):
        """Detect if CSV is from muse-player or custom script"""
        try:
            if not os.path.exists(self.csv_file):
                return "unknown"
            
            # Read first few lines to detect format
            with open(self.csv_file, 'r') as f:
                first_line = f.readline().strip()
                
            if first_line.startswith('timestamp_utc'):
                return "custom_script"
            elif ',' in first_line and ('/muse/' in first_line or first_line.split(',')[0].replace('.', '').isdigit()):
                return "muse_player"
            else:
                return "unknown"
        except:
            return "unknown"
    
    def parse_muse_player_data(self, raw_df):
        """Convert muse-player CSV format to structured data"""
        structured_data = {
            'timestamp': [],
            'eeg': {'tp9': [], 'af7': [], 'af8': [], 'tp10': [], 'aux1': [], 'aux2': [], 'aux3': [], 'aux4': []},
            'optics': {'ch1': [], 'ch2': [], 'ch3': [], 'ch4': [], 'ch5': [], 'ch6': [], 'ch7': [], 'ch8': [],
                      'ch9': [], 'ch10': [], 'ch11': [], 'ch12': [], 'ch13': [], 'ch14': [], 'ch15': [], 'ch16': []},
            'motion': {'accel_x': [], 'accel_y': [], 'accel_z': [], 'gyro_x': [], 'gyro_y': [], 'gyro_z': []},
            'bands': {'delta': [], 'theta': [], 'alpha': [], 'beta': [], 'gamma': []},
            'quality': {'touching_forehead': [], 'horseshoe': []},
            'features': {'blink': [], 'jaw_clench': []},
            'battery': []
        }
        
        for _, row in raw_df.iterrows():
            timestamp = float(row['timestamp']) if pd.notna(row['timestamp']) else None
            osc_address = row['osc_address'] if pd.notna(row['osc_address']) else ''
            
            if timestamp is None or not osc_address:
                continue
                
            # Parse data based on OSC address
            if osc_address == ' /muse/eeg':
                # EEG data - up to 8 channels
                try:
                    eeg_data = [float(x) for x in row.iloc[2:10] if pd.notna(x) and str(x) != '']
                    if len(eeg_data) >= 4:
                        structured_data['timestamp'].append(timestamp)
                        structured_data['eeg']['tp9'].append(eeg_data[0])
                        structured_data['eeg']['af7'].append(eeg_data[1])
                        structured_data['eeg']['af8'].append(eeg_data[2])
                        structured_data['eeg']['tp10'].append(eeg_data[3])
                        # Additional channels if available
                        for i, aux_ch in enumerate(['aux1', 'aux2', 'aux3', 'aux4']):
                            if len(eeg_data) > 4 + i:
                                structured_data['eeg'][aux_ch].append(eeg_data[4 + i])
                            else:
                                structured_data['eeg'][aux_ch].append(np.nan)
                except (ValueError, TypeError):
                    continue
            
            elif osc_address == ' /muse/optics':
                # fNIRS optical data - 16 channels
                try:
                    optics_data = [float(x) for x in row.iloc[2:18] if pd.notna(x) and str(x) != '']
                    if len(optics_data) >= 4:
                        structured_data['timestamp'].append(timestamp)
                        for i, ch_name in enumerate([f'ch{i+1}' for i in range(16)]):
                            if i < len(optics_data):
                                structured_data['optics'][ch_name].append(optics_data[i])
                            else:
                                structured_data['optics'][ch_name].append(0.0)
                except (ValueError, TypeError):
                    continue
            
            elif osc_address == ' /muse/acc':
                # Accelerometer data
                try:
                    acc_data = [float(x) for x in row.iloc[2:5] if pd.notna(x) and str(x) != '']
                    if len(acc_data) == 3:
                        structured_data['motion']['accel_x'].append(acc_data[0])
                        structured_data['motion']['accel_y'].append(acc_data[1])
                        structured_data['motion']['accel_z'].append(acc_data[2])
                except (ValueError, TypeError):
                    continue
            
            elif osc_address == ' /muse/gyro':
                # Gyroscope data
                try:
                    gyro_data = [float(x) for x in row.iloc[2:5] if pd.notna(x) and str(x) != '']
                    if len(gyro_data) == 3:
                        structured_data['motion']['gyro_x'].append(gyro_data[0])
                        structured_data['motion']['gyro_y'].append(gyro_data[1])
                        structured_data['motion']['gyro_z'].append(gyro_data[2])
                except (ValueError, TypeError):
                    continue
            
            elif 'absolute' in osc_address:
                # Band power data
                band_name = osc_address.split('/')[-1].replace('_absolute', '')
                value = float(row.iloc[2]) if pd.notna(row.iloc[2]) and row.iloc[2] != '' else None
                if value is not None and band_name in self.bands:
                    structured_data['bands'][band_name].append(value)
        
        return structured_data
    
    def _power_to_db(self, power_value, reference_power=1.0):
        """Convert power value to dB scale"""
        try:
            if power_value <= 0:
                return -100.0  # Very low value for zero/negative power
            db_value = 10 * np.log10(power_value / reference_power)
            return max(-100.0, min(100.0, db_value))  # Clamp to reasonable range
        except:
            return -100.0
    
    def _update_db_tracking(self, ratios):
        """Update dB tracking with current band power values and calculate changes"""
        # Store previous values
        self.previous_db_values = self.current_db_values.copy()
        
        # Calculate new dB values
        self.current_db_values = {}
        self.db_changes = {}
        
        for band, percentage in ratios.items():
            # Convert percentage to power (assuming total power = 1.0)
            power = percentage / 100.0
            current_db = self._power_to_db(power)
            self.current_db_values[band] = current_db
            
            # Calculate dB change if we have previous values
            if band in self.previous_db_values:
                self.db_changes[band] = current_db - self.previous_db_values[band]
            else:
                self.db_changes[band] = 0.0
    
    def _format_band_with_db(self, band, percentage):
        """Format band display with percentage and dB tracking, emphasizing significant changes"""
        current_db = self.current_db_values.get(band, -100.0)
        db_change = self.db_changes.get(band, 0.0)
        
        # Show change prominently if significant (especially for Security Guard detection)
        if abs(db_change) > 0.5:  # Lower threshold to catch more changes
            sign = "+" if db_change > 0 else ""
            return f"{band.capitalize()}: {percentage:.0f}% ({sign}{db_change:.1f}dB)"
        elif abs(db_change) > 0.1:  # Show transition for smaller changes
            previous_db = self.previous_db_values.get(band, current_db)
            return f"{band.capitalize()}: {percentage:.0f}% ({previous_db:.1f}dB→{current_db:.1f}dB)"
        else:
            return f"{band.capitalize()}: {percentage:.0f}% ({current_db:.1f}dB)"
    
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
                clipboard_text = "\\n".join([event['text'] for event in recent_events])
                
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
            
            summary = f"ENHANCED SESSION: {duration_min}min | States: {states_str}\\n"
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
    
    def analyze_optics_data(self, optics_data, window_samples=None):
        """Analyze fNIRS optical data for hemodynamic responses"""
        if not optics_data:
            return None
        
        # Check if we have valid channel data
        if 'ch1' not in optics_data or optics_data['ch1'] is None or len(optics_data['ch1']) < 10:
            return None
            
        # Get recent window of data
        if window_samples:
            for ch in optics_data:
                if optics_data[ch] is not None and len(optics_data[ch]) > 0:
                    optics_data[ch] = optics_data[ch][-window_samples:]
        
        # Analyze first 4 channels (typical fNIRS setup)
        active_channels = ['ch1', 'ch2', 'ch3', 'ch4']
        results = {}
        
        for ch in active_channels:
            if ch in optics_data and optics_data[ch] is not None and len(optics_data[ch]) > 0:
                data = np.array(optics_data[ch])
                if len(data) > 5:
                    # Basic hemodynamic analysis
                    baseline = np.mean(data[:5]) if len(data) > 5 else np.mean(data)
                    current = np.mean(data[-5:]) if len(data) > 5 else np.mean(data)
                    change = current - baseline
                    
                    # Detect activation patterns
                    activation = "none"
                    if change > 0.1:
                        activation = "increased"
                    elif change < -0.1:
                        activation = "decreased"
                    
                    results[ch] = {
                        'baseline': baseline,
                        'current': current,
                        'change': change,
                        'activation': activation,
                        'intensity': abs(change)
                    }
        
        return results
    
    def interpret_enhanced_state(self, eeg_analysis, optics_analysis=None):
        """Enhanced mental state interpretation including fNIRS data with robust error handling"""
        try:
            base_interpretation = eeg_analysis
            
            if not base_interpretation:
                return self._get_no_signal_result()
            
            # Enhanced EEG interpretation with validation
            ratios = base_interpretation.get('ratios', {})
            if not ratios:
                return self._get_no_signal_result()
            
            # Validate ratio values
            valid_ratios = {}
            for band, ratio in ratios.items():
                if ratio is not None and not np.isnan(float(ratio)) and not np.isinf(float(ratio)):
                    valid_ratios[band] = max(0, float(ratio))
            
            if not valid_ratios:
                return self._get_no_signal_result()
            
            # Enhanced state detection
            state_indicators = []
            confidence = "MODERATE"
            
            # Convert to percentages if needed
            total_power = sum(valid_ratios.values())
            if total_power > 0:
                percentage_ratios = {band: (power / total_power) * 100 for band, power in valid_ratios.items()}
            else:
                return self._get_no_signal_result()
            
            # Configuration-driven state detection with maintainable architecture
            
            # Initialize insights list
            enhanced_insights = []
            
            # Get dB changes (will be 0 for first measurement)
            delta_db_change = self.db_changes.get('delta', 0.0)
            beta_db_change = self.db_changes.get('beta', 0.0)
            alpha_db_change = self.db_changes.get('alpha', 0.0)
            gamma_db_change = self.db_changes.get('gamma', 0.0)
            
            # Debug mode output
            if self.debug:
                print(f"Debug - Band %: Alpha={percentage_ratios.get('alpha', 0):.1f}% Beta={percentage_ratios.get('beta', 0):.1f}% Delta={percentage_ratios.get('delta', 0):.1f}% Theta={percentage_ratios.get('theta', 0):.1f}% Gamma={percentage_ratios.get('gamma', 0):.1f}%")
                print(f"Debug - dB changes: Alpha={alpha_db_change:+.1f} Beta={beta_db_change:+.1f} Delta={delta_db_change:+.1f}")
            
            # Test rules in priority order
            detected_state = self._evaluate_detection_rules(percentage_ratios, {
                'delta_db_change': delta_db_change,
                'beta_db_change': beta_db_change, 
                'alpha_db_change': alpha_db_change,
                'gamma_db_change': gamma_db_change
            })
            
            if detected_state:
                state_indicators = [detected_state['state']]
                emoji = detected_state['emoji']
                confidence = "HIGH"
                enhanced_insights.extend(detected_state['insights'])
            else:
                # Fallback to neutral
                state_indicators = ["NEUTRAL"]
                emoji = "🧠"
                confidence = "MODERATE"
            
            state = " + ".join(state_indicators)
            
            # Generate additional insights with validation - therapeutic context
            try:
                # Check for parts work transitions
                if (hasattr(self, 'last_state') and self.last_state and 
                    self.last_state != state and 
                    any("PART" in state_name for state_name in [self.last_state, state])):
                    enhanced_insights.append("🔄 Internal parts transition detected")
                
                # Safety visualization detection (massive alpha spikes)
                if alpha_db_change > 90:
                    enhanced_insights.append("🌊 Powerful safety visualization detected")
                    enhanced_insights.append(f"⚡ Alpha surge: +{alpha_db_change:.1f}dB - conscious regulation active")
                
                # Show dB changes for security guard detection (if significant)
                if "SECURITY GUARD" in state:
                    enhanced_insights.append(f"⚡ dB changes: Delta={delta_db_change:+.1f}, Beta={beta_db_change:+.1f}, Alpha={alpha_db_change:+.1f}")
                
                # Alpha dominance levels (additional context)
                alpha_percent = percentage_ratios.get('alpha', 0)
                if alpha_percent > 90:
                    enhanced_insights.append("✨ Near-pure consciousness state")
                elif alpha_percent > 80:
                    enhanced_insights.append("🧘 Deep transcendent awareness")
                elif alpha_percent > 70 and "JHANA" not in state:
                    enhanced_insights.append("😌 Excellent regulation state")
                
                # Therapeutic work recognition
                if any(part in state for part in ["HOPEFUL", "CAUTIOUS", "YOUNG"]):
                    enhanced_insights.append("🧠 Active internal family systems work detected")
                
                # Standard emotional terrain navigation
                if percentage_ratios.get('theta', 0) > 15 and percentage_ratios.get('alpha', 0) > 15:
                    enhanced_insights.append("🌊 Good emotional terrain navigation")
                
                # Detect rapid parts switching (therapeutic "sandwich" patterns)
                if hasattr(self, 'last_output_time') and hasattr(self, 'last_state'):
                    time_since_last_state = time.time() - self.last_output_time
                    if (time_since_last_state < 60 and self.last_state != state and 
                        "PART" in str(self.last_state) and "PART" in str(state)):
                        enhanced_insights.append("🥪 Parts dialogue sequence detected")
            except Exception as e:
                warning_color = f"{Fore.YELLOW}" if COLORS_AVAILABLE else ""
                reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
                print(f"{warning_color}⚠️ EEG insight generation error: {e}{reset_color}")
            
            # Add optical analysis with enhanced validation
            fnirs_value = 0
            if optics_analysis and self.show_optics:
                try:
                    # Analyze hemodynamic patterns with null safety
                    valid_optics = {ch: data for ch, data in optics_analysis.items() 
                                   if data and 'intensity' in data and 'change' in data}
                    
                    if valid_optics:
                        total_activation = sum(ch['intensity'] for ch in valid_optics.values())
                        changes = [ch['change'] for ch in valid_optics.values()]
                        avg_change = np.mean(changes) if changes else 0
                        fnirs_value = avg_change
                        
                        if total_activation > 0.5:
                            enhanced_insights.append("🔴 Strong hemodynamic activity detected")
                        
                        if avg_change > 0.2:
                            enhanced_insights.append("🧠 Increased cerebral blood flow - active cognition")
                        elif avg_change < -0.2:
                            enhanced_insights.append("💤 Decreased cerebral blood flow - rest state")
                        
                        # Cross-correlate with EEG
                        if percentage_ratios.get('alpha', 0) > 30 and avg_change > 0.1:
                            enhanced_insights.append("🎯 Alpha waves + blood flow = optimal learning state")
                        
                        if percentage_ratios.get('gamma', 0) > 15 and total_activation > 0.3:
                            enhanced_insights.append("⚡ Gamma activity + hemodynamics = intense focus")
                except Exception as e:
                    warning_color = f"{Fore.YELLOW}" if COLORS_AVAILABLE else ""
                    reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
                    print(f"{warning_color}⚠️ fNIRS analysis error: {e}{reset_color}")
            
            return {
                'state': state,
                'confidence': confidence,
                'insights': enhanced_insights,
                'ratios': percentage_ratios,
                'quality': base_interpretation.get('quality', {}),
                'optics': optics_analysis,
                'fnirs': fnirs_value
            }
        
        except Exception as e:
            error_color = f"{Fore.RED}" if COLORS_AVAILABLE else ""
            reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
            print(f"{error_color}❌ Enhanced state interpretation error: {e}{reset_color}")
            return self._get_no_signal_result()
    
    def _get_no_signal_result(self):
        """Return standard no signal result"""
        return {
            "state": "No signal", 
            "confidence": "LOW", 
            "insights": [], 
            "ratios": {band: 0 for band in self.bands.keys()}, 
            "quality": {},
            "optics": None,
            "fnirs": 0
        }
    
    def _safe_get_band(self, bands, band_name):
        """Handle missing or zero band data safely"""
        if band_name not in bands or bands[band_name] is None:
            return 0
        value = bands[band_name]
        if isinstance(value, (int, float)) and not (np.isnan(value) or np.isinf(value)):
            return max(0, value)
        return 0
    
    def _evaluate_detection_rules(self, percentage_ratios, db_changes):
        """Configuration-driven rule evaluation with priority ordering"""
        # Safe band value extraction
        alpha_percent = self._safe_get_band(percentage_ratios, 'alpha')
        beta_percent = self._safe_get_band(percentage_ratios, 'beta')
        delta_percent = self._safe_get_band(percentage_ratios, 'delta')
        theta_percent = self._safe_get_band(percentage_ratios, 'theta')
        gamma_percent = self._safe_get_band(percentage_ratios, 'gamma')
        
        # Sort rules by priority
        sorted_rules = sorted(self.DETECTION_RULES.items(), key=lambda x: x[1]['priority'])
        
        for rule_name, rule in sorted_rules:
            if self.debug:
                print(f"Debug - Testing rule: {rule_name}")
            
            if self._test_rule_conditions(rule_name, rule, {
                'alpha': alpha_percent, 'beta': beta_percent, 'delta': delta_percent, 
                'theta': theta_percent, 'gamma': gamma_percent
            }, db_changes):
                if self.debug:
                    print(f"Debug - Rule matched: {rule_name} ✅")
                
                return {
                    'state': rule_name.replace('_', ' ').upper(),
                    'emoji': rule['emoji'],
                    'insights': rule.get('insights', [])
                }
            elif self.debug:
                print(f"Debug - Rule failed: {rule_name} ❌")
        
        return None
    
    def _test_rule_conditions(self, rule_name, rule, bands, db_changes):
        """Test if a rule's conditions are met"""
        conditions = rule['conditions']
        
        # Special handling for security guard with meditation exemption
        if rule_name == 'security_guard':
            return self._test_security_guard_conditions(conditions, bands, db_changes)
        
        # Special handling for recovery state
        if rule_name == 'recovery':
            if not (hasattr(self, 'last_state') and self.last_state and 
                   conditions.get('requires_previous_state', '') in self.last_state):
                return False
        
        # Test standard percentage conditions
        for condition, value in conditions.items():
            if condition.endswith('_min') and not condition.endswith('_db_change_min'):
                if bands.get(condition[:-4], 0) < value:
                    return False
            elif condition.endswith('_max') and not condition.endswith('_db_change_max'):
                if bands.get(condition[:-4], 0) > value:
                    return False
            elif condition.endswith('_db_change_min'):
                # Handle dB change minimum conditions (e.g., beta_db_change_min)
                band_name = condition.replace('_db_change_min', '')
                db_change_key = f'{band_name}_db_change'
                if db_changes.get(db_change_key, 0) < value:
                    return False
        
        return True
    
    def _test_security_guard_conditions(self, conditions, bands, db_changes):
        """Special security guard detection with meditation exemption"""
        alpha_percent = bands.get('alpha', 0)
        
        # Meditation exemption - don't trigger security guard if alpha > 80%
        if alpha_percent > conditions.get('alpha_exemption', 80):
            if self.debug:
                print(f"Debug - Security guard exempted due to meditation state (alpha={alpha_percent:.1f}%)")
            return False
        
        # Primary dB-based detection
        db_spike = conditions.get('db_spike', {})
        if ((db_changes.get('delta_db_change', 0) > db_spike.get('delta', 6.0) or 
             db_changes.get('beta_db_change', 0) > db_spike.get('beta', 6.0)) and
            db_changes.get('alpha_db_change', 0) < db_spike.get('alpha_drop', -2.0)):
            return True
        
        # Fallback percentage-based detection
        fallback = conditions.get('percentage_fallback', {})
        if (bands.get('beta', 0) > fallback.get('beta_min', 25) and 
            bands.get('gamma', 0) > fallback.get('gamma_min', 25) and 
            bands.get('delta', 0) < fallback.get('delta_max', 15)):
            return True
        
        return False
    
    def _load_rules_from_file(self, filename):
        """Load detection rules from external file"""
        try:
            import json
            with open(filename, 'r') as f:
                loaded_rules = json.load(f)
            self.DETECTION_RULES.update(loaded_rules)
            print(f"📁 Loaded rules from {filename}")
        except Exception as e:
            print(f"⚠️ Could not load rules from {filename}: {e}")
    
    def _apply_rule_tuning(self, tune_rules):
        """Apply command-line rule tuning"""
        for rule_name, params in tune_rules.items():
            if rule_name in self.DETECTION_RULES:
                conditions = self.DETECTION_RULES[rule_name].get('conditions', {})
                for param, value in params.items():
                    if param in conditions:
                        old_value = conditions[param]
                        conditions[param] = value
                        print(f"🔧 Tuned {rule_name}.{param}: {old_value} → {value}")
                    else:
                        print(f"⚠️ Unknown parameter {rule_name}.{param}")
            else:
                print(f"⚠️ Unknown rule: {rule_name}")
    
    def display_enhanced_results(self, interpretation, timestamp=None):
        """Display enhanced analysis results with smart output system"""
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
                # Update dB tracking
                self._update_db_tracking(ratios)
                
                # Generate compact output
                timestamp_str = datetime.now().strftime("%H:%M:%S")
                
                # Format main output line with enhanced features including dB
                if dominant_value > 50:  # Show single dominant band
                    band_str = self._format_band_with_db(dominant_band, dominant_value)
                    emoji = self._get_band_emoji(dominant_band)
                else:  # Show multiple bands if balanced
                    significant_bands = [(band, value) for band, value in ratios.items() if value > 20]
                    band_str = " ".join([self._format_band_with_db(band, value) for band, value in significant_bands[:2]])
                    emoji = self._get_state_emoji(state)
                
                # Enhanced fNIRS display
                fnirs_str = f"fNIRS: {fnirs:+.3f}"
                
                # Color coding with enhanced states
                if "SECURITY GUARD" in state:
                    color = f"{Fore.RED}" if COLORS_AVAILABLE else ""
                elif "RECOVERY" in state:
                    color = f"{Fore.YELLOW}" if COLORS_AVAILABLE else ""
                elif "ALERT" in state or "TENSE" in state:
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
                
                # Show optical data if available
                if self.show_optics and interpretation.get('optics'):
                    optics = interpretation['optics']
                    if optics:
                        activations = [f"{ch}:{data.get('activation', 'none')}" for ch, data in list(optics.items())[:2]]
                        output_line += f" | Optics: {' '.join(activations)}"
                
                print(output_line)
                
                # Show detailed bands if requested
                if self.show_bands and ratios:
                    bands_display = " ".join([self._format_band_with_db(band, value) for band, value in ratios.items() if value > 10])
                    if bands_display:
                        print(f"         Bands: {bands_display}")
                
                # Show insights if available and requested
                if self.show_insights and interpretation.get('insights'):
                    for insight in interpretation['insights'][:2]:  # Limit to 2 insights for compactness
                        print(f"         {insight}")
                
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
                if ("Security guard" in str(interpretation.get('insights', [])) or 
                    "SECURITY GUARD" in state or 
                    "🚨" in str(interpretation.get('insights', []))):
                    self.security_guard_count += 1
        
        except Exception as e:
            error_color = f"{Fore.RED}" if COLORS_AVAILABLE else ""
            reset_color = f"{Style.RESET_ALL}" if COLORS_AVAILABLE else ""
            print(f"{error_color}❌ Enhanced display error: {e}{reset_color}")
    
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
        if "SECURITY GUARD" in state:
            return "🚨"
        elif "RECOVERY" in state:
            return "🛡️"
        elif "ALERT" in state or "TENSE" in state:
            return "🔴"
        elif "FLOW STATE" in state:
            return "🌊"
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
    
    def get_latest_data_muse_player(self):
        """Get latest data from muse-player CSV format"""
        try:
            if not os.path.exists(self.csv_file):
                return None
            
            # Check if file has new data
            current_size = os.path.getsize(self.csv_file)
            if current_size <= self.last_file_size:
                return None
            
            # Read new data
            lines = []
            max_cols = 0
            
            with open(self.csv_file, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    lines.append(parts)
                    max_cols = max(max_cols, len(parts))
            
            if not lines:
                return None
            
            # Pad all rows to same length
            for line in lines:
                while len(line) < max_cols:
                    line.append('')
            
            # Create DataFrame
            df = pd.DataFrame(lines)
            df.columns = ['timestamp', 'osc_address'] + [f'data_{i}' for i in range(max_cols-2)]
            df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
            
            # Update file size
            self.last_file_size = current_size
            
            # Get recent window
            recent_df = df.tail(int(self.window_seconds * 500))  # Estimate based on sample rate
            
            return self.parse_muse_player_data(recent_df)
            
        except Exception as e:
            print(f"Error getting latest data: {e}")
            return None
    
    def get_latest_data_mind_monitor(self):
        """Get latest data from Mind Monitor CSV format"""
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
            print(f"Error getting latest Mind Monitor data: {e}")
            return None
    
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
    
    def monitor_realtime(self):
        """Monitor consciousness in real-time with enhanced analysis and command interface"""
        if self.data_format != "muse_player" and self.data_format != "custom_script":
            print("❌ This monitor supports muse-player or Mind Monitor CSV formats")
            return
        
        print("🔄 Starting enhanced real-time monitoring...")
        print("Commands: 'c' + Enter (copy recent), 's' + Enter (summary), 'n' + Enter (show now), 'q' + Enter (quit)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                # Check for user commands
                if not self._check_for_commands():
                    print("\n👋 Enhanced monitoring stopped by user command")
                    break
                
                # Get data based on detected format
                if self.data_format == "muse_player":
                    data = self.get_latest_data_muse_player()
                else:
                    # Handle Mind Monitor format or custom script format
                    data = self.get_latest_data_mind_monitor()
                
                if self.debug:
                    if data:
                        print(f"🔍 Debug: Got data, format: {self.data_format}")
                    else:
                        print(f"🔍 Debug: No new data, format: {self.data_format}")
                
                if data:
                    if self.data_format == "muse_player" and len(data.get('timestamp', [])) > 10:
                        # Analyze muse-player data
                        eeg_ratios = {}
                        if data['bands']:
                            total_power = sum(sum(band_data[-10:]) for band_data in data['bands'].values() if band_data)
                            if total_power > 0:
                                for band, band_data in data['bands'].items():
                                    if band_data:
                                        recent_power = sum(band_data[-10:])
                                        eeg_ratios[band] = recent_power / total_power
                        
                        eeg_analysis = {
                            'state': 'Active',
                            'confidence': 'MODERATE',
                            'insights': [],
                            'ratios': eeg_ratios
                        }
                        
                        # Analyze fNIRS
                        optics_analysis = self.analyze_optics_data(data['optics'], window_samples=50)
                        
                        # Combine analyses
                        interpretation = self.interpret_enhanced_state(eeg_analysis, optics_analysis)
                        
                        # Display results
                        latest_timestamp = data['timestamp'][-1] if data['timestamp'] else None
                        self.display_enhanced_results(interpretation, latest_timestamp)
                    
                    elif hasattr(data, 'columns'):
                        # Handle Mind Monitor DataFrame format
                        results = self.analyze_eeg_window_precomputed(data)
                        if results and 'averaged' in results:
                            # Check if we have valid relative powers, otherwise use absolute
                            use_rel = sum(results['averaged']['rel_powers'].values()) > 0
                            interpretation = self.interpret_enhanced_state(results['averaged'], None)
                            
                            # Handle different timestamp column names
                            timestamp_col = None
                            for col in ['timestamp_local', 'timestamp_utc', 'TimeStamp', 'timestamp']:
                                if col in data.columns:
                                    timestamp_col = col
                                    break
                            
                            if timestamp_col:
                                timestamp = data[timestamp_col].iloc[-1]
                            else:
                                timestamp = datetime.now().strftime("%H:%M:%S")
                            
                            self.display_enhanced_results(interpretation, timestamp)
                
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print("\n👋 Enhanced monitoring stopped by user")
        except Exception as e:
            print(f"❌ Error in enhanced monitoring: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)
    
    def analyze_file(self):
        """Analyze entire file and generate comprehensive report"""
        if not os.path.exists(self.csv_file):
            print(f"❌ File not found: {self.csv_file}")
            return
        
        print(f"📊 Analyzing file: {self.csv_file}")
        print(f"Mode: {'Pre-computed Features' if self.use_precomputed else 'Raw Signal Processing'}")
        print("=" * 70)
        
        try:
            # Read entire file
            if self.data_format == "custom_script":
                df = pd.read_csv(self.csv_file)
                total_samples = len(df)
                duration_minutes = total_samples / self.sample_rate / 60
                
                print(f"📈 Dataset: {total_samples:,} samples ({duration_minutes:.1f} minutes)")
                print(f"🔍 Sample rate: {self.sample_rate}Hz | Window: {self.window_seconds}s")
                print("=" * 70)
                
                # Analyze in chunks
                self._analyze_file_chunks(df)
                
            elif self.data_format == "muse_player":
                # Handle muse-player format
                print("📊 Analyzing muse-player format...")
                self._analyze_muse_player_file()
            
            else:
                print(f"❌ Unsupported file format: {self.data_format}")
                return
                
        except Exception as e:
            print(f"❌ Error analyzing file: {e}")
    
    def _analyze_file_chunks(self, df):
        """Analyze file in chunks and generate statistics"""
        window_samples = int(self.window_seconds * self.sample_rate)
        step_samples = int(self.update_interval * self.sample_rate)
        
        # Initialize statistics
        all_states = []
        all_ratios = []
        significant_events = []
        state_durations = {}
        peak_values = {'alpha': 0, 'beta': 0, 'theta': 0, 'delta': 0, 'gamma': 0}
        
        print("🔄 Processing data chunks...")
        
        # Process in overlapping windows
        for start_idx in range(0, len(df) - window_samples, step_samples):
            end_idx = start_idx + window_samples
            chunk = df.iloc[start_idx:end_idx]
            
            if len(chunk) < window_samples:
                continue
            
            # Analyze this chunk
            if self.use_precomputed:
                results = self.analyze_eeg_window_precomputed(chunk)
            else:
                # For raw analysis, we'd need to implement raw signal processing
                results = self.analyze_eeg_window_precomputed(chunk)  # Fallback to precomputed
            
            if results and 'averaged' in results:
                interpretation = self.interpret_enhanced_state(results['averaged'], None)
                
                if interpretation and interpretation.get('ratios'):
                    # Store for analysis
                    all_states.append(interpretation['state'])
                    all_ratios.append(interpretation['ratios'])
                    
                    # Track peak values
                    for band, value in interpretation['ratios'].items():
                        if value > peak_values[band]:
                            peak_values[band] = value
                    
                    # Track significant events
                    if interpretation.get('insights'):
                        timestamp_col = self._get_timestamp_column(chunk)
                        if timestamp_col:
                            timestamp = chunk[timestamp_col].iloc[-1]
                        else:
                            timestamp = f"Sample {end_idx}"
                        
                        for insight in interpretation['insights']:
                            significant_events.append({
                                'timestamp': timestamp,
                                'insight': insight,
                                'state': interpretation['state'],
                                'ratios': interpretation['ratios'].copy()
                            })
                    
                    # Track state durations
                    state = interpretation['state']
                    if state in state_durations:
                        state_durations[state] += 1
                    else:
                        state_durations[state] = 1
        
        # Generate comprehensive report
        self._generate_analysis_report(all_states, all_ratios, significant_events, 
                                     state_durations, peak_values, df)
    
    def _analyze_muse_player_file(self):
        """Analyze muse-player format file"""
        try:
            lines = []
            max_cols = 0
            
            with open(self.csv_file, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    lines.append(parts)
                    max_cols = max(max_cols, len(parts))
            
            # Process data similar to real-time monitoring
            for line in lines:
                while len(line) < max_cols:
                    line.append(None)
            
            df = pd.DataFrame(lines)
            df.columns = ['timestamp', 'osc_address'] + [f'data_{i}' for i in range(max_cols-2)]
            df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
            
            # Parse and analyze
            parsed_data = self.parse_muse_player_data(df)
            
            if parsed_data and len(parsed_data.get('timestamp', [])) > 0:
                duration_seconds = len(parsed_data['timestamp']) / self.sample_rate
                print(f"📈 Dataset: {len(parsed_data['timestamp']):,} samples ({duration_seconds/60:.1f} minutes)")
                
                # Analyze EEG and fNIRS data
                self._analyze_parsed_muse_data(parsed_data)
            else:
                print("❌ No valid data found in muse-player file")
                
        except Exception as e:
            print(f"❌ Error analyzing muse-player file: {e}")
    
    def _analyze_parsed_muse_data(self, data):
        """Analyze parsed muse-player data"""
        if not data or not data.get('timestamp'):
            print("❌ No valid muse-player data found")
            return
        
        print("🔄 Processing muse-player data...")
        
        # Initialize statistics
        all_states = []
        all_ratios = []
        significant_events = []
        state_durations = {}
        peak_values = {'alpha': 0, 'beta': 0, 'theta': 0, 'delta': 0, 'gamma': 0}
        
        # Process EEG data in windows
        timestamps = data['timestamp']
        eeg_data = data['eeg']
        window_samples = int(self.window_seconds * self.sample_rate)
        step_samples = int(self.update_interval * self.sample_rate)
        
        # Check if we have band power data
        has_bands = any(data['bands'].get(band, []) for band in ['delta', 'theta', 'alpha', 'beta', 'gamma'])
        
        for start_idx in range(0, len(timestamps) - window_samples, step_samples):
            end_idx = start_idx + window_samples
            
            if end_idx > len(timestamps):
                break
            
            # Extract window data
            window_timestamps = timestamps[start_idx:end_idx]
            if not window_timestamps:
                continue
            
            # Analyze this window
            if has_bands:
                # Use pre-computed band powers if available
                eeg_ratios = {}
                total_power = 0
                
                for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
                    band_data = data['bands'].get(band, [])
                    if band_data and start_idx < len(band_data):
                        # Get band power for this window
                        window_band_data = band_data[start_idx:end_idx]
                        if window_band_data:
                            avg_power = np.mean([x for x in window_band_data if x is not None and not np.isnan(x)])
                            if not np.isnan(avg_power):
                                eeg_ratios[band] = max(0, avg_power)
                                total_power += avg_power
                
                # Normalize to percentages
                if total_power > 0:
                    eeg_ratios = {band: (power / total_power) * 100 for band, power in eeg_ratios.items()}
                else:
                    eeg_ratios = {band: 0 for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']}
            else:
                # Calculate from raw EEG if no band data
                eeg_ratios = self._calculate_bands_from_raw_muse(eeg_data, start_idx, end_idx)
            
            if eeg_ratios and sum(eeg_ratios.values()) > 0:
                # Create interpretation
                eeg_analysis = {
                    'state': 'Active',
                    'confidence': 'MODERATE',
                    'insights': [],
                    'ratios': eeg_ratios
                }
                
                # Analyze fNIRS if available
                optics_analysis = None
                if data.get('optics') and any(data['optics'].get(f'ch{i}', []) for i in range(1, 5)):
                    window_optics = {}
                    for i in range(1, 5):
                        ch_name = f'ch{i}'
                        if ch_name in data['optics'] and start_idx < len(data['optics'][ch_name]):
                            window_optics[ch_name] = data['optics'][ch_name][start_idx:end_idx]
                    
                    if window_optics:
                        optics_analysis = self.analyze_optics_data(window_optics, window_samples)
                
                # Get enhanced interpretation
                interpretation = self.interpret_enhanced_state(eeg_analysis, optics_analysis)
                
                if interpretation and interpretation.get('ratios'):
                    # Store for analysis
                    all_states.append(interpretation['state'])
                    all_ratios.append(interpretation['ratios'])
                    
                    # Track peak values
                    for band, value in interpretation['ratios'].items():
                        if value > peak_values[band]:
                            peak_values[band] = value
                    
                    # Track significant events
                    if interpretation.get('insights'):
                        timestamp = window_timestamps[-1] if window_timestamps else f"Sample {end_idx}"
                        
                        for insight in interpretation['insights']:
                            significant_events.append({
                                'timestamp': timestamp,
                                'insight': insight,
                                'state': interpretation['state'],
                                'ratios': interpretation['ratios'].copy()
                            })
                    
                    # Track state durations
                    state = interpretation['state']
                    if state in state_durations:
                        state_durations[state] += 1
                    else:
                        state_durations[state] = 1
        
        # Generate report using existing method
        # Create a dummy DataFrame for compatibility
        dummy_df = pd.DataFrame({'touching_forehead': [1] * len(timestamps)})
        self._generate_analysis_report(all_states, all_ratios, significant_events, 
                                     state_durations, peak_values, dummy_df)
    
    def _calculate_bands_from_raw_muse(self, eeg_data, start_idx, end_idx):
        """Calculate band powers from raw EEG data for muse-player format"""
        try:
            # Extract EEG channels for this window
            channels = ['tp9', 'af7', 'af8', 'tp10']
            channel_powers = {}
            
            for ch in channels:
                if ch in eeg_data and start_idx < len(eeg_data[ch]):
                    ch_data = eeg_data[ch][start_idx:end_idx]
                    if ch_data and len(ch_data) > 50:  # Need sufficient data
                        # Calculate band powers for this channel
                        ch_powers = {}
                        for band, (low_freq, high_freq) in self.bands.items():
                            power = self.get_band_power(ch_data, low_freq, high_freq)
                            ch_powers[band] = power
                        channel_powers[ch] = ch_powers
            
            if not channel_powers:
                return {}
            
            # Average across channels
            avg_powers = {}
            for band in self.bands.keys():
                band_values = [ch_powers.get(band, 0) for ch_powers in channel_powers.values()]
                if band_values:
                    avg_powers[band] = np.mean(band_values)
                else:
                    avg_powers[band] = 0
            
            # Convert to percentages
            total_power = sum(avg_powers.values())
            if total_power > 0:
                return {band: (power / total_power) * 100 for band, power in avg_powers.items()}
            else:
                return {band: 0 for band in self.bands.keys()}
                
        except Exception as e:
            print(f"⚠️ Error calculating bands from raw data: {e}")
            return {}
    
    def _get_timestamp_column(self, df):
        """Get the appropriate timestamp column from DataFrame"""
        for col in ['timestamp_local', 'timestamp_utc', 'TimeStamp', 'timestamp']:
            if col in df.columns:
                return col
        return None
    
    def _generate_analysis_report(self, all_states, all_ratios, significant_events, 
                                state_durations, peak_values, original_df):
        """Generate comprehensive analysis report"""
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE ANALYSIS REPORT")
        print("=" * 70)
        
        # Overall statistics
        total_windows = len(all_states)
        if total_windows == 0:
            print("❌ No valid analysis windows found")
            return
        
        duration_minutes = (total_windows * self.update_interval) / 60
        print(f"⏱️  Analysis Duration: {duration_minutes:.1f} minutes ({total_windows} windows)")
        
        # State distribution
        print(f"\n🧠 MENTAL STATE DISTRIBUTION:")
        total_states = sum(state_durations.values())
        for state, count in sorted(state_durations.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_states) * 100
            print(f"   {state}: {percentage:.1f}% ({count} windows)")
        
        # Peak band powers
        print(f"\n⚡ PEAK BAND POWERS:")
        for band, peak in peak_values.items():
            print(f"   {band.capitalize()}: {peak:.1f}%")
        
        # Average band powers
        if all_ratios:
            print(f"\n📈 AVERAGE BAND POWERS:")
            avg_ratios = {}
            for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
                values = [ratios.get(band, 0) for ratios in all_ratios if ratios.get(band, 0) > 0]
                if values:
                    avg_ratios[band] = np.mean(values)
                    print(f"   {band.capitalize()}: {avg_ratios[band]:.1f}%")
        
        # Significant events
        if significant_events:
            print(f"\n🎯 SIGNIFICANT EVENTS ({len(significant_events)} total):")
            # Group by insight type
            insight_counts = {}
            for event in significant_events:
                insight = event['insight']
                if insight in insight_counts:
                    insight_counts[insight] += 1
                else:
                    insight_counts[insight] = 1
            
            for insight, count in sorted(insight_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   {insight}: {count} occurrences")
        
        # Data quality assessment
        print(f"\n📊 DATA QUALITY:")
        if 'touching_forehead' in original_df.columns:
            forehead_contact = original_df['touching_forehead'].dropna()
            if len(forehead_contact) > 0:
                avg_contact = forehead_contact.mean()
                print(f"   Average forehead contact: {avg_contact:.1f}")
        
        # Generate session summary
        print(f"\n📋 SESSION SUMMARY:")
        if state_durations:
            dominant_state = max(state_durations.items(), key=lambda x: x[1])
            print(f"   Dominant state: {dominant_state[0]} ({(dominant_state[1]/total_states*100):.1f}%)")
        
        if avg_ratios:
            dominant_band = max(avg_ratios.items(), key=lambda x: x[1])
            print(f"   Dominant frequency: {dominant_band[0]} ({dominant_band[1]:.1f}%)")
        
        print(f"   Total insights generated: {len(significant_events)}")
        
        # Copy summary to clipboard if available
        summary_text = self._generate_file_analysis_summary(duration_minutes, state_durations, 
                                                           peak_values, significant_events)
        
        if CLIPBOARD_AVAILABLE:
            try:
                pyperclip.copy(summary_text)
                print(f"\n📋 Analysis summary copied to clipboard!")
            except:
                pass
        
        print("=" * 70)
    
    def _generate_file_analysis_summary(self, duration_minutes, state_durations, 
                                      peak_values, significant_events):
        """Generate concise summary for clipboard"""
        total_states = sum(state_durations.values())
        
        # Top 3 states
        top_states = sorted(state_durations.items(), key=lambda x: x[1], reverse=True)[:3]
        states_str = " | ".join([f"{state}({count/total_states*100:.0f}%)" 
                               for state, count in top_states])
        
        # Peak bands
        top_bands = sorted(peak_values.items(), key=lambda x: x[1], reverse=True)[:3]
        bands_str = " | ".join([f"{band.capitalize()}({peak:.0f}%)" 
                              for band, peak in top_bands])
        
        summary = f"ENHANCED ANALYSIS: {duration_minutes:.1f}min\\n"
        summary += f"States: {states_str}\\n"
        summary += f"Peak Bands: {bands_str}\\n"
        summary += f"Insights: {len(significant_events)} events"
        
        return summary

def main():
    parser = argparse.ArgumentParser(description="Enhanced Consciousness Monitor v4 - Therapeutic Edition: EEG + fNIRS + Therapeutic Pattern Detection")
    parser.add_argument("--file", "-f", help="CSV file to monitor or analyze", default="mind_monitor_complete.csv")
    parser.add_argument("--window", "-w", type=float, default=0.75, help="Analysis window in seconds (default: 0.75)")
    parser.add_argument("--update", "-u", type=float, default=1.0, help="Update interval in seconds (default: 1.0)")
    parser.add_argument("--analyze", "-a", action="store_true", help="Analyze entire file instead of real-time monitoring")
    parser.add_argument("--no-bands", action="store_true", help="Hide EEG band power visualization")
    parser.add_argument("--no-insights", action="store_true", help="Hide psychological insights")
    parser.add_argument("--no-optics", action="store_true", help="Hide fNIRS optical data")
    parser.add_argument("--raw", action="store_true", help="Use raw signal processing instead of pre-computed bands")
    parser.add_argument("--force-output", action="store_true", help="Force output every update (disable smart event detection)")
    parser.add_argument("--output-interval", type=float, help="Force output every N seconds (overrides smart detection)")
    parser.add_argument("--debug", action="store_true", help="Show debug information about data updates and rule testing")
    parser.add_argument("--konrad-mode", action="store_true", help="Enable Konrad's personalized detection patterns (dB-based Security Guard detection)")
    parser.add_argument("--tune-rule", action="append", help="Tune rule parameters (e.g. --tune-rule jhana.alpha_min=85)")
    parser.add_argument("--load-rules", help="Load detection rules from JSON file")
    
    args = parser.parse_args()
    
    # Parse rule tuning arguments
    tune_rules = {}
    if args.tune_rule:
        for rule_tune in args.tune_rule:
            try:
                rule_path, value = rule_tune.split('=')
                parts = rule_path.split('.')
                if len(parts) == 2:
                    rule_name, param = parts
                    if rule_name not in tune_rules:
                        tune_rules[rule_name] = {}
                    tune_rules[rule_name][param] = float(value)
                    print(f"🔧 Rule tuning: {rule_name}.{param} = {value}")
            except ValueError:
                print(f"⚠️ Invalid rule tuning format: {rule_tune} (use rule.param=value)")
                continue
    
    monitor = EnhancedConsciousnessMonitor(
        csv_file=args.file,
        window_seconds=args.window,
        update_interval=args.update,
        show_bands=not args.no_bands,
        show_insights=not args.no_insights,
        show_optics=not args.no_optics,
        use_precomputed=not args.raw,
        force_output=args.force_output,
        output_interval=args.output_interval,
        debug=args.debug,
        konrad_mode=args.konrad_mode,
        tune_rules=tune_rules,
        load_rules=args.load_rules
    )
    
    if args.analyze:
        monitor.analyze_file()
    else:
        monitor.monitor_realtime()

if __name__ == "__main__":
    main()