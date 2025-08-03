"""Report generation for analysis results and session summaries."""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

from ..data.models import AnalysisResult, SessionEvent


class ReportGenerator:
    """Generates various reports and summaries."""
    
    def __init__(self):
        self.session_start = datetime.now()
        self.events = []
        self.states = {}
        self.peak_values = {}
    
    def track_event(self, timestamp: datetime, text: str, state: str, 
                   ratios: Optional[Dict[str, float]] = None):
        """Track a session event for reporting."""
        event = SessionEvent(
            timestamp=timestamp,
            event_type='state_detection',
            description=text,
            state=state,
            data={'ratios': ratios} if ratios else {}
        )
        self.events.append(event)
        
        # Update state counts
        if state not in self.states:
            self.states[state] = 0
        self.states[state] += 1
        
        # Track peak values
        if ratios:
            for band, value in ratios.items():
                peak_key = f"peak_{band}"
                if peak_key not in self.peak_values or value > self.peak_values[peak_key]:
                    self.peak_values[peak_key] = value
    
    def generate_recent_events(self, count: int = 10) -> str:
        """Generate formatted string of recent events."""
        if not self.events:
            return "No recent events to display"
        
        recent_events = self.events[-count:]
        output_lines = []
        
        output_lines.append("🕒 Recent Events:")
        output_lines.append("-" * 50)
        
        for event in recent_events:
            time_str = event.timestamp.strftime("%H:%M:%S")
            state_str = event.state or "UNKNOWN"
            description = event.description or f"State: {state_str}"
            output_lines.append(f"{time_str} - {description}")
        
        return "\n".join(output_lines)
    
    def generate_session_summary(self) -> Dict[str, Any]:
        """Generate comprehensive session summary."""
        now = datetime.now()
        duration = (now - self.session_start).total_seconds() / 60.0  # minutes
        
        summary = {
            'session_start': self.session_start.isoformat(),
            'session_end': now.isoformat(),
            'duration_minutes': duration,
            'total_events': len(self.events),
            'states': dict(self.states),
            'peaks': dict(self.peak_values),
            'events': [
                {
                    'timestamp': event.timestamp.strftime("%H:%M:%S"),
                    'description': event.description,
                    'state': event.state
                } for event in self.events
            ]
        }
        
        return summary
    
    def generate_session_summary_text(self) -> str:
        """Generate formatted text summary of the session."""
        summary = self.generate_session_summary()
        
        output_lines = []
        output_lines.append("🧠 Session Summary")
        output_lines.append("=" * 50)
        
        # Duration and basic stats
        duration = summary['duration_minutes']
        total_events = summary['total_events']
        output_lines.append(f"Duration: {duration:.1f} minutes")
        output_lines.append(f"Total events: {total_events}")
        output_lines.append("")
        
        # State distribution
        states = summary['states']
        if states:
            output_lines.append("State Distribution:")
            sorted_states = sorted(states.items(), key=lambda x: x[1], reverse=True)
            total_states = sum(states.values())
            
            for state, count in sorted_states:
                percentage = (count / total_states) * 100 if total_states > 0 else 0
                output_lines.append(f"  {state}: {count} ({percentage:.1f}%)")
            output_lines.append("")
        
        # Peak values
        peaks = summary['peaks']
        if peaks:
            output_lines.append("Peak Values:")
            for metric, value in sorted(peaks.items()):
                metric_name = metric.replace('peak_', '').title()
                output_lines.append(f"  {metric_name}: {value:.1f}%")
            output_lines.append("")
        
        # Recent significant events
        events = summary['events']
        if events:
            output_lines.append(f"Recent Events ({min(10, len(events))}):")
            for event in events[-10:]:
                timestamp = event['timestamp']
                description = event['description']
                output_lines.append(f"  {timestamp}: {description}")
        
        return "\n".join(output_lines)
    
    def generate_therapeutic_report(self, results: List[AnalysisResult]) -> str:
        """Generate therapeutic patterns report."""
        if not results:
            return "No data available for therapeutic report"
        
        output_lines = []
        output_lines.append("🧘 Therapeutic Patterns Report")
        output_lines.append("=" * 50)
        
        # Analyze therapeutic states
        therapeutic_states = {}
        total_readings = len(results)
        
        for result in results:
            state = result.state.lower()
            
            # Group related therapeutic states
            if 'jhana' in state or 'flow' in state:
                category = 'Meditative States'
            elif 'young' in state or 'hopeful' in state or 'cautious' in state:
                category = 'Parts Work'
            elif 'security' in state or 'anxiety' in state or 'startled' in state:
                category = 'Nervous System'
            elif 'integration' in state:
                category = 'Integration'
            else:
                category = 'General States'
            
            if category not in therapeutic_states:
                therapeutic_states[category] = {}
            
            if result.state not in therapeutic_states[category]:
                therapeutic_states[category][result.state] = 0
            therapeutic_states[category][result.state] += 1
        
        # Generate report sections
        for category, states in therapeutic_states.items():
            if not states:
                continue
                
            output_lines.append(f"\n{category}:")
            category_total = sum(states.values())
            category_percentage = (category_total / total_readings) * 100
            output_lines.append(f"  Total time: {category_percentage:.1f}% of session")
            
            for state, count in sorted(states.items(), key=lambda x: x[1], reverse=True):
                state_percentage = (count / total_readings) * 100
                output_lines.append(f"    {state}: {state_percentage:.1f}%")
        
        # Add insights section
        output_lines.append("\n💡 Therapeutic Insights:")
        
        # Check for meditation progression
        jhana_count = sum(1 for r in results if 'jhana' in r.state.lower())
        flow_count = sum(1 for r in results if 'flow' in r.state.lower())
        
        if jhana_count > 0:
            jhana_percentage = (jhana_count / total_readings) * 100
            output_lines.append(f"  • Transcendent states achieved {jhana_percentage:.1f}% of time")
        
        if flow_count > 0:
            flow_percentage = (flow_count / total_readings) * 100
            output_lines.append(f"  • Flow states present {flow_percentage:.1f}% of time")
        
        # Check for parts work
        parts_states = ['young', 'hopeful', 'cautious']
        parts_count = sum(1 for r in results 
                         for part in parts_states 
                         if part in r.state.lower())
        
        if parts_count > 0:
            parts_percentage = (parts_count / total_readings) * 100
            output_lines.append(f"  • Parts work patterns detected {parts_percentage:.1f}% of time")
        
        # Check for nervous system activation
        security_count = sum(1 for r in results if 'security' in r.state.lower())
        if security_count > 0:
            security_percentage = (security_count / total_readings) * 100
            output_lines.append(f"  • Security guard activations: {security_percentage:.1f}% of time")
        
        return "\n".join(output_lines)
    
    def export_session_data(self, filename: Optional[str] = None) -> str:
        """Export session data to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"consciousness_session_{timestamp}.json"
        
        summary = self.generate_session_summary()
        
        try:
            with open(filename, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            return f"Session data exported to {filename}"
        except Exception as e:
            return f"Export failed: {e}"
    
    def clear_session_data(self):
        """Clear accumulated session data."""
        self.events.clear()
        self.states.clear()
        self.peak_values.clear()
        self.session_start = datetime.now()