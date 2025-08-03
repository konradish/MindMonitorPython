"""Data validation utilities for EEG analysis."""

import numpy as np
from typing import Dict, List, Any, Tuple
import pandas as pd


class DataValidator:
    """Validates EEG data quality and integrity."""
    
    @staticmethod
    def validate_eeg_data(data: np.ndarray, channel_name: str = "") -> Tuple[bool, List[str]]:
        """
        Validate EEG signal data quality.
        
        Args:
            data: EEG signal data array
            channel_name: Name of the channel for error reporting
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Check for empty data
            if len(data) == 0:
                issues.append(f"Empty data array for {channel_name}")
                return False, issues
            
            # Check for all NaN values
            if np.all(np.isnan(data)):
                issues.append(f"All NaN values in {channel_name}")
                return False, issues
            
            # Check for all zero values
            if np.all(data == 0):
                issues.append(f"All zero values in {channel_name}")
                return False, issues
            
            # Check for excessive NaN ratio
            nan_ratio = np.sum(np.isnan(data)) / len(data)
            if nan_ratio > 0.5:
                issues.append(f"High NaN ratio ({nan_ratio:.1%}) in {channel_name}")
            
            # Check for reasonable EEG amplitude range (microvolts)
            data_clean = data[~np.isnan(data)]
            if len(data_clean) > 0:
                signal_range = np.max(data_clean) - np.min(data_clean)
                
                # Typical EEG range: 50-2000 microvolts
                if signal_range < 10:
                    issues.append(f"Very low signal range ({signal_range:.1f}µV) in {channel_name}")
                elif signal_range > 5000:
                    issues.append(f"Excessive signal range ({signal_range:.1f}µV) in {channel_name}")
            
            # Check for flat line segments
            if len(data_clean) > 10:
                diff = np.diff(data_clean)
                zero_diff_ratio = np.sum(np.abs(diff) < 0.1) / len(diff)
                if zero_diff_ratio > 0.8:
                    issues.append(f"Flat line detected ({zero_diff_ratio:.1%} unchanged) in {channel_name}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Validation error for {channel_name}: {e}")
            return False, issues
    
    @staticmethod
    def validate_band_powers(band_powers: Dict[str, float]) -> Tuple[bool, List[str]]:
        """
        Validate calculated band power values.
        
        Args:
            band_powers: Dictionary of band name to power value
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            required_bands = ['delta', 'theta', 'alpha', 'beta', 'gamma']
            
            # Check for missing bands
            for band in required_bands:
                if band not in band_powers:
                    issues.append(f"Missing {band} band power")
            
            # Check for invalid values
            for band, power in band_powers.items():
                if np.isnan(power) or np.isinf(power):
                    issues.append(f"Invalid {band} power value: {power}")
                elif power < 0:
                    issues.append(f"Negative {band} power: {power}")
            
            # Check for reasonable power distribution
            valid_powers = {k: v for k, v in band_powers.items() 
                          if not (np.isnan(v) or np.isinf(v) or v < 0)}
            
            if valid_powers:
                total_power = sum(valid_powers.values())
                if total_power == 0:
                    issues.append("Total power is zero")
                else:
                    # Check if any single band dominates completely
                    max_power = max(valid_powers.values())
                    if max_power / total_power > 0.98:
                        dominant_band = max(valid_powers.items(), key=lambda x: x[1])[0]
                        issues.append(f"Single band dominance: {dominant_band} = {max_power/total_power:.1%}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Band power validation error: {e}")
            return False, issues
    
    @staticmethod
    def validate_timestamps(timestamps: pd.Series) -> Tuple[bool, List[str]]:
        """
        Validate timestamp data quality.
        
        Args:
            timestamps: Pandas Series of timestamps
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            if len(timestamps) == 0:
                issues.append("Empty timestamp series")
                return False, issues
            
            # Check for NaT values
            nat_count = timestamps.isna().sum()
            if nat_count > 0:
                issues.append(f"{nat_count} invalid timestamps (NaT)")
            
            # Check for reasonable time ordering
            if len(timestamps) > 1:
                time_diffs = timestamps.diff().dropna()
                
                # Check for negative time differences (backwards time)
                negative_diffs = (time_diffs < pd.Timedelta(0)).sum()
                if negative_diffs > 0:
                    issues.append(f"{negative_diffs} backwards time jumps detected")
                
                # Check for reasonable sampling intervals
                if len(time_diffs) > 0:
                    median_interval = time_diffs.median().total_seconds()
                    
                    # Expect intervals between 1ms and 100ms for EEG
                    if median_interval < 0.001:
                        issues.append(f"Very high sampling rate: {1/median_interval:.1f}Hz")
                    elif median_interval > 0.1:
                        issues.append(f"Very low sampling rate: {1/median_interval:.1f}Hz")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"Timestamp validation error: {e}")
            return False, issues
    
    @staticmethod
    def validate_csv_structure(df: pd.DataFrame, expected_format: str) -> Tuple[bool, List[str]]:
        """
        Validate CSV structure for expected format.
        
        Args:
            df: DataFrame to validate
            expected_format: Expected format ('mind_monitor' or 'muse_player')
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            if len(df) == 0:
                issues.append("Empty DataFrame")
                return False, issues
            
            if expected_format == "mind_monitor":
                # Check for essential Mind Monitor columns
                required_cols = ['timestamp_utc', 'eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']
                alternative_cols = ['timestamp_local', 'timestamp']
                
                has_timestamp = any(col in df.columns for col in ['timestamp_utc', 'timestamp_local', 'timestamp'])
                if not has_timestamp:
                    issues.append("No timestamp column found")
                
                eeg_cols = [col for col in required_cols[1:] if col in df.columns]
                if len(eeg_cols) < 4:
                    issues.append(f"Missing EEG channels, found: {eeg_cols}")
            
            elif expected_format == "muse_player":
                # For Muse Player, we expect at least timestamp and message columns
                if len(df.columns) < 2:
                    issues.append("Insufficient columns for Muse Player format")
            
            # Check for reasonable data types
            for col in df.columns:
                if col.startswith('eeg_') or col.startswith('optics_'):
                    try:
                        pd.to_numeric(df[col], errors='coerce')
                    except:
                        issues.append(f"Non-numeric data in {col}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            issues.append(f"CSV structure validation error: {e}")
            return False, issues