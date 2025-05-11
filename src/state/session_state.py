# src/state/session_state.py

import streamlit as st
from src.config import keys
from src.logic import trigger_engine

def initialize_session_state() -> None:
    """
    Ensure every expected wizard field exists in st.session_state.
    Calling it more than once is a no-op.
    """
    if "_vacalyser_state_init" in st.session_state:
        return  # already initialized in this session

    # Initialize all wizard step fields to None
    for step_fields in keys.STEP_KEYS.values():
        for fld in step_fields:
            st.session_state.setdefault(fld, None)
    # Initialize generated/internal fields
    for fld in keys.GENERATED_KEYS:
        st.session_state.setdefault(fld, None)

    st.session_state.setdefault("trace_events", [])
    st.session_state["_vacalyser_state_init"] = True

class SessionState:
    """Helper class to manage Vacalyser session state across Streamlit reruns."""

    def load_from_dict(self, data: dict):
        """Load multiple fields into session state from a given dict (e.g., AI output)."""
        for key, value in data.items():
            if key in st.session_state:
                st.session_state[key] = value
