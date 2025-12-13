"""State Definitions page - Manage custom EEG states."""

import streamlit as st
import pandas as pd
import json

import sys
sys.path.insert(0, str(__file__).rsplit('/pages', 1)[0])
from utils.db import (
    get_state_definitions, add_state_definition, update_state_definition,
    delete_state_definition, get_current_state
)

st.set_page_config(page_title="State Definitions", page_icon="⚙️", layout="wide")

st.title("⚙️ State Definitions")
st.markdown("Create and manage custom brain state patterns")


# Show current state for reference
st.subheader("Current Brain State (Reference)")
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

    st.info("💡 Use the current values above as a reference when defining state thresholds.")
else:
    st.info("No current EEG data available.")


# Create new state definition
st.subheader("Create New State")

with st.expander("➕ Add New State Definition", expanded=False):
    with st.form("new_state"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "State Name",
                placeholder="e.g., DEEP_WORK, K_RELAXED",
                help="Unique name for this state (uppercase recommended)"
            )

            emoji = st.text_input(
                "Emoji",
                value="🧠",
                max_chars=2,
                help="Emoji to display for this state"
            )

            priority = st.slider(
                "Priority",
                min_value=1,
                max_value=100,
                value=50,
                help="Higher priority = checked first among custom states. Custom states always beat hardcoded rules."
            )

            enabled = st.checkbox("Enabled", value=True)

        with col2:
            interpretation = st.text_area(
                "Interpretation",
                placeholder="What does this state mean? How should Claude respond?",
                help="Explanation of this brain state"
            )

            recommendations_text = st.text_area(
                "Recommendations (one per line)",
                placeholder="Keep responses concise\nAvoid complex topics\n...",
                help="Communication recommendations for this state"
            )

            notes = st.text_area(
                "Notes",
                placeholder="Any additional notes about this state...",
                help="Internal notes (not shown to Claude)"
            )

        # Band thresholds
        st.markdown("**Band Power Thresholds (%)**")
        st.markdown("_Leave blank to not check that band. Values are percentages (0-100)._")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.markdown("**Alpha**")
            alpha_min = st.number_input("Min", min_value=0.0, max_value=100.0, value=None, key="alpha_min", format="%.1f")
            alpha_max = st.number_input("Max", min_value=0.0, max_value=100.0, value=None, key="alpha_max", format="%.1f")

        with col2:
            st.markdown("**Beta**")
            beta_min = st.number_input("Min", min_value=0.0, max_value=100.0, value=None, key="beta_min", format="%.1f")
            beta_max = st.number_input("Max", min_value=0.0, max_value=100.0, value=None, key="beta_max", format="%.1f")

        with col3:
            st.markdown("**Theta**")
            theta_min = st.number_input("Min", min_value=0.0, max_value=100.0, value=None, key="theta_min", format="%.1f")
            theta_max = st.number_input("Max", min_value=0.0, max_value=100.0, value=None, key="theta_max", format="%.1f")

        with col4:
            st.markdown("**Delta**")
            delta_min = st.number_input("Min", min_value=0.0, max_value=100.0, value=None, key="delta_min", format="%.1f")
            delta_max = st.number_input("Max", min_value=0.0, max_value=100.0, value=None, key="delta_max", format="%.1f")

        with col5:
            st.markdown("**Gamma**")
            gamma_min = st.number_input("Min", min_value=0.0, max_value=100.0, value=None, key="gamma_min", format="%.1f")
            gamma_max = st.number_input("Max", min_value=0.0, max_value=100.0, value=None, key="gamma_max", format="%.1f")

        submitted = st.form_submit_button("Create State", type="primary")

        if submitted:
            if not name:
                st.error("Please enter a state name")
            else:
                # Build conditions dict
                conditions = {}
                if alpha_min is not None:
                    conditions['alpha_min'] = alpha_min
                if alpha_max is not None:
                    conditions['alpha_max'] = alpha_max
                if beta_min is not None:
                    conditions['beta_min'] = beta_min
                if beta_max is not None:
                    conditions['beta_max'] = beta_max
                if theta_min is not None:
                    conditions['theta_min'] = theta_min
                if theta_max is not None:
                    conditions['theta_max'] = theta_max
                if delta_min is not None:
                    conditions['delta_min'] = delta_min
                if delta_max is not None:
                    conditions['delta_max'] = delta_max
                if gamma_min is not None:
                    conditions['gamma_min'] = gamma_min
                if gamma_max is not None:
                    conditions['gamma_max'] = gamma_max

                if not conditions:
                    st.error("Please set at least one band threshold")
                else:
                    # Parse recommendations
                    recommendations = [r.strip() for r in recommendations_text.split('\n') if r.strip()]

                    if add_state_definition(
                        name=name.upper(),
                        conditions=conditions,
                        interpretation=interpretation,
                        recommendations=recommendations,
                        emoji=emoji,
                        priority=priority,
                        enabled=enabled,
                        notes=notes
                    ):
                        st.success(f"✅ Created state: {name.upper()}")
                        st.rerun()


# List existing state definitions
st.subheader("Existing State Definitions")

states = get_state_definitions()

if states:
    for state in states:
        with st.expander(f"{state['emoji']} **{state['name']}** (Priority: {state['priority']}) {'✅' if state['enabled'] else '❌'}"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("**Conditions:**")
                conditions = state.get('conditions', {})
                if conditions:
                    cond_text = ", ".join([f"{k}: {v}%" for k, v in conditions.items()])
                    st.code(cond_text)
                else:
                    st.write("No conditions defined")

                st.markdown("**Interpretation:**")
                st.write(state.get('interpretation', 'No interpretation'))

                if state.get('recommendations'):
                    st.markdown("**Recommendations:**")
                    for rec in state['recommendations']:
                        st.write(f"- {rec}")

                if state.get('notes'):
                    st.markdown("**Notes:**")
                    st.write(state['notes'])

            with col2:
                st.markdown("**Actions:**")

                # Toggle enabled
                new_enabled = st.checkbox(
                    "Enabled",
                    value=state['enabled'],
                    key=f"enabled_{state['name']}"
                )
                if new_enabled != state['enabled']:
                    if update_state_definition(state['name'], enabled=new_enabled):
                        st.success("Updated!")
                        st.rerun()

                # Priority slider
                new_priority = st.slider(
                    "Priority",
                    min_value=1,
                    max_value=100,
                    value=state['priority'],
                    key=f"priority_{state['name']}"
                )
                if new_priority != state['priority']:
                    if st.button("Update Priority", key=f"update_priority_{state['name']}"):
                        if update_state_definition(state['name'], priority=new_priority):
                            st.success("Updated!")
                            st.rerun()

                # Delete button
                if st.button("🗑️ Delete", key=f"delete_{state['name']}", type="secondary"):
                    if delete_state_definition(state['name']):
                        st.success(f"Deleted {state['name']}")
                        st.rerun()

                st.markdown("---")
                st.caption(f"Author: {state.get('author', 'unknown')}")
                st.caption(f"Created: {state.get('created_at', 'unknown')}")

else:
    st.info("No custom state definitions yet. Create one above!")


# State definition guide
st.subheader("State Definition Guide")

with st.expander("View common state patterns"):
    st.markdown("""
    **The detection engine uses only custom states defined above.**
    If no custom state matches, the state will be **UNKNOWN**.

    Here are some common patterns you might want to define:

    | State | Emoji | Suggested Conditions |
    |-------|-------|---------------------|
    | **RELAXED** | 😌 | alpha_min: 40, beta_max: 25 |
    | **FOCUSED** | 🎯 | beta_min: 25, alpha_min: 20 |
    | **MEDITATIVE** | 🧘 | alpha_min: 60, beta_max: 15 |
    | **DROWSY** | 😴 | theta_min: 30, alpha_max: 30 |
    | **CREATIVE_FLOW** | 🎨 | alpha_min: 35, theta_min: 20 |
    | **ALERT** | ⚡ | beta_min: 35, gamma_min: 15 |
    | **CALM** | 🌊 | alpha_min: 45, beta_max: 20, delta_max: 25 |

    **Priority:** Higher priority states are checked first.
    The first matching state wins.
    """)


# Test against current state
st.subheader("Test State Matching")

if current and current.get('ts_start'):
    st.markdown("See which custom states would match the current brain state:")

    if st.button("Test Custom States"):
        matched = []
        percentages = {
            'alpha': current.get('alpha_rel', 0),
            'beta': current.get('beta_rel', 0),
            'theta': current.get('theta_rel', 0),
            'delta': current.get('delta_rel', 0),
            'gamma': current.get('gamma_rel', 0),
        }

        for state in states:
            if not state['enabled']:
                continue

            conditions = state.get('conditions', {})
            match = True

            for key, threshold in conditions.items():
                if key.endswith('_min'):
                    band = key.replace('_min', '')
                    if band in percentages and percentages[band] < threshold:
                        match = False
                        break
                elif key.endswith('_max'):
                    band = key.replace('_max', '')
                    if band in percentages and percentages[band] > threshold:
                        match = False
                        break

            if match:
                matched.append(state)

        if matched:
            # Sort by priority descending to show which would actually win
            matched.sort(key=lambda x: x['priority'], reverse=True)
            winner = matched[0]

            st.success(f"**{len(matched)} custom state(s) match current brain state:**")
            st.markdown(f"**Winner:** {winner['emoji']} **{winner['name']}** (priority {winner['priority']})")

            if len(matched) > 1:
                st.caption("Other matching states (lower priority, would not trigger):")
                for m in matched[1:]:
                    st.write(f"  {m['emoji']} {m['name']} (priority {m['priority']})")

            st.info("💡 The first matching state by priority wins. Define more states to cover different brain patterns.")
        else:
            st.warning("No custom states match the current brain state. The detection engine will return **UNKNOWN**.")
else:
    st.info("No current EEG data available for testing.")
