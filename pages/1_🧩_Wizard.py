import os
from typing import Any, Dict
import streamlit as st

# Vacalyser internals
from src.state.session_state import initialize_session_state
from src.logic.trigger_engine import TriggerEngine, build_default_graph
from src.processors import register_all_processors
from src.tools.file_tools import extract_text_from_file
from src.tools.scraping_tools import scrape_company_site
from src.utils.text_cleanup import clean_text
from src.config.keys import STEP_KEYS
from src.agents.vacancy_agent import auto_fill_job_spec  # LLM extraction function

# Initialize session state (ensures all keys exist with default empty values)
initialize_session_state()

# Ensure TriggerEngine is initialized and processors registered
def _ensure_engine() -> TriggerEngine:
    eng: TriggerEngine = st.session_state.get("trigger_engine")
    if eng is None:
        eng = TriggerEngine()
        build_default_graph(eng)
        register_all_processors(eng)
        st.session_state["trigger_engine"] = eng
    return eng

# Guarantee wizard_step is within 1–8
def _clamp_step() -> int:
    st.session_state["wizard_step"] = max(1, min(8, int(st.session_state.get("wizard_step", 1))))
    return st.session_state["wizard_step"]

# Utility: fetch and clean text from a URL (HTML or PDF/DOCX)
def fetch_url_text(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        st.warning(f"Failed to fetch URL: {exc}")
        return ""
    ctype = resp.headers.get("content-type", "").lower()
    if "text/html" in ctype:
        text = scrape_company_site(url)
    elif "pdf" in ctype:
        text = extract_text_from_file(resp.content, "temp.pdf")
    elif "officedocument" in ctype or "msword" in ctype:
        text = extract_text_from_file(resp.content, "temp.docx")
    else:
        text = resp.text
    return clean_text(text or "")

# Simple regex-based extraction: looks for "Label: value" patterns in raw text
def match_and_store_keys(raw_text: str) -> None:
    if not raw_text:
        return
    labels = {
        "job_title": "Job Title:",
        "company_name": "Company Name:",
        "brand_name": "Brand Name:",
        "headquarters_location": "HQ Location:",
        "company_website": "Company Website:",
        "company_size": "Company Size:",
        "industry_sector": "Industry Sector:",
        "date_of_employment_start": "Date of Employment Start:",
        "job_type": "Job Type:",
        "contract_type": "Contract Type:",
        "job_level": "Job Level:",
        "city": "City",
        "team_structure": "Team Structure:",
        "role_description": "Role Description:",
        "reports_to": "Reports To:",
        "supervises": "Supervises:",
        "role_type": "Role Type:",
        "role_priority_projects": "Priority Projects:",
        "travel_requirements": "Travel Requirements:",
        "work_schedule": "Work Schedule:",
        "role_keywords": "Role Keywords:",
        "decision_making_authority": "Decision Making Authority:",
        "role_performance_metrics": "Performance Metrics:",
        "task_list": "Task List:",
        "key_responsibilities": "Key Responsibilities:",
        # ... (additional labels for other fields as needed)
    }
    for key, label in labels.items():
        if label in raw_text:
            start = raw_text.find(label) + len(label)
            end = raw_text.find("\n", start)
            value = raw_text[start:end if end != -1 else None].strip().lstrip(": ")
            if value:
                st.session_state[key] = value

# Step 1: Job Discovery & Source Analysis
def start_discovery_page():
    # Language toggle (persist selection in session)
    if "lang" not in st.session_state:
        st.session_state["lang"] = "en"
    lang_choice = st.radio("🌐 Language / Sprache", ["English", "Deutsch"], 
                            index=0 if st.session_state["lang"] == "en" else 1, horizontal=True)
    st.session_state["lang"] = "en" if lang_choice == "English" else "de"
    LANG = st.session_state["lang"]

    # Titles and intro text based on language
    if LANG == "de":
        st.title("🚀 Erstelle die perfekte Stellenbeschreibung")
        st.subheader("Von der ersten Idee bis zur fertigen Ausschreibung.")
        intro_text = (
            "Willkommen bei **RoleCraft**!\n\n"
            "Beginne mit einem Jobtitel oder lade eine vorhandene Ausschreibung hoch.\n"
            "Unser KI-gestützter Assistent analysiert die Angaben, füllt Lücken automatisch und führt dich Schritt für Schritt zum perfekten Profil."
        )
        button_job = "➕ Jobtitel eingeben"
        button_upload = "📂 PDF / DOCX hochladen"
        analyze_label = "🔎 Analysieren"
    else:
        st.title("🚀 Create the Perfect Job Description")
        st.subheader("From the first idea to a fully crafted profile.")
        intro_text = (
            "Welcome to **RoleCraft**!\n\n"
            "Start by entering a job title or uploading an existing job ad.\n"
            "Our AI-powered assistant will analyze the content, fill in any gaps, and guide you step-by-step to the perfect profile."
        )
        button_job = "➕ Enter Job Title"
        button_upload = "📂 Upload PDF / DOCX"
        analyze_label = "🔎 Analyze Sources"

    st.markdown(intro_text)

    st.header("Vacalyzer – Start Discovery")
    if LANG == "de":
        st.write("Gib einen Jobtitel ein und entweder einen Link zu einer Stellenanzeige oder lade eine Datei mit der Stellenbeschreibung hoch. "
                 "Der Assistent analysiert den Inhalt und füllt alle relevanten Felder automatisch aus.")
    else:
        st.write("Enter a job title and either a link to an existing job ad or upload a job description file. "
                 "The wizard will analyze the content and auto-fill relevant fields where possible.")

    col1, col2 = st.columns(2)
    with col1:
        job_title_label = "Job Title" if LANG == "en" else "Stellentitel"
        job_title_ph = "e.g. Senior Data Scientist" if LANG == "en" else "z.B. Senior Data Scientist"
        job_title = st.text_input(job_title_label, value=st.session_state.get("job_title", ""), placeholder=job_title_ph)
        if job_title:
            st.session_state["job_title"] = job_title

        url_label = "🔗 Job Ad URL (optional)" if LANG == "en" else "🔗 URL der Stellenanzeige (optional)"
        input_url = st.text_input(url_label, value=st.session_state.get("input_url", ""))
        if input_url:
            st.session_state["input_url"] = input_url

    with col2:
        upload_label = button_upload  # already language-specific above
        uploaded_file = st.file_uploader(upload_label, type=["pdf", "docx", "txt"])
        file_bytes = None
        file_name = ""
        if uploaded_file is not None:
            file_name = uploaded_file.name
            file_bytes = uploaded_file.read()
            raw_text = extract_text_from_file(file_bytes, file_name)
            raw_text = clean_text(raw_text)
            if raw_text:
                st.session_state["uploaded_file_text"] = raw_text
                st.success("✅ Text aus Datei extrahiert." if LANG == "de" else "✅ File uploaded and text extracted.")
            else:
                st.error("❌ Konnte keinen Text aus der Datei lesen." if LANG == "de" else "❌ Failed to extract text from the uploaded file.")

    analyze_clicked = st.button(analyze_label)
    if analyze_clicked:
        raw_text = ""
        source_used = None
        if st.session_state.get("uploaded_file_text"):
            raw_text = st.session_state["uploaded_file_text"]
            source_used = "file"
        elif st.session_state.get("input_url"):
            raw_text = fetch_url_text(st.session_state["input_url"])
            source_used = "url"
        if not raw_text:
            st.warning("⚠️ Bitte gib eine gültige URL oder lade eine Datei hoch, bevor du analysierst." if LANG == "de" 
                       else "⚠️ Please provide a valid URL or upload a file before analysis.")
        else:
            # Store raw text and attempt auto-extraction
            st.session_state["parsed_data_raw"] = raw_text
            try:
                # Run regex-based quick extraction
                match_and_store_keys(raw_text)
                # Run LLM-based detailed extraction
                if source_used == "file":
                    result: Dict[str, Any] = auto_fill_job_spec(file_bytes=file_bytes, file_name=file_name)
                else:
                    # Use URL if provided (file_bytes will be None in this case)
                    result: Dict[str, Any] = auto_fill_job_spec(input_url=st.session_state.get("input_url", ""), 
                                                                file_bytes=file_bytes if file_bytes else None, 
                                                                file_name=file_name)
                # Update session state with extracted fields
                if result:
                    for key, val in result.items():
                        if val:  # only update if value is not empty
                            st.session_state[key] = val
                st.success("🎯 Analyse abgeschlossen! Wichtige Felder wurden automatisch ausgefüllt." if LANG == "de" 
                           else "🎯 Analysis complete! Key details auto-filled.")
                # Log event for debugging/tracking
                st.session_state.get("trace_events", []).append("Auto-extracted fields from provided source.")
            except Exception as e:
                st.error(f"❌ Analyse fehlgeschlagen: {e}" if LANG == "de" else f"❌ Analysis failed: {e}")

# Generic handler for steps 2–7 (static forms with possible follow-ups)
def _handle_static_step(idx: int, renderer_func):
    form_key = f"step{idx}_form"
    submitted_flag = f"step{idx}_static_submitted"
    with st.form(form_key):
        # Render the form fields
        values = renderer_func()
        # Show Next button (labeled in current language)
        next_label = "Weiter ➡" if st.session_state.get("lang") == "de" else "Next ➡"
        submitted = st.form_submit_button(next_label)
    if submitted:
        # Save all form fields to session_state
        for k, v in values.items():
            st.session_state[k] = v
        # Trigger the engine for all keys in this step
        for k in STEP_KEYS.get(idx, []):
            _ensure_engine().notify_change(k, st.session_state)
        # Check which fields are still empty
        missing = [k for k in STEP_KEYS.get(idx, []) if not st.session_state.get(k)]
        # Mark flag if any missing (to present follow-up inputs)
        st.session_state[submitted_flag] = bool(missing)
        if missing:
            st.session_state.get("trace_events", []).append(f"Step {idx} submitted with missing: {missing}")
        else:
            # All fields provided, advance to next step
            st.session_state["wizard_step"] += 1
            st.session_state.get("trace_events", []).append(f"Step {idx} complete.")
        st.experimental_rerun()
    # If some fields were missing, show follow-up inputs dynamically
    if st.session_state.get(submitted_flag):
        missing_keys = [k for k in STEP_KEYS[idx] if not st.session_state.get(k)]
        info_text = "Bitte ergänze noch folgende Felder:" if st.session_state.get("lang") == "de" else "Please provide additional details for the following fields:"
        st.info(info_text)
        for key in missing_keys:
            label = key.replace("_", " ").title()
            # (We could translate label here as well if needed)
            if any(t in key for t in ("description", "tasks", "details", "comments", "responsibilities")):
                st.text_area(label, key=key)
            else:
                st.text_input(label, key=key)
        cont_label = "Weiter" if st.session_state.get("lang") == "de" else "Continue"
        if st.button(cont_label, key=f"continue_step{idx}"):
            # Re-trigger engine for all keys of this step after follow-ups
            for k in STEP_KEYS.get(idx, []):
                _ensure_engine().notify_change(k, st.session_state)
            st.session_state[submitted_flag] = False
            st.session_state["wizard_step"] += 1
            st.experimental_rerun()

# Navigation controls (Back/Next arrows outside forms)
def _nav(step: int):
    col_prev, col_next = st.columns(2)
    with col_prev:
        if step > 1:
            back_label = "⬅️ Zurück" if st.session_state.get("lang") == "de" else "⬅️ Back"
            if st.button(back_label):
                st.session_state["wizard_step"] -= 1
                st.experimental_rerun()
    with col_next:
        # Show a Next button for Step 1 (since it's not a form) and also as a fallback if user skips form
        if step < 8 and not st.session_state.get(f"step{step}_static_submitted", False):
            next_label = "Weiter ➡" if st.session_state.get("lang") == "de" else "Next ➡"
            if st.button(next_label):
                st.session_state["wizard_step"] += 1
                st.experimental_rerun()

# Step 2: Basic Job & Company Info
def render_step2_static():
    LANG = st.session_state.get("lang", "en")
    st.title("Step 2: Basic Job & Company Info" if LANG == "en" else "Schritt 2: Basisdaten zu Job & Unternehmen")
    # Company Information
    comp_name_label = "Company Name" if LANG == "en" else "Firmenname"
    comp_name_ph = "e.g. Tech Corp Ltd." if LANG == "en" else "z.B. Tech Corp GmbH"
    company_name = st.text_input(comp_name_label, value=st.session_state.get("company_name", ""), placeholder=comp_name_ph)
    brand_label = "Brand Name (if different)" if LANG == "en" else "Markenname (falls abweichend)"
    brand_name = st.text_input(brand_label, value=st.session_state.get("brand_name", ""), placeholder="e.g. Parent Company Inc." if LANG == "en" else "z.B. Muttergesellschaft AG")
    hq_label = "Headquarters Location" if LANG == "en" else "Hauptsitz (Ort)"
    headquarters_location = st.text_input(hq_label, value=st.session_state.get("headquarters_location", ""), placeholder="e.g. Berlin, Germany" if LANG == "en" else "z.B. Berlin, Deutschland")
    website_label = "Company Website" if LANG == "en" else "Webseite des Unternehmens"
    company_website = st.text_input(website_label, value=st.session_state.get("company_website", ""), placeholder="e.g. https://company.com" if LANG == "en" else "z.B. https://firma.de")
    size_label = "Company Size (employees)" if LANG == "en" else "Unternehmensgröße (Mitarbeiter)"
    size_ph = "e.g. 51-200" if LANG == "en" else "z.B. 51-200"
    company_size = st.text_input(size_label, value=st.session_state.get("company_size", ""), placeholder=size_ph)
    industry_label = "Industry Sector" if LANG == "en" else "Branche"
    industry_sector = st.text_input(industry_label, value=st.session_state.get("industry_sector", ""), placeholder="e.g. Software, Finance" if LANG == "en" else "z.B. Software, Finanzen")
    # Job Basics
    start_date_label = "Preferred Start Date" if LANG == "en" else "Bevorzugtes Startdatum"
    date_of_start = st.text_input(start_date_label, value=st.session_state.get("date_of_employment_start", ""), placeholder="e.g. ASAP or 2025-01-15" if LANG == "en" else "z.B. sofort oder 01.05.2025")
    job_type_label = "Job Type" if LANG == "en" else "Art der Stelle"
    job_type_options = ["Full-Time", "Part-Time", "Internship", "Freelance", "Volunteer", "Other"] if LANG == "en" else ["Vollzeit", "Teilzeit", "Praktikum", "Freiberuflich", "Ehrenamtlich", "Andere"]
    job_type = st.selectbox(job_type_label, job_type_options, index=0)
    contract_label = "Contract Type" if LANG == "en" else "Vertragsart"
    contract_options = ["Permanent", "Fixed-Term", "Contract", "Other"] if LANG == "en" else ["Unbefristet", "Befristet", "Auftragsarbeit", "Andere"]
    contract_type = st.selectbox(contract_label, contract_options, index=0)
    level_label = "Job Level" if LANG == "en" else "Karrierestufe"
    level_options = ["Entry-level", "Mid-level", "Senior", "Director", "C-level", "Other"] if LANG == "en" else ["Einsteiger", "Berufserfahren", "Senior", "Direktor", "Führungsebene (C-Level)", "Andere"]
    job_level = st.selectbox(level_label, level_options, index=0)
    city_label = "City (Job Location)" if LANG == "en" else "Stadt (Einsatzort)"
    city = st.text_input(city_label, value=st.session_state.get("city", ""), placeholder="e.g. London" if LANG == "en" else "z.B. München")
    team_label = "Team Structure" if LANG == "en" else "Teamstruktur"
    team_ph = "Describe the team setup, reporting hierarchy, etc." if LANG == "en" else "Beschreibe Aufbau, Berichtswege, etc."
    team_structure = st.text_area(team_label, value=st.session_state.get("team_structure", ""), placeholder=team_ph)
    return {
        "company_name": company_name,
        "brand_name": brand_name,
        "headquarters_location": headquarters_location,
        "company_website": company_website,
        "company_size": company_size,
        "industry_sector": industry_sector,
        "date_of_employment_start": date_of_start,
        "job_type": job_type,
        "contract_type": contract_type,
        "job_level": job_level,
        "city": city,
        "team_structure": team_structure,
    }

# Step 3: Role Definition
def render_step3_static():
    LANG = st.session_state.get("lang", "en")
    st.title("Step 3: Role Definition" if LANG == "en" else "Schritt 3: Rollenbeschreibung")
    role_desc_label = "Role Description" if LANG == "en" else "Rollenbeschreibung"
    role_desc_ph = "High-level summary of the role..." if LANG == "en" else "Überblick über die Position und Aufgaben..."
    role_description = st.text_area(role_desc_label, value=st.session_state.get("role_description", ""), placeholder=role_desc_ph)
    reports_label = "Reports To" if LANG == "en" else "Berichtet an"
    reports_to = st.text_input(reports_label, value=st.session_state.get("reports_to", ""), placeholder="e.g. Head of Department" if LANG == "en" else "z.B. Abteilungsleiter")
    supervises_label = "Supervises" if LANG == "en" else "Führt Aufsicht über"
    supervises = st.text_area(supervises_label, value=st.session_state.get("supervises", ""), placeholder="List positions or teams this role manages" if LANG == "en" else "Liste von Positionen/Teams, die diese Rolle führt")
    role_type_label = "Role Type" if LANG == "en" else "Positionstyp"
    role_type_options = ["Individual Contributor", "Team Lead", "Manager", "Director", "Executive", "Other"] if LANG == "en" else ["Fachkraft (kein Lead)", "Teamleitung", "Manager", "Direktor", "Führungskraft", "Andere"]
    role_type = st.selectbox(role_type_label, role_type_options, index=0)
    projects_label = "Priority Projects" if LANG == "en" else "Wichtige Projekte"
    projects_ph = "Key projects or initiatives for this role" if LANG == "en" else "Wichtige Projekte oder Initiativen in dieser Rolle"
    role_priority_projects = st.text_area(projects_label, value=st.session_state.get("role_priority_projects", ""), placeholder=projects_ph)
    travel_label = "Travel Requirements" if LANG == "en" else "Reisebereitschaft"
    travel_requirements = st.text_input(travel_label, value=st.session_state.get("travel_requirements", ""), placeholder="e.g. Up to 20% travel required" if LANG == "en" else "z.B. bis zu 20% Reisetätigkeit")
    schedule_label = "Work Schedule" if LANG == "en" else "Arbeitszeit"
    work_schedule = st.text_input(schedule_label, value=st.session_state.get("work_schedule", ""), placeholder="e.g. Mon-Fri 9-5, rotating shifts" if LANG == "en" else "z.B. Mo-Fr 9-17 Uhr, Schichtbetrieb")
    keywords_label = "Role Keywords" if LANG == "en" else "Schlüsselwörter zur Rolle"
    keywords_ph = "Keywords for this role (for SEO or analytics)" if LANG == "en" else "Stichworte zur Rolle (für SEO/Analyse)"
    role_keywords = st.text_area(keywords_label, value=st.session_state.get("role_keywords", ""), placeholder=keywords_ph)
    authority_label = "Decision Making Authority" if LANG == "en" else "Entscheidungsbefugnis"
    decision_making_authority = st.text_input(authority_label, value=st.session_state.get("decision_making_authority", ""), placeholder="e.g. Final say on budget allocations" if LANG == "en" else "z.B. finale Entscheidungsgewalt über Budget")
    metrics_label = "Performance Metrics" if LANG == "en" else "Leistungskennzahlen"
    role_performance_metrics = st.text_input(metrics_label, value=st.session_state.get("role_performance_metrics", ""), placeholder="How performance is measured for this role" if LANG == "en" else "Wie der Erfolg in dieser Rolle gemessen wird")
    return {
        "role_description": role_description,
        "reports_to": reports_to,
        "supervises": supervises,
        "role_type": role_type,
        "role_priority_projects": role_priority_projects,
        "travel_requirements": travel_requirements,
        "work_schedule": work_schedule,
        "role_keywords": role_keywords,
        "decision_making_authority": decision_making_authority,
        "role_performance_metrics": role_performance_metrics,
    }

# Step 4: Tasks & Responsibilities
def render_step4_static():
    LANG = st.session_state.get("lang", "en")
    st.title("Step 4: Tasks & Responsibilities" if LANG == "en" else "Schritt 4: Aufgaben & Verantwortlichkeiten")
    # Always visible core fields
    task_list_label = "General Task List" if LANG == "en" else "Allgemeine Aufgabenliste"
    task_list_ph = "Bullet points of day-to-day tasks" if LANG == "en" else "Aufzählung der täglichen Aufgaben"
    task_list = st.text_area(task_list_label, value=st.session_state.get("task_list", ""), placeholder=task_list_ph)
    responsibilities_label = "Key Responsibilities" if LANG == "en" else "Hauptverantwortlichkeiten"
    responsibilities_ph = "Major areas of responsibility" if LANG == "en" else "Wichtigste Verantwortungsbereiche"
    key_responsibilities = st.text_area(responsibilities_label, value=st.session_state.get("key_responsibilities", ""), placeholder=responsibilities_ph)
    # Optional detailed breakdown in expander
    with st.expander("Detailed Task Breakdown (optional)" if LANG == "en" else "Detaillierte Aufgabenkategorien (optional)"):
        technical_label = "Technical Tasks" if LANG == "en" else "Technische Aufgaben"
        technical_tasks = st.text_area(technical_label, value=st.session_state.get("technical_tasks", ""), placeholder="Specialized or technical duties" if LANG == "en" else "Spezialisierte/technische Aufgaben")
        managerial_label = "Managerial Tasks" if LANG == "en" else "Leitungsaufgaben"
        managerial_tasks = st.text_area(managerial_label, value=st.session_state.get("managerial_tasks", ""), placeholder="Managerial or leadership duties" if LANG == "en" else "Führungs- oder Managementaufgaben")
        admin_label = "Administrative Tasks" if LANG == "en" else "Administrative Aufgaben"
        administrative_tasks = st.text_area(admin_label, value=st.session_state.get("administrative_tasks", ""), placeholder="Administrative or support tasks" if LANG == "en" else "Administrative Unterstützungsaufgaben")
        customer_label = "Customer-Facing Tasks" if LANG == "en" else "Kundenbezogene Aufgaben"
        customer_facing_tasks = st.text_area(customer_label, value=st.session_state.get("customer_facing_tasks", ""), placeholder="Client-facing duties" if LANG == "en" else "Aufgaben mit Kundenkontakt")
        reporting_label = "Internal Reporting Tasks" if LANG == "en" else "Interne Berichtspflichten"
        internal_reporting_tasks = st.text_area(reporting_label, value=st.session_state.get("internal_reporting_tasks", ""), placeholder="Reporting and documentation tasks" if LANG == "en" else "Aufgaben in Bezug auf Berichterstattung/Dokumentation")
        perf_label = "Performance-Related Tasks" if LANG == "en" else "Leistungsbezogene Aufgaben"
        performance_tasks = st.text_area(perf_label, value=st.session_state.get("performance_tasks", ""), placeholder="Tasks tied to performance metrics" if LANG == "en" else "Aufgaben in Zusammenhang mit Leistungskennzahlen")
        innovation_label = "Innovation Tasks" if LANG == "en" else "Innovationsaufgaben"
        innovation_tasks = st.text_area(innovation_label, value=st.session_state.get("innovation_tasks", ""), placeholder="R&D or innovation-related tasks" if LANG == "en" else "Forschungs- und Entwicklungsaufgaben")
        prioritization_label = "Task Prioritization" if LANG == "en" else "Priorisierung der Aufgaben"
        task_prioritization = st.text_area(prioritization_label, value=st.session_state.get("task_prioritization", ""), placeholder="How tasks are prioritized" if LANG == "en" else "Wie die Aufgaben priorisiert werden")
    return {
        "task_list": task_list,
        "key_responsibilities": key_responsibilities,
        "technical_tasks": technical_tasks,
        "managerial_tasks": managerial_tasks,
        "administrative_tasks": administrative_tasks,
        "customer_facing_tasks": customer_facing_tasks,
        "internal_reporting_tasks": internal_reporting_tasks,
        "performance_tasks": performance_tasks,
        "innovation_tasks": innovation_tasks,
        "task_prioritization": task_prioritization,
    }

# Step 5: Skills & Competencies
def render_step5_static():
    LANG = st.session_state.get("lang", "en")
    st.title("Step 5: Skills & Competencies" if LANG == "en" else "Schritt 5: Fähigkeiten & Kompetenzen")
    # Core skill requirements
    must_label = "Must-Have Skills" if LANG == "en" else "Unbedingt erforderliche Fähigkeiten"
    must_ph = "Non-negotiable requirements" if LANG == "en" else "Unverzichtbare Anforderungen"
    must_have_skills = st.text_area(must_label, value=st.session_state.get("must_have_skills", ""), placeholder=must_ph)
    nice_label = "Nice-to-Have Skills" if LANG == "en" else "Wünschenswerte Fähigkeiten"
    nice_ph = "Preferred additional skills" if LANG == "en" else "Optionale, zusätzliche Fähigkeiten"
    nice_to_have_skills = st.text_area(nice_label, value=st.session_state.get("nice_to_have_skills", ""), placeholder=nice_ph)
    # Detailed skills breakdown
    with st.expander("Additional Skill Details" if LANG == "en" else "Weitere Details zu Fähigkeiten"):
        hard_label = "Hard Skills" if LANG == "en" else "Fachliche Fähigkeiten"
        hard_ph = "Technical or job-specific skills" if LANG == "en" else "Technische oder positionsspezifische Fähigkeiten"
        hard_skills = st.text_area(hard_label, value=st.session_state.get("hard_skills", ""), placeholder=hard_ph)
        soft_label = "Soft Skills" if LANG == "en" else "Soft Skills (soziale Kompetenzen)"
        soft_ph = "Communication, teamwork, leadership, etc." if LANG == "en" else "Kommunikation, Teamarbeit, Führung, etc."
        soft_skills = st.text_area(soft_label, value=st.session_state.get("soft_skills", ""), placeholder=soft_ph)
        cert_label = "Certifications Required" if LANG == "en" else "Erforderliche Zertifizierungen"
        cert_ph = "Degrees or certifications (if any)" if LANG == "en" else "Abschlüsse oder Zertifikate (falls zutreffend)"
        certifications_required = st.text_area(cert_label, value=st.session_state.get("certifications_required", ""), placeholder=cert_ph)
        lang_req_label = "Language Requirements" if LANG == "en" else "Sprachkenntnisse"
        lang_req_ph = "e.g. English C1, French B2" if LANG == "en" else "z.B. Englisch C1, Französisch B2"
        language_requirements = st.text_area(lang_req_label, value=st.session_state.get("language_requirements", ""), placeholder=lang_req_ph)
        tool_label = "Tool Proficiency" if LANG == "en" else "Tool-Kenntnisse"
        tool_ph = "Software or tools expertise (e.g. Excel, AWS)" if LANG == "en" else "Software- oder Tool-Kenntnisse (z.B. Excel, AWS)"
        tool_proficiency = st.text_area(tool_label, value=st.session_state.get("tool_proficiency", ""), placeholder=tool_ph)
        domain_label = "Domain Expertise" if LANG == "en" else "Branchenerfahrung"
        domain_ph = "Industry/field expertise (e.g. finance, AI)" if LANG == "en" else "Erfahrung in bestimmter Branche (z.B. Finanzwesen, KI)"
        domain_expertise = st.text_area(domain_label, value=st.session_state.get("domain_expertise", ""), placeholder=domain_ph)
        leadership_label = "Leadership Competencies" if LANG == "en" else "Führungskompetenzen"
        leadership_ph = "For managerial roles: mentoring, strategic thinking, etc." if LANG == "en" else "Bei Führungsrollen: z.B. Mentoring, strategisches Denken"
        leadership_competencies = st.text_area(leadership_label, value=st.session_state.get("leadership_competencies", ""), placeholder=leadership_ph)
        tech_stack_label = "Technical Stack" if LANG == "en" else "Tech-Stack"
        tech_stack_ph = "Technologies used (for technical roles)" if LANG == "en" else "Eingesetzte Technologien (bei technischen Rollen)"
        technical_stack = st.text_area(tech_stack_label, value=st.session_state.get("technical_stack", ""), placeholder=tech_stack_ph)
        industry_exp_label = "Industry Experience" if LANG == "en" else "Industrie-Erfahrung"
        industry_exp_ph = "Years of experience in relevant industry" if LANG == "en" else "Jahre Erfahrung in der relevanten Branche"
        industry_experience = st.text_input(industry_exp_label, value=st.session_state.get("industry_experience", ""), placeholder=industry_exp_ph)
        analytical_label = "Analytical Skills" if LANG == "en" else "Analytische Fähigkeiten"
        analytical_skills = st.text_input(analytical_label, value=st.session_state.get("analytical_skills", ""), placeholder="e.g. Data analysis, critical thinking" if LANG == "en" else "z.B. Datenanalyse, kritisches Denken")
        communication_label = "Communication Skills" if LANG == "en" else "Kommunikationsfähigkeiten"
        communication_skills = st.text_input(communication_label, value=st.session_state.get("communication_skills", ""), placeholder="e.g. Presentation, writing" if LANG == "en" else "z.B. Präsentation, schriftliche Kommunikation")
        pm_label = "Project Management Skills" if LANG == "en" else "Projektmanagement-Fähigkeiten"
        project_management_skills = st.text_input(pm_label, value=st.session_state.get("project_management_skills", ""), placeholder="Ability to plan and execute projects" if LANG == "en" else "Fähigkeit, Projekte zu planen und durchzuführen")
        other_req_label = "Additional Soft Requirements" if LANG == "en" else "Weitere Anforderungen"
        other_req_ph = "Other personality or work style requirements" if LANG == "en" else "Andere Anforderungen an Persönlichkeit oder Arbeitsstil"
        soft_requirement_details = st.text_area(other_req_label, value=st.session_state.get("soft_requirement_details", ""), placeholder=other_req_ph)
    visa_label = "Visa Sponsorship" if LANG == "en" else "Visa-Sponsoring"
    visa_options = ["No", "Yes", "Case-by-Case"] if LANG == "en" else ["Nein", "Ja", "Einzelfall"]
    visa_sponsorship = st.selectbox(visa_label, visa_options, index=0)
    return {
        "must_have_skills": must_have_skills,
        "nice_to_have_skills": nice_to_have_skills,
        "hard_skills": hard_skills,
        "soft_skills": soft_skills,
        "certifications_required": certifications_required,
        "language_requirements": language_requirements,
        "tool_proficiency": tool_proficiency,
        "domain_expertise": domain_expertise,
        "leadership_competencies": leadership_competencies,
        "technical_stack": technical_stack,
        "industry_experience": industry_experience,
        "analytical_skills": analytical_skills,
        "communication_skills": communication_skills,
        "project_management_skills": project_management_skills,
        "soft_requirement_details": soft_requirement_details,
        "visa_sponsorship": visa_sponsorship,
    }

# Step 6: Compensation & Benefits
def render_step6_static():
    LANG = st.session_state.get("lang", "en")
    st.title("Step 6: Compensation & Benefits" if LANG == "en" else "Schritt 6: Vergütung & Benefits")
    salary_label = "Salary Range" if LANG == "en" else "Gehaltsspanne"
    salary_range = st.text_input(salary_label, value=st.session_state.get("salary_range", ""), placeholder="e.g. 50,000 - 60,000 EUR" if LANG == "en" else "z.B. 50.000 - 60.000 EUR")
    currency_label = "Currency" if LANG == "en" else "Währung"
    currency_options = ["EUR", "USD", "GBP", "Other"] if LANG == "en" else ["EUR", "USD", "GBP", "Andere"]
    currency = st.selectbox(currency_label, currency_options, index=0)
    pay_label = "Pay Frequency" if LANG == "en" else "Zahlungshäufigkeit"
    pay_options = ["Annual", "Monthly", "Bi-weekly", "Weekly", "Other"] if LANG == "en" else ["Jährlich", "Monatlich", "14-tägig", "Wöchentlich", "Andere"]
    pay_frequency = st.selectbox(pay_label, pay_options, index=0)
    commission_label = "Commission Structure" if LANG == "en" else "Provisionsregelung"
    commission_structure = st.text_input(commission_label, value=st.session_state.get("commission_structure", ""), placeholder="Details of any commission" if LANG == "en" else "Details zu etwaigen Provisionen")
    bonus_label = "Bonus Scheme" if LANG == "en" else "Bonusregelung"
    bonus_scheme = st.text_input(bonus_label, value=st.session_state.get("bonus_scheme", ""), placeholder="Details of bonus or incentives" if LANG == "en" else "Details zu Bonus oder Prämien")
    vacation_label = "Vacation Days" if LANG == "en" else "Urlaubstage"
    vacation_days = st.text_input(vacation_label, value=st.session_state.get("vacation_days", ""), placeholder="e.g. 25 days" if LANG == "en" else "z.B. 25 Tage")
    flexible_label = "Flexible Hours" if LANG == "en" else "Gleitzeit/Flexible Arbeitszeiten"
    flexible_options = ["No", "Yes", "Partial/Flex"] if LANG == "en" else ["Nein", "Ja", "Teilweise"]
    flexible_hours = st.selectbox(flexible_label, flexible_options, index=0)
    remote_label = "Remote Work Policy" if LANG == "en" else "Homeoffice-Regelung"
    remote_options = ["On-site", "Hybrid", "Full Remote", "Other"] if LANG == "en" else ["Vor Ort", "Hybrid", "Voll Remote", "Andere"]
    remote_work_policy = st.selectbox(remote_label, remote_options, index=0)
    relocation_label = "Relocation Assistance" if LANG == "en" else "Umzugsunterstützung"
    relocation_options = ["No", "Yes", "Case-by-Case"] if LANG == "en" else ["Nein", "Ja", "Einzelfall"]
    relocation_assistance = st.selectbox(relocation_label, relocation_options, index=0)
    childcare_label = "Childcare Support" if LANG == "en" else "Kinderbetreuungszuschuss"
    childcare_options = ["No", "Yes", "Case-by-Case"] if LANG == "en" else ["Nein", "Ja", "Einzelfall"]
    childcare_support = st.selectbox(childcare_label, childcare_options, index=0)
    return {
        "salary_range": salary_range,
        "currency": currency,
        "pay_frequency": pay_frequency,
        "commission_structure": commission_structure,
        "bonus_scheme": bonus_scheme,
        "vacation_days": vacation_days,
        "flexible_hours": flexible_hours,
        "remote_work_policy": remote_work_policy,
        "relocation_assistance": relocation_assistance,
        "childcare_support": childcare_support,
    }

# Step 7: Recruitment Process
def render_step7_static():
    LANG = st.session_state.get("lang", "en")
    st.title("Step 7: Recruitment Process" if LANG == "en" else "Schritt 7: Einstellungsprozess")
    steps_label = "Recruitment Steps" if LANG == "en" else "Ablauf der Bewerbung"
    steps_ph = "Outline the hiring process steps (e.g. screening, interviews, etc.)" if LANG == "en" else "Überblick über den Bewerbungsprozess (z.B. Vorauswahl, Interviews, etc.)"
    recruitment_steps = st.text_area(steps_label, value=st.session_state.get("recruitment_steps", ""), placeholder=steps_ph)
    timeline_label = "Recruitment Timeline" if LANG == "en" else "Zeitplan bis Einstellung"
    timeline_ph = "Estimated time from application to offer" if LANG == "en" else "Geschätzte Dauer vom Eingang der Bewerbung bis zum Angebot"
    recruitment_timeline = st.text_input(timeline_label, value=st.session_state.get("recruitment_timeline", ""), placeholder=timeline_ph)
    interviews_label = "Number of Interviews" if LANG == "en" else "Anzahl der Vorstellungsgespräche"
    number_of_interviews = st.text_input(interviews_label, value=st.session_state.get("number_of_interviews", ""), placeholder="e.g. 3" if LANG == "en" else "z.B. 3")
    format_label = "Interview Format" if LANG == "en" else "Interview-Format"
    format_ph = "e.g. Phone, On-site, Video" if LANG == "en" else "z.B. Telefon, vor Ort, Video"
    interview_format = st.text_input(format_label, value=st.session_state.get("interview_format", ""), placeholder=format_ph)
    tests_label = "Assessment Tests" if LANG == "en" else "Assessment-Tests"
    tests_ph = "Any tests or assignments for candidates?" if LANG == "en" else "Etwaige Tests oder Aufgaben für Bewerber?"
    assessment_tests = st.text_area(tests_label, value=st.session_state.get("assessment_tests", ""), placeholder=tests_ph)
    onboarding_label = "Onboarding Process Overview" if LANG == "en" else "Onboarding-Prozess"
    onboarding_ph = "Brief overview of post-hire onboarding" if LANG == "en" else "Kurzer Überblick zum Onboarding nach Einstellung"
    onboarding_process_overview = st.text_area(onboarding_label, value=st.session_state.get("onboarding_process_overview", ""), placeholder=onboarding_ph)
    email_label = "Recruitment Contact Email" if LANG == "en" else "Kontakt E-Mail für Bewerbungen"
    recruitment_contact_email = st.text_input(email_label, value=st.session_state.get("recruitment_contact_email", ""), placeholder="e.g. jobs@company.com" if LANG == "en" else "z.B. jobs@firma.de")
    phone_label = "Recruitment Contact Phone" if LANG == "en" else "Kontakt Telefon"
    recruitment_contact_phone = st.text_input(phone_label, value=st.session_state.get("recruitment_contact_phone", ""), placeholder="e.g. +1 234 567 890" if LANG == "en" else "z.B. +49 170 1234567")
    instructions_label = "Application Instructions" if LANG == "en" else "Bewerbungsinstruktionen"
    instructions_ph = "How to apply (e.g. via portal or email)" if LANG == "en" else "Wie bewerben? (z.B. über Portal oder per E-Mail)"
    application_instructions = st.text_area(instructions_label, value=st.session_state.get("application_instructions", ""), placeholder=instructions_ph)
    return {
        "recruitment_steps": recruitment_steps,
        "recruitment_timeline": recruitment_timeline,
        "number_of_interviews": number_of_interviews,
        "interview_format": interview_format,
        "assessment_tests": assessment_tests,
        "onboarding_process_overview": onboarding_process_overview,
        "recruitment_contact_email": recruitment_contact_email,
        "recruitment_contact_phone": recruitment_contact_phone,
        "application_instructions": application_instructions,
    }

# Step 8: Additional Information & Final Review
def render_step8():
    LANG = st.session_state.get("lang", "en")
    st.title("Step 8: Additional Information & Final Review" if LANG == "en" else "Schritt 8: Weitere Informationen & Abschluss")
    st.subheader("Additional Metadata" if LANG == "en" else "Weitere Metadaten")
    parsed_label = "Parsed Data (Raw)" if LANG == "en" else "Analysierter Rohtext"
    parsed_help = "This is the raw text extracted from the provided source." if LANG == "en" else "Dies ist der aus der Quelle extrahierte Rohtext."
    parsed_data = st.text_area(parsed_label, value=st.session_state.get("parsed_data_raw", ""), placeholder="(Auto-generated raw text from analysis)" if LANG == "en" else "(Automatisch extrahierter Text)", help=parsed_help)
    lang_ad_label = "Language of Ad" if LANG == "en" else "Sprache der Anzeige"
    language_of_ad = st.text_input(lang_ad_label, value=st.session_state.get("language_of_ad", ""), placeholder="e.g. English, German" if LANG == "en" else "z.B. Englisch, Deutsch")
    translation_label = "Translation Required?" if LANG == "en" else "Übersetzung erforderlich?"
    translation_options = ["No", "Yes"] if LANG == "en" else ["Nein", "Ja"]
    translation_required = st.selectbox(translation_label, translation_options, index=0 if st.session_state.get("translation_required", "No") in ["No", "Nein", "False"] else 1)
    branding_label = "Employer Branding Elements" if LANG == "en" else "Employer-Branding-Elemente"
    branding_ph = "Company culture or branding highlights to include" if LANG == "en" else "Besondere Kultur- oder Branding-Highlights der Firma"
    employer_branding_elements = st.text_area(branding_label, value=st.session_state.get("employer_branding_elements", ""), placeholder=branding_ph)
    publication_label = "Desired Publication Channels" if LANG == "en" else "Bevorzugte Veröffentlichungsorte"
    publication_ph = "Where will this ad be posted? (if specific)" if LANG == "en" else "Wo soll die Stelle veröffentlicht werden? (falls festgelegt)"
    desired_publication_channels = st.text_area(publication_label, value=st.session_state.get("desired_publication_channels", ""), placeholder=publication_ph)
    job_id_label = "Internal Job ID" if LANG == "en" else "Interne Job-ID"
    internal_job_id = st.text_input(job_id_label, value=st.session_state.get("internal_job_id", ""), placeholder="Internal reference ID for this position" if LANG == "en" else "Interne Referenzkennung der Stelle")
    tone_label = "Ad Seniority Tone" if LANG == "en" else "Ton der Anzeige (Seniorität)"
    tone_options = ["Casual", "Formal", "Neutral", "Enthusiastic"] if LANG == "en" else ["Locker", "Formal", "Neutral", "Enthusiastisch"]
    ad_seniority_tone = st.selectbox(tone_label, tone_options, index=0)
    length_label = "Ad Length Preference" if LANG == "en" else "Präferenz zur Anzeigelänge"
    length_options = ["Short & Concise", "Detailed", "Flexible"] if LANG == "en" else ["Kurz & prägnant", "Detailreich", "Flexibel"]
    ad_length_preference = st.selectbox(length_label, length_options, index=0)
    deadline_label = "Application Deadline/Urgency" if LANG == "en" else "Bewerbungsfrist/Dringlichkeit"
    deadline_urgency = st.text_input(deadline_label, value=st.session_state.get("deadline_urgency", ""), placeholder="e.g. Apply by 30 June; Urgent fill" if LANG == "en" else "z.B. Bewerbung bis 30. Juni; dringende Stelle")
    awards_label = "Company Awards" if LANG == "en" else "Auszeichnungen des Unternehmens"
    company_awards = st.text_area(awards_label, value=st.session_state.get("company_awards", ""), placeholder="Notable awards or recognitions" if LANG == "en" else "Wichtige Auszeichnungen oder Anerkennungen")
    diversity_label = "Diversity & Inclusion Statement" if LANG == "en" else "Diversity-&-Inclusion-Statement"
    diversity_inclusion_statement = st.text_area(diversity_label, value=st.session_state.get("diversity_inclusion_statement", ""), placeholder="Company's D&I commitment statement" if LANG == "en" else "Verpflichtungserklärung des Unternehmens zu Vielfalt & Inklusion")
    legal_label = "Legal Disclaimers" if LANG == "en" else "Rechtliche Hinweise"
    legal_disclaimers = st.text_area(legal_label, value=st.session_state.get("legal_disclaimers", ""), placeholder="Any legal or compliance text for the ad" if LANG == "en" else "Rechtliche Hinweise oder Disclaimer für die Anzeige")
    social_label = "Social Media Links" if LANG == "en" else "Social-Media-Links"
    social_media_links = st.text_area(social_label, value=st.session_state.get("social_media_links", ""), placeholder="Links to company social profiles" if LANG == "en" else "Links zu Social-Media-Profilen des Unternehmens")
    video_label = "Video Introduction Option" if LANG == "en" else "Option auf Videovorstellung"
    video_options = ["No", "Yes"] if LANG == "en" else ["Nein", "Ja"]
    video_introduction_option = st.selectbox(video_label, video_options, index=0)
    comments_label = "Comments (Internal)" if LANG == "en" else "Interne Anmerkungen"
    comments_internal = st.text_area(comments_label, value=st.session_state.get("comments_internal", ""), placeholder="Any internal comments or notes" if LANG == "en" else "Interne Anmerkungen oder Notizen")
    # Save all step 8 fields into session_state
    st.session_state["parsed_data_raw"] = parsed_data
    st.session_state["language_of_ad"] = language_of_ad
    st.session_state["translation_required"] = translation_required
    st.session_state["employer_branding_elements"] = employer_branding_elements
    st.session_state["desired_publication_channels"] = desired_publication_channels
    st.session_state["internal_job_id"] = internal_job_id
    st.session_state["ad_seniority_tone"] = ad_seniority_tone
    st.session_state["ad_length_preference"] = ad_length_preference
    st.session_state["deadline_urgency"] = deadline_urgency
    st.session_state["company_awards"] = company_awards
    st.session_state["diversity_inclusion_statement"] = diversity_inclusion_statement
    st.session_state["legal_disclaimers"] = legal_disclaimers
    st.session_state["social_media_links"] = social_media_links
    st.session_state["video_introduction_option"] = video_introduction_option
    st.session_state["comments_internal"] = comments_internal

# Main wizard runner – decides which step to show
def run_wizard():
    step = _clamp_step()
    _ensure_engine()  # Make sure engine is initialized
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
    # Show navigation buttons for current step
    _nav(step)

# Run the wizard
run_wizard()
