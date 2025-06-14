import pytest
from unittest.mock import patch
import streamlit.runtime.secrets as st_secrets

with patch.object(st_secrets.Secrets, "_parse", return_value={}):
    from services.external_data import fetch_external_insight, WEB_TOPICS


def test_fetch_external_insight_calls_web_run() -> None:
    with patch("ace_tools.web.run", return_value={"results": ["x"]}) as mock_run:
        result = fetch_external_insight(list(WEB_TOPICS.keys())[0])
    mock_run.assert_called_once()
    assert result == ["x"]


def test_fetch_external_insight_unknown_topic() -> None:
    with pytest.raises(ValueError):
        fetch_external_insight("unknown")
