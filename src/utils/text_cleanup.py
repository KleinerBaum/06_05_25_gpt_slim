"""Utility functions for cleaning extracted text."""
from __future__ import annotations
import re

__all__ = ["clean_text"]

def clean_text(text: str) -> str:
    """Return a simplified version of *text* with normalised whitespace."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u00A0-\uFFFF]+", "", text)
    return text.strip()
