#!/usr/bin/env python3
"""
Analyze the data ranges for EEG band powers to understand the actual value distribution
"""

import pandas as pd
import numpy as np

def analyze_eeg_data_ranges(csv_file="mind_monitor_data.csv"):
    """Analyze the ranges of EEG band power data"""
    
    print(f"📊 Analyzing data ranges in: {csv_file}")
    print("=" * 60)
    
    # Read the CSV file
    try:
        df = pd.read_csv(csv_file)
        print(f"✅ Loaded {len(df)} samples")
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return
    
    # Define the band columns
    abs_bands = ['abs_delta', 'abs_theta', 'abs_alpha', 'abs_beta', 'abs_gamma']
    rel_bands = ['rel_delta', 'rel_theta', 'rel_alpha', 'rel_beta', 'rel_gamma']
    
    print(f"\n📈 ABSOLUTE BAND POWER ANALYSIS")
    print("-" * 40)
    
    for band in abs_bands:
        if band in df.columns:
            data = df[band].dropna()
            if len(data) > 0:
                print(f"{band:>11}: min={data.min():8.4f}, max={data.max():8.4f}, mean={data.mean():8.4f}, std={data.std():8.4f}")
            else:
                print(f"{band:>11}: No valid data")
        else:
            print(f"{band:>11}: Column not found")
    
    print(f"\n📈 RELATIVE BAND POWER ANALYSIS")
    print("-" * 40)
    
    for band in rel_bands:
        if band in df.columns:
            # Handle potential string/empty values in relative bands
            data = pd.to_numeric(df[band], errors='coerce').dropna()
            if len(data) > 0:
                print(f"{band:>11}: min={data.min():8.4f}, max={data.max():8.4f}, mean={data.mean():8.4f}, std={data.std():8.4f}")
            else:
                print(f"{band:>11}: No valid numeric data")
        else:
            print(f"{band:>11}: Column not found")
    
    # Check if data is in expected -1 to 1 range
    print(f"\n🔍 RANGE ANALYSIS")
    print("-" * 40)
    
    print("Checking if data falls within expected [-1, 1] range:")
    
    all_abs_data = []
    all_rel_data = []
    
    for band in abs_bands:
        if band in df.columns:
            data = df[band].dropna()
            if len(data) > 0:
                all_abs_data.extend(data.values)
                in_range = ((data >= -1) & (data <= 1)).sum()
                print(f"  {band}: {in_range}/{len(data)} ({in_range/len(data)*100:.1f}%) in [-1,1] range")
    
    for band in rel_bands:
        if band in df.columns:
            data = pd.to_numeric(df[band], errors='coerce').dropna()
            if len(data) > 0:
                all_rel_data.extend(data.values)
                in_range = ((data >= -1) & (data <= 1)).sum()
                print(f"  {band}: {in_range}/{len(data)} ({in_range/len(data)*100:.1f}%) in [-1,1] range")
    
    # Overall statistics
    if all_abs_data:
        abs_array = np.array(all_abs_data)
        print(f"\n📊 OVERALL ABSOLUTE STATS:")
        print(f"  Global min: {abs_array.min():.4f}")
        print(f"  Global max: {abs_array.max():.4f}")
        print(f"  % in [-1,1]: {((abs_array >= -1) & (abs_array <= 1)).sum() / len(abs_array) * 100:.1f}%")
    
    if all_rel_data:
        rel_array = np.array(all_rel_data)
        print(f"\n📊 OVERALL RELATIVE STATS:")
        print(f"  Global min: {rel_array.min():.4f}")
        print(f"  Global max: {rel_array.max():.4f}")
        print(f"  % in [-1,1]: {((rel_array >= -1) & (rel_array <= 1)).sum() / len(rel_array) * 100:.1f}%")
    
    # Sample some data points for inspection
    print(f"\n🔍 SAMPLE DATA (first 10 non-null values):")
    print("-" * 40)
    
    for band in abs_bands + rel_bands:
        if band in df.columns:
            if 'rel_' in band:
                data = pd.to_numeric(df[band], errors='coerce').dropna().head(10)
            else:
                data = df[band].dropna().head(10)
            
            if len(data) > 0:
                values_str = ', '.join([f"{x:.3f}" for x in data.values])
                print(f"  {band}: [{values_str}]")

if __name__ == "__main__":
    analyze_eeg_data_ranges()