from unittest.mock import patch
import streamlit.runtime.secrets as st_secrets

with patch.object(st_secrets.Secrets, "_parse", return_value={}):
    from components.wizard import match_and_store_keys


def test_match_and_store_keys_extracts_values() -> None:
    text = "company name - ACME\ncity: Berlin"
    state: dict[str, str | None] = {"company_name": None, "city": None}
    match_and_store_keys(text, state)
    assert state["company_name"] == "ACME"
    assert state["city"] == "Berlin"


def test_match_and_store_keys_does_not_override_existing() -> None:
    text = "City: Berlin"
    state = {"city": "Hamburg"}
    match_and_store_keys(text, state)
    assert state["city"] == "Hamburg"
