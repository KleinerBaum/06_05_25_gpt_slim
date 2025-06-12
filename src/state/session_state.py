# src/state/session_state.py

import streamlit as st
from src.config import keys

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
