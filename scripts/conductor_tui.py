#!/usr/bin/env python3
"""
Neural Music Conductor TUI

Real-time terminal interface for brain-responsive music generation.
Replaces conductor.sh with a proper interactive TUI.

Usage:
    DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" uv run python scripts/conductor_tui.py
"""

import asyncio
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import yaml
import psycopg2
from psycopg2.extras import RealDictCursor

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Input, Button, ProgressBar, Log
from textual.reactive import reactive
from textual import work

# Chicago timezone
CHICAGO_TZ = ZoneInfo("America/Chicago")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
BEATS_LIBRARY_PATH = PROJECT_ROOT / "config" / "beats-library.yaml"
CONDUCTOR_PROMPT_PATH = PROJECT_ROOT / "config" / "conductor-prompt.md"
PATTERN_FILE = Path("/mnt/c/projects/prompt-kit/chrome-automation/pattern.txt")
SESSION_FILE = Path("/tmp/conductor_session.json")
DECISION_FILE = Path("/tmp/conductor_decision.json")
REASONING_LOG = PROJECT_ROOT / "logs" / "conductor_reasoning.log"

# LLM Mode toggle
USE_LLM_CONDUCTOR = os.environ.get("LLM_CONDUCTOR", "1") == "1"

# Database
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://eeg:eegpass@localhost:5590/eeg'
)


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


def to_chicago(ts) -> str:
    """Convert timestamp to Chicago time string."""
    if ts is None:
        return ""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(CHICAGO_TZ).strftime("%H:%M:%S")


def load_beats_library() -> dict:
    """Load the beats library from YAML."""
    if not BEATS_LIBRARY_PATH.exists():
        return {"library": {}, "mood_state_map": {}}
    with open(BEATS_LIBRARY_PATH) as f:
        return yaml.safe_load(f)


def get_current_eeg_state(window_seconds: int = 10) -> dict:
    """Get current EEG state from database."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                MAX(ts_start) as ts_start,
                AVG(alpha_rel) as alpha_rel,
                AVG(beta_rel) as beta_rel,
                AVG(delta_rel) as delta_rel,
                AVG(theta_rel) as theta_rel,
                AVG(gamma_rel) as gamma_rel,
                COUNT(*) as sample_count,
                MODE() WITHIN GROUP (ORDER BY features->>'state') as dominant_state
            FROM eeg_window
            WHERE ts_start > NOW() - INTERVAL '%s seconds'
        """, (window_seconds,))

        row = cur.fetchone()
        conn.close()

        if not row or row['sample_count'] == 0:
            return {"status": "no_data", "state": "NO_DATA"}

        ts = row['ts_start']
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()

        return {
            "status": "ok",
            "timestamp": to_chicago(ts),
            "data_age_seconds": round(age_seconds, 1),
            "is_fresh": age_seconds < 10,
            "state": row['dominant_state'] or "UNKNOWN",
            "bands": {
                "alpha": round(float(row['alpha_rel'] or 0), 1),
                "beta": round(float(row['beta_rel'] or 0), 1),
                "delta": round(float(row['delta_rel'] or 0), 1),
                "theta": round(float(row['theta_rel'] or 0), 1),
                "gamma": round(float(row['gamma_rel'] or 0), 1),
            }
        }
    except Exception as e:
        return {"status": "error", "state": "ERROR", "message": str(e)}


def get_state_history(minutes: int = 5) -> list:
    """Get recent state transitions."""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT ts_start, features->>'state' as state
            FROM eeg_window
            WHERE ts_start > NOW() - INTERVAL '%s minutes'
            ORDER BY ts_start DESC
            LIMIT 60
        """, (minutes,))

        rows = cur.fetchall()
        conn.close()
        return list(reversed(rows))
    except Exception:
        return []


def select_pattern_for_state(state: str, library: dict, recent_patterns: list) -> Optional[dict]:
    """Select a pattern matching the brain state, avoiding recent patterns."""
    mood_map = library.get("mood_state_map", {})
    patterns = library.get("library", {})

    # Get target moods for this state
    target_moods = mood_map.get(state, [])
    if not target_moods:
        # Fallback moods
        target_moods = ["flow", "ambient"]

    # Find matching patterns
    matching = []
    for name, data in patterns.items():
        pattern_moods = data.get("moods", [])
        if any(m in target_moods for m in pattern_moods):
            matching.append((name, data))

    if not matching:
        return None

    # Avoid recently played patterns
    available = [(n, d) for n, d in matching if n not in recent_patterns[-3:]]
    if not available:
        available = matching

    # Random selection
    name, data = random.choice(available)
    return {"name": name, **data}


def play_pattern_sync(pattern_code: str) -> tuple[bool, str]:
    """Write pattern to file and trigger Strudel playback (sync version)."""
    try:
        # Write pattern to file
        PATTERN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PATTERN_FILE, 'w') as f:
            f.write(pattern_code)

        # Execute via PowerShell
        cmd = [
            'powershell.exe', '-Command',
            "cd C:\\projects\\prompt-kit\\chrome-automation; "
            "$env:CDP_PORT='9223'; "
            "node scripts/run-automation.mjs strudel-play-file.mjs pattern.txt"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return True, result.stdout
    except Exception as e:
        return False, str(e)


def log_reasoning(reasoning: str, pattern_name: str, action: str) -> None:
    """Append reasoning to the log file."""
    REASONING_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(REASONING_LOG, 'a') as f:
        f.write(f"\n[{timestamp}] Action: {action}\n")
        f.write(f"Pattern: {pattern_name}\n")
        f.write(f"Reasoning: {reasoning}\n")
        f.write("-" * 60 + "\n")


def call_llm_conductor(eeg_state: dict, current_pattern: str, pattern_duration_min: float,
                       library: dict, user_message: str = None) -> Optional[dict]:
    """Call Claude Code CLI to make conductor decision."""
    # Build context for Claude
    patterns_summary = []
    for name, data in library.get("library", {}).items():
        moods = ", ".join(data.get("moods", []))
        patterns_summary.append(f"- {name}: {moods}")

    context = f"""## Current State
- EEG State: {eeg_state.get('state', 'UNKNOWN')}
- Alpha: {eeg_state.get('bands', {}).get('alpha', 0):.1f}%
- Beta: {eeg_state.get('bands', {}).get('beta', 0):.1f}%
- Theta: {eeg_state.get('bands', {}).get('theta', 0):.1f}%
- Delta: {eeg_state.get('bands', {}).get('delta', 0):.1f}%
- Gamma: {eeg_state.get('bands', {}).get('gamma', 0):.1f}%
- Data Fresh: {eeg_state.get('is_fresh', False)}

## Current Pattern
- Name: {current_pattern or 'None'}
- Playing for: {pattern_duration_min:.1f} minutes

## Available Patterns
{chr(10).join(patterns_summary)}

## User Message
{user_message or 'None'}

## Your Task
Decide whether to change the pattern or keep it. Write your decision to {DECISION_FILE}.
Remember: stability is good, don't change too often unless the state clearly calls for it.
"""

    # Read system prompt
    system_prompt = ""
    if CONDUCTOR_PROMPT_PATH.exists():
        system_prompt = CONDUCTOR_PROMPT_PATH.read_text()

    # Pre-create decision file (Write tool requires file to exist)
    DECISION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DECISION_FILE, 'w') as f:
        json.dump({"action": "pending"}, f)

    # Call Claude CLI
    try:
        cmd = [
            '/home/kodell/.claude/local/claude',
            '-p',
            '--dangerously-skip-permissions',
            '--tools', 'Read,Write,WebSearch,WebFetch,mcp__eeg-consciousness__get_current_eeg_state',
            '--append-system-prompt', system_prompt,
            context
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        # Debug: log any errors from Claude
        if result.returncode != 0 or result.stderr:
            log_reasoning(f"Claude stderr: {result.stderr[:500] if result.stderr else 'none'}", "N/A", "debug")

        # Read decision file
        if DECISION_FILE.exists():
            with open(DECISION_FILE) as f:
                decision = json.load(f)

            # Check if Claude actually wrote a decision
            if decision.get('action') == 'pending':
                log_reasoning("Claude did not write a decision", "N/A", "error")
                return None

            # Log the reasoning
            log_reasoning(
                decision.get('reasoning', 'No reasoning provided'),
                decision.get('pattern_name', 'N/A'),
                decision.get('action', 'unknown')
            )

            return decision
        else:
            return None
    except Exception as e:
        log_reasoning(f"LLM call failed: {e}", "N/A", "error")
        return None


def load_session() -> dict:
    """Load session state from file."""
    if SESSION_FILE.exists():
        with open(SESSION_FILE) as f:
            return json.load(f)
    return {
        "last_states": [],
        "recent_patterns": [],
        "current_pattern": None,
        "pattern_start_time": None,
        "paused": False
    }


def save_session(session: dict):
    """Save session state to file."""
    with open(SESSION_FILE, 'w') as f:
        json.dump(session, f)


# ============================================================================
# TUI Widgets
# ============================================================================

class BrainStateWidget(Static):
    """Displays current brain state and band powers."""

    state = reactive("WAITING")
    alpha = reactive(0.0)
    beta = reactive(0.0)
    delta = reactive(0.0)
    theta = reactive(0.0)
    gamma = reactive(0.0)
    timestamp = reactive("")
    fresh = reactive(True)

    def render(self) -> str:
        state_emoji = {
            "K_FLOW": "~",
            "K_PLAYING": "*",
            "K_DOWNSHIFT": "v",
            "K_HIGH_LOAD": "!",
            "K_THINKING": "?",
            "K_MUSICAL_CHILLS": "^",
            "NO_DATA": ".",
            "ERROR": "X",
        }.get(self.state, "o")

        fresh_indicator = "[green]LIVE[/]" if self.fresh else "[red]STALE[/]"

        def bar(val: float, width: int = 20) -> str:
            filled = int(val / 100 * width)
            return "[cyan]" + "#" * filled + "[/][dim]" + "-" * (width - filled) + "[/]"

        return f"""[bold]Brain State[/] {fresh_indicator}
[bold yellow]{self.state}[/] {state_emoji}  [{self.timestamp}]
{"=" * 36}
[blue]a[/] Alpha  {bar(self.alpha)} {self.alpha:5.1f}%
[green]b[/] Beta   {bar(self.beta)} {self.beta:5.1f}%
[magenta]d[/] Delta  {bar(self.delta)} {self.delta:5.1f}%
[yellow]t[/] Theta  {bar(self.theta)} {self.theta:5.1f}%
[red]g[/] Gamma  {bar(self.gamma)} {self.gamma:5.1f}%"""


class PatternWidget(Static):
    """Displays current pattern info."""

    pattern_name = reactive("none")
    moods = reactive("")
    playing_for = reactive("0:00")
    paused = reactive(False)

    def render(self) -> str:
        status = "[yellow]PAUSED[/]" if self.paused else "[green]PLAYING[/]"
        return f"""[bold]Current Pattern[/] {status}
{"=" * 30}
[cyan]{self.pattern_name}[/]
Moods: {self.moods}
Duration: {self.playing_for}

[dim][Space] Pause  [N] Next  [R] Regen[/]"""


class HistoryWidget(Static):
    """Shows state transition history."""

    history = reactive("")

    def render(self) -> str:
        return f"""[bold]State History[/] (5 min)
{"=" * 40}
{self.history or "[dim]No history yet[/]"}"""


class MessageInput(Static):
    """Input for sending messages to Claude."""

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Message to conductor (Enter=queue, Ctrl+Enter=immediate)")


# ============================================================================
# Main App
# ============================================================================

class ConductorApp(App):
    """Neural Music Conductor TUI."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-rows: auto auto 1fr;
    }

    BrainStateWidget {
        border: solid green;
        padding: 1;
        height: auto;
    }

    PatternWidget {
        border: solid cyan;
        padding: 1;
        height: auto;
    }

    HistoryWidget {
        border: solid yellow;
        padding: 1;
        column-span: 2;
        height: auto;
    }

    #log-container {
        border: solid blue;
        column-span: 2;
        height: 100%;
    }

    Log {
        height: 100%;
    }

    #input-container {
        border: solid magenta;
        column-span: 2;
        height: auto;
        padding: 1;
    }

    Input {
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("space", "toggle_pause", "Pause"),
        Binding("n", "next_pattern", "Next"),
        Binding("r", "regenerate", "Regen"),
        Binding("ctrl+enter", "send_immediate", "Send Now", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.library = load_beats_library()
        self.session = load_session()
        self.poll_interval = 3.0  # seconds
        self.change_cooldown = 30  # seconds between pattern changes
        self.last_change_time = 0
        self.pending_message: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield BrainStateWidget()
        yield PatternWidget()
        yield HistoryWidget()
        yield Container(Log(highlight=True), id="log-container")
        yield Container(
            Input(placeholder="Message to conductor (Enter=queue, Ctrl+Enter=immediate)"),
            id="input-container"
        )
        yield Footer()

    def on_mount(self) -> None:
        """Start background tasks on mount."""
        self.log_message("[bold green]Neural Music Conductor started[/]")
        mode = "[bold cyan]LLM Mode (Claude Code)[/]" if USE_LLM_CONDUCTOR else "[yellow]Rule-based Mode[/]"
        self.log_message(f"Mode: {mode}")
        self.log_message(f"Loaded {len(self.library.get('library', {}))} patterns")
        if USE_LLM_CONDUCTOR:
            self.log_message(f"[dim]Reasoning log: {REASONING_LOG}[/]")
        self.set_interval(self.poll_interval, self.poll_eeg)
        self.set_interval(1.0, self.update_playing_time)

    def log_message(self, msg: str) -> None:
        """Add message to log."""
        log = self.query_one(Log)
        timestamp = datetime.now().strftime("%H:%M:%S")
        log.write_line(f"[dim]{timestamp}[/] {msg}")

    @work(exclusive=True)
    async def poll_eeg(self) -> None:
        """Poll EEG state and update UI."""
        eeg = get_current_eeg_state()

        # Update brain state widget
        brain_widget = self.query_one(BrainStateWidget)
        brain_widget.state = eeg.get("state", "UNKNOWN")
        brain_widget.timestamp = eeg.get("timestamp", "")
        brain_widget.fresh = eeg.get("is_fresh", False)

        bands = eeg.get("bands", {})
        brain_widget.alpha = bands.get("alpha", 0)
        brain_widget.beta = bands.get("beta", 0)
        brain_widget.delta = bands.get("delta", 0)
        brain_widget.theta = bands.get("theta", 0)
        brain_widget.gamma = bands.get("gamma", 0)

        # Update history
        history = get_state_history(5)
        if history:
            # Group consecutive states
            grouped = []
            current_state = None
            count = 0
            for row in history:
                if row['state'] != current_state:
                    if current_state:
                        grouped.append(f"{current_state}({count})")
                    current_state = row['state']
                    count = 1
                else:
                    count += 1
            if current_state:
                grouped.append(f"{current_state}({count})")

            self.query_one(HistoryWidget).history = " -> ".join(grouped[-6:])

        # Check if we should change pattern
        await self.maybe_change_pattern(eeg)

    async def maybe_change_pattern(self, eeg: dict) -> None:
        """Decide whether to change the pattern based on EEG state."""
        if self.session.get("paused"):
            return

        state = eeg.get("state", "UNKNOWN")
        if state in ("NO_DATA", "ERROR", "UNKNOWN"):
            return

        # Track state history
        last_states = self.session.get("last_states", [])
        last_states.append(state)
        last_states = last_states[-5:]  # Keep last 5
        self.session["last_states"] = last_states

        # Check cooldown
        now = asyncio.get_event_loop().time()
        if now - self.last_change_time < self.change_cooldown:
            # Allow override for user messages
            if not self.pending_message:
                return

        # Get user message if any
        user_message = self.pending_message
        self.pending_message = None

        if USE_LLM_CONDUCTOR:
            await self.llm_decide_pattern(eeg, user_message)
        else:
            # Legacy rule-based logic
            should_change = False
            reason = ""

            if len(last_states) >= 3 and last_states[-1] != last_states[-2] and last_states[-1] != last_states[-3]:
                should_change = True
                reason = f"State changed to {state}"

            if not self.session.get("current_pattern"):
                should_change = True
                reason = "Initial pattern"

            if user_message:
                should_change = True
                reason = f"User request: {user_message}"

            if should_change:
                await self.change_pattern(state, reason)

    async def llm_decide_pattern(self, eeg: dict, user_message: str = None) -> None:
        """Use Claude Code to decide pattern changes."""
        import concurrent.futures

        # Calculate pattern duration
        pattern_duration_min = 0.0
        start_str = self.session.get("pattern_start_time")
        if start_str:
            start = datetime.fromisoformat(start_str)
            pattern_duration_min = (datetime.now() - start).total_seconds() / 60

        current_pattern = self.session.get("current_pattern")

        self.log_message(f"[cyan]Asking Claude for decision...[/]")

        # Call LLM in thread pool to not block
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                call_llm_conductor,
                eeg,
                current_pattern,
                pattern_duration_min,
                self.library,
                user_message
            )
            try:
                decision = future.result(timeout=90)
            except Exception as e:
                self.log_message(f"[red]LLM call failed: {e}[/]")
                return

        if not decision:
            self.log_message(f"[yellow]No decision from LLM[/]")
            return

        action = decision.get("action", "keep")
        reasoning = decision.get("reasoning", "No reason given")

        # Truncate reasoning for display
        short_reasoning = reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
        self.log_message(f"[dim]LLM: {short_reasoning}[/]")

        if action == "keep":
            self.log_message(f"[blue]Keeping current pattern[/]")
            return

        # Action is "change"
        pattern_name = decision.get("pattern_name")
        pattern_code = decision.get("pattern_code")

        if not pattern_code:
            # Look up pattern from library
            lib_pattern = self.library.get("library", {}).get(pattern_name)
            if lib_pattern:
                pattern_code = lib_pattern.get("pattern")
            else:
                self.log_message(f"[red]Pattern {pattern_name} not found[/]")
                return

        self.log_message(f"[green]Playing: {pattern_name}[/]")

        # Play the pattern
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(play_pattern_sync, pattern_code)
            success, output = future.result(timeout=20)

        self.log_message(f"[dim]Automation: {output[:100] if output else 'no output'}[/]")
        if success:
            self.session["current_pattern"] = pattern_name
            self.session["pattern_start_time"] = datetime.now().isoformat()
            recent = self.session.get("recent_patterns", [])
            recent.append(pattern_name)
            self.session["recent_patterns"] = recent[-10:]
            self.last_change_time = asyncio.get_event_loop().time()

            # Update pattern widget
            pw = self.query_one(PatternWidget)
            pw.pattern_name = pattern_name
            lib_pattern = self.library.get("library", {}).get(pattern_name, {})
            pw.moods = ", ".join(lib_pattern.get("moods", []))

            save_session(self.session)
        else:
            self.log_message("[red]Failed to play pattern[/]")

    async def change_pattern(self, state: str, reason: str) -> None:
        """Select and play a new pattern."""
        recent = self.session.get("recent_patterns", [])
        pattern = select_pattern_for_state(state, self.library, recent)

        if not pattern:
            self.log_message(f"[yellow]No pattern found for state {state}[/]")
            return

        self.log_message(f"[cyan]{reason}[/]")
        self.log_message(f"[green]Playing: {pattern['name']}[/] ({', '.join(pattern.get('moods', []))})")

        # Play the pattern (run in thread to not block)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(play_pattern_sync, pattern['pattern'])
            success, output = future.result(timeout=20)

        self.log_message(f"[dim]Automation: {output[:100] if output else 'no output'}[/]")
        if success:
            self.session["current_pattern"] = pattern['name']
            self.session["pattern_start_time"] = datetime.now().isoformat()
            recent.append(pattern['name'])
            self.session["recent_patterns"] = recent[-10:]
            self.last_change_time = asyncio.get_event_loop().time()

            # Update pattern widget
            pw = self.query_one(PatternWidget)
            pw.pattern_name = pattern['name']
            pw.moods = ", ".join(pattern.get('moods', []))

            save_session(self.session)
        else:
            self.log_message("[red]Failed to play pattern[/]")

    def update_playing_time(self) -> None:
        """Update the playing duration display."""
        start_str = self.session.get("pattern_start_time")
        if start_str:
            start = datetime.fromisoformat(start_str)
            duration = datetime.now() - start
            minutes = int(duration.total_seconds() // 60)
            seconds = int(duration.total_seconds() % 60)
            self.query_one(PatternWidget).playing_for = f"{minutes}:{seconds:02d}"

    def action_toggle_pause(self) -> None:
        """Toggle pause state."""
        self.session["paused"] = not self.session.get("paused", False)
        self.query_one(PatternWidget).paused = self.session["paused"]
        status = "paused" if self.session["paused"] else "resumed"
        self.log_message(f"[yellow]Conductor {status}[/]")
        save_session(self.session)

    def action_next_pattern(self) -> None:
        """Force next pattern."""
        self.pending_message = "next pattern"
        self.last_change_time = 0  # Reset cooldown

    def action_regenerate(self) -> None:
        """Regenerate/reshuffle pattern."""
        self.pending_message = "different pattern"
        self.last_change_time = 0

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key on input - queue message for next cycle."""
        if event.value.strip():
            self.pending_message = event.value.strip()
            self.log_message(f"[magenta]Queued: {event.value}[/]")
            event.input.value = ""

    def action_send_immediate(self) -> None:
        """Handle Ctrl+Enter - send message immediately."""
        input_widget = self.query_one(Input)
        if input_widget.value.strip():
            self.pending_message = input_widget.value.strip()
            self.last_change_time = 0  # Reset cooldown for immediate action
            self.log_message(f"[bold magenta]Immediate: {input_widget.value}[/]")
            input_widget.value = ""


def reset_terminal():
    """Reset terminal to normal mode (disable mouse tracking, etc)."""
    import sys
    # Disable mouse tracking modes
    sys.stdout.write('\x1b[?1000l')  # Disable mouse click tracking
    sys.stdout.write('\x1b[?1003l')  # Disable all mouse tracking
    sys.stdout.write('\x1b[?1006l')  # Disable SGR mouse mode
    sys.stdout.flush()


def main():
    """Run the conductor TUI."""
    import atexit
    atexit.register(reset_terminal)

    try:
        app = ConductorApp()
        app.run()
    finally:
        reset_terminal()


if __name__ == "__main__":
    main()
