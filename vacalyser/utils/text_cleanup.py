"""Utility functions to sanitize text data used across the app."""

from __future__ import annotations

import re

__all__ = ["clean_text"]


def clean_text(text: str) -> str:
    """Normalize whitespace and remove control characters from text.

    Parameters
    ----------
    text: str
        Raw text which may contain irregular line breaks or unwanted
        control characters.

    Returns
    -------
    str
        Cleaned text with at most two consecutive line breaks and
        without control characters.
    """
    if not isinstance(text, str):
        text = str(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]+", "", text)
    return text.strip()
