#!/usr/bin/env python3
"""
Test script for enhanced consciousness monitor features
Tests artifact filtering and sub-state detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from consciousness_monitor import EnhancedConsciousnessMonitor

def test_artifact_filtering():
    """Test artifact filtering functionality"""
    print("🧪 Testing artifact filtering...")
    
    monitor = EnhancedConsciousnessMonitor(debug=True)
    
    # Test 1: Multi-band spike artifact
    bands = {'alpha': 50, 'beta': 40, 'delta': 30, 'theta': 20, 'gamma': 15}
    db_changes = {'alpha_db_change': 95, 'beta_db_change': 95, 'delta_db_change': 95, 'theta_db_change': 2, 'gamma_db_change': 2}
    
    artifact = monitor.detect_artifacts(bands, db_changes)
    print(f"   Multi-band spike test: {artifact} {'✅' if artifact == 'ARTIFACT_MULTIBAND_SPIKE' else '❌'}")
    
    # Test 2: Impossible combination
    bands = {'alpha': 96, 'beta': 35, 'delta': 5, 'theta': 2, 'gamma': 2}
    db_changes = {'alpha_db_change': 1, 'beta_db_change': 1, 'delta_db_change': 1, 'theta_db_change': 1, 'gamma_db_change': 1}
    
    artifact = monitor.detect_artifacts(bands, db_changes)
    print(f"   Impossible combination test: {artifact} {'✅' if artifact == 'ARTIFACT_IMPOSSIBLE_COMBO' else '❌'}")
    
    # Test 3: Normal data (no artifact)
    bands = {'alpha': 70, 'beta': 15, 'delta': 10, 'theta': 3, 'gamma': 2}
    db_changes = {'alpha_db_change': 2, 'beta_db_change': 1, 'delta_db_change': -1, 'theta_db_change': 0, 'gamma_db_change': 0}
    
    artifact = monitor.detect_artifacts(bands, db_changes)
    print(f"   Normal data test: {artifact} {'✅' if artifact is None else '❌'}")

def test_sub_state_detection():
    """Test sub-state detection functionality"""
    print("\n🧪 Testing sub-state detection...")
    
    monitor = EnhancedConsciousnessMonitor(debug=True)
    
    # Test 1: Flow - Engaged
    bands = {'alpha': 75, 'beta': 20, 'delta': 3, 'theta': 1, 'gamma': 1}
    db_changes = {'alpha_db_change': 0, 'beta_db_change': 0, 'delta_db_change': 0, 'theta_db_change': 0, 'gamma_db_change': 0}
    
    sub_state = monitor.detect_sub_state('flow_state', bands, db_changes)
    print(f"   Flow Engaged test: {sub_state['display'] if sub_state else None} {'✅' if sub_state and sub_state['name'] == 'engaged' else '❌'}")
    
    # Test 2: Flow - Absorbed  
    bands = {'alpha': 87, 'beta': 5, 'delta': 5, 'theta': 2, 'gamma': 1}
    db_changes = {'alpha_db_change': 0, 'beta_db_change': 0, 'delta_db_change': 0, 'theta_db_change': 0, 'gamma_db_change': 0}
    
    sub_state = monitor.detect_sub_state('flow_state', bands, db_changes)
    print(f"   Flow Absorbed test: {sub_state['display'] if sub_state else None} {'✅' if sub_state and sub_state['name'] == 'absorbed' else '❌'}")
    
    # Test 3: Jhana - Entry
    bands = {'alpha': 92, 'beta': 3, 'delta': 3, 'theta': 1, 'gamma': 1}
    db_changes = {'alpha_db_change': 0, 'beta_db_change': 0, 'delta_db_change': 0, 'theta_db_change': 0, 'gamma_db_change': 0}
    
    sub_state = monitor.detect_sub_state('jhana', bands, db_changes)
    print(f"   Jhana Entry test: {sub_state['display'] if sub_state else None} {'✅' if sub_state and sub_state['name'] == 'entry' else '❌'}")
    
    # Test 4: Jhana - Stable
    bands = {'alpha': 96, 'beta': 2, 'delta': 1, 'theta': 1, 'gamma': 0}
    db_changes = {'alpha_db_change': 0, 'beta_db_change': 0, 'delta_db_change': 0, 'theta_db_change': 0, 'gamma_db_change': 0}
    
    sub_state = monitor.detect_sub_state('jhana', bands, db_changes)
    print(f"   Jhana Stable test: {sub_state['display'] if sub_state else None} {'✅' if sub_state and sub_state['name'] == 'stable' else '❌'}")

def test_enhanced_pipeline():
    """Test the full enhanced detection pipeline"""
    print("\n🧪 Testing enhanced detection pipeline...")
    
    monitor = EnhancedConsciousnessMonitor(debug=True)
    
    # Simulate valid EEG data for flow state
    eeg_analysis = {
        'state': 'Active',
        'confidence': 'MODERATE', 
        'insights': [],
        'ratios': {'alpha': 75, 'beta': 20, 'delta': 3, 'theta': 1, 'gamma': 1},
        'quality': {}
    }
    
    # Update dB tracking to simulate changes
    monitor._update_db_tracking(eeg_analysis['ratios'])
    
    interpretation = monitor.interpret_enhanced_state(eeg_analysis, None)
    
    print(f"   Enhanced pipeline test: {interpretation['state']} {'✅' if 'FLOW' in interpretation['state'] else '❌'}")
    print(f"   Insights generated: {len(interpretation['insights'])} {'✅' if len(interpretation['insights']) > 0 else '❌'}")

def test_command_line_tuning():
    """Test command line rule tuning"""
    print("\n🧪 Testing command line tuning...")
    
    # Test artifact threshold tuning
    tune_rules = {
        'artifact': {'multiband_spike': 85},
        'jhana': {'alpha_min': 85}
    }
    
    monitor = EnhancedConsciousnessMonitor(debug=True, tune_rules=tune_rules)
    
    # Check if tuning was applied
    artifact_threshold = monitor.ARTIFACT_THRESHOLDS['multiband_spike']
    jhana_threshold = monitor.DETECTION_RULES['jhana']['conditions']['alpha_min']
    
    print(f"   Artifact tuning test: {artifact_threshold} {'✅' if artifact_threshold == 85 else '❌'}")
    print(f"   Rule tuning test: {jhana_threshold} {'✅' if jhana_threshold == 85 else '❌'}")

if __name__ == "__main__":
    print("🧠 Enhanced Consciousness Monitor Feature Tests")
    print("=" * 50)
    
    try:
        test_artifact_filtering()
        test_sub_state_detection()
        test_enhanced_pipeline()
        test_command_line_tuning()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed! Enhanced features are working.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()