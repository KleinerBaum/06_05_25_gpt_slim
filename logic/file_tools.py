"""Utilities to extract text from uploaded job-ad files.

This module was formerly located at `src/tools/file_tools.py`.


Robuste Text-Extraktion aus hochgeladenen Stellenanzeigen
(PDF, DOCX, TXT oder generische Binärdatei).

• Dekoriert mit @tool  →  kann direkt im OpenAI-Function-Calling
  eingesetzt werden (siehe vacancy_agent.py).
• Erkennt Dateityp primär über Dateiendung, notfalls über einfache
  Magic-Header-Checks.
• Verwendet PyMuPDF (fitz) für PDF-Seiten, python-docx für DOCX.
• Fällt andernfalls auf UTF-8-/Latin-1-Decode zurück.
• Liefert immer einen **reinen UTF-8-String** (keine Zeilen mit
  mehr als 2 aufeinander­folgenden Leerzeichen).

Benötigte Dependencies (stehen bereits in requirements.txt):
    pymupdf>=1.25.2
    python-docx>=1.1
"""

from __future__ import annotations

import io
import logging
import os
import re
import zipfile
from typing import Literal

import fitz  # PyMuPDF
from docx import Document

from utils.text_cleanup import clean_text

# Optionaler Decorator (funktioniert auch ohne tool_registry)
try:
    from utils.tool_registry import tool
except (ImportError, ModuleNotFoundError):  # Fallback-Decorator

    def tool(_func=None, **_kwargs):  # type: ignore
        def decorator(func):
            return func

        return decorator if _func is None else decorator(_func)


logger = logging.getLogger(__name__)

# --- interne Hilfsfunktionen -------------------------------------------------


def _ext(filename: str) -> str:
    """liefert Dateiendung (ohne Punkt) in Kleinbuchstaben."""
    return os.path.splitext(filename)[1].lower().lstrip(".")


def _extract_text_pdf(data: bytes) -> str:
    """Extrahiert Text aus PDF-Bytes mittels PyMuPDF."""
    text_parts: list[str] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text().strip())
    return "\n".join(text_parts)


def _extract_text_docx(data: bytes) -> str:
    """Extrahiert Text aus DOCX-Bytes ohne Zwischenspeichern auf Platte."""
    # python-docx erwartet einen Dateipfad oder eine Datei-ähnliche BinaryIO
    with io.BytesIO(data) as buf:
        doc = Document(buf)
        text_parts = [p.text for p in doc.paragraphs if p.text]
    return "\n".join(text_parts)


def _extract_text_zip_plain(data: bytes) -> str | None:
    """
    Versucht, aus ZIP-Containern (z. B. OOXML) Klartext-XML zu extrahieren,
    falls python-docx nicht verfügbar ist.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # Suche «word/document.xml»
            for name in zf.namelist():
                if name.endswith("document.xml"):
                    xml_bytes = zf.read(name)
                    # entferne rudimentär XML-Tags
                    xml_text = re.sub(rb"<[^>]+>", b"\n", xml_bytes)
                    return xml_text.decode("utf-8", errors="ignore")
    except Exception:
        pass
    return None


# --- öffentliches Tool -------------------------------------------------------


@tool(
    name="extract_text_from_file",
    description=(
        "Extracts readable UTF-8 text from an uploaded file (job ad). "
        "Supports PDF, DOCX and plain text. "
        "Returns a cleaned text block with maximal 2 consecutive line breaks."
    ),
    return_type="string",
)
def extract_text_from_file(
    file_content: bytes,
    filename: str,
    *,
    preferred_language: Literal["auto", "de", "en"] = "auto",
) -> str:
    """
    Parameters
    ----------
    file_content : bytes
        Die rohen Byte-Daten der Datei.
    filename : str
        Ursprünglicher Dateiname (nur für Endungs-Erkennung).
    preferred_language : {'auto', 'de', 'en'}, default='auto'
        Wird nicht aktiv gefiltert, kann aber in Zukunft für OCR/Language
        Detection genutzt werden.

    Returns
    -------
    str
        Gecleanter UTF-8-Text oder leerer String bei Fehler.
    """
    try:
        ext = _ext(filename)
        if ext == "pdf" or file_content[:5] == b"%PDF-":
            text = _extract_text_pdf(file_content)
        elif ext in {"docx", "doc"}:
            try:
                text = _extract_text_docx(file_content)
            except Exception:
                # Fallback: rohes XML ohne Docx-Lib
                text = _extract_text_zip_plain(file_content) or ""
        else:
            # Plain-Text-Versuch
            text = file_content.decode("utf-8", errors="ignore")
            if not text.strip():  # Fallback Latin-1
                text = file_content.decode("latin-1", errors="ignore")
        return clean_text(text)
    except Exception as err:
        logger.error("extract_text_from_file() failed: %s", err, exc_info=True)
        return ""
