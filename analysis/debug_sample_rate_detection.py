#!/usr/bin/env python3
"""Debug the DataParser sample rate detection"""

import pandas as pd
from consciousness_monitor.data.parsers import DataParser

def debug_sample_rate_detection():
    """Debug why DataParser sample rate detection fails"""
    
    print("🔍 Debugging DataParser sample rate detection")
    print("=" * 60)
    
    parser = DataParser()
    csv_file = "meditation.csv"
    
    # Manually execute the detection logic with debug output
    try:
        print(f"📊 Attempting to read {csv_file}")
        
        # Try to read the CSV
        try:
            df = pd.read_csv(csv_file, header=None, nrows=1000)  # Limit rows for speed
            print(f"📊 Successfully read CSV: {len(df)} rows, {len(df.columns)} columns")
            print(f"📊 First few rows:\n{df.head()}")
        except Exception as e:
            print(f"❌ Failed to read CSV: {e}")
            return
        
        if df is not None and len(df) > 0:
            print("📊 DataFrame loaded successfully")
            
            # Try different timestamp column names
            timestamp_col = None
            for col in ['timestamp_utc', 'timestamp_local', 'TimeStamp', 'timestamp']:
                if col in df.columns:
                    timestamp_col = col
                    print(f"📊 Found named timestamp column: {col}")
                    break
            
            # If no named timestamp column, assume first column is timestamp
            if timestamp_col is None and len(df.columns) > 0:
                timestamp_col = 0  # Use first column as timestamp
                print(f"📊 Using first column (index 0) as timestamp")
            
            if timestamp_col is not None and len(df) > 100:
                print(f"📊 Processing with timestamp column: {timestamp_col}")
                
                # Filter for EEG data only to get true sample rate
                print(f"📊 Filtering for EEG data...")
                eeg_data = df[df.iloc[:, 1] == '/muse/eeg'] if len(df.columns) > 1 else df
                print(f"📊 EEG data: {len(eeg_data)} rows")
                
                if len(eeg_data) > 100:
                    print("📊 Enough EEG data found")
                    
                    # Parse EEG timestamps and get unique values
                    if isinstance(timestamp_col, int):
                        print(f"📊 Extracting timestamps from column {timestamp_col}")
                        timestamps = pd.to_numeric(eeg_data.iloc[:, timestamp_col], errors='coerce').dropna()
                    else:
                        print(f"📊 Extracting timestamps from named column {timestamp_col}")
                        timestamps = pd.to_numeric(eeg_data[timestamp_col], errors='coerce').dropna()
                    
                    print(f"📊 Parsed {len(timestamps)} timestamps")
                    
                    unique_timestamps = timestamps.drop_duplicates().sort_values()
                    print(f"📊 Found {len(unique_timestamps)} unique timestamps")
                    
                    if len(unique_timestamps) > 50:
                        total_duration = unique_timestamps.iloc[-1] - unique_timestamps.iloc[0]
                        print(f"📊 Duration: {total_duration:.3f} seconds")
                        
                        if total_duration > 0:
                            effective_rate = len(unique_timestamps) / total_duration
                            
                            print(f"📊 EEG samples: {len(timestamps)}, unique timestamps: {len(unique_timestamps)}")
                            print(f"📊 Duration: {total_duration:.2f}s, effective rate: {effective_rate:.1f}Hz")
                            
                            # Cap at reasonable EEG rates
                            if effective_rate > 512:
                                print(f"📊 Very high rate detected ({effective_rate:.0f}Hz), using 256Hz")
                                return 256
                            elif effective_rate > 50:  # Accept rates down to 50Hz
                                print(f"📊 Detected sample rate: {effective_rate:.1f}Hz")
                                return effective_rate
                            else:
                                print(f"📊 Very low rate detected ({effective_rate:.1f}Hz), using 256Hz default")
                                return 256
                        else:
                            print("❌ Zero duration calculated")
                    else:
                        print("❌ Not enough unique timestamps")
                else:
                    print("❌ Not enough EEG data")
            else:
                print("❌ No valid timestamp column or not enough data")
        else:
            print("❌ DataFrame is empty or None")
    
    except Exception as e:
        print(f"❌ Exception during detection: {e}")
        import traceback
        traceback.print_exc()
    
    print("📊 Falling back to default: 256Hz")
    return 256

if __name__ == "__main__":
    rate = debug_sample_rate_detection()
    print(f"\n🎯 Final result: {rate}Hz")