#!/usr/bin/env python3
"""
Debug script to identify the signal processing issue
"""

import numpy as np
import pandas as pd
from scipy import signal
import os
from consciousness_monitor import ConsciousnessMonitor

def debug_signal_processing():
    """Debug the signal processing step by step"""
    
    # Create monitor
    monitor = ConsciousnessMonitor(
        csv_file="OSC-Python-Recording.csv",
        window_seconds=2,
        update_interval=1.0
    )
    
    print("🔍 Debugging EEG Signal Processing")
    print("=" * 50)
    
    # Check if CSV exists and has data
    if not os.path.exists("OSC-Python-Recording.csv"):
        print("❌ No CSV file found")
        return
        
    df = pd.read_csv("OSC-Python-Recording.csv")
    print(f"📊 CSV has {len(df)} rows")
    
    # Clean data - remove marker rows and NaN values in EEG channels
    eeg_columns = ['RAW_TP9', 'RAW_AF7', 'RAW_AF8', 'RAW_TP10']
    clean_df = df[eeg_columns].dropna()
    print(f"📊 Clean EEG rows: {len(clean_df)}")
    
    if len(clean_df) < 512:
        print("❌ Not enough clean data for analysis")
        return
    
    # Get recent data for analysis
    window_data = clean_df.tail(512)
    print(f"📈 Analyzing last 512 samples")
    
    # Check raw data ranges
    print("\n🔢 Raw Data Ranges:")
    for i, channel in enumerate(['TP9', 'AF7', 'AF8', 'TP10']):
        channel_data = window_data.iloc[:, i].values
        print(f"  {channel}: {channel_data.min():.1f} to {channel_data.max():.1f} (mean: {channel_data.mean():.1f})")
    
    # Test preprocessing on first channel
    print("\n🧪 Testing Preprocessing (TP9 channel):")
    raw_data = window_data.iloc[:, 0].values  # TP9 (first column in clean_df)
    print(f"  Before: range {raw_data.min():.1f} to {raw_data.max():.1f}, mean {raw_data.mean():.1f}")
    
    processed = monitor.preprocess_signal(raw_data)
    print(f"  After:  range {processed.min():.1f} to {processed.max():.1f}, mean {processed.mean():.3f}")
    
    # Test band power calculation step by step
    print("\n🌊 Band Power Analysis (TP9 channel):")
    for band_name, (low, high) in monitor.bands.items():
        power = monitor.get_band_power(raw_data, low, high)
        print(f"  {band_name:6} ({low:4.1f}-{high:2.0f} Hz): {power:.6f}")
    
    # Test full consciousness analysis
    print("\n🧠 Full Consciousness Analysis:")
    analysis = monitor.analyze_consciousness_state(window_data)
    
    if analysis is None:
        print("❌ Analysis returned None!")
        return
    
    print(f"  State: {analysis['state']}")
    print(f"  Confidence: {analysis['confidence']}")
    print("  Band Ratios:")
    
    total_ratio = 0
    for band, ratio in analysis['ratios'].items():
        print(f"    {band:6}: {ratio:.3f} ({ratio*100:5.1f}%)")
        total_ratio += ratio
    
    print(f"  Total: {total_ratio:.3f}")
    
    # Identify the problem
    print("\n🕵️ Problem Analysis:")
    if total_ratio < 0.9 or total_ratio > 1.1:
        print(f"  ⚠️  Band ratios don't sum to 1.0 (got {total_ratio:.3f})")
    
    problem_bands = [band for band, ratio in analysis['ratios'].items() if ratio > 0.9]
    if problem_bands:
        print(f"  ⚠️  {problem_bands[0]} dominates with {analysis['ratios'][problem_bands[0]]*100:.1f}%")
        print("     This suggests a signal processing error")
    
    zero_bands = [band for band, ratio in analysis['ratios'].items() if ratio < 0.01]
    if len(zero_bands) > 2:
        print(f"  ⚠️  Too many bands near zero: {zero_bands}")
    
    # Check for common issues
    if np.any(processed < -1000):
        print("  ⚠️  Preprocessed signal has very negative values - conversion issue?")
    
    if np.all(np.abs(processed) < 10):
        print("  ⚠️  Preprocessed signal amplitude too small - normalization issue?")
        
    print("\n✅ Debug complete!")

if __name__ == "__main__":
    debug_signal_processing()