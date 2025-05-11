# vacancy_agent.py
# ─────────────────────────────────────────────────────────────────────────────
"""High-level interface for vacancy analysis, delegating to llm_utils."""

from __future__ import annotations
from src import llm_utils

__all__ = ["auto_fill_job_spec"]

def auto_fill_job_spec(input_url: str = "", file_bytes: bytes = None, file_name: str = "", summary_quality: str = "standard") -> dict:
    """Extract structured job information from a URL or file using AI.
    This is a convenience wrapper around llm_utils.extract_job_spec."""
    return llm_utils.extract_job_spec(input_url=input_url, file_bytes=file_bytes, file_name=file_name, summary_quality=summary_quality)
