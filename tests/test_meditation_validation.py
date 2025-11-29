#!/usr/bin/env python3
"""
Comprehensive Meditation Session Validation Test Suite

This test suite validates the consciousness monitor against the meditation.csv data
using the corrected sample rate and proper data understanding.
"""

import pytest
import numpy as np
import pandas as pd
from consciousness_monitor.data.parsers import DataParser
from consciousness_monitor.data.processors import SignalProcessor
from consciousness_monitor.detection.engine import DetectionEngine
from consciousness_monitor.config.rules import RuleManager

def test_sample_rate_detection():
    """Test that sample rate is correctly detected from meditation.csv"""
    parser = DataParser()
    
    # Test with meditation.csv
    rate = parser.detect_sample_rate('meditation.csv')
    
    # Should detect ~88-90Hz based on unique EEG timestamps
    assert 80 <= rate <= 100, f"Expected ~88Hz, got {rate}Hz"
    print(f"✅ Sample rate correctly detected: {rate:.1f}Hz")

def test_contact_quality_realistic():
    """Test that contact quality values are in realistic range"""
    # Load meditation data
    rows = []
    with open('meditation.csv', 'r') as f:
        for i, line in enumerate(f):
            if i > 5000:  # Limit for testing
                break
            parts = line.strip().split(', ')
            if len(parts) >= 2 and parts[1] == '/muse/optics':
                rows.append(parts)
    
    assert len(rows) > 100, "Should have contact quality data"
    
    # Extract contact values (TP9, AF7, AF8, TP10 in columns 2-5)
    for i, channel in enumerate(['TP9', 'AF7', 'AF8', 'TP10']):
        values = []
        for row in rows:
            if len(row) > i + 2:
                try:
                    val = float(row[i + 2])
                    values.append(val)
                except:
                    pass
        
        if values:
            mean_val = np.mean(values)
            # Contact quality should be in range 8-10 for good connection
            assert 8.0 <= mean_val <= 10.0, f"{channel} contact quality {mean_val:.2f} outside expected range"
            print(f"✅ {channel} contact quality realistic: {mean_val:.2f}")

def test_motion_magnitude_reasonable():
    """Test that motion magnitude is reasonable for meditation"""
    # Load motion data
    rows = []
    with open('meditation.csv', 'r') as f:
        for i, line in enumerate(f):
            if i > 5000:
                break
            parts = line.strip().split(', ')
            if len(parts) >= 5 and parts[1] == '/muse/acc':
                try:
                    x = float(parts[2])
                    y = float(parts[3]) 
                    z = float(parts[4])
                    magnitude = np.sqrt(x**2 + y**2 + z**2)
                    rows.append(magnitude)
                except:
                    pass
    
    assert len(rows) > 100, "Should have motion data"
    
    mean_motion = np.mean(rows)
    std_motion = np.std(rows)
    
    # During meditation, motion should be low and consistent
    assert 0.8 <= mean_motion <= 1.2, f"Motion magnitude {mean_motion:.3f} unexpected"
    assert std_motion <= 0.1, f"Motion variation {std_motion:.3f} too high for meditation"
    
    print(f"✅ Motion magnitude reasonable: {mean_motion:.3f} ± {std_motion:.3f}")

def test_eeg_data_quality():
    """Test that EEG data is in reasonable range"""
    parser = DataParser()
    
    # Get some EEG data
    latest_data, format_type = parser.get_latest_data('meditation.csv', 500)
    assert latest_data is not None, "Should load EEG data"
    
    channels = parser.extract_eeg_channels(latest_data, format_type)
    assert len(channels) == 4, f"Expected 4 channels, got {len(channels)}"
    
    for channel_name, channel_data in channels.items():
        # EEG should be in microvolts, roughly 200-1200 range for good signal
        mean_val = np.mean(channel_data)
        std_val = np.std(channel_data)
        
        assert 200 <= mean_val <= 1200, f"{channel_name}: mean {mean_val:.1f}µV outside expected range"
        assert 10 <= std_val <= 200, f"{channel_name}: std {std_val:.1f}µV outside expected range"
        
        print(f"✅ {channel_name} EEG data quality good: {mean_val:.1f} ± {std_val:.1f} µV")

def test_band_power_calculations():
    """Test band power calculations with corrected sample rate"""
    parser = DataParser()
    
    # Get detected sample rate
    sample_rate = parser.detect_sample_rate('meditation.csv')
    processor = SignalProcessor(sample_rate)
    
    # Get EEG data
    latest_data, format_type = parser.get_latest_data('meditation.csv', 1000)
    channels = parser.extract_eeg_channels(latest_data, format_type)
    
    for channel_name, channel_data in channels.items():
        # Calculate band powers
        band_power = processor.calculate_all_band_powers(channel_data)
        percentages = band_power.as_percentages()
        
        # Band percentages should sum to ~100%
        total = sum(percentages.values())
        assert 99 <= total <= 101, f"{channel_name}: Band percentages sum to {total:.1f}%, not 100%"
        
        # All bands should have some power (no zeros)
        for band, pct in percentages.items():
            assert pct > 0, f"{channel_name}: {band} has zero power"
            assert pct < 95, f"{channel_name}: {band} has {pct:.1f}% (too dominant)"
        
        print(f"✅ {channel_name} band powers valid: Σ={total:.1f}%")

def test_meditation_state_detection():
    """Test that meditation patterns are detected appropriately"""
    parser = DataParser()
    sample_rate = parser.detect_sample_rate('meditation.csv')
    processor = SignalProcessor(sample_rate)
    
    # Initialize detection engine
    rule_manager = RuleManager()
    engine = DetectionEngine(rule_manager, debug=False)
    
    # Get EEG data
    latest_data, format_type = parser.get_latest_data('meditation.csv', 2000)
    channels = parser.extract_eeg_channels(latest_data, format_type)
    
    # Calculate average band powers across channels
    all_band_powers = []
    for channel_data in channels.values():
        band_power = processor.calculate_all_band_powers(channel_data)
        all_band_powers.append(band_power.as_percentages())
    
    # Average across channels
    avg_bands = {}
    for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
        avg_bands[band] = np.mean([bp[band] for bp in all_band_powers])
    
    print(f"📊 Average band powers: {avg_bands}")
    
    # For meditation session, expect certain patterns
    alpha_pct = avg_bands['alpha']
    beta_pct = avg_bands['beta']
    theta_pct = avg_bands['theta']
    
    # Meditation should show some alpha and theta, low beta
    meditation_score = 0
    
    if alpha_pct >= 15:  # Reasonable alpha for meditation
        meditation_score += 1
        print(f"✅ Good alpha activity: {alpha_pct:.1f}%")
    else:
        print(f"⚠️ Low alpha activity: {alpha_pct:.1f}%")
    
    if theta_pct >= 20:  # Good theta for deep states
        meditation_score += 1
        print(f"✅ Good theta activity: {theta_pct:.1f}%")
    
    if beta_pct <= 30:  # Not too much mental chatter
        meditation_score += 1
        print(f"✅ Controlled beta: {beta_pct:.1f}%")
    
    # Should have at least 2/3 meditation indicators
    assert meditation_score >= 2, f"Meditation score {meditation_score}/3 too low for meditation session"
    print(f"✅ Meditation session validated: {meditation_score}/3 indicators")

def test_no_artifacts_during_meditation():
    """Test that artifact detection doesn't trigger excessively during meditation"""
    parser = DataParser()
    sample_rate = parser.detect_sample_rate('meditation.csv')
    processor = SignalProcessor(sample_rate)
    
    # Get EEG data
    latest_data, format_type = parser.get_latest_data('meditation.csv', 2000)
    channels = parser.extract_eeg_channels(latest_data, format_type)
    
    artifact_count = 0
    total_windows = 0
    
    # Test in sliding windows
    window_size = int(sample_rate * 0.75)  # 0.75 second windows
    
    for channel_data in channels.values():
        for i in range(0, len(channel_data) - window_size, window_size // 2):
            window = channel_data[i:i + window_size]
            
            # Calculate band powers for this window
            try:
                band_power = processor.calculate_all_band_powers(window)
                percentages = band_power.as_percentages()
                
                # Check for obvious artifacts
                total_windows += 1
                
                # Single band over 90% is likely artifact
                if any(pct > 90 for pct in percentages.values()):
                    artifact_count += 1
                
                # Impossibly high gamma (>50%) during meditation
                if percentages.get('gamma', 0) > 50:
                    artifact_count += 1
                    
            except Exception as e:
                artifact_count += 1  # Processing error counts as artifact
    
    artifact_rate = artifact_count / total_windows if total_windows > 0 else 0
    
    # Artifact rate should be low during meditation
    assert artifact_rate <= 0.1, f"Artifact rate {artifact_rate*100:.1f}% too high for meditation"
    print(f"✅ Low artifact rate during meditation: {artifact_rate*100:.1f}%")

def run_all_meditation_tests():
    """Run all meditation validation tests"""
    print("🧘 Running Meditation Validation Test Suite")
    print("=" * 60)
    
    tests = [
        test_sample_rate_detection,
        test_contact_quality_realistic,
        test_motion_magnitude_reasonable,
        test_eeg_data_quality,
        test_band_power_calculations,
        test_meditation_state_detection,
        test_no_artifacts_during_meditation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"\n🧪 Running {test.__name__}...")
            test()
            passed += 1
            print(f"✅ {test.__name__} PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All meditation validation tests PASSED!")
        return True
    else:
        print("⚠️ Some tests failed - system needs fixes")
        return False

if __name__ == "__main__":
    success = run_all_meditation_tests()