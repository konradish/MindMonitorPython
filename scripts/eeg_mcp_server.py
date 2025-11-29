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
        "NO_SIGNAL": "EEG signal unclear - possible movement or poor electrode contact.",
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
            "timestamp": ts.isoformat(),
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
                    "time": r['ts_start'].isoformat(),
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
                    "first_window": s['first_window'].isoformat() if s['first_window'] else None,
                    "last_window": s['last_window'].isoformat() if s['last_window'] else None
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


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_tools()
    else:
        # Run as MCP server (stdio transport for Claude Desktop)
        mcp.run()
