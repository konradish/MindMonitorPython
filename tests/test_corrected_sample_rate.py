#!/usr/bin/env python3
"""
Test the corrected sample rate detection on meditation.csv
"""

import pandas as pd
import numpy as np

def test_corrected_sample_rate_detection(csv_file="meditation.csv"):
    """Test the corrected sample rate detection logic"""
    
    print(f"🔍 Testing corrected sample rate detection on {csv_file}")
    print("=" * 60)
    
    # Load data manually to test the logic
    rows = []
    with open(csv_file, 'r') as f:
        for i, line in enumerate(f):
            if i > 10000:  # Limit for testing
                break
            parts = line.strip().split(', ')
            rows.append(parts)
    
    df = pd.DataFrame(rows)
    print(f"📊 Loaded {len(df)} total rows")
    
    # Filter for EEG data only
    eeg_data = df[df.iloc[:, 1] == '/muse/eeg']
    print(f"📊 Found {len(eeg_data)} EEG rows")
    
    if len(eeg_data) > 100:
        # Parse EEG timestamps and get unique values
        timestamps = pd.to_numeric(eeg_data.iloc[:, 0], errors='coerce').dropna()
        unique_timestamps = timestamps.drop_duplicates().sort_values()
        
        print(f"📊 EEG timestamps: {len(timestamps)}")
        print(f"📊 Unique timestamps: {len(unique_timestamps)}")
        print(f"📊 First few timestamps: {list(timestamps.head(10))}")
        print(f"📊 First few unique: {list(unique_timestamps.head(10))}")
        
        if len(unique_timestamps) > 50:
            total_duration = unique_timestamps.iloc[-1] - unique_timestamps.iloc[0]
            effective_rate = len(unique_timestamps) / total_duration
            
            print(f"📊 Duration: {total_duration:.3f}s")
            print(f"📊 Effective rate: {effective_rate:.1f}Hz")
            
            # Check interval consistency
            intervals = np.diff(unique_timestamps.values)
            avg_interval = np.mean(intervals)
            std_interval = np.std(intervals)
            
            print(f"📊 Average interval: {avg_interval*1000:.2f}ms")
            print(f"📊 Interval std: {std_interval*1000:.2f}ms")
            print(f"📊 Expected rate from intervals: {1/avg_interval:.1f}Hz")
            
            return effective_rate
    
    return None

if __name__ == "__main__":
    rate = test_corrected_sample_rate_detection()