"""Configuration management for consciousness monitor."""

from .rules import RuleManager
from .settings import Settings
from .thresholds import ArtifactThresholds

__all__ = ["RuleManager", "Settings", "ArtifactThresholds"]