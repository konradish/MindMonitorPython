#!/usr/bin/env python3
"""
EEG Consciousness MCP Server

Exposes real-time EEG consciousness state to Claude via Model Context Protocol.
Queries TimescaleDB for current and historical brain state data.

Usage:
    # Direct run (stdio transport for Claude Desktop)
    uv run python scripts/eeg_mcp_server.py

    # Test the tools
    DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" \
        uv run python scripts/eeg_mcp_server.py --test
"""

import os
import sys
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

# Chicago timezone for display
CHICAGO_TZ = ZoneInfo("America/Chicago")


def to_chicago(ts) -> str:
    """Convert a timestamp to Chicago time ISO format."""
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(CHICAGO_TZ).isoformat()


# MCP imports
from mcp.server.fastmcp import FastMCP

# Database
import psycopg2
from psycopg2.extras import RealDictCursor

# Initialize MCP server
mcp = FastMCP("eeg-consciousness")

# Database connection
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://eeg:eegpass@localhost:5590/eeg'
)


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


def interpret_state(state: str, alpha: float, beta: float, delta: float, theta: float) -> dict:
    """Provide interpretation of the EEG state for Claude."""
    interpretations = {
        "DROWSY": "User is very relaxed or tired. Keep responses concise and check understanding.",
        "FOCUSED": "User is actively concentrating. Good time for detailed technical information.",
        "RELAXED": "User is calm and receptive. Good for creative discussions or learning.",
        "MEDITATIVE": "User is in a calm, introspective state. Speak gently, avoid interrupting flow.",
        "ALERT_TENSE": "User may be stressed or anxious. Be supportive and keep things simple.",
        "CREATIVE_FLOW": "User is in a creative state. Encourage exploration and ideas.",
        "PEAK_FOCUS": "User is deeply concentrated. Minimize distractions, be precise.",
        "JHANA": "User is in deep meditative absorption. Minimize interruption.",
        "SECURITY_GUARD": "User's nervous system detected a threat pattern. Be calming.",
        "RECOVERY": "User is recovering from an alert state. Give space.",
        "MIXED": "User in transitional state - no dominant pattern. Brain activity present but ambiguous.",
        "ERROR": "EEG signal error - possible movement or poor electrode contact.",
    }

    # Cognitive load estimation
    if beta > 35:
        cognitive_load = "high"
    elif beta > 20:
        cognitive_load = "moderate"
    else:
        cognitive_load = "low"

    # Relaxation level
    if alpha > 30:
        relaxation = "high"
    elif alpha > 15:
        relaxation = "moderate"
    else:
        relaxation = "low"

    return {
        "interpretation": interpretations.get(state, "Unknown state"),
        "cognitive_load": cognitive_load,
        "relaxation_level": relaxation,
        "recommendations": get_recommendations(state, cognitive_load)
    }


def get_recommendations(state: str, cognitive_load: str) -> list:
    """Get communication recommendations based on state."""
    recs = []

    if state == "DROWSY":
        recs.append("Keep responses short and clear")
        recs.append("Ask if user needs a break")
    elif state in ("FOCUSED", "PEAK_FOCUS"):
        recs.append("Can provide detailed technical information")
        recs.append("User is ready for complex topics")
    elif state == "RELAXED":
        recs.append("Good time for brainstorming")
        recs.append("User is receptive to new ideas")
    elif state == "ALERT_TENSE":
        recs.append("Be supportive and calming")
        recs.append("Avoid adding pressure")
    elif state == "SECURITY_GUARD":
        recs.append("User's nervous system detected something alarming")
        recs.append("Be gentle and grounding")

    if cognitive_load == "high":
        recs.append("Break complex info into smaller chunks")

    return recs


@mcp.tool()
def get_current_eeg_state() -> dict:
    """
    Get the user's current EEG consciousness state and brain wave patterns.

    Returns the detected mental state (FOCUSED, RELAXED, DROWSY, etc.),
    relative band powers (alpha, beta, delta, theta, gamma as percentages),
    and interpretation/recommendations for how to interact.

    Use this to understand the user's current cognitive/emotional state
    and adapt your responses accordingly.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get most recent window
        cur.execute("""
            SELECT
                ts_start,
                features->>'state' as state,
                alpha_rel,
                beta_rel,
                delta_rel,
                theta_rel,
                gamma_rel
            FROM eeg_window
            ORDER BY ts_start DESC
            LIMIT 1
        """)

        row = cur.fetchone()
        conn.close()

        if not row:
            return {
                "status": "no_data",
                "message": "No EEG data available. User may not be wearing headband."
            }

        # Check data freshness
        ts = row['ts_start']
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()

        state = row['state'] or "UNKNOWN"
        alpha = float(row['alpha_rel'] or 0)
        beta = float(row['beta_rel'] or 0)
        delta = float(row['delta_rel'] or 0)
        theta = float(row['theta_rel'] or 0)
        gamma = float(row['gamma_rel'] or 0)

        interpretation = interpret_state(state, alpha, beta, delta, theta)

        return {
            "status": "ok",
            "timestamp": to_chicago(ts),
            "data_age_seconds": round(age_seconds, 1),
            "is_fresh": age_seconds < 10,  # Data from last 10 seconds
            "state": state,
            "band_powers": {
                "alpha": round(alpha, 1),
                "beta": round(beta, 1),
                "delta": round(delta, 1),
                "theta": round(theta, 1),
                "gamma": round(gamma, 1)
            },
            "interpretation": interpretation["interpretation"],
            "cognitive_load": interpretation["cognitive_load"],
            "relaxation_level": interpretation["relaxation_level"],
            "recommendations": interpretation["recommendations"]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get EEG state: {str(e)}"
        }


@mcp.tool()
def get_eeg_history(minutes: int = 5) -> dict:
    """
    Get the user's EEG state history over the specified time period.

    Args:
        minutes: How many minutes of history to retrieve (default: 5, max: 60)

    Returns state transitions, average band powers, and trends.
    Use this to understand how the user's mental state has been changing.
    """
    minutes = min(max(1, minutes), 60)  # Clamp to 1-60

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get state distribution
        cur.execute("""
            SELECT
                features->>'state' as state,
                COUNT(*) as count,
                AVG(alpha_rel) as avg_alpha,
                AVG(beta_rel) as avg_beta,
                AVG(delta_rel) as avg_delta
            FROM eeg_window
            WHERE ts_start > NOW() - INTERVAL '%s minutes'
            GROUP BY features->>'state'
            ORDER BY count DESC
        """, (minutes,))

        state_dist = cur.fetchall()

        # Get recent transitions
        cur.execute("""
            SELECT
                ts_start,
                features->>'state' as state
            FROM eeg_window
            WHERE ts_start > NOW() - INTERVAL '%s minutes'
            ORDER BY ts_start DESC
            LIMIT 30
        """, (minutes,))

        recent = cur.fetchall()
        conn.close()

        if not state_dist:
            return {
                "status": "no_data",
                "message": f"No EEG data in the last {minutes} minutes"
            }

        # Calculate dominant state
        total_windows = sum(s['count'] for s in state_dist)
        dominant_state = state_dist[0]['state'] if state_dist else "UNKNOWN"
        dominant_pct = round(state_dist[0]['count'] / total_windows * 100, 1) if state_dist else 0

        # State breakdown
        state_breakdown = {
            s['state']: {
                "percentage": round(s['count'] / total_windows * 100, 1),
                "avg_alpha": round(float(s['avg_alpha'] or 0), 1),
                "avg_beta": round(float(s['avg_beta'] or 0), 1),
                "avg_delta": round(float(s['avg_delta'] or 0), 1)
            }
            for s in state_dist
        }

        # Detect state changes
        state_changes = []
        prev_state = None
        for r in reversed(recent):
            if r['state'] != prev_state and prev_state is not None:
                state_changes.append({
                    "time": to_chicago(r['ts_start']),
                    "from": prev_state,
                    "to": r['state']
                })
            prev_state = r['state']

        return {
            "status": "ok",
            "period_minutes": minutes,
            "total_windows": total_windows,
            "dominant_state": dominant_state,
            "dominant_state_percentage": dominant_pct,
            "state_breakdown": state_breakdown,
            "recent_state_changes": state_changes[-5:],  # Last 5 transitions
            "summary": f"User has been primarily {dominant_state} ({dominant_pct}%) over the last {minutes} minutes with {len(state_changes)} state transitions."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get EEG history: {str(e)}"
        }


def _compute_band_stats(rows: list) -> dict:
    """Compute statistics for each band from a list of rows."""
    import statistics

    bands = ['alpha', 'beta', 'delta', 'theta', 'gamma']
    stats = {}

    for band in bands:
        key = f'{band}_rel'
        values = [float(r[key] or 0) for r in rows]
        if values:
            stats[band] = {
                "mean": round(statistics.mean(values), 1),
                "std": round(statistics.stdev(values), 1) if len(values) > 1 else 0,
                "min": round(min(values), 1),
                "max": round(max(values), 1)
            }
        else:
            stats[band] = {"mean": 0, "std": 0, "min": 0, "max": 0}

    return stats


def _find_longest_state(rows: list) -> dict:
    """Find the longest continuous state period."""
    if not rows:
        return None

    longest = {"state": None, "duration_sec": 0}
    current_state = rows[0]['state']
    current_start = rows[0]['ts_start']

    for row in rows[1:]:
        if row['state'] != current_state:
            duration = (row['ts_start'] - current_start).total_seconds()
            if duration > longest['duration_sec']:
                longest = {"state": current_state, "duration_sec": round(duration, 1)}
            current_state = row['state']
            current_start = row['ts_start']

    # Check final segment
    if rows:
        duration = (rows[-1]['ts_start'] - current_start).total_seconds()
        if duration > longest['duration_sec']:
            longest = {"state": current_state, "duration_sec": round(duration, 1)}

    return longest if longest['state'] else None


@mcp.tool()
def get_band_timeseries(minutes: int = 5, detail: str = "summary") -> dict:
    """
    Get band power data over time with configurable detail level.

    Args:
        minutes: How many minutes of data to retrieve (default: 5, max: 60)
        detail: Level of detail - "summary" (default), "csv", or "json"
            - summary: Statistics per band, state distribution, longest state
            - csv: Raw data as compact CSV string (timestamp,alpha,beta,delta,theta,gamma,state)
            - json: Full JSON array of all readings (highest token usage)

    Returns summary statistics by default. Use csv/json only when you need
    to see the exact shape of transitions over time.
    """
    minutes = min(max(1, minutes), 60)
    detail = detail.lower() if detail else "summary"
    if detail not in ("summary", "csv", "json"):
        detail = "summary"

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                ts_start,
                alpha_rel,
                beta_rel,
                delta_rel,
                theta_rel,
                gamma_rel,
                features->>'state' as state
            FROM eeg_window
            WHERE ts_start > NOW() - INTERVAL '%s minutes'
            ORDER BY ts_start ASC
        """, (minutes,))

        rows = cur.fetchall()
        conn.close()

        if not rows:
            return {
                "status": "no_data",
                "message": f"No EEG data in the last {minutes} minutes"
            }

        # Count state distribution
        state_counts = {}
        for r in rows:
            state = r['state'] or 'UNKNOWN'
            state_counts[state] = state_counts.get(state, 0) + 1
        total = len(rows)
        state_distribution = {
            s: round(c / total, 2) for s, c in
            sorted(state_counts.items(), key=lambda x: -x[1])
        }

        # Count transitions
        transitions = sum(1 for i in range(1, len(rows)) if rows[i]['state'] != rows[i-1]['state'])

        base_response = {
            "status": "ok",
            "period": {
                "start": to_chicago(rows[0]['ts_start']),
                "end": to_chicago(rows[-1]['ts_start']),
                "duration_sec": round((rows[-1]['ts_start'] - rows[0]['ts_start']).total_seconds(), 1)
            },
            "readings_count": len(rows),
            "transitions": transitions,
            "state_distribution": state_distribution,
        }

        if detail == "summary":
            # Compute statistics - most compact and useful
            band_stats = _compute_band_stats(rows)
            longest_state = _find_longest_state(rows)

            return {
                **base_response,
                "band_stats": band_stats,
                "longest_state": longest_state
            }

        elif detail == "csv":
            # CSV format - ~40-50% fewer tokens than JSON
            lines = ["timestamp,alpha,beta,delta,theta,gamma,state"]
            for r in rows:
                lines.append(
                    f"{to_chicago(r['ts_start'])},"
                    f"{round(float(r['alpha_rel'] or 0), 1)},"
                    f"{round(float(r['beta_rel'] or 0), 1)},"
                    f"{round(float(r['delta_rel'] or 0), 1)},"
                    f"{round(float(r['theta_rel'] or 0), 1)},"
                    f"{round(float(r['gamma_rel'] or 0), 1)},"
                    f"{r['state'] or 'UNKNOWN'}"
                )
            return {
                **base_response,
                "format": "csv",
                "data": "\n".join(lines)
            }

        else:  # json
            # Full JSON - most tokens but most parseable
            timeseries = [
                {
                    "timestamp": to_chicago(r['ts_start']),
                    "alpha": round(float(r['alpha_rel'] or 0), 1),
                    "beta": round(float(r['beta_rel'] or 0), 1),
                    "delta": round(float(r['delta_rel'] or 0), 1),
                    "theta": round(float(r['theta_rel'] or 0), 1),
                    "gamma": round(float(r['gamma_rel'] or 0), 1),
                    "state": r['state']
                }
                for r in rows
            ]
            return {
                **base_response,
                "format": "json",
                "timeseries": timeseries
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get band timeseries: {str(e)}"
        }


@mcp.tool()
def get_transition_analysis(minutes: int = 30) -> dict:
    """
    Analyze state transition patterns and velocity.

    Args:
        minutes: How many minutes to analyze (default: 30, max: 120)

    Returns metrics about state stability, rapid oscillations,
    longest stable periods, and transition pair frequencies.
    """
    minutes = min(max(1, minutes), 120)

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                ts_start,
                features->>'state' as state
            FROM eeg_window
            WHERE ts_start > NOW() - INTERVAL '%s minutes'
            ORDER BY ts_start ASC
        """, (minutes,))

        rows = cur.fetchall()
        conn.close()

        if len(rows) < 2:
            return {
                "status": "no_data",
                "message": f"Not enough data in the last {minutes} minutes"
            }

        # Analyze transitions
        transitions = []
        state_durations = []
        current_state = rows[0]['state']
        state_start = rows[0]['ts_start']

        for i, row in enumerate(rows[1:], 1):
            if row['state'] != current_state:
                duration = (row['ts_start'] - state_start).total_seconds()
                state_durations.append({
                    'state': current_state,
                    'duration_seconds': duration
                })
                transitions.append({
                    'timestamp': to_chicago(row['ts_start']),
                    'from': current_state,
                    'to': row['state'],
                    'prev_duration_seconds': duration
                })
                current_state = row['state']
                state_start = row['ts_start']

        # Add final state duration
        if rows:
            final_duration = (rows[-1]['ts_start'] - state_start).total_seconds()
            state_durations.append({
                'state': current_state,
                'duration_seconds': final_duration
            })

        # Calculate metrics
        avg_duration = sum(d['duration_seconds'] for d in state_durations) / len(state_durations) if state_durations else 0

        # Rapid oscillations (state changes < 5 sec apart)
        rapid_oscillations = sum(1 for t in transitions if t['prev_duration_seconds'] < 5)

        # Longest stable period
        longest_stable = max(state_durations, key=lambda x: x['duration_seconds']) if state_durations else None

        # Transition pair frequencies
        transition_pairs = {}
        for t in transitions:
            pair = f"{t['from']} -> {t['to']}"
            transition_pairs[pair] = transition_pairs.get(pair, 0) + 1

        # Sort by frequency
        sorted_pairs = dict(sorted(transition_pairs.items(), key=lambda x: x[1], reverse=True))

        return {
            "status": "ok",
            "period_minutes": minutes,
            "total_windows": len(rows),
            "total_transitions": len(transitions),
            "avg_state_duration_seconds": round(avg_duration, 1),
            "rapid_oscillations": rapid_oscillations,
            "longest_stable_period": {
                "state": longest_stable['state'],
                "duration_seconds": round(longest_stable['duration_seconds'], 1)
            } if longest_stable else None,
            "transition_pairs": sorted_pairs,
            "recent_transitions": transitions[-10:]  # Last 10
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get transition analysis: {str(e)}"
        }


@mcp.tool()
def query_band_events(
    band: str,
    operator: str,
    value: float,
    minutes: int = 60
) -> dict:
    """
    Find timestamps where a specific band power meets a threshold.

    Args:
        band: Which band to query ("alpha", "beta", "gamma", "delta", "theta")
        operator: Comparison operator ("gt", "lt", "gte", "lte")
        value: Threshold value (percentage, 0-100)
        minutes: How many minutes to search (default: 60, max: 180)

    Returns timestamps and contexts where the condition was met.
    Use this to find flow states, activation moments, relaxation peaks, etc.
    """
    valid_bands = ['alpha', 'beta', 'gamma', 'delta', 'theta']
    if band not in valid_bands:
        return {"status": "error", "message": f"Invalid band. Must be one of: {valid_bands}"}

    valid_ops = {'gt': '>', 'lt': '<', 'gte': '>=', 'lte': '<='}
    if operator not in valid_ops:
        return {"status": "error", "message": f"Invalid operator. Must be one of: {list(valid_ops.keys())}"}

    minutes = min(max(1, minutes), 180)

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        column = f"{band}_rel"
        op_sql = valid_ops[operator]

        cur.execute(f"""
            SELECT
                ts_start,
                alpha_rel, beta_rel, delta_rel, theta_rel, gamma_rel,
                features->>'state' as state
            FROM eeg_window
            WHERE ts_start > NOW() - INTERVAL '%s minutes'
              AND {column} {op_sql} %s
            ORDER BY ts_start DESC
            LIMIT 100
        """, (minutes, value))

        rows = cur.fetchall()
        conn.close()

        events = [
            {
                "timestamp": to_chicago(r['ts_start']),
                "state": r['state'],
                "band_value": round(float(r[column] or 0), 1),
                "all_bands": {
                    "alpha": round(float(r['alpha_rel'] or 0), 1),
                    "beta": round(float(r['beta_rel'] or 0), 1),
                    "delta": round(float(r['delta_rel'] or 0), 1),
                    "theta": round(float(r['theta_rel'] or 0), 1),
                    "gamma": round(float(r['gamma_rel'] or 0), 1)
                }
            }
            for r in rows
        ]

        return {
            "status": "ok",
            "query": f"{band} {operator} {value}",
            "period_minutes": minutes,
            "matches_found": len(events),
            "events": events
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to query band events: {str(e)}"
        }


@mcp.tool()
def add_annotation(note: str, label: str = "observation") -> dict:
    """
    Add a subjective annotation to correlate with EEG data.

    Args:
        note: The annotation text (e.g., "Feeling anxious", "Started meditation")
        label: Category label for the annotation (default: "observation")

    Use this to mark subjective experiences that can be correlated with EEG patterns later.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get current session ID from most recent window
        cur.execute("""
            SELECT session_id, ts_start
            FROM eeg_window
            ORDER BY ts_start DESC
            LIMIT 1
        """)

        row = cur.fetchone()
        if not row:
            conn.close()
            return {
                "status": "error",
                "message": "No active EEG session found"
            }

        session_id = row['session_id']
        now = datetime.now(timezone.utc)

        # Create a point-in-time span (cast to timestamp for tsrange)
        cur.execute("""
            INSERT INTO annotation (session_id, span, label, author, notes)
            VALUES (%s, tsrange(%s::timestamp, %s::timestamp), %s, 'claude_mcp', %s)
            RETURNING created_at
        """, (session_id, now, now, label, note))

        result = cur.fetchone()
        conn.commit()
        conn.close()

        return {
            "status": "ok",
            "message": "Annotation saved",
            "timestamp": to_chicago(now),
            "label": label,
            "note": note,
            "session_id": str(session_id)
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to add annotation: {str(e)}"
        }


@mcp.tool()
def get_annotations(minutes: int = 60) -> dict:
    """
    Get annotations with surrounding EEG context.

    Args:
        minutes: How many minutes of annotations to retrieve (default: 60)

    Returns annotations with the EEG state at the time of annotation.
    """
    minutes = min(max(1, minutes), 1440)  # Max 24 hours

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                a.created_at,
                a.label,
                a.notes,
                a.author,
                e.features->>'state' as eeg_state,
                e.alpha_rel, e.beta_rel, e.delta_rel, e.theta_rel, e.gamma_rel
            FROM annotation a
            LEFT JOIN LATERAL (
                SELECT * FROM eeg_window w
                WHERE w.session_id = a.session_id
                  AND w.ts_start <= a.created_at
                ORDER BY w.ts_start DESC
                LIMIT 1
            ) e ON true
            WHERE a.created_at > NOW() - INTERVAL '%s minutes'
            ORDER BY a.created_at DESC
            LIMIT 50
        """, (minutes,))

        rows = cur.fetchall()
        conn.close()

        annotations = [
            {
                "timestamp": to_chicago(r['created_at']),
                "label": r['label'],
                "note": r['notes'],
                "author": r['author'],
                "eeg_context": {
                    "state": r['eeg_state'],
                    "alpha": round(float(r['alpha_rel'] or 0), 1) if r['alpha_rel'] else None,
                    "beta": round(float(r['beta_rel'] or 0), 1) if r['beta_rel'] else None,
                    "delta": round(float(r['delta_rel'] or 0), 1) if r['delta_rel'] else None,
                    "theta": round(float(r['theta_rel'] or 0), 1) if r['theta_rel'] else None,
                    "gamma": round(float(r['gamma_rel'] or 0), 1) if r['gamma_rel'] else None
                } if r['eeg_state'] else None
            }
            for r in rows
        ]

        return {
            "status": "ok",
            "period_minutes": minutes,
            "count": len(annotations),
            "annotations": annotations
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get annotations: {str(e)}"
        }


@mcp.tool()
def save_baseline(name: str, minutes_to_average: int = 5, notes: str = "") -> dict:
    """
    Save current EEG average as a named baseline for future comparison.

    Args:
        name: Name for this baseline (e.g., "morning_regulated", "flow_state", "anxious")
        minutes_to_average: How many minutes of recent data to average (default: 5)
        notes: Optional description of this baseline state

    Use this to capture personal reference points for different mental states.
    """
    minutes_to_average = min(max(1, minutes_to_average), 30)

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Calculate averages
        cur.execute("""
            SELECT
                AVG(alpha_rel) as alpha,
                AVG(beta_rel) as beta,
                AVG(delta_rel) as delta,
                AVG(theta_rel) as theta,
                AVG(gamma_rel) as gamma,
                COUNT(*) as samples
            FROM eeg_window
            WHERE ts_start > NOW() - INTERVAL '%s minutes'
        """, (minutes_to_average,))

        row = cur.fetchone()

        if not row or row['samples'] == 0:
            conn.close()
            return {
                "status": "error",
                "message": f"No EEG data in the last {minutes_to_average} minutes"
            }

        # Ensure baseline table exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS eeg_baseline (
                name TEXT PRIMARY KEY,
                alpha_rel REAL NOT NULL,
                beta_rel REAL NOT NULL,
                theta_rel REAL NOT NULL,
                delta_rel REAL NOT NULL,
                gamma_rel REAL NOT NULL,
                samples INT NOT NULL,
                notes TEXT,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """)

        # Upsert baseline
        cur.execute("""
            INSERT INTO eeg_baseline (name, alpha_rel, beta_rel, theta_rel, delta_rel, gamma_rel, samples, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                alpha_rel = EXCLUDED.alpha_rel,
                beta_rel = EXCLUDED.beta_rel,
                theta_rel = EXCLUDED.theta_rel,
                delta_rel = EXCLUDED.delta_rel,
                gamma_rel = EXCLUDED.gamma_rel,
                samples = EXCLUDED.samples,
                notes = EXCLUDED.notes,
                updated_at = now()
            RETURNING created_at, updated_at
        """, (
            name,
            float(row['alpha']),
            float(row['beta']),
            float(row['theta']),
            float(row['delta']),
            float(row['gamma']),
            int(row['samples']),
            notes or None
        ))

        result = cur.fetchone()
        conn.commit()
        conn.close()

        baseline = {
            "alpha": round(float(row['alpha']), 1),
            "beta": round(float(row['beta']), 1),
            "delta": round(float(row['delta']), 1),
            "theta": round(float(row['theta']), 1),
            "gamma": round(float(row['gamma']), 1)
        }

        return {
            "status": "ok",
            "message": f"Baseline '{name}' saved",
            "name": name,
            "samples_averaged": int(row['samples']),
            "minutes_averaged": minutes_to_average,
            "baseline": baseline,
            "notes": notes or None
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to save baseline: {str(e)}"
        }


@mcp.tool()
def compare_to_baseline(baseline_name: str = "default") -> dict:
    """
    Compare current EEG state to a stored personal baseline.

    Args:
        baseline_name: Name of the baseline to compare against (default: "default")

    Returns current state, baseline values, deviation, and interpretation.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get baseline
        cur.execute("""
            SELECT * FROM eeg_baseline WHERE name = %s
        """, (baseline_name,))

        baseline_row = cur.fetchone()

        if not baseline_row:
            # List available baselines
            cur.execute("SELECT name FROM eeg_baseline ORDER BY name")
            available = [r['name'] for r in cur.fetchall()]
            conn.close()
            return {
                "status": "error",
                "message": f"Baseline '{baseline_name}' not found",
                "available_baselines": available
            }

        # Get current averages (last 2 minutes)
        cur.execute("""
            SELECT
                AVG(alpha_rel) as alpha,
                AVG(beta_rel) as beta,
                AVG(delta_rel) as delta,
                AVG(theta_rel) as theta,
                AVG(gamma_rel) as gamma,
                COUNT(*) as samples
            FROM eeg_window
            WHERE ts_start > NOW() - INTERVAL '2 minutes'
        """)

        current_row = cur.fetchone()
        conn.close()

        if not current_row or current_row['samples'] == 0:
            return {
                "status": "error",
                "message": "No recent EEG data for comparison"
            }

        # Calculate deviations
        current = {
            "alpha": round(float(current_row['alpha']), 1),
            "beta": round(float(current_row['beta']), 1),
            "delta": round(float(current_row['delta']), 1),
            "theta": round(float(current_row['theta']), 1),
            "gamma": round(float(current_row['gamma']), 1)
        }

        baseline = {
            "alpha": round(float(baseline_row['alpha_rel']), 1),
            "beta": round(float(baseline_row['beta_rel']), 1),
            "delta": round(float(baseline_row['delta_rel']), 1),
            "theta": round(float(baseline_row['theta_rel']), 1),
            "gamma": round(float(baseline_row['gamma_rel']), 1)
        }

        deviation = {
            band: round(current[band] - baseline[band], 1)
            for band in ['alpha', 'beta', 'delta', 'theta', 'gamma']
        }

        # Generate interpretation
        interpretations = []
        if deviation['beta'] > 10:
            interpretations.append("Significantly elevated beta - more cognitive load/stress than baseline")
        elif deviation['beta'] < -10:
            interpretations.append("Lower beta than baseline - more relaxed cognitively")

        if deviation['alpha'] > 10:
            interpretations.append("Elevated alpha - more relaxed/calm than baseline")
        elif deviation['alpha'] < -10:
            interpretations.append("Lower alpha than baseline - less relaxed, possibly more engaged or tense")

        if deviation['delta'] > 10:
            interpretations.append("Elevated delta - more drowsy than baseline")
        elif deviation['delta'] < -10:
            interpretations.append("Lower delta than baseline - more alert")

        if deviation['gamma'] > 10:
            interpretations.append("Elevated gamma - heightened cognitive binding/processing")

        if not interpretations:
            interpretations.append("Current state is similar to your baseline")

        return {
            "status": "ok",
            "baseline_name": baseline_name,
            "baseline_notes": baseline_row['notes'],
            "current_state": current,
            "baseline": baseline,
            "deviation": deviation,
            "interpretation": interpretations
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to compare to baseline: {str(e)}"
        }


@mcp.tool()
def list_baselines() -> dict:
    """
    List all saved EEG baselines.

    Returns names, creation dates, and brief summaries of all stored baselines.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT name, alpha_rel, beta_rel, delta_rel, theta_rel, gamma_rel,
                   samples, notes, created_at, updated_at
            FROM eeg_baseline
            ORDER BY updated_at DESC
        """)

        rows = cur.fetchall()
        conn.close()

        baselines = [
            {
                "name": r['name'],
                "bands": {
                    "alpha": round(float(r['alpha_rel']), 1),
                    "beta": round(float(r['beta_rel']), 1),
                    "delta": round(float(r['delta_rel']), 1),
                    "theta": round(float(r['theta_rel']), 1),
                    "gamma": round(float(r['gamma_rel']), 1)
                },
                "samples": r['samples'],
                "notes": r['notes'],
                "created_at": to_chicago(r['created_at']),
                "updated_at": to_chicago(r['updated_at'])
            }
            for r in rows
        ]

        return {
            "status": "ok",
            "count": len(baselines),
            "baselines": baselines
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to list baselines: {str(e)}"
        }


@mcp.tool()
def get_session_summary() -> dict:
    """
    Get a summary of all EEG recording sessions in the database.

    Returns information about available sessions, total windows recorded,
    and time ranges. Useful for understanding the user's EEG history.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                session_id,
                COUNT(*) as windows,
                MIN(ts_start) as first_window,
                MAX(ts_start) as last_window,
                EXTRACT(EPOCH FROM (MAX(ts_start) - MIN(ts_start))) / 60 as duration_minutes
            FROM eeg_window
            GROUP BY session_id
            ORDER BY MAX(ts_start) DESC
            LIMIT 10
        """)

        sessions = cur.fetchall()
        conn.close()

        return {
            "status": "ok",
            "total_sessions": len(sessions),
            "sessions": [
                {
                    "session_id": str(s['session_id']),
                    "windows": s['windows'],
                    "duration_minutes": round(float(s['duration_minutes'] or 0), 1),
                    "first_window": to_chicago(s['first_window']) if s['first_window'] else None,
                    "last_window": to_chicago(s['last_window']) if s['last_window'] else None
                }
                for s in sessions
            ]
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get session summary: {str(e)}"
        }


def test_tools():
    """Test the MCP tools locally."""
    print("Testing EEG MCP Server Tools\n")
    print("=" * 50)

    print("\n1. get_current_eeg_state():")
    result = get_current_eeg_state()
    print(json.dumps(result, indent=2, default=str))

    print("\n2. get_eeg_history(minutes=5):")
    result = get_eeg_history(5)
    print(json.dumps(result, indent=2, default=str))

    print("\n3. get_session_summary():")
    result = get_session_summary()
    print(json.dumps(result, indent=2, default=str))

    print("\n4. get_band_timeseries(minutes=2) - summary (default):")
    result = get_band_timeseries(2)
    print(json.dumps(result, indent=2, default=str))

    print("\n4b. get_band_timeseries(minutes=2, detail='csv'):")
    result = get_band_timeseries(2, detail='csv')
    # Truncate CSV for display
    if result.get('data'):
        lines = result['data'].split('\n')
        if len(lines) > 6:
            result['data'] = '\n'.join(lines[:6]) + f'\n... ({len(lines)-6} more rows)'
    print(json.dumps(result, indent=2, default=str))

    print("\n5. get_transition_analysis(minutes=10):")
    result = get_transition_analysis(10)
    print(json.dumps(result, indent=2, default=str))

    print("\n6. query_band_events(band='alpha', operator='gt', value=30, minutes=10):")
    result = query_band_events('alpha', 'gt', 30, 10)
    if result.get('events'):
        result['events'] = result['events'][:3] + ['...truncated...'] if len(result['events']) > 3 else result['events']
    print(json.dumps(result, indent=2, default=str))

    print("\n7. list_baselines():")
    result = list_baselines()
    print(json.dumps(result, indent=2, default=str))

    print("\n8. get_annotations(minutes=60):")
    result = get_annotations(60)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_tools()
    else:
        # Run as MCP server (stdio transport for Claude Desktop)
        mcp.run()
