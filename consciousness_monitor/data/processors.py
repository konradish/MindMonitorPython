"""Signal processing for EEG data analysis."""

import numpy as np
from scipy import signal
from typing import Dict, List, Optional, Tuple
import pandas as pd

from .models import BandPower, EEGReading
from ..config.settings import Settings
from ..utils.math_helpers import MathHelpers


class SignalProcessor:
    """Handles EEG signal processing and band power calculations."""
    
    def __init__(self, sample_rate: float = 256):
        self.sample_rate = sample_rate
        self.settings = Settings()
        self.bands = self.settings.get_eeg_bands()
        
        # Design filters once during initialization
        self._setup_filters()
    
    def _setup_filters(self):
        """Setup commonly used filters."""
        try:
            self.highpass_filter = signal.butter(4, 0.5, btype='high', fs=self.sample_rate)
            
            # Adapt lowpass filter to sample rate (must be < Nyquist frequency)
            nyquist = self.sample_rate / 2
            lowpass_freq = min(40, nyquist * 0.9)  # Use 40Hz or 90% of Nyquist, whichever is lower
            self.lowpass_filter = signal.butter(4, lowpass_freq, btype='low', fs=self.sample_rate)
            
            # Adapt notch filter to sample rate (skip if 60Hz > Nyquist)
            if nyquist > 60:
                self.notch_filter = signal.iirnotch(60, 30, fs=self.sample_rate)
            else:
                self.notch_filter = None  # Skip notch filter for low sample rates
                
        except Exception as e:
            print(f"⚠️ Warning: Could not setup filters: {e}")
            self.highpass_filter = None
            self.lowpass_filter = None
            self.notch_filter = None
    
    def preprocess_signal(self, raw_data: np.ndarray) -> np.ndarray:
        """
        Preprocess raw EEG signal with basic filtering.
        
        Args:
            raw_data: Raw EEG signal data
            
        Returns:
            Preprocessed signal data
        """
        if len(raw_data) == 0:
            return raw_data
        
        try:
            # Remove DC component (mean)
            data = MathHelpers.remove_dc_component(raw_data)
            
            # Apply filters if available
            if self.highpass_filter is not None:
                data = signal.filtfilt(*self.highpass_filter, data)
            
            if self.lowpass_filter is not None:
                data = signal.filtfilt(*self.lowpass_filter, data)
            
            if self.notch_filter is not None:
                data = signal.filtfilt(*self.notch_filter, data)
            
            return data
            
        except Exception as e:
            print(f"⚠️ Signal preprocessing failed: {e}")
            return MathHelpers.remove_dc_component(raw_data)
    
    def calculate_welch_power(self, data: np.ndarray, nperseg: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate power spectral density using Welch's method.
        
        Args:
            data: Signal data
            nperseg: Length of each segment for Welch's method
            
        Returns:
            Frequency array and power spectral density
        """
        if len(data) == 0:
            return np.array([]), np.array([])
        
        if nperseg is None:
            nperseg = min(len(data), int(self.sample_rate))
        
        try:
            frequencies, psd = signal.welch(
                data, 
                fs=self.sample_rate, 
                nperseg=nperseg,
                noverlap=nperseg//2
            )
            return frequencies, psd
        except Exception as e:
            print(f"⚠️ Welch power calculation failed: {e}")
            return np.array([]), np.array([])
    
    def get_band_power(self, data: np.ndarray, low_freq: float, high_freq: float) -> float:
        """
        Calculate power in a specific frequency band.
        
        Args:
            data: Signal data
            low_freq: Lower frequency bound
            high_freq: Upper frequency bound
            
        Returns:
            Band power value
        """
        if len(data) == 0:
            return 0.0
        
        try:
            frequencies, psd = self.calculate_welch_power(data)
            
            if len(frequencies) == 0:
                return 0.0
            
            # Find frequency indices for the band
            freq_mask = (frequencies >= low_freq) & (frequencies <= high_freq)
            
            if not np.any(freq_mask):
                return 0.0
            
            # Calculate band power using trapezoidal integration
            band_power = np.trapz(psd[freq_mask], frequencies[freq_mask])
            return max(0.0, band_power)
            
        except Exception as e:
            print(f"⚠️ Band power calculation failed for {low_freq}-{high_freq}Hz: {e}")
            return 0.0
    
    def calculate_all_band_powers(self, data: np.ndarray) -> BandPower:
        """
        Calculate power for all EEG frequency bands.
        
        Args:
            data: Signal data
            
        Returns:
            BandPower object with all band powers
        """
        if len(data) == 0:
            return BandPower(0.0, 0.0, 0.0, 0.0, 0.0)
        
        try:
            # Preprocess the signal
            processed_data = self.preprocess_signal(data)
            
            # Calculate power for each band
            delta_power = self.get_band_power(processed_data, *self.bands['delta'])
            theta_power = self.get_band_power(processed_data, *self.bands['theta'])
            alpha_power = self.get_band_power(processed_data, *self.bands['alpha'])
            beta_power = self.get_band_power(processed_data, *self.bands['beta'])
            gamma_power = self.get_band_power(processed_data, *self.bands['gamma'])
            
            return BandPower(
                delta=delta_power,
                theta=theta_power,
                alpha=alpha_power,
                beta=beta_power,
                gamma=gamma_power
            )
            
        except Exception as e:
            print(f"⚠️ All band power calculation failed: {e}")
            return BandPower(0.0, 0.0, 0.0, 0.0, 0.0)
    
    def calculate_multichannel_average(self, channel_data: Dict[str, np.ndarray]) -> BandPower:
        """
        Calculate average band powers across multiple EEG channels.
        
        Args:
            channel_data: Dictionary of channel name to signal data
            
        Returns:
            Averaged BandPower across all channels
        """
        if not channel_data:
            return BandPower(0.0, 0.0, 0.0, 0.0, 0.0)
        
        all_powers = []
        for channel_name, data in channel_data.items():
            if len(data) > 0:
                powers = self.calculate_all_band_powers(data)
                all_powers.append(powers)
        
        if not all_powers:
            return BandPower(0.0, 0.0, 0.0, 0.0, 0.0)
        
        # Average across channels
        avg_delta = np.mean([p.delta for p in all_powers])
        avg_theta = np.mean([p.theta for p in all_powers])
        avg_alpha = np.mean([p.alpha for p in all_powers])
        avg_beta = np.mean([p.beta for p in all_powers])
        avg_gamma = np.mean([p.gamma for p in all_powers])
        
        return BandPower(
            delta=avg_delta,
            theta=avg_theta,
            alpha=avg_alpha,
            beta=avg_beta,
            gamma=avg_gamma
        )
    
    def detect_signal_quality(self, data: np.ndarray) -> Dict[str, float]:
        """
        Assess signal quality metrics.
        
        Args:
            data: Signal data
            
        Returns:
            Dictionary of quality metrics
        """
        if len(data) == 0:
            return {'snr': 0.0, 'outlier_ratio': 1.0, 'signal_range': 0.0}
        
        try:
            # Calculate basic quality metrics
            signal_range = np.max(data) - np.min(data)
            outliers = MathHelpers.detect_outliers(data)
            outlier_ratio = np.sum(outliers) / len(data) if len(data) > 0 else 1.0
            
            # Estimate SNR (signal vs high-frequency noise)
            if len(data) > 64:
                # Use high-frequency content as noise estimate
                high_freq_data = data[::8]  # Downsample to estimate noise
                noise_std = np.std(high_freq_data)
                signal_std = np.std(data)
                snr = MathHelpers.safe_division(signal_std, noise_std, 1.0)
                snr_db = MathHelpers.power_to_db(snr)
            else:
                snr_db = 0.0
            
            return {
                'snr': snr_db,
                'outlier_ratio': outlier_ratio,
                'signal_range': signal_range
            }
            
        except Exception as e:
            print(f"⚠️ Signal quality assessment failed: {e}")
            return {'snr': 0.0, 'outlier_ratio': 1.0, 'signal_range': 0.0}