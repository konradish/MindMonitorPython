"""
Cross-Channel Coherence Analysis for Anxiety Detection

This module provides coherence analysis between EEG channels to detect
changes in brain network synchronization that may indicate anxiety or stress states.
"""

import numpy as np
from scipy import signal
from typing import Tuple, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_cross_spectrum(signal1: np.ndarray, signal2: np.ndarray, 
                           sample_rate: int = 256, nperseg: int = 256,
                           overlap_ratio: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate cross-power spectral density between two signals.
    
    Args:
        signal1: First EEG channel
        signal2: Second EEG channel  
        sample_rate: Sampling rate in Hz
        nperseg: Length of each segment for FFT
        overlap_ratio: Overlap between segments (0-1)
        
    Returns:
        tuple: (frequencies, cross_spectrum)
        
    Raises:
        ValueError: If parameters are invalid
    """
    if len(signal1) != len(signal2):
        raise ValueError("Signals must have the same length")
        
    if len(signal1) == 0:
        raise ValueError("Signals cannot be empty")
        
    if sample_rate <= 0:
        raise ValueError("Sample rate must be positive")
        
    if not 0 <= overlap_ratio < 1:
        raise ValueError("Overlap ratio must be between 0 and 1")
        
    if nperseg > len(signal1):
        nperseg = len(signal1)
    
    # Calculate number of overlapping samples
    noverlap = int(nperseg * overlap_ratio)
    
    # Calculate cross-spectral density
    frequencies, cross_psd = signal.csd(
        signal1, signal2, 
        fs=sample_rate, 
        nperseg=nperseg,
        noverlap=noverlap,
        window='hann'
    )
    
    return frequencies, cross_psd


def calculate_coherence(signal1: np.ndarray, signal2: np.ndarray,
                       sample_rate: int = 256, nperseg: int = 256,
                       overlap_ratio: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate magnitude-squared coherence between two EEG channels.
    
    Coherence measures the linear relationship between signals as a function
    of frequency. Lower coherence may indicate reduced synchronization 
    during anxiety states.
    
    Args:
        signal1: First EEG channel
        signal2: Second EEG channel
        sample_rate: Sampling rate in Hz  
        nperseg: Length of each segment for FFT
        overlap_ratio: Overlap between segments (0-1)
        
    Returns:
        tuple: (frequencies, coherence_values)
        coherence_values range from 0 (no coherence) to 1 (perfect coherence)
        
    Raises:
        ValueError: If parameters are invalid
    """
    if len(signal1) != len(signal2):
        raise ValueError("Signals must have the same length")
        
    if len(signal1) == 0:
        raise ValueError("Signals cannot be empty")
        
    if sample_rate <= 0:
        raise ValueError("Sample rate must be positive")
        
    if not 0 <= overlap_ratio < 1:
        raise ValueError("Overlap ratio must be between 0 and 1")
        
    if nperseg > len(signal1):
        nperseg = len(signal1)
    
    # Calculate number of overlapping samples
    noverlap = int(nperseg * overlap_ratio)
    
    # Calculate coherence
    frequencies, coherence = signal.coherence(
        signal1, signal2,
        fs=sample_rate,
        nperseg=nperseg, 
        noverlap=noverlap,
        window='hann'
    )
    
    return frequencies, coherence


def calculate_phase_locking_value(signal1: np.ndarray, signal2: np.ndarray,
                                 frequency_band: Tuple[float, float],
                                 sample_rate: int = 256) -> float:
    """
    Calculate Phase Locking Value (PLV) between two signals in a frequency band.
    
    PLV measures phase synchronization between signals, with values from 0
    (no synchronization) to 1 (perfect phase locking). Anxiety may reduce PLV.
    
    Args:
        signal1: First EEG channel
        signal2: Second EEG channel
        frequency_band: (low_freq, high_freq) in Hz
        sample_rate: Sampling rate in Hz
        
    Returns:
        float: Phase locking value (0-1)
        
    Raises:
        ValueError: If parameters are invalid
    """
    if len(signal1) != len(signal2):
        raise ValueError("Signals must have the same length")
        
    if len(signal1) == 0:  
        raise ValueError("Signals cannot be empty")
        
    if sample_rate <= 0:
        raise ValueError("Sample rate must be positive")
        
    low_freq, high_freq = frequency_band
    if low_freq >= high_freq:
        raise ValueError("Low frequency must be less than high frequency")
        
    if high_freq >= sample_rate / 2:
        raise ValueError(f"High frequency ({high_freq}) must be less than Nyquist frequency ({sample_rate/2})")
    
    # Design bandpass filter for frequency band
    nyquist = sample_rate / 2
    low_norm = low_freq / nyquist
    high_norm = high_freq / nyquist
    
    sos = signal.butter(4, [low_norm, high_norm], btype='band', output='sos')
    
    # Filter both signals
    filtered_signal1 = signal.sosfiltfilt(sos, signal1)
    filtered_signal2 = signal.sosfiltfilt(sos, signal2)
    
    # Calculate analytic signals (complex-valued)
    analytic1 = signal.hilbert(filtered_signal1)
    analytic2 = signal.hilbert(filtered_signal2)
    
    # Extract instantaneous phases
    phase1 = np.angle(analytic1)
    phase2 = np.angle(analytic2)
    
    # Calculate phase difference
    phase_diff = phase1 - phase2
    
    # Calculate PLV as the magnitude of the mean complex exponential
    plv = np.abs(np.mean(np.exp(1j * phase_diff)))
    
    return float(plv)


def analyze_multi_channel_coherence(channels: Dict[str, np.ndarray], 
                                   sample_rate: int = 256,
                                   frequency_bands: Optional[Dict[str, Tuple[float, float]]] = None) -> Dict:
    """
    Comprehensive coherence analysis across multiple EEG channels.
    
    Args:
        channels: Dictionary of channel_name -> signal_data
        sample_rate: Sampling rate in Hz
        frequency_bands: Dictionary of band_name -> (low_freq, high_freq)
                        If None, uses standard EEG bands
        
    Returns:
        dict: Analysis results containing:
            - channel_pairs: List of analyzed channel pairs
            - coherence_matrix: Average coherence between all channel pairs
            - band_coherence: Coherence in specific frequency bands
            - plv_matrix: Phase locking values between channel pairs
            - coherence_stats: Statistical summary
            
    Raises:
        ValueError: If parameters are invalid
    """
    if len(channels) < 2:
        raise ValueError("Need at least 2 channels for coherence analysis")
        
    # Validate all channels have same length
    channel_names = list(channels.keys())
    signal_lengths = [len(channels[name]) for name in channel_names]
    
    if len(set(signal_lengths)) > 1:
        raise ValueError("All channels must have the same length")
        
    if signal_lengths[0] == 0:
        raise ValueError("Channels cannot be empty")
    
    if sample_rate <= 0:
        raise ValueError("Sample rate must be positive")
    
    # Default frequency bands if not provided
    if frequency_bands is None:
        frequency_bands = {
            'delta': (0.5, 4.0),
            'theta': (4.0, 8.0),
            'alpha': (8.0, 13.0),
            'beta': (13.0, 30.0),
            'gamma': (30.0, 50.0)
        }
    
    # Initialize result structures
    n_channels = len(channel_names)
    coherence_matrix = np.zeros((n_channels, n_channels))
    plv_matrix = np.zeros((n_channels, n_channels))
    band_coherence = {band: np.zeros((n_channels, n_channels)) for band in frequency_bands}
    
    channel_pairs = []
    all_coherences = []
    
    # Analyze all channel pairs
    for i, name1 in enumerate(channel_names):
        for j, name2 in enumerate(channel_names):
            if i >= j:  # Skip diagonal and duplicate pairs
                continue
                
            signal1 = channels[name1]
            signal2 = channels[name2]
            
            channel_pairs.append((name1, name2))
            
            # Calculate broadband coherence
            freqs, coherence = calculate_coherence(signal1, signal2, sample_rate)
            mean_coherence = np.mean(coherence)
            
            coherence_matrix[i, j] = mean_coherence
            coherence_matrix[j, i] = mean_coherence  # Symmetric
            all_coherences.append(mean_coherence)
            
            # Calculate band-specific coherence and PLV
            for band_name, (low_freq, high_freq) in frequency_bands.items():
                # Find frequency indices for this band
                band_mask = (freqs >= low_freq) & (freqs <= high_freq)
                if np.any(band_mask):
                    band_coh = np.mean(coherence[band_mask])
                else:
                    band_coh = 0.0
                    
                band_coherence[band_name][i, j] = band_coh
                band_coherence[band_name][j, i] = band_coh
                
                # Calculate PLV for this band
                try:
                    plv = calculate_phase_locking_value(
                        signal1, signal2, (low_freq, high_freq), sample_rate
                    )
                    plv_matrix[i, j] = plv
                    plv_matrix[j, i] = plv
                except Exception as e:
                    logger.warning(f"Failed to calculate PLV for {name1}-{name2} in {band_name}: {e}")
                    plv_matrix[i, j] = 0.0
                    plv_matrix[j, i] = 0.0
    
    # Calculate statistics
    coherence_stats = {
        'mean_coherence': np.mean(all_coherences),
        'std_coherence': np.std(all_coherences),
        'min_coherence': np.min(all_coherences),
        'max_coherence': np.max(all_coherences),
        'median_coherence': np.median(all_coherences)
    }
    
    return {
        'channel_pairs': channel_pairs,
        'coherence_matrix': coherence_matrix,
        'band_coherence': band_coherence,
        'plv_matrix': plv_matrix,
        'coherence_stats': coherence_stats,
        'channel_names': channel_names,
        'frequency_bands': frequency_bands
    }


def detect_coherence_anomalies(coherence_analysis: Dict, 
                              baseline_coherence: Optional[Dict] = None,
                              z_threshold: float = 2.0) -> Dict:
    """
    Detect anomalies in coherence patterns that may indicate anxiety/stress.
    
    Args:
        coherence_analysis: Result from analyze_multi_channel_coherence
        baseline_coherence: Baseline coherence for comparison (optional)
        z_threshold: Z-score threshold for anomaly detection
        
    Returns:
        dict: Anomaly detection results
        
    Raises:
        ValueError: If parameters are invalid
    """
    if 'coherence_stats' not in coherence_analysis:
        raise ValueError("Invalid coherence analysis format")
        
    if z_threshold <= 0:
        raise ValueError("Z-score threshold must be positive")
    
    stats = coherence_analysis['coherence_stats']
    coherence_matrix = coherence_analysis['coherence_matrix']
    
    # Extract upper triangle (unique pairs) for analysis
    n_channels = coherence_matrix.shape[0]
    upper_triangle_mask = np.triu(np.ones((n_channels, n_channels)), k=1).astype(bool)
    coherence_values = coherence_matrix[upper_triangle_mask]
    
    anomalies = {
        'low_coherence_pairs': [],
        'high_coherence_pairs': [],
        'overall_assessment': 'normal',
        'anomaly_score': 0.0
    }
    
    # Detect anomalies based on statistical thresholds
    mean_coh = stats['mean_coherence']
    std_coh = stats['std_coherence']
    
    if std_coh > 0:  # Avoid division by zero
        channel_pairs = coherence_analysis['channel_pairs']
        
        for i, (name1, name2) in enumerate(channel_pairs):
            coh_value = coherence_values[i]
            z_score = (coh_value - mean_coh) / std_coh
            
            if z_score < -z_threshold:  # Unusually low coherence
                anomalies['low_coherence_pairs'].append({
                    'pair': (name1, name2),
                    'coherence': coh_value,
                    'z_score': z_score
                })
            elif z_score > z_threshold:  # Unusually high coherence
                anomalies['high_coherence_pairs'].append({
                    'pair': (name1, name2),
                    'coherence': coh_value,
                    'z_score': z_score
                })
    
    # Calculate overall anomaly score
    n_anomalies = len(anomalies['low_coherence_pairs']) + len(anomalies['high_coherence_pairs'])
    n_total_pairs = len(coherence_analysis['channel_pairs'])
    
    if n_total_pairs > 0:
        anomaly_score = n_anomalies / n_total_pairs
        anomalies['anomaly_score'] = anomaly_score
        
        # Assess overall state
        if anomaly_score > 0.5:
            anomalies['overall_assessment'] = 'high_anomaly'
        elif anomaly_score > 0.25:
            anomalies['overall_assessment'] = 'moderate_anomaly'
        elif anomaly_score > 0:
            anomalies['overall_assessment'] = 'mild_anomaly'
    
    return anomalies