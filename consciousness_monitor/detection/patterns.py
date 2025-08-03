"""Therapeutic pattern detection and analysis."""

from typing import Dict, List, Optional, Any
from collections import deque
import numpy as np

from ..data.models import AnalysisResult, SessionEvent
from ..config.rules import RuleManager


class TherapeuticPatterns:
    """Specialized detection for therapeutic EEG patterns."""
    
    def __init__(self, rule_manager: RuleManager):
        self.rule_manager = rule_manager
        self.state_history = deque(maxlen=10)  # Track recent states
        self.pattern_sequences = []  # Track pattern sequences
        
    def detect_parts_work_patterns(self, result: AnalysisResult) -> List[str]:
        """
        Detect Internal Family Systems (IFS) parts work patterns.
        
        Args:
            result: Analysis result to examine
            
        Returns:
            List of parts work insights
        """
        insights = []
        
        if not result.band_percentages:
            return insights
        
        state = result.state.lower()
        
        # Young Part patterns
        if 'young' in state:
            delta_percent = float(result.band_percentages.get('delta', 0))
            alpha_percent = float(result.band_percentages.get('alpha', 0))
            
            if delta_percent > 40:
                insights.append("🤗 Strong delta suggests deep trust and vulnerability")
            if 30 <= alpha_percent <= 40:
                insights.append("💝 Regulated young part - safe to feel vulnerable")
        
        # Cautious Part patterns
        elif 'cautious' in state:
            beta_percent = float(result.band_percentages.get('beta', 0))
            alpha_percent = float(result.band_percentages.get('alpha', 0))
            
            if beta_percent > 20:
                insights.append("👁️ Cautious part actively scanning environment")
            if alpha_percent > 60:
                insights.append("🛡️ Protective awareness with good regulation")
        
        # Hopeful Part patterns
        elif 'hopeful' in state:
            alpha_percent = float(result.band_percentages.get('alpha', 0))
            if alpha_percent > 75:
                insights.append("🌟 Strong optimism with excellent nervous system regulation")
        
        return insights
    
    def detect_meditation_patterns(self, result: AnalysisResult) -> List[str]:
        """
        Detect meditation-related patterns and progressions.
        
        Args:
            result: Analysis result to examine
            
        Returns:
            List of meditation insights
        """
        insights = []
        
        if not result.band_percentages:
            return insights
        
        state = result.state.lower()
        alpha_percent = float(result.band_percentages.get('alpha', 0))
        beta_percent = float(result.band_percentages.get('beta', 0))
        theta_percent = float(result.band_percentages.get('theta', 0))
        
        # Jhana progression analysis
        if 'jhana' in state:
            if result.sub_state:
                sub_state = result.sub_state.lower()
                if 'entry' in sub_state:
                    insights.append("🚪 Jhana entry achieved - absorption beginning")
                elif 'stable' in sub_state:
                    insights.append("✨ Stable jhana - sustained transcendent state")
                elif 'deepening' in sub_state:
                    insights.append("🌌 Deepening absorption - approaching formless jhanas")
            
            # Additional jhana quality indicators
            if beta_percent < 5:
                insights.append("🧘 Thinking mind nearly dissolved")
            if alpha_percent > 95:
                insights.append("🕉️ Exceptionally pure consciousness state")
        
        # Flow state meditation
        elif 'flow' in state:
            if result.sub_state and 'absorbed' in result.sub_state.lower():
                insights.append("🌊 Micro-transcendence within activity")
        
        # Meditative state analysis
        elif 'meditative' in state:
            if theta_percent > 35:
                insights.append("🧘 Deep introspective meditation")
            if alpha_percent < 15:
                insights.append("💭 Inward-focused contemplative state")
        
        return insights
    
    def detect_nervous_system_patterns(self, result: AnalysisResult) -> List[str]:
        """
        Detect nervous system regulation patterns.
        
        Args:
            result: Analysis result to examine
            
        Returns:
            List of nervous system insights
        """
        insights = []
        
        if not result.band_percentages or not result.db_changes:
            return insights
        
        state = result.state.lower()
        
        # Security guard analysis
        if 'security' in state or result.artifact_type == 'SECURITY_GUARD':
            beta_change = result.db_changes.get('beta', 0)
            delta_change = result.db_changes.get('delta', 0)
            
            if beta_change > 8:
                insights.append("⚡ Intense hypervigilance response")
            elif beta_change > 6:
                insights.append("🚨 Moderate threat detection activated")
            
            if delta_change > 8:
                insights.append("💥 Strong autonomic nervous system activation")
        
        # Startled response analysis
        elif 'startled' in state:
            alpha_percent = float(result.band_percentages.get('alpha', 0))
            beta_percent = float(result.band_percentages.get('beta', 0))
            
            if alpha_percent > 40 and beta_percent < 50:
                insights.append("😌 Healthy startle with quick recovery")
            elif alpha_percent < 30:
                insights.append("⚠️ Startled with reduced regulation")
        
        # Recovery patterns
        elif 'recovery' in state:
            delta_percent = float(result.band_percentages.get('delta', 0))
            if delta_percent > 45:
                insights.append("😮‍💨 Deep nervous system recovery underway")
        
        # Integration patterns  
        elif 'integration' in state:
            gamma_change = result.db_changes.get('gamma', 0)
            if gamma_change > 2:
                insights.append("🧩 Active memory consolidation with gamma bursts")
        
        return insights
    
    def analyze_state_sequence(self, results: List[AnalysisResult]) -> List[str]:
        """
        Analyze sequences of states for therapeutic patterns.
        
        Args:
            results: List of recent analysis results
            
        Returns:
            List of sequence-based insights
        """
        insights = []
        
        if len(results) < 3:
            return insights
        
        states = [r.state.lower() for r in results[-3:]]
        
        # Security guard to recovery progression
        if 'security' in states[0] and 'recovery' in states[-1]:
            insights.append("🛡️➡️😮‍💨 Healthy threat response to recovery progression")
        
        # Young part to cautious part transition
        if 'young' in states[0] and 'cautious' in states[-1]:
            insights.append("💝➡️🛡️ Vulnerability to protection transition")
        
        # Meditation progression
        if 'flow' in states[0] and 'jhana' in states[-1]:
            insights.append("🌊➡️🧘 Flow to transcendent meditation progression")
        
        # Anxiety to relaxed progression
        if 'anxiety' in states[0] and 'relaxed' in states[-1]:
            insights.append("⚠️➡️😌 Anxiety to regulation progression")
        
        return insights
    
    def detect_unusual_patterns(self, result: AnalysisResult) -> List[str]:
        """
        Detect unusual or noteworthy patterns that may need attention.
        
        Args:
            result: Analysis result to examine
            
        Returns:
            List of unusual pattern insights
        """
        insights = []
        
        if not result.band_percentages or not result.db_changes:
            return insights
        
        # Extremely high single-band dominance
        max_band_percent = max(float(v) for v in result.band_percentages.values())
        if max_band_percent > 85:
            dominant_band = max(result.band_percentages.items(), key=lambda x: float(x[1]))[0]
            insights.append(f"⚡ Unusual {dominant_band} dominance ({max_band_percent:.1f}%)")
        
        # Rapid state changes (high dB changes)
        max_db_change = max([abs(change) for change in result.db_changes.values()])
        if max_db_change > 15:
            insights.append(f"🌊 Rapid neurological shift detected ({max_db_change:.1f}dB)")
        
        # Unusual combinations
        alpha_percent = float(result.band_percentages.get('alpha', 0))
        gamma_percent = float(result.band_percentages.get('gamma', 0))
        
        if alpha_percent > 80 and gamma_percent > 15:
            insights.append("✨ Rare alpha-gamma coupling - transcendent focus state")
        
        return insights