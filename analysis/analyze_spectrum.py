#!/usr/bin/env python3
"""
Analyze the frequency spectrum to understand why delta dominates
"""

import numpy as np
import pandas as pd
from scipy import signal
# import matplotlib.pyplot as plt  # Not needed for text output
from consciousness_monitor import ConsciousnessMonitor

def analyze_frequency_spectrum():
    """Analyze the frequency spectrum of the EEG data"""
    
    print("🔍 Analyzing Frequency Spectrum")
    print("=" * 40)
    
    # Load data
    df = pd.read_csv("OSC-Python-Recording.csv")
    window_data = df.tail(512)
    raw_data = window_data.iloc[:, 1].values  # TP9 channel
    
    print(f"Raw data: {len(raw_data)} samples")
    print(f"Range: {raw_data.min():.1f} to {raw_data.max():.1f}")
    print(f"Mean: {raw_data.mean():.1f}, Std: {raw_data.std():.1f}")
    
    # Create monitor for preprocessing
    monitor = ConsciousnessMonitor()
    
    # Test different preprocessing approaches
    print("\n1️⃣ Raw signal spectrum:")
    plot_spectrum(raw_data, "Raw Signal")
    
    print("\n2️⃣ After DC removal only:")
    dc_removed = raw_data - np.mean(raw_data)
    plot_spectrum(dc_removed, "DC Removed")
    
    print("\n3️⃣ After full preprocessing:")
    processed = monitor.preprocess_signal(raw_data)
    plot_spectrum(processed, "Fully Processed")
    
    print("\n4️⃣ Band powers with different approaches:")
    
    # Raw signal band powers
    raw_powers = {}
    for band, (low, high) in monitor.bands.items():
        power = calculate_band_power_simple(raw_data, low, high, 256)
        raw_powers[band] = power
    
    print("Raw signal:")
    total = sum(raw_powers.values())
    for band, power in raw_powers.items():
        ratio = power/total if total > 0 else 0
        print(f"  {band:6}: {power:10.1f} ({ratio*100:5.1f}%)")
    
    # DC removed signal band powers  
    dc_powers = {}
    for band, (low, high) in monitor.bands.items():
        power = calculate_band_power_simple(dc_removed, low, high, 256)
        dc_powers[band] = power
    
    print("DC removed:")
    total = sum(dc_powers.values())
    for band, power in dc_powers.items():
        ratio = power/total if total > 0 else 0
        print(f"  {band:6}: {power:10.1f} ({ratio*100:5.1f}%)")
    
    # Processed signal band powers
    proc_powers = {}
    for band, (low, high) in monitor.bands.items():
        power = calculate_band_power_simple(processed, low, high, 256)
        proc_powers[band] = power
    
    print("Fully processed:")
    total = sum(proc_powers.values())
    for band, power in proc_powers.items():
        ratio = power/total if total > 0 else 0
        print(f"  {band:6}: {power:10.1f} ({ratio*100:5.1f}%)")

def plot_spectrum(data, title):
    """Plot frequency spectrum of data"""
    fs = 256
    freqs, psd = signal.welch(data, fs=fs, nperseg=min(256, len(data)))
    
    # Find peak frequency
    peak_idx = np.argmax(psd)
    peak_freq = freqs[peak_idx]
    
    print(f"  {title}: Peak at {peak_freq:.1f} Hz")
    
    # Show power in each band
    bands = {
        'delta': (0.5, 4),
        'theta': (4, 8), 
        'alpha': (8, 13),
        'beta': (13, 30),
        'gamma': (30, 50)
    }
    
    for band, (low, high) in bands.items():
        mask = (freqs >= low) & (freqs <= high)
        band_power = np.sum(psd[mask])
        print(f"    {band:6}: {band_power:8.1f}")

def calculate_band_power_simple(data, low_freq, high_freq, fs):
    """Simple band power calculation without preprocessing"""
    if len(data) < 100:
        return 0
    
    freqs, psd = signal.welch(data, fs=fs, nperseg=min(256, len(data)))
    freq_mask = (freqs >= low_freq) & (freqs <= high_freq)
    return np.sum(psd[freq_mask])

if __name__ == "__main__":
    analyze_frequency_spectrum()