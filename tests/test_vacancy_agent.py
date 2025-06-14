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
