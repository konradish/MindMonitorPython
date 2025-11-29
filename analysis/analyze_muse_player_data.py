#!/usr/bin/env python3
"""
Analyze the complete muse-player CSV to understand all available data streams
"""

import pandas as pd
import numpy as np
from collections import defaultdict

def analyze_muse_player_csv(csv_file="mind_monitor_complete.csv"):
    """Analyze the muse-player CSV structure and data streams"""
    
    print(f"📊 Analyzing muse-player CSV: {csv_file}")
    print("=" * 70)
    
    try:
        # Read the CSV with variable-length rows
        lines = []
        max_cols = 0
        
        with open(csv_file, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                lines.append(parts)
                max_cols = max(max_cols, len(parts))
        
        print(f"✅ Loaded {len(lines)} rows, max {max_cols} columns")
        
        # Pad all rows to same length
        for line in lines:
            while len(line) < max_cols:
                line.append(None)
        
        # Create DataFrame
        df = pd.DataFrame(lines)
        df.columns = ['timestamp', 'osc_address'] + [f'data_{i}' for i in range(max_cols-2)]
        
        # Convert timestamp column to numeric
        df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
        
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    # Analyze OSC addresses (data stream types)
    print(f"\n🎯 OSC DATA STREAMS DETECTED:")
    print("-" * 40)
    
    stream_counts = df['osc_address'].value_counts()
    stream_data = defaultdict(list)
    
    for address, count in stream_counts.items():
        print(f"{address:>25}: {count:>6} samples")
        
        # Get sample data for each stream
        sample_data = df[df['osc_address'] == address].iloc[0]
        non_null_data = [x for x in sample_data[2:] if pd.notna(x)]
        stream_data[address] = non_null_data[:10]  # First 10 values
    
    # Detailed analysis of each stream
    print(f"\n📈 DETAILED STREAM ANALYSIS:")
    print("-" * 40)
    
    for address in sorted(stream_data.keys()):
        stream_df = df[df['osc_address'] == address].copy()
        
        print(f"\n🔍 {address}")
        print(f"   Samples: {len(stream_df)}")
        
        # Analyze data columns for this stream
        data_cols = [col for col in stream_df.columns if col.startswith('data_')]
        non_empty_cols = []
        
        for col in data_cols:
            non_null_count = stream_df[col].notna().sum()
            if non_null_count > 0:
                non_empty_cols.append(col)
                
        print(f"   Data fields: {len(non_empty_cols)}")
        
        # Show sample values and ranges
        if non_empty_cols:
            sample_row = stream_df.iloc[0]
            sample_values = [sample_row[col] for col in non_empty_cols if pd.notna(sample_row[col])]
            
            if sample_values:
                print(f"   Sample values: {sample_values[:8]}")  # First 8 values
                
                # Calculate ranges for numeric data
                try:
                    all_values = []
                    for col in non_empty_cols:
                        values = pd.to_numeric(stream_df[col], errors='coerce').dropna()
                        if len(values) > 0:
                            all_values.extend(values)
                    
                    if all_values:
                        all_values = np.array(all_values)
                        print(f"   Range: [{all_values.min():.3f}, {all_values.max():.3f}]")
                        print(f"   Mean: {all_values.mean():.3f}, Std: {all_values.std():.3f}")
                except:
                    print("   (Non-numeric data)")
    
    # Check for timing patterns
    print(f"\n⏰ TIMING ANALYSIS:")
    print("-" * 40)
    
    timestamps = pd.to_numeric(df['timestamp'], errors='coerce').dropna()
    if len(timestamps) > 1:
        time_diffs = np.diff(timestamps)
        print(f"Sample rate analysis:")
        print(f"   Duration: {timestamps.max() - timestamps.min():.1f} seconds")
        print(f"   Avg interval: {time_diffs.mean():.4f}s")
        print(f"   Est. sample rate: {1/time_diffs.mean():.1f} Hz")
        
        # Check timing per stream
        for address in ['/muse/eeg', '/muse/optics']:
            if address in stream_counts:
                stream_df = df[df['osc_address'] == address]
                stream_timestamps = pd.to_numeric(stream_df['timestamp'], errors='coerce').dropna()
                if len(stream_timestamps) > 1:
                    stream_diffs = np.diff(stream_timestamps)
                    print(f"   {address}: {1/stream_diffs.mean():.1f} Hz")
    
    # Generate comparison with current script
    print(f"\n🔄 COMPARISON WITH CURRENT SCRIPT:")
    print("-" * 40)
    
    current_fields = [
        'timestamp_utc', 'timestamp_local', 'eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10',
        'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z',
        'abs_delta', 'abs_theta', 'abs_alpha', 'abs_beta', 'abs_gamma',
        'rel_delta', 'rel_theta', 'rel_alpha', 'rel_beta', 'rel_gamma',
        'touching_forehead', 'horseshoe_tp9', 'horseshoe_af7', 'horseshoe_af8', 'horseshoe_tp10',
        'jaw_clench', 'blink'
    ]
    
    detected_streams = list(stream_counts.keys())
    
    print("Streams in muse-player data:")
    for stream in detected_streams:
        print(f"   ✅ {stream}")
    
    print(f"\nNew streams not in current script:")
    if '/muse/optics' in detected_streams:
        print("   🆕 /muse/optics - fNIRS/optical data!")
    
    # Suggest updates needed
    print(f"\n💡 SUGGESTED UPDATES:")
    print("-" * 40)
    print("1. Add optical/fNIRS data parsing")
    print("2. Handle timestamp format (Unix epoch)")
    print("3. Parse variable-length OSC message format")
    print("4. Add optical data to consciousness analysis")
    
    return stream_data, stream_counts

if __name__ == "__main__":
    analyze_muse_player_csv()