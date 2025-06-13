from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class JobSpec(BaseModel):
    """Simplified vacancy profile used throughout the app."""

    job_title: Optional[str] = None
    company_name: Optional[str] = None
    task_list: Optional[str] = None
    must_have_skills: Optional[str] = None
    nice_to_have_skills: Optional[str] = None
    salary_range: Optional[str] = None
