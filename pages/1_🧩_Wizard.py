import streamlit as st
from utils.session_keys import init_session_state, KEYS
from utils.extraction import extract_text_from_file, match_and_store_keys
from utils.url_fetcher import fetch_url_text
from services.logger import log_event

init_session_state()

step = st.session_state.get("wizard_step", 1)

if step == 1:
    st.title("🧩 Schritt 1 – Discovery")
    job_title = st.text_input("Jobtitel", key="job_title")
    url_input = st.text_input("Stellenanzeige‑URL", key="input_url")
    uploaded_file = st.file_uploader("ODER PDF/TXT hochladen")

    if st.button("Analyse starten"):
        raw_text = ""
        if uploaded_file:
            raw_text = extract_text_from_file(uploaded_file.read(), uploaded_file.name)
            st.session_state["uploaded_text"] = raw_text
        elif url_input:
            raw_text = fetch_url_text(url_input)
            st.session_state["uploaded_text"] = raw_text
        else:
            st.info("Kein Quelltext bereitgestellt – Analyse basiert nur auf Jobtitel.")

        match_and_store_keys(raw_text, st.session_state)
        log_event("analysis_started", {"title": job_title})
        st.session_state["wizard_step"] = 2
        st.rerun()

st.sidebar.write(f"Aktueller Schritt: {step}/8")
