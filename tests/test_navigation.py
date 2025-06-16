from unittest.mock import patch
import streamlit.runtime.secrets as st_secrets

with patch.object(st_secrets.Secrets, "_parse", return_value={}):
    from components.wizard import next_step, previous_step
    import streamlit as st


def test_next_previous_step() -> None:
    st.session_state.clear()
    st.session_state["wizard_step"] = 1
    next_step()
    assert st.session_state["wizard_step"] == 2
    previous_step()
    assert st.session_state["wizard_step"] == 1
