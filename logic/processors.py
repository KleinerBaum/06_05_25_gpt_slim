# processors.py
# ─────────────────────────────────────────────────────────────────────────────
"""Functions to auto-update wizard fields using AI suggestions or logic, and registration of processors."""

from __future__ import annotations
from typing import Any, cast
import logging

from logic.trigger_engine import TriggerEngine
from utils.llm_utils import call_with_retry, openai  # type: ignore

openai = cast(Any, openai)

# Use a fast model for suggestions
_SUGGESTION_MODEL = "gpt-3.5-turbo"


def update_task_list(state: dict[str, Any]) -> None:
    """Auto-generate a general task list from the job title (and industry)."""
    if state.get("task_list"):
        return  # already specified by user
    role = state.get("job_title", "") or state.get("role_description", "")
    industry = state.get("industry_sector", "") or state.get("industry_experience", "")
    if not role:
        return  # no context to generate tasks
    prompt = f"List 5 key tasks or responsibilities for a {role}"
    if industry:
        prompt += f" in the {industry} industry"
    prompt += ".\n- "
    try:
        response = call_with_retry(
            openai.ChatCompletion.create,  # type: ignore[attr-defined]
            model=_SUGGESTION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100,
        )
        tasks_text = response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Task list suggestion failed: {e}")
        return
    if tasks_text:
        state["task_list"] = tasks_text


def update_must_have_skills(state: dict[str, Any]) -> None:
    """Auto-generate must-have skills based on the role (and tasks)."""
    if state.get("must_have_skills"):
        return
    if not state.get("job_title") and not state.get("task_list"):
        return
    role_desc = state.get("job_title", "this role")
    tasks_info = state.get("task_list", "")
    prompt = f"List 5 must-have skills or qualifications for {role_desc}."
    if tasks_info:
        prompt += f" Key tasks: {tasks_info}"
    prompt += "\n- "
    try:
        response = call_with_retry(
            openai.ChatCompletion.create,  # type: ignore[attr-defined]
            model=_SUGGESTION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100,
        )
        skills_text = response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Must-have skills suggestion failed: {e}")
        return
    if skills_text:
        state["must_have_skills"] = skills_text


def update_nice_to_have_skills(state: dict[str, Any]) -> None:
    """Auto-generate nice-to-have skills complementing the must-haves."""
    if state.get("nice_to_have_skills"):
        return
    must = state.get("must_have_skills", "")
    if not must:
        return
    role_desc = state.get("job_title", "this role")
    prompt = f"List 3 nice-to-have skills for {role_desc} (additional beneficial skills beyond the must-haves)."
    if must:
        prompt += f" Must-have skills already listed: {must}"
    prompt += "\n- "
    try:
        response = call_with_retry(
            openai.ChatCompletion.create,  # type: ignore[attr-defined]
            model=_SUGGESTION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=60,
        )
        extra_skills = response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Nice-to-have skills suggestion failed: {e}")
        return
    if extra_skills:
        state["nice_to_have_skills"] = extra_skills


def update_salary_range(state: dict[str, Any]) -> None:
    """Estimate a realistic salary range (EUR) based on role, location, tasks, etc."""
    current = state.get("salary_range", "")
    if current and str(current).strip().lower() not in {"", "competitive"}:
        return  # already set to a specific range
    role_desc = (
        state.get("job_title", "")
        or state.get("role_description", "")
        or "this position"
    )
    city = state.get("city", "N/A")
    tasks = state.get("task_list", "-")
    skills = state.get("must_have_skills", "-")
    prompt = (
        "Estimate a fair annual salary range in EUR for the following position in the given city.\n"
        f"Job title: {role_desc}\nCity: {city}\nKey tasks: {tasks}\nMust-have skills: {skills}\n"
        'Answer only in the format "MIN – MAX EUR".'
    )
    try:
        response = call_with_retry(
            openai.ChatCompletion.create,  # type: ignore[attr-defined]
            model=_SUGGESTION_MODEL,
            messages=[
                {"role": "system", "content": "You are a labour-market analyst."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=40,
        )
        result = response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Salary range estimation failed: {e}")
        return
    if result:
        state["salary_range"] = result


def update_publication_channels(state: dict[str, Any]) -> None:
    """Set recommended publication channels based on remote work policy."""
    raw_policy = state.get("remote_work_policy", "")
    if isinstance(raw_policy, (list, tuple)):
        remote = " ".join(str(v).lower() for v in raw_policy)
    else:
        remote = str(raw_policy).lower()
    if remote in {"hybrid", "full remote"}:
        state["desired_publication_channels"] = "LinkedIn Remote Jobs; WeWorkRemotely"


def update_bonus_scheme(state: dict[str, Any]) -> None:
    """Suggest a bonus scheme for mid-to-senior level roles."""
    if state.get("bonus_scheme"):
        return
    level = str(state.get("job_level", "")).lower()
    if level in {"mid-level", "senior", "director", "c-level", "executive"}:
        state["bonus_scheme"] = "Eligible for an annual performance bonus."


def update_commission_structure(state: dict[str, Any]) -> None:
    """Suggest a commission structure for sales-related roles."""
    if state.get("commission_structure"):
        return
    title = str(state.get("job_title", "")).lower()
    if any(
        term in title
        for term in (
            "sales",
            "business development",
            "account executive",
            "account manager",
        )
    ):
        state["commission_structure"] = "Commission based on sales performance."


def update_translation_required(state: dict[str, Any]) -> None:
    """Determine if a translation is needed based on ad language vs required languages."""
    if not state.get("language_requirements"):
        return
    lang_req = state["language_requirements"].strip()
    ad_lang = state.get("language_of_ad", "").strip() or "English"
    # If the ad's language is not among the required languages, translation is likely needed
    required_languages = {
        lang.strip().lower() for lang in lang_req.split(",") if lang.strip()
    }
    if ad_lang.lower() and ad_lang.lower() not in required_languages:
        state["translation_required"] = "Yes"
    else:
        state["translation_required"] = "No"


def register_all_processors(engine: TriggerEngine) -> None:
    """Register all processor functions with the TriggerEngine."""
    engine.register_processor("task_list", update_task_list)
    engine.register_processor("must_have_skills", update_must_have_skills)
    engine.register_processor("nice_to_have_skills", update_nice_to_have_skills)
    engine.register_processor("salary_range", update_salary_range)
    engine.register_processor(
        "desired_publication_channels", update_publication_channels
    )
    engine.register_processor("bonus_scheme", update_bonus_scheme)
    engine.register_processor("commission_structure", update_commission_structure)
    engine.register_processor("translation_required", update_translation_required)
