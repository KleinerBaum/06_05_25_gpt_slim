import requests
import streamlit as st
from bs4 import BeautifulSoup


def fetch_url_text(url: str) -> str:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
    except Exception as exc:
        st.warning(f"URL‑Fehler: {exc}")
        return ""
    soup = BeautifulSoup(r.text, "html.parser")
    return soup.get_text(separator="\n")
