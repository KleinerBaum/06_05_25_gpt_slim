from __future__ import annotations
import logging
from typing import Any
import openai

from src.config import config
from src.agents.vacancy_agent import USE_LOCAL_MODEL, local_client

def update_salary_range(state: dict[str, Any]) -> None:
    """Schätzt eine angemessene jährliche Gehaltsspanne (EUR) basierend auf Rolle, Standort, Aufgaben und Fähigkeiten."""
    # Abbrechen, falls bereits ein konkreter Gehaltswert (nicht "competitive") gesetzt ist
    current = state.get("salary_range", "")
    if current and str(current).strip().lower() not in {"", "competitive"}:
        return
    role_desc = state.get("job_title", "") or state.get("role_description", "") or "diese Position"
    city = state.get("city", "N/A")
    tasks = state.get("task_list", "-")
    skills = state.get("must_have_skills", "-")
    prompt = (
        "Estimate a fair annual salary range in EUR for the following position in the given city.\n"
        f"Job title: {role_desc}\nCity: {city}\nKey tasks: {tasks}\nMust-have skills: {skills}\n"
        "Answer only in the format \"MIN – MAX EUR\"."
    )
    try:
        if USE_LOCAL_MODEL:
            # Lokales LLM für Schätzung nutzen
            result = local_client.generate(prompt)
        else:
            # OpenAI API aufrufen
            messages = [
                {"role": "system", "content": "You are a labour-market analyst."},
                {"role": "user", "content": prompt}
            ]
            response = openai.ChatCompletion.create(
                model=config.SUGGESTION_MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=40
            )
            result = response.choices[0].message.content.strip()
    except openai.error.APIConnectionError as e:
        logging.error(f"Verbindung zum OpenAI-API fehlgeschlagen: {e}")
        return
    except openai.error.RateLimitError as e:
        logging.error(f"OpenAI Rate-Limit überschritten: {e}")
        return
    except Exception as e:
        logging.error(f"Fehler bei Gehaltsschätzung: {e}")
        return
    if result:
        state["salary_range"] = result
