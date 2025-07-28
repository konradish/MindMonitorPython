#!/usr/bin/env python3
"""Test the force output and clipboard features"""

import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

def create_simple_test_data():
    """Create simple test data"""
    n_samples = 50
    timestamps = [datetime.now() - timedelta(seconds=i*0.004) for i in range(n_samples, 0, -1)]
    
    # Create data with obvious alpha dominance for testing
    test_data = {
        'timestamp_utc': [ts.isoformat() for ts in timestamps],
        'eeg_tp9': np.random.normal(600, 50, n_samples),
        'eeg_af7': np.random.normal(580, 60, n_samples),
        'eeg_af8': np.random.normal(590, 55, n_samples),
        'eeg_tp10': np.random.normal(610, 50, n_samples),
        
        # Strong alpha pattern for clear results
        'abs_delta': np.random.uniform(0.1, 0.2, n_samples),
        'abs_theta': np.random.uniform(0.1, 0.2, n_samples),
        'abs_alpha': np.random.uniform(0.5, 0.7, n_samples),  # High alpha
        'abs_beta': np.random.uniform(0.1, 0.2, n_samples),
        'abs_gamma': np.random.uniform(0.05, 0.1, n_samples),
        
        # Relative powers (normalized)
        'rel_delta': np.random.uniform(15, 20, n_samples),
        'rel_theta': np.random.uniform(15, 20, n_samples),
        'rel_alpha': np.random.uniform(40, 50, n_samples),  # High alpha %
        'rel_beta': np.random.uniform(15, 20, n_samples),
        'rel_gamma': np.random.uniform(5, 10, n_samples),
        
        # Good quality
        'touching_forehead': np.ones(n_samples),
        'horseshoe_tp9': np.random.uniform(0.9, 1.0, n_samples),
        'horseshoe_af7': np.random.uniform(0.9, 1.0, n_samples),
        'horseshoe_af8': np.random.uniform(0.9, 1.0, n_samples),
        'horseshoe_tp10': np.random.uniform(0.9, 1.0, n_samples),
        
        'jaw_clench': np.zeros(n_samples),
        'blink': np.zeros(n_samples)
    }
    
    return pd.DataFrame(test_data)

def test_features():
    """Test the enhanced features"""
    print("🧪 Testing Enhanced Consciousness Monitor Features")
    print("=" * 55)
    
    # Create test data
    test_df = create_simple_test_data()
    test_csv = "test_force_output.csv"
    test_df.to_csv(test_csv, index=False)
    print(f"✅ Created test data: {test_csv}")
    
    print(f"\n🎯 Testing Different Output Modes:")
    print("-" * 40)
    
    from consciousness_monitor import ConsciousnessMonitor
    
    # Test 1: Smart mode (default)
    print(f"\n1️⃣ SMART MODE (only significant changes):")
    monitor_smart = ConsciousnessMonitor(
        csv_file=test_csv,
        window_seconds=1.0,
        update_interval=1.0,
        show_bands=False,
        show_insights=True,
        force_output=False  # Smart mode
    )
    
    # Process data
    data = monitor_smart.get_latest_data()
    if data is not None:
        results = monitor_smart.analyze_eeg_window_precomputed(data)
        if results:
            interpretation = monitor_smart.interpret_mental_state(results['averaged'])
            monitor_smart.display_results(interpretation)
            # Second call should not output (no significant change)
            monitor_smart.display_results(interpretation)
    
    # Test 2: Force output mode
    print(f"\n2️⃣ FORCE OUTPUT MODE (every update):")
    monitor_force = ConsciousnessMonitor(
        csv_file=test_csv,
        window_seconds=1.0,
        update_interval=1.0,
        show_bands=False,
        show_insights=True,
        force_output=True  # Force mode
    )
    
    # Process same data multiple times
    data = monitor_force.get_latest_data()
    if data is not None:
        results = monitor_force.analyze_eeg_window_precomputed(data)
        if results:
            interpretation = monitor_force.interpret_mental_state(results['averaged'])
            for i in range(3):
                print(f"   Update {i+1}:")
                monitor_force.display_results(interpretation)
                time.sleep(1.1)  # Exceed update interval
    
    # Test 3: Clipboard functionality
    print(f"\n3️⃣ CLIPBOARD FUNCTIONALITY:")
    print("Testing clipboard copy (will show fallback if clipboard unavailable)")
    
    # Simulate some events
    for i in range(3):
        monitor_force._track_session_event(
            time.time() - (2-i), 
            f"[12:0{i}:0{i}] Test event {i+1}",
            "TEST",
            {'alpha': 45 + i*5, 'beta': 25, 'delta': 20, 'theta': 15, 'gamma': 5}
        )
    
    # Test copy commands
    monitor_force._copy_recent_events()
    monitor_force._copy_session_summary()
    
    print(f"\n✨ COMMAND LINE OPTIONS:")
    print("  • Default (smart):   python consciousness_monitor.py")
    print("  • Force every 2s:    python consciousness_monitor.py --force-output --update 2")
    print("  • Force every 5s:    python consciousness_monitor.py --output-interval 5")
    print("  • Interactive commands: 'c' (copy), 's' (summary), 'n' (now), 'q' (quit)")
    
    print(f"\n🎉 Feature test completed!")

if __name__ == "__main__":
    test_features()