# src/utils/llm_utils.py

from __future__ import annotations
import os
import re
import logging
from typing import List
# Import LLM clients from vacancy_agent
from src.agents import vacancy_agent

# Ensure logger is configured
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_role_skills(job_title: str, num_skills: int = 15) -> List[str]:
    """
    Generate a list of top `num_skills` skills for the given job_title using either OpenAI or local LLM.
    Returns a list of skill strings.
    """
    job_title = job_title.strip()
    if not job_title:
        return []

    # Determine mode from vacancy_agent configuration
    USE_LOCAL = getattr(vacancy_agent, "USE_LOCAL_MODEL", False)

    # Prepare prompt using the predefined assistant prompt
    # Attempt to retrieve the assistant's skill prompt from stored source (e.g., file search or config)
    try:
        # If the assistant prompt is stored in vacancy_agent or elsewhere, use it
        assistant_prompt = vacancy_agent.SKILLS_ASSISTANT_PROMPT
    except AttributeError:
        # Fallback prompt if no stored prompt is found
        assistant_prompt = (
            "You are an expert career advisor. The user will provide a job title. "
            f"List the top {num_skills} must-have skills (technical skills and core competencies) "
            f"that an ideal candidate for the '{job_title}' role should possess. "
            "Provide the list as bullet points or a comma-separated list, without any additional commentary."
        )

    skills_list: List[str] = []

    if USE_LOCAL:
        # Use local Ollama LLM (LLaMA model) for generation
        prompt_text = f"List {num_skills} essential skills required for a {job_title}."
        try:
            response = vacancy_agent.local_client.generate(text=prompt_text)
        except Exception as e:
            logger.error(f"Local LLM error: {e}")
            return skills_list
        raw_output = response.strip()
    else:
        # Use OpenAI API for generation
        openai_client = getattr(vacancy_agent, "openai_client", None)
        if openai_client is None:
            logger.error("OpenAI client is not initialized or API key missing.")
            return skills_list
        # Formulate the messages for OpenAI chat completion
        messages = [
            {"role": "system", "content": assistant_prompt},
            {"role": "user", "content": f"List {num_skills} must-have skills for a '{job_title}' position."}
        ]
        try:
            completion = openai_client.chat.completions.create(
                model="gpt-4", 
                messages=messages,
                temperature=0.5,
                max_tokens=200
            )
        except Exception as e:
            logger.error(f"OpenAI API error while fetching skills: {e}")
            return skills_list
        raw_output = completion.choices[0].message.content if completion and completion.choices else ""
        raw_output = (raw_output or "").strip()

    # Parse the raw output into a list of skills
    if not raw_output:
        return skills_list

    # Split by lines if possible (handles bulleted or numbered lists)
    if "\n" in raw_output:
        for line in raw_output.splitlines():
            line = line.strip()
            if not line:
                continue
            # Remove any leading bullets, numbers, or punctuation
            line = re.sub(r'^(\d+[\.\)]\s*|[-*\u2022]\s*)', '', line).strip()
            if line:
                skills_list.append(line)
    else:
        # If no newlines, perhaps comma-separated
        parts = [part.strip() for part in raw_output.split(",") if part.strip()]
        skills_list.extend(parts)

    # Ensure we only return up to num_skills items
    if len(skills_list) > num_skills:
        skills_list = skills_list[:num_skills]
    return skills_list
