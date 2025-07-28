#!/usr/bin/env python3
"""
Exact Mind Monitor replication - test multiple approaches to match the app exactly
"""

import numpy as np
import pandas as pd
from scipy import signal
import time
import os

def wait_for_data_and_analyze():
    """Wait for fresh CSV data and run comprehensive analysis"""
    
    print("🔍 Mind Monitor Exact Match Analysis")
    print("=" * 50)
    print("Waiting for fresh CSV data...")
    print("Start your Mind Monitor recording and I'll analyze it!")
    
    last_size = 0
    
    while True:
        if not os.path.exists("OSC-Python-Recording.csv"):
            time.sleep(1)
            continue
        
        current_size = os.path.getsize("OSC-Python-Recording.csv")
        
        if current_size > last_size and current_size > 1000:  # At least 1KB of data
            try:
                df = pd.read_csv("OSC-Python-Recording.csv")
                
                # Clean data
                eeg_columns = ['RAW_TP9', 'RAW_AF7', 'RAW_AF8', 'RAW_TP10']
                clean_df = df[eeg_columns].dropna()
                
                if len(clean_df) >= 256:  # Need at least 1 second of data
                    print(f"\n📊 Analyzing {len(clean_df)} samples...")
                    analyze_all_approaches(clean_df)
                    
            except Exception as e:
                print(f"Error reading CSV: {e}")
        
        last_size = current_size
        time.sleep(2)  # Check every 2 seconds

def analyze_all_approaches(clean_df):
    """Test all possible approaches to match Mind Monitor"""
    
    # Test different window sizes
    window_sizes = [64, 128, 256, 512]  # 0.25s, 0.5s, 1s, 2s
    
    print("\n🧪 Testing Different Approaches:")
    print("-" * 50)
    
    for window_size in window_sizes:
        if len(clean_df) < window_size:
            continue
            
        window_data = clean_df.tail(window_size)
        raw_tp9 = window_data.iloc[:, 0].values  # TP9 channel
        
        print(f"\n📏 Window: {window_size} samples ({window_size/256:.2f}s)")
        
        approaches = [
            ("Raw (no processing)", raw_tp9),
            ("DC removal only", dc_removal(raw_tp9)),
            ("DC + light detrend", dc_and_detrend(raw_tp9)),
            ("Moving average (5)", moving_average_filter(raw_tp9, 5)),
            ("Moving average (10)", moving_average_filter(raw_tp9, 10)),
            ("Median filter", median_filter(raw_tp9)),
            ("High-pass 0.1Hz", highpass_filter(raw_tp9, 0.1)),
            ("High-pass 0.5Hz", highpass_filter(raw_tp9, 0.5)),
            ("Bandpass 0.5-40Hz", bandpass_filter(raw_tp9, 0.5, 40)),
            ("Mind Monitor style", mindmonitor_style(raw_tp9))
        ]
        
        best_alpha = 0
        best_approach = ""
        
        for name, processed in approaches:
            if processed is None or len(processed) == 0:
                continue
                
            ratios = calculate_band_ratios(processed, window_size)
            if ratios is None:
                continue
                
            alpha_pct = ratios.get('alpha', 0) * 100
            delta_pct = ratios.get('delta', 0) * 100
            
            # Track best alpha performance
            if alpha_pct > best_alpha:
                best_alpha = alpha_pct
                best_approach = name
            
            # Show results with indicators
            alpha_marker = " 🥇" if alpha_pct > delta_pct and alpha_pct > 25 else ""
            delta_marker = " ⚠️" if delta_pct > 50 else ""
            
            print(f"  {name:18}: α{alpha_pct:5.1f}% δ{delta_pct:5.1f}%{alpha_marker}{delta_marker}")
        
        print(f"  🏆 Best: {best_approach} (α{best_alpha:.1f}%)")
        
        # If we found a good alpha-dominant approach, show details
        if best_alpha > 30:
            print("  ✅ Found alpha-dominant approach! Details:")
            for name, processed in approaches:
                if name == best_approach:
                    ratios = calculate_band_ratios(processed, window_size)
                    if ratios:
                        for band, ratio in ratios.items():
                            print(f"    {band:6}: {ratio*100:5.1f}%")

def dc_removal(data):
    """Simple DC removal"""
    return data - np.mean(data)

def dc_and_detrend(data):
    """DC removal plus detrending"""
    dc_removed = data - np.mean(data)
    return signal.detrend(dc_removed)

def moving_average_filter(data, window):
    """Moving average smoothing"""
    if len(data) < window:
        return data
    smoothed = np.convolve(data, np.ones(window)/window, mode='same')
    return data - smoothed  # Remove the slow component

def median_filter(data):
    """Median filtering for artifact removal"""
    if len(data) < 5:
        return data
    try:
        filtered = signal.medfilt(data, kernel_size=5)
        return data - filtered + np.mean(filtered)  # Remove slow component
    except:
        return data

def highpass_filter(data, cutoff):
    """High-pass filter"""
    if len(data) < 100:
        return data
    try:
        sos = signal.butter(2, cutoff, btype='high', fs=256, output='sos')
        return signal.sosfilt(sos, data)
    except:
        return data

def bandpass_filter(data, low, high):
    """Bandpass filter"""
    if len(data) < 100:
        return data
    try:
        sos = signal.butter(2, [low, high], btype='band', fs=256, output='sos')
        return signal.sosfilt(sos, data)
    except:
        return data

def mindmonitor_style(data):
    """Hypothetical Mind Monitor preprocessing"""
    # Very light processing to preserve natural rhythms
    processed = data - np.mean(data)  # DC removal
    
    # Light artifact removal without killing alpha
    if len(processed) > 50:
        # Remove very slow drifts only (< 0.1 Hz)
        processed = highpass_filter(processed, 0.1)
    
    return processed

def calculate_band_ratios(data, window_size):
    """Calculate frequency band ratios"""
    if len(data) < 32:  # Need minimum samples
        return None
    
    try:
        # Use appropriate parameters for window size
        nperseg = min(window_size // 2, 128)
        if nperseg < 8:
            nperseg = len(data) // 4
        
        freqs, psd = signal.welch(data, fs=256, nperseg=nperseg)
        
        bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 50)
        }
        
        powers = {}
        for band, (low, high) in bands.items():
            mask = (freqs >= low) & (freqs <= high)
            powers[band] = np.sum(psd[mask])
        
        total = sum(powers.values())
        if total == 0:
            return None
            
        return {band: power/total for band, power in powers.items()}
        
    except Exception as e:
        return None

if __name__ == "__main__":
    wait_for_data_and_analyze()