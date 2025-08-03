"""Hierarchical sub-state detection for enhanced pattern recognition."""

from typing import Dict, Optional, Any


class SubStateDetector:
    """Handles detection of hierarchical sub-states within base states."""
    
    def __init__(self, sub_state_rules: Dict[str, Any]):
        self.sub_state_rules = sub_state_rules
    
    def detect_sub_state(self, base_state_name: str, bands: Dict[str, float], 
                        db_changes: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        Detect sub-states within a base state.
        
        Args:
            base_state_name: Name of the detected base state
            bands: Band power percentages
            db_changes: dB changes for each band
            
        Returns:
            Sub-state information dictionary if detected, None otherwise
        """
        try:
            # Convert state name to lowercase for lookup
            lookup_name = base_state_name.lower().replace(' ', '_')
            
            if lookup_name not in self.sub_state_rules:
                return None
            
            sub_state_config = self.sub_state_rules[lookup_name]
            
            # Check base conditions first
            base_conditions = sub_state_config.get("base_conditions", {})
            if not self._test_conditions(base_conditions, bands, db_changes):
                return None
            
            # Test each sub-state in order
            sub_states = sub_state_config.get("sub_states", {})
            for sub_state_name, sub_state_info in sub_states.items():
                conditions = sub_state_info.get("conditions", {})
                
                if self._test_conditions(conditions, bands, db_changes):
                    return {
                        'name': sub_state_name,
                        'display': sub_state_info.get('display', sub_state_name.upper()),
                        'emoji': sub_state_info.get('emoji', ''),
                        'insights': sub_state_info.get('insights', [])
                    }
            
            return None
            
        except Exception as e:
            print(f"⚠️ Sub-state detection error: {e}")
            return None
    
    def _test_conditions(self, conditions: Dict[str, Any], 
                        bands: Dict[str, float], db_changes: Dict[str, float]) -> bool:
        """
        Test if conditions are met for a sub-state.
        
        Args:
            conditions: Condition dictionary
            bands: Band power percentages
            db_changes: dB changes for each band
            
        Returns:
            True if all conditions are satisfied
        """
        try:
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
                        
                elif param.endswith('_db_change_max'):
                    band = param.replace('_db_change_max', '')
                    if band in db_changes and float(db_changes[band]) > value:
                        return False
            
            return True
            
        except Exception as e:
            print(f"⚠️ Condition testing error: {e}")
            return False
    
    def get_available_sub_states(self, base_state_name: str) -> Dict[str, Any]:
        """
        Get available sub-states for a base state.
        
        Args:
            base_state_name: Name of the base state
            
        Returns:
            Dictionary of available sub-states
        """
        lookup_name = base_state_name.lower().replace(' ', '_')
        
        if lookup_name in self.sub_state_rules:
            return self.sub_state_rules[lookup_name].get("sub_states", {})
        
        return {}