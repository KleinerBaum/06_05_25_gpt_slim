from __future__ import annotations

import json
from unittest.mock import Mock, patch

import streamlit.runtime.secrets as st_secrets

with patch.object(st_secrets.Secrets, "_parse", return_value={}):
    from logic.processors import suggest_additional_skills


def test_suggest_additional_skills_parses_json() -> None:
    response_data = {"technical": ["Python", "SQL"], "soft": ["Communication"]}
    fake_resp = Mock()
    fake_resp.choices = [Mock(message=Mock(content=json.dumps(response_data)))]

    with patch(
        "logic.processors.openai.chat.completions.create",
        return_value=fake_resp,
    ) as create_mock:
        result = suggest_additional_skills(
            "Data Scientist",
            "Analyze data",
            "Senior",
            "Some job ad text",
            num_skills=2,
        )
    create_mock.assert_called_once()
    assert result == {
        "technical": ["Python", "SQL"],
        "soft": ["Communication"],
    }
