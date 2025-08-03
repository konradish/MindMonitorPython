"""
High-Gamma Micro-burst Detection for Anxiety/Hypervigilance

This module provides detection of sudden increases in high-gamma (30-100Hz) activity,
which may indicate anxiety, hypervigilance, or internal distress states that don't
show up in traditional EEG band power analysis.
"""

import numpy as np
from scipy import signal
from typing import Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


def extract_high_gamma_band(eeg_data: np.ndarray, sample_rate: int = 256, 
                           low_freq: float = 30.0, high_freq: float = 100.0) -> np.ndarray:
    """
    Extract high-gamma frequency band from EEG data.
    
    Args:
        eeg_data: 1D array of EEG samples
        sample_rate: Sampling rate in Hz (default: 256)
        low_freq: Lower bound of gamma band in Hz (default: 30)
        high_freq: Upper bound of gamma band in Hz (default: 100)
        
    Returns:
        np.ndarray: Filtered high-gamma signal
        
    Raises:
        ValueError: If parameters are invalid
    """
    if len(eeg_data) == 0:
        raise ValueError("EEG data cannot be empty")
    
    if sample_rate <= 0:
        raise ValueError("Sample rate must be positive")
        
    if low_freq >= high_freq:
        raise ValueError("Low frequency must be less than high frequency")
        
    if high_freq >= sample_rate / 2:
        raise ValueError(f"High frequency ({high_freq}) must be less than Nyquist frequency ({sample_rate/2})")
    
    # Design bandpass filter
    nyquist = sample_rate / 2
    low_norm = low_freq / nyquist
    high_norm = high_freq / nyquist
    
    # Use butterworth filter, order 4 for good frequency response
    sos = signal.butter(4, [low_norm, high_norm], btype='band', output='sos')
    
    # Apply zero-phase filtering to avoid phase distortion
    filtered_signal = signal.sosfiltfilt(sos, eeg_data)
    
    return filtered_signal


def calculate_gamma_power_envelope(gamma_signal: np.ndarray, window_size: int = 64) -> np.ndarray:
    """
    Calculate power envelope of high-gamma signal using Hilbert transform.
    
    Args:
        gamma_signal: High-gamma filtered EEG signal
        window_size: Smoothing window size for envelope (default: 64 samples)
        
    Returns:
        np.ndarray: Power envelope of gamma signal
        
    Raises:
        ValueError: If parameters are invalid
    """
    if len(gamma_signal) == 0:
        raise ValueError("Gamma signal cannot be empty")
        
    if window_size <= 0:
        raise ValueError("Window size must be positive")
    
    # Calculate analytic signal using Hilbert transform
    analytic_signal = signal.hilbert(gamma_signal)
    
    # Calculate instantaneous amplitude (envelope)
    envelope = np.abs(analytic_signal)
    
    # Smooth the envelope to reduce noise
    if window_size > 1:
        # Use moving average for smoothing
        kernel = np.ones(window_size) / window_size
        envelope = np.convolve(envelope, kernel, mode='same')
    
    return envelope


def detect_gamma_bursts(gamma_envelope: np.ndarray, baseline_window: int = 512,
                       threshold_db: float = 2.0, min_duration_samples: int = 16,
                       sample_rate: int = 256, exclude_edges: bool = True) -> List[Tuple[int, int, float]]:
    """
    Detect micro-bursts in high-gamma power envelope.
    
    Args:
        gamma_envelope: Power envelope of high-gamma signal
        baseline_window: Window size for baseline calculation (default: 512 samples = 2s)
        threshold_db: Minimum dB increase above baseline (default: 2.0 dB)
        min_duration_samples: Minimum burst duration in samples (default: 16 = ~60ms at 256Hz)
        sample_rate: Sampling rate for time calculations
        exclude_edges: Whether to exclude edge regions prone to filter artifacts (default: True)
        
    Returns:
        List of tuples: (start_idx, end_idx, peak_db_increase)
        
    Raises:
        ValueError: If parameters are invalid
    """
    if len(gamma_envelope) == 0:
        raise ValueError("Gamma envelope cannot be empty")
        
    if baseline_window <= 0 or threshold_db <= 0 or min_duration_samples <= 0:
        raise ValueError("All parameters must be positive")
        
    if sample_rate <= 0:
        raise ValueError("Sample rate must be positive")
    
    bursts = []
    
    # Calculate rolling baseline using median for robustness
    half_window = baseline_window // 2
    
    # Define analysis range (exclude edges if requested)
    if exclude_edges:
        # Exclude first and last 5% of signal to avoid filter artifacts
        # but don't be too aggressive
        edge_samples = max(32, len(gamma_envelope) // 20)  # At least 32 samples (~125ms at 256Hz)
        start_idx = max(edge_samples, half_window)
        end_idx = min(len(gamma_envelope) - edge_samples, len(gamma_envelope) - half_window)
    else:
        start_idx = 0
        end_idx = len(gamma_envelope)
    
    for i in range(start_idx, end_idx):
        # Define baseline window around current sample
        start_baseline = max(0, i - half_window)
        end_baseline = min(len(gamma_envelope), i + half_window)
        
        if end_baseline - start_baseline < baseline_window // 4:
            continue  # Skip if we don't have enough baseline data
            
        baseline_power = np.median(gamma_envelope[start_baseline:end_baseline])
        
        if baseline_power <= 0:
            continue  # Skip if baseline is zero or negative
            
        current_power = gamma_envelope[i]
        
        # Calculate dB increase
        db_increase = 20 * np.log10(current_power / baseline_power) if current_power > 0 else -np.inf
        
        # Check if this sample exceeds threshold
        if db_increase >= threshold_db:
            # Look for the start and end of this burst
            burst_start = i
            burst_end = i
            
            # Extend backwards to find burst start
            while (burst_start > 0 and 
                   burst_start > i - min_duration_samples * 4):  # Max backward search
                prev_baseline_start = max(0, burst_start - 1 - half_window)
                prev_baseline_end = min(len(gamma_envelope), burst_start - 1 + half_window)
                
                if prev_baseline_end - prev_baseline_start < baseline_window // 4:
                    break
                    
                prev_baseline = np.median(gamma_envelope[prev_baseline_start:prev_baseline_end])
                if prev_baseline <= 0:
                    break
                    
                prev_db = 20 * np.log10(gamma_envelope[burst_start - 1] / prev_baseline)
                
                if prev_db < threshold_db:
                    break
                    
                burst_start -= 1
            
            # Extend forwards to find burst end
            while (burst_end < len(gamma_envelope) - 1 and 
                   burst_end < i + min_duration_samples * 4):  # Max forward search
                next_baseline_start = max(0, burst_end + 1 - half_window)
                next_baseline_end = min(len(gamma_envelope), burst_end + 1 + half_window)
                
                if next_baseline_end - next_baseline_start < baseline_window // 4:
                    break
                    
                next_baseline = np.median(gamma_envelope[next_baseline_start:next_baseline_end])
                if next_baseline <= 0:
                    break
                    
                next_db = 20 * np.log10(gamma_envelope[burst_end + 1] / next_baseline)
                
                if next_db < threshold_db:
                    break
                    
                burst_end += 1
            
            # Check if burst meets minimum duration requirement
            if burst_end - burst_start >= min_duration_samples:
                # Find peak dB increase in this burst
                peak_power = np.max(gamma_envelope[burst_start:burst_end + 1])
                peak_db = 20 * np.log10(peak_power / baseline_power)
                
                # Check if we already detected a burst overlapping with this one
                overlap = False
                for existing_start, existing_end, _ in bursts:
                    if not (burst_end < existing_start or burst_start > existing_end):
                        overlap = True
                        break
                
                if not overlap:
                    bursts.append((burst_start, burst_end, peak_db))
                    
                # Skip ahead to avoid detecting overlapping bursts
                i = burst_end
    
    return bursts


def analyze_gamma_burst_pattern(eeg_data: np.ndarray, sample_rate: int = 256,
                               analysis_window: float = 1.0) -> dict:
    """
    Comprehensive analysis of high-gamma burst patterns in EEG data.
    
    Args:
        eeg_data: 1D array of EEG samples
        sample_rate: Sampling rate in Hz
        analysis_window: Time window for analysis in seconds
        
    Returns:
        dict: Analysis results containing:
            - burst_count: Number of detected bursts
            - burst_rate: Bursts per second
            - avg_burst_duration: Average burst duration in seconds
            - avg_burst_intensity: Average peak dB increase
            - total_burst_time: Total time spent in bursts (seconds)
            - burst_coverage: Percentage of time in bursts
            
    Raises:
        ValueError: If parameters are invalid
    """
    if len(eeg_data) == 0:
        raise ValueError("EEG data cannot be empty")
        
    if sample_rate <= 0:
        raise ValueError("Sample rate must be positive")
        
    if analysis_window <= 0:
        raise ValueError("Analysis window must be positive")
    
    # Extract high-gamma band
    gamma_signal = extract_high_gamma_band(eeg_data, sample_rate)
    
    # Calculate power envelope
    gamma_envelope = calculate_gamma_power_envelope(gamma_signal)
    
    # Detect bursts
    bursts = detect_gamma_bursts(gamma_envelope, sample_rate=sample_rate)
    
    # Calculate statistics
    burst_count = len(bursts)
    burst_rate = burst_count / analysis_window
    
    if burst_count > 0:
        # Calculate duration statistics
        durations = [(end - start) / sample_rate for start, end, _ in bursts]
        avg_burst_duration = np.mean(durations)
        total_burst_time = np.sum(durations)
        
        # Calculate intensity statistics
        intensities = [intensity for _, _, intensity in bursts]
        avg_burst_intensity = np.mean(intensities)
        
        # Calculate coverage
        burst_coverage = (total_burst_time / analysis_window) * 100
    else:
        avg_burst_duration = 0.0
        total_burst_time = 0.0
        avg_burst_intensity = 0.0
        burst_coverage = 0.0
    
    return {
        'burst_count': burst_count,
        'burst_rate': burst_rate,
        'avg_burst_duration': avg_burst_duration,
        'avg_burst_intensity': avg_burst_intensity,
        'total_burst_time': total_burst_time,
        'burst_coverage': burst_coverage,
        'raw_bursts': bursts  # For detailed analysis
    }