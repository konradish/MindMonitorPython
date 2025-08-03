"""Artifact detection and filtering for EEG data."""

from typing import Dict, Optional
import numpy as np

from ..config.thresholds import ArtifactThresholds


class ArtifactFilter:
    """Handles detection and filtering of EEG artifacts."""
    
    def __init__(self, thresholds: ArtifactThresholds):
        self.thresholds = thresholds
    
    def detect_artifacts(self, bands: Dict[str, float], 
                        db_changes: Dict[str, float]) -> Optional[str]:
        """
        Detect various types of EEG artifacts.
        
        Args:
            bands: Band power percentages
            db_changes: dB changes for each band
            
        Returns:
            Artifact type string if detected, None otherwise
        """
        try:
            # Multi-band simultaneous spike (classic artifact)
            simultaneous_spikes = sum(
                1 for change in db_changes.values() 
                if abs(float(change)) > self.thresholds.get_threshold("multiband_spike")
            )
            
            if simultaneous_spikes >= self.thresholds.get_threshold("simultaneous_bands"):
                return "ARTIFACT_MULTIBAND_SPIKE"
            
            # Impossible value combinations
            alpha_percent = float(bands.get('alpha', 0))
            beta_percent = float(bands.get('beta', 0))
            
            if (alpha_percent > self.thresholds.get_threshold("impossible_combo_alpha") and 
                beta_percent > self.thresholds.get_threshold("impossible_combo_beta")):
                return "ARTIFACT_IMPOSSIBLE_COMBO"
            
            # Sudden extreme shifts from baseline
            total_change = sum(abs(float(change)) for change in db_changes.values())
            if total_change > self.thresholds.get_threshold("extreme_shift"):
                return "ARTIFACT_EXTREME_SHIFT"
            
            # Check for NaN or infinite values
            if any(np.isnan(float(value)) or np.isinf(float(value)) for value in bands.values()):
                return "ARTIFACT_INVALID_VALUES"
            
            # Check for zero power in all bands (sensor disconnection)
            total_power = sum(float(value) for value in bands.values())
            if total_power < 0.001:  # Very low threshold for total power
                return "ARTIFACT_NO_SIGNAL"
            
            return None  # No artifact detected
            
        except Exception as e:
            print(f"⚠️ Artifact detection error: {e}")
            return "ARTIFACT_DETECTION_ERROR"
    
    def is_signal_quality_acceptable(self, bands: Dict[str, float]) -> bool:
        """
        Check if signal quality is acceptable for analysis.
        
        Args:
            bands: Band power percentages
            
        Returns:
            True if signal quality is acceptable
        """
        try:
            # Check for reasonable distribution across bands
            total_power = sum(bands.values())
            if total_power < 50:  # Very low total power
                return False
            
            # Check that no single band dominates completely (>95%)
            max_band_percent = max(bands.values())
            if max_band_percent > 95:
                return False
            
            # Check for reasonable alpha presence (basic sanity check)
            alpha_percent = bands.get('alpha', 0)
            if alpha_percent < 1:  # Alpha should be at least 1%
                return False
            
            return True
            
        except Exception:
            return False
    
    def filter_outliers(self, band_values: Dict[str, float], 
                       z_threshold: float = 3.0) -> Dict[str, float]:
        """
        Filter outlier values using z-score method.
        
        Args:
            band_values: Band power values
            z_threshold: Z-score threshold for outlier detection
            
        Returns:
            Filtered band values
        """
        try:
            values = list(band_values.values())
            if len(values) < 3:
                return band_values
            
            mean_val = np.mean(values)
            std_val = np.std(values)
            
            if std_val == 0:
                return band_values
            
            filtered_values = {}
            for band, value in band_values.items():
                z_score = abs((value - mean_val) / std_val)
                if z_score <= z_threshold:
                    filtered_values[band] = value
                else:
                    # Replace outlier with mean
                    filtered_values[band] = mean_val
            
            return filtered_values
            
        except Exception as e:
            print(f"⚠️ Outlier filtering error: {e}")
            return band_values