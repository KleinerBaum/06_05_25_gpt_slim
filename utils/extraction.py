import io, re, streamlit as st
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

MAX_CHARS = 15000


def extract_text_from_file(data: bytes, filename: str) -> str:
    """Extrahiert Text aus PDF oder TXT."""
    if filename.lower().endswith(".pdf"):
        text = pdf_extract(io.BytesIO(data))
    else:
        text = data.decode(errors="ignore")
    if len(text) > MAX_CHARS:
        st.warning("Text länger als 15 000 Zeichen – abgeschnitten.")
        text = text[:MAX_CHARS]
    return text


def match_and_store_keys(text: str, session_state):
    """Schreibt erkannte Label nur dann in den Session‑State,
    wenn das Feld noch **nicht** von einem Widget belegt wurde.
    Damit werden Widget‑Key‑Kollisionen vermieden."""
    for label, key in LABELS.items():
        if label in text and session_state.get(key) in (None, ""):
            value = text.split(label, 1)[1].split("
", 1)[0].strip()
            session_state[key] = value
    session_state["parsed_data_raw"] = text
```python
import io, re, streamlit as st
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

MAX_CHARS = 15000


def extract_text_from_file(data: bytes, filename: str) -> str:
    """Extrahiert Text aus PDF oder TXT."""
    if filename.lower().endswith(".pdf"):
        text = pdf_extract(io.BytesIO(data))
    else:
        text = data.decode(errors="ignore")
    if len(text) > MAX_CHARS:
        st.warning("Text länger als 15 000 Zeichen – abgeschnitten.")
        text = text[:MAX_CHARS]
    return text


def match_and_store_keys(text: str, session_state):
    """Schreibt erkannte Label nur dann in den Session‑State,
    wenn das Feld noch **nicht** von einem Widget belegt wurde.
    Das vermeidet den StreamlitAPIException (Änderung eines Widget‑Keys).
    """
    for label, key in LABELS.items():
        if label in text and session_state.get(key) in (None, ""):
            value = text.split(label, 1)[1].split("
", 1)[0].strip()
            session_state[key] = value
    session_state["parsed_data_raw"] = text
    return ""
    soup = BeautifulSoup(r.text, "html.parser")
    return soup.get_text(separator="\n")
