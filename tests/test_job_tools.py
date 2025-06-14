from models.job_models import JobSpec
from logic.job_tools import (
    parse_job_spec,
    progress_percentage,
    highlight_keywords,
)
from utils.keys import STEP_KEYS


def test_parse_job_spec_basic() -> None:
    text = "Job: Developer\nCompany: ACME\nSalary: 50k"
    spec = parse_job_spec(text)
    assert isinstance(spec, JobSpec)
    assert spec.job_title == "Developer"
    assert spec.company_name == "ACME"
    assert spec.salary_range == "50k"


def test_parse_job_spec_empty() -> None:
    spec = parse_job_spec("")
    assert spec.job_title is None
    assert spec.company_name is None
    assert spec.salary_range is None


def test_progress_percentage_single_field() -> None:
    total = sum(len(v) for v in STEP_KEYS.values())
    state: dict[str, object] = {"job_title": "Dev"}
    expected = round(1 / total * 100, 1)
    assert progress_percentage(state) == expected


def test_highlight_keywords_case_insensitive() -> None:
    text = "Python developer needed"
    result = highlight_keywords(text, ["python"])
    assert result.startswith("**Python**")
