import streamlit as st
from utils.session_keys import KEYS, ALL_KEYS, init_session_state
from utils.extraction import extract_text_from_file, match_and_store_keys
# Optional: Import fetch_url_text if available; otherwise define a fallback
try:
    from utils.extraction import fetch_url_text
except ImportError:
    import requests
    from bs4 import BeautifulSoup
    def fetch_url_text(url: str) -> str:
        """Lädt den Inhalt der URL und gibt den extrahierten Text zurück."""
        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                st.error("Fehler beim Laden der URL. Status-Code: {}".format(res.status_code))
                return ""
        except Exception as e:
            st.error("Fehler beim Laden der URL: {}".format(e))
            return ""
        # HTML zu Text konvertieren
        soup = BeautifulSoup(res.text, "html.parser")
        # Gesamten sichtbaren Text extrahieren
        text = soup.get_text(separator="\n")
        # Optional: Sehr langen Text abschneiden
        MAX_CHARS = 15000
        if len(text) > MAX_CHARS:
            st.warning("Text länger als {} Zeichen – wurde gekürzt.".format(MAX_CHARS))
            text = text[:MAX_CHARS]
        return text

# Initialisiere Session-State (alle benötigten Keys)
init_session_state()
# Stelle sicher, dass der Wizard-Step initialisiert ist
if "wizard_step" not in st.session_state:
    st.session_state["wizard_step"] = 1

step = st.session_state["wizard_step"]

# Hilfs-Dictionary: Zuordnung von Schlüssel zu Feldbeschriftung (Deutsch)
KEY_LABELS = {
    # Step1
    "job_title": "Jobtitel",
    "input_url": "Stellenanzeige-URL",
    "uploaded_text": "Geladener Anzeigentext",
    "parsed_data_raw": "Analyse-Rohdaten",
    "source_language": "Sprache",
    # Step2
    "company_name": "Unternehmensname",
    "brand_name": "Markenname",
    "headquarters_location": "Hauptsitz (Ort)",
    "city": "Stadt (Standort)",
    "company_website": "Unternehmens-Website",
    "company_size": "Unternehmensgröße",
    "industry_sector": "Branche",
    "job_type": "Beschäftigungsart",
    "contract_type": "Vertragsart",
    "job_level": "Karrierestufe",
    "team_structure": "Teamstruktur",
    "date_of_employment_start": "Startdatum",
    # Step3
    "role_description": "Rollenbeschreibung",
    "reports_to": "Berichtet an",
    "supervises": "Leitet / Beaufsichtigt",
    "role_type": "Rollenart",
    "role_performance_metrics": "Leistungskennzahlen",
    "role_priority_projects": "Prioritäre Projekte",
    "travel_requirements": "Reisebereitschaft",
    "work_schedule": "Arbeitszeitmodell",
    "decision_making_authority": "Entscheidungsbefugnis",
    "role_keywords": "Schlüsselwörter (Rolle)",
    # Step4
    "task_list": "Aufgabenliste",
    "key_responsibilities": "Hauptverantwortlichkeiten",
    "technical_tasks": "Technische Aufgaben",
    "managerial_tasks": "Führungsaufgaben",
    "administrative_tasks": "Administrative Aufgaben",
    "customer_facing_tasks": "Kundenkontakt-Aufgaben",
    "internal_reporting_tasks": "Interne Reporting-Aufgaben",
    "performance_tasks": "Leistungsbezogene Aufgaben",
    "innovation_tasks": "Innovationsaufgaben",
    "task_prioritization": "Aufgabenpriorisierung",
    # Step5
    "must_have_skills": "Must-have-Fähigkeiten",
    "hard_skills": "Hard Skills",
    "nice_to_have_skills": "Nice-to-have-Fähigkeiten",
    "soft_skills": "Soft Skills",
    "language_requirements": "Sprachanforderungen",
    "tool_proficiency": "Tool-Kenntnisse",
    "technical_stack": "Technologie-Stack",
    "domain_expertise": "Domain-Expertise",
    "leadership_competencies": "Führungskompetenzen",
    "certifications_required": "Erforderliche Zertifizierungen",
    "industry_experience": "Branchenerfahrung",
    "analytical_skills": "Analytische Fähigkeiten",
    "communication_skills": "Kommunikationsfähigkeiten",
    "project_management_skills": "Projektmanagement-Fähigkeiten",
    "soft_requirement_details": "Weitere Anforderungsdetails",
    "visa_sponsorship": "Visa-Unterstützung",
    # Step6
    "salary_range": "Gehaltsspanne",
    "currency": "Währung",
    "pay_frequency": "Zahlungsfrequenz",
    "bonus_scheme": "Bonusregelung",
    "commission_structure": "Provisionsmodell",
    "vacation_days": "Urlaubstage",
    "remote_work_policy": "Remote-Work-Regelung",
    "flexible_hours": "Flexible Arbeitszeiten",
    "relocation_assistance": "Umzugsunterstützung",
    "childcare_support": "Kinderbetreuung",
    "travel_requirements_link": "Reiseanforderungen (Link)",
    # Step7
    "recruitment_steps": "Bewerbungsphasen",
    "number_of_interviews": "Anzahl der Interviews",
    "assessment_tests": "Assessment-Tests",
    "interview_format": "Interview-Format",
    "recruitment_timeline": "Rekrutierungszeitplan",
    "onboarding_process_overview": "Onboarding-Prozess (Übersicht)",
    "recruitment_contact_email": "Kontakt E-Mail",
    "recruitment_contact_phone": "Kontakt Telefon",
    "application_instructions": "Bewerbungsanweisungen",
    # Step8 (falls benötigt, meistens intern)
    "ad_seniority_tone": "Ton bzgl. Seniorität",
    "ad_length_preference": "Präferenz Anzeigenlänge",
    "language_of_ad": "Sprache der Anzeige",
    "translation_required": "Übersetzung benötigt",
    "desired_publication_channels": "Gewünschte Veröffentlichungskanäle",
    "employer_branding_elements": "Employer-Branding-Elemente",
    "diversity_inclusion_statement": "Diversity & Inclusion Statement",
    "legal_disclaimers": "Rechtliche Hinweise",
    "company_awards": "Auszeichnungen des Unternehmens",
    "social_media_links": "Social-Media-Links",
    "video_introduction_option": "Option Video-Einführung",
    "internal_job_id": "Interne Job-ID",
    "deadline_urgency": "Dringlichkeit/Frist",
    "comments_internal": "Interne Kommentare"
}

# Schrittabhängige Darstellung
if step == 1:
    st.title("Schritt 1 – Discovery")
    st.markdown("Bitte wählen Sie eine Methode zur Dateneingabe für die Stellenausschreibung:")
    # Eingabe: Jobtitel immer abfragen
    st.text_input("Jobtitel", key="job_title")
    # Auswahl der Datenquelle
    method = st.radio("Datenquelle", ("URL eingeben", "PDF/TXT hochladen", "Text manuell eingeben"), index=0)
    url_input = None
    uploaded_file = None
    manual_text = None
    if method == "URL eingeben":
        url_input = st.text_input("Stellenanzeige-URL", key="input_url")
    elif method == "PDF/TXT hochladen":
        uploaded_file = st.file_uploader("Stellenanzeige als PDF oder Textdatei hochladen", type=["pdf", "txt"], key="uploaded_file")
    else:
        manual_text = st.text_area("Stellentext manuell eingeben", key="manual_text")
    if st.button("Analyse starten"):
        raw_text = ""
        # Wähle Quelle basierend auf der Auswahl und Eingaben
        if method == "PDF/TXT hochladen" and uploaded_file is not None:
            raw_text = extract_text_from_file(uploaded_file.read(), uploaded_file.name)
        elif method == "URL eingeben" and url_input:
            raw_text = fetch_url_text(url_input)
        elif method == "Text manuell eingeben" and manual_text:
            raw_text = manual_text
        # Falls keine Quelldaten angegeben wurden
        if raw_text == "":
            st.info("Kein Beschreibungstext angegeben – die Analyse basiert nur auf dem Jobtitel.")
        # Wenn überhaupt keine Informationen vorhanden, Abbruch
        if raw_text == "" and not st.session_state["job_title"]:
            st.error("Bitte geben Sie mindestens einen Jobtitel oder eine Stellenbeschreibung ein.")
        else:
            # Texte analysieren und relevante Felder füllen
            match_and_store_keys(raw_text, st.session_state)
            # (Optionales Event-Logging kann hier eingefügt werden)
            # Zum nächsten Schritt wechseln
            st.session_state["wizard_step"] = 2
            st.rerun()

elif step == 2:
    st.title("Schritt 2 – Basisinformationen")
    # Felder Schritt 2 anzeigen
    for key in KEYS["step2"]:
        label = KEY_LABELS.get(key, key)
        st.text_input(label, key=key)
    # Navigations-Buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("◀️ Zurück"):
            st.session_state["wizard_step"] = 1
            st.rerun()
    with col2:
        if st.button("Weiter ▶️"):
            st.session_state["wizard_step"] = 3
            st.rerun()

elif step == 3:
    st.title("Schritt 3 – Rollenbeschreibung")
    for key in KEYS["step3"]:
        label = KEY_LABELS.get(key, key)
        # Längere Texte in Textarea, ansonsten Textinput
        if key in ["role_description", "role_performance_metrics", "role_priority_projects", "work_schedule", "decision_making_authority", "role_keywords"]:
            st.text_area(label, key=key)
        else:
            st.text_input(label, key=key)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("◀️ Zurück"):
            st.session_state["wizard_step"] = 2
            st.rerun()
    with col2:
        if st.button("Weiter ▶️"):
            st.session_state["wizard_step"] = 4
            st.rerun()

elif step == 4:
    st.title("Schritt 4 – Aufgaben")
    for key in KEYS["step4"]:
        label = KEY_LABELS.get(key, key)
        # Aufgabenfelder als mehrzeiliger Text
        st.text_area(label, key=key)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("◀️ Zurück"):
            st.session_state["wizard_step"] = 3
            st.rerun()
    with col2:
        if st.button("Weiter ▶️"):
            st.session_state["wizard_step"] = 5
            st.rerun()

elif step == 5:
    st.title("Schritt 5 – Anforderungen")
    for key in KEYS["step5"]:
        label = KEY_LABELS.get(key, key)
        if key in ["must_have_skills", "hard_skills", "nice_to_have_skills", "soft_skills",
                   "language_requirements", "tool_proficiency", "technical_stack", "domain_expertise",
                   "leadership_competencies", "certifications_required", "industry_experience",
                   "soft_requirement_details", "visa_sponsorship"]:
            # Visa-Sponsoring und Soft-Requirement-Details evtl. kurze Texte, trotzdem Textinput lassen?
            if key in ["visa_sponsorship"]:
                st.text_input(label, key=key)
            else:
                st.text_area(label, key=key)
        elif key in ["analytical_skills", "communication_skills", "project_management_skills"]:
            st.text_input(label, key=key)
        else:
            st.text_input(label, key=key)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("◀️ Zurück"):
            st.session_state["wizard_step"] = 4
            st.rerun()
    with col2:
        if st.button("Weiter ▶️"):
            st.session_state["wizard_step"] = 6
            st.rerun()

elif step == 6:
    st.title("Schritt 6 – Rahmenbedingungen")
    for key in KEYS["step6"]:
        label = KEY_LABELS.get(key, key)
        st.text_input(label, key=key)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("◀️ Zurück"):
            st.session_state["wizard_step"] = 5
            st.rerun()
    with col2:
        if st.button("Weiter ▶️"):
            st.session_state["wizard_step"] = 7
            st.rerun()

elif step == 7:
    st.title("Schritt 7 – Bewerbungsprozess")
    for key in KEYS["step7"]:
        label = KEY_LABELS.get(key, key)
        if key in ["recruitment_steps", "assessment_tests", "onboarding_process_overview", "application_instructions"]:
            st.text_area(label, key=key)
        else:
            st.text_input(label, key=key)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("◀️ Zurück"):
            st.session_state["wizard_step"] = 6
            st.rerun()
    with col2:
        if st.button("Weiter ▶️"):
            st.session_state["wizard_step"] = 8
            st.rerun()

elif step == 8:
    st.title("Schritt 8 – Zusammenfassung")
    # Zusammenfassung aller gesammelten Daten anzeigen
    # Jobtitel separat aus Schritt 1
    if st.session_state.get("job_title"):
        st.markdown(f"**Jobtitel:** {st.session_state['job_title']}")
    # Gehe durch Schritte 2 bis 7 und zeige ausgefüllte Felder
    step_sections = {
        2: "Basisinformationen",
        3: "Rollenbeschreibung",
        4: "Aufgaben",
        5: "Anforderungen",
        6: "Rahmenbedingungen",
        7: "Bewerbungsprozess"
    }
    for st_num, section_name in step_sections.items():
        # Sammle alle Werte aus diesem Schritt, die nicht leer sind
        values = []
        for key in KEYS[f"step{st_num}"]:
            val = st.session_state.get(key)
            # Wert berücksichtigen, wenn nicht None/leer
            if val not in [None, ""]:
                label = KEY_LABELS.get(key, key)
                values.append(f"**{label}:** {val}")
        if values:
            st.subheader(section_name)
            for item in values:
                st.markdown(item)
    # Navigations-Buttons: Zurück oder Neustart
    col1, col2 = st.columns(2)
    with col1:
        if st.button("◀️ Zurück"):
            st.session_state["wizard_step"] = 7
            st.rerun()
    with col2:
        if st.button("🔄 Neue Analyse beginnen"):
            # Alle Felder zurücksetzen und zum Start
            for key in ALL_KEYS:
                st.session_state[key] = None
            # Auch den Upload löschen, falls vorhanden
            if "uploaded_file" in st.session_state:
                st.session_state["uploaded_file"] = None
            if "manual_text" in st.session_state:
                st.session_state["manual_text"] = ""
            st.session_state["wizard_step"] = 1
            st.rerun()
