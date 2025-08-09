"""Data parsers for different EEG data formats."""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import os

from .models import EEGReading
from ..config.settings import Settings


class DataParser:
    """Handles parsing of different EEG data formats."""
    
    def __init__(self):
        self.settings = Settings()
        self.data_columns = self.settings.get_data_columns()
    
    def detect_format(self, csv_file: str) -> str:
        """
        Detect the format of the CSV file.
        
        Args:
            csv_file: Path to the CSV file
            
        Returns:
            Format string: 'mind_monitor', 'muse_player', or 'unknown'
        """
        try:
            if not os.path.exists(csv_file):
                return "unknown"
            
            # Read first few lines to detect format
            with open(csv_file, 'r') as f:
                first_line = f.readline().strip()
            
            if first_line.startswith('timestamp_utc'):
                return "mind_monitor"
            elif ',' in first_line and ('/muse/' in first_line or first_line.split(',')[0].replace('.', '').isdigit()):
                return "muse_player"
            else:
                return "unknown"
                
        except Exception as e:
            print(f"⚠️ Format detection failed: {e}")
            return "unknown"
    
    def detect_sample_rate(self, csv_file: str) -> float:
        """
        Auto-detect effective sample rate from data.
        
        Args:
            csv_file: Path to the CSV file
            
        Returns:
            Detected sample rate in Hz
        """
        try:
            if not os.path.exists(csv_file):
                return self.settings.get_default_sample_rate()
            
            # Try different CSV reading strategies
            df = None
            try:
                df = pd.read_csv(csv_file, nrows=5000)
            except pd.errors.ParserError:
                try:
                    df = pd.read_csv(csv_file, nrows=5000, on_bad_lines='skip')
                except:
                    # Handle variable-width CSV by reading line by line
                    try:
                        rows = []
                        with open(csv_file, 'r') as f:
                            for i, line in enumerate(f):
                                if i >= 5000:  # Limit for speed
                                    break
                                parts = line.strip().split(', ')
                                rows.append(parts)
                        df = pd.DataFrame(rows)
                        print(f"📊 Parsed variable-width CSV: {len(df)} rows")
                    except Exception as e:
                        print(f"📊 Could not parse CSV for sample rate detection ({e}), using default")
                        return self.settings.get_default_sample_rate()
            
            if df is not None and len(df) > 0:
                # Try different timestamp column names
                timestamp_col = None
                for col in ['timestamp_utc', 'timestamp_local', 'TimeStamp', 'timestamp']:
                    if col in df.columns:
                        timestamp_col = col
                        break
                
                # If no named timestamp column, assume first column is timestamp
                if timestamp_col is None and len(df.columns) > 0:
                    timestamp_col = 0  # Use first column as timestamp
                
                if timestamp_col is not None and len(df) > 100:
                    # Filter for EEG data only to get true sample rate
                    eeg_data = df[df.iloc[:, 1] == '/muse/eeg'] if len(df.columns) > 1 else df
                    
                    if len(eeg_data) > 100:
                        # Parse EEG timestamps and get unique values
                        if isinstance(timestamp_col, int):
                            timestamps = pd.to_numeric(eeg_data.iloc[:, timestamp_col], errors='coerce').dropna()
                        else:
                            timestamps = pd.to_numeric(eeg_data[timestamp_col], errors='coerce').dropna()
                        unique_timestamps = timestamps.drop_duplicates().sort_values()
                        
                        if len(unique_timestamps) > 50:
                            total_duration = unique_timestamps.iloc[-1] - unique_timestamps.iloc[0]
                            if total_duration > 0:
                                effective_rate = len(unique_timestamps) / total_duration
                                
                                print(f"📊 EEG samples: {len(timestamps)}, unique timestamps: {len(unique_timestamps)}")
                                print(f"📊 Duration: {total_duration:.2f}s, effective rate: {effective_rate:.1f}Hz")
                                
                                # Cap at reasonable EEG rates
                                if effective_rate > 512:
                                    print(f"📊 Very high rate detected ({effective_rate:.0f}Hz), using 256Hz")
                                    return 256
                                elif effective_rate > 50:  # Accept rates down to 50Hz
                                    print(f"📊 Detected sample rate: {effective_rate:.1f}Hz")
                                    return effective_rate
                                else:
                                    print(f"📊 Very low rate detected ({effective_rate:.1f}Hz), using 256Hz default")
                                    return 256
        except Exception as e:
            print(f"⚠️ Could not detect sample rate: {e}")
        
        # Default fallback
        print("📊 Using default sample rate: 256Hz")
        return self.settings.get_default_sample_rate()
    
    def parse_mind_monitor_csv(self, csv_file: str, max_rows: Optional[int] = None) -> pd.DataFrame:
        """
        Parse Mind Monitor CSV format.
        
        Args:
            csv_file: Path to the CSV file
            max_rows: Maximum number of rows to read
            
        Returns:
            Parsed DataFrame
        """
        try:
            if max_rows:
                df = pd.read_csv(csv_file, nrows=max_rows)
            else:
                df = pd.read_csv(csv_file)
            
            # Ensure timestamp column exists
            if 'timestamp_utc' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp_utc'])
            elif 'timestamp_local' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp_local'])
            else:
                # Create synthetic timestamps if missing
                df['timestamp'] = pd.date_range(
                    start=datetime.now(),
                    periods=len(df),
                    freq='4ms'  # Assume ~256Hz
                )
            
            return df
            
        except Exception as e:
            print(f"⚠️ Failed to parse Mind Monitor CSV: {e}")
            return pd.DataFrame()
    
    def parse_muse_player_csv(self, csv_file: str, max_rows: Optional[int] = None) -> Dict[str, Any]:
        """
        Parse Muse Player CSV format into structured data.
        
        Args:
            csv_file: Path to the CSV file
            max_rows: Maximum number of rows to read
            
        Returns:
            Dictionary with parsed EEG and optics data
        """
        try:
            if max_rows:
                raw_df = pd.read_csv(csv_file, nrows=max_rows, on_bad_lines='skip')
            else:
                raw_df = pd.read_csv(csv_file, on_bad_lines='skip')
            
            # Initialize structured data
            structured_data = {
                'timestamp': [],
                'eeg': {'tp9': [], 'af7': [], 'af8': [], 'tp10': [], 'aux1': [], 'aux2': [], 'aux3': [], 'aux4': []},
                'optics': {'ch1': [], 'ch2': [], 'ch3': [], 'ch4': [], 'ch5': [], 'ch6': [], 'ch7': [], 'ch8': []},
                'markers': []
            }
            
            for _, row in raw_df.iterrows():
                try:
                    timestamp = float(row.iloc[0])
                    message = str(row.iloc[1]) if len(row) > 1 else ""
                    
                    # Parse EEG data
                    if '/muse/eeg' in message:
                        values = [float(x) for x in row.iloc[2:6] if pd.notna(x)]
                        if len(values) == 4:
                            structured_data['timestamp'].append(timestamp)
                            structured_data['eeg']['tp9'].append(values[0])
                            structured_data['eeg']['af7'].append(values[1])
                            structured_data['eeg']['af8'].append(values[2])
                            structured_data['eeg']['tp10'].append(values[3])
                    
                    # Parse AUX data
                    elif '/muse/aux' in message:
                        values = [float(x) for x in row.iloc[2:6] if pd.notna(x)]
                        if len(values) >= 1:
                            for i, val in enumerate(values[:4]):
                                aux_key = f'aux{i+1}'
                                if aux_key in structured_data['eeg']:
                                    structured_data['eeg'][aux_key].append(val)
                    
                    # Parse optics data (fNIRS)
                    elif '/muse/optics' in message:
                        values = [float(x) for x in row.iloc[2:10] if pd.notna(x)]
                        for i, val in enumerate(values[:8]):
                            ch_key = f'ch{i+1}'
                            if ch_key in structured_data['optics']:
                                structured_data['optics'][ch_key].append(val)
                    
                    # Parse markers
                    elif 'marker' in message.lower():
                        structured_data['markers'].append({
                            'timestamp': timestamp,
                            'marker': message
                        })
                        
                except (ValueError, IndexError):
                    continue
            
            return structured_data
            
        except Exception as e:
            print(f"⚠️ Failed to parse Muse Player CSV: {e}")
            return {'timestamp': [], 'eeg': {}, 'optics': {}, 'markers': []}
    
    def get_latest_data(self, csv_file: str, window_samples: int) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Get the latest data window from CSV file.
        
        Args:
            csv_file: Path to the CSV file
            window_samples: Number of samples in the analysis window
            
        Returns:
            Tuple of (DataFrame with latest data, format string)
        """
        if not os.path.exists(csv_file):
            return None, "file_not_found"
        
        format_type = self.detect_format(csv_file)
        
        try:
            if format_type == "mind_monitor":
                # Read latest rows efficiently
                df = pd.read_csv(csv_file)
                if len(df) > window_samples:
                    latest_df = df.tail(window_samples).copy()
                else:
                    latest_df = df.copy()
                
                # Ensure timestamp column
                if 'timestamp_utc' in latest_df.columns:
                    latest_df['timestamp'] = pd.to_datetime(latest_df['timestamp_utc'])
                
                return latest_df, format_type
                
            elif format_type == "muse_player":
                # For large muse_player files, read only the last portion
                # Estimate lines needed (assume ~4 lines per sample for safety)
                lines_needed = window_samples * 6  # More lines than needed for safety
                
                # Read only the tail of the file efficiently
                try:
                    import subprocess
                    result = subprocess.run(['tail', '-n', str(lines_needed), csv_file], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        # Parse these lines instead of the whole file
                        structured_data = self._parse_muse_lines(lines)
                    else:
                        # Fallback to regular parsing with limited rows
                        structured_data = self.parse_muse_player_csv(csv_file, max_rows=lines_needed)
                except:
                    # Fallback to regular parsing with limited rows
                    structured_data = self.parse_muse_player_csv(csv_file, max_rows=lines_needed)
                
                # Convert to DataFrame format similar to Mind Monitor
                if structured_data['timestamp']:
                    # Take only the most recent window_samples
                    recent_count = min(len(structured_data['timestamp']), window_samples)
                    df_data = {
                        'timestamp': structured_data['timestamp'][-recent_count:],
                        'eeg_tp9': structured_data['eeg']['tp9'][-recent_count:],
                        'eeg_af7': structured_data['eeg']['af7'][-recent_count:],
                        'eeg_af8': structured_data['eeg']['af8'][-recent_count:],
                        'eeg_tp10': structured_data['eeg']['tp10'][-recent_count:],
                    }
                    
                    # Add optics data if available
                    for ch in ['ch1', 'ch2', 'ch3', 'ch4']:
                        if ch in structured_data['optics'] and structured_data['optics'][ch]:
                            df_data[f'optics_{ch}'] = structured_data['optics'][ch][-recent_count:]
                    
                    # Ensure all arrays are the same length
                    min_length = min(len(v) for v in df_data.values())
                    for key in df_data:
                        df_data[key] = df_data[key][-min_length:]
                    
                    if min_length > 0:
                        latest_df = pd.DataFrame(df_data)
                        latest_df['timestamp'] = pd.to_datetime(latest_df['timestamp'], unit='s')
                        return latest_df, format_type
                    else:
                        return None, format_type
                else:
                    return None, format_type
            
            else:
                print(f"⚠️ Unknown format: {format_type}")
                return None, format_type
                
        except Exception as e:
            print(f"⚠️ Error getting latest data: {e}")
            return None, "error"
    
    def _parse_muse_lines(self, lines: List[str]) -> Dict[str, Any]:
        """Parse a list of muse lines efficiently."""
        structured_data = {
            'timestamp': [],
            'eeg': {'tp9': [], 'af7': [], 'af8': [], 'tp10': []},
            'optics': {},
            'markers': []
        }
        
        for line in lines:
            try:
                parts = line.strip().split(',')
                if len(parts) < 2:
                    continue
                
                timestamp = float(parts[0])
                message = parts[1].strip()
                
                # Parse EEG data
                if '/muse/eeg' in message and len(parts) >= 6:
                    values = [float(parts[i]) for i in range(2, 6)]
                    structured_data['timestamp'].append(timestamp)
                    structured_data['eeg']['tp9'].append(values[0])
                    structured_data['eeg']['af7'].append(values[1])
                    structured_data['eeg']['af8'].append(values[2])
                    structured_data['eeg']['tp10'].append(values[3])
                    
            except (ValueError, IndexError):
                continue
        
        return structured_data
    
    def extract_eeg_channels(self, df: pd.DataFrame, format_type: str) -> Dict[str, np.ndarray]:
        """
        Extract EEG channel data from DataFrame.
        
        Args:
            df: DataFrame with EEG data
            format_type: Data format type
            
        Returns:
            Dictionary of channel name to signal data
        """
        channels = {}
        
        try:
            if format_type == "mind_monitor":
                # Standard Mind Monitor columns
                for col in self.data_columns.eeg_columns:
                    if col in df.columns:
                        channel_name = col.replace('eeg_', '')
                        channels[channel_name] = df[col].values
            
            elif format_type == "muse_player":
                # Muse Player format (already processed)
                for col in df.columns:
                    if col.startswith('eeg_'):
                        channel_name = col.replace('eeg_', '')
                        channels[channel_name] = df[col].values
            
            # Remove channels with all NaN values
            channels = {k: v for k, v in channels.items() if not np.all(np.isnan(v))}
            
        except Exception as e:
            print(f"⚠️ Error extracting EEG channels: {e}")
        
        return channels