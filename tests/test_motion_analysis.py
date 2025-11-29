#!/usr/bin/env python3
"""
Motion Artifact Analysis for meditation.csv

This script analyzes accelerometer data from meditation.csv to establish
empirical thresholds for motion artifact detection.
"""

import pandas as pd
import numpy as np
import os

def analyze_motion_artifacts(csv_file="meditation.csv"):
    """Analyze motion (accelerometer) data from meditation.csv"""
    
    if not os.path.exists(csv_file):
        print(f"❌ File {csv_file} not found")
        return
    
    print(f"🏃 Analyzing motion artifacts from {csv_file}")
    print("=" * 60)
    
    # Load the CSV file line by line due to variable columns
    try:
        rows = []
        with open(csv_file, 'r') as f:
            for line_num, line in enumerate(f):
                parts = line.strip().split(', ')
                rows.append(parts)
                if line_num > 50000:  # Limit for performance
                    break
        
        df = pd.DataFrame(rows)
        print(f"📊 Loaded {len(df)} total rows")
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        return
    
    # Filter for accelerometer data (/muse/acc)
    acc = df[df.iloc[:,1] == '/muse/acc']
    print(f"📊 Found {len(acc)} accelerometer rows")
    
    if len(acc) == 0:
        print("❌ No accelerometer data found")
        return
    
    # Extract X, Y, Z accelerometer values (columns 2, 3, 4)
    try:
        x_values = pd.to_numeric(acc.iloc[:, 2], errors='coerce').dropna()
        y_values = pd.to_numeric(acc.iloc[:, 3], errors='coerce').dropna()
        z_values = pd.to_numeric(acc.iloc[:, 4], errors='coerce').dropna()
        
        print(f"📊 Valid X samples: {len(x_values)}")
        print(f"📊 Valid Y samples: {len(y_values)}")
        print(f"📊 Valid Z samples: {len(z_values)}")
        
    except Exception as e:
        print(f"❌ Error parsing accelerometer data: {e}")
        return
    
    # Analysis of individual axes
    print("\n📊 Individual Axis Analysis:")
    print("-" * 40)
    
    axes_data = {'X': x_values, 'Y': y_values, 'Z': z_values}
    axis_stats = {}
    
    for axis, values in axes_data.items():
        if len(values) == 0:
            print(f"⚠️ {axis}: No valid data")
            continue
            
        stats = {
            'count': len(values),
            'mean': values.mean(),
            'std': values.std(),
            'median': values.median(),
            'mad': 1.4826 * (values - values.median()).abs().median(),  # Median Absolute Deviation
            'p75': values.quantile(0.75),
            'p90': values.quantile(0.90),
            'p95': values.quantile(0.95),
            'p99': values.quantile(0.99),
            'min': values.min(),
            'max': values.max(),
            'range': values.max() - values.min()
        }
        
        axis_stats[axis] = stats
        
        print(f"{axis:>1}: mean={stats['mean']:>8.6f} ± {stats['std']:>8.6f}")
        print(f"   median={stats['median']:>8.6f} | MAD={stats['mad']:>8.6f}")
        print(f"   p95={stats['p95']:>8.6f} | max={stats['max']:>8.6f}")
        print()
    
    # Calculate motion magnitude: sqrt(x² + y² + z²)
    print("🌊 Motion Magnitude Analysis:")
    print("-" * 40)
    
    try:
        # Align all arrays to same length for magnitude calculation
        min_len = min(len(x_values), len(y_values), len(z_values))
        if min_len == 0:
            print("❌ Cannot calculate magnitude - no overlapping data")
            return
            
        x_aligned = x_values.iloc[:min_len].values
        y_aligned = y_values.iloc[:min_len].values  
        z_aligned = z_values.iloc[:min_len].values
        
        # Calculate 3D magnitude
        magnitude = np.sqrt(x_aligned**2 + y_aligned**2 + z_aligned**2)
        
        mag_stats = {
            'count': len(magnitude),
            'mean': magnitude.mean(),
            'std': magnitude.std(),
            'median': np.median(magnitude),
            'mad': 1.4826 * np.median(np.abs(magnitude - np.median(magnitude))),
            'p75': np.percentile(magnitude, 75),
            'p90': np.percentile(magnitude, 90),
            'p95': np.percentile(magnitude, 95),
            'p99': np.percentile(magnitude, 99),
            'min': magnitude.min(),
            'max': magnitude.max()
        }
        
        print(f"Magnitude: count={mag_stats['count']:>5} | "
              f"mean={mag_stats['mean']:>8.6f} ± {mag_stats['std']:>8.6f}")
        print(f"           median={mag_stats['median']:>8.6f} | "
              f"MAD={mag_stats['mad']:>8.6f}")
        print(f"           p90={mag_stats['p90']:>8.6f} | "
              f"p95={mag_stats['p95']:>8.6f} | p99={mag_stats['p99']:>8.6f}")
        print(f"           range: {mag_stats['min']:>8.6f} to {mag_stats['max']:>8.6f}")
        
    except Exception as e:
        print(f"⚠️ Error calculating motion magnitude: {e}")
        return
    
    # Motion threshold recommendations
    print("\n💡 Motion Threshold Recommendations:")
    print("-" * 40)
    
    # Current threshold analysis
    current_threshold = 1.0106  # From the plan
    
    print(f"Current threshold in artifact_thresholds.json:")
    print(f"  motion.threshold: {current_threshold}")
    
    # Robust threshold using median + k*MAD (outlier detection)
    # Standard approach: median + 6*MAD for outlier detection
    robust_threshold = mag_stats['median'] + 6 * mag_stats['mad']
    
    # Alternative thresholds
    p95_threshold = mag_stats['p95']
    p99_threshold = mag_stats['p99']
    
    print(f"\nRecommended thresholds based on meditation data:")
    print(f"  Robust (median + 6*MAD): {robust_threshold:.6f}")
    print(f"  Conservative (p95): {p95_threshold:.6f}")
    print(f"  Permissive (p99): {p99_threshold:.6f}")
    
    # Show what percentage of data would be filtered
    thresholds_to_test = {
        'Current': current_threshold,
        'Robust': robust_threshold, 
        'P95': p95_threshold,
        'P99': p99_threshold
    }
    
    print(f"\nFiltering impact analysis:")
    for name, threshold in thresholds_to_test.items():
        filtered_pct = (magnitude > threshold).mean() * 100
        kept_pct = 100 - filtered_pct
        print(f"  {name:>12} ({threshold:>8.6f}): "
              f"keeps {kept_pct:>5.1f}%, filters {filtered_pct:>5.1f}%")
    
    # Identify potential motion events
    print(f"\n🚨 Motion Event Analysis:")
    print("-" * 40)
    
    motion_events = magnitude > robust_threshold
    if motion_events.any():
        event_count = motion_events.sum()
        print(f"Potential motion events: {event_count} samples ({event_count/len(magnitude)*100:.2f}%)")
        
        # Find peak motion values
        peak_indices = np.where(magnitude > p95_threshold)[0]
        if len(peak_indices) > 0:
            print(f"Peak motion samples: {len(peak_indices)}")
            print(f"Highest motion values: {sorted(magnitude[peak_indices], reverse=True)[:5]}")
    else:
        print("No significant motion events detected - very still meditation session!")
    
    return mag_stats

if __name__ == "__main__":
    analyze_motion_artifacts()