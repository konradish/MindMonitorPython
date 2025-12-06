"""Dashboard page - Real-time EEG visualization."""

import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(__file__).rsplit('/pages', 1)[0])
from utils.db import (
    get_current_state, get_band_timeseries, get_sessions,
    to_chicago, get_detections
)

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

st.title("📊 Dashboard")
st.markdown("Real-time brain state monitoring")

# Controls
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    window_seconds = st.slider("Rolling average window (seconds)", 5, 60, 10)
with col2:
    history_minutes = st.slider("History (minutes)", 5, 120, 30)
with col3:
    auto_refresh = st.checkbox("Auto-refresh", value=True)


# State emoji mapping
STATE_EMOJI = {
    "FOCUSED": "🎯",
    "RELAXED": "😌",
    "MEDITATIVE": "🧘",
    "DROWSY": "😴",
    "ALERT_TENSE": "😰",
    "CREATIVE_FLOW": "🎨",
    "PEAK_FOCUS": "🔥",
    "JHANA": "✨",
    "SECURITY_GUARD": "🛡️",
    "RECOVERY": "💚",
    "MIXED": "🔀",
    "ERROR": "⚠️",
}

# State color mapping
STATE_COLORS = {
    "FOCUSED": "#4CAF50",
    "RELAXED": "#2196F3",
    "MEDITATIVE": "#9C27B0",
    "DROWSY": "#607D8B",
    "ALERT_TENSE": "#FF5722",
    "CREATIVE_FLOW": "#FF9800",
    "PEAK_FOCUS": "#F44336",
    "JHANA": "#E91E63",
    "SECURITY_GUARD": "#795548",
    "RECOVERY": "#8BC34A",
    "MIXED": "#9E9E9E",
    "ERROR": "#F44336",
}


def get_state_display(state):
    """Get emoji and color for a state."""
    emoji = STATE_EMOJI.get(state, "🧠")
    color = STATE_COLORS.get(state, "#9E9E9E")
    return emoji, color


# Current state display
st.subheader("Current State")

current = get_current_state(window_seconds)

if current and current.get('ts_start'):
    state = current.get('state', 'UNKNOWN')
    emoji, color = get_state_display(state)

    # Main state display
    col1, col2, col3 = st.columns([1, 2, 2])

    with col1:
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, {color}40 0%, {color}20 100%); border-radius: 1rem; border: 2px solid {color};">
            <span style="font-size: 4rem;">{emoji}</span>
            <h2 style="margin: 0.5rem 0; color: {color};">{state}</h2>
            <p style="color: #888; margin: 0;">Last update: {to_chicago(current['ts_start'])}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Band power metrics
        st.markdown("**Band Powers (%)**")
        bands = {
            'Alpha': (current.get('alpha_rel') or 0, '#4CAF50'),
            'Beta': (current.get('beta_rel') or 0, '#2196F3'),
            'Theta': (current.get('theta_rel') or 0, '#9C27B0'),
            'Delta': (current.get('delta_rel') or 0, '#FF9800'),
            'Gamma': (current.get('gamma_rel') or 0, '#F44336'),
        }

        for band, (value, color) in bands.items():
            st.markdown(f"""
            <div style="margin-bottom: 0.5rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                    <span>{band}</span>
                    <span style="font-weight: bold;">{value:.1f}%</span>
                </div>
                <div style="background: #333; border-radius: 4px; height: 12px; overflow: hidden;">
                    <div style="background: {color}; width: {min(value, 100)}%; height: 100%; border-radius: 4px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col3:
        st.metric("Samples in window", current.get('sample_count', 0))
        st.metric("Alpha/Beta Ratio",
                  f"{(current.get('alpha_rel') or 0) / max(current.get('beta_rel') or 1, 1):.2f}")

        # Cognitive load indicator
        beta = current.get('beta_rel') or 0
        if beta > 35:
            st.warning("⚡ High cognitive load")
        elif beta > 20:
            st.info("🔄 Moderate cognitive load")
        else:
            st.success("😌 Low cognitive load")
else:
    st.warning("No recent EEG data available. Make sure the OSC receiver is running.")


# Band power chart
st.subheader("Band Power History")

timeseries = get_band_timeseries(minutes=history_minutes)

if timeseries:
    df = pd.DataFrame(timeseries)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Area chart for band powers
    chart_data = df.set_index('timestamp')[['alpha', 'beta', 'theta', 'delta', 'gamma']]
    chart_data.columns = ['Alpha', 'Beta', 'Theta', 'Delta', 'Gamma']

    st.area_chart(chart_data, use_container_width=True)

    # State timeline
    st.subheader("State Timeline")

    # Get unique states and their time ranges
    if 'state' in df.columns and df['state'].notna().any():
        state_changes = df[df['state'] != df['state'].shift()].copy()
        state_changes['duration'] = state_changes['timestamp'].shift(-1) - state_changes['timestamp']

        col1, col2 = st.columns([3, 1])

        with col1:
            # Visual timeline
            timeline_html = '<div style="display: flex; height: 40px; border-radius: 8px; overflow: hidden; background: #333;">'
            total_duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()

            for _, row in state_changes.iterrows():
                if pd.isna(row['duration']):
                    dur_secs = (df['timestamp'].max() - row['timestamp']).total_seconds()
                else:
                    dur_secs = row['duration'].total_seconds()

                width_pct = (dur_secs / total_duration * 100) if total_duration > 0 else 0
                if width_pct < 0.5:
                    continue

                state = row['state'] or 'UNKNOWN'
                emoji, color = get_state_display(state)
                timeline_html += f'<div style="width: {width_pct}%; background: {color}; display: flex; align-items: center; justify-content: center; overflow: hidden;" title="{state}">{emoji if width_pct > 3 else ""}</div>'

            timeline_html += '</div>'
            st.markdown(timeline_html, unsafe_allow_html=True)

        with col2:
            # State distribution
            state_counts = df['state'].value_counts()
            for state, count in state_counts.head(5).items():
                if state:
                    emoji, _ = get_state_display(state)
                    st.write(f"{emoji} {state}: {count}")
else:
    st.info("No historical data available for the selected time range.")


# Recent detections
st.subheader("Recent Detections")

detections = get_detections(minutes=history_minutes, limit=10)

if detections:
    det_df = pd.DataFrame(detections)
    det_df['time'] = det_df['span_start'].apply(to_chicago)
    det_df['emoji'] = det_df['label'].apply(lambda x: STATE_EMOJI.get(x, "🧠"))

    display_df = det_df[['time', 'emoji', 'label', 'source', 'score']].copy()
    display_df.columns = ['Time', '', 'State', 'Source', 'Score']
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No detections in the selected time range.")


# Auto-refresh
if auto_refresh:
    time.sleep(2)
    st.rerun()
