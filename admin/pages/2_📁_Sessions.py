"""Sessions page - View and manage recording sessions."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(__file__).rsplit('/pages', 1)[0])
from utils.db import (
    get_sessions, get_session_by_id, get_eeg_windows,
    get_band_timeseries, get_annotations, get_detections, to_chicago
)

st.set_page_config(page_title="Sessions", page_icon="📁", layout="wide")

st.title("📁 Sessions")
st.markdown("View and explore EEG recording sessions")

# Get sessions
sessions = get_sessions(limit=50)

if not sessions:
    st.warning("No sessions found. Start recording EEG data to see sessions here.")
    st.stop()

# Session list
st.subheader("Recording Sessions")

# Create display dataframe
session_df = pd.DataFrame(sessions)
session_df['started'] = session_df['started_at'].apply(to_chicago)
session_df['duration'] = session_df.apply(
    lambda r: str(r['last_window'] - r['first_window']).split('.')[0]
    if r['first_window'] and r['last_window'] else 'N/A',
    axis=1
)
session_df['id_short'] = session_df['id'].apply(lambda x: str(x)[:8] + '...')

display_df = session_df[['id_short', 'started', 'window_count', 'duration', 'device', 'subject', 'notes']].copy()
display_df.columns = ['ID', 'Started', 'Windows', 'Duration', 'Device', 'Subject', 'Notes']

st.dataframe(display_df, use_container_width=True, hide_index=True)


# Session selector
st.subheader("Session Details")

session_options = {
    f"{to_chicago(s['started_at'])} ({s['window_count']} windows)": str(s['id'])
    for s in sessions
}

selected_label = st.selectbox("Select a session to view details", options=list(session_options.keys()))
selected_session_id = session_options.get(selected_label)

if selected_session_id:
    session = get_session_by_id(selected_session_id)

    if session:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Session ID", str(session['id'])[:8] + "...")
            st.metric("Device", session.get('device') or 'Unknown')

        with col2:
            st.metric("Started", to_chicago(session['started_at']))
            st.metric("Sample Rate", f"{session.get('sample_rate') or 256} Hz")

        with col3:
            st.metric("Subject", session.get('subject') or 'Unknown')
            if session.get('notes'):
                st.text(f"Notes: {session['notes']}")

        # Session data tabs
        tab1, tab2, tab3 = st.tabs(["📈 Band Powers", "🏷️ Annotations", "🔍 Detections"])

        with tab1:
            # Band power chart for session
            timeseries = get_band_timeseries(session_id=selected_session_id)

            if timeseries:
                df = pd.DataFrame(timeseries)
                df['timestamp'] = pd.to_datetime(df['timestamp'])

                chart_data = df.set_index('timestamp')[['alpha', 'beta', 'theta', 'delta', 'gamma']]
                chart_data.columns = ['Alpha', 'Beta', 'Theta', 'Delta', 'Gamma']

                st.area_chart(chart_data, use_container_width=True)

                # Summary stats
                st.markdown("**Session Statistics**")
                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:
                    st.metric("Avg Alpha", f"{df['alpha'].mean():.1f}%")
                with col2:
                    st.metric("Avg Beta", f"{df['beta'].mean():.1f}%")
                with col3:
                    st.metric("Avg Theta", f"{df['theta'].mean():.1f}%")
                with col4:
                    st.metric("Avg Delta", f"{df['delta'].mean():.1f}%")
                with col5:
                    st.metric("Avg Gamma", f"{df['gamma'].mean():.1f}%")

                # State distribution
                if 'state' in df.columns and df['state'].notna().any():
                    st.markdown("**State Distribution**")
                    state_counts = df['state'].value_counts()

                    # Pie chart data
                    state_df = pd.DataFrame({
                        'State': state_counts.index,
                        'Count': state_counts.values
                    })
                    st.bar_chart(state_df.set_index('State')['Count'])
            else:
                st.info("No EEG data for this session.")

        with tab2:
            annotations = get_annotations(session_id=selected_session_id)

            if annotations:
                ann_df = pd.DataFrame(annotations)
                ann_df['time'] = ann_df['span_start'].apply(to_chicago)

                display_ann = ann_df[['time', 'label', 'author', 'notes']].copy()
                display_ann.columns = ['Time', 'Label', 'Author', 'Notes']
                st.dataframe(display_ann, use_container_width=True, hide_index=True)
            else:
                st.info("No annotations for this session. Add some on the Annotations page!")

        with tab3:
            detections = get_detections(session_id=selected_session_id)

            if detections:
                det_df = pd.DataFrame(detections)
                det_df['time'] = det_df['span_start'].apply(to_chicago)

                display_det = det_df[['time', 'label', 'source', 'score']].copy()
                display_det.columns = ['Time', 'State', 'Source', 'Score']
                st.dataframe(display_det, use_container_width=True, hide_index=True)
            else:
                st.info("No automated detections for this session.")


# Export options
st.subheader("Export")

if selected_session_id:
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 Export Session Data (CSV)"):
            windows = get_eeg_windows(session_id=selected_session_id, limit=100000)
            if windows:
                export_df = pd.DataFrame(windows)
                csv = export_df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    f"session_{selected_session_id[:8]}.csv",
                    "text/csv"
                )
            else:
                st.warning("No data to export")

    with col2:
        if st.button("📥 Export Annotations (CSV)"):
            annotations = get_annotations(session_id=selected_session_id)
            if annotations:
                export_df = pd.DataFrame(annotations)
                csv = export_df.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    f"annotations_{selected_session_id[:8]}.csv",
                    "text/csv"
                )
            else:
                st.warning("No annotations to export")
