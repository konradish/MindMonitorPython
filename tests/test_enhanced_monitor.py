#!/usr/bin/env python3
"""Test script for the enhanced consciousness monitor"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Create test data that mimics Mind Monitor CSV format
def create_test_data():
    # Generate 100 samples of mock EEG data
    n_samples = 100
    timestamps = [datetime.now() - timedelta(seconds=i*0.004) for i in range(n_samples, 0, -1)]
    
    # Mock EEG data (microvolts)
    np.random.seed(42)  # For reproducible test data
    
    test_data = {
        'timestamp_utc': [ts.isoformat() for ts in timestamps],
        'eeg_tp9': np.random.normal(500, 100, n_samples),
        'eeg_af7': np.random.normal(450, 120, n_samples),
        'eeg_af8': np.random.normal(480, 110, n_samples),
        'eeg_tp10': np.random.normal(520, 105, n_samples),
        
        # Pre-computed band powers (mock values)
        'abs_delta': np.random.uniform(0.1, 0.5, n_samples),
        'abs_theta': np.random.uniform(0.05, 0.3, n_samples),
        'abs_alpha': np.random.uniform(0.2, 0.8, n_samples),  # Higher alpha for testing
        'abs_beta': np.random.uniform(0.1, 0.4, n_samples),
        'abs_gamma': np.random.uniform(0.02, 0.15, n_samples),
        
        # Relative band powers
        'rel_delta': np.random.uniform(0.15, 0.35, n_samples),
        'rel_theta': np.random.uniform(0.10, 0.25, n_samples),
        'rel_alpha': np.random.uniform(0.25, 0.45, n_samples),
        'rel_beta': np.random.uniform(0.15, 0.35, n_samples),
        'rel_gamma': np.random.uniform(0.05, 0.15, n_samples),
        
        # Quality indicators
        'touching_forehead': np.random.choice([0, 1], n_samples, p=[0.2, 0.8]),
        'horseshoe_tp9': np.random.uniform(0.6, 1.0, n_samples),
        'horseshoe_af7': np.random.uniform(0.5, 1.0, n_samples),
        'horseshoe_af8': np.random.uniform(0.6, 1.0, n_samples),
        'horseshoe_tp10': np.random.uniform(0.7, 1.0, n_samples),
        
        # Additional features
        'jaw_clench': np.random.choice([0, 1], n_samples, p=[0.95, 0.05]),
        'blink': np.random.choice([0, 1], n_samples, p=[0.9, 0.1])
    }
    
    return pd.DataFrame(test_data)

# Test the enhanced consciousness monitor
def test_enhanced_monitor():
    print("🧪 Testing Enhanced Consciousness Monitor")
    
    # Create test data
    test_df = create_test_data()
    test_csv = "test_consciousness_data.csv"
    test_df.to_csv(test_csv, index=False)
    print(f"✅ Created test data: {test_csv}")
    
    # Import and test the monitor
    try:
        from consciousness_monitor import ConsciousnessMonitor
        
        # Initialize monitor
        monitor = ConsciousnessMonitor(
            csv_file=test_csv,
            window_seconds=1.0,
            update_interval=0.5,
            show_bands=False,  # Use compact output
            show_insights=True
        )
        print("✅ Monitor initialized successfully")
        
        # Test analysis methods
        data = monitor.get_latest_data()
        if data is not None:
            print(f"✅ Data loaded: {len(data)} samples")
            
            # Test precomputed analysis
            results = monitor.analyze_eeg_window_precomputed(data)
            if results:
                print("✅ Precomputed analysis successful")
                
                # Test interpretation
                interpretation = monitor.interpret_mental_state(results['averaged'])
                print(f"✅ Mental state interpretation: {interpretation['state']}")
                
                # Test display (should use compact format)
                print("\n🎯 Testing Compact Display Format:")
                monitor.display_results(interpretation)
                
                # Test session summary
                summary = monitor._generate_session_summary()
                print(f"\n📊 Session Summary: {summary}")
                
            else:
                print("❌ Analysis failed")
        else:
            print("❌ Could not load data")
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Test error: {e}")
        raise
    
    print("\n🎉 Enhanced consciousness monitor test completed!")

if __name__ == "__main__":
    test_enhanced_monitor()