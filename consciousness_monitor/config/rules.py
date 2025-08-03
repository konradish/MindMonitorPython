"""Rule management for consciousness monitor detection patterns."""

import json
import os
from typing import Dict, Any, Optional


class RuleManager:
    """Manages loading and manipulation of detection rules."""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = os.path.dirname(__file__)
        self.config_dir = config_dir
        
        self.detection_rules = {}
        self.sub_state_rules = {}
        self.legacy_rules = {}
        self.version = "unknown"
        self.changelog = {}
        
        self._load_all_rules()
    
    def _load_all_rules(self):
        """Load all rule configurations from JSON files."""
        try:
            self._load_detection_rules()
            self._load_sub_state_rules()
            self._load_legacy_rules()
        except Exception as e:
            print(f"⚠️ Error loading rules: {e}")
            self._use_fallback_rules()
    
    def _load_detection_rules(self):
        """Load main detection rules from JSON."""
        rules_file = os.path.join(self.config_dir, "detection_rules.json")
        with open(rules_file, 'r') as f:
            data = json.load(f)
            self.detection_rules = data.get("rules", {})
            self.version = data.get("version", "unknown")
            self.changelog = data.get("changelog", {})
    
    def _load_sub_state_rules(self):
        """Load hierarchical sub-state rules from JSON."""
        sub_states_file = os.path.join(self.config_dir, "sub_states.json")
        with open(sub_states_file, 'r') as f:
            data = json.load(f)
            self.sub_state_rules = data.get("sub_state_rules", {})
    
    def _load_legacy_rules(self):
        """Load legacy/personalized rules for backward compatibility."""
        legacy_file = os.path.join(self.config_dir, "konrad_personalized.json")
        with open(legacy_file, 'r') as f:
            data = json.load(f)
            self.legacy_rules = data.get("legacy_rules", {})
    
    def _use_fallback_rules(self):
        """Use minimal fallback rules if JSON loading fails."""
        print("📋 Using fallback detection rules")
        self.detection_rules = {
            "relaxed": {
                "priority": 1,
                "conditions": {"alpha_min": 40},
                "emoji": "🌊",
                "insights": ["😌 Relaxed state"]
            }
        }
        self.sub_state_rules = {}
        self.legacy_rules = {}
    
    def get_detection_rules(self) -> Dict[str, Any]:
        """Get the main detection rules dictionary."""
        return self.detection_rules
    
    def get_sub_state_rules(self) -> Dict[str, Any]:
        """Get the hierarchical sub-state rules dictionary."""
        return self.sub_state_rules
    
    def get_legacy_rules(self) -> Dict[str, Any]:
        """Get legacy rules for backward compatibility."""
        return self.legacy_rules
    
    def get_version(self) -> str:
        """Get the rules version."""
        return self.version
    
    def get_changelog(self) -> Dict[str, str]:
        """Get the rules changelog."""
        return self.changelog
    
    def load_custom_rules(self, filename: str):
        """Load custom rules from an external JSON file."""
        try:
            with open(filename, 'r') as f:
                custom_rules = json.load(f)
            
            # Merge custom rules with existing ones
            if "rules" in custom_rules:
                self.detection_rules.update(custom_rules["rules"])
            
            if "sub_state_rules" in custom_rules:
                self.sub_state_rules.update(custom_rules["sub_state_rules"])
            
            print(f"📁 Loaded custom rules from {filename}")
        except Exception as e:
            print(f"⚠️ Could not load custom rules from {filename}: {e}")
    
    def tune_rule(self, rule_path: str, value: float):
        """Tune a specific rule parameter via dot notation (e.g., 'jhana.alpha_min')."""
        try:
            parts = rule_path.split('.')
            if len(parts) != 2:
                raise ValueError("Rule path must be in format 'rule_name.parameter'")
            
            rule_name, param = parts
            
            if rule_name in self.detection_rules:
                conditions = self.detection_rules[rule_name].get('conditions', {})
                if param in conditions:
                    old_value = conditions[param]
                    conditions[param] = value
                    print(f"🔧 Tuned {rule_name}.{param}: {old_value} → {value}")
                else:
                    print(f"⚠️ Parameter '{param}' not found in rule '{rule_name}'")
            else:
                print(f"⚠️ Rule '{rule_name}' not found")
        except Exception as e:
            print(f"⚠️ Error tuning rule {rule_path}: {e}")
    
    def get_sorted_rules(self):
        """Get detection rules sorted by priority."""
        return sorted(self.detection_rules.items(), key=lambda x: x[1].get('priority', 999))