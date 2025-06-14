from __future__ import annotations

from unittest.mock import Mock, patch
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from models.job_models import JobSpec
from services.vacancy_agent import fix_json_output


def test_fix_json_output_returns_same_when_json_valid() -> None:
    spec = JobSpec(job_title="Dev")
    raw = spec.model_dump_json()
    result = fix_json_output(raw)
    assert result == spec.model_dump()


def test_fix_json_output_repairs_malformed_json() -> None:
    malformed = '{"job_title": "Engineer", "company_name": "ACME",}'
    fixed_spec = JobSpec(job_title="Engineer", company_name="ACME")
    completion = fixed_spec.model_dump_json()
    fake_resp = Mock()
    fake_resp.choices = [Mock(message=Mock(content=completion))]

    with patch(
        "services.vacancy_agent.openai.chat.completions.create",
        return_value=fake_resp,
    ) as create_mock:
        result = fix_json_output(malformed)

    create_mock.assert_called_once()
    assert result == fixed_spec.model_dump()


def test_auto_fill_uses_file_bytes() -> None:
    call_obj = Mock()
    call_obj.name = "extract_text_from_file"
    call_obj.arguments = "{}"
    fake_first = Mock()
    fake_first.choices = [Mock(message=Mock(function_call=call_obj))]
    fake_second = Mock()
    fake_second.choices = [Mock(message=Mock(content='{"job_title": "Dev"}'))]
    responses = [fake_first, fake_second]

    def fake_create(*_args, **_kwargs):
        return responses.pop(0)

    with (
        patch(
            "services.vacancy_agent.openai.chat.completions.create",
            side_effect=fake_create,
        ) as create_mock,
        patch(
            "logic.file_tools.extract_text_from_file", return_value="job text"
        ) as extract_mock,
    ):
        from services.vacancy_agent import auto_fill_job_spec

        result = auto_fill_job_spec(file_bytes=b"abc", file_name="sample.txt")

    extract_mock.assert_called_once_with(b"abc", "sample.txt")
    assert result["job_title"] == "Dev"
    assert create_mock.call_count == 2
