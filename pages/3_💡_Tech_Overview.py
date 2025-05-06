# pages/tech_overview.py
"""Streamlit-Seite: Technologischer Überblick

Stellt die genutzte Architektur, Libraries und Tools dar – mit Sprachumschalter und Zielgruppenumschalter
(Tech-affin vs. nicht tech-affin)."""

import streamlit as st

# ---------------------------------------------------------------------------
# Sprach- und Zielgruppenumschalter
# ---------------------------------------------------------------------------
lang = st.radio("🌐 Sprache / Language", ("Deutsch", "English"), horizontal=True)
audience = st.radio(
    "🎯 Zielgruppe / Audience",
    ("Tech-interessiert", "Allgemein verständlich") if lang == "Deutsch" else ("Tech-savvy", "General public"),
    horizontal=True
)

# ---------------------------------------------------------------------------
# Inhalte (DE & EN, je nach Zielgruppe)
# ---------------------------------------------------------------------------
technology_info = {
    "Deutsch": {
        "Tech-interessiert": [
            ("Streamlit", "Framework für Python-basierte Web-Apps mit minimalem Overhead. Optimal für schnelle Prototypen und datengetriebene Interfaces."),
            ("Python 3.11", "Verlässliche Programmiersprache mit modernen Features (z.B. Pattern Matching, AsyncIO Verbesserungen)."),
            ("OpenAI API (GPT-4)", "Berechnung von Textanalysen, Embedding-Matching und dynamischen Antworten auf Nutzeranfragen."),
            ("FAISS + Langchain", "Vektorindizierte semantische Suche über ESCO Skills, Aufgaben und Branchendaten."),
            ("pypdf, docx2txt", "Extraktion und Parsing von Dokumenteninhalt für strukturierten Session-State-Aufbau."),
            ("st.session_state", "Effiziente Persistenz von Nutzerinteraktionen, extrahierten Daten und Flow-Steuerung."),
            ("ESCO API", "Ontologie-basierte Zuordnung von Fähigkeiten, Berufen und Spezialisierungen gemäß EU-Standards."),
            ("Tailwind CSS (geplant)", "Utility-First CSS Framework für konsistente und wartbare Designs in zukünftigen Erweiterungen."),
            ("Markdown/PDF Export", "Transformation von Session-Daten in formatierte, druckfähige Outputs (Anforderungsprofile, Sourcing-Reports)."),
            ("i18n über Dictionaries", "Interne, skalierbare Lösung für Internationalisierung ohne externe Abhängigkeiten."),
        ],
        "Allgemein verständlich": [
            ("Streamlit", "Werkzeug, um sehr einfach moderne Webseiten für Analysen zu erstellen."),
            ("Python 3.11", "Eine vielseitige Computersprache, beliebt für KI- und Datenprojekte."),
            ("OpenAI API (GPT-4)", "Künstliche Intelligenz hilft, Texte zu verstehen, Empfehlungen zu geben und Fragen dynamisch zu beantworten."),
            ("FAISS + Langchain", "Intelligente Suche, um passende Fähigkeiten und Aufgaben schneller zu finden."),
            ("pypdf, docx2txt", "Dateien (wie PDFs) werden automatisch ausgelesen, um Informationen weiterzuverwenden."),
            ("st.session_state", "Sorgt dafür, dass bereits eingegebene Daten während des gesamten Prozesses erhalten bleiben."),
            ("ESCO API", "Datenbank für europaweit anerkannte Berufe und Kompetenzen."),
            ("Tailwind CSS (geplant)", "Sorgt künftig für noch schönere und einheitlichere Designs."),
            ("Markdown/PDF Export", "Erlaubt es, Ergebnisse einfach als übersichtliche Dateien herunterzuladen."),
            ("i18n über Dictionaries", "Umschalten zwischen Deutsch und Englisch – ohne Ladezeiten."),
        ],
    },
    "English": {
        "Tech-savvy": [
            ("Streamlit", "Python-native web app framework with minimal overhead. Excellent for rapid prototypes and data-driven interfaces."),
            ("Python 3.11", "Reliable modern programming language featuring pattern matching, improved async IO, etc."),
            ("OpenAI API (GPT-4)", "Handles semantic text analysis, embedding matching, and dynamic conversation responses."),
            ("FAISS + Langchain", "Vector-based semantic search over skills, tasks, and industry data."),
            ("pypdf, docx2txt", "Document extraction and parsing modules for structured session state construction."),
            ("st.session_state", "Efficient storage for user interactions, parsed data, and dynamic flow control."),
            ("ESCO API", "Ontology-driven job and skill mapping compliant with European standards."),
            ("Tailwind CSS (planned)", "Utility-first CSS framework for maintainable, consistent UI design extensions."),
            ("Markdown/PDF Export", "Formatted output of job profiles and sourcing reports ready for download."),
            ("i18n via Dictionaries", "In-house extendable solution for fast internationalization switching."),
        ],
        "General public": [
            ("Streamlit", "Tool to quickly build modern websites for presenting and analyzing information."),
            ("Python 3.11", "A popular language often used for AI and data projects."),
            ("OpenAI API (GPT-4)", "Artificial intelligence helping to understand texts, suggest ideas, and answer questions dynamically."),
            ("FAISS + Langchain", "Smart search engine helping to quickly find relevant skills and tasks."),
            ("pypdf, docx2txt", "Uploads like PDFs are automatically read and prepared for further use."),
            ("st.session_state", "Keeps already entered information available throughout the process."),
            ("ESCO API", "Database of recognized occupations and competencies across Europe."),
            ("Tailwind CSS (planned)", "Future improvement for even better and consistent designs."),
            ("Markdown/PDF Export", "Allows exporting results as clear, easy-to-share files."),
            ("i18n via Dictionaries", "Switch easily between German and English without page reload."),
        ],
    },
}

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
st.title("🛠️ Technologischer Überblick" if lang == "Deutsch" else "🛠️ Technology Overview")

intro = (
    "Hier siehst du die wichtigsten Technologien und was sie für Vacalyser bewirken."
    if lang == "Deutsch"
    else "An overview of the key technologies driving Vacalyser."
)

st.markdown(intro)

for tech, desc in technology_info[lang][audience]:
    st.markdown(f"### 🔹 {tech}\n{desc}")

st.divider()

footer = (
    "Diese Struktur erlaubt schnelles Weiterentwickeln, übersichtliche Wartung und flexible Erweiterungen."
    if lang == "Deutsch"
    else "This structure enables fast development, easy maintenance, and flexible extension capabilities."
)

st.info(footer)
