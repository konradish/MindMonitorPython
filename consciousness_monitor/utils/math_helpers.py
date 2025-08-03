"""Mathematical helper functions for EEG analysis."""

import numpy as np
from typing import Dict, Optional


class MathHelpers:
    """Mathematical utilities for EEG signal processing."""
    
    @staticmethod
    def power_to_db(power_value: float, reference_power: float = 1.0) -> float:
        """Convert power value to decibels."""
        if power_value <= 0:
            return -np.inf
        return 10 * np.log10(power_value / reference_power)
    
    @staticmethod
    def db_to_power(db_value: float, reference_power: float = 1.0) -> float:
        """Convert decibels back to power value."""
        if db_value == -np.inf:
            return 0.0
        return reference_power * (10 ** (db_value / 10))
    
    @staticmethod
    def calculate_db_change(current_db: float, previous_db: float) -> float:
        """Calculate change in dB between two measurements."""
        if np.isinf(previous_db) or np.isinf(current_db):
            return 0.0
        return current_db - previous_db
    
    @staticmethod
    def normalize_band_powers(powers: Dict[str, float]) -> Dict[str, float]:
        """Normalize band powers to percentages."""
        total = sum(powers.values())
        if total == 0:
            return {band: 0.0 for band in powers.keys()}
        return {band: (power / total) * 100 for band, power in powers.items()}
    
    @staticmethod
    def safe_division(numerator: float, denominator: float, default: float = 0.0) -> float:
        """Safely divide two numbers, returning default if denominator is zero."""
        if denominator == 0:
            return default
        return numerator / denominator
    
    @staticmethod
    def calculate_rms(data: np.ndarray) -> float:
        """Calculate root mean square of signal data."""
        if len(data) == 0:
            return 0.0
        return np.sqrt(np.mean(data ** 2))
    
    @staticmethod
    def remove_dc_component(data: np.ndarray) -> np.ndarray:
        """Remove DC component (mean) from signal."""
        return data - np.mean(data)
    
    @staticmethod
    def calculate_snr(signal: np.ndarray, noise: np.ndarray) -> float:
        """Calculate signal-to-noise ratio in dB."""
        signal_power = np.mean(signal ** 2)
        noise_power = np.mean(noise ** 2)
        
        if noise_power == 0:
            return np.inf
        
        snr_linear = signal_power / noise_power
        return MathHelpers.power_to_db(snr_linear)
    
    @staticmethod
    def moving_average(data: np.ndarray, window_size: int) -> np.ndarray:
        """Calculate moving average with specified window size."""
        if len(data) < window_size:
            return data
        
        return np.convolve(data, np.ones(window_size) / window_size, mode='valid')
    
    @staticmethod
    def detect_outliers(data: np.ndarray, threshold: float = 3.0) -> np.ndarray:
        """Detect outliers using z-score method."""
        if len(data) == 0:
            return np.array([])
        
        z_scores = np.abs((data - np.mean(data)) / np.std(data))
        return z_scores > threshold
    
    @staticmethod
    def bandpass_filter_design(low_freq: float, high_freq: float, sample_rate: float, order: int = 4):
        """Design a Butterworth bandpass filter."""
        from scipy import signal
        nyquist = sample_rate / 2
        low_normalized = low_freq / nyquist
        high_normalized = high_freq / nyquist
        
        # Ensure frequencies are in valid range
        low_normalized = max(0.001, min(0.999, low_normalized))
        high_normalized = max(0.001, min(0.999, high_normalized))
        
        return signal.butter(order, [low_normalized, high_normalized], btype='band')
    
    @staticmethod
    def calculate_coherence(signal1: np.ndarray, signal2: np.ndarray, sample_rate: float) -> tuple:
        """Calculate coherence between two signals."""
        from scipy import signal
        frequencies, coherence = signal.coherence(signal1, signal2, fs=sample_rate)
        return frequencies, coherence