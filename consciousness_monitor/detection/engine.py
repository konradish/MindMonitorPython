"""Core detection engine for EEG pattern matching."""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from collections import deque

from ..config.rules import RuleManager
from ..config.thresholds import ArtifactThresholds
from ..data.models import AnalysisResult, BandPower
from ..utils.math_helpers import MathHelpers
from .artifacts import ArtifactFilter
from .sub_states import SubStateDetector


class DetectionEngine:
    """Main engine for detecting consciousness states from EEG data."""
    
    def __init__(self, 
                 rule_manager: Optional[RuleManager] = None,
                 artifact_thresholds: Optional[ArtifactThresholds] = None,
                 debug: bool = False,
                 konrad_mode: bool = False):
        
        self.rule_manager = rule_manager or RuleManager()
        self.artifact_filter = ArtifactFilter(artifact_thresholds or ArtifactThresholds())
        self.sub_state_detector = SubStateDetector(self.rule_manager.get_sub_state_rules())
        
        self.debug = debug
        self.konrad_mode = konrad_mode
        
        # State tracking
        self.last_state = None
        self.previous_db_values = {}
        self.current_db_values = {}
        self.db_changes = {}
        
        # Beta trend analysis for anxiety detection
        self.beta_history = deque(maxlen=5)
        
        # Gamma trend analysis for excitement detection
        self.gamma_history = deque(maxlen=5)
        
        print(f"🔍 Detection Engine initialized | Rules: {len(self.rule_manager.get_detection_rules())}")
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
            
            # Update trend tracking (centralized)
            self._update_trend_tracking(percentages)
            
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
    
    def _update_trend_tracking(self, percentages: Dict[str, float]):
        """Update trend tracking for beta and gamma (centralized)."""
        beta_percent = float(percentages.get('beta', 0))
        gamma_percent = float(percentages.get('gamma', 0))
        
        self.beta_history.append(beta_percent)
        self.gamma_history.append(gamma_percent)
    
    def _evaluate_detection_rules(self, percentages: Dict[str, float], db_changes: Dict[str, float]) -> Tuple[str, Dict[str, Any]]:
        """
        Evaluate all detection rules to find the best match.
        
        Args:
            percentages: Band power percentages
            db_changes: dB changes for each band
            
        Returns:
            Tuple of (state_name, rule_data)
        """
        # Get rules sorted by priority
        sorted_rules = self.rule_manager.get_sorted_rules()
        
        for rule_name, rule in sorted_rules:
            if self.debug:
                print(f"Debug - Testing rule: {rule_name}")
            
            if self._test_rule_conditions(rule_name, rule, percentages, db_changes):
                if self.debug:
                    print(f"Debug - Rule {rule_name} MATCHED")
                return rule_name.upper().replace('_', ' '), rule
            elif self.debug:
                print(f"Debug - Rule {rule_name} failed")
        
        # Default fallback - valid signal but no pattern match
        return "MIXED", {"emoji": "🔀", "insights": ["Mixed state - no dominant pattern"]}
    
    def _test_rule_conditions(self, rule_name: str, rule: Dict[str, Any], 
                            bands: Dict[str, float], db_changes: Dict[str, float]) -> bool:
        """
        Test if a rule's conditions are met.
        
        Args:
            rule_name: Name of the rule
            rule: Rule configuration
            bands: Band percentage values
            db_changes: dB changes for each band
            
        Returns:
            True if rule conditions are satisfied
        """
        conditions = rule.get('conditions', {})
        
        try:
            # Special handling for security guard rule
            if rule_name == 'security_guard':
                return self._test_security_guard_conditions(conditions, bands, db_changes)
            
            # Special handling for anxiety escalation (requires trend)
            if rule_name == 'anxiety_escalation':
                return self._test_anxiety_escalation_conditions(conditions, bands, db_changes)
            
            # Special handling for positive activation (requires beta+gamma trends)
            if rule_name == 'positive_activation':
                return self._test_positive_activation_conditions(conditions, bands, db_changes)
            
            # Special handling for recovery rule (requires previous state)
            if 'requires_previous_state' in conditions:
                required_state = conditions['requires_previous_state']
                if self.last_state != required_state:
                    return False
            
            # Test standard conditions
            return self._test_standard_conditions(conditions, bands, db_changes)
            
        except Exception as e:
            if self.debug:
                print(f"Debug - Error testing rule {rule_name}: {e}")
            return False
    
    def _test_standard_conditions(self, conditions: Dict[str, Any], 
                                bands: Dict[str, float], db_changes: Dict[str, float]) -> bool:
        """Test standard min/max conditions."""
        for param, value in conditions.items():
            if param.endswith('_min'):
                band = param.replace('_min', '')
                if band in bands and float(bands[band]) < value:
                    return False
            elif param.endswith('_max'):
                band = param.replace('_max', '')
                if band in bands and float(bands[band]) > value:
                    return False
            elif param.endswith('_db_change_min'):
                band = param.replace('_db_change_min', '')
                if band in db_changes and float(db_changes[band]) < value:
                    return False
            elif param == 'gamma_trend':
                # Handle gamma trend conditions
                if len(self.gamma_history) >= 3:
                    gamma_values = list(self.gamma_history)
                    recent_change = gamma_values[-1] - gamma_values[-3]
                    if value == 'increasing' and recent_change <= 1:
                        return False
                    elif value == 'decreasing' and recent_change >= -1:
                        return False
                else:
                    return False  # Not enough history for trend
            elif param in ['beta_trend', 'exclude_high_gamma']:
                # Skip these - handled by specialized methods
                continue
        
        return True
    
    def _test_security_guard_conditions(self, conditions: Dict[str, Any], 
                                      bands: Dict[str, float], db_changes: Dict[str, float]) -> bool:
        """Test specialized security guard detection conditions."""
        db_spike_config = conditions.get('db_spike', {})
        alpha_exemption = conditions.get('alpha_exemption', 80)
        beta_exemption_max = conditions.get('beta_exemption_max', 15)
        
        # Check for meditation exemption (Konrad mode)
        if self.konrad_mode:
            alpha_percent = float(bands.get('alpha', 0))
            beta_percent = float(bands.get('beta', 0))
            if alpha_percent > alpha_exemption and beta_percent < beta_exemption_max:
                return False  # Skip security guard during deep meditation
        
        # Check dB spikes
        delta_spike = float(db_changes.get('delta', 0))
        beta_spike = float(db_changes.get('beta', 0))
        alpha_drop = float(db_changes.get('alpha', 0))
        
        delta_threshold = db_spike_config.get('delta', 6.0)
        beta_threshold = db_spike_config.get('beta', 6.0)
        alpha_drop_threshold = db_spike_config.get('alpha_drop', -2.0)
        
        # Primary dB-based detection
        if (delta_spike > delta_threshold or beta_spike > beta_threshold) and alpha_drop < alpha_drop_threshold:
            return True
        
        # Fallback percentage-based detection
        fallback = conditions.get('percentage_fallback', {})
        if fallback:
            beta_min = fallback.get('beta_min', 25)
            gamma_min = fallback.get('gamma_min', 25)
            delta_max = fallback.get('delta_max', 15)
            
            if (float(bands.get('beta', 0)) > beta_min and 
                float(bands.get('gamma', 0)) > gamma_min and 
                float(bands.get('delta', 0)) < delta_max):
                return True
        
        return False
    
    def _test_anxiety_escalation_conditions(self, conditions: Dict[str, Any], 
                                          bands: Dict[str, float], db_changes: Dict[str, float]) -> bool:
        """Test anxiety escalation with beta trend analysis and gamma exclusion."""
        if len(self.beta_history) < 3:
            return False  # Need enough history
        
        # Check for gamma exclusion (anxiety has low gamma, excitement has high gamma)
        gamma_percent = float(bands.get('gamma', 0))
        gamma_max = conditions.get('gamma_max', 20)
        exclude_high_gamma = conditions.get('exclude_high_gamma', False)
        
        if exclude_high_gamma and gamma_percent > gamma_max:
            return False  # High gamma suggests excitement, not anxiety
        
        # Check for increasing trend
        beta_values = list(self.beta_history)
        if len(beta_values) >= 3:
            recent_change = beta_values[-1] - beta_values[-3]
            min_change = conditions.get('beta_min_change', 5)
            alpha_min = conditions.get('alpha_min', 40)
            
            if recent_change > min_change and float(bands.get('alpha', 0)) > alpha_min:
                return True
        
        return False
    
    def _test_positive_activation_conditions(self, conditions: Dict[str, Any], 
                                           bands: Dict[str, float], db_changes: Dict[str, float]) -> bool:
        """Test positive activation with beta trend and gamma requirements."""
        if len(self.beta_history) < 3:
            return False  # Need enough history
        
        # Test standard conditions first
        if not self._test_standard_conditions(conditions, bands, db_changes):
            return False
        
        # Check for increasing beta trend (required for positive activation)
        beta_trend = conditions.get('beta_trend')
        if beta_trend == 'increasing':
            beta_values = list(self.beta_history)
            if len(beta_values) >= 3:
                recent_change = beta_values[-1] - beta_values[-3]
                if recent_change <= 2:  # Require some beta increase for excitement
                    return False
        
        return True
    
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