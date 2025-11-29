"""
Refactored Enhanced Consciousness Monitor - Main orchestrator class.

This is the main entry point that coordinates all the modular components
while maintaining backward compatibility with the original API.
"""

import os
import time
import argparse
import uuid
from datetime import datetime
from typing import Dict, Optional, Any, List
import pandas as pd

# Import modular components
from .config import RuleManager, ArtifactThresholds, Settings
from .data import DataParser, SignalProcessor, EEGReading, AnalysisResult
from .detection import DetectionEngine, TherapeuticPatterns
from .ui import DisplayManager, CommandInterface, ReportGenerator
from .data.models import BandPower

# Import sink for database integration
try:
    from .sinks import TimescaleSink
    TIMESCALE_AVAILABLE = True
except ImportError:
    TIMESCALE_AVAILABLE = False


class EnhancedConsciousnessMonitor:
    """
    Main orchestrator for the Enhanced Consciousness Monitor.
    
    Maintains backward compatibility while using modular architecture.
    """
    
    def __init__(self, csv_file="mind_monitor_complete.csv", window_seconds=0.75,
                 update_interval=1.0, show_bands=True, show_insights=True,
                 show_optics=True, use_precomputed=True, force_output=False,
                 output_interval=None, debug=False, konrad_mode=False,
                 tune_rules=None, load_rules=None, gamma_sensitivity=1.0,
                 positive_bias=False, **kwargs):
        
        # Store configuration
        self.csv_file = csv_file
        self.window_seconds = window_seconds
        self.update_interval = update_interval or 1.0
        self.use_precomputed = use_precomputed
        self.force_output = force_output
        self.output_interval = output_interval or (30 if not force_output else self.update_interval)
        self.debug = debug
        self.konrad_mode = konrad_mode
        self.gamma_sensitivity = gamma_sensitivity
        self.positive_bias = positive_bias
        
        # Initialize settings and detect file format
        self.settings = Settings()
        self.data_parser = DataParser()
        self.data_format = self.data_parser.detect_format(csv_file)
        self.sample_rate = self.data_parser.detect_sample_rate(csv_file)
        self.window_samples = int(window_seconds * self.sample_rate)
        
        # Auto-switch to raw processing for formats with raw EEG data
        if self.data_format in ("muse_player", "osc_receiver") and use_precomputed:
            print(f"📊 {self.data_format} format detected - switching to raw signal processing")
            self.use_precomputed = False
        else:
            self.use_precomputed = use_precomputed
        
        # Initialize configuration managers
        self.rule_manager = RuleManager()
        self.artifact_thresholds = ArtifactThresholds()
        
        # Apply rule tuning and loading
        if tune_rules:
            self._apply_rule_tuning(tune_rules)
        if load_rules:
            self.rule_manager.load_custom_rules(load_rules)
        
        # Initialize signal processor
        self.signal_processor = SignalProcessor(self.sample_rate)
        
        # Initialize detection engine
        self.detection_engine = DetectionEngine(
            rule_manager=self.rule_manager,
            artifact_thresholds=self.artifact_thresholds,
            debug=debug,
            konrad_mode=konrad_mode
        )
        
        # Initialize therapeutic patterns analyzer
        self.therapeutic_patterns = TherapeuticPatterns(self.rule_manager)
        
        # Initialize UI components
        self.display_manager = DisplayManager(
            show_bands=show_bands,
            show_insights=show_insights,
            show_optics=show_optics
        )
        
        self.command_interface = CommandInterface()
        self.report_generator = ReportGenerator()
        
        # Register command handlers
        self._setup_command_handlers()
        
        # Session tracking
        self.last_file_size = 0
        self.session_start = time.time()
        self.last_output_time = 0
        self.last_state = None
        self.session_id = str(uuid.uuid4())  # Generate unique session ID
        
        # Initialize TimescaleSink if available
        self.sink = None
        if TIMESCALE_AVAILABLE and os.environ.get('DATABASE_URL'):
            try:
                self.sink = TimescaleSink()
                if self.debug:
                    print(f"✅ TimescaleSink initialized for session {self.session_id}")
            except Exception as e:
                if self.debug:
                    print(f"⚠️  TimescaleSink initialization failed: {e}")
                self.sink = None
        
        # Display startup information
        self._display_startup_info()
    
    def _apply_rule_tuning(self, tune_rules: Dict[str, Dict[str, float]]):
        """Apply command-line rule tuning."""
        for rule_name, params in tune_rules.items():
            if rule_name == "artifact":
                # Handle artifact threshold tuning
                for param, value in params.items():
                    self.artifact_thresholds.tune_threshold(param, value)
            else:
                # Handle detection rule tuning
                for param, value in params.items():
                    rule_path = f"{rule_name}.{param}"
                    self.rule_manager.tune_rule(rule_path, value)
    
    def _setup_command_handlers(self):
        """Setup interactive command handlers."""
        self.command_interface.register_handler('copy_events', self._copy_recent_events)
        self.command_interface.register_handler('show_summary', self._show_session_summary)
        self.command_interface.register_handler('force_output', self._force_immediate_output)
        self.command_interface.register_handler('toggle_debug', self._toggle_debug_mode)
    
    def _display_startup_info(self):
        """Display startup information."""
        config = {
            'mode': "Pre-computed Features" if self.use_precomputed else "Raw Signal Processing",
            'konrad_mode': self.konrad_mode,
            'data_format': self.data_format,
            'window_seconds': self.window_seconds,
            'update_interval': self.update_interval,
            'sample_rate': self.sample_rate,
            'features': 'EEG + fNIRS + Therapeutic Pattern Detection',
            'debug': self.debug,
            'rule_version': self.rule_manager.get_version(),
            'num_rules': len(self.rule_manager.get_detection_rules()),
            'therapeutic_patterns': 'Jhana States, Parts Work (Young/Hopeful/Cautious), Startled Response, Safety Visualization',
            'sub_states': 'Flow (Engaged/Absorbed/Processing/Creative), Jhana (Entry/Stable/Deepening)',
            'artifact_features': 'Multi-band spikes, impossible combinations, extreme shifts',
            'hotkey_message': " | Commands: 'c' (copy), 's' (summary), 'n' (now), 'q' (quit)"
        }
        
        self.display_manager.display_startup_info(config)
    
    def analyze_eeg_window(self, data: Dict[str, Any]) -> AnalysisResult:
        """
        Analyze a window of EEG data.
        
        Args:
            data: Dictionary containing EEG channel data
            
        Returns:
            AnalysisResult with detected state and analysis
        """
        try:
            if self.debug:
                print(f"Main - analyze_eeg_window called with: {type(data)}")
            timestamp = datetime.now()
            
            # Extract channel data
            if self.debug:
                print(f"Main - Extracting channels, format: {self.data_format}")
                print(f"Main - Data keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
            if self.data_format == "mind_monitor":
                channels = self._extract_mind_monitor_channels(data)
            else:
                channels = self._extract_channels_generic(data)
            if self.debug:
                print(f"Main - Channels extracted: {len(channels) if channels else 0}")
            
            if not channels:
                return self._get_no_signal_result(timestamp)
            
            # Calculate band powers using signal processor
            if self.debug:
                print(f"Main - Calculating band powers, channels: {len(channels)}")
            if len(channels) == 1:
                # Single channel analysis
                channel_data = list(channels.values())[0]
                band_power = self.signal_processor.calculate_all_band_powers(channel_data)
            else:
                # Multi-channel average
                band_power = self.signal_processor.calculate_multichannel_average(channels)
            if self.debug:
                print(f"Main - Band power calculated: {type(band_power)}")
            
            # Detect consciousness state using detection engine
            if self.debug:
                print(f"Main - Calling detection engine with {type(band_power)}")
            result = self.detection_engine.analyze_bands(band_power, timestamp)
            if self.debug:
                print(f"Main - Detection engine returned: {result.state}")
            
            # Add therapeutic pattern insights
            if self.debug:
                print(f"Main - Getting therapeutic insights")
            try:
                therapeutic_insights = self._get_therapeutic_insights(result)
                result.insights.extend(therapeutic_insights)
                if self.debug:
                    print(f"Main - Therapeutic insights added: {len(therapeutic_insights)}")
            except Exception as e:
                if self.debug:
                    print(f"Main - Therapeutic insights failed: {e}")
                    import traceback
                    traceback.print_exc()
                raise e
            
            # Add optics data if available
            optics_data = self._extract_optics_data(data)
            if optics_data:
                result.optics_data = optics_data
            
            return result
            
        except Exception as e:
            if self.debug:
                self.display_manager.display_error(f"Analysis failed: {e}")
            return self._get_no_signal_result()
    
    def _extract_mind_monitor_channels(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract EEG channels from Mind Monitor format data."""
        channels = {}
        
        # Handle direct channels data (from data parser)
        if 'channels' in data:
            return data['channels']
        
        # Handle DataFrame format (legacy)
        if 'df' in data and hasattr(data['df'], 'columns'):
            df = data['df']
            for col in self.settings.get_data_columns().eeg_columns:
                if col in df.columns:
                    channel_name = col.replace('eeg_', '')
                    channels[channel_name] = df[col].values
        
        return channels
    
    def _extract_channels_generic(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract EEG channels from generic data format."""
        channels = {}
        
        # Handle different data structures
        if isinstance(data, dict):
            if 'eeg' in data:
                # Structured EEG data
                eeg_data = data['eeg']
                for channel, values in eeg_data.items():
                    if values and len(values) > 0:
                        import numpy as np
                        channels[channel] = np.array(values)
            elif 'channels' in data:
                # Direct channel data
                if self.debug:
                    print(f"Main - Found channels in data: {list(data['channels'].keys())}")
                for channel, values in data['channels'].items():
                    if values is not None and len(values) > 0:
                        import numpy as np
                        if self.debug:
                            print(f"Main - Processing channel {channel}, type: {type(values)}")
                        channels[channel] = np.array(values)
                        if self.debug:
                            print(f"Main - Channel {channel} processed successfully")
        
        return channels
    
    def _extract_optics_data(self, data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract fNIRS optics data if available."""
        optics_data = {}
        
        try:
            if isinstance(data, dict) and 'optics' in data:
                optics = data['optics']
                for channel, values in optics.items():
                    if values and len(values) > 0:
                        # Use the latest value
                        optics_data[channel] = values[-1]
            
            return optics_data if optics_data else None
            
        except Exception:
            return None
    
    def _get_therapeutic_insights(self, result: AnalysisResult) -> List[str]:
        """Get additional therapeutic pattern insights."""
        insights = []
        
        try:
            # Get different types of therapeutic insights
            parts_insights = self.therapeutic_patterns.detect_parts_work_patterns(result)
            meditation_insights = self.therapeutic_patterns.detect_meditation_patterns(result)
            nervous_system_insights = self.therapeutic_patterns.detect_nervous_system_patterns(result)
            unusual_insights = self.therapeutic_patterns.detect_unusual_patterns(result)
            
            insights.extend(parts_insights)
            insights.extend(meditation_insights)
            insights.extend(nervous_system_insights)
            insights.extend(unusual_insights)
            
        except Exception as e:
            if self.debug:
                insights.append(f"⚠️ Therapeutic analysis error: {e}")
        
        return insights
    
    def monitor_realtime(self):
        """Main real-time monitoring loop."""
        print("🧠 Starting real-time consciousness monitoring...")
        print("Press 'q' to quit, 'h' for help")
        
        try:
            while True:
                # Check for user commands
                command = self.command_interface.check_for_commands()
                if command:
                    if not self.command_interface.process_command(command, {'monitor': self}):
                        break  # User requested quit
                
                # Get latest data
                latest_data, format_type = self.data_parser.get_latest_data(
                    self.csv_file, self.window_samples
                )
                
                if latest_data is not None and len(latest_data) > 0:
                    # Analyze the data
                    if self.use_precomputed:
                        result = self._analyze_precomputed_data(latest_data)
                    else:
                        channels = self.data_parser.extract_eeg_channels(latest_data, format_type)
                        result = self.analyze_eeg_window({'channels': channels})
                    
                    # Display results
                    should_display = self._should_display_output(result)
                    if should_display:
                        self.display_manager.display_analysis_result(result)
                        self._track_session_event(result)
                        self.last_output_time = time.time()
                        self.last_state = result.state
                
                else:
                    # No data available
                    if time.time() - self.last_output_time > 5.0:  # Show waiting message every 5 seconds
                        self.display_manager.display_no_signal()
                        self.last_output_time = time.time()
                
                # Sleep until next update
                time.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")
        except Exception as e:
            self.display_manager.display_error(f"Monitoring error: {e}")
        finally:
            self.command_interface.shutdown()
    
    def _analyze_precomputed_data(self, df) -> AnalysisResult:
        """Analyze data using precomputed band powers from Mind Monitor."""
        try:
            timestamp = datetime.now()
            
            # Extract precomputed relative band powers
            data_columns = self.settings.get_data_columns()
            band_percentages = {}
            
            for i, band in enumerate(['delta', 'theta', 'alpha', 'beta', 'gamma']):
                col_name = data_columns.rel_band_columns[i]
                if col_name in df.columns:
                    # Use the latest value and convert to percentage
                    latest_value = df[col_name].iloc[-1]
                    band_percentages[band] = latest_value * 100  # Convert from ratio to percentage
                else:
                    band_percentages[band] = 0.0
            
            # Create BandPower object (convert percentages back to relative powers for processing)
            total_percentage = sum(band_percentages.values())
            if total_percentage > 0:
                normalized_powers = {k: v / total_percentage for k, v in band_percentages.items()}
            else:
                normalized_powers = {k: 0.2 for k in band_percentages.keys()}  # Equal distribution fallback
            
            band_power = BandPower(
                delta=normalized_powers['delta'],
                theta=normalized_powers['theta'],
                alpha=normalized_powers['alpha'],
                beta=normalized_powers['beta'],
                gamma=normalized_powers['gamma']
            )
            
            # Use detection engine to analyze
            result = self.detection_engine.analyze_bands(band_power, timestamp)
            
            # Add optics data if available
            optics_data = self._extract_optics_from_df(df)
            if optics_data:
                result.optics_data = optics_data
            
            # Add therapeutic insights
            therapeutic_insights = self._get_therapeutic_insights(result)
            result.insights.extend(therapeutic_insights)
            
            return result
            
        except Exception as e:
            if self.debug:
                self.display_manager.display_error(f"Precomputed analysis failed: {e}")
            return self._get_no_signal_result()
    
    def _extract_optics_from_df(self, df) -> Optional[Dict[str, float]]:
        """Extract optics data from DataFrame."""
        optics_data = {}
        
        try:
            # Look for optics columns
            optics_cols = [col for col in df.columns if 'optics' in col.lower() or col.startswith('aux')]
            
            for col in optics_cols:
                if len(df[col]) > 0:
                    latest_value = df[col].iloc[-1]
                    if not pd.isna(latest_value):
                        optics_data[col] = float(latest_value)
            
            return optics_data if optics_data else None
            
        except Exception:
            return None
    
    def _should_display_output(self, result: AnalysisResult) -> bool:
        """Determine if output should be displayed based on smart filtering."""
        if self.force_output:
            return True
        
        current_time = time.time()
        
        # Always show if enough time has passed
        if current_time - self.last_output_time >= self.output_interval:
            return True
        
        # Show if state changed
        if self.last_state != result.state:
            return True
        
        # Show if artifacts detected
        if result.has_artifacts():
            return True
        
        # Show if security guard or other significant events
        if 'security' in result.state.lower() or 'jhana' in result.state.lower():
            return True
        
        return False
    
    def _track_session_event(self, result: AnalysisResult):
        """Track session events for reporting."""
        timestamp = result.timestamp or datetime.now()
        text = f"{result.emoji} {result.get_display_name()}"
        
        self.report_generator.track_event(
            timestamp=timestamp,
            text=text,
            state=result.state,
            ratios=result.band_percentages
        )
        
        # Send to TimescaleSink if available
        if self.sink:
            try:
                self._send_to_timescale(result, timestamp)
            except Exception as e:
                if self.debug:
                    print(f"⚠️  TimescaleSink error: {e}")
    
    def _send_to_timescale(self, result: AnalysisResult, timestamp: datetime):
        """Send analysis result to TimescaleDB."""
        # Create window data
        window_data = {
            'session_id': self.session_id,
            'ts_start': timestamp.isoformat(),
            'ts_end': timestamp.isoformat(),  # Single-point window
            'alpha_rel': result.band_percentages.get('alpha', 0.0) / 100.0,
            'beta_rel': result.band_percentages.get('beta', 0.0) / 100.0,
            'theta_rel': result.band_percentages.get('theta', 0.0) / 100.0,
            'delta_rel': result.band_percentages.get('delta', 0.0) / 100.0,
            'gamma_rel': result.band_percentages.get('gamma', 0.0) / 100.0,
            'entropy': getattr(result, 'entropy', None),
            'artifact_flags': getattr(result, 'artifact_flags', {}),
            'features': {
                'state': result.state,
                'display_name': result.get_display_name(),
                'has_artifacts': result.has_artifacts()
            }
        }
        
        # Send window data
        self.sink.on_windows([window_data])
        
        # Send detection if it's a significant state
        if result.state != "NO_SIGNAL" and result.state != "BASELINE":
            self.sink.on_detection(
                session_id=self.session_id,
                start=timestamp.isoformat(),
                end=timestamp.isoformat(),
                label=result.get_display_name(),
                source="rule",
                score=getattr(result, 'confidence_score', None),
                extra={'emoji': result.emoji, 'insights': result.insights}
            )
    
    def _get_no_signal_result(self, timestamp=None) -> AnalysisResult:
        """Create a no-signal result."""
        return AnalysisResult(
            timestamp=timestamp or datetime.now(),
            state="NO_SIGNAL",
            emoji="❓",
            insights=["No clear signal detected"],
            band_percentages={band: 0.0 for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']}
        )
    
    # Command handler methods
    def _copy_recent_events(self, context: Dict[str, Any]):
        """Copy recent events to clipboard."""
        events_text = self.report_generator.generate_recent_events()
        self.command_interface.copy_to_clipboard(events_text)
    
    def _show_session_summary(self, context: Dict[str, Any]):
        """Show session summary."""
        summary_text = self.report_generator.generate_session_summary_text()
        print("\n" + summary_text + "\n")
    
    def _force_immediate_output(self, context: Dict[str, Any]):
        """Force immediate output."""
        print("⚡ Forcing immediate output...")
        self.last_output_time = 0  # Reset timer to force next output
    
    def _toggle_debug_mode(self, context: Dict[str, Any]):
        """Toggle debug mode."""
        self.debug = not self.debug
        self.detection_engine.debug = self.debug
        status = "enabled" if self.debug else "disabled"
        print(f"🔍 Debug mode {status}")
    
    def analyze_file(self):
        """Analyze entire file (batch processing)."""
        print(f"📊 Analyzing file: {self.csv_file}")
        
        try:
            if self.data_format == "mind_monitor":
                df = self.data_parser.parse_mind_monitor_csv(self.csv_file)
                if df.empty:
                    print("❌ No data found in file")
                    return
                
                # Process file in chunks
                self._analyze_file_chunks(df)
            
            elif self.data_format == "muse_player":
                # Parse structured Muse Player data
                structured_data = self.data_parser.parse_muse_player_csv(self.csv_file)
                self._analyze_muse_player_data(structured_data)
            
            else:
                print(f"❌ Unsupported file format: {self.data_format}")
        
        except Exception as e:
            self.display_manager.display_error(f"File analysis failed: {e}")
    
    def _analyze_file_chunks(self, df):
        """Analyze Mind Monitor file in chunks."""
        results = []
        chunk_size = self.window_samples
        
        print(f"Processing {len(df)} samples in chunks of {chunk_size}...")
        
        for i in range(0, len(df), chunk_size // 2):  # 50% overlap
            chunk = df.iloc[i:i + chunk_size]
            
            if len(chunk) < chunk_size // 2:  # Skip very small chunks
                continue
            
            if self.use_precomputed:
                result = self._analyze_precomputed_data(chunk)
            else:
                channels = self.data_parser.extract_eeg_channels(chunk, self.data_format)
                result = self.analyze_eeg_window({'channels': channels})
            
            results.append(result)
            
            # Display progress occasionally
            if len(results) % 10 == 0:
                progress = (i / len(df)) * 100
                print(f"Progress: {progress:.1f}% - Latest: {result.emoji} {result.get_display_name()}")
        
        # Generate final report
        self._generate_file_analysis_report(results)
    
    def _analyze_muse_player_data(self, structured_data):
        """Analyze Muse Player structured data."""
        results = []
        timestamps = structured_data.get('timestamp', [])
        
        if not timestamps:
            print("❌ No timestamp data found")
            return
        
        print(f"Processing {len(timestamps)} samples...")
        
        chunk_size = self.window_samples
        for i in range(0, len(timestamps), chunk_size // 2):
            end_idx = min(i + chunk_size, len(timestamps))
            
            if end_idx - i < chunk_size // 2:
                continue
            
            # Extract chunk data
            chunk_data = {
                'timestamp': timestamps[i:end_idx],
                'eeg': {},
                'optics': {}
            }
            
            # Extract EEG channels
            for channel, values in structured_data['eeg'].items():
                if i < len(values):
                    chunk_data['eeg'][channel] = values[i:end_idx]
            
            # Extract optics channels
            for channel, values in structured_data['optics'].items():
                if i < len(values):
                    chunk_data['optics'][channel] = values[i:end_idx]
            
            # Analyze chunk
            result = self.analyze_eeg_window(chunk_data)
            results.append(result)
            
            # Display progress
            if len(results) % 10 == 0:
                progress = (i / len(timestamps)) * 100
                print(f"Progress: {progress:.1f}% - Latest: {result.emoji} {result.get_display_name()}")
        
        # Generate final report
        self._generate_file_analysis_report(results)
    
    def _generate_file_analysis_report(self, results: List[AnalysisResult]):
        """Generate comprehensive file analysis report."""
        if not results:
            print("❌ No results to analyze")
            return
        
        print("\n" + "="*70)
        print("📊 FILE ANALYSIS COMPLETE")
        print("="*70)
        
        # Basic statistics
        total_results = len(results)
        duration_minutes = (total_results * self.window_seconds) / 60.0
        
        print(f"Total samples analyzed: {total_results}")
        print(f"Estimated duration: {duration_minutes:.1f} minutes")
        
        # State distribution
        state_counts = {}
        for result in results:
            state = result.state
            state_counts[state] = state_counts.get(state, 0) + 1
        
        print("\nState Distribution:")
        for state, count in sorted(state_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_results) * 100
            print(f"  {state}: {count} ({percentage:.1f}%)")
        
        # Generate therapeutic report
        therapeutic_report = self.report_generator.generate_therapeutic_report(results)
        print("\n" + therapeutic_report)
        
        # Export option
        export_result = self.report_generator.export_session_data()
        print(f"\n📁 {export_result}")


def main():
    """Main entry point with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Enhanced Consciousness Monitor v4 - Therapeutic Edition: EEG + fNIRS + Therapeutic Pattern Detection"
    )
    
    # File and analysis parameters
    parser.add_argument("--file", "-f", help="CSV file to monitor or analyze", default="mind_monitor_complete.csv")
    parser.add_argument("--window", "-w", type=float, default=0.75, help="Analysis window in seconds (default: 0.75)")
    parser.add_argument("--update", "-u", type=float, default=1.0, help="Update interval in seconds (default: 1.0)")
    parser.add_argument("--analyze", "-a", action="store_true", help="Analyze entire file instead of real-time monitoring")
    
    # Display options
    parser.add_argument("--no-bands", action="store_true", help="Hide EEG band power visualization")
    parser.add_argument("--no-insights", action="store_true", help="Hide psychological insights")
    parser.add_argument("--no-optics", action="store_true", help="Hide fNIRS optical data")
    
    # Processing options
    parser.add_argument("--raw", action="store_true", help="Use raw signal processing instead of pre-computed bands")
    parser.add_argument("--force-output", action="store_true", help="Force output every update (disable smart event detection)")
    parser.add_argument("--output-interval", type=float, help="Force output every N seconds (overrides smart detection)")
    
    # Detection options
    parser.add_argument("--debug", action="store_true", help="Show debug information about data updates and rule testing")
    parser.add_argument("--konrad-mode", action="store_true", help="Enable Konrad's personalized detection patterns (dB-based Security Guard detection)")
    parser.add_argument("--tune-rule", action="append", help="Tune rule parameters (e.g. --tune-rule jhana.alpha_min=85 or --tune-rule artifact.multiband_spike=85)")
    parser.add_argument("--load-rules", help="Load detection rules from JSON file")
    parser.add_argument("--gamma-sensitivity", type=float, default=1.0, help="Sensitivity multiplier for gamma-based detection (excitement vs anxiety)")
    parser.add_argument("--positive-bias", action="store_true", help="Prefer positive interpretations when patterns could match multiple states")
    
    args = parser.parse_args()
    
    # Parse rule tuning arguments
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
                print(f"⚠️ Invalid rule tuning format: {rule_tune} (use rule.param=value)")
                continue
    
    # Create monitor instance
    try:
        monitor = EnhancedConsciousnessMonitor(
            csv_file=args.file,
            window_seconds=args.window,
            update_interval=args.update,
            show_bands=not args.no_bands,
            show_insights=not args.no_insights,
            show_optics=not args.no_optics,
            use_precomputed=not args.raw,
            force_output=args.force_output,
            output_interval=args.output_interval,
            debug=args.debug,
            konrad_mode=args.konrad_mode,
            tune_rules=tune_rules,
            load_rules=args.load_rules,
            gamma_sensitivity=args.gamma_sensitivity,
            positive_bias=args.positive_bias
        )
        
        # Run analysis or monitoring
        if args.analyze:
            monitor.analyze_file()
        else:
            monitor.monitor_realtime()
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()