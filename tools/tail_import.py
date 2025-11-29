#!/usr/bin/env python3
"""
Live tail CSV ingestion for EEG data with resumable checkpoints.

This script monitors a CSV file for new data and ingests it into TimescaleDB
in near real-time. It maintains checkpoints for resumable processing and 
handles edge cases like partial lines and file rotation.

Usage:
    uv run python tools/tail_import.py --session <UUID> --csv <path>
    uv run python tools/tail_import.py --session <UUID> --csv <path> --poll-interval 500
"""

import argparse
import csv
import hashlib
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# Import existing processors
import sys
sys.path.append(str(Path(__file__).parent.parent))

from consciousness_monitor.data.parsers import detect_format, parse_osc_data
from consciousness_monitor.data.processors import compute_band_powers
from consciousness_monitor.data.models import BandPower
from consciousness_monitor.sinks.timescale_sink import TimescaleSink


@dataclass
class Checkpoint:
    """Represents ingestion checkpoint state."""
    file_path: str
    session_id: str
    byte_offset: int = 0
    line_number: int = 0
    last_ts: Optional[datetime] = None
    file_sha256: Optional[str] = None


class CSVTailer:
    """Live CSV tailer with resumable checkpoints."""
    
    def __init__(self, csv_path: str, session_id: str, 
                 poll_interval: float = 0.5, batch_size: int = 500):
        self.csv_path = Path(csv_path)
        self.session_id = uuid.UUID(session_id)
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self.running = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize database connection and sink
        db_url = os.environ.get(
            'DATABASE_URL', 
            'postgresql://eeg:eegpass@localhost:5432/eeg'
        )
        self.db_conn = psycopg2.connect(db_url)
        self.sink = TimescaleSink(db_url)
        
        # Load checkpoint
        self.checkpoint = self.load_checkpoint()
        
    def load_checkpoint(self) -> Checkpoint:
        """Load existing checkpoint or create new one."""
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT file_path, session_id, byte_offset, line_number, 
                       last_ts, file_sha256
                FROM ingestion_checkpoint 
                WHERE file_path = %s
            """, (str(self.csv_path),))
            
            row = cur.fetchone()
            if row:
                self.logger.info(f"Resuming from checkpoint: byte {row['byte_offset']}, line {row['line_number']}")
                return Checkpoint(
                    file_path=row['file_path'],
                    session_id=str(row['session_id']),
                    byte_offset=row['byte_offset'],
                    line_number=row['line_number'],
                    last_ts=row['last_ts'],
                    file_sha256=row['file_sha256']
                )
            else:
                self.logger.info("Starting fresh ingestion")
                return Checkpoint(
                    file_path=str(self.csv_path),
                    session_id=str(self.session_id)
                )
    
    def save_checkpoint(self, byte_offset: int, line_number: int, last_ts: datetime):
        """Save current checkpoint to database."""
        with self.db_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ingestion_checkpoint 
                (file_path, session_id, byte_offset, line_number, last_ts, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (file_path) 
                DO UPDATE SET 
                    byte_offset = EXCLUDED.byte_offset,
                    line_number = EXCLUDED.line_number,
                    last_ts = EXCLUDED.last_ts,
                    updated_at = now()
            """, (str(self.csv_path), str(self.session_id), byte_offset, line_number, last_ts))
            self.db_conn.commit()
    
    def compute_file_hash(self) -> str:
        """Compute SHA256 hash of file for integrity checking."""
        if not self.csv_path.exists():
            return ""
        
        sha256_hash = hashlib.sha256()
        with open(self.csv_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def is_header_line(self, line: str) -> bool:
        """Check if line is a CSV header."""
        line = line.strip().lower()
        return (line.startswith('timestamp,') or 
                line.startswith('time,') or
                'raw_tp9' in line or
                'raw_af7' in line)
    
    def parse_csv_row(self, line: str) -> Optional[Dict]:
        """Parse a single CSV row into EEG data."""
        try:
            # Use CSV reader to properly handle quoted fields
            reader = csv.reader([line])
            row_data = next(reader)
            
            if len(row_data) < 5:  # Need at least timestamp + 4 channels
                return None
            
            # Parse timestamp and channels based on detected format
            format_type = detect_format(row_data)
            if format_type == 'osc':
                return parse_osc_data(row_data)
            else:
                # Fallback parsing
                timestamp_str = row_data[0]
                try:
                    # Try parsing as float first (Unix timestamp)
                    timestamp = pd.to_datetime(float(timestamp_str), unit='s', utc=True)
                except ValueError:
                    # Try parsing as string
                    timestamp = pd.to_datetime(timestamp_str, utc=True)
                
                return {
                    'timestamp': timestamp,
                    'tp9': float(row_data[1]) if row_data[1] else 0.0,
                    'af7': float(row_data[2]) if row_data[2] else 0.0,
                    'af8': float(row_data[3]) if row_data[3] else 0.0,
                    'tp10': float(row_data[4]) if row_data[4] else 0.0,
                }
        except Exception as e:
            self.logger.warning(f"Failed to parse row: {line.strip()[:100]}... Error: {e}")
            return None
    
    def process_eeg_data(self, eeg_data: Dict) -> Dict:
        """Process raw EEG data into features for database."""
        # Extract channels
        channels = {
            'tp9': eeg_data['tp9'],
            'af7': eeg_data['af7'], 
            'af8': eeg_data['af8'],
            'tp10': eeg_data['tp10']
        }
        
        # Compute band powers using existing processor
        sample_rate = 256  # Muse standard
        window_length = 1.0  # 1 second window
        
        try:
            band_powers = compute_band_powers(
                channels, 
                sample_rate, 
                window_length,
                eeg_data['timestamp']
            )
            
            # Average band powers across channels and compute relative powers
            avg_powers = {
                'delta': np.mean([bp.delta for bp in band_powers.values()]),
                'theta': np.mean([bp.theta for bp in band_powers.values()]),
                'alpha': np.mean([bp.alpha for bp in band_powers.values()]),
                'beta': np.mean([bp.beta for bp in band_powers.values()]),
                'gamma': np.mean([bp.gamma for bp in band_powers.values()])
            }
            
            # Compute total power for relative calculation
            total_power = sum(avg_powers.values())
            
            # Compute relative powers (percentages)
            rel_powers = {
                'alpha_rel': (avg_powers['alpha'] / total_power * 100) if total_power > 0 else 0,
                'beta_rel': (avg_powers['beta'] / total_power * 100) if total_power > 0 else 0,
                'theta_rel': (avg_powers['theta'] / total_power * 100) if total_power > 0 else 0,
                'delta_rel': (avg_powers['delta'] / total_power * 100) if total_power > 0 else 0,
                'gamma_rel': (avg_powers['gamma'] / total_power * 100) if total_power > 0 else 0,
            }
            
            # Compute entropy (simple spectral entropy approximation)
            entropy = -sum([
                (p/100) * np.log2(p/100) if p > 0 else 0 
                for p in rel_powers.values()
            ])
            
            # Convert to database format (matching TimescaleSink expectations)
            return {
                'session_id': str(self.session_id),
                'ts_start': eeg_data['timestamp'],
                'ts_end': eeg_data['timestamp'],  # Single sample
                **rel_powers,
                'entropy': entropy,
                'artifact_flags': {'movement': False, 'blink': False, 'muscle': False},
                'features': {
                    'channels': channels,
                    'avg_powers': avg_powers,
                    'sample_rate': sample_rate
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to process EEG data: {e}")
            return None
    
    def tail_file(self):
        """Main tailing loop."""
        self.running = True
        self.logger.info(f"Starting to tail {self.csv_path}")
        
        if not self.csv_path.exists():
            self.logger.error(f"CSV file does not exist: {self.csv_path}")
            return
        
        batch = []
        buffer = ""
        
        try:
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
                # Seek to checkpoint position
                f.seek(self.checkpoint.byte_offset)
                current_line_num = self.checkpoint.line_number
                
                while self.running:
                    # Read new data
                    chunk = f.read(65536)  # 64KB chunks
                    
                    if not chunk:
                        # No new data, sleep and continue
                        time.sleep(self.poll_interval)
                        continue
                    
                    # Add to buffer and process complete lines
                    buffer += chunk
                    lines = buffer.splitlines(keepends=True)
                    
                    # Keep incomplete line in buffer
                    if lines and not lines[-1].endswith('\n'):
                        complete_lines = lines[:-1]
                        buffer = lines[-1]
                    else:
                        complete_lines = lines
                        buffer = ""
                    
                    # Process each complete line
                    for line in complete_lines:
                        current_line_num += 1
                        
                        # Skip headers
                        if self.is_header_line(line):
                            continue
                        
                        # Parse EEG data
                        eeg_data = self.parse_csv_row(line)
                        if not eeg_data:
                            continue
                        
                        # Process into features
                        processed_data = self.process_eeg_data(eeg_data)
                        if not processed_data:
                            continue
                        
                        batch.append(processed_data)
                        
                        # Batch insert when we have enough data
                        if len(batch) >= self.batch_size:
                            try:
                                self.sink.on_windows(batch)
                                self.logger.info(f"Inserted batch of {len(batch)} windows")
                                
                                # Save checkpoint
                                self.save_checkpoint(
                                    f.tell(), 
                                    current_line_num, 
                                    batch[-1]['ts_start']
                                )
                                
                                batch.clear()
                                
                            except Exception as e:
                                self.logger.error(f"Failed to insert batch: {e}")
                                # Don't clear batch, will retry on next iteration
                    
                    # Update checkpoint periodically even without full batch
                    if complete_lines:
                        self.checkpoint.byte_offset = f.tell()
                        self.checkpoint.line_number = current_line_num
            
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down...")
            self.running = False
        except Exception as e:
            self.logger.error(f"Unexpected error in tail loop: {e}")
            raise
        finally:
            # Insert any remaining data
            if batch:
                try:
                    self.sink.on_windows(batch)
                    self.logger.info(f"Inserted final batch of {len(batch)} windows")
                    
                    self.save_checkpoint(
                        self.checkpoint.byte_offset,
                        self.checkpoint.line_number, 
                        batch[-1]['ts_start']
                    )
                except Exception as e:
                    self.logger.error(f"Failed to insert final batch: {e}")
            
            self.db_conn.close()
            self.logger.info("Tailer shutdown complete")
    
    def stop(self):
        """Stop the tailer."""
        self.running = False


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Live tail CSV ingestion for EEG data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Tail a live recording session
  uv run python tools/tail_import.py --session 12345678-1234-5678-9abc-123456789012 --csv data/live_recording.csv
  
  # Tail with custom polling interval (milliseconds)  
  uv run python tools/tail_import.py --session <UUID> --csv data/recording.csv --poll-interval 1000
  
  # Tail with larger batch size for high-throughput
  uv run python tools/tail_import.py --session <UUID> --csv data/recording.csv --batch-size 1000
        """
    )
    
    parser.add_argument('--session', required=True,
                       help='Session UUID for this ingestion')
    parser.add_argument('--csv', required=True,
                       help='Path to CSV file to tail')
    parser.add_argument('--poll-interval', type=int, default=500,
                       help='Polling interval in milliseconds (default: 500)')
    parser.add_argument('--batch-size', type=int, default=500,
                       help='Batch size for database inserts (default: 500)')
    
    args = parser.parse_args()
    
    # Convert milliseconds to seconds
    poll_interval = args.poll_interval / 1000.0
    
    # Validate session UUID
    try:
        uuid.UUID(args.session)
    except ValueError:
        print(f"Error: Invalid session UUID: {args.session}")
        return 1
    
    # Create and start tailer
    tailer = CSVTailer(
        csv_path=args.csv,
        session_id=args.session,
        poll_interval=poll_interval,
        batch_size=args.batch_size
    )
    
    try:
        tailer.tail_file()
    except KeyboardInterrupt:
        print("\nReceived interrupt, stopping tailer...")
        tailer.stop()
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())