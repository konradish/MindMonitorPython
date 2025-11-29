#!/usr/bin/env python3
"""Demo script showing the enhanced consciousness monitor features"""

import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

def create_dynamic_test_data():
    """Create test data that simulates changing mental states"""
    n_samples = 500
    base_time = datetime.now()
    
    # Simulate different mental states over time
    data = []
    
    for i in range(n_samples):
        timestamp = base_time + timedelta(seconds=i*0.004)
        
        # Simulate state transitions
        if i < 100:  # Initial relaxed state
            alpha_power = np.random.uniform(0.4, 0.7)
            beta_power = np.random.uniform(0.1, 0.3)
            delta_power = np.random.uniform(0.1, 0.3)
        elif i < 200:  # Transition to focused state
            alpha_power = np.random.uniform(0.3, 0.5)
            beta_power = np.random.uniform(0.3, 0.6)  # Higher beta
            delta_power = np.random.uniform(0.1, 0.2)
        elif i < 300:  # Alert/tense state
            alpha_power = np.random.uniform(0.1, 0.3)  # Low alpha
            beta_power = np.random.uniform(0.5, 0.8)   # High beta
            delta_power = np.random.uniform(0.1, 0.2)
        elif i < 400:  # Creative/flow state
            alpha_power = np.random.uniform(0.3, 0.5)
            beta_power = np.random.uniform(0.2, 0.4)
            delta_power = np.random.uniform(0.1, 0.2)
        else:  # Back to relaxed
            alpha_power = np.random.uniform(0.5, 0.8)  # High alpha
            beta_power = np.random.uniform(0.1, 0.3)
            delta_power = np.random.uniform(0.2, 0.4)
        
        # Calculate remaining bands
        theta_power = np.random.uniform(0.1, 0.3)
        gamma_power = np.random.uniform(0.05, 0.15)
        
        # Normalize to ensure they sum to 1
        total = alpha_power + beta_power + delta_power + theta_power + gamma_power
        
        # Add some noise to make it more realistic
        alpha_power = alpha_power / total + np.random.normal(0, 0.05)
        beta_power = beta_power / total + np.random.normal(0, 0.05)
        delta_power = delta_power / total + np.random.normal(0, 0.05)
        theta_power = theta_power / total + np.random.normal(0, 0.05)
        gamma_power = gamma_power / total + np.random.normal(0, 0.05)
        
        # Mock EEG values that correspond to the band powers
        eeg_base = 500 + (alpha_power * 200)  # Higher alpha = higher base signal
        
        data.append({
            'timestamp_utc': timestamp.isoformat(),
            'eeg_tp9': eeg_base + np.random.normal(0, 50),
            'eeg_af7': eeg_base + np.random.normal(0, 60),
            'eeg_af8': eeg_base + np.random.normal(0, 55),
            'eeg_tp10': eeg_base + np.random.normal(0, 50),
            
            # Pre-computed band powers
            'abs_delta': max(0.01, delta_power),
            'abs_theta': max(0.01, theta_power),
            'abs_alpha': max(0.01, alpha_power),
            'abs_beta': max(0.01, beta_power),
            'abs_gamma': max(0.01, gamma_power),
            
            # Relative powers (normalized)
            'rel_delta': max(0.01, delta_power) * 100,
            'rel_theta': max(0.01, theta_power) * 100,
            'rel_alpha': max(0.01, alpha_power) * 100,
            'rel_beta': max(0.01, beta_power) * 100,
            'rel_gamma': max(0.01, gamma_power) * 100,
            
            # Quality indicators
            'touching_forehead': 1,
            'horseshoe_tp9': np.random.uniform(0.8, 1.0),
            'horseshoe_af7': np.random.uniform(0.8, 1.0),
            'horseshoe_af8': np.random.uniform(0.8, 1.0),
            'horseshoe_tp10': np.random.uniform(0.8, 1.0),
            
            'jaw_clench': 0,
            'blink': 0
        })
    
    return pd.DataFrame(data)

def demo_enhanced_monitor():
    """Demonstrate the enhanced consciousness monitor"""
    print("🎯 Enhanced Consciousness Monitor Demo")
    print("=" * 50)
    
    # Create dynamic test data
    print("📊 Creating dynamic test data with state transitions...")
    test_df = create_dynamic_test_data()
    test_csv = "demo_consciousness_data.csv"
    test_df.to_csv(test_csv, index=False)
    print(f"✅ Created {len(test_df)} samples with simulated state changes")
    
    # Import the enhanced monitor
    from consciousness_monitor import ConsciousnessMonitor
    
    # Initialize monitor
    print(f"\n🔄 Initializing enhanced monitor...")
    monitor = ConsciousnessMonitor(
        csv_file=test_csv,
        window_seconds=0.75,
        update_interval=1.0,
        show_bands=False,  # Use compact output
        show_insights=True
    )
    
    print(f"\n🎪 Simulating real-time monitoring...")
    print("Watch for state transitions in the compact output!")
    print("The format: [time] Band% | fNIRS | STATE | emoji")
    print("-" * 60)
    
    # Simulate real-time by processing chunks
    chunk_size = 50
    for i in range(0, len(test_df), chunk_size):
        chunk = test_df.iloc[:i+chunk_size]  # Cumulative data
        
        # Analyze current window
        results = monitor.analyze_eeg_window_precomputed(chunk.tail(200))  # Last 200 samples
        if results and 'averaged' in results:
            interpretation = monitor.interpret_mental_state(results['averaged'])
            monitor.display_results(interpretation)
        
        time.sleep(0.5)  # Pause to show transitions
        
        if i > 300:  # Show enough to see multiple state changes
            break
    
    # Show final session summary
    print(f"\n🏁 Demo Session Summary:")
    summary = monitor._generate_session_summary()
    print(summary)
    
    print(f"\n✨ Key Features Demonstrated:")
    print("  • Compact output format with smart event detection")
    print("  • Color-coded mental states with emojis")
    print("  • fNIRS-equivalent values from EEG channels")
    print("  • Session tracking and summary generation")
    print("  • Enhanced error handling and validation")
    
    print(f"\n🎉 Demo completed! Try running: uv run python consciousness_monitor.py")

if __name__ == "__main__":
    demo_enhanced_monitor()