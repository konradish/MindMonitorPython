"""Data models for EEG analysis results."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class EEGReading:
    """Represents a single EEG reading with all channels."""
    timestamp: datetime
    channels: Dict[str, float]  # e.g., {'tp9': 123.4, 'af7': 234.5, ...}
    quality: Dict[str, float] = None  # Signal quality metrics
    aux_channels: Dict[str, float] = None  # AUX/optics data
    marker: str = None  # Event marker if present
    
    def __post_init__(self):
        if self.quality is None:
            self.quality = {}
        if self.aux_channels is None:
            self.aux_channels = {}


@dataclass
class BandPower:
    """EEG frequency band power analysis."""
    delta: float
    theta: float
    alpha: float
    beta: float
    gamma: float
    
    def as_dict(self) -> Dict[str, float]:
        """Return as dictionary."""
        return {
            'delta': self.delta,
            'theta': self.theta,
            'alpha': self.alpha,
            'beta': self.beta,
            'gamma': self.gamma
        }
    
    def as_percentages(self) -> Dict[str, float]:
        """Return as percentage ratios."""
        total = sum(self.as_dict().values())
        if total == 0:
            return {band: 0.0 for band in self.as_dict().keys()}
        return {band: (power / total) * 100 for band, power in self.as_dict().items()}


@dataclass
class AnalysisResult:
    """Results of EEG state analysis."""
    timestamp: datetime
    state: str
    sub_state: Optional[str] = None
    confidence: float = 0.0
    band_powers: Optional[BandPower] = None
    band_percentages: Optional[Dict[str, float]] = None
    db_changes: Optional[Dict[str, float]] = None
    insights: List[str] = None
    emoji: str = ""
    optics_data: Optional[Dict[str, float]] = None
    artifact_detected: bool = False
    artifact_type: Optional[str] = None
    
    def __post_init__(self):
        if self.insights is None:
            self.insights = []
    
    def get_display_name(self) -> str:
        """Get the formatted display name for the state."""
        if self.sub_state:
            return self.sub_state
        return self.state.upper()
    
    def has_artifacts(self) -> bool:
        """Check if artifacts were detected."""
        return self.artifact_detected


@dataclass
class SessionEvent:
    """Represents a significant event during monitoring session."""
    timestamp: datetime
    event_type: str  # 'state_change', 'security_guard', 'peak_alpha', etc.
    description: str
    state: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


@dataclass
class MacroTrend:
    """Represents macro-level trends in EEG data."""
    band: str
    trend: str  # 'increasing', 'decreasing', 'stable'
    duration_minutes: float
    change_magnitude: float
    confidence: float
    description: str