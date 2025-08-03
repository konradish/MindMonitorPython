#!/usr/bin/env python3
"""Test the monitor briefly to see output."""

import sys
import time
sys.path.append('/mnt/c/projects/MindMonitorPython')

from consciousness_monitor import EnhancedConsciousnessMonitor

def test_monitor():
    monitor = EnhancedConsciousnessMonitor(
        csv_file="mind_monitor_complete.csv",
        window_seconds=0.75,
        update_interval=1.0,
        debug=False,
        konrad_mode=True,
        force_output=True  # Force output to see results
    )
    
    print("Testing analysis...")
    
    # Get latest data and analyze it once
    latest_data, format_type = monitor.data_parser.get_latest_data(
        monitor.csv_file, monitor.window_samples
    )
    
    if latest_data is not None:
        print(f"Got data: {len(latest_data)} samples")
        
        # Extract channels and analyze
        channels = monitor.data_parser.extract_eeg_channels(latest_data, format_type)
        if channels:
            print(f"Channels: {list(channels.keys())}")
            result = monitor.analyze_eeg_window({'channels': channels})
            
            print(f"Analysis result:")
            print(f"  State: {result.state}")
            print(f"  Emoji: {result.emoji}")
            print(f"  Band percentages: {result.band_percentages}")
            print(f"  dB changes: {result.db_changes}")
            print(f"  Insights: {result.insights}")
            
            # Display it properly
            monitor.display_manager.display_analysis_result(result)
        else:
            print("No channels extracted")
    else:
        print("No data available")

if __name__ == "__main__":
    test_monitor()