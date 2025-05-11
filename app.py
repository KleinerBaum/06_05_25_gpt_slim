import streamlit as st
from src.pages import wizard  # import the wizard module (8-step recruitment flow)

# Set up page configuration (title, icon, layout, etc.)
st.set_page_config(page_title="RoleCraft Recruitment Wizard",
                   page_icon="🚀", layout="wide")  # wide layout for better use of space:contentReference[oaicite:0]{index=0}

# App-wide language selection (German or English)
if "language" not in st.session_state:
    st.session_state["language"] = "Deutsch"  # default to German (can default to English as needed)
language_choice = st.sidebar.radio("🌐 Sprache / Language", ("Deutsch", "English"),
                                   index=0 if st.session_state["language"] == "Deutsch" else 1)
st.session_state["language"] = language_choice

# Run the main wizard interface (UI logic is handled in wizard.py based on selected language)
wizard.run_wizard()
