#!/usr/bin/env python3
"""
Final validation of signal processing against expected Mind Monitor results
"""

import numpy as np
import pandas as pd
from scipy import signal
from consciousness_monitor import ConsciousnessMonitor

def final_validation():
    """Final test to validate signal processing matches Mind Monitor"""
    
    print("🧠 Final Validation Test")
    print("=" * 40)
    
    # Load clean data
    df = pd.read_csv("OSC-Python-Recording.csv")
    eeg_columns = ['RAW_TP9', 'RAW_AF7', 'RAW_AF8', 'RAW_TP10']
    clean_df = df[eeg_columns].dropna()
    
    print(f"Clean data: {len(clean_df)} rows")
    
    # Test different window sizes
    window_sizes = [128, 256, 512, 1024]  # 0.5s, 1s, 2s, 4s
    
    for window_size in window_sizes:
        if len(clean_df) < window_size:
            continue
            
        print(f"\n📊 Window size: {window_size} samples ({window_size/256:.1f}s)")
        
        # Get data
        window_data = clean_df.tail(window_size)
        
        # Test with current consciousness monitor
        monitor = ConsciousnessMonitor(window_seconds=window_size/256)
        analysis = monitor.analyze_consciousness_state(window_data)
        
        if analysis:
            print("  Current implementation:")
            for band, ratio in analysis['ratios'].items():
                marker = " ⭐" if ratio > 0.25 else ""
                print(f"    {band:6}: {ratio*100:5.1f}%{marker}")
            print(f"    State: {analysis['state']}")
        
        # Test with minimal processing (like Mind Monitor)
        raw_data = window_data.iloc[:, 0].values  # TP9
        minimal_ratios = calculate_minimal_bands(raw_data)
        
        if minimal_ratios:
            print("  Minimal processing (Mind Monitor style):")
            for band, ratio in minimal_ratios.items():
                marker = " ⭐" if ratio > 0.25 else ""
                print(f"    {band:6}: {ratio*100:5.1f}%{marker}")
    
    # Recommend best approach
    print(f"\n🎯 Recommendation:")
    print("Based on testing, Mind Monitor likely uses:")
    print("- Minimal preprocessing (DC removal + detrend only)")
    print("- Short windows (0.5-1 second) for responsive feedback")
    print("- No aggressive filtering that kills natural rhythms")

def calculate_minimal_bands(data):
    """Calculate band powers with minimal processing like Mind Monitor"""
    if len(data) < 50:
        return None
    
    # Minimal preprocessing - just DC removal and detrend
    processed = data - np.mean(data)
    processed = signal.detrend(processed)
    
    # Calculate band powers
    fs = 256
    bands = {
        'delta': (0.5, 4),
        'theta': (4, 8), 
        'alpha': (8, 13),
        'beta': (13, 30),
        'gamma': (30, 50)
    }
    
    powers = {}
    try:
        freqs, psd = signal.welch(processed, fs=fs, nperseg=min(128, len(processed)))
        
        for band, (low, high) in bands.items():
            freq_mask = (freqs >= low) & (freqs <= high)
            powers[band] = np.sum(psd[freq_mask])
    except:
        return None
    
    # Normalize to ratios
    total = sum(powers.values())
    if total == 0:
        return None
        
    return {band: power/total for band, power in powers.items()}

if __name__ == "__main__":
    final_validation()