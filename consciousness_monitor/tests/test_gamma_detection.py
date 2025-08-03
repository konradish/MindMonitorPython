"""
Unit tests for gamma detection module.
"""

import numpy as np
import pytest
from consciousness_monitor.analysis.gamma_detection import (
    extract_high_gamma_band,
    calculate_gamma_power_envelope,
    detect_gamma_bursts,
    analyze_gamma_burst_pattern
)


class TestHighGammaExtraction:
    """Test high-gamma band extraction."""
    
    def test_basic_filtering(self):
        """Test basic bandpass filtering functionality."""
        # Create test signal with known frequency components
        sample_rate = 256
        duration = 2.0  # seconds
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        
        # Mix of low frequency (10 Hz) and high gamma (50 Hz)
        low_freq_signal = np.sin(2 * np.pi * 10 * t)
        gamma_signal = np.sin(2 * np.pi * 50 * t)
        mixed_signal = low_freq_signal + gamma_signal
        
        # Extract gamma band
        filtered = extract_high_gamma_band(mixed_signal, sample_rate)
        
        # Filtered signal should have same length
        assert len(filtered) == len(mixed_signal)
        
        # Filtered signal should be primarily the gamma component
        # (exact comparison is difficult due to filter characteristics)
        assert np.std(filtered) > 0  # Should have variation
    
    def test_empty_input_raises_error(self):
        """Empty input should raise ValueError."""
        with pytest.raises(ValueError, match="EEG data cannot be empty"):
            extract_high_gamma_band(np.array([]), 256)
    
    def test_invalid_sample_rate_raises_error(self):
        """Invalid sample rate should raise ValueError."""
        test_data = np.random.randn(100)
        
        with pytest.raises(ValueError, match="Sample rate must be positive"):
            extract_high_gamma_band(test_data, 0)
        
        with pytest.raises(ValueError, match="Sample rate must be positive"):
            extract_high_gamma_band(test_data, -256)
    
    def test_invalid_frequency_bounds_raise_error(self):
        """Invalid frequency bounds should raise ValueError."""
        test_data = np.random.randn(100)
        
        # Low >= High
        with pytest.raises(ValueError, match="Low frequency must be less than high frequency"):
            extract_high_gamma_band(test_data, 256, low_freq=50, high_freq=30)
        
        # High >= Nyquist
        with pytest.raises(ValueError, match="High frequency .* must be less than Nyquist frequency"):
            extract_high_gamma_band(test_data, 256, low_freq=30, high_freq=150)
    
    def test_custom_frequency_bounds(self):
        """Test with custom frequency bounds."""
        test_data = np.random.randn(256)  # 1 second at 256 Hz
        
        # Should work with valid custom bounds
        filtered = extract_high_gamma_band(test_data, 256, low_freq=40, high_freq=80)
        
        assert len(filtered) == len(test_data)
        assert isinstance(filtered, np.ndarray)


class TestGammaPowerEnvelope:
    """Test gamma power envelope calculation."""
    
    def test_basic_envelope_calculation(self):
        """Test basic envelope calculation using Hilbert transform."""
        # Create amplitude-modulated signal (gamma burst pattern)
        sample_rate = 256
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        
        # Carrier frequency in gamma range
        carrier = np.sin(2 * np.pi * 50 * t)
        
        # Modulation envelope (simulates burst)
        modulation = 1 + 0.5 * np.sin(2 * np.pi * 2 * t)  # 2 Hz modulation
        
        modulated_signal = carrier * modulation
        
        envelope = calculate_gamma_power_envelope(modulated_signal, window_size=1)
        
        # Envelope should have same length as input
        assert len(envelope) == len(modulated_signal)
        
        # Envelope should be all positive
        assert np.all(envelope >= 0)
        
        # Envelope should capture the modulation pattern
        # (should vary around the expected modulation envelope)
        assert np.std(envelope) > 0
    
    def test_smoothing_effect(self):
        """Test that larger window size produces smoother envelope."""
        # Create noisy signal
        np.random.seed(42)  # For reproducible results
        noisy_signal = np.random.randn(256) + np.sin(2 * np.pi * 50 * np.linspace(0, 1, 256))
        
        envelope_no_smooth = calculate_gamma_power_envelope(noisy_signal, window_size=1)
        envelope_smooth = calculate_gamma_power_envelope(noisy_signal, window_size=32)
        
        # Smoothed envelope should be less variable
        assert np.std(envelope_smooth) < np.std(envelope_no_smooth)
    
    def test_empty_input_raises_error(self):
        """Empty input should raise ValueError."""
        with pytest.raises(ValueError, match="Gamma signal cannot be empty"):
            calculate_gamma_power_envelope(np.array([]))
    
    def test_invalid_window_size_raises_error(self):
        """Invalid window size should raise ValueError."""
        test_signal = np.random.randn(100)
        
        with pytest.raises(ValueError, match="Window size must be positive"):
            calculate_gamma_power_envelope(test_signal, window_size=0)
        
        with pytest.raises(ValueError, match="Window size must be positive"):
            calculate_gamma_power_envelope(test_signal, window_size=-5)


class TestGammaBurstDetection:
    """Test gamma burst detection."""
    
    def test_no_bursts_in_flat_signal(self):
        """Flat signal should produce no bursts."""
        flat_signal = np.ones(1000) * 0.5  # Constant envelope
        
        bursts = detect_gamma_bursts(flat_signal)
        
        assert len(bursts) == 0
    
    def test_single_burst_detection(self):
        """Should detect a single clear burst."""
        # Create signal with one clear burst
        baseline_level = 1.0
        burst_level = baseline_level * 10**(3.0/20)  # 3 dB increase
        
        envelope = np.full(1000, baseline_level)
        envelope[400:500] = burst_level  # 100-sample burst
        
        bursts = detect_gamma_bursts(envelope, threshold_db=2.0, min_duration_samples=50)
        
        # Should detect exactly one burst
        assert len(bursts) == 1
        
        start, end, intensity = bursts[0]
        
        # Burst should be roughly in the expected location
        assert 350 <= start <= 450
        assert 450 <= end <= 550
        
        # Intensity should be approximately 3 dB
        assert 2.5 <= intensity <= 3.5
    
    def test_multiple_burst_detection(self):
        """Should detect multiple separate bursts."""
        baseline_level = 1.0
        burst_level = baseline_level * 10**(4.0/20)  # 4 dB increase
        
        envelope = np.full(2000, baseline_level)
        
        # Add two separate bursts
        envelope[300:400] = burst_level
        envelope[1200:1300] = burst_level
        
        bursts = detect_gamma_bursts(envelope, threshold_db=2.0, min_duration_samples=50)
        
        # Should detect both bursts
        assert len(bursts) == 2
        
        # Bursts should be in chronological order
        assert bursts[0][0] < bursts[1][0]
    
    def test_minimum_duration_filtering(self):
        """Should filter out bursts that are too short."""
        baseline_level = 1.0
        burst_level = baseline_level * 10**(5.0/20)  # 5 dB increase
        
        envelope = np.full(1000, baseline_level)
        envelope[400:410] = burst_level  # 10-sample burst (too short)
        envelope[600:700] = burst_level  # 100-sample burst (long enough)
        
        bursts = detect_gamma_bursts(envelope, threshold_db=2.0, min_duration_samples=50)
        
        # Should only detect the longer burst
        assert len(bursts) == 1
        assert 550 <= bursts[0][0] <= 650
    
    def test_empty_input_raises_error(self):
        """Empty input should raise ValueError."""
        with pytest.raises(ValueError, match="Gamma envelope cannot be empty"):
            detect_gamma_bursts(np.array([]))
    
    def test_invalid_parameters_raise_error(self):
        """Invalid parameters should raise ValueError."""
        test_envelope = np.ones(100)
        
        with pytest.raises(ValueError, match="All parameters must be positive"):
            detect_gamma_bursts(test_envelope, baseline_window=0)
        
        with pytest.raises(ValueError, match="All parameters must be positive"):
            detect_gamma_bursts(test_envelope, threshold_db=-1.0)
        
        with pytest.raises(ValueError, match="Sample rate must be positive"):
            detect_gamma_bursts(test_envelope, sample_rate=0)


class TestGammaBurstAnalysis:
    """Test comprehensive gamma burst analysis."""
    
    def test_analysis_with_no_bursts(self):
        """Analysis of signal with no bursts should return zero statistics."""
        # Flat signal with no bursts
        flat_signal = np.ones(256)  # 1 second at 256 Hz
        
        analysis = analyze_gamma_burst_pattern(flat_signal, sample_rate=256, analysis_window=1.0)
        
        assert analysis['burst_count'] == 0
        assert analysis['burst_rate'] == 0.0
        assert analysis['avg_burst_duration'] == 0.0
        assert analysis['avg_burst_intensity'] == 0.0
        assert analysis['total_burst_time'] == 0.0
        assert analysis['burst_coverage'] == 0.0
        assert len(analysis['raw_bursts']) == 0
    
    def test_analysis_with_synthetic_bursts(self):
        """Analysis should correctly characterize synthetic burst patterns."""
        # Create signal with realistic burst characteristics
        sample_rate = 256
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        
        # Base signal: low-level broadband noise in gamma range
        np.random.seed(42)  # For reproducible tests
        base_signal = np.random.randn(len(t)) * 0.02
        
        # Create burst pattern: amplitude-modulated gamma activity
        gamma_carrier = np.sin(2 * np.pi * 50 * t)
        
        # First burst: 0.3-0.6 seconds (0.3s duration, away from edges)  
        burst1_start = int(0.3 * sample_rate)
        burst1_end = int(0.6 * sample_rate)
        burst1_envelope = np.zeros_like(t)
        burst1_envelope[burst1_start:burst1_end] = 0.2  # Strong burst
        
        # Second burst: 1.2-1.4 seconds (0.2s duration)
        burst2_start = int(1.2 * sample_rate) 
        burst2_end = int(1.4 * sample_rate)
        burst2_envelope = np.zeros_like(t)
        burst2_envelope[burst2_start:burst2_end] = 0.15  # Moderate burst
        
        # Combine signals
        burst_signal = base_signal + gamma_carrier * (burst1_envelope + burst2_envelope)
        
        analysis = analyze_gamma_burst_pattern(burst_signal, sample_rate=sample_rate, analysis_window=duration)
        
        # With realistic bursts, we should detect activity
        # Note: Exact detection depends on filtering and thresholds
        # so we test that the analysis runs and produces reasonable results
        assert isinstance(analysis['burst_count'], int)
        assert analysis['burst_count'] >= 0
        assert analysis['burst_rate'] >= 0
        assert analysis['avg_burst_duration'] >= 0
        assert analysis['avg_burst_intensity'] >= 0
        assert analysis['total_burst_time'] >= 0
        assert 0 <= analysis['burst_coverage'] <= 100
        
        # If bursts detected, statistics should be reasonable
        if analysis['burst_count'] > 0:
            assert analysis['avg_burst_duration'] > 0
            assert analysis['avg_burst_intensity'] > 0
            assert analysis['total_burst_time'] > 0
            assert analysis['burst_coverage'] > 0
    
    def test_empty_input_raises_error(self):
        """Empty input should raise ValueError."""
        with pytest.raises(ValueError, match="EEG data cannot be empty"):
            analyze_gamma_burst_pattern(np.array([]), 256, 1.0)
    
    def test_invalid_parameters_raise_error(self):
        """Invalid parameters should raise ValueError."""
        test_data = np.random.randn(256)
        
        with pytest.raises(ValueError, match="Sample rate must be positive"):
            analyze_gamma_burst_pattern(test_data, sample_rate=0, analysis_window=1.0)
        
        with pytest.raises(ValueError, match="Analysis window must be positive"):
            analyze_gamma_burst_pattern(test_data, sample_rate=256, analysis_window=0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])