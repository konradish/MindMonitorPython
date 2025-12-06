"""Annotations page - View and manage EEG labels."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(__file__).rsplit('/pages', 1)[0])
from utils.db import (
    get_annotations, add_annotation, add_annotation_with_range,
    delete_annotation, get_sessions, get_current_state, to_chicago
)

st.set_page_config(page_title="Annotations", page_icon="🏷️", layout="wide")

st.title("🏷️ Annotations")
st.markdown("Label and annotate your EEG data")


# Get sessions for dropdown
sessions = get_sessions(limit=50)

if not sessions:
    st.warning("No sessions found. Record some EEG data first.")
    st.stop()


# Create annotation form
st.subheader("Add New Annotation")

# Common labels
COMMON_LABELS = [
    "meditation",
    "work",
    "creative",
    "relaxing",
    "exercise",
    "reading",
    "conversation",
    "stress",
    "anxiety",
    "flow",
    "distracted",
    "focused",
    "tired",
    "energized",
    "other"
]

with st.form("new_annotation"):
    col1, col2 = st.columns(2)

    with col1:
        # Session selector
        session_options = {
            f"{to_chicago(s['started_at'])} ({s['window_count']} windows)": str(s['id'])
            for s in sessions
        }
        selected_label = st.selectbox(
            "Session",
            options=list(session_options.keys()),
            help="Select which session to annotate"
        )
        selected_session = session_options.get(selected_label)

        # Label input
        label_choice = st.selectbox(
            "Label",
            options=COMMON_LABELS,
            help="Choose a predefined label or select 'other' for custom"
        )

        if label_choice == "other":
            custom_label = st.text_input("Custom label")
            label = custom_label if custom_label else "unlabeled"
        else:
            label = label_choice

    with col2:
        # Notes
        notes = st.text_area(
            "Notes",
            placeholder="Describe what you were doing or feeling...",
            help="Add context about this annotation"
        )

        # Author
        author = st.text_input(
            "Author",
            value="admin_panel",
            help="Who is creating this annotation"
        )

    # Time range options
    st.markdown("**Timing**")
    timing_option = st.radio(
        "When does this annotation apply?",
        options=["Right now", "Time range"],
        horizontal=True
    )

    if timing_option == "Time range":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date", datetime.now())
            start_time = st.time_input("Start time", datetime.now().time())
        with col2:
            end_date = st.date_input("End date", datetime.now())
            end_time = st.time_input("End time", datetime.now().time())

        start_dt = datetime.combine(start_date, start_time)
        end_dt = datetime.combine(end_date, end_time)

    submitted = st.form_submit_button("Add Annotation", type="primary")

    if submitted:
        if not label:
            st.error("Please enter a label")
        elif not selected_session:
            st.error("Please select a session")
        else:
            if timing_option == "Right now":
                if add_annotation(selected_session, label, notes, author):
                    st.success(f"✅ Added annotation: {label}")
                    st.rerun()
            else:
                if add_annotation_with_range(selected_session, label, notes, start_dt, end_dt, author):
                    st.success(f"✅ Added annotation: {label} ({start_dt} to {end_dt})")
                    st.rerun()


# Show current state for context
st.subheader("Current Brain State")
current = get_current_state(window_seconds=10)

if current and current.get('ts_start'):
    state = current.get('state', 'UNKNOWN')

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("State", state)
    with col2:
        st.metric("Alpha", f"{current.get('alpha_rel', 0):.1f}%")
    with col3:
        st.metric("Beta", f"{current.get('beta_rel', 0):.1f}%")
    with col4:
        st.metric("Theta", f"{current.get('theta_rel', 0):.1f}%")
    with col5:
        st.metric("Delta", f"{current.get('delta_rel', 0):.1f}%")
    with col6:
        st.metric("Gamma", f"{current.get('gamma_rel', 0):.1f}%")
else:
    st.info("No current EEG data. Start recording to see brain state.")


# View existing annotations
st.subheader("Recent Annotations")

# Filters
col1, col2, col3 = st.columns(3)

with col1:
    filter_session = st.selectbox(
        "Filter by session",
        options=["All sessions"] + list(session_options.keys()),
        key="filter_session"
    )

with col2:
    filter_minutes = st.selectbox(
        "Time range",
        options=[60, 120, 360, 1440, 10080],
        format_func=lambda x: {
            60: "Last hour",
            120: "Last 2 hours",
            360: "Last 6 hours",
            1440: "Last 24 hours",
            10080: "Last week"
        }.get(x, f"{x} minutes"),
        key="filter_minutes"
    )

with col3:
    filter_label = st.text_input("Filter by label", key="filter_label")

# Get annotations
if filter_session == "All sessions":
    annotations = get_annotations(minutes=filter_minutes, limit=100)
else:
    session_id = session_options.get(filter_session)
    annotations = get_annotations(session_id=session_id, minutes=filter_minutes, limit=100)

# Filter by label if specified
if filter_label:
    annotations = [a for a in annotations if filter_label.lower() in a['label'].lower()]

if annotations:
    # Build dataframe
    ann_df = pd.DataFrame(annotations)
    ann_df['time'] = ann_df['created_at'].apply(to_chicago)
    ann_df['session_short'] = ann_df['session_id'].apply(lambda x: str(x)[:8])

    # Display with delete buttons
    for idx, row in ann_df.iterrows():
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 3, 1])

            with col1:
                st.write(f"**{row['label']}**")
            with col2:
                st.write(row['time'])
            with col3:
                st.write(f"by {row['author']}")
            with col4:
                if row['notes']:
                    st.write(row['notes'][:50] + "..." if len(row['notes'] or '') > 50 else row['notes'])
            with col5:
                if st.button("🗑️", key=f"del_{idx}", help="Delete this annotation"):
                    if delete_annotation(row['session_id'], row['span_start'], row['label']):
                        st.success("Deleted!")
                        st.rerun()

            st.divider()

    # Summary stats
    st.subheader("Annotation Statistics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Label Distribution**")
        label_counts = ann_df['label'].value_counts()
        st.bar_chart(label_counts)

    with col2:
        st.markdown("**Authors**")
        author_counts = ann_df['author'].value_counts()
        for author, count in author_counts.items():
            st.write(f"- {author}: {count} annotations")

else:
    st.info("No annotations found matching your filters. Add some above!")


# Bulk actions
st.subheader("Bulk Actions")

with st.expander("Import Annotations from CSV"):
    st.markdown("""
    Upload a CSV file with columns:
    - `session_id` (UUID)
    - `label` (text)
    - `notes` (text, optional)
    - `author` (text, optional - defaults to 'csv_import')
    """)

    uploaded_file = st.file_uploader("Choose CSV file", type="csv")

    if uploaded_file is not None:
        import_df = pd.read_csv(uploaded_file)
        st.write("Preview:")
        st.dataframe(import_df.head())

        if st.button("Import All"):
            imported = 0
            for _, row in import_df.iterrows():
                if add_annotation(
                    row['session_id'],
                    row['label'],
                    row.get('notes', ''),
                    row.get('author', 'csv_import')
                ):
                    imported += 1
            st.success(f"Imported {imported} annotations!")
            st.rerun()
