"""
Spectral Features for Enhanced Anxiety Detection

This module provides advanced spectral analysis features for detecting
internal distress states that may not manifest in traditional EEG band power ratios.
"""

import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_spectral_entropy(power_spectrum: np.ndarray, normalize: bool = True) -> float:
    """
    Calculate Shannon entropy of frequency power distribution.
    
    Higher entropy indicates more chaotic/disorganized frequency patterns,
    which may correlate with anxiety and internal distress states.
    
    Args:
        power_spectrum: 1D array of power values across frequencies
        normalize: Whether to normalize spectrum to probability distribution
        
    Returns:
        float: Spectral entropy value (higher = more chaotic)
        
    Raises:
        ValueError: If power_spectrum is empty or contains invalid values
    """
    if len(power_spectrum) == 0:
        raise ValueError("Power spectrum cannot be empty")
    
    if np.any(power_spectrum < 0):
        raise ValueError("Power spectrum cannot contain negative values")
    
    # Handle edge case where all power is zero
    if np.sum(power_spectrum) == 0:
        return 0.0
        
    # Always normalize to probability distribution for meaningful entropy calculation
    # The normalize flag is kept for API compatibility but doesn't change behavior
    spectrum = power_spectrum / np.sum(power_spectrum)
    
    # Remove zero values to avoid log(0)
    spectrum = spectrum[spectrum > 0]
    
    if len(spectrum) == 0:
        return 0.0
    
    # Calculate Shannon entropy: -sum(p * log2(p))
    entropy = -np.sum(spectrum * np.log2(spectrum))
    
    return float(entropy)


def calculate_frequency_peak_instability(
    power_spectrum: np.ndarray, 
    frequencies: np.ndarray,
    previous_peak_freq: Optional[float] = None
) -> Tuple[float, float]:
    """
    Calculate instability of dominant frequency peak.
    
    Anxiety may manifest as rapid shifts in dominant frequency,
    even when overall band power ratios remain stable.
    
    Args:
        power_spectrum: 1D array of power values
        frequencies: 1D array of corresponding frequencies (Hz)
        previous_peak_freq: Previous dominant frequency for instability calculation
        
    Returns:
        tuple: (current_peak_frequency, instability_measure)
            instability_measure is Hz/second rate of change
            
    Raises:
        ValueError: If arrays are mismatched or empty
    """
    if len(power_spectrum) != len(frequencies):
        raise ValueError("Power spectrum and frequencies must have same length")
        
    if len(power_spectrum) == 0:
        raise ValueError("Arrays cannot be empty")
    
    # Find dominant frequency peak
    peak_idx = np.argmax(power_spectrum)
    current_peak_freq = float(frequencies[peak_idx])
    
    # Calculate instability if we have previous measurement
    if previous_peak_freq is not None:
        instability = abs(current_peak_freq - previous_peak_freq)
    else:
        instability = 0.0
    
    return current_peak_freq, instability


def calculate_spectral_centroid(power_spectrum: np.ndarray, frequencies: np.ndarray) -> float:
    """
    Calculate spectral centroid (center of mass of frequency distribution).
    
    Anxiety may shift the spectral centroid toward higher frequencies
    as the brain becomes more activated/hypervigilant.
    
    Args:
        power_spectrum: 1D array of power values
        frequencies: 1D array of corresponding frequencies (Hz)
        
    Returns:
        float: Spectral centroid frequency in Hz
        
    Raises:
        ValueError: If arrays are mismatched or empty
    """
    if len(power_spectrum) != len(frequencies):
        raise ValueError("Power spectrum and frequencies must have same length")
        
    if len(power_spectrum) == 0:
        raise ValueError("Arrays cannot be empty")
    
    # Handle case where all power is zero
    total_power = np.sum(power_spectrum)
    if total_power == 0:
        return float(np.mean(frequencies))
    
    # Calculate weighted average frequency
    centroid = np.sum(frequencies * power_spectrum) / total_power
    
    return float(centroid)


def calculate_spectral_rolloff(power_spectrum: np.ndarray, frequencies: np.ndarray, 
                              percentile: float = 85.0) -> float:
    """
    Calculate spectral rolloff frequency.
    
    The frequency below which a specified percentage of total power is contained.
    Higher rolloff may indicate more high-frequency activation (anxiety).
    
    Args:
        power_spectrum: 1D array of power values
        frequencies: 1D array of corresponding frequencies (Hz)
        percentile: Percentage of total power (default 85%)
        
    Returns:
        float: Rolloff frequency in Hz
        
    Raises:
        ValueError: If arrays are mismatched, empty, or percentile invalid
    """
    if len(power_spectrum) != len(frequencies):
        raise ValueError("Power spectrum and frequencies must have same length")
        
    if len(power_spectrum) == 0:
        raise ValueError("Arrays cannot be empty")
        
    if not 0 < percentile < 100:
        raise ValueError("Percentile must be between 0 and 100")
    
    # Handle case where all power is zero
    total_power = np.sum(power_spectrum)
    if total_power == 0:
        return float(frequencies[-1])  # Return highest frequency
    
    # Calculate cumulative power distribution
    cumulative_power = np.cumsum(power_spectrum)
    threshold = (percentile / 100.0) * total_power
    
    # Find first frequency where cumulative power exceeds threshold
    rolloff_idx = np.where(cumulative_power >= threshold)[0]
    
    if len(rolloff_idx) == 0:
        return float(frequencies[-1])
    
    return float(frequencies[rolloff_idx[0]])