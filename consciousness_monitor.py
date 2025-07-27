# /// script
# dependencies = ["numpy", "scipy", "pandas"]
# ///

import numpy as np
import pandas as pd
from scipy import signal
import time
import os
import argparse
from datetime import datetime

class ConsciousnessMonitor:
    def __init__(self, csv_file="OSC-Python-Recording.csv", window_seconds=0.75, 
                 update_interval=1.0, channels=['TP9', 'AF7', 'AF8', 'TP10'],
                 show_bands=True, show_insights=True):
        
        self.csv_file = csv_file
        self.window_seconds = window_seconds
        self.update_interval = update_interval
        self.channels = channels
        self.show_bands = show_bands
        self.show_insights = show_insights
        self.sample_rate = 256
        self.window_samples = int(window_seconds * self.sample_rate)  # Ensure integer
        
        # EEG frequency bands (clinical standards)
        self.bands = {
            'delta': (0.5, 4),    # Not 0-4, starts at 0.5
            'theta': (4, 8),      
            'alpha': (8, 13),     # Wider alpha band
            'beta': (13, 30),     
            'gamma': (30, 50)     # Clinical gamma, not 30-100
        }
        
        # Design filters once during initialization
        self.highpass_filter = signal.butter(4, 0.5, btype='high', fs=self.sample_rate)
        self.lowpass_filter = signal.butter(4, 50, btype='low', fs=self.sample_rate)
        self.notch_filter = signal.iirnotch(60, 30, fs=self.sample_rate)  # 60Hz notch
        
        self.last_file_size = 0
        print(f"🧠 Consciousness Monitor v2 Ready! (With Real Signal Processing)")
        print(f"Window: {window_seconds}s | Update: {update_interval}s | Channels: {len(channels)}")
        print("=" * 60)
    
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
        
        # Sum power in the frequency band
        band_power = np.sum(psd[freq_mask])
        
        return band_power
    
    def analyze_consciousness_state(self, eeg_data):
        """Analyze current mental state from EEG data"""
        if len(eeg_data) < 50:
            return None
            
        # Clean data - remove NaN values from EEG channels only
        if 'TimeStamp' in eeg_data.columns:
            # Full CSV with timestamp - skip timestamp column
            eeg_columns = ['RAW_TP9', 'RAW_AF7', 'RAW_AF8', 'RAW_TP10']
            clean_eeg = eeg_data[eeg_columns].dropna()
            if len(clean_eeg) < 50:
                return None
            eeg_data = clean_eeg
            timestamp_offset = 0  # No timestamp column after cleaning
        else:
            # Already cleaned data or data without timestamp
            timestamp_offset = 1 if len(eeg_data.columns) > 4 else 0
            
        # Calculate band powers for each channel
        results = {}
        
        for i, channel in enumerate(self.channels):
            if i+timestamp_offset >= len(eeg_data.columns):  # Skip if channel doesn't exist
                continue
                
            channel_data = eeg_data.iloc[:, i+timestamp_offset].values
            
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
        
        if not results:
            return None
            
        # Calculate average across available channels
        avg_powers = {}
        for band in self.bands.keys():
            powers = [results[ch][band] for ch in results.keys() if band in results[ch]]
            avg_powers[band] = np.mean(powers) if powers else 0
        
        return self.interpret_mental_state(avg_powers)
    
    def interpret_mental_state(self, powers):
        """Convert band powers to psychological insights"""
        # Handle invalid values
        valid_powers = {band: power for band, power in powers.items() 
                       if power > 0 and not np.isnan(power) and not np.isinf(power)}
        
        if not valid_powers:
            return {"state": "No signal", "confidence": "LOW", "insights": [], "ratios": {band: 0 for band in self.bands.keys()}}
        
        # Powers are already linear values from get_band_power(), just normalize
        total_power = sum(valid_powers.values())
        
        if total_power == 0:
            return {"state": "No signal", "confidence": "LOW", "insights": [], "ratios": {band: 0 for band in self.bands.keys()}}
            
        ratios = {band: power/total_power for band, power in valid_powers.items()}
        
        # Fill in missing bands with 0
        for band in self.bands.keys():
            if band not in ratios:
                ratios[band] = 0
        
        # Psychological interpretation with refined thresholds
        state_indicators = []
        confidence = "MODERATE"
        
        # State detection thresholds (adjusted for proper signal processing)
        if ratios['alpha'] > 0.25:
            state_indicators.append("RELAXED")
            confidence = "HIGH"
        
        if ratios['beta'] > 0.30:
            if ratios['alpha'] > 0.20:
                state_indicators.append("FOCUSED")
            else:
                state_indicators.append("ALERT/TENSE")
                confidence = "HIGH"
        
        if ratios['theta'] > 0.20:
            if ratios['alpha'] > 0.15:
                state_indicators.append("CREATIVE/FLOW")
            else:
                state_indicators.append("MEDITATIVE")
            confidence = "HIGH"
        
        if ratios['delta'] > 0.35:
            state_indicators.append("DROWSY")
            confidence = "HIGH"
        
        if ratios['gamma'] > 0.12:
            state_indicators.append("PEAK FOCUS")
            confidence = "HIGH"
        
        if not state_indicators:
            state_indicators = ["NEUTRAL"]
        
        state = " + ".join(state_indicators)
        
        # Generate insights (updated thresholds)
        insights = []
        if ratios['beta'] > ratios['alpha'] * 2:
            insights.append("🚨 Security guard might be active")
        if ratios['theta'] > 0.15 and ratios['alpha'] > 0.15:
            insights.append("🌊 Good emotional terrain navigation")
        if ratios['alpha'] > 0.35:
            insights.append("😌 Excellent regulation state")
        if ratios['gamma'] > 0.20:
            insights.append("⚡ Intense cognitive processing")
        if ratios['delta'] > 0.45:
            insights.append("😴 Very relaxed/tired state")
        if ratios['theta'] > 0.30:
            insights.append("🎨 Creative/flow state active")
            
        return {
            'state': state,
            'confidence': confidence,
            'insights': insights,
            'ratios': ratios
        }
    
    def display_analysis(self, analysis):
        """Display consciousness analysis results"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n[{timestamp}] 🧠 CONSCIOUSNESS STATE:")
        print(f"  State: {analysis['state']} ({analysis['confidence']} confidence)")
        
        # Show band ratios if enabled
        if self.show_bands:
            print("  Brain Waves:")
            for band, ratio in analysis['ratios'].items():
                bar_length = int(ratio * 20)
                bar = "█" * bar_length + "░" * (20 - bar_length)
                print(f"    {band.upper():6}: {bar} {ratio:.2%}")
        
        # Show insights if enabled
        if self.show_insights and analysis['insights']:
            print("  Insights:")
            for insight in analysis['insights']:
                print(f"    {insight}")
        
        print("-" * 60)
    
    def analyze_session_file(self, filename):
        """Analyze an entire CSV file and show summary"""
        try:
            df = pd.read_csv(filename)
            print(f"\n📊 Analyzing session file: {filename}")
            print(f"Total samples: {len(df)} ({len(df)/self.sample_rate:.1f} seconds)")
            
            # Analyze in chunks
            chunk_size = int(self.window_samples)  # Ensure integer
            states = []
            
            for i in range(0, len(df) - chunk_size, chunk_size // 2):  # 50% overlap
                chunk = df.iloc[i:i+chunk_size]
                analysis = self.analyze_consciousness_state(chunk)
                if analysis:
                    states.append(analysis)
                    
            if not states:
                print("No valid data found in file")
                return
                
            # Summary statistics
            all_states = [s['state'] for s in states]
            unique_states = list(set(all_states))
            
            print(f"\nSession Summary:")
            print(f"  States detected: {len(unique_states)}")
            for state in unique_states:
                count = all_states.count(state)
                percent = (count / len(all_states)) * 100
                print(f"    {state}: {count} windows ({percent:.1f}%)")
                
            # Average band powers
            avg_ratios = {}
            for band in self.bands.keys():
                ratios = [s['ratios'][band] for s in states if band in s['ratios']]
                avg_ratios[band] = np.mean(ratios) if ratios else 0
                
            print(f"\nAverage Brain Wave Distribution:")
            for band, ratio in avg_ratios.items():
                bar_length = int(ratio * 20)
                bar = "█" * bar_length + "░" * (20 - bar_length)
                print(f"  {band.upper():6}: {bar} {ratio:.2%}")
                
        except Exception as e:
            print(f"Error analyzing file: {e}")
    
    def monitor_realtime(self):
        """Monitor real-time consciousness from CSV file"""
        print("Waiting for EEG data to start flowing...")
        
        while True:
            try:
                if not os.path.exists(self.csv_file):
                    time.sleep(1)
                    continue
                
                current_size = os.path.getsize(self.csv_file)
                if current_size <= self.last_file_size:
                    time.sleep(self.update_interval)
                    continue
                
                df = pd.read_csv(self.csv_file)
                
                if len(df) < self.window_samples:
                    time.sleep(1)
                    continue
                
                recent_data = df.tail(self.window_samples)
                analysis = self.analyze_consciousness_state(recent_data)
                
                if analysis:
                    self.display_analysis(analysis)
                
                self.last_file_size = current_size
                time.sleep(self.update_interval)
                
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description="Consciousness Monitor v2 - Real Signal Processing Edition")
    parser.add_argument("--file", "-f", help="CSV file to monitor or analyze")
    parser.add_argument("--window", "-w", type=float, default=0.75, help="Analysis window in seconds (default: 0.75)")
    parser.add_argument("--update", "-u", type=float, default=1.0, help="Update interval in seconds (default: 1.0)")
    parser.add_argument("--analyze", "-a", action="store_true", help="Analyze entire file instead of real-time monitoring")
    parser.add_argument("--no-bands", action="store_true", help="Hide band power visualization")
    parser.add_argument("--no-insights", action="store_true", help="Hide insights")
    parser.add_argument("--channels", nargs="+", default=['TP9', 'AF7', 'AF8', 'TP10'], help="Channel names")
    
    args = parser.parse_args()
    
    csv_file = args.file or "OSC-Python-Recording.csv"
    
    monitor = ConsciousnessMonitor(
        csv_file=csv_file,
        window_seconds=args.window,
        update_interval=args.update,
        channels=args.channels,
        show_bands=not args.no_bands,
        show_insights=not args.no_insights
    )
    
    if args.analyze:
        monitor.analyze_session_file(csv_file)
    else:
        print("🚀 Starting real-time consciousness monitoring...")
        print("Press Ctrl+C to stop\n")
        
        try:
            monitor.monitor_realtime()
        except KeyboardInterrupt:
            print("\n🛑 Consciousness monitoring stopped")

if __name__ == "__main__":
    main()