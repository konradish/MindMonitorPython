#!/usr/bin/env python3
"""
Unit tests for EEG signal processing
TDD approach to validate consciousness monitor
"""

import pytest
import numpy as np
import pandas as pd
from scipy import signal
import os
import sys

# Import the consciousness monitor
from consciousness_monitor import ConsciousnessMonitor

class TestSignalProcessing:
    """Test EEG signal processing functions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.monitor = ConsciousnessMonitor(
            csv_file="test_data.csv",
            window_seconds=2,
            update_interval=1.0
        )
        
    def test_actual_csv_data_ranges(self):
        """Test that actual CSV data is in expected microvolt range"""
        if not os.path.exists("OSC-Python-Recording.csv"):
            pytest.skip("No actual CSV data available")
            
        df = pd.read_csv("OSC-Python-Recording.csv")
        if len(df) == 0:
            pytest.skip("Empty CSV file")
            
        # Check raw values are in microvolt range (200-1200)
        for i, channel in enumerate(['TP9', 'AF7', 'AF8', 'TP10']):
            if i+1 < len(df.columns):
                channel_data = df.iloc[:, i+1].dropna()
                if len(channel_data) > 0:
                    min_val = channel_data.min()
                    max_val = channel_data.max()
                    mean_val = channel_data.mean()
                    
                    print(f"\n{channel} data range: {min_val:.1f} to {max_val:.1f}, mean: {mean_val:.1f}")
                    
                    # These should be microvolts already (200-1200 typical range)
                    assert 50 < min_val < 2000, f"{channel} min value {min_val} outside expected microvolt range"
                    assert 100 < max_val < 5000, f"{channel} max value {max_val} outside expected microvolt range"
    
    def test_preprocess_signal_no_conversion(self):
        """Test that preprocessing doesn't incorrectly convert already-microvolt data"""
        # Simulate typical Mind Monitor microvolt values
        raw_microvolts = np.array([650, 750, 680, 720, 690, 800, 670, 640] * 64)  # 512 samples
        
        processed = self.monitor.preprocess_signal(raw_microvolts)
        
        # After preprocessing, values should still be in reasonable microvolt range
        # Not negative (which would happen with incorrect ADC conversion)
        assert not np.any(processed < -500), "Preprocessed values should not be extremely negative"
        assert not np.all(processed == 0), "Preprocessing should not zero out all values"
        
        # Mean should be close to zero after DC removal
        assert abs(np.mean(processed)) < 10, "DC offset should be removed"
        
    def test_get_band_power_realistic_values(self):
        """Test band power calculation with realistic EEG data"""
        # Generate synthetic EEG signal with known frequency content
        fs = 256  # Sample rate
        t = np.linspace(0, 2, fs * 2)  # 2 seconds
        
        # Create signal with strong alpha (10 Hz) component
        alpha_signal = 100 * np.sin(2 * np.pi * 10 * t)  # 10 Hz, 100 µV amplitude
        theta_signal = 50 * np.sin(2 * np.pi * 6 * t)    # 6 Hz, 50 µV amplitude  
        noise = 20 * np.random.randn(len(t))              # Noise
        
        test_signal = alpha_signal + theta_signal + noise + 600  # Add DC offset like real EEG
        
        # Calculate band powers
        alpha_power = self.monitor.get_band_power(test_signal, 8, 13)
        theta_power = self.monitor.get_band_power(test_signal, 4, 8)
        beta_power = self.monitor.get_band_power(test_signal, 13, 30)
        delta_power = self.monitor.get_band_power(test_signal, 0.5, 4)
        
        print(f"\nSynthetic signal band powers:")
        print(f"Alpha (should be highest): {alpha_power:.2f}")
        print(f"Theta (should be moderate): {theta_power:.2f}")
        print(f"Beta (should be low): {beta_power:.2f}")
        print(f"Delta (should be low): {delta_power:.2f}")
        
        # Alpha should be highest since we put most energy there
        assert alpha_power > theta_power, "Alpha should be higher than theta for this test signal"
        assert alpha_power > beta_power, "Alpha should be higher than beta for this test signal"
        
    def test_consciousness_analysis_with_real_data(self):
        """Test consciousness analysis with actual CSV data"""
        if not os.path.exists("OSC-Python-Recording.csv"):
            pytest.skip("No actual CSV data available")
            
        df = pd.read_csv("OSC-Python-Recording.csv")
        if len(df) < 512:  # Need enough samples
            pytest.skip("Not enough CSV data for analysis")
            
        # Take a window of data
        window_data = df.tail(512)
        analysis = self.monitor.analyze_consciousness_state(window_data)
        
        if analysis is None:
            pytest.fail("Analysis returned None - this shouldn't happen with valid data")
            
        print(f"\nReal data analysis:")
        print(f"State: {analysis['state']}")
        print(f"Confidence: {analysis['confidence']}")
        print("Band ratios:")
        for band, ratio in analysis['ratios'].items():
            print(f"  {band}: {ratio:.3f} ({ratio*100:.1f}%)")
            
        # Sanity checks
        total_ratio = sum(analysis['ratios'].values())
        assert 0.95 < total_ratio < 1.05, f"Band ratios should sum to ~1.0, got {total_ratio}"
        
        # No band should be 100% (that indicates a bug)
        for band, ratio in analysis['ratios'].items():
            assert ratio < 0.95, f"{band} shows {ratio*100:.1f}% - this indicates a processing error"
            assert ratio >= 0, f"{band} shows negative ratio {ratio} - this indicates a processing error"
            
        # At least some bands should have measurable power
        non_zero_bands = sum(1 for ratio in analysis['ratios'].values() if ratio > 0.01)
        assert non_zero_bands >= 3, "At least 3 bands should have measurable power in real EEG"

    def test_debug_band_power_calculation(self):
        """Detailed debugging of band power calculation"""
        if not os.path.exists("OSC-Python-Recording.csv"):
            pytest.skip("No actual CSV data available")
            
        df = pd.read_csv("OSC-Python-Recording.csv")
        if len(df) < 512:
            pytest.skip("Not enough data")
            
        # Get recent data for one channel
        channel_data = df.iloc[-512:, 1].values  # TP9 channel, last 512 samples
        
        print(f"\nDebugging channel data:")
        print(f"Raw data range: {channel_data.min():.1f} to {channel_data.max():.1f}")
        print(f"Raw data mean: {channel_data.mean():.1f}")
        print(f"Raw data std: {channel_data.std():.1f}")
        
        # Test preprocessing step by step
        preprocessed = self.monitor.preprocess_signal(channel_data)
        print(f"After preprocessing range: {preprocessed.min():.1f} to {preprocessed.max():.1f}")
        print(f"After preprocessing mean: {preprocessed.mean():.3f}")
        print(f"After preprocessing std: {preprocessed.std():.1f}")
        
        # Test band power calculation
        for band_name, (low, high) in self.monitor.bands.items():
            power = self.monitor.get_band_power(channel_data, low, high)
            print(f"{band_name} ({low}-{high} Hz): {power:.6f}")
            
        # The issue might be in the band power calculation or normalization
        assert not np.isnan(preprocessed).any(), "Preprocessing should not produce NaN values"
        assert not np.isinf(preprocessed).any(), "Preprocessing should not produce infinite values"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])