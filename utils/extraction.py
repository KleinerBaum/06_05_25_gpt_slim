import io, streamlit as st
from pdfminer.high_level import extract_text as pdf_extract

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
    """Label > Session‑State (nur leere Felder füllen)."""
    for label, key in LABELS.items():
        if label in text and session_state.get(key) in (None, ""):
            value = text.split(label, 1)[1].split("\n", 1)[0].strip()
            session_state[key] = value
    session_state["parsed_data_raw"] = text
