"""Core detection engine for EEG pattern matching."""

from typing import Dict, List, Optional, Any, Tuple
import os

from ..config.rules import RuleManager
from ..config.thresholds import ArtifactThresholds
from ..data.models import AnalysisResult, BandPower
from ..utils.math_helpers import MathHelpers
from .artifacts import ArtifactFilter
from .sub_states import SubStateDetector

# Optional database support for custom state definitions
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


class DetectionEngine:
    """Main engine for detecting consciousness states from EEG data."""
    
    def __init__(self,
                 rule_manager: Optional[RuleManager] = None,
                 artifact_thresholds: Optional[ArtifactThresholds] = None,
                 debug: bool = False,
                 database_url: Optional[str] = None,
                 konrad_mode: bool = False):  # Deprecated, kept for API compatibility

        self.rule_manager = rule_manager or RuleManager()
        self.artifact_filter = ArtifactFilter(artifact_thresholds or ArtifactThresholds())
        self.sub_state_detector = SubStateDetector(self.rule_manager.get_sub_state_rules())

        self.debug = debug

        # Database connection for custom state definitions
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        self._custom_states_cache = None
        self._custom_states_cache_time = 0
        self._cache_ttl_seconds = 30  # Refresh custom states every 30 seconds

        # State tracking
        self.last_state = None
        self.previous_db_values = {}
        self.current_db_values = {}
        self.db_changes = {}

        # Load initial custom states count
        custom_count = len(self._get_custom_states()) if self.database_url and HAS_PSYCOPG2 else 0
        if custom_count > 0:
            print(f"🔍 Detection Engine initialized | Custom states: {custom_count}")
        else:
            print(f"🔍 Detection Engine initialized | No custom states defined (will return UNKNOWN)")
        if debug:
            print(f"🔍 Debug Mode: Rule testing enabled")
    
    def analyze_bands(self, band_power: BandPower, timestamp=None) -> AnalysisResult:
        """
        Analyze EEG band powers to detect consciousness state.
        
        Args:
            band_power: BandPower object with frequency band data
            timestamp: Optional timestamp for the analysis
            
        Returns:
            AnalysisResult with detected state and metadata
        """
        try:
            # Convert to percentages and dB values
            band_dict = band_power.as_dict()
            percentages = band_power.as_percentages()
            
            if self.debug:
                print(f"Debug - Band dict types: {[(k, type(v)) for k, v in band_dict.items()]}")
                print(f"Debug - Percentages types: {[(k, type(v)) for k, v in percentages.items()]}")
            
            # Update dB tracking
            self._update_db_tracking(band_dict)

            # Check for artifacts first
            if self.debug:
                print(f"Debug - Calling artifact detection")
            artifact_type = self.artifact_filter.detect_artifacts(percentages, self.db_changes)
            if self.debug:
                print(f"Debug - Artifact detection complete: {artifact_type}")
            if artifact_type:
                return AnalysisResult(
                    timestamp=timestamp,
                    state="ARTIFACT",
                    band_powers=band_power,
                    band_percentages=percentages,
                    db_changes=self.db_changes.copy(),
                    artifact_detected=True,
                    artifact_type=artifact_type,
                    emoji="⚠️",
                    insights=[f"⚠️ {artifact_type.replace('_', ' ').title()} detected"]
                )
            
            # Detect primary state
            primary_state, rule_data = self._evaluate_detection_rules(percentages, self.db_changes)
            if self.debug:
                print(f"Debug - Primary state detected: {primary_state}")
            
            # Check for sub-states
            if self.debug:
                print(f"Debug - Checking sub-states for: {primary_state}")
            sub_state_info = self.sub_state_detector.detect_sub_state(
                primary_state, percentages, self.db_changes
            )
            if self.debug:
                print(f"Debug - Sub-state info: {sub_state_info}")
            
            # Create result
            result = AnalysisResult(
                timestamp=timestamp,
                state=primary_state,
                sub_state=sub_state_info.get('display') if sub_state_info else None,
                band_powers=band_power,
                band_percentages=percentages,
                db_changes=self.db_changes.copy(),
                emoji=sub_state_info.get('emoji', rule_data.get('emoji', '')) if sub_state_info else rule_data.get('emoji', ''),
                insights=sub_state_info.get('insights', rule_data.get('insights', [])) if sub_state_info else rule_data.get('insights', [])
            )
            
            # Update state tracking
            self.last_state = primary_state
            
            if self.debug:
                print(f"Debug - Returning result: {result.state}")
            
            return result
            
        except Exception as e:
            print(f"⚠️ Analysis failed: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return self._get_error_result(timestamp)
    
    def _update_db_tracking(self, band_powers: Dict[str, float]):
        """Update dB value tracking for change detection."""
        # Store previous values
        self.previous_db_values = self.current_db_values.copy()
        
        # Calculate current dB values
        self.current_db_values = {
            band: MathHelpers.power_to_db(power) for band, power in band_powers.items()
        }
        
        # Calculate changes
        self.db_changes = {}
        for band in band_powers.keys():
            if band in self.previous_db_values:
                self.db_changes[band] = MathHelpers.calculate_db_change(
                    self.current_db_values[band], 
                    self.previous_db_values[band]
                )
            else:
                self.db_changes[band] = 0.0
    
    def _get_custom_states(self) -> List[Dict[str, Any]]:
        """
        Get custom state definitions from database with caching.

        Returns list of enabled custom states sorted by priority (descending).
        Caches results for _cache_ttl_seconds to avoid excessive DB queries.
        """
        import time

        # Return empty if no database support
        if not HAS_PSYCOPG2 or not self.database_url:
            return []

        # Check cache
        now = time.time()
        if self._custom_states_cache is not None and (now - self._custom_states_cache_time) < self._cache_ttl_seconds:
            return self._custom_states_cache

        try:
            conn = psycopg2.connect(self.database_url)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            cur.execute("""
                SELECT name, priority, conditions, interpretation, recommendations, emoji
                FROM state_definition
                WHERE enabled = true
                ORDER BY priority DESC, name
            """)

            rows = cur.fetchall()
            conn.close()

            # Convert to list of dicts
            self._custom_states_cache = [dict(r) for r in rows]
            self._custom_states_cache_time = now

            if self.debug and self._custom_states_cache:
                print(f"Debug - Loaded {len(self._custom_states_cache)} custom states from database")

            return self._custom_states_cache

        except Exception as e:
            if self.debug:
                print(f"Debug - Failed to load custom states: {e}")
            return []

    def _evaluate_custom_state(self, state: Dict[str, Any], percentages: Dict[str, float]) -> bool:
        """
        Test if a custom state's conditions are met.

        Args:
            state: Custom state definition with 'conditions' dict
            percentages: Current band power percentages

        Returns:
            True if all conditions are satisfied
        """
        conditions = state.get('conditions', {})
        if not conditions:
            return False

        for key, threshold in conditions.items():
            if key.endswith('_min'):
                band = key.replace('_min', '')
                if band in percentages and float(percentages[band]) < threshold:
                    return False
            elif key.endswith('_max'):
                band = key.replace('_max', '')
                if band in percentages and float(percentages[band]) > threshold:
                    return False

        return True

    def _evaluate_database_rules(self, percentages: Dict[str, float]) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Evaluate custom database-defined state rules.

        These are checked BEFORE hardcoded rules, allowing Claude-defined
        personalized states to take priority.

        Args:
            percentages: Band power percentages

        Returns:
            Tuple of (state_name, rule_data) if a custom state matches, None otherwise
        """
        custom_states = self._get_custom_states()

        for state in custom_states:
            if self._evaluate_custom_state(state, percentages):
                if self.debug:
                    print(f"Debug - Custom state matched: {state['name']}")

                rule_data = {
                    'emoji': state.get('emoji', '🧠'),
                    'insights': [state.get('interpretation', f"Custom state: {state['name']}")],
                    'recommendations': state.get('recommendations', []),
                    'source': 'database'
                }
                return state['name'], rule_data

        return None

    def _evaluate_detection_rules(self, percentages: Dict[str, float], db_changes: Dict[str, float]) -> Tuple[str, Dict[str, Any]]:
        """
        Evaluate custom state definitions to find a match.

        Only database-defined custom states are used. Falls back to UNKNOWN
        if no custom states match.

        Args:
            percentages: Band power percentages
            db_changes: dB changes for each band (unused, kept for API compatibility)

        Returns:
            Tuple of (state_name, rule_data)
        """
        # Check custom database-defined states
        db_result = self._evaluate_database_rules(percentages)
        if db_result:
            return db_result

        # No custom state matched - return UNKNOWN
        if self.debug:
            print("Debug - No custom state matched, returning UNKNOWN")

        return "UNKNOWN", {
            "emoji": "❓",
            "insights": ["No matching state definition. Define custom states in the admin panel."],
            "source": "fallback"
        }
    
    def _get_error_result(self, timestamp=None) -> AnalysisResult:
        """Create an error result for exception cases."""
        return AnalysisResult(
            timestamp=timestamp,
            state="ERROR",
            emoji="⚠️",
            insights=["Analysis error - check signal quality"],
            band_percentages={band: 0.0 for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']},
            db_changes={band: 0.0 for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']}
        )