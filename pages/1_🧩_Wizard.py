import streamlit as st
from services.openai_functions import generate_tasks, generate_skills, generate_benefits
from utils import session_keys

"""
Dieses Modul kombiniert den Discovery-Schritt (Dateiupload, URL, Texteingabe) 
mit einem mehrstufigen Wizard. Jeder Schritt des Wizards wird über den Session-State gesteuert.
"""

# Definiere die Schritte des Wizards mit Titeln und Beschreibungen (für Nutzerführung)
WIZARD_STEPS = [
    {"title": "Angaben", "description": "Wählen Sie eine Methode, um die Ausgangsinformationen bereitzustellen. Laden Sie ein Dokument hoch, geben Sie eine URL ein oder fügen Sie Text manuell ein."},
    {"title": "Aufgaben", "description": "Basierend auf Ihren Eingaben werden im Folgenden die Aufgaben vorgeschlagen."},
    {"title": "Anforderungen & Fähigkeiten", "description": "Basierend auf den Aufgaben werden nun die erforderlichen Anforderungen und Fähigkeiten generiert."},
    {"title": "Benefits", "description": "Abschließend werden noch passende Benefits für diese Position vorgeschlagen."},
    {"title": "Zusammenfassung", "description": "Überblick über alle generierten Inhalte der Stellenausschreibung."}
]

# Überprüfe und initialisiere die erforderlichen Session-State Keys 
session_keys.ensure_session_state()  # stellt sicher, dass 'content', 'tasks', 'skills', 'benefits', 'current_step' existieren

# Titel und Fortschrittsanzeige
current_step = st.session_state.get('current_step', 0)
total_steps = len(WIZARD_STEPS)
st.title('🧩 KI-Assistent für Stellenausschreibungen')
st.markdown(f"**Schritt {current_step+1} von {total_steps}: {WIZARD_STEPS[current_step]['title']}**")
st.write(WIZARD_STEPS[current_step]['description'])
st.progress(current_step / (total_steps - 1))

# Schritt 1: Angaben (Discovery-Schritt)
if st.session_state['current_step'] == 0:
    # Auswahl der Eingabemethode
    input_method = st.radio("Eingabemethode auswählen:", ("Datei hochladen", "URL eingeben", "Text eingeben"))
    if input_method == "Datei hochladen":
        uploaded_file = st.file_uploader("Bitte wählen Sie eine Datei aus:", type=["txt", "pdf", "docx"])
        if uploaded_file is not None:
            file_name = uploaded_file.name.lower()
            if file_name.endswith('.txt'):
                # Textdatei direkt einlesen
                st.session_state['content'] = str(uploaded_file.read(), 'utf-8')
            elif file_name.endswith('.pdf'):
                try:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(uploaded_file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                    st.session_state['content'] = text
                except Exception as e:
                    st.error("Fehler beim Lesen der PDF-Datei.")
                    st.session_state['content'] = ""
            elif file_name.endswith('.docx'):
                try:
                    import docx
                    doc = docx.Document(uploaded_file)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    st.session_state['content'] = text
                except Exception as e:
                    st.error("Fehler beim Lesen der DOCX-Datei.")
                    st.session_state['content'] = ""
            else:
                st.warning("Dateiformat nicht unterstützt. Bitte eine .txt, .pdf oder .docx Datei hochladen.")
                st.session_state['content'] = ""
    elif input_method == "URL eingeben":
        url = st.text_input("Bitte geben Sie die URL ein:")
        if url:
            import requests
            try:
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    # Text aus HTML extrahieren
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(res.text, "html.parser")
                    text = soup.get_text(separator="\n")
                    st.session_state['content'] = text
                else:
                    st.error(f"Die URL konnte nicht abgerufen werden (Status {res.status_code}).")
                    st.session_state['content'] = ""
            except Exception as e:
                st.error("Fehler beim Abrufen der URL.")
                st.session_state['content'] = ""
    else:  # "Text eingeben"
        manual_text = st.text_area("Bitte geben Sie den Text ein:")
        if manual_text:
            st.session_state['content'] = manual_text

    # Weiter-Button (aktiviert, wenn Inhalt vorhanden ist)
    if st.session_state['content'] and st.button("Weiter zu Aufgaben →"):
        # Vor dem Schrittwechsel bisherige KI-Ergebnisse zurücksetzen
        st.session_state['tasks'] = None
        st.session_state['skills'] = None
        st.session_state['benefits'] = None
        st.session_state['current_step'] = 1

# Schritt 2: Aufgaben (KI-generierte Aufgaben anzeigen)
elif st.session_state['current_step'] == 1:
    # Aufgaben generieren (falls noch nicht erfolgt)
    if st.session_state['tasks'] is None:
        with st.spinner("KI generiert Aufgaben..."):
            st.session_state['tasks'] = generate_tasks(st.session_state['content'])
    # Ergebnisse anzeigen
    tasks_result = st.session_state['tasks']
    st.subheader("Vorgeschlagene Aufgaben")
    if isinstance(tasks_result, list):
        for task in tasks_result:
            st.markdown(f"- {task}")
    elif tasks_result:
        st.markdown(tasks_result)
    else:
        st.info("Keine Aufgaben gefunden.")

    # Navigation: Zurück / Weiter
    col1, col2 = st.columns([1, 1])
    if col1.button("← Zurück zu Angaben"):
        st.session_state['current_step'] = 0
    if col2.button("Weiter zu Anforderungen →"):
        # Nachfolgende Ergebnisse zurücksetzen, falls neu generiert werden soll
        st.session_state['skills'] = None
        st.session_state['benefits'] = None
        st.session_state['current_step'] = 2

# Schritt 3: Anforderungen & Fähigkeiten 
elif st.session_state['current_step'] == 2:
    if st.session_state['skills'] is None:
        with st.spinner("KI generiert Anforderungen und Fähigkeiten..."):
            # Optional könnten hier die tasks als Kontext übergeben werden
            st.session_state['skills'] = generate_skills(st.session_state['content'])
    skills_result = st.session_state['skills']
    st.subheader("Vorgeschlagene Anforderungen & Fähigkeiten")
    if isinstance(skills_result, list):
        for skill in skills_result:
            st.markdown(f"- {skill}")
    elif skills_result:
        st.markdown(skills_result)
    else:
        st.info("Keine Anforderungen gefunden.")

    col1, col2 = st.columns([1, 1])
    if col1.button("← Zurück zu Aufgaben"):
        st.session_state['current_step'] = 1
    if col2.button("Weiter zu Benefits →"):
        st.session_state['benefits'] = None
        st.session_state['current_step'] = 3

# Schritt 4: Benefits 
elif st.session_state['current_step'] == 3:
    if st.session_state['benefits'] is None:
        with st.spinner("KI generiert Benefits..."):
            st.session_state['benefits'] = generate_benefits(st.session_state['content'])
    benefits_result = st.session_state['benefits']
    st.subheader("Vorgeschlagene Benefits")
    if isinstance(benefits_result, list):
        for benefit in benefits_result:
            st.markdown(f"- {benefit}")
    elif benefits_result:
        st.markdown(benefits_result)
    else:
        st.info("Keine Benefits gefunden.")

    col1, col2 = st.columns([1, 1])
    if col1.button("← Zurück zu Anforderungen"):
        st.session_state['current_step'] = 2
    if col2.button("Weiter zur Zusammenfassung →"):
        st.session_state['current_step'] = 4

# Schritt 5: Zusammenfassung 
elif st.session_state['current_step'] == 4:
    st.subheader("Zusammenfassung aller Ergebnisse")
    # Aufgaben Übersicht
    st.markdown("**Aufgaben:**")
    tasks_result = st.session_state.get('tasks', [])
    if isinstance(tasks_result, list):
        for task in tasks_result:
            st.markdown(f"- {task}")
    elif tasks_result:
        st.markdown(tasks_result)
    else:
        st.text("Keine Aufgaben angegeben.")
    # Anforderungen & Fähigkeiten Übersicht
    st.markdown("**Anforderungen & Fähigkeiten:**")
    skills_result = st.session_state.get('skills', [])
    if isinstance(skills_result, list):
        for skill in skills_result:
            st.markdown(f"- {skill}")
    elif skills_result:
        st.markdown(skills_result)
    else:
        st.text("Keine Anforderungen angegeben.")
    # Benefits Übersicht
    st.markdown("**Benefits:**")
    benefits_result = st.session_state.get('benefits', [])
    if isinstance(benefits_result, list):
        for benefit in benefits_result:
            st.markdown(f"- {benefit}")
    elif benefits_result:
        st.markdown(benefits_result)
    else:
        st.text("Keine Benefits angegeben.")

    st.success("Die Stellenausschreibung wurde vollständig generiert.")

    # Option: Assistent neu starten für eine weitere Nutzung
    if st.button("🔄 Assistent neu starten"):
        # Alle genutzten Session-State Werte zurücksetzen
        for key in ['content', 'tasks', 'skills', 'benefits']:
            st.session_state[key] = "" if key == 'content' else None
        st.session_state['current_step'] = 0
