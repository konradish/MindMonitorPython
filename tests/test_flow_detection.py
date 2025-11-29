#!/usr/bin/env python3
"""Test script to validate Flow State vs Jhana detection"""

import sys
sys.path.insert(0, '.')

from consciousness_monitor import EnhancedConsciousnessMonitor

def test_detection_rules():
    """Test the new Flow State and refined Jhana detection"""
    
    # Create monitor instance
    monitor = EnhancedConsciousnessMonitor(debug=True, konrad_mode=True)
    
    # Test cases based on the problem description
    test_cases = [
        {
            "name": "Sudoku Flow State",
            "ratios": {"alpha": 80, "beta": 12, "delta": 5, "theta": 2, "gamma": 1},
            "expected": "FLOW STATE"
        },
        {
            "name": "Real Jhana State", 
            "ratios": {"alpha": 95, "beta": 3, "delta": 1, "theta": 1, "gamma": 0},
            "expected": "JHANA"
        },
        {
            "name": "High Alpha Flow",
            "ratios": {"alpha": 85, "beta": 10, "delta": 3, "theta": 1, "gamma": 1}, 
            "expected": "FLOW STATE"
        },
        {
            "name": "Near-Pure Consciousness",
            "ratios": {"alpha": 92, "beta": 5, "delta": 2, "theta": 1, "gamma": 0},
            "expected": "JHANA"
        },
        {
            "name": "Regular Relaxed",
            "ratios": {"alpha": 45, "beta": 20, "delta": 25, "theta": 8, "gamma": 2},
            "expected": "RELAXED"
        },
        {
            "name": "Edge Case - Low Alpha Flow",
            "ratios": {"alpha": 70, "beta": 15, "delta": 10, "theta": 3, "gamma": 2},
            "expected": "FLOW STATE"
        }
    ]
    
    print("🧪 Testing Flow State vs Jhana Detection")
    print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print(f"Input: Alpha={test['ratios']['alpha']}% Beta={test['ratios']['beta']}% Delta={test['ratios']['delta']}% Theta={test['ratios']['theta']}% Gamma={test['ratios']['gamma']}%")
        
        # Test the detection
        db_changes = {'delta_db_change': 0, 'beta_db_change': 0, 'alpha_db_change': 0, 'gamma_db_change': 0}
        result = monitor._evaluate_detection_rules(test['ratios'], db_changes)
        
        if result:
            detected_state = result['state']
            emoji = result['emoji']
            insights = result['insights']
            
            print(f"Detected: {detected_state} {emoji}")
            if insights:
                print(f"Insights: {insights[0]}")
            
            # Check if detection matches expected
            if test['expected'] in detected_state:
                print("✅ PASS - Correct detection")
            else:
                print(f"❌ FAIL - Expected {test['expected']}, got {detected_state}")
        else:
            print("❌ FAIL - No state detected")
        
        print("-" * 40)
    
    print("\n🎯 Test Summary")
    print("Expected behavior:")
    print("- Sudoku concentration (80-85% alpha, 10-15% beta) → FLOW STATE")
    print("- Pure meditation (90%+ alpha, <10% beta) → JHANA") 
    print("- Regular relaxation (40-70% alpha) → RELAXED")

if __name__ == "__main__":
    test_detection_rules()