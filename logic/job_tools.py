"""Utility functions for job-spec processing and analysis."""

from __future__ import annotations
import re
from typing import List

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
