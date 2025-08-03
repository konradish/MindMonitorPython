#!/usr/bin/env python3
"""
Test script for the Enhanced Consciousness Monitor v4 - Therapeutic Edition
Demonstrates all fixed bugs and new therapeutic pattern detection capabilities
"""

import sys
import os
sys.path.append('/mnt/c/projects/MindMonitorPython')

from consciousness_monitor.main import EnhancedConsciousnessMonitor

def test_therapeutic_patterns():
    """Test all therapeutic EEG patterns"""
    
    print("🧠 ENHANCED CONSCIOUSNESS MONITOR v5 - MODULAR ARCHITECTURE")
    print("🧪 Testing Modular EEG Detection System")
    print("=" * 60)
    
    # Initialize monitor with Konrad's personalized rules
    monitor = EnhancedConsciousnessMonitor(
        debug=False, 
        konrad_mode=True,
        csv_file="mind_monitor_complete.csv"
    )
    
    print(f"✅ Initialization successful")
    print(f"🎯 Rule Version: {monitor.RULE_VERSION}")
    print(f"🔧 Available rules: {len(monitor.DETECTION_RULES)}")
    print()
    
    # Test cases covering all therapeutic patterns
    test_cases = [
        {
            'name': '🧘 Jhana/Transcendent State', 
            'description': 'Alpha >80%, Beta <15% - Deep meditation',
            'bands': {'alpha': 92, 'beta': 5, 'delta': 2, 'theta': 1, 'gamma': 0},
            'expected': 'JHANA'
        },
        {
            'name': '🌟 Hopeful Part Active', 
            'description': 'Alpha 75-80%, Beta <15% - Optimistic consciousness',
            'bands': {'alpha': 78, 'beta': 12, 'delta': 8, 'theta': 2, 'gamma': 0},
            'expected': 'HOPEFUL PART'
        },
        {
            'name': '💝 Young Part Connected', 
            'description': 'Delta >35%, Alpha 30-40%, Theta >15% - Vulnerable state',
            'bands': {'alpha': 34, 'beta': 8, 'delta': 44, 'theta': 23, 'gamma': 1},
            'expected': 'YOUNG PART'
        },
        {
            'name': '🛡️ Cautious Part Active', 
            'description': 'Alpha 50-70%, Delta >15%, Beta >15% - Protective awareness',
            'bands': {'alpha': 54, 'beta': 19, 'delta': 20, 'theta': 5, 'gamma': 2},
            'expected': 'CAUTIOUS PART'
        },
        {
            'name': '🚨 Security Guard (Normal)', 
            'description': 'Low alpha + dB spikes - Threat detection',
            'bands': {'alpha': 15, 'beta': 35, 'delta': 25, 'theta': 15, 'gamma': 10},
            'db_changes': {'delta_db_change': 7.0, 'beta_db_change': 8.0, 'alpha_db_change': -3.0},
            'expected': 'SECURITY GUARD'
        },
        {
            'name': '😲 Startled Response', 
            'description': 'Beta spike (48%) + maintained alpha (42%) - Healthy startle',
            'bands': {'alpha': 42, 'beta': 48, 'delta': 8, 'theta': 2, 'gamma': 0},
            'db_changes': {'beta_db_change': 3.0, 'alpha_db_change': 0.5, 'delta_db_change': 0.2},
            'expected': 'STARTLED'
        },
        {
            'name': '🧘 Meditation Exemption', 
            'description': 'High alpha (85%) + dB spikes - Should NOT trigger security guard',
            'bands': {'alpha': 85, 'beta': 8, 'delta': 5, 'theta': 2, 'gamma': 0},
            'db_changes': {'delta_db_change': 7.0, 'beta_db_change': 8.0, 'alpha_db_change': -3.0},
            'expected': 'JHANA'  # Should be jhana, not security guard
        },
    ]
    
    print("🧪 TESTING THERAPEUTIC PATTERNS:")
    print("-" * 60)
    
    passed = 0
    total = len(test_cases)
    
    for i, test in enumerate(test_cases, 1):
        # Prepare test data
        bands = test['bands']
        db_changes = test.get('db_changes', {
            'delta_db_change': 0, 'beta_db_change': 0, 
            'alpha_db_change': 0, 'gamma_db_change': 0
        })
        
        # Run detection
        result = monitor._evaluate_detection_rules(bands, db_changes)
        
        # Check result
        if result and test['expected'] in result['state']:
            status = "✅ PASS"
            passed += 1
            detected_state = f"{result['state']} {result['emoji']}"
            insight = result['insights'][0] if result['insights'] else "No insights"
        elif result:
            status = "❌ FAIL"
            detected_state = f"{result['state']} {result['emoji']} (expected {test['expected']})"
            insight = "Wrong detection"
        else:
            status = "❌ FAIL"
            detected_state = f"No detection (expected {test['expected']})"
            insight = "No detection"
        
        print(f"{i}. {test['name']}")
        print(f"   {test['description']}")
        print(f"   Result: {detected_state}")
        print(f"   Status: {status}")
        if result and result['insights']:
            print(f"   Insight: {insight}")
        print()
    
    # Summary
    print("=" * 60)
    print(f"🎯 TEST RESULTS: {passed}/{total} patterns working correctly")
    
    if passed == total:
        print("✅ ALL THERAPEUTIC PATTERNS WORKING PERFECTLY!")
        print("🧠 Ready for consciousness monitoring and therapeutic work")
        print("🔧 Maintainable architecture enables easy threshold tuning")
        print("🎯 Bug fixes successful: Jhana detection, meditation exemption, missing values")
    else:
        print("❌ Some patterns need adjustment")
    
    print()
    print("🚀 USAGE EXAMPLES:")
    print("   Basic monitoring:    uv run python consciousness_monitor.py --konrad-mode")
    print("   Debug mode:          uv run python consciousness_monitor.py --debug")
    print("   Tune thresholds:     uv run python consciousness_monitor.py --tune-rule jhana.alpha_min=85")
    print("   Load custom rules:   uv run python consciousness_monitor.py --load-rules my_rules.json")
    print("   Analyze recording:   uv run python consciousness_monitor.py --analyze --file recording.csv")

if __name__ == "__main__":
    test_therapeutic_patterns()