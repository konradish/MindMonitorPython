"""Database utilities for the admin panel."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st

# Chicago timezone for display
CHICAGO_TZ = ZoneInfo("America/Chicago")

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://eeg:eegpass@localhost:5590/eeg'
)


@contextmanager
def get_connection():
    """Get database connection as context manager."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        conn.close()


def to_chicago(ts) -> Optional[str]:
    """Convert a timestamp to Chicago time ISO format."""
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(CHICAGO_TZ).strftime("%Y-%m-%d %H:%M:%S")


def get_sessions(limit: int = 50) -> list:
    """Get recent sessions."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT
                s.id,
                s.subject,
                s.started_at,
                s.device,
                s.sample_rate,
                s.notes,
                COUNT(w.ts_start) as window_count,
                MIN(w.ts_start) as first_window,
                MAX(w.ts_start) as last_window
            FROM session s
            LEFT JOIN eeg_window w ON s.id = w.session_id
            GROUP BY s.id
            ORDER BY s.started_at DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()


def get_session_by_id(session_id: str) -> Optional[dict]:
    """Get a single session by ID."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM session WHERE id = %s
        """, (session_id,))
        return cur.fetchone()


def get_eeg_windows(session_id: str = None, minutes: int = 60, limit: int = 3600) -> list:
    """Get EEG windows, optionally filtered by session."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if session_id:
            cur.execute("""
                SELECT
                    session_id,
                    ts_start,
                    ts_end,
                    alpha_rel,
                    beta_rel,
                    theta_rel,
                    delta_rel,
                    gamma_rel,
                    entropy,
                    features
                FROM eeg_window
                WHERE session_id = %s
                ORDER BY ts_start DESC
                LIMIT %s
            """, (session_id, limit))
        else:
            cur.execute("""
                SELECT
                    session_id,
                    ts_start,
                    ts_end,
                    alpha_rel,
                    beta_rel,
                    theta_rel,
                    delta_rel,
                    gamma_rel,
                    entropy,
                    features
                FROM eeg_window
                WHERE ts_start > NOW() - INTERVAL '%s minutes'
                ORDER BY ts_start DESC
                LIMIT %s
            """, (minutes, limit))

        return cur.fetchall()


def get_current_state(window_seconds: int = 10) -> Optional[dict]:
    """Get current EEG state with rolling average."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT
                MAX(ts_start) as ts_start,
                AVG(alpha_rel) as alpha_rel,
                AVG(beta_rel) as beta_rel,
                AVG(theta_rel) as theta_rel,
                AVG(delta_rel) as delta_rel,
                AVG(gamma_rel) as gamma_rel,
                COUNT(*) as sample_count
            FROM eeg_window
            WHERE ts_start > NOW() - INTERVAL '%s seconds'
        """, (window_seconds,))
        result = cur.fetchone()

        if result and result['ts_start']:
            # Get latest state from features
            cur.execute("""
                SELECT features->>'state' as state
                FROM eeg_window
                ORDER BY ts_start DESC
                LIMIT 1
            """)
            state_row = cur.fetchone()
            result['state'] = state_row['state'] if state_row else 'UNKNOWN'
            return result
        return None


def get_annotations(session_id: str = None, minutes: int = None, limit: int = 100) -> list:
    """Get annotations, optionally filtered."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT
                a.session_id,
                a.span,
                a.label,
                a.author,
                a.notes,
                a.created_at,
                lower(a.span) as span_start,
                upper(a.span) as span_end
            FROM annotation a
        """
        conditions = []
        params = []

        if session_id:
            conditions.append("a.session_id = %s")
            params.append(session_id)

        if minutes:
            conditions.append("a.created_at > NOW() - INTERVAL '%s minutes'")
            params.append(minutes)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY a.created_at DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        return cur.fetchall()


def add_annotation(session_id: str, label: str, notes: str, author: str = "admin_panel") -> bool:
    """Add a new annotation at current time."""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            # Create point-in-time annotation
            cur.execute("""
                INSERT INTO annotation (session_id, span, label, author, notes)
                VALUES (%s, tsrange(NOW(), NOW(), '[]'), %s, %s, %s)
            """, (session_id, label, author, notes))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to add annotation: {e}")
            return False


def add_annotation_with_range(session_id: str, label: str, notes: str,
                              start_time: datetime, end_time: datetime,
                              author: str = "admin_panel") -> bool:
    """Add a new annotation with a time range."""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO annotation (session_id, span, label, author, notes)
                VALUES (%s, tsrange(%s, %s, '[]'), %s, %s, %s)
            """, (session_id, start_time, end_time, label, author, notes))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to add annotation: {e}")
            return False


def delete_annotation(session_id: str, span_start: datetime, label: str) -> bool:
    """Delete an annotation."""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("""
                DELETE FROM annotation
                WHERE session_id = %s
                  AND lower(span) = %s
                  AND label = %s
            """, (session_id, span_start, label))
            conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to delete annotation: {e}")
            return False


def get_state_definitions() -> list:
    """Get all state definitions."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT *
            FROM state_definition
            ORDER BY priority DESC, name
        """)
        return cur.fetchall()


def add_state_definition(name: str, conditions: dict, interpretation: str,
                         recommendations: list, emoji: str = "🧠",
                         priority: int = 50, enabled: bool = True,
                         notes: str = None) -> bool:
    """Add a new state definition."""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            import json
            cur.execute("""
                INSERT INTO state_definition
                    (name, priority, conditions, interpretation, recommendations, emoji, enabled, author, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'admin_panel', %s)
            """, (name, priority, json.dumps(conditions), interpretation,
                  recommendations, emoji, enabled, notes))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to add state definition: {e}")
            return False


def update_state_definition(name: str, enabled: bool = None, priority: int = None,
                            conditions: dict = None, interpretation: str = None,
                            recommendations: list = None, emoji: str = None,
                            notes: str = None) -> bool:
    """Update an existing state definition."""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            import json
            updates = []
            params = []

            if enabled is not None:
                updates.append("enabled = %s")
                params.append(enabled)
            if priority is not None:
                updates.append("priority = %s")
                params.append(priority)
            if conditions is not None:
                updates.append("conditions = %s")
                params.append(json.dumps(conditions))
            if interpretation is not None:
                updates.append("interpretation = %s")
                params.append(interpretation)
            if recommendations is not None:
                updates.append("recommendations = %s")
                params.append(recommendations)
            if emoji is not None:
                updates.append("emoji = %s")
                params.append(emoji)
            if notes is not None:
                updates.append("notes = %s")
                params.append(notes)

            if not updates:
                return True

            updates.append("updated_at = NOW()")
            params.append(name)

            cur.execute(f"""
                UPDATE state_definition
                SET {', '.join(updates)}
                WHERE name = %s
            """, params)
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to update state definition: {e}")
            return False


def delete_state_definition(name: str) -> bool:
    """Delete a state definition."""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM state_definition WHERE name = %s", (name,))
            conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to delete state definition: {e}")
            return False


def get_baselines() -> list:
    """Get all baselines."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT *
            FROM eeg_baseline
            ORDER BY name
        """)
        return cur.fetchall()


def save_baseline(name: str, minutes: int = 5, notes: str = None) -> bool:
    """Save current averages as a baseline."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Get averages
            cur.execute("""
                SELECT
                    AVG(alpha_rel) as alpha_rel,
                    AVG(beta_rel) as beta_rel,
                    AVG(theta_rel) as theta_rel,
                    AVG(delta_rel) as delta_rel,
                    AVG(gamma_rel) as gamma_rel,
                    COUNT(*) as samples
                FROM eeg_window
                WHERE ts_start > NOW() - INTERVAL '%s minutes'
            """, (minutes,))
            avgs = cur.fetchone()

            if not avgs or avgs['samples'] == 0:
                st.error("No data available for baseline")
                return False

            # Upsert baseline
            cur.execute("""
                INSERT INTO eeg_baseline
                    (name, alpha_rel, beta_rel, theta_rel, delta_rel, gamma_rel, samples, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    alpha_rel = EXCLUDED.alpha_rel,
                    beta_rel = EXCLUDED.beta_rel,
                    theta_rel = EXCLUDED.theta_rel,
                    delta_rel = EXCLUDED.delta_rel,
                    gamma_rel = EXCLUDED.gamma_rel,
                    samples = EXCLUDED.samples,
                    notes = EXCLUDED.notes,
                    updated_at = NOW()
            """, (name, avgs['alpha_rel'], avgs['beta_rel'], avgs['theta_rel'],
                  avgs['delta_rel'], avgs['gamma_rel'], avgs['samples'], notes))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to save baseline: {e}")
            return False


def delete_baseline(name: str) -> bool:
    """Delete a baseline."""
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM eeg_baseline WHERE name = %s", (name,))
            conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            conn.rollback()
            st.error(f"Failed to delete baseline: {e}")
            return False


def get_detections(session_id: str = None, minutes: int = 60, limit: int = 200) -> list:
    """Get automated detections."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = """
            SELECT
                session_id,
                span,
                label,
                source,
                score,
                extra,
                lower(span) as span_start,
                upper(span) as span_end
            FROM detection
        """
        conditions = []
        params = []

        if session_id:
            conditions.append("session_id = %s")
            params.append(session_id)
        else:
            conditions.append("lower(span) > NOW() - INTERVAL '%s minutes'")
            params.append(minutes)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY lower(span) DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, params)
        return cur.fetchall()


def get_band_timeseries(session_id: str = None, minutes: int = 60) -> list:
    """Get band power timeseries for charting."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if session_id:
            cur.execute("""
                SELECT
                    ts_start as timestamp,
                    alpha_rel as alpha,
                    beta_rel as beta,
                    theta_rel as theta,
                    delta_rel as delta,
                    gamma_rel as gamma,
                    features->>'state' as state
                FROM eeg_window
                WHERE session_id = %s
                ORDER BY ts_start ASC
            """, (session_id,))
        else:
            cur.execute("""
                SELECT
                    ts_start as timestamp,
                    alpha_rel as alpha,
                    beta_rel as beta,
                    theta_rel as theta,
                    delta_rel as delta,
                    gamma_rel as gamma,
                    features->>'state' as state
                FROM eeg_window
                WHERE ts_start > NOW() - INTERVAL '%s minutes'
                ORDER BY ts_start ASC
            """, (minutes,))

        return cur.fetchall()
