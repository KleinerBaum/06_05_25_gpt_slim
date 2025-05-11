from __future__ import annotations
import streamlit as st
import requests
# Vacalyser modules and utilities
from src.state.session_state import initialize_session_state
from src.logic.trigger_engine import TriggerEngine, build_default_graph
from src.processors import register_all_processors
from src.tools.file_tools import extract_text_from_file
from src.tools.scraping_tools import scrape_company_site
from src.utils.text_cleanup import clean_text
from src.config.keys import STEP_KEYS
from src.agents.vacancy_agent import auto_fill_job_spec
from src.utils.tool_registry import call_with_retry
from openai import OpenAI

# Initialize all expected session state keys (only runs once per session)
initialize_session_state()

def _ensure_engine() -> TriggerEngine:
    """Initialize TriggerEngine with default dependencies and processors (if not already)."""
    eng: TriggerEngine | None = st.session_state.get("trigger_engine")
    if eng is None:
        eng = TriggerEngine()
        build_default_graph(eng)
        register_all_processors(eng)
        st.session_state["trigger_engine"] = eng
    return eng

def _clamp_step() -> int:
    """Keep wizard_step within 1–8."""
    st.session_state["wizard_step"] = max(1, min(8, int(st.session_state.get("wizard_step", 1))))
    return st.session_state["wizard_step"]

def fetch_url_text(url: str) -> str:
    """Fetch content from URL and return cleaned text."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        st.warning(f"Failed to fetch URL: {exc}")
        return ""
    content_type = resp.headers.get("content-type", "").lower()
    # If HTML, use scraping tool to get readable text (e.g., page title & description)
    if "text/html" in content_type:
        data = scrape_company_site(url)
        if isinstance(data, dict):
            text = (data.get("title", "") or "") + "\n" + (data.get("description", "") or "")
        else:
            text = str(data)
    elif "pdf" in content_type:
        text = extract_text_from_file(resp.content, "file.pdf")
    elif "officedocument" in content_type or "msword" in content_type:
        text = extract_text_from_file(resp.content, "file.docx")
    else:
        text = resp.text
    return clean_text(text or "")

def match_and_store_keys(raw_text: str) -> None:
    """Fallback parser: extract fields by matching label patterns in text."""
    if not raw_text:
        return
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
        "city": "City",  # "City (Job Location):" sometimes abbreviated
        "team_structure": "Team Structure:",
        "role_description": "Role Description:",
        "reports_to": "Reports To:",
        "supervises": "Supervises:",
        "role_type": "Role Type:",
        "role_priority_projects": "Role Priority Projects:",
        "travel_requirements": "Travel Requirements:",
        "must_have_skills": "Requirements:",
        "nice_to_have_skills": "Preferred Skills:"
    }
    for key, label in labels.items():
        if label in raw_text:
            try:
                # Take text immediately after the label up to the next newline
                value = raw_text.split(label, 1)[1].split("\n", 1)[0].strip().rstrip(":;,.")
            except IndexError:
                continue
            if value:
                st.session_state[key] = value

def display_step_summary(step: int) -> None:
    """Show a collapsible summary of all filled fields so far, and list missing fields for the current step."""
    lang = st.session_state.get("lang", "English")
    # Gather all filled fields up to this step (exclude technical fields)
    filled = {}
    for s in range(1, step+1):
        for field in STEP_KEYS[s]:
            if field in ["input_url", "uploaded_file", "parsed_data_raw", "source_language"]:
                continue
            val = st.session_state.get(field)
            if val not in (None, "", []):
                filled[field] = val
    # Determine which fields in this step are missing
    missing_fields = [
        f for f in STEP_KEYS[step]
        if f not in ["input_url", "uploaded_file", "parsed_data_raw", "source_language"]
        and not st.session_state.get(f)
    ]
    # Summary expander for filled fields
    if filled:
        exp_label = "Zusammenfassung ausgefüllter Felder" if lang == "Deutsch" else "Summary of Filled Fields"
        with st.expander(exp_label, expanded=False):
            # Group summary by step sections for clarity
            for s in range(1, step):
                section_fields = [f for f in STEP_KEYS[s] if f in filled]
                if not section_fields:
                    continue
                # Section title (translated)
                section_titles = {
                    1: "Grunddaten" if lang == "Deutsch" else "Basic Info",
                    2: "Job & Unternehmen" if lang == "Deutsch" else "Job & Company Info",
                    3: "Rollenbeschreibung" if lang == "Deutsch" else "Role Definition",
                    4: "Aufgaben" if lang == "Deutsch" else "Tasks & Responsibilities",
                    5: "Fähigkeiten" if lang == "Deutsch" else "Skills & Competencies",
                    6: "Vergütung & Benefits" if lang == "Deutsch" else "Compensation & Benefits",
                    7: "Bewerbungsprozess" if lang == "Deutsch" else "Recruitment Process",
                    8: "Weitere Details" if lang == "Deutsch" else "Additional Details"
                }
                st.markdown(f"**{section_titles.get(s, '')}:**")
                for field in section_fields:
                    # Human-readable label (with basic formatting)
                    label = field.replace("_", " ").title().replace("Hq", "HQ").replace("Url", "URL")
                    # Translate key labels for summary output
                    translations = {
                        # Basic Info
                        "Company Name": "Unternehmensname",
                        "Brand Name (If Different)": "Markenname (falls abweichend)",
                        "Headquarters Location": "Hauptsitz",
                        "City (Job Location)": "Einsatzort",
                        "Company Website": "Webseite",
                        "Company Size": "Unternehmensgröße",
                        "Industry Sector": "Branche",
                        "Job Type": "Beschäftigungsart",
                        "Contract Type": "Vertragsart",
                        "Job Level": "Karrierestufe",
                        "Team Structure": "Teamstruktur",
                        "Date Of Employment Start": "Startdatum",
                        # Role Definition
                        "Role Description": "Rollenbeschreibung",
                        "Reports To": "Berichtet an",
                        "Supervises": "Führt",
                        "Role Type": "Rollentyp",
                        "Role Performance Metrics": "Leistungskennzahlen",
                        "Role Priority Projects": "Prioritätsprojekte",
                        "Travel Requirements": "Reiseanforderungen",
                        "Work Schedule": "Arbeitszeit",
                        "Decision Making Authority": "Entscheidungsbefugnis",
                        "Role Keywords": "Rollen-Schlüsselwörter",
                        # Tasks
                        "Task List": "Aufgabenliste",
                        "Key Responsibilities": "Hauptverantwortlichkeiten",
                        "Technical Tasks": "Technische Aufgaben",
                        "Managerial Tasks": "Führungsaufgaben",
                        "Administrative Tasks": "Administrative Aufgaben",
                        "Customer Facing Tasks": "Kundenkontakte",
                        "Internal Reporting Tasks": "Interne Berichte",
                        "Performance Tasks": "Leistungsaufgaben",
                        "Innovation Tasks": "Innovationsaufgaben",
                        "Task Prioritization": "Aufgabenpriorisierung",
                        # Skills
                        "Must Have Skills": "Erforderliche Fähigkeiten",
                        "Hard Skills": "Fachliche Fähigkeiten",
                        "Nice To Have Skills": "Wünschenswerte Fähigkeiten",
                        "Soft Skills": "Soft Skills",
                        "Language Requirements": "Sprachkenntnisse",
                        "Tool Proficiency": "Tool-Kenntnisse",
                        "Technical Stack": "Technologie-Stack",
                        "Domain Expertise": "Domänenkenntnisse",
                        "Leadership Competencies": "Führungsqualitäten",
                        "Certifications Required": "Zertifizierungen",
                        "Industry Experience": "Branchenerfahrung",
                        "Analytical Skills": "Analytische Fähigkeiten",
                        "Communication Skills": "Kommunikationsfähigkeiten",
                        "Project Management Skills": "Projektmanagement-Fähigkeiten",
                        "Soft Requirement Details": "Weitere Anforderungen",
                        "Visa Sponsorship": "Visum-Sponsoring",
                        # Compensation
                        "Salary Range": "Gehaltsrahmen",
                        "Currency": "Währung",
                        "Pay Frequency": "Zahlungshäufigkeit",
                        "Bonus Scheme": "Bonusregelung",
                        "Commission Structure": "Provisionsstruktur",
                        "Vacation Days": "Urlaubstage",
                        "Remote Work Policy": "Remote-Arbeit",
                        "Flexible Hours": "Flexible Arbeitszeiten",
                        "Relocation Assistance": "Umzugshilfe",
                        "Childcare Support": "Kinderbetreuung",
                        "Travel Requirements Link": "Reiserichtlinien-Link",
                        # Recruitment
                        "Recruitment Steps": "Ablauf Bewerbung",
                        "Number Of Interviews": "Anzahl Interviews",
                        "Assessment Tests": "Einstellungstests",
                        "Interview Format": "Interview-Format",
                        "Recruitment Timeline": "Einstellungszeitplan",
                        "Onboarding Process Overview": "Onboarding-Prozess",
                        "Recruitment Contact Email": "Kontakt E-Mail",
                        "Recruitment Contact Phone": "Kontakt Telefon",
                        "Application Instructions": "Bewerbungsanweisungen",
                        # Additional
                        "Ad Seniority Tone": "Ton der Anzeige",
                        "Ad Length Preference": "Länge der Anzeige",
                        "Language Of Ad": "Sprache der Anzeige",
                        "Translation Required": "Übersetzung benötigt",
                        "Desired Publication Channels": "Veröffentlichungskanäle",
                        "Employer Branding Elements": "Employer-Branding-Elemente",
                        "Diversity Inclusion Statement": "Diversity-Statement",
                        "Legal Disclaimers": "Rechtliche Hinweise",
                        "Company Awards": "Auszeichnungen",
                        "Social Media Links": "Social-Media-Links",
                        "Video Introduction Option": "Option Videovorstellung",
                        "Internal Job Id": "Interne Job-ID",
                        "Deadline Urgency": "Dringlichkeit",
                        "Comments Internal": "Interne Notizen"
                    }
                    if lang == "Deutsch":
                        label = translations.get(label, label)
                    st.write(f"- **{label}:** {filled[field]}")
    # Show list of missing fields for this step (priority up to 10)
    if missing_fields:
        # Translate field names for the message
        missing_labels = []
        for field in missing_fields[:10]:
            label = field.replace("_", " ").title().replace("Hq", "HQ").replace("Url", "URL")
            if lang == "Deutsch":
                translations = {
                    "Company Name": "Unternehmensname", "Brand Name (If Different)": "Markenname",
                    "Headquarters Location": "Hauptsitz", "City (Job Location)": "Einsatzort",
                    "Company Website": "Webseite", "Company Size": "Unternehmensgröße",
                    "Industry Sector": "Branche", "Job Type": "Beschäftigungsart",
                    "Contract Type": "Vertragsart", "Job Level": "Karrierestufe",
                    "Team Structure": "Teamstruktur", "Date Of Employment Start": "Startdatum",
                    "Role Description": "Rollenbeschreibung", "Reports To": "Vorgesetzter",
                    "Supervises": "Unterstellte", "Role Type": "Rollentyp",
                    "Role Performance Metrics": "Leistungskennzahlen", "Role Priority Projects": "Prioritätsprojekte",
                    "Travel Requirements": "Reiseanforderungen", "Work Schedule": "Arbeitszeit",
                    "Decision Making Authority": "Entscheidungsbefugnis", "Role Keywords": "Rollen-Schlüsselwörter",
                    "Task List": "Aufgabenliste", "Key Responsibilities": "Hauptverantwortlichkeiten",
                    "Technical Tasks": "Technische Aufgaben", "Managerial Tasks": "Führungsaufgaben",
                    "Administrative Tasks": "Administrative Aufgaben", "Customer Facing Tasks": "Kundenkontakt",
                    "Internal Reporting Tasks": "Interne Berichte", "Performance Tasks": "Leistungsaufgaben",
                    "Innovation Tasks": "Innovationsaufgaben", "Task Prioritization": "Aufgabenpriorisierung",
                    "Must Have Skills": "Erforderliche Fähigkeiten", "Hard Skills": "Fachliche Fähigkeiten",
                    "Nice To Have Skills": "Wünschenswerte Fähigkeiten", "Soft Skills": "Soft Skills",
                    "Language Requirements": "Sprachkenntnisse", "Tool Proficiency": "Tool-Kenntnisse",
                    "Technical Stack": "Technologie-Stack", "Domain Expertise": "Branchendomain",
                    "Leadership Competencies": "Führungsqualitäten", "Certifications Required": "Zertifizierungen",
                    "Industry Experience": "Branchenerfahrung", "Analytical Skills": "Analytische Fähigkeiten",
                    "Communication Skills": "Kommunikationsfähigkeiten", "Project Management Skills": "Projektmanagement",
                    "Soft Requirement Details": "Weitere Anforderungen", "Visa Sponsorship": "Visum-Unterstützung",
                    "Salary Range": "Gehaltsrahmen", "Currency": "Währung", "Pay Frequency": "Zahlungshäufigkeit",
                    "Bonus Scheme": "Bonusregelung", "Commission Structure": "Provisionsstruktur",
                    "Vacation Days": "Urlaubstage", "Remote Work Policy": "Remote-Policy",
                    "Flexible Hours": "Flexible Arbeitszeiten", "Relocation Assistance": "Umzugshilfe",
                    "Childcare Support": "Kinderbetreuung", "Travel Requirements Link": "Reiseinfo-Link",
                    "Recruitment Steps": "Prozessschritte", "Number Of Interviews": "Anzahl Interviews",
                    "Assessment Tests": "Tests", "Interview Format": "Interview-Format",
                    "Recruitment Timeline": "Zeitplan", "Onboarding Process Overview": "Onboarding-Überblick",
                    "Recruitment Contact Email": "Kontakt E-Mail", "Recruitment Contact Phone": "Kontakt Telefon",
                    "Application Instructions": "Bewerbungsanweisungen", "Ad Seniority Tone": "Ton der Anzeige",
                    "Ad Length Preference": "Länge der Anzeige", "Language Of Ad": "Sprache der Anzeige",
                    "Translation Required": "Übersetzung", "Desired Publication Channels": "Kanäle",
                    "Employer Branding Elements": "Branding-Elemente", "Diversity Inclusion Statement": "Diversity-Statement",
                    "Legal Disclaimers": "Rechtliche Hinweise", "Company Awards": "Auszeichnungen",
                    "Social Media Links": "Social-Media-Links", "Video Introduction Option": "Video-Option",
                    "Internal Job Id": "Interne Job-ID", "Deadline Urgency": "Dringlichkeit",
                    "Comments Internal": "Interne Kommentare"
                }
                label = translations.get(label, label)
            missing_labels.append(label)
        msg = ("Bitte füllen Sie noch folgende Felder aus: " if lang == "Deutsch" else "Please provide details for: ")
        st.info(msg + ", ".join(missing_labels))

# Step 1: Start Discovery (job title & source input)
def start_discovery_page():
    # Language toggle (persists in session_state['lang'])
    lang = st.session_state.get("lang", "English")
    # Introduction text
    if lang == "Deutsch":
        st.title("🚀 Erstelle die perfekte Stellenbeschreibung")
        st.subheader("Von der ersten Idee bis zur fertigen Ausschreibung.")
        intro_text = (
            "Willkommen bei **RoleCraft**.\n\n"
            "Starte mit einem Jobtitel oder lade eine Anzeige hoch.\n"
            "Unser KI-gestützter Wizard analysiert, ergänzt fehlende Infos und führt dich sicher zum perfekten Profil."
        )
        btn_job = "➕ Jobtitel eingeben"
        btn_upload = "📂 PDF / DOCX hochladen"
    else:
        st.title("🚀 Create the Perfect Job Description")
        st.subheader("From the first idea to a fully crafted profile.")
        intro_text = (
            "Welcome to **RoleCraft**.\n\n"
            "Start with a job title or upload an ad.\n"
            "Our AI-powered wizard analyzes, fills gaps, and guides you seamlessly to a perfect profile."
        )
        btn_job = "➕ Enter Job Title"
        btn_upload = "📂 Upload PDF / DOCX"
    st.markdown(intro_text)
    st.header("Vacalyser – Start Discovery")
    st.write(
        "Gib einen Jobtitel ein und entweder eine URL zu einer bestehenden Stellenanzeige oder lade eine Stellenbeschreibung hoch. "
        "Der Assistent analysiert die Inhalte und füllt relevante Felder automatisch aus."
        if lang == "Deutsch" else
        "Enter a job title and either a link to an existing job ad or upload a job description file. "
        "The wizard will analyze the content and auto-fill relevant fields where possible."
    )
    col1, col2 = st.columns(2)
    with col1:
        job_title = st.text_input(btn_job, value=st.session_state.get("job_title", ""),
                                  placeholder="z.B. Senior Data Scientist" if lang == "Deutsch" else "e.g. Senior Data Scientist")
        if job_title:
            st.session_state["job_title"] = job_title
        input_url = st.text_input("🔗 Stellenanzeigen-URL (optional)" if lang == "Deutsch" else "🔗 Job Ad URL (optional)",
                                  value=st.session_state.get("input_url", ""))
        if input_url:
            st.session_state["input_url"] = input_url
    with col2:
        uploaded_file = st.file_uploader(btn_upload, type=["pdf", "docx", "txt"])
        if uploaded_file is not None:
            file_bytes = uploaded_file.read()
            raw_text = extract_text_from_file(file_bytes, uploaded_file.name)
            raw_text = clean_text(raw_text)
            if raw_text:
                st.session_state["uploaded_file"] = raw_text
                st.success("✅ Datei hochgeladen und Text extrahiert." if lang == "Deutsch" else "✅ File uploaded and text extracted.")
            else:
                st.error("❌ Konnte den Text aus der Datei nicht extrahieren." if lang == "Deutsch" else "❌ Failed to extract text from the uploaded file.")
    analyze_clicked = st.button("🔎 Analysieren" if lang == "Deutsch" else "🔎 Analyze Sources")
    if analyze_clicked:
        raw_text = ""
        if st.session_state.get("uploaded_file"):
            raw_text = st.session_state["uploaded_file"]
        elif st.session_state.get("input_url"):
            raw_text = fetch_url_text(st.session_state["input_url"])
        if not raw_text:
            st.warning("⚠️ Bitte gib eine gültige URL oder lade eine Datei hoch, bevor du analysierst." if lang == "Deutsch"
                       else "⚠️ Please provide a valid URL or upload a file before analysis.")
        else:
            st.session_state["parsed_data_raw"] = raw_text
            # Simple language detection for the source text (to default output language)
            sample = raw_text[:500].lower()
            if sample.count(" der ") + sample.count(" die ") + sample.count(" und ") > sample.count(" the "):
                st.session_state["source_language"] = "Deutsch"
            else:
                st.session_state["source_language"] = "English"
            try:
                # Use AI assistant to extract structured job info
                result = auto_fill_job_spec(
                    input_url=st.session_state.get("input_url", ""),
                    file_bytes=raw_text.encode('utf-8') if raw_text else None,
                    file_name=uploaded_file.name if uploaded_file else "",
                    summary_quality="standard"
                )
                if result:
                    # Populate session_state with extracted fields
                    for key, value in result.items():
                        if key in st.session_state and value not in (None, ""):
                            # Join list outputs into multiline string if necessary
                            if isinstance(value, list):
                                st.session_state[key] = "\n".join(str(v) for v in value if v)
                            else:
                                st.session_state[key] = value
                    # Trigger engine for all fields set by AI extraction
                    for k in result.keys():
                        _ensure_engine().notify_change(k, st.session_state)
                    st.success("🎯 Analyse abgeschlossen! Wichtige Felder wurden automatisch ausgefüllt." if lang == "Deutsch"
                               else "🎯 Analysis complete! Key details have been auto-filled.")
                else:
                    # Fallback: simple keyword-based extraction
                    match_and_store_keys(raw_text)
                    st.info("⚠️ KI-Analyse nicht verfügbar – wichtige Felder anhand von Schlagworten ausgefüllt." if lang == "Deutsch"
                            else "⚠️ AI extraction not available – applied basic extraction for key fields.")
                st.session_state.setdefault("trace_events", []).append("Auto-extracted fields from provided job description.")
            except Exception as e:
                st.error(f"❌ Analyse fehlgeschlagen: {e}" if lang == "Deutsch" else f"❌ Analysis failed: {e}")

# Steps 2–7: Static form renderers (each returns a dict of field values)
def render_step2_static():
    lang = st.session_state.get("lang", "English")
    st.title("Schritt 2: Grundlegende Stellen- & Firmendaten" if lang == "Deutsch" else "Step 2: Basic Job & Company Info")
    display_step_summary(2)
    company_name = st.text_input("Unternehmensname" if lang == "Deutsch" else "Company Name",
                                 value=st.session_state.get("company_name", ""),
                                 placeholder="z.B. Tech Corp GmbH" if lang == "Deutsch" else "e.g. Tech Corp Ltd.",
                                 help="Name des einstellenden Unternehmens." if lang == "Deutsch" else "Official name of the hiring company.")
    brand_name = st.text_input("Markenname (falls abweichend)" if lang == "Deutsch" else "Brand Name (if different)",
                               value=st.session_state.get("brand_name", ""),
                               placeholder="z.B. Mutterfirma AG" if lang == "Deutsch" else "e.g. Parent Company Inc.",
                               help="Falls unter einem anderen Marken- oder Firmennamen ausgeschrieben." if lang == "Deutsch"
                                    else "If the job is advertised under a different brand or subsidiary name.")
    headquarters_location = st.text_input("Hauptsitz (Ort)" if lang == "Deutsch" else "Headquarters Location",
                                         value=st.session_state.get("headquarters_location", ""),
                                         placeholder="z.B. Berlin, Deutschland" if lang == "Deutsch" else "e.g. Berlin, Germany",
                                         help="Stadt und Land des Unternehmenshauptsitzes." if lang == "Deutsch"
                                              else "City and country where the company is headquartered.")
    city = st.text_input("Stadt (Einsatzort)" if lang == "Deutsch" else "City (Job Location)",
                         value=st.session_state.get("city", ""),
                         placeholder="z.B. München" if lang == "Deutsch" else "e.g. Munich",
                         help="Ort, an dem die Stelle angesiedelt ist." if lang == "Deutsch" else "City or location where the job will be based.")
    company_website = st.text_input("Webseite des Unternehmens" if lang == "Deutsch" else "Company Website",
                                    value=st.session_state.get("company_website", ""),
                                    placeholder="e.g. https://company.com",
                                    help="URL der offiziellen Unternehmenswebsite." if lang == "Deutsch" else "Official company website URL.")
    company_size = st.text_input("Unternehmensgröße (Mitarbeiterzahl)" if lang == "Deutsch" else "Company Size (employees)",
                                 value=st.session_state.get("company_size", ""),
                                 placeholder="z.B. 500" if lang == "Deutsch" else "e.g. 500",
                                 help="Ungefähre Anzahl der Mitarbeiter im Unternehmen." if lang == "Deutsch"
                                      else "Approximate number of employees in the company.")
    industry_sector = st.text_input("Branche" if lang == "Deutsch" else "Industry Sector",
                                    value=st.session_state.get("industry_sector", ""),
                                    placeholder="z.B. IT-Dienstleistungen" if lang == "Deutsch" else "e.g. IT Services",
                                    help="Branche bzw. Industriezweig des Unternehmens." if lang == "Deutsch"
                                         else "Industry or sector in which the company operates.")
    job_type = st.text_input("Beschäftigungsart" if lang == "Deutsch" else "Job Type",
                             value=st.session_state.get("job_type", ""),
                             placeholder="z.B. Vollzeit" if lang == "Deutsch" else "e.g. Full-time",
                             help="Art der Anstellung (Vollzeit, Teilzeit, Praktikum etc.)." if lang == "Deutsch"
                                  else "Type of employment (Full-time, Part-time, Internship, etc.).")
    contract_type = st.text_input("Vertragsart" if lang == "Deutsch" else "Contract Type",
                                  value=st.session_state.get("contract_type", ""),
                                  placeholder="z.B. Unbefristet" if lang == "Deutsch" else "e.g. Permanent",
                                  help="Vertragsform (unbefristet, befristet, freiberuflich etc.)." if lang == "Deutsch"
                                       else "Type of contract (Permanent, Fixed-term, Freelance, etc.).")
    job_level = st.text_input("Karrierestufe" if lang == "Deutsch" else "Job Level",
                              value=st.session_state.get("job_level", ""),
                              placeholder="z.B. Senior" if lang == "Deutsch" else "e.g. Senior",
                              help="Senioritäts-/Erfahrungsstufe der Position (Junior, Senior, etc.)." if lang == "Deutsch"
                                   else "Seniority level of the position (e.g. Junior, Mid, Senior).")
    team_structure = st.text_input("Teamstruktur" if lang == "Deutsch" else "Team Structure",
                                   value=st.session_state.get("team_structure", ""),
                                   placeholder="z.B. unterstellt dem CTO; leitet 5 Entwickler" if lang == "Deutsch"
                                               else "e.g. Reports to CTO; leads 5 engineers",
                                   help="Aufbau des Teams: Vorgesetzte Person und unterstellte Mitarbeiter (falls zutreffend)." if lang == "Deutsch"
                                        else "Overview of team context (who this role reports to and who it supervises, if applicable).")
    date_of_start = st.text_input("Bevorzugtes Startdatum" if lang == "Deutsch" else "Preferred Start Date",
                                  value=st.session_state.get("date_of_employment_start", ""),
                                  placeholder="z.B. sofort oder 01/2024" if lang == "Deutsch" else "e.g. ASAP or Jan 2024",
                                  help="Gewünschter oder erwarteter Eintrittstermin." if lang == "Deutsch"
                                       else "Desired or expected start date for the position.")
    return {
        "company_name": company_name,
        "brand_name": brand_name,
        "headquarters_location": headquarters_location,
        "city": city,
        "company_website": company_website,
        "company_size": company_size,
        "industry_sector": industry_sector,
        "job_type": job_type,
        "contract_type": contract_type,
        "job_level": job_level,
        "team_structure": team_structure,
        "date_of_employment_start": date_of_start
    }

def render_step3_static():
    lang = st.session_state.get("lang", "English")
    st.title("Schritt 3: Rollenbeschreibung & Details" if lang == "Deutsch" else "Step 3: Role Definition & Details")
    display_step_summary(3)
    role_description = st.text_area("Rollenbeschreibung" if lang == "Deutsch" else "Role Description",
                                    value=st.session_state.get("role_description", ""),
                                    placeholder="z.B. Überblick über Zweck und Verantwortung der Rolle..." if lang == "Deutsch"
                                                else "e.g. Overview of the role's purpose, scope, and main objectives...",
                                    help="Kurze Beschreibung des Ziels und Umfangs der Rolle." if lang == "Deutsch"
                                         else "High-level summary of the role’s purpose and scope.")
    reports_to = st.text_input("Berichtet an" if lang == "Deutsch" else "Reports To",
                               value=st.session_state.get("reports_to", ""),
                               placeholder="z.B. Leiter Technik" if lang == "Deutsch" else "e.g. Head of Engineering",
                               help="Titel/Position der vorgesetzten Person für diese Rolle." if lang == "Deutsch"
                                    else "Job title of the person this role reports to.")
    supervises = st.text_input("Führt (unterstellt)" if lang == "Deutsch" else "Supervises",
                               value=st.session_state.get("supervises", ""),
                               placeholder="z.B. 5 Entwickler" if lang == "Deutsch" else "e.g. 5 Engineers",
                               help="Anzahl und Art der Mitarbeiter, die diese Position führt (falls zutreffend)." if lang == "Deutsch"
                                    else "Roles or number of people this position manages (if any).")
    role_type = st.text_input("Rollentyp" if lang == "Deutsch" else "Role Type",
                              value=st.session_state.get("role_type", ""),
                              placeholder="z.B. neue Stelle oder Nachbesetzung" if lang == "Deutsch"
                                          else "e.g. Newly created position or Replacement",
                              help="Kategorie der Rolle, z.B. neu geschaffen, Nachbesetzung, Praktikum etc." if lang == "Deutsch"
                                   else "Type/category of the role (new headcount, backfill, internship, etc.).")
    role_performance_metrics = st.text_area("Leistungskennzahlen" if lang == "Deutsch" else "Role Performance Metrics",
                                            value=st.session_state.get("role_performance_metrics", ""),
                                            placeholder="z.B. Umsatzziele, Kundenzufriedenheitsquote..." if lang == "Deutsch"
                                                        else "e.g. Sales targets, Customer satisfaction rating, etc.",
                                            help="Woran der Erfolg in dieser Rolle gemessen wird (KPIs)." if lang == "Deutsch"
                                                 else "Key performance indicators for success in this role.")
    role_priority_projects = st.text_area("Prioritätsprojekte" if lang == "Deutsch" else "Role Priority Projects",
                                          value=st.session_state.get("role_priority_projects", ""),
                                          placeholder="z.B. Projekt Apollo Launch, Redesign der Plattform..." if lang == "Deutsch"
                                                      else "e.g. Project Apollo launch, Core product redesign...",
                                          help="Wichtige aktuelle Projekte oder Initiativen für diese Rolle." if lang == "Deutsch"
                                               else "Current key projects or initiatives this role will focus on.")
    travel_requirements = st.text_input("Reiseanforderungen" if lang == "Deutsch" else "Travel Requirements",
                                        value=st.session_state.get("travel_requirements", ""),
                                        placeholder="z.B. Gelegentliche Reisen (10%)" if lang == "Deutsch"
                                                    else "e.g. Occasional travel (10%)",
                                        help="Notwendige Reisetätigkeit in dieser Rolle (Häufigkeit/Prozentsatz)." if lang == "Deutsch"
                                             else "Extent of travel required for the role (e.g., 10% or 'occasional').")
    work_schedule = st.text_input("Arbeitszeiten" if lang == "Deutsch" else "Work Schedule",
                                  value=st.session_state.get("work_schedule", ""),
                                  placeholder="z.B. Mo-Fr 9-17 Uhr" if lang == "Deutsch"
                                              else "e.g. Mon-Fri 9-5, or Shift-based",
                                  help="Reguläre Arbeitszeiten oder Schichtmodell." if lang == "Deutsch"
                                       else "Normal working hours or shift schedule for the role.")
    decision_making_authority = st.text_area("Entscheidungsbefugnis" if lang == "Deutsch" else "Decision Making Authority",
                                             value=st.session_state.get("decision_making_authority", ""),
                                             placeholder="z.B. Kann Budget bis 50k freigeben" if lang == "Deutsch"
                                                         else "e.g. Can approve budgets up to $50k; final say on team hires",
                                             help="Welche Entscheidungen diese Rolle eigenständig treffen darf." if lang == "Deutsch"
                                                  else "Level of decisions the role can make independently.")
    role_keywords = st.text_input("Schlüsselwörter zur Rolle" if lang == "Deutsch" else "Role Keywords",
                                  value=st.session_state.get("role_keywords", ""),
                                  placeholder="z.B. Data Science, KI, Python" if lang == "Deutsch"
                                              else "e.g. data science, machine learning, Python",
                                  help="Stichworte zur Rolle (für Suche/SEO)." if lang == "Deutsch"
                                       else "Keywords related to this role for search/SEO purposes.")
    return {
        "role_description": role_description,
        "reports_to": reports_to,
        "supervises": supervises,
        "role_type": role_type,
        "role_performance_metrics": role_performance_metrics,
        "role_priority_projects": role_priority_projects,
        "travel_requirements": travel_requirements,
        "work_schedule": work_schedule,
        "decision_making_authority": decision_making_authority,
        "role_keywords": role_keywords
    }

def render_step4_static():
    lang = st.session_state.get("lang", "English")
    st.title("Schritt 4: Aufgaben & Verantwortlichkeiten" if lang == "Deutsch" else "Step 4: Tasks & Responsibilities")
    display_step_summary(4)
    task_list = st.text_area("Aufgabenliste" if lang == "Deutsch" else "Task List",
                             value=st.session_state.get("task_list", ""),
                             placeholder=("z.B.\n- Entwicklung von Feature X und Y\n- Abstimmung mit dem Produktteam\n- Pflege der Dokumentation") if lang == "Deutsch"
                                         else ("e.g.\n- Develop features X and Y\n- Coordinate with product team\n- Maintain documentation"),
                             help="Gesamtliste der wichtigsten Aufgaben und Pflichten in dieser Rolle." if lang == "Deutsch"
                                  else "Overall list of key tasks and duties for this role.")
    key_responsibilities = st.text_area("Hauptverantwortlichkeiten" if lang == "Deutsch" else "Key Responsibilities",
                                        value=st.session_state.get("key_responsibilities", ""),
                                        placeholder=("z.B.\n- Strategische Planung fürs Team\n- Sicherstellung der fristgerechten Projektlieferung") if lang == "Deutsch"
                                                    else ("e.g.\n- Strategic planning for the team\n- Ensuring timely project delivery"),
                                        help="Wichtigste Verantwortungsbereiche in dieser Position." if lang == "Deutsch"
                                             else "Major areas of responsibility for this role.")
    technical_tasks = st.text_area("Technische Aufgaben" if lang == "Deutsch" else "Technical Tasks",
                                   value=st.session_state.get("technical_tasks", ""),
                                   placeholder=("z.B.\n- Code-Reviews durchführen\n- Systemarchitektur entwerfen") if lang == "Deutsch"
                                               else ("e.g.\n- Conduct code reviews\n- Design system architecture"),
                                   help="Technische Tätigkeiten, die zu dieser Rolle gehören." if lang == "Deutsch"
                                        else "Tasks of a technical nature associated with this role.")
    managerial_tasks = st.text_area("Führungsaufgaben" if lang == "Deutsch" else "Managerial Tasks",
                                    value=st.session_state.get("managerial_tasks", ""),
                                    placeholder=("z.B.\n- Teammitglieder anleiten\n- Mitarbeitergespräche führen") if lang == "Deutsch"
                                                else ("e.g.\n- Mentor junior staff\n- Conduct performance evaluations"),
                                    help="Aufgaben im Bereich Teamführung/Projektleitung in dieser Rolle." if lang == "Deutsch"
                                         else "Tasks related to managing people or projects in this role.")
    administrative_tasks = st.text_area("Administrative Aufgaben" if lang == "Deutsch" else "Administrative Tasks",
                                        value=st.session_state.get("administrative_tasks", ""),
                                        placeholder=("z.B.\n- Wöchentliche Status-Reports erstellen\n- Dokumentation pflegen") if lang == "Deutsch"
                                                    else ("e.g.\n- Prepare weekly status reports\n- Maintain documentation"),
                                        help="Verwaltungsaufgaben oder Routineprozesse dieser Rolle." if lang == "Deutsch"
                                             else "Administrative or routine tasks associated with the role.")
    customer_facing_tasks = st.text_area("Kundenkontakt & -aufgaben" if lang == "Deutsch" else "Customer Facing Tasks",
                                         value=st.session_state.get("customer_facing_tasks", ""),
                                         placeholder=("z.B.\n- Präsentation von Lösungen beim Kunden\n- Beantwortung von Kundenanfragen") if lang == "Deutsch"
                                                     else ("e.g.\n- Present solutions to clients\n- Handle client inquiries"),
                                         help="Aufgaben mit direkter Interaktion mit Kunden/Klienten." if lang == "Deutsch"
                                              else "Tasks involving direct interaction with clients or customers.")
    internal_reporting_tasks = st.text_area("Interne Berichtsaufgaben" if lang == "Deutsch" else "Internal Reporting Tasks",
                                            value=st.session_state.get("internal_reporting_tasks", ""),
                                            placeholder=("z.B.\n- Monatliche Berichte ans Management") if lang == "Deutsch"
                                                        else ("e.g.\n- Monthly progress report to management"),
                                            help="Interne Reporting-/Dokumentationspflichten in dieser Rolle." if lang == "Deutsch"
                                                 else "Internal reporting duties (reports or updates to management).")
    performance_tasks = st.text_area("Leistungsaufgaben" if lang == "Deutsch" else "Performance Tasks",
                                     value=st.session_state.get("performance_tasks", ""),
                                     placeholder=("z.B.\n- Arbeitsabläufe optimieren zur Effizienzsteigerung") if lang == "Deutsch"
                                                 else ("e.g.\n- Optimize workflows to improve efficiency"),
                                     help="Aufgaben zur Überwachung oder Steigerung der Leistung." if lang == "Deutsch"
                                          else "Tasks aimed at maintaining or improving performance metrics.")
    innovation_tasks = st.text_area("Innovationsaufgaben" if lang == "Deutsch" else "Innovation Tasks",
                                    value=st.session_state.get("innovation_tasks", ""),
                                    placeholder=("z.B.\n- Erforschung neuer Technologien zur Produktverbesserung") if lang == "Deutsch"
                                                else ("e.g.\n- Research new technologies for product improvement"),
                                    help="Aufgaben mit Fokus auf Innovation oder Verbesserungen." if lang == "Deutsch"
                                         else "Tasks focused on innovation, R&D, or process improvements.")
    task_prioritization = st.text_area("Aufgabenpriorisierung" if lang == "Deutsch" else "Task Prioritization",
                                       value=st.session_state.get("task_prioritization", ""),
                                       placeholder=("z.B. Höchste Priorität für Kundenprojekte, danach interne Optimierungen") if lang == "Deutsch"
                                                   else ("e.g. Highest priority to client projects, then internal improvements"),
                                       help="Informationen dazu, welche Aufgaben Priorität haben." if lang == "Deutsch"
                                            else "Information on how tasks are ranked or prioritized in importance.")
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
        "task_prioritization": task_prioritization
    }

def render_step5_static():
    lang = st.session_state.get("lang", "English")
    st.title("Schritt 5: Fähigkeiten & Kompetenzen" if lang == "Deutsch" else "Step 5: Skills & Competencies")
    display_step_summary(5)
    must_have_skills = st.text_area("Erforderliche Fähigkeiten" if lang == "Deutsch" else "Must-Have Skills",
                                    value=st.session_state.get("must_have_skills", ""),
                                    placeholder="z.B.\nPython; SQL; Maschinelles Lernen" if lang == "Deutsch"
                                                else "e.g.\nPython; SQL; Machine Learning",
                                    help="Unverzichtbare Fähigkeiten oder Qualifikationen für die Rolle." if lang == "Deutsch"
                                         else "Crucial skills or qualifications required for the role.")
    hard_skills = st.text_area("Fachliche (Hard) Skills" if lang == "Deutsch" else "Hard Skills",
                               value=st.session_state.get("hard_skills", ""),
                               placeholder="z.B.\nDatenanalyse; Cloud-Computing" if lang == "Deutsch"
                                           else "e.g.\nData analysis; Cloud computing",
                               help="Konkrete fachliche/technische Fähigkeiten für den Job." if lang == "Deutsch"
                                    else "Specific technical or job-related skills needed.")
    nice_to_have_skills = st.text_area("Wünschenswerte Fähigkeiten" if lang == "Deutsch" else "Nice-to-Have Skills",
                                       value=st.session_state.get("nice_to_have_skills", ""),
                                       placeholder="z.B.\nDocker; Tableau" if lang == "Deutsch"
                                                   else "e.g.\nDocker; Tableau",
                                       help="Zusätzliche Fähigkeiten, die vorteilhaft wären, aber nicht zwingend erforderlich." if lang == "Deutsch"
                                            else "Skills that are advantageous but not strictly required.")
    soft_skills = st.text_area("Soft Skills" if lang == "Deutsch" else "Soft Skills",
                               value=st.session_state.get("soft_skills", ""),
                               placeholder="z.B.\nTeamführung; Kommunikation" if lang == "Deutsch"
                                           else "e.g.\nTeam leadership; Communication",
                               help="Zwischenmenschliche und persönliche Kompetenzen." if lang == "Deutsch"
                                    else "Interpersonal or personal attributes (communication, teamwork, etc.).")
    language_requirements = st.text_input("Sprachanforderungen" if lang == "Deutsch" else "Language Requirements",
                                          value=st.session_state.get("language_requirements", ""),
                                          placeholder="z.B. Fließend Deutsch, Englisch-Grundkenntnisse" if lang == "Deutsch"
                                                      else "e.g. Fluent German, Basic English",
                                          help="Erforderliche Sprachkenntnisse und -niveaus." if lang == "Deutsch"
                                               else "Required languages and proficiency levels for the role.")
    tool_proficiency = st.text_input("Tool-Kenntnisse" if lang == "Deutsch" else "Tool Proficiency",
                                     value=st.session_state.get("tool_proficiency", ""),
                                     placeholder="z.B. Excel, Jira, Git" if lang == "Deutsch"
                                                 else "e.g. Excel, Jira, Git",
                                     help="Software-Tools oder Plattformen, die beherrscht werden sollten." if lang == "Deutsch"
                                          else "Software tools or platforms the candidate should be proficient with.")
    technical_stack = st.text_input("Technologie-Stack" if lang == "Deutsch" else "Technical Stack",
                                    value=st.session_state.get("technical_stack", ""),
                                    placeholder="z.B. AWS, Docker, Kubernetes" if lang == "Deutsch"
                                                else "e.g. AWS, Docker, Kubernetes",
                                    help="Technologien und Frameworks, die in dieser Rolle eingesetzt werden." if lang == "Deutsch"
                                         else "Technologies and frameworks used in this role.")
    domain_expertise = st.text_input("Branchenerfahrung" if lang == "Deutsch" else "Domain Expertise",
                                     value=st.session_state.get("domain_expertise", ""),
                                     placeholder="z.B. Erfahrung in der Finanzbranche" if lang == "Deutsch"
                                                 else "e.g. Experience in finance industry",
                                     help="Erfahrung oder Fachwissen in einer bestimmten Branche/Domäne." if lang == "Deutsch"
                                          else "Experience or knowledge in a specific industry domain.")
    leadership_competencies = st.text_input("Führungsqualitäten" if lang == "Deutsch" else "Leadership Competencies",
                                            value=st.session_state.get("leadership_competencies", ""),
                                            placeholder="z.B. Teamentwicklung; Konfliktlösung" if lang == "Deutsch"
                                                        else "e.g. Team building; Conflict resolution",
                                            help="Wichtige Führungs- oder Managementfähigkeiten (falls relevant)." if lang == "Deutsch"
                                                 else "Key leadership or managerial skills required (if applicable).")
    certifications_required = st.text_input("Erforderliche Zertifizierungen" if lang == "Deutsch" else "Certifications Required",
                                            value=st.session_state.get("certifications_required", ""),
                                            placeholder="z.B. PMP; Scrum Master" if lang == "Deutsch"
                                                        else "e.g. PMP; Certified Scrum Master",
                                            help="Zertifikate oder Abschlüsse, die benötigt oder bevorzugt werden." if lang == "Deutsch"
                                                 else "Professional certifications or licenses required/preferred.")
    # Additional optional fields in a collapsible section
    with st.expander("Weitere optionale Anforderungen" if lang == "Deutsch" else "Additional Optional Requirements"):
        industry_experience = st.text_input("Branchenerfahrung (Details)" if lang == "Deutsch" else "Industry Experience",
                                            value=st.session_state.get("industry_experience", ""),
                                            placeholder="z.B. 5+ Jahre im E-Commerce" if lang == "Deutsch"
                                                        else "e.g. 5+ years in e-commerce sector",
                                            help="Erfahrung in einer bestimmten Branche (Dauer oder Art)." if lang == "Deutsch"
                                                 else "Years or type of experience in the specific industry sector.")
        analytical_skills = st.text_input("Analytische Fähigkeiten" if lang == "Deutsch" else "Analytical Skills",
                                          value=st.session_state.get("analytical_skills", ""),
                                          placeholder="z.B. Dateninterpretation; Kritisches Denken" if lang == "Deutsch"
                                                      else "e.g. Data interpretation; Critical thinking",
                                          help="Analytische bzw. konzeptionelle Fähigkeiten." if lang == "Deutsch"
                                               else "Analytical or critical-thinking skills relevant to the role.")
        communication_skills = st.text_input("Kommunikationsfähigkeiten" if lang == "Deutsch" else "Communication Skills",
                                             value=st.session_state.get("communication_skills", ""),
                                             placeholder="z.B. Präsentationsstärke; Verhandlungsgeschick" if lang == "Deutsch"
                                                         else "e.g. Presentation skills; Negotiation",
                                             help="Spezifische kommunikative Fähigkeiten (Präsentation, Verhandlung, etc.)." if lang == "Deutsch"
                                                  else "Specific communication skills (e.g., presentation, negotiation).")
        project_management_skills = st.text_input("Projektmanagement-Fähigkeiten" if lang == "Deutsch" else "Project Management Skills",
                                                  value=st.session_state.get("project_management_skills", ""),
                                                  placeholder="z.B. Agile Methoden; Risikomanagement" if lang == "Deutsch"
                                                              else "e.g. Agile methodologies; Risk management",
                                                  help="Fähigkeiten im Bereich Projektplanung und -durchführung." if lang == "Deutsch"
                                                       else "Skills related to planning and executing projects.")
        soft_requirement_details = st.text_input("Weitere Anforderungen (Details)" if lang == "Deutsch" else "Other Requirements (Details)",
                                                 value=st.session_state.get("soft_requirement_details", ""),
                                                 placeholder="z.B. Führerschein Klasse B" if lang == "Deutsch"
                                                             else "e.g. Driver’s license required",
                                                 help="Sonstige spezifische Anforderungen, die nicht oben abgedeckt sind." if lang == "Deutsch"
                                                      else "Any other specific requirements not covered above (e.g., driver's license).")
        visa_sponsorship = st.text_input("Visum-Unterstützung" if lang == "Deutsch" else "Visa Sponsorship",
                                         value=st.session_state.get("visa_sponsorship", ""),
                                         placeholder="z.B. Ja, für qualifizierte Kandidaten" if lang == "Deutsch"
                                                     else "e.g. Yes, available for qualified candidates",
                                         help="Hinweis, ob eine Visa-/Arbeitserlaubnis-Unterstützung geboten wird." if lang == "Deutsch"
                                              else "Note whether visa/work permit sponsorship is available for candidates.")
    return {
        "must_have_skills": must_have_skills,
        "hard_skills": hard_skills,
        "nice_to_have_skills": nice_to_have_skills,
        "soft_skills": soft_skills,
        "language_requirements": language_requirements,
        "tool_proficiency": tool_proficiency,
        "technical_stack": technical_stack,
        "domain_expertise": domain_expertise,
        "leadership_competencies": leadership_competencies,
        "certifications_required": certifications_required,
        "industry_experience": industry_experience,
        "analytical_skills": analytical_skills,
        "communication_skills": communication_skills,
        "project_management_skills": project_management_skills,
        "soft_requirement_details": soft_requirement_details,
        "visa_sponsorship": visa_sponsorship
    }

def render_step6_static():
    lang = st.session_state.get("lang", "English")
    st.title("Schritt 6: Vergütung & Benefits" if lang == "Deutsch" else "Step 6: Compensation & Benefits")
    display_step_summary(6)
    salary_range = st.text_input("Gehaltsrahmen" if lang == "Deutsch" else "Salary Range",
                                 value=st.session_state.get("salary_range", ""),
                                 placeholder="z.B. 50.000–60.000 €" if lang == "Deutsch" else "e.g. €50,000–60,000",
                                 help="Geschätzte Gehaltsspanne (Jahresgehalt in Brutto, falls anzugeben)." if lang == "Deutsch"
                                      else "Approximate annual salary range (if willing to disclose).")
    currency = st.text_input("Währung" if lang == "Deutsch" else "Currency",
                              value=st.session_state.get("currency", "EUR") or "EUR",
                              help="Währung für die Gehaltsangabe (z.B. EUR, USD)." if lang == "Deutsch"
                                   else "Currency of the salary (e.g., EUR, USD).")
    pay_frequency = st.text_input("Zahlungsfrequenz" if lang == "Deutsch" else "Pay Frequency",
                                  value=st.session_state.get("pay_frequency", ""),
                                  placeholder="z.B. jährlich, monatlich" if lang == "Deutsch" else "e.g. per year, per month",
                                  help="Intervall der Gehaltszahlung (jährlich, monatlich etc.)." if lang == "Deutsch"
                                       else "Frequency of pay (per year, per month, etc.).")
    bonus_scheme = st.text_input("Bonusregelung" if lang == "Deutsch" else "Bonus Scheme",
                                 value=st.session_state.get("bonus_scheme", ""),
                                 placeholder="z.B. Bis zu 10% Jahresbonus" if lang == "Deutsch" else "e.g. Up to 10% annual bonus",
                                 help="Etwaige Boni oder Gewinnbeteiligungen (z.B. jährlicher Bonus)." if lang == "Deutsch"
                                      else "Details of any bonus structure (e.g., up to 10% annual bonus).")
    commission_structure = st.text_input("Provisionsstruktur" if lang == "Deutsch" else "Commission Structure",
                                         value=st.session_state.get("commission_structure", ""),
                                         placeholder="z.B. Provision auf Verkäufe über dem Soll" if lang == "Deutsch"
                                                     else "e.g. Commission on sales above target",
                                         help="Provisionsmodell, falls zutreffend (z.B. für Vertriebspositionen)." if lang == "Deutsch"
                                              else "Commission details if applicable (e.g., for sales roles).")
    vacation_days = st.text_input("Urlaubstage" if lang == "Deutsch" else "Vacation Days",
                                  value=st.session_state.get("vacation_days", ""),
                                  placeholder="z.B. 30" if lang == "Deutsch" else "e.g. 25",
                                  help="Anzahl der jährlichen Urlaubstage." if lang == "Deutsch"
                                       else "Number of paid vacation days per year.")
    remote_work_policy = st.text_input("Remote-Arbeit Regelung" if lang == "Deutsch" else "Remote Work Policy",
                                       value=st.session_state.get("remote_work_policy", ""),
                                       placeholder="z.B. Hybrid (2 Tage/Woche remote)" if lang == "Deutsch"
                                                   else "e.g. Hybrid (2 days remote per week)",
                                       help="Regelung zum Home-Office: vor Ort, hybrid, vollständig remote." if lang == "Deutsch"
                                            else "Remote working arrangement (on-site only, hybrid, or fully remote).")
    flexible_hours = st.text_input("Flexible Arbeitszeiten" if lang == "Deutsch" else "Flexible Hours",
                                   value=st.session_state.get("flexible_hours", ""),
                                   placeholder="z.B. Ja (Gleitzeit)" if lang == "Deutsch"
                                               else "e.g. Yes (flexible schedule)",
                                   help="Ob flexible Arbeitszeitgestaltung möglich ist." if lang == "Deutsch"
                                        else "Whether flexible working hours are offered.")
    relocation_assistance = st.text_input("Umzugsunterstützung" if lang == "Deutsch" else "Relocation Assistance",
                                          value=st.session_state.get("relocation_assistance", ""),
                                          placeholder="z.B. Ja, Umzugspaket verfügbar" if lang == "Deutsch"
                                                      else "e.g. Yes, relocation package available",
                                          help="Ob Unterstützung beim Umzug/Standortwechsel geboten wird." if lang == "Deutsch"
                                               else "Whether relocation support is provided for candidates.")
    childcare_support = st.text_input("Unterstützung Kinderbetreuung" if lang == "Deutsch" else "Childcare Support",
                                      value=st.session_state.get("childcare_support", ""),
                                      placeholder="z.B. Ja, Kinderbetreuungszuschuss" if lang == "Deutsch"
                                                  else "e.g. Yes, childcare stipend",
                                      help="Leistungen in Bezug auf Kinderbetreuung (z.B. Kita-Platz, Zuschuss)." if lang == "Deutsch"
                                           else "Any benefits for childcare (e.g., on-site daycare, childcare stipend).")
    travel_requirements_link = st.text_input("Link zu Reiserichtlinien" if lang == "Deutsch" else "Travel Requirements Link",
                                             value=st.session_state.get("travel_requirements_link", ""),
                                             placeholder="z.B. https://firma.de/reiserichtlinie" if lang == "Deutsch"
                                                         else "e.g. https://company.com/travel-policy",
                                             help="Link zu detaillierten Reiserichtlinien oder -anforderungen, falls vorhanden." if lang == "Deutsch"
                                                  else "Link to detailed travel policy/requirements if applicable.")
    return {
        "salary_range": salary_range,
        "currency": currency,
        "pay_frequency": pay_frequency,
        "bonus_scheme": bonus_scheme,
        "commission_structure": commission_structure,
        "vacation_days": vacation_days,
        "remote_work_policy": remote_work_policy,
        "flexible_hours": flexible_hours,
        "relocation_assistance": relocation_assistance,
        "childcare_support": childcare_support,
        "travel_requirements_link": travel_requirements_link
    }

def render_step7_static():
    lang = st.session_state.get("lang", "English")
    st.title("Schritt 7: Bewerbungsprozess" if lang == "Deutsch" else "Step 7: Recruitment Process")
    display_step_summary(7)
    recruitment_steps = st.text_area("Ablauf des Bewerbungsprozesses" if lang == "Deutsch" else "Recruitment Steps",
                                     value=st.session_state.get("recruitment_steps", ""),
                                     placeholder=("z.B.\n1. HR-Vorauswahl\n2. Fachliches Interview\n3. Finale Gesprächsrunde") if lang == "Deutsch"
                                                 else ("e.g.\n1. HR Screen\n2. Technical Interview\n3. Final Round"),
                                     help="Schritte des Auswahlprozesses (Interviews, Tests, etc.)." if lang == "Deutsch"
                                          else "Outline of the hiring process steps (interviews, tests, etc.).")
    number_of_interviews = st.text_input("Anzahl der Interviews" if lang == "Deutsch" else "Number of Interviews",
                                         value=st.session_state.get("number_of_interviews", ""),
                                         placeholder="z.B. 3" if lang == "Deutsch" else "e.g. 3",
                                         help="Wie viele Interview-Runden es insgesamt gibt." if lang == "Deutsch"
                                              else "Total number of interview rounds in the process.")
    assessment_tests = st.text_input("Einstellungstests" if lang == "Deutsch" else "Assessment Tests",
                                     value=st.session_state.get("assessment_tests", ""),
                                     placeholder="z.B. Programmier-Test, Persönlichkeits-Test, keiner" if lang == "Deutsch"
                                                 else "e.g. Coding test, Aptitude test, None",
                                     help="Etwaige Tests im Prozess (z.B. fachliche Tests, Persönlichkeitstests)." if lang == "Deutsch"
                                          else "Any tests involved (technical test, aptitude test, or 'none').")
    interview_format = st.text_input("Interview-Format" if lang == "Deutsch" else "Interview Format",
                                     value=st.session_state.get("interview_format", ""),
                                     placeholder="z.B. Alle vor Ort, finale Runde per Video" if lang == "Deutsch"
                                                 else "e.g. All on-site, final round via video call",
                                     help="Format der Interviews (persönlich, per Video, Panel, etc.)." if lang == "Deutsch"
                                          else "Format of interviews (in-person, video call, panel, etc.).")
    recruitment_timeline = st.text_input("Einstellungszeitplan" if lang == "Deutsch" else "Recruitment Timeline",
                                         value=st.session_state.get("recruitment_timeline", ""),
                                         placeholder="z.B. Zusage bis Ende Juni angestrebt" if lang == "Deutsch"
                                                     else "e.g. Offers expected by end of June",
                                         help="Voraussichtlicher Zeitrahmen für den gesamten Einstellungsprozess." if lang == "Deutsch"
                                              else "Expected overall timeline for the hiring process.")
    onboarding_process_overview = st.text_area("Überblick Onboarding-Prozess" if lang == "Deutsch" else "Onboarding Process Overview",
                                               value=st.session_state.get("onboarding_process_overview", ""),
                                               placeholder=("z.B. 1 Woche Orientierung + 3 Monate Mentoring-Programm") if lang == "Deutsch"
                                                           else ("e.g. 1-week orientation + 3-month mentorship program"),
                                               help="Kurzer Überblick, wie neue Mitarbeiter eingearbeitet werden (Onboarding)." if lang == "Deutsch"
                                                    else "Brief overview of the onboarding process for a new hire.")
    recruitment_contact_email = st.text_input("Kontakt E-Mail für Bewerber" if lang == "Deutsch" else "Recruitment Contact Email",
                                              value=st.session_state.get("recruitment_contact_email", ""),
                                              placeholder="z.B. jobs@firma.de" if lang == "Deutsch" else "e.g. jobs@company.com",
                                              help="E-Mail-Adresse für Bewerbungen oder Rückfragen der Kandidaten." if lang == "Deutsch"
                                                   else "Contact email for candidates to send applications or inquiries.")
    recruitment_contact_phone = st.text_input("Kontakt Telefon für Bewerber" if lang == "Deutsch" else "Recruitment Contact Phone",
                                              value=st.session_state.get("recruitment_contact_phone", ""),
                                              placeholder="z.B. +49 123 4567890" if lang == "Deutsch" else "e.g. +1 555 123 4567",
                                              help="Telefonnummer für Bewerberanfragen (optional)." if lang == "Deutsch"
                                                   else "Phone number for candidate inquiries (optional).")
    application_instructions = st.text_area("Bewerbungsanweisungen" if lang == "Deutsch" else "Application Instructions",
                                            value=st.session_state.get("application_instructions", ""),
                                            placeholder=("z.B. Über unser Karriereportal bewerben oder Lebenslauf per E-Mail senden.") if lang == "Deutsch"
                                                        else ("e.g. Apply via our careers page or email your resume to HR."),
                                            help="Spezielle Hinweise, wie sich Bewerber bewerben sollen." if lang == "Deutsch"
                                                 else "Specific instructions on how to apply (e.g., via a portal or email).")
    return {
        "recruitment_steps": recruitment_steps,
        "number_of_interviews": number_of_interviews,
        "assessment_tests": assessment_tests,
        "interview_format": interview_format,
        "recruitment_timeline": recruitment_timeline,
        "onboarding_process_overview": onboarding_process_overview,
        "recruitment_contact_email": recruitment_contact_email,
        "recruitment_contact_phone": recruitment_contact_phone,
        "application_instructions": application_instructions
    }

# Step 8: Final Review & Output Generation
def render_step8():
    lang = st.session_state.get("lang", "English")
    st.title("Schritt 8: Abschluss & Veröffentlichung" if lang == "Deutsch" else "Step 8: Final Review & Outputs")
    display_step_summary(8)
    st.subheader("Überprüfe alle Angaben" if lang == "Deutsch" else "Review All Details")
    st.write("Du kannst alle Felder bearbeiten, bevor die finale Anzeige erstellt wird:" if lang == "Deutsch"
             else "All fields are shown below for final review and editing before generating the outputs:")
    # Expander sections to edit fields from previous steps without navigating back
    with st.expander("Grundlegende Stellen- & Firmendaten" if lang == "Deutsch" else "Basic Job & Company Info", expanded=False):
        vals2 = render_step2_static()
        for k, v in vals2.items():
            st.session_state[k] = v
            _ensure_engine().notify_change(k, st.session_state)
    with st.expander("Rollenbeschreibung & Details" if lang == "Deutsch" else "Role Definition & Details", expanded=False):
        vals3 = render_step3_static()
        for k, v in vals3.items():
            st.session_state[k] = v
            _ensure_engine().notify_change(k, st.session_state)
    with st.expander("Aufgaben & Verantwortlichkeiten" if lang == "Deutsch" else "Tasks & Responsibilities", expanded=False):
        vals4 = render_step4_static()
        for k, v in vals4.items():
            st.session_state[k] = v
            _ensure_engine().notify_change(k, st.session_state)
    with st.expander("Fähigkeiten & Kompetenzen" if lang == "Deutsch" else "Skills & Competencies", expanded=False):
        vals5 = render_step5_static()
        for k, v in vals5.items():
            st.session_state[k] = v
            _ensure_engine().notify_change(k, st.session_state)
    with st.expander("Vergütung & Benefits" if lang == "Deutsch" else "Compensation & Benefits", expanded=False):
        vals6 = render_step6_static()
        for k, v in vals6.items():
            st.session_state[k] = v
            _ensure_engine().notify_change(k, st.session_state)
    with st.expander("Bewerbungsprozess" if lang == "Deutsch" else "Recruitment Process", expanded=False):
        vals7 = render_step7_static()
        for k, v in vals7.items():
            st.session_state[k] = v
            _ensure_engine().notify_change(k, st.session_state)
    st.subheader("Zusätzliche Einstellungen" if lang == "Deutsch" else "Additional Settings")
    ad_seniority_tone = st.text_input("Ton/Stil der Anzeige" if lang == "Deutsch" else "Ad Tone/Style",
                                      value=st.session_state.get("ad_seniority_tone", ""),
                                      placeholder="z.B. Professionell und förmlich" if lang == "Deutsch"
                                                  else "e.g. Professional and formal",
                                      help="Gewünschter Tonfall/Schreibstil der Anzeige (z.B. locker, formell)." if lang == "Deutsch"
                                           else "Desired tone or style for the job ad (e.g. formal, casual, friendly).")
    ad_length_preference = st.text_input("Präferenz Anzeigenlänge" if lang == "Deutsch" else "Ad Length Preference",
                                         value=st.session_state.get("ad_length_preference", ""),
                                         placeholder="z.B. Kurz und prägnant" if lang == "Deutsch"
                                                     else "e.g. Short and concise",
                                         help="Präferenz für die Länge der Stellenbeschreibung (knapp vs. ausführlich)." if lang == "Deutsch"
                                              else "Preference for the length/detail level of the job description (concise vs. detailed).")
    # Language of Ad: select English/German for output content
    language_options = ["Deutsch", "Englisch"] if lang == "Deutsch" else ["German", "English"]
    default_idx = 0 if st.session_state.get("language_of_ad", "English") in ["German", "Deutsch"] else 1
    selected_lang = st.selectbox("Sprache der Anzeige" if lang == "Deutsch" else "Language of Ad",
                                 options=language_options, index=(0 if default_idx == 0 else 1))
    # Normalize to English/German internally
    st.session_state["language_of_ad"] = "German" if selected_lang in ["German", "Deutsch"] else "English"
    translation_required = st.checkbox("Übersetzung der Anzeige benötigt?" if lang == "Deutsch" else "Translation required?",
                                       value=bool(st.session_state.get("translation_required", False)))
    st.session_state["translation_required"] = translation_required
    desired_publication_channels = st.text_input("Gewünschte Veröffentlichungskanäle" if lang == "Deutsch" else "Desired Publication Channels",
                                                 value=st.session_state.get("desired_publication_channels", ""),
                                                 placeholder="z.B. LinkedIn, Firmenwebsite" if lang == "Deutsch"
                                                             else "e.g. LinkedIn, Company careers page",
                                                 help="Kanäle/Plattformen, auf denen die Stelle veröffentlicht werden soll." if lang == "Deutsch"
                                                      else "Channels where the job ad will be posted (job boards, company site, etc.).")
    employer_branding_elements = st.text_input("Employer-Branding-Elemente" if lang == "Deutsch" else "Employer Branding Elements",
                                               value=st.session_state.get("employer_branding_elements", ""),
                                               placeholder="z.B. Unternehmensmission, Werte" if lang == "Deutsch"
                                                           else "e.g. Company mission statement, core values",
                                               help="Unternehmenselemente für die Anzeige (Mission, Werte, Motto, etc.)." if lang == "Deutsch"
                                                    else "Company branding elements to include (mission, values, tagline, etc.).")
    diversity_inclusion_statement = st.text_area("Diversity & Inclusion Statement",
                                                 value=st.session_state.get("diversity_inclusion_statement", ""),
                                                 placeholder="z.B. Wir begrüßen alle Bewerbungen unabhängig von..." if lang == "Deutsch"
                                                             else "e.g. We welcome applicants from all backgrounds...",
                                                 help="Statement zur Diversität/Chancengleichheit für die Anzeige." if lang == "Deutsch"
                                                      else "Optional diversity & inclusion statement to include in the job ad.")
    legal_disclaimers = st.text_area("Rechtliche Hinweise" if lang == "Deutsch" else "Legal Disclaimers",
                                     value=st.session_state.get("legal_disclaimers", ""),
                                     placeholder="z.B. Hinweis auf Gleichbehandlungsgesetz oder Datenschutz" if lang == "Deutsch"
                                                 else "e.g. Any legal disclaimer (equal opportunity employer, data privacy, etc.)",
                                     help="Rechtlich erforderliche Hinweise für die Ausschreibung." if lang == "Deutsch"
                                          else "Any legally required disclaimers to include (EEO statements, data privacy, etc.).")
    company_awards = st.text_input("Unternehmensauszeichnungen" if lang == "Deutsch" else "Company Awards",
                                   value=st.session_state.get("company_awards", ""),
                                   placeholder="z.B. Auszeichnung als Top-Arbeitgeber 2022" if lang == "Deutsch"
                                               else "e.g. Fortune 100 Best Companies to Work For 2022",
                                   help="Auszeichnungen oder Preise des Unternehmens, die erwähnt werden sollen." if lang == "Deutsch"
                                        else "Notable company awards or accolades to mention.")
    social_media_links = st.text_input("Social-Media-Links" if lang == "Deutsch" else "Social Media Links",
                                       value=st.session_state.get("social_media_links", ""),
                                       placeholder="z.B. LinkedIn: linkedin.com/company/..., Xing: ..." if lang == "Deutsch"
                                                   else "e.g. LinkedIn: linkedin.com/company/...; Twitter: @CompanyHandle",
                                       help="Links zu Social-Media-Profilen oder Karriereseiten, die in der Anzeige erscheinen sollen." if lang == "Deutsch"
                                            else "Social media or careers page links to include in the job ad (optional).")
    video_introduction_option = st.text_input("Option für Videovorstellung" if lang == "Deutsch" else "Video Introduction Option",
                                              value=st.session_state.get("video_introduction_option", ""),
                                              placeholder="z.B. Bewerber können ein 2-minütiges Vorstellungsvideo einsenden" if lang == "Deutsch"
                                                          else "e.g. Candidates may submit a 2-minute intro video",
                                              help="Hinweis, ob Bewerber ein Vorstellungsvideo einreichen können/dürfen." if lang == "Deutsch"
                                                   else "Note if candidates have the option to submit an intro video as part of application.")
    internal_job_id = st.text_input("Interne Job-ID" if lang == "Deutsch" else "Internal Job ID",
                                    value=st.session_state.get("internal_job_id", ""),
                                    placeholder="z.B. JOB-1234" if lang == "Deutsch" else "e.g. JOB-1234",
                                    help="Interne Referenz oder Kennziffer für diese Position." if lang == "Deutsch"
                                         else "Internal reference ID or job requisition number (for internal use only).")
    deadline_urgency = st.text_input("Dringlichkeit/Frist" if lang == "Deutsch" else "Deadline/Urgency",
                                     value=st.session_state.get("deadline_urgency", ""),
                                     placeholder="z.B. Stelle schnellstmöglich besetzen" if lang == "Deutsch"
                                                 else "e.g. Looking to hire ASAP",
                                     help="Dringlichkeit oder Frist für die Besetzung der Stelle." if lang == "Deutsch"
                                          else "Any urgency or target deadline for filling this position.")
    comments_internal = st.text_area("Interne Kommentare" if lang == "Deutsch" else "Internal Comments",
                                     value=st.session_state.get("comments_internal", ""),
                                     placeholder="z.B. Hinweis: Ersatz für Max Mustermann" if lang == "Deutsch"
                                                 else "e.g. Note: backfill for Jane Doe; focus on XYZ skill",
                                     help="Interne Anmerkungen oder Notizen (nicht in der Anzeige enthalten)." if lang == "Deutsch"
                                          else "Any internal notes about the position (not included in the job ad).")
    # Save additional inputs to session state
    st.session_state["ad_seniority_tone"] = ad_seniority_tone
    st.session_state["ad_length_preference"] = ad_length_preference
    st.session_state["desired_publication_channels"] = desired_publication_channels
    st.session_state["employer_branding_elements"] = employer_branding_elements
    st.session_state["diversity_inclusion_statement"] = diversity_inclusion_statement
    st.session_state["legal_disclaimers"] = legal_disclaimers
    st.session_state["company_awards"] = company_awards
    st.session_state["social_media_links"] = social_media_links
    st.session_state["video_introduction_option"] = video_introduction_option
    st.session_state["internal_job_id"] = internal_job_id
    st.session_state["deadline_urgency"] = deadline_urgency
    st.session_state["comments_internal"] = comments_internal

    st.subheader("🔄 " + ("Finale Inhalte generieren" if lang == "Deutsch" else "Generate Final Outputs"))
    if st.button("📄 Stellenbeschreibung & Ausgaben erstellen" if lang == "Deutsch" else "📄 Generate Job Description & Outputs"):
        # Compile the job spec from session state
        job_spec = {}
        for step in range(2, 8):
            for field in STEP_KEYS[step]:
                if field in ["input_url", "uploaded_file", "parsed_data_raw", "source_language"]:
                    continue
                val = st.session_state.get(field)
                if val not in (None, "", []):
                    job_spec[field] = val
        output_lang = st.session_state.get("language_of_ad", "English")
        # Initialize OpenAI client (which handles local/remote model selection)
        client = OpenAI()
        def generate_text(prompt: str, max_tokens: int = 300, temperature: float = 0.7) -> str:
            try:
                # Use GPT-4 (function-calling enabled model) for generation
                response = call_with_retry(
                    client.chat.completions.create,
                    model="gpt-4-0613",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature, max_tokens=max_tokens
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                return f"Error: {e}"
        # Determine language instruction for prompts
        in_language = "German" if output_lang in ["German", "Deutsch"] else "English"
        # Prompt: Full job description
        prompt_jd = f"Write a detailed job description in {in_language} for the following position:\n"
        for key, val in job_spec.items():
            # Format the spec lines for the prompt
            label = key.replace("_", " ").title()
            if isinstance(val, str) and "\n" in val:
                prompt_jd += f"{label}:\n{val}\n"
            else:
                prompt_jd += f"{label}: {val}\n"
        tone = st.session_state.get("ad_seniority_tone") or ("formal" if output_lang in ["German", "Deutsch"] else "professional")
        length_pref = st.session_state.get("ad_length_preference") or ("prägnant" if output_lang in ["German", "Deutsch"] else "concise")
        prompt_jd += f"Use a {tone.lower()} tone and make the description {length_pref.lower()}."
        job_ad_text = generate_text(prompt_jd, max_tokens=800, temperature=0.65)
        # Append diversity or legal statements verbatim if provided
        if st.session_state.get("diversity_inclusion_statement"):
            job_ad_text += "\n\n" + st.session_state["diversity_inclusion_statement"]
        if st.session_state.get("legal_disclaimers"):
            job_ad_text += "\n\n" + st.session_state["legal_disclaimers"]
        # Prompt: Boolean search query for sourcing
        prompt_bool = f"Create a Boolean search string in {in_language} to find candidates for the above position (include title and must-have skills)."
        boolean_query = generate_text(prompt_bool, max_tokens=100, temperature=0.0)
        # Prompt: Recruiter outreach email
        prompt_email = (f"Write a short, engaging recruiting email in {in_language} to a potential candidate about the above job. "
                        "Introduce the role and company briefly, highlight a couple of key points (like a top responsibility or benefit), and invite them to discuss further.")
        email_text = generate_text(prompt_email, max_tokens=200, temperature=0.6)
        # Prompt: LinkedIn post
        prompt_li = (f"Write a brief LinkedIn post in {in_language} announcing the job opening for this position. "
                     "Encourage people to apply or share, and include a couple of relevant hashtags (e.g., #hiring, #job).")
        linkedin_post = generate_text(prompt_li, max_tokens=150, temperature=0.7)
        # Display the generated outputs
        st.success("✅ " + ("Inhalte generiert! Scrollen Sie nach unten, um sie zu sehen." if lang == "Deutsch"
                            else "Outputs generated! Scroll down to view each of them."))
        st.subheader("📄 " + ("Stellenbeschreibung (Entwurf)" if lang == "Deutsch" else "Job Description Draft"))
        st.text_area("", value=job_ad_text, height=300)
        st.subheader("🔎 " + ("Boolean-Suchstring" if lang == "Deutsch" else "Boolean Search String"))
        st.code(boolean_query, language="")
        st.subheader("✉️ " + ("E-Mail Vorlage (Recruiter an Kandidaten)" if lang == "Deutsch" else "Recruiter Email Template"))
        st.text_area("", value=email_text, height=150)
        st.subheader("🔗 " + ("LinkedIn-Post (Kurztext)" if lang == "Deutsch" else "LinkedIn Post Copy"))
        st.text_area("", value=linkedin_post, height=100)

# Handle static step form submission (Steps 2–7)
def _handle_static_step(idx: int, renderer_func):
    with st.form(f"step{idx}_form"):
        values = renderer_func()
        submit_label = "Weiter" if st.session_state.get("lang") == "Deutsch" else "Next"
        submitted = st.form_submit_button(submit_label)
    if submitted:
        # Save form values and trigger engine for dependencies
        for k, v in values.items():
            st.session_state[k] = v
        for k in STEP_KEYS[idx]:
            _ensure_engine().notify_change(k, st.session_state)
        missing = [
            k for k in STEP_KEYS[idx]
            if k not in ["input_url", "uploaded_file", "parsed_data_raw", "source_language"]
            and not st.session_state.get(k)
        ]
        st.session_state[f"step{idx}_static_submitted"] = bool(missing)
        # Log step completion vs missing
        if missing:
            st.session_state.setdefault("trace_events", []).append(f"Step {idx} submitted with missing: {missing}")
        else:
            st.session_state["wizard_step"] += 1
            st.session_state.setdefault("trace_events", []).append(f"Step {idx} complete.")
        st.rerun()
    # If some fields were missing, present dynamic inputs for them
    if st.session_state.get(f"step{idx}_static_submitted"):
        remaining = [
            k for k in STEP_KEYS[idx]
            if k not in ["input_url", "uploaded_file", "parsed_data_raw", "source_language"]
            and not st.session_state.get(k)
        ]
        if remaining:
            st.info("Bitte ergänzen Sie noch folgende Punkte:" if st.session_state.get("lang") == "Deutsch"
                    else "Please fill in the following missing fields:")
        for key in remaining[:10]:
            label = key.replace("_", " ").title()
            if any(term in key for term in ("description", "tasks", "details", "comments", "steps")):
                st.text_area(label, key=key)
            else:
                st.text_input(label, key=key)
        if st.button("Weiter" if st.session_state.get("lang") == "Deutsch" else "Continue", key=f"cont{idx}"):
            # Trigger engine for any newly filled follow-ups
            for k in STEP_KEYS[idx]:
                _ensure_engine().notify_change(k, st.session_state)
            st.session_state[f"step{idx}_static_submitted"] = False
            st.session_state["wizard_step"] += 1
            st.rerun()

def _nav(step: int):
    """Bottom navigation buttons (Back/Next) for steps."""
    col_prev, col_next = st.columns(2)
    with col_prev:
        if step > 1 and st.button("⬅️ Zurück" if st.session_state.get("lang") == "Deutsch" else "⬅️ Back"):
            st.session_state["wizard_step"] -= 1
            st.rerun()
    with col_next:
        # Show "Next" only if static form is not awaiting completion
        if step < 8 and not st.session_state.get(f"step{step}_static_submitted", False):
            if st.button("Weiter ➡" if st.session_state.get("lang") == "Deutsch" else "Next ➡"):
                st.session_state["wizard_step"] += 1
                st.rerun()

def run_wizard():
    """Main entry point to render the wizard based on current step."""
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

# Run the wizard UI
run_wizard()
