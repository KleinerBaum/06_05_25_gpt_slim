from models.job_models import JobSpec
from logic.job_tools import (
    parse_job_spec,
    progress_percentage,
    highlight_keywords,
    build_boolean_query,
    generate_interview_questions,
    summarize_job_ad,
    generate_task_plan,
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


def test_build_boolean_query() -> None:
    query = build_boolean_query("Data Scientist", ["Python", "SQL"])
    assert '"Data Scientist"' in query
    assert "Python" in query and "SQL" in query


def test_generate_interview_questions() -> None:
    tasks = "Develop models\nAnalyze data"
    questions = generate_interview_questions(tasks, num_questions=2)
    assert len(questions) == 2
    assert all("?" in q for q in questions)


def test_summarize_job_ad() -> None:
    text = "word " * 100
    summary = summarize_job_ad(text, max_words=5)
    assert summary.endswith("...")
    assert len(summary.split()) <= 6


def test_generate_task_plan_splits_list() -> None:
    tasks = "Task A\nTask B\nTask C\nTask D"
    plan = generate_task_plan(tasks)
    assert set(plan.keys()) == {"day_30", "day_60", "day_90"}
    assert plan["day_30"]
