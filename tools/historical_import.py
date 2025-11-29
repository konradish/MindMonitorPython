#!/usr/bin/env python3
"""
Chunked historical import for large CSV files with resumable checkpoints.

This script processes large CSV files in chunks, maintaining checkpoints for 
resumable processing. It's designed for one-shot historical imports of existing
EEG recordings into TimescaleDB.

Usage:
    uv run python tools/historical_import.py --session <UUID> --csv <path>
    uv run python tools/historical_import.py --session <UUID> --csv <path> --chunk-size 10000
"""

import argparse
import hashlib
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional
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


class HistoricalImporter:
    """Chunked historical CSV importer with resumable checkpoints."""
    
    def __init__(self, csv_path: str, session_id: str, chunk_size: int = 10000):
        self.csv_path = Path(csv_path)
        self.session_id = uuid.UUID(session_id)
        self.chunk_size = chunk_size
        
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
    
    def get_checkpoint(self) -> Dict:
        """Get current checkpoint for this file."""
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT byte_offset, line_number, last_ts, file_sha256
                FROM ingestion_checkpoint 
                WHERE file_path = %s
            """, (str(self.csv_path),))
            
            row = cur.fetchone()
            return dict(row) if row else {}
    
    def save_checkpoint(self, byte_offset: int, line_number: int, 
                       last_ts: datetime, file_sha256: str):
        """Save checkpoint to database."""
        with self.db_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ingestion_checkpoint 
                (file_path, session_id, byte_offset, line_number, last_ts, file_sha256, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, now())
                ON CONFLICT (file_path) 
                DO UPDATE SET 
                    byte_offset = EXCLUDED.byte_offset,
                    line_number = EXCLUDED.line_number,
                    last_ts = EXCLUDED.last_ts,
                    file_sha256 = EXCLUDED.file_sha256,
                    updated_at = now()
            """, (str(self.csv_path), str(self.session_id), byte_offset, 
                  line_number, last_ts, file_sha256))
            self.db_conn.commit()
    
    def compute_file_hash(self) -> str:
        """Compute SHA256 hash of entire file."""
        if not self.csv_path.exists():
            return ""
        
        sha256_hash = hashlib.sha256()
        with open(self.csv_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def detect_csv_format(self) -> str:
        """Detect CSV format by examining first few rows."""
        try:
            # Read first few rows to detect format
            sample_df = pd.read_csv(self.csv_path, nrows=5)
            
            # Check column names to identify format
            columns = [col.lower() for col in sample_df.columns]
            
            if any('raw_tp9' in col or 'raw_af7' in col for col in columns):
                return 'osc'
            elif 'timestamp' in columns or 'time' in columns:
                return 'generic'
            else:
                return 'unknown'
                
        except Exception as e:
            self.logger.error(f"Failed to detect CSV format: {e}")
            return 'unknown'
    
    def process_chunk(self, chunk_df: pd.DataFrame) -> List[Dict]:
        """Process a chunk of CSV data into database format."""
        processed_data = []
        
        for _, row in chunk_df.iterrows():
            try:
                # Convert row to dict and detect format
                row_data = row.tolist()
                format_type = detect_format(row_data)
                
                if format_type == 'osc':
                    eeg_data = parse_osc_data(row_data)
                else:
                    # Generic parsing fallback
                    timestamp_col = 'timestamp' if 'timestamp' in chunk_df.columns else chunk_df.columns[0]
                    timestamp = pd.to_datetime(row[timestamp_col], utc=True)
                    
                    # Try to find channel columns
                    eeg_data = {
                        'timestamp': timestamp,
                        'tp9': row.get('RAW_TP9', row.get('tp9', 0.0)),
                        'af7': row.get('RAW_AF7', row.get('af7', 0.0)),
                        'af8': row.get('RAW_AF8', row.get('af8', 0.0)),
                        'tp10': row.get('RAW_TP10', row.get('tp10', 0.0)),
                    }
                
                if not eeg_data:
                    continue
                
                # Extract channels for processing
                channels = {
                    'tp9': float(eeg_data['tp9']),
                    'af7': float(eeg_data['af7']), 
                    'af8': float(eeg_data['af8']),
                    'tp10': float(eeg_data['tp10'])
                }
                
                # Compute band powers
                sample_rate = 256  # Muse standard
                window_length = 1.0  # 1 second window
                
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
                processed_data.append({
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
                })
                
            except Exception as e:
                self.logger.warning(f"Failed to process row: {e}")
                continue
        
        return processed_data
    
    def import_csv(self):
        """Main import function with chunked processing."""
        if not self.csv_path.exists():
            self.logger.error(f"CSV file does not exist: {self.csv_path}")
            return False
        
        self.logger.info(f"Starting historical import of {self.csv_path}")
        
        # Compute file hash for integrity checking
        file_hash = self.compute_file_hash()
        self.logger.info(f"File SHA256: {file_hash}")
        
        # Check existing checkpoint
        checkpoint = self.get_checkpoint()
        start_row = checkpoint.get('line_number', 0)
        
        if checkpoint and checkpoint.get('file_sha256') == file_hash:
            self.logger.info(f"Resuming from row {start_row}")
        else:
            self.logger.info("Starting fresh import")
            start_row = 0
        
        # Detect CSV format
        csv_format = self.detect_csv_format()
        self.logger.info(f"Detected CSV format: {csv_format}")
        
        try:
            # Use pandas chunked reading for memory efficiency
            chunk_iter = pd.read_csv(
                self.csv_path,
                chunksize=self.chunk_size,
                skiprows=range(1, start_row + 1) if start_row > 0 else None,
                low_memory=False
            )
            
            total_processed = start_row
            total_inserted = 0
            
            for chunk_num, chunk_df in enumerate(chunk_iter):
                self.logger.info(f"Processing chunk {chunk_num + 1}, rows {total_processed + 1}-{total_processed + len(chunk_df)}")
                
                # Process chunk into database format
                processed_data = self.process_chunk(chunk_df)
                
                if processed_data:
                    try:
                        # Insert batch into database
                        self.sink.on_windows(processed_data)
                        total_inserted += len(processed_data)
                        
                        self.logger.info(f"Inserted {len(processed_data)} windows from chunk {chunk_num + 1}")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to insert chunk {chunk_num + 1}: {e}")
                        raise
                
                # Update progress
                total_processed += len(chunk_df)
                
                # Save checkpoint every chunk
                if processed_data:
                    last_ts = processed_data[-1]['ts_start']
                    self.save_checkpoint(0, total_processed, last_ts, file_hash)
                
                # Progress logging
                if (chunk_num + 1) % 10 == 0:
                    self.logger.info(f"Progress: {total_processed} rows processed, {total_inserted} windows inserted")
            
            self.logger.info(f"Import complete: {total_processed} rows processed, {total_inserted} windows inserted")
            return True
            
        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            raise
        finally:
            self.db_conn.close()
    
    def validate_import(self):
        """Validate the imported data."""
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Count records for this session
            cur.execute("""
                SELECT COUNT(*) as count,
                       MIN(ts_start) as min_time,
                       MAX(ts_start) as max_time
                FROM eeg_window 
                WHERE session_id = %s
            """, (str(self.session_id),))
            
            result = cur.fetchone()
            
            self.logger.info(f"Validation - Session {self.session_id}:")
            self.logger.info(f"  Records: {result['count']}")
            self.logger.info(f"  Time range: {result['min_time']} to {result['max_time']}")
            
            # Check for data continuity
            cur.execute("""
                SELECT ts_start,
                       LAG(ts_start) OVER (ORDER BY ts_start) as prev_ts,
                       EXTRACT(EPOCH FROM (ts_start - LAG(ts_start) OVER (ORDER BY ts_start))) as gap_seconds
                FROM eeg_window 
                WHERE session_id = %s
                ORDER BY ts_start
                LIMIT 100
            """, (str(self.session_id),))
            
            gaps = [row for row in cur.fetchall() if row['gap_seconds'] and row['gap_seconds'] > 2.0]
            if gaps:
                self.logger.warning(f"Found {len(gaps)} gaps > 2 seconds in data")
                for gap in gaps[:5]:  # Show first 5 gaps
                    self.logger.warning(f"  Gap: {gap['gap_seconds']:.1f}s at {gap['ts_start']}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Chunked historical import for large CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import large historical recording
  uv run python tools/historical_import.py --session 12345678-1234-5678-9abc-123456789012 --csv data/large_recording.csv
  
  # Import with custom chunk size
  uv run python tools/historical_import.py --session <UUID> --csv data/recording.csv --chunk-size 5000
  
  # Validate import after completion
  uv run python tools/historical_import.py --session <UUID> --csv data/recording.csv --validate-only
        """
    )
    
    parser.add_argument('--session', required=True,
                       help='Session UUID for this import')
    parser.add_argument('--csv', required=True,
                       help='Path to CSV file to import')
    parser.add_argument('--chunk-size', type=int, default=10000,
                       help='Number of rows to process per chunk (default: 10000)')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate existing import, do not import')
    
    args = parser.parse_args()
    
    # Validate session UUID
    try:
        uuid.UUID(args.session)
    except ValueError:
        print(f"Error: Invalid session UUID: {args.session}")
        return 1
    
    # Create importer
    importer = HistoricalImporter(
        csv_path=args.csv,
        session_id=args.session,
        chunk_size=args.chunk_size
    )
    
    try:
        if args.validate_only:
            importer.validate_import()
        else:
            success = importer.import_csv()
            if success:
                importer.validate_import()
            return 0 if success else 1
    except KeyboardInterrupt:
        print("\nReceived interrupt, stopping import...")
        return 1
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())