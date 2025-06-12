from __future__ import annotations
import re
import logging
from typing import List

import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Vacancy Agent und Konfiguration importieren
from src.agents import vacancy_agent
from src.config import config

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
    messages = [
        {"role": "system", "content": assistant_prompt},
        {"role": "user", "content": f"List {num_skills} must-have skills for a '{job_title}' position."}
    ]
    try:
        completion = call_with_retry(
            openai.ChatCompletion.create,
            model=config.OPENAI_MODEL,
            messages=messages,
            temperature=0.5,
            max_tokens=200,
        )
    except Exception as e:
        logger.error(f"OpenAI API Fehler bei get_role_skills: {e}")
        return skills_list
    raw_output = completion.choices[0].message.content if completion and completion.choices else ""
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
            line = re.sub(r'^(\d+[\.\)]\s*|[-*\u2022]\s*)', '', line).strip()
            if line:
                skills_list.append(line)
    else:
        parts = [part.strip() for part in raw_output.split(",") if part.strip()]
        skills_list.extend(parts)
    # Auf num_skills Einträge begrenzen
    if len(skills_list) > num_skills:
        skills_list = skills_list[:num_skills]
    return skills_list

# Wrapper-Funktion mit automatischen Wiederholungen für OpenAI-Aufrufe
@retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=4),
       retry=retry_if_exception_type((openai.error.APIConnectionError, openai.error.Timeout, openai.error.RateLimitError, openai.error.APIError)))
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
