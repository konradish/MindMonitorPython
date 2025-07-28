#!/usr/bin/env python3
"""
Test different approaches to match Mind Monitor's analysis
"""

import numpy as np
import pandas as pd
from scipy import signal

def test_mindmonitor_approaches():
    """Test different signal processing approaches that might match Mind Monitor"""
    
    print("🧠 Testing Mind Monitor-like approaches")
    print("=" * 50)
    
    # Load data and clean NaN values
    df = pd.read_csv("OSC-Python-Recording.csv")
    eeg_columns = ['RAW_TP9', 'RAW_AF7', 'RAW_AF8', 'RAW_TP10']
    clean_df = df[eeg_columns].dropna()
    window_data = clean_df.tail(512)
    raw_data = window_data.iloc[:, 0].values  # TP9 channel (first column in clean data)
    
    fs = 256
    bands = {
        'delta': (0.5, 4),
        'theta': (4, 8), 
        'alpha': (8, 13),
        'beta': (13, 30),
        'gamma': (30, 50)
    }
    
    print(f"Raw data range: {raw_data.min():.1f} to {raw_data.max():.1f}")
    
    approaches = [
        ("1. Raw signal (no preprocessing)", raw_data),
        ("2. DC removal only", raw_data - np.mean(raw_data)),
        ("3. High-pass 1Hz (remove slow drifts)", apply_highpass(raw_data, 1.0, fs)),
        ("4. High-pass 2Hz (aggressive drift removal)", apply_highpass(raw_data, 2.0, fs)),
        ("5. Bandpass 1-50Hz", apply_bandpass(raw_data, 1.0, 50.0, fs)),
        ("6. Detrend + high-pass 1Hz", apply_highpass(signal.detrend(raw_data - np.mean(raw_data)), 1.0, fs)),
        ("7. Shorter window (last 128 samples)", raw_data[-128:]),
        ("8. Mind Monitor style (aggressive filtering)", mindmonitor_preprocessing(raw_data, fs))
    ]
    
    for name, processed_data in approaches:
        print(f"\n{name}:")
        if len(processed_data) < 50:
            print("  Too few samples")
            continue
            
        # Calculate band powers
        powers = {}
        for band, (low, high) in bands.items():
            powers[band] = calculate_band_power(processed_data, low, high, fs)
        
        # Normalize to ratios
        total = sum(powers.values())
        if total == 0:
            print("  No signal")
            continue
            
        ratios = {band: power/total for band, power in powers.items()}
        
        # Show results
        alpha_ratio = ratios.get('alpha', 0)
        delta_ratio = ratios.get('delta', 0)
        
        for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
            ratio = ratios.get(band, 0)
            marker = " ⭐" if band == 'alpha' and ratio > 0.3 else ""
            marker = " 🔺" if band == 'delta' and ratio > 0.5 else marker
            print(f"    {band:6}: {ratio*100:5.1f}%{marker}")
        
        if alpha_ratio > delta_ratio:
            print("    ✅ Alpha dominant (matches Mind Monitor?)")
        elif delta_ratio > 0.6:
            print("    ⚠️  Delta dominant (may indicate drowsiness or artifact)")

def apply_highpass(data, cutoff, fs):
    """Apply high-pass filter"""
    if len(data) < 100:
        return data
    try:
        sos = signal.butter(4, cutoff, btype='high', fs=fs, output='sos')
        return signal.sosfilt(sos, data)
    except:
        return data

def apply_bandpass(data, low, high, fs):
    """Apply bandpass filter"""
    if len(data) < 100:
        return data
    try:
        sos = signal.butter(4, [low, high], btype='band', fs=fs, output='sos')
        return signal.sosfilt(sos, data)
    except:
        return data

def mindmonitor_preprocessing(data, fs):
    """Aggressive preprocessing that might match Mind Monitor"""
    # Remove DC and trends more aggressively
    processed = data - np.mean(data)
    processed = signal.detrend(processed)
    
    # Stronger high-pass to remove very slow components
    processed = apply_highpass(processed, 2.0, fs)
    
    # Notch filter for power line
    try:
        notch_sos = signal.iirnotch(60, 30, fs=fs, output='sos')
        processed = signal.sosfilt(notch_sos, processed)
    except:
        pass
    
    # Light low-pass to remove high freq noise
    processed = apply_lowpass(processed, 45, fs)
    
    return processed

def apply_lowpass(data, cutoff, fs):
    """Apply low-pass filter"""
    if len(data) < 100:
        return data
    try:
        sos = signal.butter(4, cutoff, btype='low', fs=fs, output='sos')
        return signal.sosfilt(sos, data)
    except:
        return data

def calculate_band_power(data, low_freq, high_freq, fs):
    """Calculate band power using Welch's method"""
    if len(data) < 50:
        return 0
    
    try:
        freqs, psd = signal.welch(data, fs=fs, nperseg=min(128, len(data)))
        freq_mask = (freqs >= low_freq) & (freqs <= high_freq)
        return np.sum(psd[freq_mask])
    except:
        return 0

if __name__ == "__main__":
    test_mindmonitor_approaches()