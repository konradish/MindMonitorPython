"""Artifact threshold management for EEG data quality control."""

import json
import os
from typing import Dict, Any, Optional


class ArtifactThresholds:
    """Manages artifact detection thresholds."""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = os.path.dirname(__file__)
        self.config_dir = config_dir
        
        self.thresholds = {}
        self.version = "unknown"
        
        self._load_thresholds()
    
    def _load_thresholds(self):
        """Load artifact thresholds from JSON file."""
        try:
            thresholds_file = os.path.join(self.config_dir, "artifact_thresholds.json")
            with open(thresholds_file, 'r') as f:
                data = json.load(f)
                # Extract just the values for backward compatibility
                raw_thresholds = data.get("thresholds", {})
                self.thresholds = {}
                for key, config in raw_thresholds.items():
                    if isinstance(config, dict) and "value" in config:
                        # Simple threshold with "value" key
                        self.thresholds[key] = config["value"]
                    elif isinstance(config, dict):
                        # Complex threshold - store the whole dict
                        self.thresholds[key] = config
                    else:
                        # Direct value
                        self.thresholds[key] = config
                self.version = data.get("version", "unknown")
        except Exception as e:
            print(f"⚠️ Error loading artifact thresholds: {e}")
            self._use_fallback_thresholds()
    
    def _use_fallback_thresholds(self):
        """Use default thresholds if JSON loading fails."""
        print("📋 Using fallback artifact thresholds")
        self.thresholds = {
            "multiband_spike": 90,
            "impossible_combo_alpha": 95,
            "impossible_combo_beta": 30,
            "extreme_shift": 300,
            "simultaneous_bands": 3
        }
    
    def get_threshold(self, name: str) -> float:
        """Get a specific threshold value."""
        return self.thresholds.get(name, 0)
    
    def get_all_thresholds(self) -> Dict[str, float]:
        """Get all threshold values."""
        return self.thresholds.copy()
    
    def tune_threshold(self, name: str, value: float):
        """Tune a specific threshold value."""
        if name in self.thresholds:
            old_value = self.thresholds[name]
            self.thresholds[name] = value
            print(f"🔧 Tuned artifact.{name}: {old_value} → {value}")
        else:
            print(f"⚠️ Unknown artifact threshold: {name}")
    
    def get_version(self) -> str:
        """Get the thresholds version."""
        return self.version