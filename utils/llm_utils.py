from __future__ import annotations
import re
import logging
from typing import Any, List, cast

import openai  # type: ignore
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Vacancy Agent und Konfiguration importieren
from services import vacancy_agent
from utils import config

openai = cast(Any, openai)

# Logger konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_role_skills(job_title: str, num_skills: int = 15) -> List[str]:
    """
    Ermittelt eine Liste der Top-{num_skills} Skills für den gegebenen Jobtitel über OpenAI.
    Gibt eine Liste von Skill-Bezeichnungen zurück.
    """
    job_title = job_title.strip()
    if not job_title:
        return []
    skills_list: List[str] = []
    # Prompt für den Assistant (ggf. vordefiniert) abrufen
    try:
        assistant_prompt = vacancy_agent.SKILLS_ASSISTANT_PROMPT
    except AttributeError:
        assistant_prompt = (
            "You are an expert career advisor. The user will provide a job title. "
            f"List the top {num_skills} must-have skills (technical skills and core competencies) "
            f"that an ideal candidate for the '{job_title}' role should possess. "
            "Provide the list as bullet points or a comma-separated list, without any additional commentary."
        )
    # OpenAI API nutzen
    try:
        completion = call_with_retry(
            openai.responses.create,  # type: ignore[attr-defined]
            model=config.OPENAI_MODEL,
            instructions=assistant_prompt,
            input=f"List {num_skills} must-have skills for a '{job_title}' position.",
            temperature=0.5,
            max_output_tokens=200,
        )
    except Exception as e:
        logger.error(f"OpenAI API Fehler bei get_role_skills: {e}")
        return skills_list
    raw_output = completion.output_text if completion else ""
    raw_output = (raw_output or "").strip()
    # Ergebnis-String in Skills-Liste umwandeln
    if not raw_output:
        return skills_list
    if "\n" in raw_output:
        for line in raw_output.splitlines():
            line = line.strip()
            if not line:
                continue
            # Führende Aufzählungszeichen/Nummern entfernen
            line = re.sub(r"^(\d+[\.\)]\s*|[-*\u2022]\s*)", "", line).strip()
            if line:
                skills_list.append(line)
    else:
        parts = [part.strip() for part in raw_output.split(",") if part.strip()]
        skills_list.extend(parts)
    # Auf num_skills Einträge begrenzen
    if len(skills_list) > num_skills:
        skills_list = skills_list[:num_skills]
    return skills_list


def suggest_additional_skills(
    job_title: str,
    tasks: str = "",
    level: str = "",
    existing: str = "",
    num_skills: int = 30,
) -> dict[str, list[str]]:
    """Generate technical and soft skills not mentioned in the job ad.

    Args:
        job_title: Title of the role.
        tasks: Key tasks or responsibilities.
        level: Seniority level of the role.
        existing: Skills already extracted from the job ad.
        num_skills: Total number of suggestions to return (split in half).

    Returns:
        Dictionary with ``technical`` and ``soft`` skill lists.
    """

    job_title = job_title.strip()
    if not job_title:
        return {"technical": [], "soft": []}

    tech_count = num_skills // 2
    soft_count = num_skills - tech_count
    prompt = (
        f"You are an expert career advisor. Suggest {tech_count} technical skills"
        f" and {soft_count} soft skills for a {level} {job_title} role. "
        "Do not repeat skills from the job ad. "
    )
    if tasks:
        prompt += f" Key tasks: {tasks}."
    if existing:
        prompt += f" Already listed skills: {existing}."
    prompt += (
        " Respond with two sections:\nTechnical Skills:\n- skill1\n- skill2\nSoft "
        "Skills:\n- skillA\n- skillB"
    )

    try:
        resp = call_with_retry(
            openai.responses.create,  # type: ignore[attr-defined]
            model=config.OPENAI_MODEL,
            instructions=None,
            input=prompt,
            temperature=0.4,
            max_output_tokens=200,
        )
        content = resp.output_text or ""
    except Exception as e:  # pragma: no cover - network errors
        logger.error(f"OpenAI API Fehler bei suggest_additional_skills: {e}")
        return {"technical": [], "soft": []}

    tech: list[str] = []
    soft: list[str] = []
    current = None
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("technical skills"):
            current = tech
            continue
        if line.lower().startswith("soft skills"):
            current = soft
            continue
        line = re.sub(r"^(\d+[\.\)]\s*|[-*\u2022]\s*)", "", line)
        if current is not None and line:
            current.append(line)

    return {"technical": tech[:tech_count], "soft": soft[:soft_count]}


# Wrapper-Funktion mit automatischen Wiederholungen für OpenAI-Aufrufe
@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=4),
    retry=retry_if_exception_type(
        (
            openai.APIConnectionError,
            openai.APITimeoutError,
            openai.RateLimitError,
            openai.APIError,
        )
    ),
)
def _call_with_retry(func, *args, **kwargs):
    return func(*args, **kwargs)


def call_with_retry(func, *args, **kwargs):
    """
    Ruft die OpenAI-Funktion *func* mit Retry-Mechanismus auf (wiederholt bei Verbindungs- oder Rate-Limit-Fehlern).
    """
    try:
        return _call_with_retry(func, *args, **kwargs)
    except Exception as e:
        logger.error(f"API-Aufruf fehlgeschlagen nach mehreren Versuchen: {e}")
        raise
