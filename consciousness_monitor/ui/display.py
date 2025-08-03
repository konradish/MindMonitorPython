"""Display management for terminal output and visualization."""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any
try:
    import colorama
    from colorama import Fore, Style
    colorama.init()
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Fallback color definitions
    class Fore:
        RED = YELLOW = GREEN = CYAN = MAGENTA = WHITE = ""
    class Style:
        RESET_ALL = ""

from ..data.models import AnalysisResult, BandPower


class DisplayManager:
    """Manages terminal display and visualization."""
    
    def __init__(self, show_bands: bool = True, show_insights: bool = True, 
                 show_optics: bool = True, colors_enabled: bool = True):
        self.show_bands = show_bands
        self.show_insights = show_insights
        self.show_optics = show_optics
        self.colors_enabled = colors_enabled and COLORS_AVAILABLE
        
    def display_analysis_result(self, result: AnalysisResult, timestamp: Optional[datetime] = None):
        """
        Display a complete analysis result.
        
        Args:
            result: Analysis result to display
            timestamp: Optional timestamp override
        """
        if timestamp is None:
            timestamp = result.timestamp or datetime.now()
        
        # Display header with timestamp and state
        self._display_header(result, timestamp)
        
        # Display band powers if requested
        if self.show_bands and result.band_percentages:
            self._display_band_powers(result.band_percentages, result.db_changes)
        
        # Display optics data if available and requested
        if self.show_optics and result.optics_data:
            self._display_optics_data(result.optics_data)
        
        # Display insights if requested
        if self.show_insights and result.insights:
            self._display_insights(result.insights)
        
        # Display artifacts if detected
        if result.has_artifacts():
            self._display_artifact_warning(result.artifact_type)
        
        print()  # Add spacing between results
    
    def _display_header(self, result: AnalysisResult, timestamp: datetime):
        """Display the main header with state and timestamp."""
        time_str = timestamp.strftime("%H:%M:%S")
        display_name = result.get_display_name()
        emoji = result.emoji
        
        if self.colors_enabled:
            state_color = self._get_state_color(result.state)
            print(f"{Fore.WHITE}[{time_str}]{Style.RESET_ALL} "
                  f"{state_color}{emoji} {display_name}{Style.RESET_ALL}")
        else:
            print(f"[{time_str}] {emoji} {display_name}")
    
    def _display_band_powers(self, percentages: Dict[str, float], 
                           db_changes: Optional[Dict[str, float]] = None):
        """Display EEG band power percentages with optional dB changes."""
        if not percentages:
            return
        
        print("  EEG Bands:", end="")
        
        for band, percentage in percentages.items():
            emoji = self._get_band_emoji(band)
            
            # Format with dB change if available
            if db_changes and band in db_changes:
                db_change = db_changes[band]
                db_str = f"{db_change:+.1f}dB" if abs(db_change) >= 0.1 else ""
                if self.colors_enabled:
                    color = self._get_band_color(band)
                    print(f" {color}{emoji}{percentage:.0f}%{db_str}{Style.RESET_ALL}", end="")
                else:
                    print(f" {emoji}{percentage:.0f}%{db_str}", end="")
            else:
                if self.colors_enabled:
                    color = self._get_band_color(band)
                    print(f" {color}{emoji}{percentage:.0f}%{Style.RESET_ALL}", end="")
                else:
                    print(f" {emoji}{percentage:.0f}%", end="")
        
        print()  # New line after bands
    
    def _display_optics_data(self, optics_data: Dict[str, float]):
        """Display fNIRS optics data."""
        if not optics_data:
            return
        
        print("  fNIRS:", end="")
        for channel, value in optics_data.items():
            if self.colors_enabled:
                print(f" {Fore.MAGENTA}{channel}:{value:.3f}{Style.RESET_ALL}", end="")
            else:
                print(f" {channel}:{value:.3f}", end="")
        print()  # New line after optics
    
    def _display_insights(self, insights: List[str]):
        """Display psychological insights."""
        if not insights:
            return
        
        for insight in insights:
            if self.colors_enabled:
                print(f"  {Fore.YELLOW}💡 {insight}{Style.RESET_ALL}")
            else:
                print(f"  💡 {insight}")
    
    def _display_artifact_warning(self, artifact_type: Optional[str]):
        """Display artifact detection warning."""
        if not artifact_type:
            return
        
        warning = f"⚠️ ARTIFACT: {artifact_type.replace('_', ' ').title()}"
        if self.colors_enabled:
            print(f"  {Fore.RED}{warning}{Style.RESET_ALL}")
        else:
            print(f"  {warning}")
    
    def _get_state_color(self, state: str) -> str:
        """Get color for a consciousness state."""
        if not self.colors_enabled:
            return ""
        
        state_lower = state.lower()
        
        if 'jhana' in state_lower or 'flow' in state_lower:
            return Fore.CYAN
        elif 'security' in state_lower:
            return Fore.RED
        elif 'relaxed' in state_lower:
            return Fore.GREEN
        elif 'young' in state_lower or 'hopeful' in state_lower:
            return Fore.MAGENTA
        elif 'anxiety' in state_lower:
            return Fore.YELLOW
        else:
            return Fore.WHITE
    
    def _get_band_color(self, band: str) -> str:
        """Get color for an EEG band."""
        if not self.colors_enabled:
            return ""
        
        colors = {
            'delta': Fore.CYAN,
            'theta': Fore.GREEN,
            'alpha': Fore.YELLOW,
            'beta': Fore.RED,
            'gamma': Fore.MAGENTA
        }
        return colors.get(band.lower(), Fore.WHITE)
    
    def _get_band_emoji(self, band: str) -> str:
        """Get emoji for an EEG band."""
        emojis = {
            'delta': 'Δ',
            'theta': 'Θ',
            'alpha': 'α',
            'beta': 'β',
            'gamma': 'γ'
        }
        return emojis.get(band.lower(), band.upper())
    
    def display_session_summary(self, session_data: Dict[str, Any]):
        """Display session summary information."""
        if self.colors_enabled:
            print(f"\n{Fore.CYAN}🧠 Session Summary{Style.RESET_ALL}")
            print("=" * 50)
        else:
            print("\n🧠 Session Summary")
            print("=" * 50)
        
        duration = session_data.get('duration_minutes', 0)
        print(f"Duration: {duration:.1f} minutes")
        
        # State distribution
        states = session_data.get('states', {})
        if states:
            print("\nState Distribution:")
            for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / sum(states.values())) * 100
                print(f"  {state}: {count} ({percentage:.1f}%)")
        
        # Peak values
        peaks = session_data.get('peaks', {})
        if peaks:
            print("\nPeak Values:")
            for metric, value in peaks.items():
                print(f"  {metric}: {value:.1f}")
        
        # Significant events
        events = session_data.get('events', [])
        if events:
            print(f"\nSignificant Events: {len(events)}")
            for event in events[-5:]:  # Show last 5 events
                event_time = event.get('timestamp', 'Unknown')
                event_desc = event.get('description', 'Unknown event')
                print(f"  {event_time}: {event_desc}")
    
    def display_startup_info(self, config: Dict[str, Any]):
        """Display startup information and configuration."""
        color_prefix = f"{Fore.CYAN}" if self.colors_enabled else ""
        color_suffix = f"{Style.RESET_ALL}" if self.colors_enabled else ""
        
        print(f"{color_prefix}🧠 Enhanced Consciousness Monitor v4 - Therapeutic Edition{color_suffix}")
        
        mode = config.get('mode', 'Unknown')
        konrad_suffix = " | KONRAD MODE" if config.get('konrad_mode', False) else ""
        data_format = config.get('data_format', 'unknown')
        
        print(f"Mode: {mode}{konrad_suffix} | Data format: {data_format}")
        
        window = config.get('window_seconds', 0.75)
        update = config.get('update_interval', 1.0)
        sample_rate = config.get('sample_rate', 256)
        
        print(f"Window: {window}s | Update: {update}s | Sample Rate: {sample_rate}Hz")
        
        features = config.get('features', 'EEG Analysis')
        print(f"Features: {features}")
        
        if config.get('konrad_mode'):
            rule_version = config.get('rule_version', 'unknown')
            print(f"🎯 Rule Version: {rule_version} - dB-based Security Guard with Meditation Exemption")
        
        if config.get('debug'):
            num_rules = config.get('num_rules', 0)
            print(f"🔍 Debug Mode: Rule testing enabled | Available rules: {num_rules}")
        
        therapeutic_patterns = config.get('therapeutic_patterns', 
                                        'Jhana States, Parts Work, Startled Response, Safety Visualization')
        print(f"🧠 Therapeutic Patterns: {therapeutic_patterns}")
        
        sub_states = config.get('sub_states', 
                               'Flow (Engaged/Absorbed/Processing/Creative), Jhana (Entry/Stable/Deepening)')
        print(f"🔍 Sub-States: {sub_states}")
        
        artifacts = config.get('artifact_features', 
                              'Multi-band spikes, impossible combinations, extreme shifts')
        print(f"⚠️ Artifact Filtering: {artifacts}")
        
        hotkey_msg = config.get('hotkey_message', 
                               "Commands: 'c' (copy), 's' (summary), 'n' (now), 'q' (quit)")
        print(hotkey_msg)
        
        print("=" * 70)
    
    def display_no_signal(self):
        """Display no signal message."""
        if self.colors_enabled:
            print(f"{Fore.YELLOW}📡 Waiting for EEG data...{Style.RESET_ALL}")
        else:
            print("📡 Waiting for EEG data...")
    
    def display_error(self, error_msg: str):
        """Display error message."""
        if self.colors_enabled:
            print(f"{Fore.RED}❌ Error: {error_msg}{Style.RESET_ALL}")
        else:
            print(f"❌ Error: {error_msg}")
    
    def display_debug(self, debug_msg: str):
        """Display debug message."""
        if self.colors_enabled:
            print(f"{Fore.CYAN}🔍 Debug: {debug_msg}{Style.RESET_ALL}")
        else:
            print(f"🔍 Debug: {debug_msg}")