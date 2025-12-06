"""Baselines page - Manage personal EEG baselines."""

import streamlit as st
import pandas as pd

import sys
sys.path.insert(0, str(__file__).rsplit('/pages', 1)[0])
from utils.db import (
    get_baselines, save_baseline, delete_baseline, get_current_state, to_chicago
)

st.set_page_config(page_title="Baselines", page_icon="📐", layout="wide")

st.title("📐 Baselines")
st.markdown("Save and compare personal EEG baselines")


# Show current state for reference
st.subheader("Current Brain State")
current = get_current_state(window_seconds=10)

if current and current.get('ts_start'):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("State", current.get('state', 'UNKNOWN'))
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

    has_current = True
else:
    st.warning("No current EEG data available. Start recording to save baselines.")
    has_current = False


# Save new baseline
st.subheader("Save New Baseline")

with st.form("save_baseline"):
    col1, col2 = st.columns(2)

    with col1:
        baseline_name = st.text_input(
            "Baseline Name",
            placeholder="e.g., morning_regulated, flow_state, relaxed_evening",
            help="Unique name for this baseline"
        )

        avg_minutes = st.slider(
            "Average over (minutes)",
            min_value=1,
            max_value=60,
            value=5,
            help="How many minutes of data to average"
        )

    with col2:
        baseline_notes = st.text_area(
            "Notes",
            placeholder="What were you doing during this period? What does this baseline represent?",
            help="Description of this baseline for future reference"
        )

    submitted = st.form_submit_button("💾 Save Baseline", type="primary", disabled=not has_current)

    if submitted:
        if not baseline_name:
            st.error("Please enter a baseline name")
        else:
            if save_baseline(baseline_name, avg_minutes, baseline_notes):
                st.success(f"✅ Saved baseline: {baseline_name}")
                st.rerun()


# List existing baselines
st.subheader("Saved Baselines")

baselines = get_baselines()

if baselines:
    # Create display dataframe
    baseline_df = pd.DataFrame(baselines)

    # Comparison view
    for baseline in baselines:
        with st.expander(f"📐 **{baseline['name']}** ({baseline['samples']} samples)"):
            col1, col2 = st.columns([2, 1])

            with col1:
                # Band power bars
                bands = {
                    'Alpha': (baseline['alpha_rel'], '#4CAF50'),
                    'Beta': (baseline['beta_rel'], '#2196F3'),
                    'Theta': (baseline['theta_rel'], '#9C27B0'),
                    'Delta': (baseline['delta_rel'], '#FF9800'),
                    'Gamma': (baseline['gamma_rel'], '#F44336'),
                }

                st.markdown("**Band Powers:**")
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

                if baseline.get('notes'):
                    st.markdown("**Notes:**")
                    st.write(baseline['notes'])

            with col2:
                # Comparison with current
                if has_current:
                    st.markdown("**Comparison with Current:**")

                    diff_alpha = (current.get('alpha_rel', 0) or 0) - baseline['alpha_rel']
                    diff_beta = (current.get('beta_rel', 0) or 0) - baseline['beta_rel']
                    diff_theta = (current.get('theta_rel', 0) or 0) - baseline['theta_rel']
                    diff_delta = (current.get('delta_rel', 0) or 0) - baseline['delta_rel']
                    diff_gamma = (current.get('gamma_rel', 0) or 0) - baseline['gamma_rel']

                    st.metric("Alpha Δ", f"{diff_alpha:+.1f}%")
                    st.metric("Beta Δ", f"{diff_beta:+.1f}%")
                    st.metric("Theta Δ", f"{diff_theta:+.1f}%")
                    st.metric("Delta Δ", f"{diff_delta:+.1f}%")
                    st.metric("Gamma Δ", f"{diff_gamma:+.1f}%")

                st.markdown("---")

                # Delete button
                if st.button("🗑️ Delete", key=f"delete_{baseline['name']}", type="secondary"):
                    if delete_baseline(baseline['name']):
                        st.success(f"Deleted {baseline['name']}")
                        st.rerun()

                st.caption(f"Created: {to_chicago(baseline.get('created_at'))}")
                if baseline.get('updated_at'):
                    st.caption(f"Updated: {to_chicago(baseline.get('updated_at'))}")

    # Comparison chart
    st.subheader("Baseline Comparison Chart")

    # Prepare chart data
    chart_data = pd.DataFrame({
        'Baseline': [b['name'] for b in baselines],
        'Alpha': [b['alpha_rel'] for b in baselines],
        'Beta': [b['beta_rel'] for b in baselines],
        'Theta': [b['theta_rel'] for b in baselines],
        'Delta': [b['delta_rel'] for b in baselines],
        'Gamma': [b['gamma_rel'] for b in baselines],
    })

    if has_current:
        # Add current state for comparison
        current_row = pd.DataFrame({
            'Baseline': ['CURRENT'],
            'Alpha': [current.get('alpha_rel', 0)],
            'Beta': [current.get('beta_rel', 0)],
            'Theta': [current.get('theta_rel', 0)],
            'Delta': [current.get('delta_rel', 0)],
            'Gamma': [current.get('gamma_rel', 0)],
        })
        chart_data = pd.concat([current_row, chart_data], ignore_index=True)

    # Melt for grouped bar chart
    melted = chart_data.melt(id_vars=['Baseline'], var_name='Band', value_name='Power (%)')

    # Use Streamlit's bar chart with horizontal layout for comparison
    st.bar_chart(chart_data.set_index('Baseline'))

else:
    st.info("No baselines saved yet. Save one above when you're in a desired brain state!")


# Tips section
st.subheader("Tips for Using Baselines")

with st.expander("💡 Best Practices"):
    st.markdown("""
    **When to Save Baselines:**
    - **Morning Regulated** - Save when you feel calm and alert in the morning
    - **Flow State** - Capture when you're deeply focused on creative work
    - **Deep Relaxation** - Record during meditation or before sleep
    - **Pre-Meeting** - Your baseline before important conversations
    - **Post-Exercise** - Brain state after physical activity

    **Using Baselines:**
    - Compare current state to baselines to understand deviations
    - Create custom state definitions from baselines for automatic detection
    - Track how your brain patterns change over time
    - Use baselines to calibrate personalized state thresholds

    **Tips:**
    - Average over at least 5 minutes for stable baselines
    - Add detailed notes about context (time of day, activities, mood)
    - Review and update baselines periodically
    - Delete outdated baselines that no longer represent your patterns
    """)
