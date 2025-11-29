#!/usr/bin/env python3
"""
Database-enabled consciousness monitor with single-compute architecture.

This script extends the existing consciousness monitor to optionally emit
computed windows and detections to TimescaleDB without duplicating parsing
or computation work.

Usage:
    # DB-only mode (no console UI)
    uv run python consciousness_monitor_db_v2.py --db-only --session-id <UUID> --csv mind_monitor_complete.csv
    
    # UI-only mode (original behavior, no DB)  
    uv run python consciousness_monitor_db_v2.py --ui-only --konrad-mode --cycle-detection --sample-rate 88
    
    # Dual mode (UI + DB) - be cautious of double work
    uv run python consciousness_monitor_db_v2.py --session-id <UUID> --konrad-mode --csv mind_monitor_complete.csv
    
    # Host database access
    DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" uv run python consciousness_monitor_db_v2.py --db-only --session-id <UUID> --csv "C:/projects/MindMonitorPython/mind_monitor_complete.csv"
"""

import argparse
import hashlib
import json
import logging
import os
import signal
import sys
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import subprocess

# Import consciousness monitor
from consciousness_monitor import EnhancedConsciousnessMonitor

# Database components
try:
    import psycopg2
    from consciousness_monitor.sinks.timescale_sink import TimescaleSink
    DB_AVAILABLE = True
except ImportError:
    print("⚠️ Database components not available - install psycopg2")
    DB_AVAILABLE = False


class DatabaseInstrumentedMonitor(EnhancedConsciousnessMonitor):
    """
    Enhanced consciousness monitor that can emit computed windows to database.
    
    This extends the base monitor to optionally write computed band powers
    and detection states to TimescaleDB without duplicating computation.
    """
    
    def __init__(self, db_sink=None, session_id=None, emit_windows=False, 
                 emit_detections=False, **kwargs):
        """
        Initialize monitor with optional database emission.
        
        Args:
            db_sink: TimescaleSink instance for database writes
            session_id: Session UUID for database records
            emit_windows: Whether to emit computed windows to database
            emit_detections: Whether to emit state detections to database
            **kwargs: Arguments for base EnhancedConsciousnessMonitor
        """
        super().__init__(**kwargs)
        
        self.db_sink = db_sink
        self.session_id = session_id
        self.emit_windows = emit_windows
        self.emit_detections = emit_detections
        self.detection_start_time = None  # Track open detection intervals
        self.last_detection_label = None
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Register shutdown handler for graceful detection closure
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown - close open detection intervals."""
        if self.emit_detections and self.db_sink and self.detection_start_time:
            try:
                end_time = datetime.now(timezone.utc)
                self.db_sink.on_detection(
                    session_id=str(self.session_id),
                    start=self.detection_start_time,
                    end=end_time,
                    label=self.last_detection_label or "INTERRUPTED",
                    source="shutdown",
                    extra={"reason": "graceful_shutdown"}
                )
                self.logger.info(f"Closed detection interval on shutdown: {self.last_detection_label}")
            except Exception as e:
                self.logger.error(f"Failed to close detection interval on shutdown: {e}")
        
        # Call original handler or exit
        sys.exit(0)
    
    def _emit_window_to_db(self, timestamp, band_powers, percentage_ratios, 
                          entropy=None, artifacts=None, features=None):
        """Emit computed window data to database."""
        if not self.emit_windows or not self.db_sink:
            return
        
        try:
            # Convert to database format
            window_data = {
                'session_id': str(self.session_id),
                'ts_start': timestamp,
                'ts_end': timestamp,  # Single point in time
                'alpha_rel': percentage_ratios.get('alpha', 0),
                'beta_rel': percentage_ratios.get('beta', 0),
                'theta_rel': percentage_ratios.get('theta', 0),
                'delta_rel': percentage_ratios.get('delta', 0),
                'gamma_rel': percentage_ratios.get('gamma', 0),
                'entropy': entropy or 0,
                'artifact_flags': artifacts or {},
                'features': features or {
                    'band_powers': band_powers,
                    'window_seconds': self.window_seconds,
                    'sample_rate': self.sample_rate
                }
            }
            
            # Emit single window
            self.db_sink.on_windows([window_data])
            
        except Exception as e:
            self.logger.error(f"Failed to emit window to database: {e}")
    
    def _emit_detection_to_db(self, timestamp, label, score=None, extra=None):
        """Emit state detection to database."""
        if not self.emit_detections or not self.db_sink:
            return
        
        try:
            # Close previous detection interval if exists
            if self.detection_start_time and self.last_detection_label:
                self.db_sink.on_detection(
                    session_id=str(self.session_id),
                    start=self.detection_start_time,
                    end=timestamp,
                    label=self.last_detection_label,
                    source="rule",
                    score=score,
                    extra=extra or {}
                )
            
            # Start new detection interval
            self.detection_start_time = timestamp
            self.last_detection_label = label
            
        except Exception as e:
            self.logger.error(f"Failed to emit detection to database: {e}")
    
    def analyze_eeg_window(self, data):
        """Override to inject database emission after computation."""
        # Call parent method to do the actual computation
        result = super().analyze_eeg_window(data)
        
        if result is None:
            return None
        
        # Extract computed values for database emission
        if self.emit_windows:
            try:
                # Get timestamp
                timestamp = datetime.now(timezone.utc)

                # Extract band powers and percentages from result
                band_powers = result.band_powers.as_dict() if result.band_powers else {}
                percentage_ratios = result.band_percentages or {}

                # Compute entropy if not provided
                entropy = 0
                if percentage_ratios:
                    import numpy as np
                    entropy = -sum([
                        (p/100) * np.log2(p/100) if p > 0 else 0
                        for p in percentage_ratios.values()
                    ])

                # Emit to database
                self._emit_window_to_db(
                    timestamp=timestamp,
                    band_powers=band_powers,
                    percentage_ratios=percentage_ratios,
                    entropy=entropy,
                    features={'state': result.state}
                )

                # Debug log
                if self.debug:
                    print(f"🗄️ DB: Window α={percentage_ratios.get('alpha', 0):.1f}% β={percentage_ratios.get('beta', 0):.1f}% δ={percentage_ratios.get('delta', 0):.1f}%", flush=True)

            except Exception as e:
                self.logger.warning(f"Failed to emit window data: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
        
        return result
    
    def analyze_eeg_window_raw(self, data):
        """Override raw processing method to also emit to database."""
        # Call parent method to do the actual computation
        result = super().analyze_eeg_window_raw(data)
        
        if result is None:
            return None
        
        # Extract computed values for database emission (same logic as precomputed)
        if self.emit_windows:
            try:
                # Get timestamp from most recent data
                timestamp = datetime.now(timezone.utc)
                
                # Extract band powers and percentages from result
                band_powers = result.band_powers.as_dict() if result.band_powers else {}
                percentage_ratios = result.band_percentages or {}
                
                # Compute entropy if not provided
                entropy = 0
                if percentage_ratios:
                    entropy = -sum([
                        (p/100) * __import__('numpy').log2(p/100) if p > 0 else 0
                        for p in percentage_ratios.values()
                    ])
                
                # Emit to database
                self._emit_window_to_db(
                    timestamp=timestamp,
                    band_powers=band_powers,
                    percentage_ratios=percentage_ratios,
                    entropy=entropy,
                    features={'analysis_result': result}
                )
                
                # Debug log (visible even in db-only mode for troubleshooting)
                if self.debug:
                    print(f"🗄️ DB: Emitted window α={percentage_ratios.get('alpha', 0):.1f}% β={percentage_ratios.get('beta', 0):.1f}% δ={percentage_ratios.get('delta', 0):.1f}%", flush=True)
                
            except Exception as e:
                self.logger.warning(f"Failed to emit raw window data: {e}")
        
        return result


class DatabaseConsciousnessWrapper:
    """Wrapper that manages database integration with consciousness monitor."""
    
    def __init__(self, session_id: Optional[str] = None, mode: str = 'dual', 
                 csv_path: Optional[str] = None, **monitor_args):
        """
        Initialize database wrapper.
        
        Args:
            session_id: Session UUID (generated if not provided)
            mode: 'db-only', 'ui-only', or 'dual'
            csv_path: Explicit CSV file path
            **monitor_args: Arguments for consciousness monitor
        """
        self.session_id = uuid.UUID(session_id) if session_id else uuid.uuid4()
        self.mode = mode
        self.csv_path = Path(csv_path) if csv_path else Path("mind_monitor_complete.csv")
        self.monitor_args = monitor_args
        
        # Setup logging
        log_level = logging.WARNING if mode == 'db-only' else logging.INFO
        logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Database components
        self.db_url = None
        self.db_conn = None
        self.db_sink = None
        
        if mode in ['db-only', 'dual']:
            self._init_database()
        
        # Initialize instrumented monitor
        self.monitor = None
        self._init_monitor()
    
    def _init_database(self):
        """Initialize database connection and session."""
        if not DB_AVAILABLE:
            self.logger.error("Database components not available")
            return False
        
        try:
            # Get database URL
            self.db_url = os.environ.get(
                'DATABASE_URL',
                'postgresql://eeg:eegpass@db:5432/eeg'  # Container default
            )
            
            # For host execution, use the exposed port by default
            if 'localhost' not in self.db_url and '127.0.0.1' not in self.db_url:
                # If using container URL, try container first, then host
                try:
                    test_conn = psycopg2.connect(self.db_url)
                    test_conn.close()  # Test connection
                except psycopg2.OperationalError:
                    # Fall back to host port
                    self.db_url = 'postgresql://eeg:eegpass@localhost:5590/eeg'
            # If already localhost URL, use as-is
            
            self.db_sink = TimescaleSink(self.db_url)
            self.db_conn = psycopg2.connect(self.db_url)
            
            # Ensure session exists
            self._ensure_session_exists()
            
            self.logger.info(f"Database initialized for session {self.session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            return False
    
    def _ensure_session_exists(self):
        """Create session record with config bundle linkage."""
        try:
            # Get git commit hash for config tracking
            try:
                git_sha = subprocess.check_output(
                    ['git', 'rev-parse', 'HEAD'], 
                    cwd=Path(__file__).parent,
                    text=True
                ).strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                git_sha = 'unknown'
            
            # Compute config hash from monitor arguments
            config_str = str(sorted(self.monitor_args.items()))
            config_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]
            
            with self.db_conn.cursor() as cur:
                # Try to find existing config bundle first
                config_json = json.dumps({
                    'monitor_args': self.monitor_args,
                    'mode': self.mode,
                    'description': f"Consciousness monitor config: konrad_mode={self.monitor_args.get('konrad_mode', False)}"
                })
                
                cur.execute("""
                    SELECT id FROM config_bundle 
                    WHERE git_head_sha = %s AND content_hash = %s
                """, (git_sha, config_hash))
                
                existing = cur.fetchone()
                if existing:
                    config_id = existing[0]
                else:
                    # Create new config bundle with UUID
                    config_bundle_id = str(uuid.uuid4())
                    cur.execute("""
                        INSERT INTO config_bundle (id, git_head_sha, content_hash, content_json, version)
                        VALUES (%s, %s, %s, %s::jsonb, %s)
                        RETURNING id
                    """, (
                        config_bundle_id,
                        git_sha, 
                        config_hash,
                        config_json,
                        'consciousness_monitor_v2'
                    ))
                    config_id = cur.fetchone()[0]
                
                # Create session with existing schema
                sample_rate = self.monitor_args.get('sample_rate')
                if sample_rate is None:
                    sample_rate = 256  # Default value
                
                cur.execute("""
                    INSERT INTO session 
                    (id, subject, started_at, device, sample_rate, config_id, notes)
                    VALUES (%s, %s, now(), %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        config_id = EXCLUDED.config_id,
                        notes = EXCLUDED.notes
                """, (
                    str(self.session_id),
                    os.environ.get('EEG_AUTHOR', 'consciousness_monitor'),
                    'muse_headband',
                    int(sample_rate),
                    config_id,
                    f"Mode: {self.mode}, CSV: {self.csv_path}"
                ))
                
                self.db_conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
    
    def _init_monitor(self):
        """Initialize instrumented consciousness monitor."""
        # Set CSV file path explicitly
        self.monitor_args['csv_file'] = str(self.csv_path)
        
        # Determine emission settings based on mode
        emit_windows = self.mode in ['db-only', 'dual']
        emit_detections = self.mode in ['db-only', 'dual']
        
        # Create instrumented monitor
        self.monitor = DatabaseInstrumentedMonitor(
            db_sink=self.db_sink,
            session_id=self.session_id,
            emit_windows=emit_windows,
            emit_detections=emit_detections,
            **self.monitor_args
        )
    
    def run(self):
        """Run the consciousness monitor."""
        if not self.csv_path.exists():
            self.logger.error(f"CSV file does not exist: {self.csv_path}")
            return False
        
        print(f"🧠 Database Consciousness Monitor v2")
        print(f"📊 Session: {self.session_id}")
        print(f"📁 CSV: {self.csv_path}")
        print(f"🎯 Mode: {self.mode}")
        print(f"🗄️ Database: {'Enabled' if self.db_sink else 'Disabled'}")
        
        if self.mode == 'db-only':
            print("📴 UI disabled - database-only mode")
            
            # In db-only mode, run silently and just process data
            try:
                # Completely disable UI output for db-only mode
                self.monitor.show_bands = False
                self.monitor.show_insights = False
                self.monitor.show_optics = False
                self.monitor.force_output = False
                self.monitor.output_interval = 999999  # Very large value to suppress output
                
                # Check if debug mode is enabled (check both places it might be stored)
                debug_enabled = getattr(self.monitor, 'debug', False) or self.monitor_args.get('debug', False)
                
                # In debug mode, don't suppress stdout so we can see database emissions
                if debug_enabled:
                    print("🔍 Debug mode: Database emissions will be visible")
                    print(f"🔍 Monitor debug flag: {getattr(self.monitor, 'debug', 'not set')}")
                    print(f"🔍 Args debug flag: {self.monitor_args.get('debug', 'not set')}")
                    self.monitor.monitor_realtime()
                else:
                    print("🔇 Running in silent mode (use --debug to see emissions)")
                    # Redirect stdout to suppress all monitor output (except debug)
                    import sys
                    from io import StringIO
                    
                    old_stdout = sys.stdout
                    sys.stdout = StringIO()  # Capture all print statements
                    
                    try:
                        # Run monitor (it will emit to DB via instrumentation)
                        self.monitor.monitor_realtime()
                    finally:
                        # Restore stdout
                        sys.stdout = old_stdout
                
            except KeyboardInterrupt:
                print("\n🛑 Database monitoring stopped")
                
        else:
            # UI mode or dual mode - run normally
            try:
                if self.monitor_args.get('analyze'):
                    self.monitor.analyze_file()
                else:
                    self.monitor.monitor_realtime()
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped")
        
        return True


def main():
    """CLI entry point with explicit mode switches."""
    parser = argparse.ArgumentParser(
        description="Database-enabled Enhanced Consciousness Monitor v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Mode Examples:
  
  # DB-only mode (no UI, silent database ingestion)
  uv run python consciousness_monitor_db_v2.py --db-only --session-id $(uuidgen) --csv "mind_monitor_complete.csv"
  
  # UI-only mode (original behavior, no database)
  uv run python consciousness_monitor_db_v2.py --ui-only --konrad-mode --cycle-detection --sample-rate 88
  
  # Dual mode (UI + Database) - use with caution
  uv run python consciousness_monitor_db_v2.py --session-id $(uuidgen) --konrad-mode --csv "mind_monitor_complete.csv"

Host Database Access:
  DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" uv run python consciousness_monitor_db_v2.py --db-only --session-id $(uuidgen) --csv "C:/projects/MindMonitorPython/mind_monitor_complete.csv"

Verification Commands (copy/paste):
  # Check ingestion progress
  docker compose exec db psql -U eeg -d eeg -c "SELECT count(*) AS n, min(ts_start), max(ts_start) FROM eeg_window WHERE session_id = '<SESSION_UUID>';"
  
  # Check continuous aggregate
  docker compose exec db psql -U eeg -d eeg -c "SELECT * FROM eeg_window_1s WHERE session_id = '<SESSION_UUID>' ORDER BY ts DESC LIMIT 5;"
  
  # Check for duplicates
  docker compose exec db psql -U eeg -d eeg -c "SELECT ts_start, count(*) c FROM eeg_window WHERE session_id = '<SESSION_UUID>' GROUP BY 1 HAVING count(*)>1 ORDER BY ts_start ASC LIMIT 5;"
        """
    )
    
    # Mode switches
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--db-only', action='store_true',
                           help='Database ingestion only (no UI output)')
    mode_group.add_argument('--ui-only', action='store_true', 
                           help='UI only (no database writes)')
    mode_group.add_argument('--dual', action='store_true',
                           help='Both UI and database (requires --double-parse-ok)')
    
    # Database arguments
    parser.add_argument('--session-id', 
                       help='Session UUID for database (auto-generated if not provided)')
    parser.add_argument('--csv', required=True,
                       help='Explicit path to CSV file to monitor')
    parser.add_argument('--double-parse-ok', action='store_true',
                       help='Acknowledge potential timing drift in dual mode')
    
    # All consciousness monitor arguments
    parser.add_argument("--window", "-w", type=float, default=0.75, 
                       help="Analysis window in seconds (default: 0.75)")
    parser.add_argument("--update", "-u", type=float, default=1.0, 
                       help="Update interval in seconds (default: 1.0)")
    parser.add_argument("--sample-rate", type=float, 
                       help="Override sample rate (Hz) - use 88 for meditation.csv format")
    parser.add_argument("--cycle-detection", action="store_true", 
                       help="Enable anxiety-regulation cycle detection (requires --konrad-mode)")
    parser.add_argument("--analyze", "-a", action="store_true", 
                       help="Analyze entire file instead of real-time monitoring")
    parser.add_argument("--no-bands", action="store_true", 
                       help="Hide EEG band power visualization")
    parser.add_argument("--no-insights", action="store_true", 
                       help="Hide psychological insights")
    parser.add_argument("--no-optics", action="store_true", 
                       help="Hide fNIRS optical data")
    parser.add_argument("--raw", action="store_true", 
                       help="Use raw signal processing instead of pre-computed bands")
    parser.add_argument("--force-output", action="store_true", 
                       help="Force output every update (disable smart event detection)")
    parser.add_argument("--output-interval", type=float, 
                       help="Force output every N seconds (overrides smart detection)")
    parser.add_argument("--debug", action="store_true", 
                       help="Show debug information about data updates and rule testing")
    parser.add_argument("--konrad-mode", action="store_true", 
                       help="Enable Konrad's personalized detection patterns (dB-based Security Guard detection)")
    parser.add_argument("--tune-rule", action="append", 
                       help="Tune rule parameters (e.g. --tune-rule jhana.alpha_min=85)")
    parser.add_argument("--load-rules", 
                       help="Load detection rules from JSON file")
    parser.add_argument("--macro-window", type=float, default=60.0, 
                       help="Macro analysis window in seconds for pattern detection (default: 60)")
    parser.add_argument("--dual-mode", action="store_true", 
                       help="Run both micro (real-time) and macro (pattern) analysis simultaneously")
    parser.add_argument("--macro-only", action="store_true", 
                       help="Only show macro patterns, suppress micro readings")
    parser.add_argument("--trend-analysis", action="store_true", 
                       help="Include trend detection (increasing/decreasing/stable)")
    parser.add_argument("--macro-update", type=float, 
                       help="Macro analysis update interval in seconds (default: half of macro window)")
    parser.add_argument("--anxiety-sensitivity", type=float, default=1.0, 
                       help="Multiplier for anxiety detection sensitivity")
    parser.add_argument("--disable-meditation-exemption", action="store_true", 
                       help="Disable meditation exemption for security guard detection during calibration")
    parser.add_argument("--beta-trend-window", type=int, default=5, 
                       help="Number of readings to analyze for beta trend detection (default: 5)")
    
    args = parser.parse_args()
    
    # Determine mode
    if args.db_only:
        mode = 'db-only'
    elif args.ui_only:
        mode = 'ui-only'  
    elif args.dual:
        if not args.double_parse_ok:
            print("❌ Dual mode requires --double-parse-ok flag to acknowledge potential timing drift")
            return 1
        mode = 'dual'
    else:
        print("❌ Must specify one of: --db-only, --ui-only, or --dual")
        return 1
    
    # Validate session ID if provided
    session_id = args.session_id
    if session_id:
        try:
            uuid.UUID(session_id)
        except ValueError:
            print(f"❌ Invalid session UUID: {session_id}")
            return 1
    elif mode in ['db-only', 'dual']:
        # Generate session ID for database modes
        session_id = str(uuid.uuid4())
        print(f"Generated session ID: {session_id}")
    
    # Validate CSV path
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"❌ CSV file does not exist: {csv_path}")
        return 1
    
    # Parse rule tuning
    tune_rules = {}
    if args.tune_rule:
        for rule_tune in args.tune_rule:
            try:
                rule_path, value = rule_tune.split('=')
                parts = rule_path.split('.')
                if len(parts) == 2:
                    rule_name, param = parts
                    if rule_name not in tune_rules:
                        tune_rules[rule_name] = {}
                    tune_rules[rule_name][param] = float(value)
                    print(f"🔧 Rule tuning: {rule_name}.{param} = {value}")
            except ValueError:
                print(f"⚠️ Invalid rule tuning format: {rule_tune}")
    
    # Build monitor arguments
    monitor_args = {
        'window_seconds': args.window,
        'update_interval': args.update,
        'show_bands': not args.no_bands,
        'show_insights': not args.no_insights,
        'show_optics': not args.no_optics,
        'use_precomputed': not args.raw,
        'force_output': args.force_output,
        'output_interval': args.output_interval,
        'debug': args.debug,
        'konrad_mode': args.konrad_mode,
        'tune_rules': tune_rules,
        'load_rules': args.load_rules,
        'macro_window': args.macro_window,
        'dual_mode': args.dual_mode,
        'macro_only': args.macro_only,
        'trend_analysis': args.trend_analysis,
        'macro_update': args.macro_update,
        'anxiety_sensitivity': args.anxiety_sensitivity,
        'disable_meditation_exemption': args.disable_meditation_exemption,
        'beta_trend_window': args.beta_trend_window,
        'sample_rate': args.sample_rate,
        'cycle_detection': args.cycle_detection,
        'analyze': args.analyze
    }
    
    # Create and run wrapper
    try:
        wrapper = DatabaseConsciousnessWrapper(
            session_id=session_id,
            mode=mode,
            csv_path=str(csv_path),
            **monitor_args
        )
        
        success = wrapper.run()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return 0
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())