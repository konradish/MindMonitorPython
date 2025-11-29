# /// script
# dependencies = ["numpy", "scipy", "pandas"]
# ///

import numpy as np
import pandas as pd
from scipy import signal
import time
import os
from datetime import datetime, timedelta

class ConsciousnessAnalyzer:
    def __init__(self, csv_file="OSC-Python-Recording.csv", window_seconds=2):
        self.csv_file = csv_file
        self.window_seconds = window_seconds
        self.sample_rate = 256  # Hz
        self.window_samples = window_seconds * self.sample_rate
        
        # EEG frequency bands
        self.bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 50)
        }
        
        self.last_file_size = 0
        print("🧠 Consciousness Analyzer Ready!")
        print(f"Analyzing {window_seconds}s windows of EEG data...")
        print("=" * 50)
    
    def get_band_power(self, data, low_freq, high_freq):
        """Calculate power in specific frequency band using FFT"""
        if len(data) < 100:
            return 0
            
        # Remove DC offset and trends
        data = data - np.mean(data)
        
        # Apply window to reduce spectral leakage
        windowed = data * np.hanning(len(data))
        
        # Calculate power spectral density using FFT
        freqs, psd = signal.welch(windowed, fs=self.sample_rate, nperseg=256)
        
        # Find frequency indices for the band
        freq_mask = (freqs >= low_freq) & (freqs <= high_freq)
        
        # Sum power in the frequency band
        band_power = np.sum(psd[freq_mask])
        
        return band_power
    
    def analyze_consciousness_state(self, eeg_data):
        """Analyze current mental state from EEG data"""
        if len(eeg_data) < 100:  # Need minimum samples
            return None
            
        # Calculate band powers for each channel
        channels = ['TP9', 'AF7', 'AF8', 'TP10']
        results = {}
        
        for i, channel in enumerate(channels):
            channel_data = eeg_data.iloc[:, i+1].values  # Skip timestamp
            
            band_powers = {}
            for band_name, (low, high) in self.bands.items():
                power = self.get_band_power(channel_data, low, high)
                band_powers[band_name] = power
            
            results[channel] = band_powers
        
        # Calculate average across channels
        avg_powers = {}
        for band in self.bands.keys():
            avg_powers[band] = np.mean([results[ch][band] for ch in channels])
        
        return self.interpret_mental_state(avg_powers)
    
    def interpret_mental_state(self, powers):
        """Convert band powers to psychological insights"""
        # Normalize powers (simple approach)
        total_power = sum(powers.values())
        if total_power == 0:
            return "No signal detected"
            
        ratios = {band: power/total_power for band, power in powers.items()}
        
        # Psychological interpretation
        state_indicators = []
        confidence = "MODERATE"
        
        # High alpha = relaxed, calm
        if ratios['alpha'] > 0.3:
            state_indicators.append("RELAXED")
            confidence = "HIGH"
        
        # High beta = focused or anxious
        if ratios['beta'] > 0.35:
            if ratios['alpha'] > 0.25:
                state_indicators.append("FOCUSED")
            else:
                state_indicators.append("ALERT/TENSE")
                confidence = "HIGH"
        
        # High theta = creative, meditative
        if ratios['theta'] > 0.25:
            state_indicators.append("CREATIVE/FLOW")
            confidence = "HIGH"
        
        # High delta = drowsy
        if ratios['delta'] > 0.4:
            state_indicators.append("DROWSY")
            confidence = "HIGH"
        
        # High gamma = peak focus
        if ratios['gamma'] > 0.15:
            state_indicators.append("PEAK FOCUS")
            confidence = "HIGH"
        
        if not state_indicators:
            state_indicators = ["NEUTRAL"]
        
        # Create readable summary
        state = " + ".join(state_indicators)
        
        # Add specific insights
        insights = []
        if ratios['beta'] > ratios['alpha'] * 1.5:
            insights.append("🚨 Security guard might be active")
        if ratios['theta'] > 0.2 and ratios['alpha'] > 0.2:
            insights.append("🌊 Good emotional terrain navigation")
        if ratios['alpha'] > 0.4:
            insights.append("😌 Excellent regulation state")
        
        return {
            'state': state,
            'confidence': confidence,
            'insights': insights,
            'ratios': ratios
        }
    
    def monitor_consciousness(self):
        """Main monitoring loop"""
        print("Waiting for EEG data to start flowing...")
        
        while True:
            try:
                # Check if file exists and has new data
                if not os.path.exists(self.csv_file):
                    time.sleep(1)
                    continue
                
                current_size = os.path.getsize(self.csv_file)
                if current_size <= self.last_file_size:
                    time.sleep(0.5)
                    continue
                
                # Read latest data 
                df = pd.read_csv(self.csv_file)
                
                if len(df) < self.window_samples:
                    time.sleep(1)
                    continue
                
                # Analyze last N seconds of data
                recent_data = df.tail(self.window_samples)
                analysis = self.analyze_consciousness_state(recent_data)
                
                if analysis:
                    self.display_analysis(analysis)
                
                self.last_file_size = current_size
                time.sleep(1)  # Update every second
                
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)
    
    def display_analysis(self, analysis):
        """Display consciousness analysis results"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n[{timestamp}] 🧠 CONSCIOUSNESS STATE:")
        print(f"  State: {analysis['state']} ({analysis['confidence']} confidence)")
        
        # Show band ratios
        print("  Brain Waves:")
        for band, ratio in analysis['ratios'].items():
            bar_length = int(ratio * 20)  # Scale to 20 chars
            bar = "█" * bar_length + "░" * (20 - bar_length)
            print(f"    {band.upper():6}: {bar} {ratio:.2%}")
        
        # Show insights
        if analysis['insights']:
            print("  Insights:")
            for insight in analysis['insights']:
                print(f"    {insight}")
        
        print("-" * 50)

if __name__ == "__main__":
    analyzer = ConsciousnessAnalyzer()
    
    print("🚀 Starting real-time consciousness monitoring...")
    print("Start your Mind Monitor recording and watch your mental states!")
    print("Press Ctrl+C to stop\n")
    
    try:
        analyzer.monitor_consciousness()
    except KeyboardInterrupt:
        print("\n🛑 Consciousness monitoring stopped")
        print("Thanks for pioneering human-AI consciousness collaboration! 🤖🧠⚡")