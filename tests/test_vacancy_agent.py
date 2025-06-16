from __future__ import annotations

from unittest.mock import Mock, patch
import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")

import streamlit.runtime.secrets as st_secrets
from models.job_models import JobSpec

with patch.object(st_secrets.Secrets, "_parse", return_value={}):
    from services.vacancy_agent import fix_json_output, FUNCTION_DEFS


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
    fake_resp.output_text = completion

    with patch(
        "services.vacancy_agent.openai.responses.create",
        return_value=fake_resp,
    ) as create_mock:
        result = fix_json_output(malformed)

    create_mock.assert_called_once()
    assert result == fixed_spec.model_dump()


def test_auto_fill_uses_file_bytes() -> None:
    call_obj = Mock()
    call_obj.name = "extract_text_from_file"
    call_obj.arguments = "{}"
    call_obj.call_id = "1"
    call_obj.type = "function_call"
    fake_first = Mock(id="r1", output=[call_obj], output_text="")
    fake_second = Mock(id="r2", output=[], output_text='{"job_title": "Dev"}')
    responses = [fake_first, fake_second]

    def fake_create(*_args, **_kwargs):
        return responses.pop(0)

    with (
        patch(
            "services.vacancy_agent.openai.responses.create",
            side_effect=fake_create,
        ) as create_mock,
        patch(
            "logic.file_tools.extract_text_from_file", return_value="job text"
        ) as extract_mock,
        patch(
            "services.vacancy_agent.run_file_search",
            return_value={"skill_extraction": ["snippet"]},
        ) as search_mock,
    ):
        from services.vacancy_agent import auto_fill_job_spec

        result = auto_fill_job_spec(file_bytes=b"abc", file_name="sample.txt")

    extract_mock.assert_called_once_with(b"abc", "sample.txt")
    search_mock.assert_called_once_with(["sample.txt"])
    assert result["job_title"] == "Dev"
    assert create_mock.call_count == 2


def test_function_defs_contains_expected_names() -> None:
    names = {f["name"] for f in FUNCTION_DEFS}
    assert {
        "extract_text_from_file",
        "scrape_company_site",
        "retrieve_esco_skills",
        "update_salary_range",
        "interview_prep_generator",
        "vector_search_candidates",
    }.issubset(names)


def test_auto_fill_uses_web_search() -> None:
    fake_resp = Mock(output=[], output_text='{"job_title": "Dev"}')

    with (
        patch(
            "services.vacancy_agent.openai.responses.create",
            return_value=fake_resp,
        ) as create_mock,
        patch(
            "services.vacancy_agent.fetch_external_insight", return_value=["info"]
        ) as fetch_mock,
    ):
        from services.vacancy_agent import auto_fill_job_spec

        result = auto_fill_job_spec(input_url="http://example.com")

    fetch_mock.assert_called_once_with("branchentrends")
    assert result["job_title"] == "Dev"
    create_mock.assert_called_once()
