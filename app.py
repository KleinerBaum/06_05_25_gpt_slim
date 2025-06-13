import base64
import streamlit as st

from components import wizard

# Set up page configuration (title, icon, layout, etc.)
st.set_page_config(
    page_title="RoleCraft Recruitment Wizard",
    page_icon="🚀",
    layout="wide",
)


def _set_background(path: str) -> None:
    """Set a background image from a local file."""
    with open(path, "rb") as img_file:
        b64 = base64.b64encode(img_file.read()).decode()
    css = (
        f"<style>.stApp {{background-image: url('data:image/jpeg;base64,{b64}');"
        "background-size: cover;background-attachment: fixed;}}</style>"
    )
    st.markdown(css, unsafe_allow_html=True)


_set_background("images/AdobeStock_506577005.jpeg")

# App-wide language selection (German or English)
if "language" not in st.session_state:
    st.session_state["language"] = (
        "Deutsch"  # default to German (can default to English as needed)
    )
language_choice = st.sidebar.radio(
    "🌐 Sprache / Language",
    ("Deutsch", "English"),
    index=0 if st.session_state["language"] == "Deutsch" else 1,
)
st.session_state["language"] = language_choice

# Run the main wizard interface (UI logic is handled in wizard.py based on selected language)
wizard.run_wizard()
