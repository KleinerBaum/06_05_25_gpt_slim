import io
import streamlit as st
from pdfminer.high_level import extract_text as pdf_extract
import re

LABELS = {
    "Job Title:": "job_title",
    "Company Name:": "company_name",
    "Brand Name:": "brand_name",
    "Headquarters Location:": "headquarters_location",
    "Company Size:": "company_size",
    "Industry Sector:": "industry_sector",
    "Travel Requirements:": "travel_requirements",
}

MAX_CHARS = 15_000


def extract_text_from_file(blob: bytes, filename: str) -> str:
    """PDF‑ oder TXT‑Extraktion."""
    text = (pdf_extract(io.BytesIO(blob)) if filename.lower().endswith(".pdf")
            else blob.decode(errors="ignore"))
    if len(text) > MAX_CHARS:
        st.warning("Text länger als 15 000 Zeichen – gekürzt.")
        text = text[:MAX_CHARS]
    return text


def match_and_store_keys(text: str, session_state):
    """Sucht Labels (regex, case-insensitiv, ':' optional) und füllt leere Felder."""
    for pattern, key in LABELS.items():
        match = re.search(pattern + r"\s*:?\s*(.+)", text, flags=re.IGNORECASE)
        if match and session_state.get(key) in (None, ""):
            # Nimm alles nach dem Label bis zum Zeilenumbruch
            value = match.group(1).split("\n")[0].strip()
            session_state[key] = value
    session_state["parsed_data_raw"] = text
