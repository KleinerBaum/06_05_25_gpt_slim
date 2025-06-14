from __future__ import annotations
from collections.abc import MutableMapping
from datetime import date
from typing import Any, cast
import re

import streamlit as st
import requests  # type: ignore
from streamlit_sortables import sort_items

# Vacalyser-Module und Utilities importieren
from state.session_state import initialize_session_state
from logic.trigger_engine import TriggerEngine, build_default_graph
from logic.file_tools import extract_text_from_file
from services.scraping_tools import scrape_company_site
from utils.text_cleanup import clean_text
from utils.keys import STEP_KEYS
from services.vacancy_agent import auto_fill_job_spec
from logic.job_tools import (
    normalize_job_title,
    progress_percentage,
    highlight_keywords,
)
from utils.llm_utils import suggest_additional_skills
from utils import config

# Session State initialisieren (nur beim ersten Aufruf)
initialize_session_state()


def update_language() -> None:
    """Synchronize UI language with the global setting on each run."""
    if "language" in st.session_state:
        st.session_state["lang"] = (
            "Deutsch" if st.session_state["language"] == "Deutsch" else "English"
        )


# Set the language immediately on import so subsequent functions can use it
update_language()


def _ensure_engine() -> TriggerEngine:
    """Initialisiert die TriggerEngine mit Standard-Graph und Prozessoren (einmal pro Session)."""
    eng: TriggerEngine | None = st.session_state.get("trigger_engine")
    if eng is None:
        eng = TriggerEngine()
        build_default_graph(eng)
        st.session_state["trigger_engine"] = eng
    return eng


def _clamp_step() -> int:
    """Begrenzt den aktuellen wizard_step auf einen Wert zwischen 1 und 8."""
    st.session_state["wizard_step"] = max(1, min(8, _int_from_state("wizard_step", 1)))
    return st.session_state["wizard_step"]


def _int_from_state(key: str, default: int) -> int:
    """Safely parse an int from session state or return the default."""
    val = st.session_state.get(key)
    try:
        return default if val is None else int(val)
    except (TypeError, ValueError):
        return default


def _date_from_state(key: str) -> date | None:
    """Return a ``date`` from session state if possible."""
    val = st.session_state.get(key)
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val)
        except ValueError:
            return None
    return None


def fetch_url_text(url: str) -> str:
    """Holt den Inhalt der gegebenen URL und liefert bereinigten Text zurück."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        st.warning(f"Failed to fetch URL: {exc}")
        return ""
    content_type = resp.headers.get("content-type", "").lower()
    if "text/html" in content_type:
        data = scrape_company_site(url)
        if isinstance(data, dict):
            text = (
                (data.get("title", "") or "")
                + "\n"
                + (data.get("description", "") or "")
            )
        else:
            text = str(data)
    elif "pdf" in content_type:
        text = extract_text_from_file(resp.content, "file.pdf")
    elif "officedocument" in content_type or "msword" in content_type:
        text = extract_text_from_file(resp.content, "file.docx")
    else:
        text = resp.text
    return clean_text(text or "")


def match_and_store_keys(
    raw_text: str, state: MutableMapping[str, Any] | None = None
) -> None:
    """Parse labeled lines and store values in ``state`` if missing.

    This fallback parser looks for simple ``"Label: value"`` patterns in the
    provided text. It only sets a field when the current value is falsy so that
    manually entered or AI‑generated values are not overwritten.
    """

    if not raw_text:
        return

    if state is None:
        state = cast(MutableMapping[str, Any], st.session_state)

    labels = {
        "job_title": "Job Title:",
        "company_name": "Company Name:",
        "brand_name": "Brand Name:",
        "headquarters_location": "HQ Location:",
        "company_website": "Company Website:",
        "date_of_employment_start": "Date of Employment Start:",
        "job_type": "Job Type:",
        "contract_type": "Contract Type:",
        "job_level": "Job Level:",
        "city": "City",  # "City (Job Location):" manchmal abgekürzt
        "team_structure": "Team Structure:",
        "role_description": "Role Description:",
        "reports_to": "Reports To:",
        "supervises": "Supervises:",
        "role_type": "Role Type:",
        "role_priority_projects": "Role Priority Projects:",
        "travel_requirements": "Travel Requirements:",
        "must_have_skills": "Requirements:",
        "nice_to_have_skills": "Preferred Skills:",
    }

    for key, label in labels.items():
        if state.get(key):
            continue
        clean_label = label.rstrip(":")
        pattern = re.compile(
            rf"{re.escape(clean_label)}\s*[:\-]?\s*(.+)", re.IGNORECASE
        )
        match = pattern.search(raw_text)
        if match:
            value = match.group(1).split("\n", 1)[0].strip(" :;,.\t")
            if value:
                state[key] = value


def display_step_summary(step: int) -> None:
    """Zeigt eine ausklappbare Zusammenfassung aller bisher ausgefüllten Felder und listet fehlende Felder im aktuellen Schritt auf."""
    lang = st.session_state.get("lang", "English")
    filled = {}
    for s in range(1, step + 1):
        for field in STEP_KEYS[s]:
            if field in [
                "input_url",
                "uploaded_file",
                "parsed_data_raw",
                "source_language",
            ]:
                continue
            val = st.session_state.get(field)
            if val not in (None, "", []):
                filled[field] = val
    missing_fields = [
        f
        for f in STEP_KEYS[step]
        if f not in ["input_url", "uploaded_file", "parsed_data_raw", "source_language"]
        and not st.session_state.get(f)
    ]
    if filled:
        exp_label = (
            "Zusammenfassung ausgefüllter Felder"
            if lang == "Deutsch"
            else "Summary of Filled Fields"
        )
        with st.expander(exp_label, expanded=False):
            # Gruppiere Zusammenfassung nach Schritten
            for s in range(1, step + 1):
                section_fields = [
                    f
                    for f in STEP_KEYS[s]
                    if f
                    not in [
                        "input_url",
                        "uploaded_file",
                        "parsed_data_raw",
                        "source_language",
                    ]
                ]
                section_filled = {
                    k: v for k, v in filled.items() if k in section_fields
                }
                if not section_filled:
                    continue
                st.markdown(f"**Step {s}:**")
                for k, v in section_filled.items():
                    st.write(f"- **{k}**: {v}")
    if missing_fields:
        warn_label = (
            "Noch auszufüllende Felder in diesem Schritt:"
            if lang == "Deutsch"
            else "Missing fields in this step:"
        )
        st.warning(warn_label + " " + ", ".join(missing_fields))


def start_discovery_page():
    """Render the first step of the wizard where users provide job details."""
    # Schritt 1: Einstieg (Jobtitel/Quelle eingeben)
    lang = st.session_state.get("lang", "English")
    if lang == "Deutsch":
        st.title("🚀 Spitzenkräfte gewinnen – mit RoleCraft")
        st.subheader("Vom ersten Konzept zur unwiderstehlichen Anzeige")
        intro_text = (
            "Willkommen bei **RoleCraft**.\n\n"
            "Starten Sie mit einem Jobtitel oder laden Sie Ihre aktuelle Anzeige hoch.\n"
            "Unsere KI veredelt jedes Detail und liefert Ihnen blitzschnell ein perfektes Anforderungsprofil."
        )
        btn_job = "➕ Jobtitel eingeben"
        btn_upload = "📂 PDF / DOCX hochladen"
    else:
        st.title("🚀 Attract Top Talent with RoleCraft")
        st.subheader("From concept to irresistible job ad")
        intro_text = (
            "Welcome to **RoleCraft**.\n\n"
            "Begin with a job title or upload your existing posting.\n"
            "Our AI instantly enriches every detail so you can present an outstanding role profile."
        )
        btn_job = "➕ Enter Job Title"
        btn_upload = "📂 Upload PDF / DOCX"
    st.markdown(intro_text)
    prog = progress_percentage(st.session_state)
    st.progress(prog / 100.0, text=f"{prog}% complete")
    col1, col2 = st.columns(2)
    with col1:
        job_title = st.text_input(
            btn_job,
            value=st.session_state.get("job_title", ""),
            placeholder=(
                "z.B. Senior Data Scientist"
                if lang == "Deutsch"
                else "e.g. Senior Data Scientist"
            ),
        )
        if job_title:
            st.session_state["job_title"] = normalize_job_title(job_title)
        input_url = st.text_input(
            (
                "🔗 Stellenanzeigen-URL (optional)"
                if lang == "Deutsch"
                else "🔗 Job Ad URL (optional)"
            ),
            value=st.session_state.get("input_url", ""),
        )
        if input_url:
            st.session_state["input_url"] = input_url
        company_url = st.text_input(
            (
                "🌐 Unternehmenswebseite (optional)"
                if lang == "Deutsch"
                else "🌐 Company Website (optional)"
            ),
            value=st.session_state.get("company_website", ""),
        )
        if company_url:
            st.session_state["company_website"] = company_url
    with col2:
        uploaded_file = st.file_uploader(btn_upload, type=["pdf", "docx", "txt"])
        if uploaded_file is not None:
            file_bytes = uploaded_file.read()
            raw_text = extract_text_from_file(file_bytes, uploaded_file.name)
            raw_text = clean_text(raw_text)
            if raw_text:
                st.session_state["uploaded_file"] = raw_text
                st.success(
                    "✅ Datei hochgeladen und Text extrahiert."
                    if lang == "Deutsch"
                    else "✅ File uploaded and text extracted."
                )
            else:
                st.error(
                    "❌ Konnte den Text aus der Datei nicht extrahieren."
                    if lang == "Deutsch"
                    else "❌ Failed to extract text from the uploaded file."
                )
    analyze_clicked = st.button(
        "🔎 Analysieren" if lang == "Deutsch" else "🔎 Analyze Sources"
    )
    if analyze_clicked:
        raw_text = ""
        if st.session_state.get("uploaded_file"):
            raw_text = st.session_state["uploaded_file"]
        elif st.session_state.get("input_url"):
            raw_text = fetch_url_text(st.session_state["input_url"])
        if not raw_text:
            st.warning(
                "⚠️ Bitte gib eine gültige URL oder lade eine Datei hoch."
                if lang == "Deutsch"
                else "⚠️ Please provide a valid URL or upload a file."
            )
            return
        if st.session_state.get("company_website"):
            info = scrape_company_site(st.session_state["company_website"])
            st.session_state["company_site_title"] = info.get("title", "")
            st.session_state["company_site_description"] = info.get("description", "")
            if info.get("title") or info.get("description"):
                with st.expander(
                    (
                        "Gefundene Unternehmensinfos"
                        if lang == "Deutsch"
                        else "Fetched Company Info"
                    ),
                    expanded=False,
                ):
                    if info.get("title"):
                        st.write(f"**Title:** {info['title']}")
                    if info.get("description"):
                        st.write(f"**Description:** {info['description']}")
        if not config.OPENAI_API_KEY:
            st.error(
                "❌ KI-Funktionen nicht verfügbar. Bitte OPENAI_API_KEY konfigurieren."
                if lang == "Deutsch"
                else "❌ AI features are disabled. Set OPENAI_API_KEY in your environment or Streamlit secrets."
            )
            match_and_store_keys(raw_text)
            return
        # Sprache der Quelle grob erkennen (Deutsch vs. Englisch)
        sample = raw_text[:500].lower()
        if sample.count(" der ") + sample.count(" die ") + sample.count(
            " und "
        ) > sample.count(" the "):
            st.session_state["source_language"] = "Deutsch"
        else:
            st.session_state["source_language"] = "English"
        # Rohtext im Session State speichern & KI-Analyse durchführen
        st.session_state["parsed_data_raw"] = raw_text
        try:
            result = auto_fill_job_spec(
                input_url=st.session_state.get("input_url", ""),
                file_bytes=raw_text.encode("utf-8") if raw_text else None,
                file_name=uploaded_file.name if uploaded_file else "",
                summary_quality="standard",
            )
            if result:
                # Automatisch ausgefüllte Felder in Session State übernehmen
                for key, value in result.items():
                    if key in st.session_state and value not in (None, ""):
                        if isinstance(value, list):
                            st.session_state[key] = "\n".join(
                                str(v) for v in value if v
                            )
                        else:
                            st.session_state[key] = value
                # TriggerEngine benachrichtigen, damit abhängige Felder berechnet werden
                for k in result.keys():
                    _ensure_engine().notify_change(k, dict(st.session_state))
                # Ergänze fehlende Felder über einfache Label-Erkennung
                match_and_store_keys(raw_text)
                skills = (st.session_state.get("must_have_skills") or "").split("\n")
                highlighted = highlight_keywords(raw_text, skills)
                with st.expander(
                    (
                        "Keyword Highlights"
                        if lang != "Deutsch"
                        else "Wichtige Stichworte"
                    ),
                    expanded=False,
                ):
                    st.write(highlighted)
                st.success(
                    "🎯 Analyse abgeschlossen! Wichtige Felder wurden automatisch ausgefüllt."
                    if lang == "Deutsch"
                    else "🎯 Analysis complete! Key details have been auto-filled."
                )
            else:
                # KI-Parsing lieferte nichts -> Fallback mittels Stichwort-Suche
                match_and_store_keys(raw_text)
                st.info(
                    "⚠️ KI-Analyse nicht verfügbar – wichtige Felder anhand von Schlagworten ausgefüllt."
                    if lang == "Deutsch"
                    else "⚠️ AI extraction not available – applied basic extraction for key fields."
                )
            st.session_state.setdefault("trace_events", []).append(
                "Auto-extracted fields from provided job description."
            )
        except Exception as e:
            st.error(
                f"❌ Analyse fehlgeschlagen: {e}"
                if lang == "Deutsch"
                else f"❌ Analysis failed: {e}"
            )


def _handle_static_step(step: int, render_func):
    """Verarbeitet einen statischen Schritt: Speichert Eingaben und aktualisiert abhängige Felder."""
    lang = st.session_state.get("lang", "English")
    render_vals = render_func()
    # Eingegebene Werte speichern und TriggerEngine benachrichtigen
    for k, v in render_vals.items():
        st.session_state[k] = v
        _ensure_engine().notify_change(k, dict(st.session_state))
    # Zusammenfassung der bisher ausgefüllten Felder anzeigen
    display_step_summary(step)
    # Button zum nächsten Schritt
    if st.button(
        "Weiter zu Schritt {}".format(step + 1)
        if lang == "Deutsch"
        else "Continue to Step {}".format(step + 1)
    ):
        st.session_state["wizard_step"] = step + 1


# Schritte 2–7: Formulareingaben
def render_step2_static():
    lang = st.session_state.get("lang", "English")
    st.title(
        "Schritt 2: Grundlegende Stellen- & Firmendaten"
        if lang == "Deutsch"
        else "Step 2: Basic Job & Company Info"
    )
    display_step_summary(2)
    company_name = st.text_input(
        "Unternehmensname" if lang == "Deutsch" else "Company Name",
        value=st.session_state.get("company_name", ""),
        placeholder=(
            "z.B. Tech Corp GmbH" if lang == "Deutsch" else "e.g. Tech Corp Ltd."
        ),
        help=(
            "Name des einstellenden Unternehmens."
            if lang == "Deutsch"
            else "Official name of the hiring company."
        ),
    )
    brand_name = st.text_input(
        (
            "Markenname (falls abweichend)"
            if lang == "Deutsch"
            else "Brand Name (if different)"
        ),
        value=st.session_state.get("brand_name", ""),
        placeholder=(
            "z.B. Mutterfirma AG" if lang == "Deutsch" else "e.g. Parent Company Inc."
        ),
        help=(
            "Falls unter einem anderen Marken- oder Firmennamen ausgeschrieben."
            if lang == "Deutsch"
            else "If the job is advertised under a different brand or subsidiary name."
        ),
    )
    headquarters_location = st.text_input(
        "Hauptsitz (Ort)" if lang == "Deutsch" else "Headquarters Location",
        value=st.session_state.get("headquarters_location", ""),
        placeholder=(
            "z.B. Berlin, Deutschland" if lang == "Deutsch" else "e.g. Berlin, Germany"
        ),
        help=(
            "Stadt und Land des Firmensitzes."
            if lang == "Deutsch"
            else "City and country of the company's headquarters."
        ),
    )
    company_website = st.text_input(
        "Webseite des Unternehmens" if lang == "Deutsch" else "Company Website",
        value=st.session_state.get("company_website", ""),
        placeholder=(
            "z.B. https://firma.de" if lang == "Deutsch" else "e.g. https://company.com"
        ),
    )
    exact_known = st.toggle(
        "Exaktes Datum?" if lang == "Deutsch" else "Exact date?",
        value=_date_from_state("date_of_employment_start") is not None,
    )
    if exact_known:
        default_date = _date_from_state("date_of_employment_start") or date.today()
        date_of_start = st.date_input(
            (
                "Bevorzugtes Eintrittsdatum"
                if lang == "Deutsch"
                else "Preferred Start Date"
            ),
            value=default_date,
        ).isoformat()
    else:
        date_of_start = st.text_input(
            (
                "Bevorzugtes Eintrittsdatum"
                if lang == "Deutsch"
                else "Preferred Start Date"
            ),
            value=st.session_state.get("date_of_employment_start", ""),
            placeholder=(
                "z.B. ab sofort oder 2025-01-15"
                if lang == "Deutsch"
                else "e.g. ASAP or 2025-01-15"
            ),
        )
    job_type = st.selectbox(
        "Art der Stelle" if lang == "Deutsch" else "Job Type",
        ["Full-Time", "Part-Time", "Internship", "Freelance", "Volunteer", "Other"],
        index=0,
    )
    contract_type = st.selectbox(
        "Vertragsart" if lang == "Deutsch" else "Contract Type",
        ["Permanent", "Fixed-Term", "Contract", "Other"],
        index=0,
    )
    job_level = st.selectbox(
        "Karrierestufe" if lang == "Deutsch" else "Job Level",
        ["Entry-level", "Mid-level", "Senior", "Director", "C-level", "Other"],
        index=0,
    )
    city = st.text_input(
        "Dienstort (Stadt)" if lang == "Deutsch" else "City (Job Location)",
        value=st.session_state.get("city", ""),
        placeholder="z.B. München" if lang == "Deutsch" else "e.g. London",
    )
    team_structure = st.text_area(
        "Teamstruktur" if lang == "Deutsch" else "Team Structure",
        value=st.session_state.get("team_structure", ""),
        placeholder=(
            "Beschreibe den Teamaufbau, Berichtslinien, etc."
            if lang == "Deutsch"
            else "Describe the team setup, reporting hierarchy, etc."
        ),
    )
    return {
        "company_name": company_name,
        "brand_name": brand_name,
        "headquarters_location": headquarters_location,
        "company_website": company_website,
        "date_of_employment_start": date_of_start,
        "job_type": job_type,
        "contract_type": contract_type,
        "job_level": job_level,
        "city": city,
        "team_structure": team_structure,
    }


def render_step3_static():
    lang = st.session_state.get("lang", "English")
    company = st.session_state.get("company_name", "")
    job_title = st.session_state.get("job_title", "")
    if lang == "Deutsch":
        title = f"Schritt 3: {job_title or 'Rollenbeschreibung'}"
        if company:
            title += f" – {company}"
    else:
        title = f"Step 3: {job_title or 'Role Definition'}"
        if company:
            title += f" – {company}"
    st.title(title)
    display_step_summary(3)
    role_description = st.text_area(
        "Rollenbeschreibung" if lang == "Deutsch" else "Role Description",
        value=st.session_state.get("role_description", ""),
        placeholder=(
            "Kurzer Überblick über die Rolle."
            if lang == "Deutsch"
            else "High-level summary of the role."
        ),
    )
    reports_to = st.text_input(
        "Berichtet an" if lang == "Deutsch" else "Reports To",
        value=st.session_state.get("reports_to", ""),
        placeholder=(
            "Position, an die diese Rolle berichtet"
            if lang == "Deutsch"
            else "Position this role reports to"
        ),
    )
    supervises = st.text_area(
        "Verantwortet (führt)" if lang == "Deutsch" else "Supervises",
        value=st.session_state.get("supervises", ""),
        placeholder=(
            "Liste der Positionen/Teams, für die diese Rolle verantwortlich ist"
            if lang == "Deutsch"
            else "List positions or teams this role supervises"
        ),
    )
    role_type = st.selectbox(
        "Rollentyp" if lang == "Deutsch" else "Role Type",
        [
            "Individual Contributor",
            "Team Lead",
            "Manager",
            "Director",
            "Executive",
            "Other",
        ],
        index=0,
    )
    role_priority_projects = st.text_area(
        "Priorisierte Projekte" if lang == "Deutsch" else "Priority Projects",
        value=st.session_state.get("role_priority_projects", ""),
        placeholder=(
            "Aktuell wichtige Projekte oder Initiativen."
            if lang == "Deutsch"
            else "Current key projects or initiatives for this role."
        ),
    )
    travel_requirements = st.text_input(
        "Reisebereitschaft" if lang == "Deutsch" else "Travel Requirements",
        value=st.session_state.get("travel_requirements", ""),
        placeholder=(
            "z.B. 20% Reisetätigkeit"
            if lang == "Deutsch"
            else "e.g. Up to 20% travel required"
        ),
    )
    return {
        "role_description": role_description,
        "reports_to": reports_to,
        "supervises": supervises,
        "role_type": role_type,
        "role_priority_projects": role_priority_projects,
        "travel_requirements": travel_requirements,
    }


def render_step4_static():
    lang = st.session_state.get("lang", "English")
    st.title(
        "Schritt 4: Aufgaben & Verantwortlichkeiten"
        if lang == "Deutsch"
        else "Step 4: Tasks & Responsibilities"
    )
    display_step_summary(4)
    task_list = st.text_area(
        "Aufgabenliste" if lang == "Deutsch" else "Task List",
        value=st.session_state.get("task_list", ""),
        placeholder=(
            "Liste der Kernaufgaben oder Zuständigkeiten."
            if lang == "Deutsch"
            else "List of key tasks or responsibilities."
        ),
    )
    key_responsibilities = st.text_area(
        "Hauptverantwortlichkeiten" if lang == "Deutsch" else "Key Responsibilities",
        value=st.session_state.get("key_responsibilities", ""),
        placeholder=(
            "z.B. Projektleitung, Teamkoordination"
            if lang == "Deutsch"
            else "e.g. Project management, team coordination"
        ),
    )
    if st.button("30/60/90-Plan" if lang == "Deutsch" else "30/60/90 Plan"):
        from logic.job_tools import generate_task_plan

        plan = generate_task_plan(task_list or key_responsibilities)
        with st.expander("30/60/90 Plan", expanded=True):
            for label, items in plan.items():
                st.markdown(f"**{label.replace('_', '/')}**")
                for it in items:
                    st.write(f"- {it}")
    return {"task_list": task_list, "key_responsibilities": key_responsibilities}


def render_step5_static():
    lang = st.session_state.get("lang", "English")
    st.title(
        "Schritt 5: Fähigkeiten & Kompetenzen"
        if lang == "Deutsch"
        else "Step 5: Skills & Competencies"
    )
    display_step_summary(5)

    if st.button(
        "Top-Skills vorschlagen" if lang == "Deutsch" else "Suggest Top Skills"
    ):
        suggestions = suggest_additional_skills(
            st.session_state.get("job_title", ""),
            st.session_state.get("task_list", ""),
            st.session_state.get("job_level", ""),
            (st.session_state.get("must_have_skills") or "")
            + "\n"
            + (st.session_state.get("nice_to_have_skills") or ""),
        )
        st.session_state["suggested_technical"] = suggestions["technical"]
        st.session_state["suggested_soft"] = suggestions["soft"]

    if st.session_state.get("suggested_technical") or st.session_state.get(
        "suggested_soft"
    ):
        col_a, col_b = st.columns(2)
        with col_a:
            selected_tech = st.multiselect(
                "Technical Skills",
                options=st.session_state.get("suggested_technical", []),
                key="select_tech",
            )
            if st.button("Zu Muss", key="add_tech"):
                for skill in selected_tech:
                    st.session_state.setdefault("must_have_skills_list", []).append(
                        skill
                    )
                st.session_state["select_tech"] = []
        with col_b:
            selected_soft = st.multiselect(
                "Soft Skills",
                options=st.session_state.get("suggested_soft", []),
                key="select_soft",
            )
            if st.button("Zu Nice", key="add_soft"):
                for skill in selected_soft:
                    st.session_state.setdefault("nice_to_have_skills_list", []).append(
                        skill
                    )
                st.session_state["select_soft"] = []

    st.write(
        "Ziehe deine eingegebenen Fähigkeiten einfach zwischen die Spalten"
        if lang == "Deutsch"
        else "Drag your skills between the columns below."
    )

    st.text_input(
        "Neuen Skill hinzufügen" if lang == "Deutsch" else "Add new skill",
        key="skill_input",
    )
    st.checkbox(
        "Zu Muss" if lang == "Deutsch" else "To Must-Have",
        value=True,
        key="add_to_must",
    )

    def _add_skill() -> None:
        if not st.session_state.get("skill_input"):
            return
        target = (
            "must_have_skills_list"
            if st.session_state.get("add_to_must", True)
            else "nice_to_have_skills_list"
        )
        st.session_state.setdefault(target, []).append(st.session_state["skill_input"])
        st.session_state["skill_input"] = ""

    st.button(
        "Skill speichern" if lang == "Deutsch" else "Save skill",
        on_click=_add_skill,
    )

    must_list = st.session_state.get("must_have_skills_list", [])
    nice_list = st.session_state.get("nice_to_have_skills_list", [])

    sorted_lists = sort_items(
        [
            {
                "header": "Muss" if lang == "Deutsch" else "Must-Have",
                "items": must_list,
            },
            {"header": "Nice-to-Have", "items": nice_list},
        ],
        multi_containers=True,
    )

    st.session_state["must_have_skills_list"] = sorted_lists[0]["items"]
    st.session_state["nice_to_have_skills_list"] = sorted_lists[1]["items"]

    must_have_skills = "\n".join(st.session_state["must_have_skills_list"])
    nice_to_have_skills = "\n".join(st.session_state["nice_to_have_skills_list"])
    certifications_required = st.text_input(
        "Erforderliche Zertifikate" if lang == "Deutsch" else "Certifications Required",
        value=st.session_state.get("certifications_required", ""),
        placeholder="z.B. PMP, CFA" if lang == "Deutsch" else "e.g. PMP, CFA",
    )
    language_requirements = st.text_input(
        "Sprachkenntnisse" if lang == "Deutsch" else "Language Requirements",
        value=st.session_state.get("language_requirements", ""),
        placeholder=(
            "z.B. Fließend Deutsch und Englisch"
            if lang == "Deutsch"
            else "e.g. Fluent in German and English"
        ),
    )
    return {
        "must_have_skills": must_have_skills,
        "nice_to_have_skills": nice_to_have_skills,
        "certifications_required": certifications_required,
        "language_requirements": language_requirements,
    }


def render_step6_static():
    lang = st.session_state.get("lang", "English")
    job_title = st.session_state.get("job_title", "")
    if lang == "Deutsch":
        title = "Schritt 6: Vergütung & Benefits"
        if job_title:
            title += f" – {job_title}"
    else:
        title = "Step 6: Compensation & Benefits"
        if job_title:
            title += f" – {job_title}"
    st.title(title)
    display_step_summary(6)
    salary_range = st.text_input(
        "Gehaltsrahmen" if lang == "Deutsch" else "Salary Range",
        value=st.session_state.get("salary_range", ""),
        placeholder=(
            "z.B. 50.000 – 60.000 EUR"
            if lang == "Deutsch"
            else "e.g. 50,000 – 60,000 EUR"
        ),
    )
    currency = st.text_input(
        "Währung" if lang == "Deutsch" else "Currency",
        value=st.session_state.get("currency", ""),
        placeholder="z.B. EUR" if lang == "Deutsch" else "e.g. EUR",
    )
    pay_frequency = st.text_input(
        "Zahlungsintervall" if lang == "Deutsch" else "Pay Frequency",
        value=st.session_state.get("pay_frequency", ""),
        placeholder="z.B. jährlich" if lang == "Deutsch" else "e.g. annual",
    )
    bonus_scheme = st.text_input(
        "Bonusregelung" if lang == "Deutsch" else "Bonus Scheme",
        value=st.session_state.get("bonus_scheme", ""),
        placeholder=(
            "z.B. Teilnahme am jährlichen Bonusprogramm"
            if lang == "Deutsch"
            else "e.g. Eligible for annual performance bonus"
        ),
    )
    commission_structure = st.text_input(
        "Provisionsmodell" if lang == "Deutsch" else "Commission Structure",
        value=st.session_state.get("commission_structure", ""),
        placeholder=(
            "z.B. Umsatzabhängige Provision"
            if lang == "Deutsch"
            else "e.g. Commission based on sales performance"
        ),
    )
    vacation_days = st.slider(
        "Urlaubstage" if lang == "Deutsch" else "Vacation Days",
        20,
        40,
        _int_from_state("vacation_days", 30),
    )
    vacation_days_str = str(vacation_days)
    remote_possible = st.toggle(
        "Remote-Arbeit möglich?" if lang == "Deutsch" else "Remote work possible?",
        value=str(st.session_state.get("remote_work_policy", "")).lower()
        in ("ja", "yes", "true"),
    )
    remote_work_policy = (
        "Ja"
        if remote_possible and lang == "Deutsch"
        else ("Yes" if remote_possible else "No")
    )
    flexible_hours = st.text_input(
        "Flexible Arbeitszeiten" if lang == "Deutsch" else "Flexible Hours",
        value=st.session_state.get("flexible_hours", ""),
        placeholder=(
            "z.B. Ja (Gleitzeit möglich)"
            if lang == "Deutsch"
            else "e.g. Yes (flexible schedule)"
        ),
    )
    relocation_possible = st.toggle(
        "Umzugsunterstützung?" if lang == "Deutsch" else "Relocation assistance?",
        value=str(st.session_state.get("relocation_assistance", "")).lower()
        in ("ja", "yes", "true"),
    )
    relocation_assistance = (
        "Ja"
        if relocation_possible and lang == "Deutsch"
        else ("Yes" if relocation_possible else "No")
    )
    return {
        "salary_range": salary_range,
        "currency": currency,
        "pay_frequency": pay_frequency,
        "bonus_scheme": bonus_scheme,
        "commission_structure": commission_structure,
        "vacation_days": vacation_days_str,
        "remote_work_policy": remote_work_policy,
        "flexible_hours": flexible_hours,
        "relocation_assistance": relocation_assistance,
    }


def render_step7_static():
    lang = st.session_state.get("lang", "English")
    st.title(
        "Schritt 7: Recruiting-Prozess"
        if lang == "Deutsch"
        else "Step 7: Recruitment Process"
    )
    display_step_summary(7)
    recruitment_contact_email = st.text_input(
        "Kontakt-Email" if lang == "Deutsch" else "Recruitment Contact Email",
        value=st.session_state.get("recruitment_contact_email", ""),
        placeholder="z.B. hr@firma.de" if lang == "Deutsch" else "e.g. hr@company.com",
    )
    recruitment_steps = st.text_area(
        "Ablauf der Bewerbungsrunden" if lang == "Deutsch" else "Recruitment Steps",
        value=st.session_state.get("recruitment_steps", ""),
        placeholder=(
            "Beschreibung des Auswahlverfahrens"
            if lang == "Deutsch"
            else "Description of the interview/application steps"
        ),
    )
    recruitment_timeline = st.text_input(
        "Geplanter Zeitrahmen" if lang == "Deutsch" else "Recruitment Timeline",
        value=st.session_state.get("recruitment_timeline", ""),
        placeholder=(
            "z.B. 6 Wochen bis zur Einstellung"
            if lang == "Deutsch"
            else "e.g. 6 weeks from first interview to offer"
        ),
    )
    number_of_interviews = st.slider(
        "Anzahl der Interviews" if lang == "Deutsch" else "Number of Interviews",
        1,
        10,
        _int_from_state("number_of_interviews", 3),
    )
    number_of_interviews_str = str(number_of_interviews)
    interview_format = st.text_input(
        "Interview-Format" if lang == "Deutsch" else "Interview Format",
        value=st.session_state.get("interview_format", ""),
        placeholder=(
            "z.B. Videokonferenz" if lang == "Deutsch" else "e.g. Video conference"
        ),
    )
    assessment_tests = st.text_input(
        "Einstellungstests" if lang == "Deutsch" else "Assessment Tests",
        value=st.session_state.get("assessment_tests", ""),
        placeholder=(
            "z.B. Programmieraufgabe, Präsentation"
            if lang == "Deutsch"
            else "e.g. Coding challenge, presentation"
        ),
    )
    onboarding_process_overview = st.text_area(
        "Onboarding-Prozess" if lang == "Deutsch" else "Onboarding Process Overview",
        value=st.session_state.get("onboarding_process_overview", ""),
        placeholder=(
            "Kurze Beschreibung des Onboarding-Prozesses"
            if lang == "Deutsch"
            else "Brief description of the onboarding process"
        ),
    )
    recruitment_contact_phone = st.text_input(
        "Kontakt-Telefon" if lang == "Deutsch" else "Recruitment Contact Phone",
        value=st.session_state.get("recruitment_contact_phone", ""),
        placeholder="z.B. +49 170 1234567",
    )
    application_instructions = st.text_area(
        "Hinweise zur Bewerbung" if lang == "Deutsch" else "Application Instructions",
        value=st.session_state.get("application_instructions", ""),
        placeholder=(
            "z.B. Ansprechpartner und benötigte Unterlagen"
            if lang == "Deutsch"
            else "e.g. Contact person and required documents"
        ),
    )
    return {
        "recruitment_contact_email": recruitment_contact_email,
        "recruitment_steps": recruitment_steps,
        "recruitment_timeline": recruitment_timeline,
        "number_of_interviews": number_of_interviews_str,
        "interview_format": interview_format,
        "assessment_tests": assessment_tests,
        "onboarding_process_overview": onboarding_process_overview,
        "recruitment_contact_phone": recruitment_contact_phone,
        "application_instructions": application_instructions,
    }


def render_step8():
    lang = st.session_state.get("lang", "English")
    st.title(
        "Schritt 8: Weitere Angaben & Zusammenfassung"
        if lang == "Deutsch"
        else "Step 8: Additional Information & Summary"
    )
    display_step_summary(8)
    st.subheader(
        "Abschließende Einstellungen" if lang == "Deutsch" else "Final Settings"
    )
    ad_seniority_tone = st.text_input(
        "Ton/Stil der Anzeige" if lang == "Deutsch" else "Ad Tone/Style",
        value=st.session_state.get("ad_seniority_tone", ""),
        placeholder=(
            "z.B. Professionell und förmlich"
            if lang == "Deutsch"
            else "e.g. Professional and formal"
        ),
        help=(
            "Gewünschter Tonfall/Schreibstil der Anzeige (z.B. locker, formell)."
            if lang == "Deutsch"
            else "Desired tone or style for the job ad (e.g. formal, casual, friendly)."
        ),
    )
    st.session_state["ad_seniority_tone"] = ad_seniority_tone
    ad_length_preference = st.text_input(
        (
            "Präferenz der Anzeigentextlänge"
            if lang == "Deutsch"
            else "Ad Length Preference"
        ),
        value=st.session_state.get("ad_length_preference", ""),
        placeholder=(
            "z.B. Kurz und prägnant" if lang == "Deutsch" else "e.g. Short and concise"
        ),
        help=(
            "Präferenz für die Länge der Stellenbeschreibung (knapp vs. ausführlich)."
            if lang == "Deutsch"
            else "Preference for the length/detail level of the job description (concise vs. detailed)."
        ),
    )
    st.session_state["ad_length_preference"] = ad_length_preference
    # Sprache der finalen Anzeige auswählen (Deutsch/Englisch)
    language_options = (
        ["Deutsch", "Englisch"] if lang == "Deutsch" else ["German", "English"]
    )
    default_idx = (
        0
        if st.session_state.get("language_of_ad", "English") in ["German", "Deutsch"]
        else 1
    )
    selected_lang = st.selectbox(
        "Sprache der Ausschreibung" if lang == "Deutsch" else "Language of Ad",
        options=language_options,
        index=(0 if default_idx == 0 else 1),
    )
    st.session_state["language_of_ad"] = (
        "German" if selected_lang in ["German", "Deutsch"] else "English"
    )
    translation_required = st.toggle(
        (
            "Übersetzung der Anzeige benötigt?"
            if lang == "Deutsch"
            else "Translation required?"
        ),
        value=bool(st.session_state.get("translation_required", False)),
    )
    st.session_state["translation_required"] = translation_required
    desired_publication_channels = st.text_input(
        (
            "Gewünschte Veröffentlichungskanäle"
            if lang == "Deutsch"
            else "Desired Publication Channels"
        ),
        value=st.session_state.get("desired_publication_channels", ""),
        placeholder=(
            "z.B. LinkedIn, Firmenwebsite"
            if lang == "Deutsch"
            else "e.g. LinkedIn, Company careers page"
        ),
        help=(
            "Kanäle/Plattformen, auf denen die Stelle veröffentlicht werden soll."
            if lang == "Deutsch"
            else "Channels where the job ad will be posted (job boards, company site, etc)."
        ),
    )
    st.session_state["desired_publication_channels"] = desired_publication_channels
    employer_branding_elements = st.text_input(
        (
            "Employer-Branding-Elemente"
            if lang == "Deutsch"
            else "Employer Branding Elements"
        ),
        value=st.session_state.get("employer_branding_elements", ""),
        placeholder=(
            "z.B. Unternehmensmission, Werte"
            if lang == "Deutsch"
            else "e.g. Company mission statement, core values"
        ),
        help=(
            "Besondere Merkmale der Arbeitgebermarke (Mission, Werte, Slogan, etc.)."
            if lang == "Deutsch"
            else "Company branding elements to include (mission, values, tagline, etc.)."
        ),
    )
    st.session_state["employer_branding_elements"] = employer_branding_elements
    diversity_inclusion_statement = st.text_area(
        "Diversity & Inclusion Statement",
        value=st.session_state.get("diversity_inclusion_statement", ""),
        placeholder=(
            "Optionale Passage zu Diversität und Inklusion"
            if lang == "Deutsch"
            else "Optional statement on diversity and inclusion"
        ),
    )
    st.session_state["diversity_inclusion_statement"] = diversity_inclusion_statement
    legal_disclaimers = st.text_area(
        "Rechtliche Hinweise" if lang == "Deutsch" else "Legal Disclaimers",
        value=st.session_state.get("legal_disclaimers", ""),
        placeholder=(
            "Rechtliche Hinweise oder Disclaimer"
            if lang == "Deutsch"
            else "Any legal disclaimers or notices"
        ),
    )
    st.session_state["legal_disclaimers"] = legal_disclaimers
    company_awards = st.text_input(
        "Auszeichnungen des Unternehmens" if lang == "Deutsch" else "Company Awards",
        value=st.session_state.get("company_awards", ""),
        placeholder=(
            "z.B. Top-Arbeitgeber 2023"
            if lang == "Deutsch"
            else "e.g. Best Employer 2023"
        ),
    )
    st.session_state["company_awards"] = company_awards
    social_media_links = st.text_input(
        "Social-Media-Links",
        value=st.session_state.get("social_media_links", ""),
        placeholder=(
            "z.B. LinkedIn, XING, Twitter"
            if lang == "Deutsch"
            else "e.g. LinkedIn, Twitter profiles"
        ),
    )
    st.session_state["social_media_links"] = social_media_links
    video_introduction_option = st.text_input(
        (
            "Option für Videoeinleitung"
            if lang == "Deutsch"
            else "Video Introduction Option"
        ),
        value=st.session_state.get("video_introduction_option", ""),
        placeholder=(
            "z.B. Link zu einem Company-Video"
            if lang == "Deutsch"
            else "e.g. Link to a company introduction video"
        ),
    )
    st.session_state["video_introduction_option"] = video_introduction_option
    internal_job_id = st.text_input(
        "Interne Job-ID",
        value=st.session_state.get("internal_job_id", ""),
        placeholder="Interne Referenznummer der Stelle",
    )
    st.session_state["internal_job_id"] = internal_job_id
    deadline_urgency = st.text_input(
        (
            "Bewerbungsfrist/Dringlichkeit"
            if lang == "Deutsch"
            else "Application Deadline/Urgency"
        ),
        value=st.session_state.get("deadline_urgency", ""),
        placeholder=(
            "z.B. Einstellung bis Q4 angepeilt"
            if lang == "Deutsch"
            else "e.g. Target to hire by Q4"
        ),
    )
    st.session_state["deadline_urgency"] = deadline_urgency
    comments_internal = st.text_area(
        "Interne Kommentare" if lang == "Deutsch" else "Internal Comments",
        value=st.session_state.get("comments_internal", ""),
        placeholder="Nur intern: Notizen oder Kommentare zum Profil",
    )
    st.session_state["comments_internal"] = comments_internal
    st.success(
        "🎉 Alle Schritte abgeschlossen! Überprüfe die Angaben und erstelle nun die Stellenanzeige."
        if lang == "Deutsch"
        else "🎉 All steps completed! Review all inputs and proceed to generate the job description."
    )

    if st.button("Interviewfragen" if lang == "Deutsch" else "Interview Questions"):
        from logic.job_tools import generate_interview_questions

        questions = generate_interview_questions(
            st.session_state.get("key_responsibilities", "")
            or st.session_state.get("task_list", "")
        )
        st.session_state["generated_interview_prep"] = "\n".join(questions)
        with st.expander("Interview Questions", expanded=True):
            for q in questions:
                st.write("- " + q)

    if st.button("Boolean Query"):
        from logic.job_tools import build_boolean_query

        skills = [
            s.strip()
            for s in (st.session_state.get("must_have_skills") or "").split("\n")
            if s.strip()
        ]
        query = build_boolean_query(st.session_state.get("job_title", ""), skills)
        st.session_state["generated_boolean_query"] = query
        st.text_area("Search Query", value=query, height=80)


def run_wizard():
    """Haupt-Einstiegspunkt zum Rendern des Wizards basierend auf dem aktuellen Schritt."""
    update_language()
    step = _clamp_step()
    _ensure_engine()
    if step == 1:
        start_discovery_page()
    elif step == 2:
        _handle_static_step(2, render_step2_static)
    elif step == 3:
        _handle_static_step(3, render_step3_static)
    elif step == 4:
        _handle_static_step(4, render_step4_static)
    elif step == 5:
        _handle_static_step(5, render_step5_static)
    elif step == 6:
        _handle_static_step(6, render_step6_static)
    elif step == 7:
        _handle_static_step(7, render_step7_static)
    elif step == 8:
        render_step8()
    _nav(step)


def _nav(step: int) -> None:
    """Display navigation buttons for the wizard.

    A "Home" button is shown from step 2 onward and jumps back to the first
    screen. Buttons appear in the order Next → Home → Back.
    """

    lang = st.session_state.get("lang", "English")
    if step < 8:
        st.button(
            "Weiter" if lang == "Deutsch" else "Next",
            on_click=lambda: st.session_state.update({"wizard_step": step + 1}),
            key=f"next_{step}",
        )
    if step > 1:
        st.button(
            "🏠 Home",
            on_click=lambda: st.session_state.update({"wizard_step": 1}),
            key=f"home_{step}",
        )
        st.button(
            "Zurück" if lang == "Deutsch" else "Back",
            on_click=lambda: st.session_state.update({"wizard_step": step - 1}),
            key=f"back_{step}",
        )
