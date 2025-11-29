#\!/usr/bin/env python3
"""Debug signal processing issue."""

import sys
import numpy as np
sys.path.append('/mnt/c/projects/MindMonitorPython')

from consciousness_monitor.data.parsers import DataParser
from consciousness_monitor.data.processors import SignalProcessor

def debug_signal_processing():
    # Get data
    parser = DataParser()
    latest_data, format_type = parser.get_latest_data("mind_monitor_complete.csv", 192)
    
    if latest_data is None:
        print("No data available")
        return
    
    # Extract channels
    channels = parser.extract_eeg_channels(latest_data, format_type)
    
    print(f"Channels extracted: {list(channels.keys())}")
    
    # Process each channel
    processor = SignalProcessor(256)
    
    for channel_name, channel_data in channels.items():
        print(f"\nChannel {channel_name}:")
        print(f"  Raw data: {len(channel_data)} samples")
        print(f"  Range: {np.min(channel_data):.1f} to {np.max(channel_data):.1f}")
        print(f"  Mean: {np.mean(channel_data):.1f}")
        print(f"  Std: {np.std(channel_data):.1f}")
        
        # Test preprocessing
        try:
            processed = processor.preprocess_signal(channel_data)
            print(f"  Processed: {len(processed)} samples")
            print(f"  Processed range: {np.min(processed):.1f} to {np.max(processed):.1f}")
            
            # Test band power calculation
            band_power = processor.calculate_all_band_powers(channel_data)
            print(f"  Band powers: {band_power.as_dict()}")
            
            # Test percentages
            percentages = band_power.as_percentages()
            print(f"  Percentages: {percentages}")
            
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Test multichannel average
    try:
        print(f"\nMultichannel average:")
        avg_power = processor.calculate_multichannel_average(channels)
        print(f"  Average powers: {avg_power.as_dict()}")
        print(f"  Average percentages: {avg_power.as_percentages()}")
    except Exception as e:
        print(f"  Multichannel error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_signal_processing()