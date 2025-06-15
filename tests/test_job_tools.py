from models.job_models import JobSpec
from logic.job_tools import (
    parse_job_spec,
    progress_percentage,
    highlight_keywords,
    build_boolean_query,
    generate_interview_questions,
    summarize_job_ad,
    generate_task_plan,
    verify_job_level,
    seo_optimize,
    check_compliance,
    generate_onboarding_plan,
    compare_benefits,
    employment_type_advisor,
    recruitment_checklist,
    risk_flagging,
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


def test_verify_job_level() -> None:
    resp = "Lead the team and manage strategy"
    assert verify_job_level(resp, "senior")
    assert not verify_job_level(resp, "junior")


def test_seo_optimize() -> None:
    text = "Python developer needed to build scalable data pipelines."
    result = seo_optimize(text, max_keywords=3)
    assert len(result["keywords"]) == 3
    assert result["meta_description"].startswith("Python developer")


def test_check_compliance() -> None:
    text = (
        "We are an equal opportunity employer and comply with GDPR data protection."
        " Applicants from all backgrounds are welcome."
    )
    assert check_compliance(text)
    assert not check_compliance("No clauses here")


def test_generate_onboarding_plan() -> None:
    plan = generate_onboarding_plan("Engineer")
    assert len(plan) >= 4
    assert any("Introduce" in step for step in plan)


def test_compare_benefits() -> None:
    offered = ["health insurance", "gym"]
    benchmark = ["health insurance", "bonus"]
    result = compare_benefits(offered, benchmark)
    assert result["missing"] == ["bonus"]
    assert result["extra"] == ["gym"]


def test_employment_type_advisor() -> None:
    text = "This is a 6 month contract position"
    assert employment_type_advisor(text) == "contract"
    assert employment_type_advisor("Freelance designer needed") == "freelance"


def test_recruitment_checklist() -> None:
    items = recruitment_checklist("Dev")
    assert any("Finalize" in i for i in items)
    assert len(items) >= 5


def test_risk_flagging() -> None:
    job = JobSpec()
    issues = risk_flagging(job)
    assert "Missing job title" in issues
