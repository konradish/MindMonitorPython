#!/usr/bin/env python3
"""
Contact Quality Baseline Analysis for meditation.csv

This script analyzes the contact quality data from meditation.csv to establish
empirical thresholds for artifact filtering.
"""

import pandas as pd
import numpy as np
import os

def analyze_contact_quality(csv_file="meditation.csv"):
    """Analyze contact quality (optics) data from meditation.csv"""
    
    if not os.path.exists(csv_file):
        print(f"❌ File {csv_file} not found")
        return
    
    print(f"🔍 Analyzing contact quality from {csv_file}")
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
    
    # Filter for optics data (/muse/optics)
    optics = df[df.iloc[:,1] == '/muse/optics']
    print(f"📊 Found {len(optics)} optics rows")
    
    if len(optics) == 0:
        print("❌ No optics data found")
        return
    
    # Extract contact quality values for each channel (columns 2-5: TP9, AF7, AF8, TP10)
    channel_names = ['TP9', 'AF7', 'AF8', 'TP10']
    
    print("\n🧠 Individual Channel Analysis:")
    print("-" * 40)
    
    channel_stats = {}
    for i, channel in enumerate(channel_names):
        try:
            values = pd.to_numeric(optics.iloc[:, i+2], errors='coerce').dropna()
            
            if len(values) == 0:
                print(f"⚠️ {channel}: No valid data")
                continue
                
            stats = {
                'count': len(values),
                'mean': values.mean(),
                'std': values.std(),
                'median': values.median(),
                'p25': values.quantile(0.25),
                'p75': values.quantile(0.75),
                'p90': values.quantile(0.90),
                'p95': values.quantile(0.95),
                'p99': values.quantile(0.99),
                'min': values.min(),
                'max': values.max()
            }
            
            channel_stats[channel] = stats
            
            print(f"{channel:>4}: count={stats['count']:>5} | "
                  f"mean={stats['mean']:>5.3f} ± {stats['std']:>5.3f}")
            print(f"      median={stats['median']:>5.3f} | "
                  f"p90={stats['p90']:>5.3f} | p95={stats['p95']:>5.3f} | "
                  f"max={stats['max']:>5.3f}")
            
        except Exception as e:
            print(f"⚠️ {channel}: Error processing data - {e}")
    
    # Calculate horseshoe average across all channels
    print("\n🔗 Combined Horseshoe Analysis:")
    print("-" * 40)
    
    try:
        # Convert all channel data to numeric and calculate row-wise averages
        channel_data = []
        for i in range(4):  # TP9, AF7, AF8, TP10
            values = pd.to_numeric(optics.iloc[:, i+2], errors='coerce')
            channel_data.append(values)
        
        # Create DataFrame for easier handling
        channel_df = pd.DataFrame({
            'TP9': channel_data[0],
            'AF7': channel_data[1], 
            'AF8': channel_data[2],
            'TP10': channel_data[3]
        })
        
        # Calculate horseshoe average (mean across channels for each timepoint)
        horseshoe_avg = channel_df.mean(axis=1, skipna=True).dropna()
        
        if len(horseshoe_avg) > 0:
            hs_stats = {
                'count': len(horseshoe_avg),
                'mean': horseshoe_avg.mean(),
                'std': horseshoe_avg.std(),
                'median': horseshoe_avg.median(),
                'p25': horseshoe_avg.quantile(0.25),
                'p75': horseshoe_avg.quantile(0.75),
                'p90': horseshoe_avg.quantile(0.90),
                'p95': horseshoe_avg.quantile(0.95),
                'p99': horseshoe_avg.quantile(0.99),
                'min': horseshoe_avg.min(),
                'max': horseshoe_avg.max()
            }
            
            print(f"Horseshoe Avg: count={hs_stats['count']:>5} | "
                  f"mean={hs_stats['mean']:>5.3f} ± {hs_stats['std']:>5.3f}")
            print(f"               median={hs_stats['median']:>5.3f} | "
                  f"p90={hs_stats['p90']:>5.3f} | p95={hs_stats['p95']:>5.3f} | "
                  f"max={hs_stats['max']:>5.3f}")
        
    except Exception as e:
        print(f"⚠️ Error calculating horseshoe average: {e}")
    
    # Provide threshold recommendations
    print("\n💡 Threshold Recommendations:")
    print("-" * 40)
    
    if channel_stats:
        # Calculate overall statistics across all channels
        all_p95 = [stats['p95'] for stats in channel_stats.values()]
        all_max = [stats['max'] for stats in channel_stats.values()]
        
        avg_p95 = np.mean(all_p95)
        avg_max = np.mean(all_max)
        
        print(f"Current thresholds in artifact_thresholds.json:")
        print(f"  good_max: 1.4 (suggested: {avg_p95:.3f})")
        print(f"  warning_max: 2.0 (suggested: {avg_max + 0.1:.3f})")
        
        # Quality categories based on data
        good_threshold = avg_p95 + 0.1  # P95 + small margin
        warning_threshold = avg_max + 0.2  # Max + margin
        
        print(f"\nRecommended thresholds based on meditation data:")
        print(f"  contact_quality.good_max: {good_threshold:.3f}")
        print(f"  contact_quality.warning_max: {warning_threshold:.3f}")
        
        # Show percentage of data that would be filtered
        if 'horseshoe_avg' in locals():
            good_pct = (horseshoe_avg <= good_threshold).mean() * 100
            warning_pct = (horseshoe_avg <= warning_threshold).mean() * 100
            
            print(f"\nData quality distribution:")
            print(f"  Good quality: {good_pct:.1f}% of samples")
            print(f"  Acceptable: {warning_pct:.1f}% of samples")
            print(f"  Poor quality: {100-warning_pct:.1f}% of samples")

if __name__ == "__main__":
    analyze_contact_quality()