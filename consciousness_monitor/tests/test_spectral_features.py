"""
Unit tests for spectral features module.
"""

import numpy as np
import pytest
from consciousness_monitor.analysis.spectral_features import (
    calculate_spectral_entropy,
    calculate_frequency_peak_instability,
    calculate_spectral_centroid,
    calculate_spectral_rolloff
)


class TestSpectralEntropy:
    """Test spectral entropy calculations."""
    
    def test_uniform_distribution_max_entropy(self):
        """Uniform distribution should have maximum entropy."""
        # Uniform power across all frequencies
        uniform_spectrum = np.ones(10)
        entropy = calculate_spectral_entropy(uniform_spectrum)
        
        # For uniform distribution, entropy = log2(N)
        expected = np.log2(10)
        assert abs(entropy - expected) < 1e-10
    
    def test_single_peak_low_entropy(self):
        """Single frequency peak should have low entropy."""
        # All power concentrated in one frequency
        peaked_spectrum = np.zeros(10)
        peaked_spectrum[5] = 1.0
        entropy = calculate_spectral_entropy(peaked_spectrum)
        
        # Single peak should have zero entropy
        assert entropy == 0.0
    
    def test_empty_spectrum_raises_error(self):
        """Empty spectrum should raise ValueError."""
        with pytest.raises(ValueError, match="Power spectrum cannot be empty"):
            calculate_spectral_entropy(np.array([]))
    
    def test_negative_values_raise_error(self):
        """Negative power values should raise ValueError."""
        with pytest.raises(ValueError, match="Power spectrum cannot contain negative values"):
            calculate_spectral_entropy(np.array([1, -1, 2]))
    
    def test_zero_spectrum_returns_zero(self):
        """All-zero spectrum should return zero entropy."""
        zero_spectrum = np.zeros(5)
        entropy = calculate_spectral_entropy(zero_spectrum)
        assert entropy == 0.0
    
    def test_normalize_flag(self):
        """Test with and without normalization."""
        spectrum = np.array([2, 4, 6])
        
        # Both should give same result since we always normalize internally
        entropy_norm = calculate_spectral_entropy(spectrum, normalize=True)
        entropy_no_norm = calculate_spectral_entropy(spectrum, normalize=False)
        
        assert entropy_norm == entropy_no_norm


class TestFrequencyPeakInstability:
    """Test frequency peak instability calculations."""
    
    def test_single_measurement_zero_instability(self):
        """First measurement should have zero instability."""
        power = np.array([1, 3, 2, 1])
        freqs = np.array([1, 2, 3, 4])
        
        peak_freq, instability = calculate_frequency_peak_instability(power, freqs)
        
        assert peak_freq == 2.0  # Peak at index 1
        assert instability == 0.0
    
    def test_stable_peak_low_instability(self):
        """Stable peak should have low instability."""
        power = np.array([1, 3, 2, 1])
        freqs = np.array([1, 2, 3, 4])
        
        peak_freq, instability = calculate_frequency_peak_instability(
            power, freqs, previous_peak_freq=2.1
        )
        
        assert peak_freq == 2.0
        assert abs(instability - 0.1) < 1e-10
    
    def test_shifting_peak_high_instability(self):
        """Rapidly shifting peak should have high instability."""
        power = np.array([1, 2, 3, 1])
        freqs = np.array([1, 2, 3, 4])
        
        peak_freq, instability = calculate_frequency_peak_instability(
            power, freqs, previous_peak_freq=1.0
        )
        
        assert peak_freq == 3.0
        assert instability == 2.0
    
    def test_mismatched_arrays_raise_error(self):
        """Mismatched array lengths should raise ValueError."""
        power = np.array([1, 2, 3])
        freqs = np.array([1, 2])
        
        with pytest.raises(ValueError, match="Power spectrum and frequencies must have same length"):
            calculate_frequency_peak_instability(power, freqs)
    
    def test_empty_arrays_raise_error(self):
        """Empty arrays should raise ValueError."""
        with pytest.raises(ValueError, match="Arrays cannot be empty"):
            calculate_frequency_peak_instability(np.array([]), np.array([]))


class TestSpectralCentroid:
    """Test spectral centroid calculations."""
    
    def test_uniform_distribution_mean_frequency(self):
        """Uniform distribution should have centroid at mean frequency."""
        power = np.ones(4)
        freqs = np.array([1, 2, 3, 4])
        
        centroid = calculate_spectral_centroid(power, freqs)
        expected = np.mean(freqs)
        
        assert abs(centroid - expected) < 1e-10
    
    def test_low_frequency_peak(self):
        """Low frequency peak should pull centroid down."""
        power = np.array([10, 1, 1, 1])
        freqs = np.array([1, 2, 3, 4])
        
        centroid = calculate_spectral_centroid(power, freqs)
        
        # Should be closer to 1 Hz than to mean (2.5 Hz)
        assert centroid < 2.0
    
    def test_high_frequency_peak(self):
        """High frequency peak should pull centroid up."""
        power = np.array([1, 1, 1, 10])
        freqs = np.array([1, 2, 3, 4])
        
        centroid = calculate_spectral_centroid(power, freqs)
        
        # Should be closer to 4 Hz than to mean (2.5 Hz)
        assert centroid > 3.0
    
    def test_zero_power_returns_mean_frequency(self):
        """Zero power should return mean frequency."""
        power = np.zeros(4)
        freqs = np.array([1, 2, 3, 4])
        
        centroid = calculate_spectral_centroid(power, freqs)
        expected = np.mean(freqs)
        
        assert abs(centroid - expected) < 1e-10
    
    def test_mismatched_arrays_raise_error(self):
        """Mismatched array lengths should raise ValueError."""
        power = np.array([1, 2, 3])
        freqs = np.array([1, 2])
        
        with pytest.raises(ValueError, match="Power spectrum and frequencies must have same length"):
            calculate_spectral_centroid(power, freqs)


class TestSpectralRolloff:
    """Test spectral rolloff calculations."""
    
    def test_85_percent_rolloff(self):
        """Test default 85% rolloff calculation."""
        # Power concentrated in first few frequencies
        power = np.array([40, 30, 20, 5, 5])  # Total = 100
        freqs = np.array([1, 2, 3, 4, 5])
        
        rolloff = calculate_spectral_rolloff(power, freqs)
        
        # 85% of 100 = 85
        # Cumulative: [40, 70, 90, 95, 100]
        # 85% threshold reached at index 2 (3 Hz)
        assert rolloff == 3.0
    
    def test_custom_percentile(self):
        """Test custom percentile rolloff."""
        power = np.array([50, 30, 20])  # Total = 100
        freqs = np.array([1, 2, 3])
        
        rolloff = calculate_spectral_rolloff(power, freqs, percentile=60.0)
        
        # 60% of 100 = 60
        # Cumulative: [50, 80, 100]
        # 60% threshold reached at index 1 (2 Hz)
        assert rolloff == 2.0
    
    def test_zero_power_returns_max_frequency(self):
        """Zero power should return maximum frequency."""
        power = np.zeros(4)
        freqs = np.array([1, 2, 3, 4])
        
        rolloff = calculate_spectral_rolloff(power, freqs)
        
        assert rolloff == 4.0
    
    def test_invalid_percentile_raises_error(self):
        """Invalid percentile should raise ValueError."""
        power = np.array([1, 2, 3])
        freqs = np.array([1, 2, 3])
        
        with pytest.raises(ValueError, match="Percentile must be between 0 and 100"):
            calculate_spectral_rolloff(power, freqs, percentile=0)
        
        with pytest.raises(ValueError, match="Percentile must be between 0 and 100"):
            calculate_spectral_rolloff(power, freqs, percentile=100)
    
    def test_all_power_at_end(self):
        """All power at end should return last frequency."""
        power = np.array([0, 0, 0, 100])
        freqs = np.array([1, 2, 3, 4])
        
        rolloff = calculate_spectral_rolloff(power, freqs, percentile=50.0)
        
        assert rolloff == 4.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])