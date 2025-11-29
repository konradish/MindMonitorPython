#!/usr/bin/env python3
"""
Test script for the refactored consciousness monitor.
This verifies backward compatibility and basic functionality.
"""

import sys
import os
import numpy as np
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, '/mnt/c/projects/MindMonitorPython')

def test_imports():
    """Test that all modules can be imported successfully."""
    print("🔍 Testing imports...")
    
    try:
        # Test main import (backward compatibility)
        from consciousness_monitor import EnhancedConsciousnessMonitor
        print("✅ Main class import successful")
        
        # Test modular imports
        from consciousness_monitor.config import RuleManager, ArtifactThresholds, Settings
        from consciousness_monitor.data import DataParser, SignalProcessor
        from consciousness_monitor.detection import DetectionEngine, TherapeuticPatterns
        from consciousness_monitor.ui import DisplayManager, CommandInterface
        print("✅ All modular imports successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_configuration_loading():
    """Test configuration loading from JSON files."""
    print("\n🔍 Testing configuration loading...")
    
    try:
        from consciousness_monitor.config import RuleManager, ArtifactThresholds
        
        # Test rule manager
        rule_manager = RuleManager()
        rules = rule_manager.get_detection_rules()
        print(f"✅ Loaded {len(rules)} detection rules")
        
        # Test artifact thresholds
        thresholds = ArtifactThresholds()
        threshold_dict = thresholds.get_all_thresholds()
        print(f"✅ Loaded {len(threshold_dict)} artifact thresholds")
        
        # Test rule version
        version = rule_manager.get_version()
        print(f"✅ Rule version: {version}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

def test_signal_processing():
    """Test signal processing functionality."""
    print("\n🔍 Testing signal processing...")
    
    try:
        from consciousness_monitor.data import SignalProcessor
        from consciousness_monitor.data.models import BandPower
        
        # Create test signal (simulated EEG)
        sample_rate = 256
        duration = 1.0  # 1 second
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Create a test signal with different frequency components
        signal = (
            0.5 * np.sin(2 * np.pi * 1 * t) +    # 1 Hz (delta)
            0.3 * np.sin(2 * np.pi * 6 * t) +    # 6 Hz (theta)
            0.8 * np.sin(2 * np.pi * 10 * t) +   # 10 Hz (alpha)
            0.2 * np.sin(2 * np.pi * 20 * t) +   # 20 Hz (beta)
            0.1 * np.sin(2 * np.pi * 40 * t)     # 40 Hz (gamma)
        )
        
        # Add some noise
        signal += 0.1 * np.random.randn(len(signal))
        
        # Process signal
        processor = SignalProcessor(sample_rate)
        band_power = processor.calculate_all_band_powers(signal)
        
        print(f"✅ Band powers calculated:")
        print(f"   Delta: {band_power.delta:.3f}")
        print(f"   Theta: {band_power.theta:.3f}")
        print(f"   Alpha: {band_power.alpha:.3f}")
        print(f"   Beta: {band_power.beta:.3f}")
        print(f"   Gamma: {band_power.gamma:.3f}")
        
        # Test percentages
        percentages = band_power.as_percentages()
        total = sum(percentages.values())
        print(f"✅ Percentage total: {total:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Signal processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_detection_engine():
    """Test the detection engine."""
    print("\n🔍 Testing detection engine...")
    
    try:
        from consciousness_monitor.config import RuleManager, ArtifactThresholds
        from consciousness_monitor.detection import DetectionEngine
        from consciousness_monitor.data.models import BandPower
        
        # Create detection engine
        rule_manager = RuleManager()
        thresholds = ArtifactThresholds()
        engine = DetectionEngine(rule_manager, thresholds, debug=True)
        
        # Test with relaxed state (high alpha)
        relaxed_bands = BandPower(
            delta=0.15,
            theta=0.20,
            alpha=0.50,  # High alpha for relaxed state
            beta=0.10,
            gamma=0.05
        )
        
        result = engine.analyze_bands(relaxed_bands, datetime.now())
        print(f"✅ Detected state: {result.state}")
        print(f"   Emoji: {result.emoji}")
        print(f"   Insights: {len(result.insights)} insights")
        
        # Test with security guard pattern (high beta spike)
        security_bands = BandPower(
            delta=0.35,  # High delta for security guard
            theta=0.15,
            alpha=0.20,
            beta=0.25,   # High beta
            gamma=0.05
        )
        
        result2 = engine.analyze_bands(security_bands, datetime.now())
        print(f"✅ Second detection: {result2.state}")
        
        return True
        
    except Exception as e:
        print(f"❌ Detection engine failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test backward compatibility with original API."""
    print("\n🔍 Testing backward compatibility...")
    
    try:
        # Test original constructor parameters
        from consciousness_monitor import EnhancedConsciousnessMonitor
        
        monitor = EnhancedConsciousnessMonitor(
            csv_file="test.csv",
            window_seconds=0.75,
            update_interval=1.0,
            debug=True,
            konrad_mode=True
        )
        
        print("✅ Monitor created with original parameters")
        print(f"   Sample rate: {monitor.sample_rate}")
        print(f"   Window samples: {monitor.window_samples}")
        print(f"   Debug mode: {monitor.debug}")
        print(f"   Konrad mode: {monitor.konrad_mode}")
        
        # Test that essential methods exist
        assert hasattr(monitor, 'monitor_realtime'), "monitor_realtime method missing"
        assert hasattr(monitor, 'analyze_file'), "analyze_file method missing"
        assert hasattr(monitor, 'analyze_eeg_window'), "analyze_eeg_window method missing"
        
        print("✅ All essential methods available")
        
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_display_system():
    """Test the display system."""
    print("\n🔍 Testing display system...")
    
    try:
        from consciousness_monitor.ui import DisplayManager
        from consciousness_monitor.data.models import AnalysisResult, BandPower
        
        display = DisplayManager(show_bands=True, show_insights=True)
        
        # Create test result
        result = AnalysisResult(
            timestamp=datetime.now(),
            state="RELAXED",
            emoji="🌊",
            insights=["😌 Excellent regulation state", "🧠 Good alpha activity"],
            band_percentages={'delta': 15, 'theta': 20, 'alpha': 45, 'beta': 15, 'gamma': 5},
            db_changes={'delta': 0.5, 'theta': -0.2, 'alpha': 2.1, 'beta': -1.0, 'gamma': 0.1}
        )
        
        print("✅ Display test result:")
        display.display_analysis_result(result)
        
        return True
        
    except Exception as e:
        print(f"❌ Display system failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🧠 Testing Refactored Consciousness Monitor")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration_loading,
        test_signal_processing,
        test_detection_engine,
        test_backward_compatibility,
        test_display_system
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"🧠 TEST RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✅ ALL TESTS PASSED - Refactoring successful!")
    else:
        print(f"❌ {failed} tests failed - Issues need to be addressed")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)