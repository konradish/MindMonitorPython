"""
EEG Admin Panel - Brain State Visualization & Management

A Streamlit-based admin panel for viewing brain states, adding labels,
managing custom state definitions, and monitoring EEG data.

Usage:
    DATABASE_URL="postgresql://eeg:eegpass@localhost:5590/eeg" \
        streamlit run admin/app.py
"""

import streamlit as st

# Page config - must be first Streamlit command
st.set_page_config(
    page_title="EEG Admin Panel",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern look
st.markdown("""
<style>
    /* Modern rounded corners and gradients */
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 1rem;
        color: white;
    }
    .stMetric label {
        color: rgba(255,255,255,0.8) !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: white !important;
    }

    /* Card-like containers */
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
        background: rgba(255,255,255,0.05);
        border-radius: 0.75rem;
        padding: 0.5rem;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }

    /* Button styling */
    .stButton > button {
        border-radius: 0.5rem;
        border: none;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        transition: transform 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }

    /* Input styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div {
        border-radius: 0.5rem;
    }

    /* Dataframe styling */
    .stDataFrame {
        border-radius: 0.75rem;
        overflow: hidden;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def main():
    st.title("🧠 EEG Admin Panel")
    st.markdown("View brain states, manage labels, and monitor your EEG data.")

    # Main content
    st.info("👈 Select a page from the sidebar to get started.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 📊 Dashboard
        Real-time brain state visualization with band power charts.
        Monitor your current consciousness state.
        """)

    with col2:
        st.markdown("""
        ### 🏷️ Annotations
        Add custom labels to your EEG data.
        Review past annotations and their context.
        """)

    with col3:
        st.markdown("""
        ### ⚙️ State Definitions
        Create custom brain state patterns.
        Define thresholds and interpretations.
        """)


if __name__ == "__main__":
    main()
