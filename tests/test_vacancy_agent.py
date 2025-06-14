import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import openai


class DummyMessage:
    def __init__(self, content, function_call=None):
        self.content = content
        self.function_call = function_call


class DummyChoice:
    def __init__(self, message):
        self.message = message


class DummyResponse:
    def __init__(self, message):
        self.choices = [DummyChoice(message)]


def test_auto_fill_job_spec_uses_retry(monkeypatch):
    def fake_call_with_retry(func, *args, **kwargs):
        assert func is openai.ChatCompletion.create
        return DummyResponse(DummyMessage('{"job_title": "Engineer"}'))

    monkeypatch.setattr(st, "secrets", {})
    from services import vacancy_agent as vac

    monkeypatch.setattr(vac.llm_utils, "call_with_retry", fake_call_with_retry)
    auto_fill_job_spec = vac.auto_fill_job_spec

    result = auto_fill_job_spec(file_bytes=b"dummy", file_name="test.txt")

    assert result.get("job_title") == "Engineer"
