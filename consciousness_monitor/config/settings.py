"""Global settings and configuration management."""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class EEGBands:
    """EEG frequency band definitions."""
    delta: tuple = (0.5, 4)
    theta: tuple = (4, 8)
    alpha: tuple = (8, 13)
    beta: tuple = (13, 30)
    gamma: tuple = (30, 50)
    
    def as_dict(self) -> Dict[str, tuple]:
        """Return bands as dictionary."""
        return {
            'delta': self.delta,
            'theta': self.theta,
            'alpha': self.alpha,
            'beta': self.beta,
            'gamma': self.gamma
        }


@dataclass  
class DataColumns:
    """CSV column mapping definitions."""
    eeg_columns: list = None
    abs_band_columns: list = None
    rel_band_columns: list = None
    quality_columns: list = None
    
    def __post_init__(self):
        if self.eeg_columns is None:
            self.eeg_columns = ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']
        if self.abs_band_columns is None:
            self.abs_band_columns = ['abs_delta', 'abs_theta', 'abs_alpha', 'abs_beta', 'abs_gamma']
        if self.rel_band_columns is None:
            self.rel_band_columns = ['rel_delta', 'rel_theta', 'rel_alpha', 'rel_beta', 'rel_gamma']
        if self.quality_columns is None:
            self.quality_columns = ['touching_forehead', 'horseshoe_tp9', 'horseshoe_af7', 'horseshoe_af8', 'horseshoe_tp10']


class Settings:
    """Global settings management."""
    
    def __init__(self):
        self.eeg_bands = EEGBands()
        self.data_columns = DataColumns()
        
        # Default sample rate
        self.default_sample_rate = 256
        
        # Default analysis parameters
        self.default_window_seconds = 0.75
        self.default_update_interval = 1.0
        
        # Event detection thresholds
        self.alpha_threshold = 10  # % change
        self.fnirs_threshold = 0.05
        self.gamma_spike_threshold = 15  # %
        
        # Macro analysis defaults
        self.default_macro_window = 60.0
        self.default_beta_trend_window = 5
        
    def get_eeg_bands(self) -> Dict[str, tuple]:
        """Get EEG frequency band definitions."""
        return self.eeg_bands.as_dict()
    
    def get_data_columns(self) -> DataColumns:
        """Get CSV column mappings."""
        return self.data_columns
    
    def get_default_sample_rate(self) -> int:
        """Get default sample rate."""
        return self.default_sample_rate