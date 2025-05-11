# session_state.py
# ─────────────────────────────────────────────────────────────────────────────
"""Helpers to initialize and manage Streamlit session state for the Vacalyser wizard."""

from __future__ import annotations
from typing import Any
import streamlit as st
from src import keys

def initialize_session_state() -> None:
    """Ensure all expected wizard fields exist in st.session_state (idempotent)."""
    if st.session_state.get("_vacalyser_state_init"):
        return  # already initialized
    # Initialize step fields to None
    for field_list in keys.STEP_KEYS.values():
        for field in field_list:
            st.session_state.setdefault(field, None)
    # Initialize generated/internal fields
    for field in keys.GENERATED_KEYS:
        st.session_state.setdefault(field, None)
    # Initialize wizard step and trace events
    st.session_state.setdefault("wizard_step", 1)
    st.session_state.setdefault("trace_events", [])
    # Mark initialization complete
    st.session_state["_vacalyser_state_init"] = True

class SessionState:
    """Utility class for manipulating Vacalyser session state."""
    def __init__(self):
        initialize_session_state()

    def reset(self) -> None:
        """Clear all wizard fields and reset wizard state (for starting a new wizard session)."""
        # Remove wizard fields
        for field_list in keys.STEP_KEYS.values():
            for field in field_list:
                if field in st.session_state:
                    del st.session_state[field]
        for field in keys.GENERATED_KEYS:
            if field in st.session_state:
                del st.session_state[field]
        # Reset trace events list
        st.session_state["trace_events"] = []
        # Reset wizard step and reinitialize
        st.session_state["wizard_step"] = 1
        st.session_state.pop("_vacalyser_state_init", None)
        initialize_session_state()

    def get_job_spec_dict(self) -> dict[str, Any]:
        """Collect all job spec fields into a dictionary from session state."""
        spec: dict[str, Any] = {}
        for field_list in keys.STEP_KEYS.values():
            for field in field_list:
                spec[field] = st.session_state.get(field)
        return spec

    def load_from_dict(self, data: dict[str, Any]) -> None:
        """Load a dictionary of field values into session state."""
        for key, value in data.items():
            if key in st.session_state:
                st.session_state[key] = value

    def toggle_flag(self, key: str) -> None:
        """Toggle a boolean session state value (for flags or modes)."""
        if key in st.session_state and isinstance(st.session_state[key], bool):
            st.session_state[key] = not st.session_state[key]
