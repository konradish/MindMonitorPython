#!/usr/bin/env python3
"""
Sample Rate Analysis for meditation.csv

Analyzes the actual sampling pattern to understand the data structure.
"""

import pandas as pd
import numpy as np

def analyze_sample_rate_pattern(csv_file="meditation.csv", max_samples=5000):
    """Analyze the actual sampling pattern in meditation.csv"""
    
    print(f"📊 Analyzing sample rate pattern in {csv_file}")
    print("=" * 60)
    
    # Load EEG data
    rows = []
    eeg_count = 0
    
    with open(csv_file, 'r') as f:
        for line in f:
            parts = line.strip().split(', ')
            if len(parts) >= 2 and parts[1] == '/muse/eeg':
                timestamp = float(parts[0])
                rows.append([timestamp] + parts[1:])
                eeg_count += 1
                if eeg_count >= max_samples:
                    break
    
    print(f"📊 Loaded {len(rows)} EEG samples")
    
    if len(rows) < 100:
        print("❌ Not enough EEG data")
        return
    
    # Extract timestamps
    timestamps = [row[0] for row in rows]
    timestamps = np.array(timestamps)
    
    # Basic timestamp analysis
    duration = timestamps[-1] - timestamps[0]
    print(f"📊 Time span: {duration:.3f} seconds")
    print(f"📊 Average rate: {len(timestamps) / duration:.1f} Hz")
    
    # Analyze timestamp differences
    diffs = np.diff(timestamps)
    print(f"\n⏱️ Timestamp Differences:")
    print(f"  Mean: {np.mean(diffs)*1000:.2f} ms")
    print(f"  Std:  {np.std(diffs)*1000:.2f} ms")
    print(f"  Min:  {np.min(diffs)*1000:.2f} ms")
    print(f"  Max:  {np.max(diffs)*1000:.2f} ms")
    
    # Find unique intervals
    unique_diffs = np.unique(np.round(diffs * 1000, 1))  # Round to 0.1ms
    print(f"\n🔍 Unique Intervals (ms):")
    for diff in sorted(unique_diffs)[:10]:  # Show first 10
        count = np.sum(np.abs(diffs * 1000 - diff) < 0.05)
        pct = count / len(diffs) * 100
        print(f"  {diff:6.1f} ms: {count:5d} times ({pct:5.1f}%)")
    
    # Look for burst patterns
    print(f"\n💥 Burst Pattern Analysis:")
    zero_diffs = np.sum(diffs == 0)
    near_zero = np.sum(diffs < 0.001)  # Less than 1ms
    
    print(f"  Identical timestamps: {zero_diffs} ({zero_diffs/len(diffs)*100:.1f}%)")
    print(f"  Near-simultaneous (<1ms): {near_zero} ({near_zero/len(diffs)*100:.1f}%)")
    
    # Calculate effective rate excluding bursts
    non_zero_diffs = diffs[diffs > 0.001]  # Exclude near-simultaneous
    if len(non_zero_diffs) > 0:
        effective_interval = np.mean(non_zero_diffs)
        effective_rate = 1.0 / effective_interval
        print(f"  Effective rate (excluding bursts): {effective_rate:.1f} Hz")
        print(f"  Effective interval: {effective_interval*1000:.1f} ms")
    
    # Look for regular patterns
    print(f"\n🔄 Pattern Detection:")
    
    # Check for 4ms intervals (~250Hz)
    four_ms_intervals = np.sum(np.abs(diffs * 1000 - 4.0) < 0.5)
    print(f"  ~4ms intervals (250Hz): {four_ms_intervals} ({four_ms_intervals/len(diffs)*100:.1f}%)")
    
    # Check for ~4.1ms intervals (~241Hz) 
    target_interval = 1000.0 / 241.0  # ~4.15ms
    target_intervals = np.sum(np.abs(diffs * 1000 - target_interval) < 0.5)
    print(f"  ~{target_interval:.1f}ms intervals (241Hz): {target_intervals} ({target_intervals/len(diffs)*100:.1f}%)")
    
    # Recommend processing approach
    print(f"\n💡 Processing Recommendations:")
    
    if zero_diffs > len(diffs) * 0.1:  # More than 10% bursts
        print("  ⚠️ High burst rate detected - use burst detection and averaging")
        print("  📊 Recommended: Group by timestamp, average within bursts")
        print("  🔧 Effective sample rate for FFT: ~241Hz based on unique timestamps")
    else:
        print("  ✅ Regular sampling detected")
        print(f"  📊 Recommended sample rate: {1.0/np.mean(diffs):.0f}Hz")
    
    return {
        'duration': duration,
        'avg_rate': len(timestamps) / duration,
        'burst_rate': zero_diffs / len(diffs),
        'effective_rate': 1.0 / np.mean(non_zero_diffs) if len(non_zero_diffs) > 0 else None,
        'unique_intervals': unique_diffs
    }

if __name__ == "__main__":
    results = analyze_sample_rate_pattern()