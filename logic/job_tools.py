"""Utility functions for job-spec processing and analysis."""

from __future__ import annotations
import re
from typing import List

from models.job_models import JobSpec


def parse_job_spec(text: str) -> JobSpec:
    """Parse a raw job ad text using simple regex patterns."""
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
    """Normalize job titles by stripping levels and synonyms."""
    if not title:
        return ""
    title = title.lower()
    title = re.sub(r"senior|jr\.?|junior|lead", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title.title()


def progress_percentage(state: dict[str, object]) -> float:
    """Return completion percentage across all wizard fields."""
    from utils.keys import STEP_KEYS

    total = sum(len(v) for v in STEP_KEYS.values())
    filled = 0
    for fields in STEP_KEYS.values():
        for f in fields:
            if state.get(f):
                filled += 1
    return round(filled / total * 100, 1)


def highlight_keywords(text: str, keywords: List[str]) -> str:
    """Wrap occurrences of keywords with ** for emphasis."""
    if not text or not keywords:
        return text
    pattern = re.compile(r"(" + "|".join(map(re.escape, keywords)) + r")", re.I)
    return pattern.sub(r"**\1**", text)
