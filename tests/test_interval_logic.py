#!/usr/bin/env python3
"""Test the interval output logic"""

import time
from consciousness_monitor import ConsciousnessMonitor

def test_interval_logic():
    print("🧪 Testing Output Interval Logic")
    
    # Create monitor with 3 second output interval
    monitor = ConsciousnessMonitor(
        csv_file="test_force_output.csv",
        window_seconds=0.75,
        update_interval=1.0,
        show_bands=False,
        show_insights=True,
        force_output=False,
        output_interval=3.0  # Force output every 3 seconds
    )
    
    print(f"Monitor configured with output_interval: {monitor.output_interval}s")
    print(f"Force output: {monitor.force_output}")
    print(f"Initial last_output_time: {monitor.last_output_time}")
    
    # Get data and test multiple times
    data = monitor.get_latest_data()
    if data is not None:
        results = monitor.analyze_eeg_window_precomputed(data)
        if results:
            interpretation = monitor.interpret_mental_state(results['averaged'])
            
            print(f"\n🔄 Testing output at different intervals:")
            for i in range(6):
                current_time = time.time()
                time_elapsed = current_time - monitor.last_output_time
                print(f"\nTest {i+1}: time_elapsed={time_elapsed:.1f}s, output_interval={monitor.output_interval}s")
                
                monitor.display_results(interpretation)
                
                if i < 5:  # Don't sleep after last iteration
                    time.sleep(1)
    else:
        print("❌ No data available for testing")

if __name__ == "__main__":
    test_interval_logic()