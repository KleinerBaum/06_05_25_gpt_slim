from __future__ import annotations

from unittest.mock import Mock, patch

import streamlit.runtime.secrets as st_secrets

with patch.object(st_secrets.Secrets, "_parse", return_value={}):
    from utils.llm_utils import suggest_additional_skills


def test_suggest_additional_skills_parses_output() -> None:
    fake_content = "Technical Skills:\n- Python\n- SQL\nSoft Skills:\n- Leadership\n- Communication"
    fake_resp = Mock()
    fake_resp.choices = [Mock(message=Mock(content=fake_content))]

    with patch(
        "utils.llm_utils.openai.chat.completions.create",
        return_value=fake_resp,
    ):
        result = suggest_additional_skills("Engineer")

    assert result["technical"] == ["Python", "SQL"]
    assert result["soft"] == ["Leadership", "Communication"]
