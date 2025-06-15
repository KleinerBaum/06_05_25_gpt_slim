"""Utility helpers related to language handling."""

from __future__ import annotations


__all__ = ["detect_language"]


def detect_language(text: str) -> str:
    """Detect whether *text* is German or English.

    This simple heuristic checks for common stop words in lowercased text
    and returns ``"de"`` for German or ``"en"`` for English.
    In ambiguous cases English is returned.
    """
    if not isinstance(text, str):
        return "en"
    sample = text.lower()[:500]
    german_score = sample.count(" der ") + sample.count(" die ") + sample.count(" und ")
    english_score = sample.count(" the ") + sample.count(" and ") + sample.count(" of ")
    return "de" if german_score > english_score else "en"
