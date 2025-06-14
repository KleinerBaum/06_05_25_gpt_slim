from __future__ import annotations
import logging
from typing import Any, cast
import openai  # type: ignore
from .llm_utils import call_with_retry
from utils import config

openai = cast(Any, openai)

logger = logging.getLogger(__name__)


def summarize_text(text: str, quality: str = "standard") -> str:
    """Summarize long text blocks using the configured OpenAI model."""
    if not text:
        return ""
    quality_map = {"economy": 0.2, "standard": 0.4, "high": 0.6}
    temperature = quality_map.get(quality, 0.4)
    prompt = (
        "Summarize the following job advertisement text focusing on key duties, "
        "skills and company information:\n" + text
    )
    try:
        response = call_with_retry(
            openai.chat.completions.create,  # type: ignore[attr-defined]
            model=config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as err:
        logger.error("summarize_text failed: %s", err)
        return ""
