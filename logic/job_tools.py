"""Utility functions for job-spec processing and analysis."""

from __future__ import annotations
import re
from typing import List, TypedDict

from models.job_models import JobSpec


def parse_job_spec(text: str) -> JobSpec:
    """Parse raw job-ad text into a ``JobSpec`` object.

    Args:
        text: Job-ad text to parse.

    Returns:
        A ``JobSpec`` instance populated with title, company and salary if
        detected.
    """
    if not text:
        return JobSpec()
    title_match = re.search(r"(?i)\b(job|position|role)\s*[:\-]\s*(.+)", text)
    company_match = re.search(r"(?i)\b(company|employer)\s*[:\-]\s*(.+)", text)
    salary_match = re.search(
        r"(?i)\b(?:salary|compensation)\s*[:\-]\s*([\w\- ,]+)", text
    )
    return JobSpec(
        job_title=title_match.group(2).strip() if title_match else None,
        company_name=company_match.group(2).strip() if company_match else None,
        salary_range=salary_match.group(1).strip() if salary_match else None,
    )


def normalize_job_title(title: str) -> str:
    """Normalize job titles by removing levels and common prefixes.

    Args:
        title: Original job title string.

    Returns:
        Normalized title in title case.
    """
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"senior|jr\.?|junior|lead", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title.title()


def progress_percentage(state: dict[str, object]) -> float:
    """Return completion percentage across all wizard fields.

    Args:
        state: Current wizard state values.

    Returns:
        Percentage of filled fields rounded to one decimal place.
    """
    from utils.keys import STEP_KEYS

    total = sum(len(v) for v in STEP_KEYS.values())
    filled = 0
    for fields in STEP_KEYS.values():
        for f in fields:
            if state.get(f):
                filled += 1
    return round(filled / total * 100, 1)


def highlight_keywords(text: str, keywords: List[str]) -> str:
    """Emphasize keywords by wrapping them in ``**`` markers.

    Args:
        text: Source text where keywords should be highlighted.
        keywords: List of keywords to highlight.

    Returns:
        Text with keywords wrapped by ``**`` for Markdown emphasis.
    """
    if not text or not keywords:
        return text
    pattern = re.compile(r"(" + "|".join(map(re.escape, keywords)) + r")", re.I)
    return pattern.sub(r"**\1**", text)


def build_boolean_query(job_title: str, skills: List[str]) -> str:
    """Return a simple boolean search string for external candidate platforms."""
    title_part = f'"{normalize_job_title(job_title)}"' if job_title else ""
    skill_terms = [f'"{s}"' for s in skills if s]
    query_parts = [p for p in [title_part, " OR ".join(skill_terms)] if p]
    if len(query_parts) == 1:
        return query_parts[0]
    return f"{query_parts[0]} AND ({query_parts[1]})"


def generate_interview_questions(
    responsibilities: str, num_questions: int = 5
) -> List[str]:
    """Generate basic interview questions from given responsibilities text."""
    if not responsibilities:
        return []
    lines = [
        ln.strip(" -*\u2022") for ln in responsibilities.splitlines() if ln.strip()
    ]
    if not lines:
        lines = [r.strip() for r in re.split(r"[.;]", responsibilities) if r.strip()]
    questions = []
    for item in lines[:num_questions]:
        questions.append(f"Can you describe your experience with {item}?")
    while len(questions) < num_questions:
        questions.append("Tell us more about your relevant experience.")
    return questions


def summarize_job_ad(text: str, max_words: int = 50) -> str:
    """Create a short summary from a job advertisement text."""
    if not text:
        return ""
    words = text.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "..."
    return text


def generate_task_plan(task_list: str) -> dict[str, list[str]]:
    """Split tasks into a basic 30/60/90 day plan.

    Args:
        task_list: Multiline string of role tasks or responsibilities.

    Returns:
        Dict with ``day_30``, ``day_60`` and ``day_90`` lists.
    """

    if not task_list:
        return {"day_30": [], "day_60": [], "day_90": []}

    tasks = [t.strip(" -*\u2022") for t in task_list.splitlines() if t.strip()]
    if not tasks:
        return {"day_30": [], "day_60": [], "day_90": []}

    chunk = max(1, len(tasks) // 3)
    return {
        "day_30": tasks[:chunk],
        "day_60": tasks[chunk : 2 * chunk],
        "day_90": tasks[2 * chunk :],
    }


class SEOResult(TypedDict):
    """Return type for :func:`seo_optimize`."""

    keywords: list[str]
    meta_description: str


def verify_job_level(responsibilities: str, job_level: str) -> bool:
    """Check if given responsibilities match the advertised job level.

    Args:
        responsibilities: Bullet list or paragraph describing duties.
        job_level: Level of the role (e.g. ``junior`` or ``senior``).

    Returns:
        ``True`` if responsibilities appear appropriate for the level.
    """

    if not responsibilities or not job_level:
        return True

    job_level = job_level.lower()
    text = responsibilities.lower()

    senior_terms = ["lead", "strategy", "manage", "mentor", "budget"]

    if job_level.startswith("junior"):
        return not any(term in text for term in senior_terms)

    if job_level.startswith("senior") or job_level in {"lead", "director"}:
        return any(term in text for term in senior_terms)

    return True


def seo_optimize(text: str, max_keywords: int = 5) -> SEOResult:
    """Suggest simple SEO keywords and meta description for a job ad.

    Args:
        text: Full job advertisement text.
        max_keywords: Number of keywords to return.

    Returns:
        Dictionary with ``keywords`` list and ``meta_description`` string.
    """

    if not text:
        return {"keywords": [], "meta_description": ""}

    words = re.findall(r"[A-Za-z]{5,}", text.lower())
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    top_words = sorted(freq, key=lambda w: freq[w], reverse=True)
    keywords = top_words[:max_keywords]

    first_sentence = re.split(r"[.!?]", text.strip())[0]
    meta_desc = (
        first_sentence[:157] + "..." if len(first_sentence) > 160 else first_sentence
    )

    return {"keywords": keywords, "meta_description": meta_desc}


def check_compliance(text: str) -> bool:
    """Return ``True`` if common legal disclaimers are present.

    The function looks for equal opportunity and data protection clauses.

    Args:
        text: Job advertisement text to inspect.

    Returns:
        ``True`` when all clauses appear in ``text``.
    """

    if not text:
        return False
    lower = text.lower()
    has_equal = "equal opportunity" in lower or "m/f/d" in lower
    has_privacy = "data protection" in lower or "gdpr" in lower
    return has_equal and has_privacy


def generate_onboarding_plan(role: str) -> list[str]:
    """Create a basic onboarding checklist for the given role.

    Args:
        role: Title of the position.

    Returns:
        List of onboarding tasks for the first week.
    """

    if not role:
        role = "the new hire"
    return [
        f"Introduce {role} to the team",
        "Set up accounts and access",
        "Explain key processes and tools",
        "Assign a small starter project",
    ]


def compare_benefits(
    offered: list[str], benchmark: list[str] | None = None
) -> dict[str, list[str]]:
    """Compare offered benefits with an optional benchmark list.

    Args:
        offered: Benefits included in the job ad.
        benchmark: Typical industry benefits to compare against.

    Returns:
        Dictionary with ``missing`` and ``extra`` benefit lists.
    """

    offered_set = {b.lower() for b in offered if b}
    benchmark_set = {b.lower() for b in benchmark or []}

    missing = sorted(benchmark_set - offered_set)
    extra = sorted(offered_set - benchmark_set) if benchmark else []

    return {"missing": missing, "extra": extra}


def employment_type_advisor(text: str) -> str:
    """Suggest whether a role is permanent, contract or freelance.

    Args:
        text: Job description or specification.

    Returns:
        Recommended employment type string.
    """

    if not text:
        return "permanent"

    lower = text.lower()
    if any(term in lower for term in ["contract", "project-based", "temporary"]):
        return "contract"
    if "freelance" in lower:
        return "freelance"
    return "permanent"


def recruitment_checklist(role: str) -> list[str]:
    """Return a simple checklist of recruitment steps for the role."""

    if not role:
        role = "the position"
    return [
        f"Finalize description for {role}",
        "Publish job ad on chosen platforms",
        "Screen incoming applications",
        "Schedule interviews",
        "Prepare offer letter",
    ]


def risk_flagging(job: JobSpec) -> list[str]:
    """Highlight missing or inconsistent fields in a ``JobSpec``."""

    issues: list[str] = []
    if not job.job_title:
        issues.append("Missing job title")
    if not job.company_name:
        issues.append("Missing company name")
    if not job.salary_range:
        issues.append("Salary range not specified")
    return issues
