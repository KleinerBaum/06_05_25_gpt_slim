"""Additional tool functions for vacancy_agent."""

from __future__ import annotations

from typing import List


def retrieve_esco_skills(
    job_title: str,
    description: str | None = None,
    max_results: int = 15,
    language: str = "en",
) -> List[str]:
    """Return mocked ESCO skills for the given job title."""
    base = job_title.lower().split()[0]
    return [f"{base}_skill_{i}" for i in range(1, max_results + 1)]


def update_salary_range(
    job_title: str,
    location: str,
    seniority: str | None = None,
    currency: str = "EUR",
    spread_pct: float = 10,
) -> str:
    """Return a dummy salary range string."""
    midpoint = 50000
    spread = midpoint * spread_pct / 100
    low = int(midpoint - spread)
    high = int(midpoint + spread)
    return f"{low} – {high} {currency}"


def interview_prep_generator(
    job_spec: str, num_questions: int = 10, language: str = "de"
) -> List[str]:
    """Generate placeholder interview questions."""
    return [
        f"Frage {i}" if language == "de" else f"Question {i}"
        for i in range(1, num_questions + 1)
    ]


def vector_search_candidates(
    query: str, top_k: int = 5, vector_store_id: str | None = None
) -> List[str]:
    """Return dummy candidate profile matches."""
    return [f"candidate_{i}" for i in range(1, top_k + 1)]
