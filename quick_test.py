#!/usr/bin/env python3
"""Quick test to debug the muse_player data issue."""

import sys
sys.path.append('/mnt/c/projects/MindMonitorPython')

from consciousness_monitor.data.parsers import DataParser
import numpy as np

def test_muse_parsing():
    parser = DataParser()
    
    # Test format detection
    format_type = parser.detect_format("mind_monitor_complete.csv")
    print(f"Detected format: {format_type}")
    
    # Test getting latest data
    latest_data, detected_format = parser.get_latest_data("mind_monitor_complete.csv", 192)
    
    print(f"Latest data format: {detected_format}")
    if latest_data is not None:
        print(f"Data shape: {latest_data.shape}")
        print(f"Columns: {list(latest_data.columns)}")
        print(f"Sample data:")
        print(latest_data.head(3))
        
        # Test channel extraction
        channels = parser.extract_eeg_channels(latest_data, detected_format)
        print(f"\nExtracted channels: {list(channels.keys())}")
        for name, data in channels.items():
            if len(data) > 0:
                print(f"  {name}: {len(data)} samples, range {np.min(data):.1f} to {np.max(data):.1f}")
    else:
        print("No data returned!")

if __name__ == "__main__":
    test_muse_parsing()