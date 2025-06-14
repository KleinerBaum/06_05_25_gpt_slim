from components.wizard import match_and_store_keys


def test_match_and_store_keys_extracts_values() -> None:
    text = "Company Name: ACME\nCity: Berlin"
    state: dict[str, str | None] = {"company_name": None, "city": None}
    match_and_store_keys(text, state)
    assert state["company_name"] == "ACME"
    assert state["city"] == "Berlin"


def test_match_and_store_keys_does_not_override_existing() -> None:
    text = "City: Berlin"
    state = {"city": "Hamburg"}
    match_and_store_keys(text, state)
    assert state["city"] == "Hamburg"
