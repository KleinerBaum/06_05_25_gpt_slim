"""Streamlit entry point for the RoleCraft wizard."""

import streamlit as st
from pages import wizard

# Set up page configuration (title, icon, layout, etc.)
st.set_page_config(
    page_title="RoleCraft Recruitment Wizard",
    page_icon="🚀",
    layout="wide",
)

# App-wide language selection (German or English)
if "language" not in st.session_state:
    # Default language is German; can be changed via the sidebar
    st.session_state["language"] = "Deutsch"
language_choice = st.sidebar.radio(
    "🌐 Sprache / Language",
    ("Deutsch", "English"),
    index=0 if st.session_state["language"] == "Deutsch" else 1,
)
st.session_state["language"] = language_choice

# Run the main wizard interface (UI logic is handled in wizard.py based on selected language)
wizard.run_wizard()
