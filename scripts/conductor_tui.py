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
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import yaml
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

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
MUSIC_PREFERENCES_PATH = PROJECT_ROOT / "config" / "music-preferences.yaml"
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

# Connection pool (initialized lazily)
_db_pool: Optional[pool.ThreadedConnectionPool] = None


def get_db_pool() -> pool.ThreadedConnectionPool:
    """Get or create the database connection pool."""
    global _db_pool
    if _db_pool is None:
        _db_pool = pool.ThreadedConnectionPool(1, 5, DATABASE_URL)
    return _db_pool


def get_db_connection():
    """Get database connection from pool."""
    return get_db_pool().getconn()


def release_db_connection(conn):
    """Return connection to pool."""
    try:
        get_db_pool().putconn(conn)
    except Exception:
        pass


# Chrome CDP settings
CDP_PORT = os.environ.get('CDP_PORT', '9223')
CDP_HOST = os.environ.get('CDP_HOST', 'localhost')

# ============================================================================
# Hubitat Light Control
# ============================================================================

# Load Hubitat credentials from env file
HUBITAT_ENV_FILE = Path.home() / ".config" / "smart-home" / ".env"
HUBITAT_IP = "192.168.1.125"
HUBITAT_DEVICE_ID = "37"  # Office RGB light

# Light color mappings for brain states (hue 0-100, saturation 0-100, level 0-100)
STATE_LIGHT_MAP = {
    "K_FLOW": {"hue": 66, "sat": 70, "level": 60, "desc": "calm blue"},
    "K_PLAYING": {"hue": 78, "sat": 80, "level": 70, "desc": "purple"},
    "K_DOWNSHIFT": {"hue": 10, "sat": 80, "level": 50, "desc": "warm amber"},
    "K_HIGH_LOAD": {"hue": 0, "sat": 60, "level": 40, "desc": "soft red"},
    "K_THINKING": {"hue": 50, "sat": 50, "level": 70, "desc": "neutral warm"},
    "K_MUSICAL_CHILLS": {"hue": 78, "sat": 90, "level": 80, "desc": "vivid purple"},
    "K_CONTAINED_DISTRESS": {"hue": 0, "sat": 100, "level": 30, "desc": "red"},
}

# Default light settings when no state mapping
DEFAULT_LIGHT = {"hue": 40, "sat": 30, "level": 50, "desc": "warm white"}


def load_hubitat_credentials() -> tuple[Optional[str], Optional[str]]:
    """Load Hubitat API credentials from env file."""
    if not HUBITAT_ENV_FILE.exists():
        return None, None

    app_id = None
    token = None

    with open(HUBITAT_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("HUBITAT_APP_ID="):
                app_id = line.split("=", 1)[1].strip('"\'')
            elif line.startswith("HUBITAT_TOKEN="):
                token = line.split("=", 1)[1].strip('"\'')

    return app_id, token


def set_light(hue: int = None, sat: int = None, level: int = None,
              color_temp: int = None, on: bool = None) -> tuple[bool, str]:
    """Control the office RGB light via Hubitat API.

    Args:
        hue: Hue value 0-100
        sat: Saturation value 0-100
        level: Brightness level 0-100
        color_temp: Color temperature in Kelvin (overrides hue/sat for white)
        on: True to turn on, False to turn off

    Returns:
        (success, message) tuple
    """
    app_id, token = load_hubitat_credentials()
    if not app_id or not token:
        return False, "Hubitat credentials not found"

    base_url = f"http://{HUBITAT_IP}/apps/api/{app_id}/devices/{HUBITAT_DEVICE_ID}"
    commands = []

    if on is not None:
        commands.append(("on" if on else "off", None))

    if color_temp is not None:
        commands.append((f"setColorTemperature/{color_temp}", None))
    else:
        if hue is not None:
            commands.append((f"setHue/{hue}", None))
        if sat is not None:
            commands.append((f"setSaturation/{sat}", None))

    if level is not None:
        commands.append((f"setLevel/{level}", None))

    if not commands:
        return True, "No commands to execute"

    for cmd, _ in commands:
        url = f"{base_url}/{cmd}?access_token={token}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                pass  # Just need success status
        except urllib.error.URLError as e:
            return False, f"Light API error: {e}"
        except Exception as e:
            return False, f"Light error: {e}"

    return True, "Light updated"


def set_light_for_state(state: str) -> tuple[bool, str]:
    """Set light color/brightness based on brain state.

    Returns:
        (success, message) tuple with description of light setting
    """
    settings = STATE_LIGHT_MAP.get(state, DEFAULT_LIGHT)
    success, msg = set_light(
        hue=settings["hue"],
        sat=settings["sat"],
        level=settings["level"]
    )
    if success:
        return True, f"Light: {settings['desc']} (h:{settings['hue']} s:{settings['sat']} l:{settings['level']})"
    return False, msg


def check_chrome_cdp(timeout: float = 2.0) -> tuple[bool, str]:
    """Check if Chrome CDP is available. Returns (success, message)."""
    import socket
    try:
        # Quick socket check first
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((CDP_HOST, int(CDP_PORT)))
        sock.close()
        if result != 0:
            return False, f"Chrome not listening on {CDP_HOST}:{CDP_PORT}"
        return True, f"Chrome CDP available on port {CDP_PORT}"
    except Exception as e:
        return False, str(e)


def wait_for_chrome_cdp(max_retries: int = 5, retry_delay: float = 2.0) -> bool:
    """Wait for Chrome CDP to become available. Returns True if connected."""
    for attempt in range(max_retries):
        ok, msg = check_chrome_cdp()
        if ok:
            return True
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
    return False


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


def load_music_preferences() -> dict:
    """Load music preferences from YAML."""
    default_prefs = {
        "likes": [],      # List of {pattern, reason, timestamp}
        "dislikes": [],   # List of {pattern, reason, timestamp}
        "notes": [],      # General notes about preferences
    }
    if not MUSIC_PREFERENCES_PATH.exists():
        return default_prefs
    with open(MUSIC_PREFERENCES_PATH) as f:
        prefs = yaml.safe_load(f) or {}
    # Merge with defaults for any missing keys
    for key in default_prefs:
        if key not in prefs:
            prefs[key] = default_prefs[key]
    return prefs


def save_music_preferences(prefs: dict) -> None:
    """Save music preferences to YAML."""
    MUSIC_PREFERENCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MUSIC_PREFERENCES_PATH, 'w') as f:
        yaml.dump(prefs, f, default_flow_style=False, sort_keys=False)


def add_preference_feedback(pattern_name: str, feedback_type: str, reason: str) -> None:
    """Add feedback for a pattern (like/dislike)."""
    prefs = load_music_preferences()
    entry = {
        "pattern": pattern_name,
        "reason": reason,
        "timestamp": datetime.now().isoformat()
    }

    key = "likes" if feedback_type == "like" else "dislikes"
    prefs[key].append(entry)

    # Also remove from opposite list if present (changed mind)
    opposite = "dislikes" if feedback_type == "like" else "likes"
    prefs[opposite] = [e for e in prefs[opposite] if e["pattern"] != pattern_name]

    save_music_preferences(prefs)


def get_current_eeg_state(window_seconds: int = 10) -> dict:
    """Get current EEG state from database."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Optimized query: get latest state directly instead of MODE() aggregate
        # This is faster and gives more immediate feedback
        cur.execute("""
            SELECT
                ts_start,
                alpha_rel, beta_rel, delta_rel, theta_rel, gamma_rel,
                features->>'state' as state
            FROM eeg_window
            WHERE ts_start > NOW() - INTERVAL '%s seconds'
            ORDER BY ts_start DESC
            LIMIT 20
        """, (window_seconds,))

        rows = cur.fetchall()

        if not rows:
            return {"status": "no_data", "state": "NO_DATA"}

        # Use latest row for timestamp and state
        latest = rows[0]
        ts = latest['ts_start']
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()

        # Average band powers across recent samples
        n = len(rows)
        bands = {
            "alpha": round(sum(float(r['alpha_rel'] or 0) for r in rows) / n, 1),
            "beta": round(sum(float(r['beta_rel'] or 0) for r in rows) / n, 1),
            "delta": round(sum(float(r['delta_rel'] or 0) for r in rows) / n, 1),
            "theta": round(sum(float(r['theta_rel'] or 0) for r in rows) / n, 1),
            "gamma": round(sum(float(r['gamma_rel'] or 0) for r in rows) / n, 1),
        }

        # Get most common state from recent samples
        from collections import Counter
        states = [r['state'] for r in rows if r['state']]
        dominant_state = Counter(states).most_common(1)[0][0] if states else "UNKNOWN"

        return {
            "status": "ok",
            "timestamp": to_chicago(ts),
            "data_age_seconds": round(age_seconds, 1),
            "is_fresh": age_seconds < 10,
            "state": dominant_state,
            "bands": bands
        }
    except Exception as e:
        return {"status": "error", "state": "ERROR", "message": str(e)}
    finally:
        if conn:
            release_db_connection(conn)


def get_state_history(minutes: int = 5) -> list:
    """Get recent state transitions."""
    conn = None
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
        return list(reversed(rows))
    except Exception:
        return []
    finally:
        if conn:
            release_db_connection(conn)


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
                       library: dict, user_message: str = None,
                       preferences: dict = None) -> Optional[dict]:
    """Call Claude Code CLI to make conductor decision."""
    # Build context for Claude
    patterns_summary = []
    for name, data in library.get("library", {}).items():
        moods = ", ".join(data.get("moods", []))
        patterns_summary.append(f"- {name}: {moods}")

    # Build preferences summary
    prefs_section = ""
    if preferences:
        likes = preferences.get("likes", [])
        dislikes = preferences.get("dislikes", [])
        notes = preferences.get("notes", [])

        if likes or dislikes or notes:
            prefs_lines = ["## User Music Preferences (IMPORTANT - use this to guide selection)"]
            if likes:
                prefs_lines.append("\n### Liked Patterns:")
                for entry in likes[-10:]:  # Last 10 likes
                    prefs_lines.append(f"- {entry['pattern']}: {entry.get('reason', 'no reason')}")
            if dislikes:
                prefs_lines.append("\n### Disliked Patterns (AVOID THESE):")
                for entry in dislikes[-10:]:  # Last 10 dislikes
                    prefs_lines.append(f"- {entry['pattern']}: {entry.get('reason', 'no reason')}")
            if notes:
                prefs_lines.append("\n### General Preferences:")
                for note in notes[-5:]:
                    prefs_lines.append(f"- {note}")
            prefs_section = "\n".join(prefs_lines) + "\n\n"

    # Check if in training mode (no EEG)
    is_training = eeg_state.get('state') == 'TRAINING'

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

{prefs_section}## Available Patterns
{chr(10).join(patterns_summary)}

## User Message
{user_message or 'None'}

## Your Task
{"TRAINING MODE: Focus on user preferences, not EEG. " if is_training else ""}Decide whether to change the pattern or keep it. Write your decision to {DECISION_FILE}.
{"Select patterns the user has liked or that match their stated preferences. Avoid disliked patterns!" if is_training else "Remember: stability is good, don't change too often unless the state clearly calls for it."}
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
            log_reasoning("Decision file not found after Claude call", "N/A", "error")
            return None
    except Exception as e:
        log_reasoning(f"LLM call failed: {e}", "N/A", "error")
        return None


def load_session() -> dict:
    """Load session state from file."""
    default_session = {
        "last_states": [],
        "recent_patterns": [],
        "current_pattern": None,
        "pattern_start_time": None,
        "paused": False
    }

    if SESSION_FILE.exists():
        with open(SESSION_FILE) as f:
            session = json.load(f)

        # Reset pattern_start_time if it's stale (> 4 hours old)
        # This handles restarts where the session file persists but music isn't playing
        start_str = session.get("pattern_start_time")
        if start_str:
            try:
                start = datetime.fromisoformat(start_str)
                age_hours = (datetime.now() - start).total_seconds() / 3600
                if age_hours > 4:
                    # Pattern can't have been playing for 4+ hours, reset
                    session["pattern_start_time"] = None
                    session["current_pattern"] = None
            except (ValueError, TypeError):
                pass

        return session

    return default_session


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
            "TRAINING": "T",
        }.get(self.state, "o")

        # Training mode gets special indicator
        if self.state == "TRAINING":
            fresh_indicator = "[magenta]TRAINING[/]"
        else:
            fresh_indicator = "[green]LIVE[/]" if self.fresh else "[red]STALE[/]"

        def bar(val: float, width: int = 20) -> str:
            filled = int(val / 100 * width)
            return "[cyan]" + "#" * filled + "[/][dim]" + "-" * (width - filled) + "[/]"

        # In training mode, show different content
        if self.state == "TRAINING":
            return f"""[bold]Training Mode[/] {fresh_indicator}
[bold magenta]NO EEG REQUIRED[/] {state_emoji}
{"=" * 36}
[dim]Give feedback on patterns to train
your preferences. The system will
learn what music you like![/]

[L] Like  [D] Dislike  [N] Next"""

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
        Binding("l", "like_pattern", "Like"),
        Binding("d", "dislike_pattern", "Dislike"),
        Binding("ctrl+enter", "send_immediate", "Send Now", show=False),
    ]

    def __init__(self, no_eeg_mode: bool = False):
        super().__init__()
        self.no_eeg_mode = no_eeg_mode
        self.library = load_beats_library()
        self.preferences = load_music_preferences()
        self.session = load_session()
        self.poll_interval = 3.0  # seconds
        self.change_cooldown = 30  # seconds between pattern changes
        self.last_change_time = 0
        self.pending_message: Optional[str] = None
        self.awaiting_feedback: Optional[str] = None  # "like" or "dislike"

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

        if self.no_eeg_mode:
            self.log_message("[bold magenta]TRAINING MODE[/] - No EEG required")
            self.log_message("[dim]Press [L] to like, [D] to dislike current pattern[/]")
            self.log_message("[dim]Press [N] to play next pattern[/]")
            # Show training mode in brain widget
            brain_widget = self.query_one(BrainStateWidget)
            brain_widget.state = "TRAINING"
            brain_widget.fresh = True
        else:
            mode = "[bold cyan]LLM Mode (Claude Code)[/]" if USE_LLM_CONDUCTOR else "[yellow]Rule-based Mode[/]"
            self.log_message(f"Mode: {mode}")
            if USE_LLM_CONDUCTOR:
                self.log_message(f"[dim]Reasoning log: {REASONING_LOG}[/]")

        self.log_message(f"Loaded {len(self.library.get('library', {}))} patterns")

        # Show preferences summary
        likes = len(self.preferences.get("likes", []))
        dislikes = len(self.preferences.get("dislikes", []))
        if likes or dislikes:
            self.log_message(f"[dim]Preferences: {likes} likes, {dislikes} dislikes[/]")

        # Check Chrome CDP connection
        self.check_chrome_connection()

        # Only poll EEG if not in training mode
        if not self.no_eeg_mode:
            self.set_interval(self.poll_interval, self.poll_eeg)
        else:
            # In training mode, poll for user messages/requests
            self.set_interval(self.poll_interval, self.poll_training_messages)
        self.set_interval(1.0, self.update_playing_time)

    @work(exclusive=True, thread=True)
    def check_chrome_connection(self) -> None:
        """Check Chrome CDP connection in background."""
        ok, msg = check_chrome_cdp()
        if ok:
            self.call_from_thread(self.log_message, f"[green]Chrome: {msg}[/]")
        else:
            self.call_from_thread(self.log_message, f"[yellow]Chrome: {msg}[/]")
            self.call_from_thread(self.log_message, "[yellow]Waiting for Chrome CDP...[/]")
            if wait_for_chrome_cdp(max_retries=3, retry_delay=2.0):
                self.call_from_thread(self.log_message, "[green]Chrome CDP connected![/]")
            else:
                self.call_from_thread(self.log_message, "[red]Chrome CDP unavailable - pattern playback will fail[/]")
                self.call_from_thread(self.log_message, "[dim]Start Chrome with: chrome --remote-debugging-port=9223[/]")

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

    @work(exclusive=True)
    async def poll_training_messages(self) -> None:
        """In training mode, check for pending user messages and handle them."""
        if not self.pending_message:
            return

        # Build a fake "training" EEG state
        training_eeg = {
            "status": "ok",
            "state": "TRAINING",
            "is_fresh": True,
            "bands": {"alpha": 0, "beta": 0, "delta": 0, "theta": 0, "gamma": 0}
        }

        # Process the message through LLM conductor
        await self.llm_decide_pattern(training_eeg, self.pending_message)
        self.pending_message = None

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
                user_message,
                self.preferences  # Pass user preferences to guide selection
            )
            try:
                decision = future.result(timeout=90)
            except Exception as e:
                log_reasoning(f"LLM future failed: {e}", "N/A", "error")
                self.log_message(f"[red]LLM call failed: {e}[/]")
                return

        if not decision:
            # Already logged in call_llm_conductor
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

            # Update light for brain state
            current_state = eeg.get("state", "UNKNOWN")
            light_ok, light_msg = set_light_for_state(current_state)
            if light_ok:
                self.log_message(f"[yellow]{light_msg}[/]")
            else:
                self.log_message(f"[dim]Light: {light_msg}[/]")

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

            # Update light for brain state
            light_ok, light_msg = set_light_for_state(state)
            if light_ok:
                self.log_message(f"[yellow]{light_msg}[/]")
            else:
                self.log_message(f"[dim]Light: {light_msg}[/]")

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

    def action_like_pattern(self) -> None:
        """Mark current pattern as liked."""
        pattern = self.session.get("current_pattern")
        if not pattern:
            self.log_message("[yellow]No pattern playing to rate[/]")
            return
        self.awaiting_feedback = "like"
        input_widget = self.query_one(Input)
        input_widget.placeholder = f"Why do you like '{pattern}'? (Enter to save, Esc to cancel)"
        input_widget.focus()
        self.log_message(f"[green]👍 Rating '{pattern}' - enter your reason below[/]")

    def action_dislike_pattern(self) -> None:
        """Mark current pattern as disliked."""
        pattern = self.session.get("current_pattern")
        if not pattern:
            self.log_message("[yellow]No pattern playing to rate[/]")
            return
        self.awaiting_feedback = "dislike"
        input_widget = self.query_one(Input)
        input_widget.placeholder = f"Why don't you like '{pattern}'? (Enter to save, Esc to cancel)"
        input_widget.focus()
        self.log_message(f"[red]👎 Rating '{pattern}' - enter your reason below[/]")

    def on_key(self, event) -> None:
        """Handle key events for canceling feedback."""
        if self.awaiting_feedback and event.key == "escape":
            self.awaiting_feedback = None
            input_widget = self.query_one(Input)
            input_widget.placeholder = "Message to conductor (Enter=queue, Ctrl+Enter=immediate)"
            input_widget.value = ""
            self.log_message("[dim]Feedback cancelled[/]")
            event.prevent_default()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key on input - queue message or save feedback."""
        value = event.value.strip()

        # Check if we're awaiting feedback
        if self.awaiting_feedback:
            pattern = self.session.get("current_pattern")
            feedback_type = self.awaiting_feedback
            self.awaiting_feedback = None

            # Reset input placeholder
            input_widget = self.query_one(Input)
            input_widget.placeholder = "Message to conductor (Enter=queue, Ctrl+Enter=immediate)"
            event.input.value = ""

            if pattern:
                # Save the feedback
                add_preference_feedback(pattern, feedback_type, value or "No reason given")
                self.preferences = load_music_preferences()  # Reload

                emoji = "👍" if feedback_type == "like" else "👎"
                color = "green" if feedback_type == "like" else "red"
                self.log_message(f"[{color}]{emoji} Saved: {feedback_type} '{pattern}'[/]")
                if value:
                    self.log_message(f"[dim]Reason: {value}[/]")

                # In training mode, auto-advance to next pattern after dislike
                if self.no_eeg_mode and feedback_type == "dislike":
                    self.log_message("[dim]Auto-advancing to next pattern...[/]")
                    self.pending_message = "play something different"
                    self.last_change_time = 0
            return

        # Normal message handling
        if value:
            self.pending_message = value
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
    import argparse
    import atexit

    parser = argparse.ArgumentParser(description="Neural Music Conductor TUI")
    parser.add_argument("--fresh", action="store_true",
                        help="Start fresh (clear session state)")
    parser.add_argument("--no-eeg", action="store_true",
                        help="Training mode: run without EEG, give feedback on patterns")
    args = parser.parse_args()

    if args.fresh and SESSION_FILE.exists():
        SESSION_FILE.unlink()
        print("Session cleared, starting fresh...")

    atexit.register(reset_terminal)

    try:
        app = ConductorApp(no_eeg_mode=args.no_eeg)
        app.run()
    finally:
        reset_terminal()


if __name__ == "__main__":
    main()
