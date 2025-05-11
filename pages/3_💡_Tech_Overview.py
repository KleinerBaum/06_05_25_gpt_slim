# pages/tech_overview.py
"""Streamlit‑Seite: Technologischer Überblick & Roadmap

Diese Seite zeigt die aktuelle Architektur von *Vacalyser* und einen
Ausblick auf künftige Schlüsseltechnologien.
Dank Zwei‑Wege‑Schalter passt sich der Text sowohl der Sprache (DE/EN)
als auch der Zielgruppe (Tech‑affin vs. Allgemein verständlich) an.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Sprach- und Zielgruppenumschalter
# ---------------------------------------------------------------------------
lang = st.radio("🌐 Sprache / Language", ("Deutsch", "English"), horizontal=True, key="lang_toggle")
audience = st.radio(
    "🎯 Zielgruppe / Audience",
    ("Tech-interessiert", "Allgemein verständlich") if lang == "Deutsch" else ("Tech‑savvy", "General public"),
    horizontal=True,
    key="audience_toggle"
)

# ---------------------------------------------------------------------------
# Inhalte (DE & EN, je nach Zielgruppe)
# ---------------------------------------------------------------------------
technology_info = {
    "Deutsch": {
        "Tech-interessiert": [
            ("Streamlit", "Framework für Python‑basierte Web‑Apps mit minimalem Overhead. Optimal für schnelle Prototypen und datengetriebene Interfaces."),
            ("Python 3.11", "Moderne Programmiersprache mit Pattern Matching und verbessertem AsyncIO – Basis sämtlicher Business‑Logik."),
            ("OpenAI API (GPT‑4o)", "Übernimmt semantische Textanalyse, Embedding‑Matching und KI‑gestützte Dialogsteuerung in Echtzeit."),
            ("FAISS + LangChain", "Vektorindizierte Suche über ESCO Skills, Aufgaben und Branchendaten für hochrelevante Treffer."),
            ("pypdf, docx2txt", "Automatisches Parsing von Dokumenten (PDF, DOCX) in strukturierte Datensätze für den Session‑State."),
            ("st.session_state", "Persistente Ablage von Nutzer­interaktionen, extrahierten Daten und Flow‑Steuerung."),
            ("ESCO API", "Ontologie‑basierte Zuordnung von Berufen, Kompetenzen und Spezialisierungen nach EU‑Standard."),
            ("Tailwind CSS (geplant)", "Utility‑First CSS‑Framework für konsistente und wartbare Designs."),
            ("Markdown/PDF Export", "Verwandelt Session‑Daten in formatierte, druckfähige Reports und Anforderungsprofile."),
            ("i18n über Dictionaries", "Interne Lösung für internationale Sprachumschaltung ohne Ladezeiten."),
            # ––– Zukunftstechnologien –––
            ("ChromaDB / Weaviate (geplant)", "Persistente Vektor­datenbanken für milliarden­skalierbare RAG‑Workflows mit Live‑Updates."),
            ("OpenAI Function Calling", "Strukturierte API‑Aufrufe zur deterministischen Steuerung komplexer Recruiting‑Pipelines."),
            ("Streaming UI Responses", "Token‑weise Ausgabe für sofortiges Feedback ohne spürbare Latenz."),
            ("Docker & GitHub Actions", "Automatisierte CI/CD‑Pipelines für Build, Test und Deployment in isolierten Containern."),
            ("Telemetry & Observability", "OpenTelemetry‑basiertes Monitoring für Performance‑ und Kosten‑Optimierung."),
        ],
        "Allgemein verständlich": [
            ("Streamlit", "Hilft, schnell moderne Weboberflächen für Daten und Analysen zu erstellen."),
            ("Python 3.11", "Beliebte Computersprache für KI‑ und Datenprojekte."),
            ("OpenAI API (GPT‑4o)", "Künstliche Intelligenz, die Texte versteht, Ideen vorschlägt und Fragen beantwortet."),
            ("FAISS + LangChain", "Schlaue Suche, um schnell passende Fähigkeiten und Aufgaben zu finden."),
            ("pypdf, docx2txt", "Liest Dateien wie PDFs automatisch aus, um Informationen weiterzuverwenden."),
            ("st.session_state", "Stellt sicher, dass bereits eingegebene Daten erhalten bleiben."),
            ("ESCO API", "Europäische Datenbank für Berufe und Kompetenzen."),
            ("Tailwind CSS (geplant)", "Sorgt künftig für noch schönere und einheitlichere Designs."),
            ("Markdown/PDF Export", "Erlaubt, Ergebnisse als übersichtliche Dateien herunterzuladen."),
            ("i18n über Dictionaries", "Schnelles Umschalten zwischen Deutsch und Englisch."),
            # ––– Zukunft –––
            ("ChromaDB / Weaviate (geplant)", "Neue Technik, um große Textmengen blitzschnell zu durchsuchen."),
            ("OpenAI Function Calling", "Erlaubt der KI, festgelegte Aufgaben zuverlässig auszuführen."),
            ("Streaming Antworten", "Antworten erscheinen Stück für Stück, ohne Wartezeit."),
            ("Docker & GitHub Actions", "Automatisches Ausliefern neuer Versionen."),
            ("Telemetry & Observability", "Hilft, Leistung und Kosten im Blick zu behalten."),
        ],
    },
    "English": {
        "Tech‑savvy": [
            ("Streamlit", "Python‑native web‑app framework with minimal overhead, perfect for rapid prototyping and data‑centric UIs."),
            ("Python 3.11", "Modern language baseline featuring structural pattern matching and improved async‑IO."),
            ("OpenAI API (GPT‑4o)", "Real‑time semantic analysis, embedding matching, and conversational orchestration."),
            ("FAISS + LangChain", "Vector‑based retrieval over ESCO skills, tasks, and domain corpora."),
            ("pypdf, docx2txt", "Automated document parsing modules feeding a structured session state."),
            ("st.session_state", "Lightweight persistence layer for user context and UI flow control."),
            ("ESCO API", "Ontology‑driven mapping of occupations and skills in compliance with EU standards."),
            ("Tailwind CSS (planned)", "Utility‑first CSS framework enabling coherent, maintainable design extensions."),
            ("Markdown/PDF Export", "Generates printable job profiles and sourcing reports on demand."),
            ("i18n via Dictionaries", "Instant language switching with no backend round‑trips."),
            # ––– Future stack –––
            ("ChromaDB / Weaviate (planned)", "Persistent vector databases powering RAG at billion‑scale with live updates."),
            ("OpenAI Function Calling", "Structured tool invocation enabling deterministic automation of complex hiring pipelines."),
            ("Streaming UI Responses", "Token streaming for latency‑free incremental rendering."),
            ("Docker & GitHub Actions", "Containerized builds, tests, and deployments with continuous delivery."),
            ("Telemetry & Observability", "OpenTelemetry‑based tracing for performance and cost governance."),
        ],
        "General public": [
            ("Streamlit", "Makes it easy to build modern web pages to show and analyze information."),
            ("Python 3.11", "A popular language often used for AI and data projects."),
            ("OpenAI API (GPT‑4o)", "Artificial intelligence that understands text, suggests ideas, and answers questions."),
            ("FAISS + LangChain", "Smart search helping to quickly find relevant skills and tasks."),
            ("pypdf, docx2txt", "Uploads like PDFs are automatically read for further use."),
            ("st.session_state", "Keeps already entered information available."),
            ("ESCO API", "Database of recognized occupations and skills across Europe."),
            ("Tailwind CSS (planned)", "Will improve design consistency and look in the future."),
            ("Markdown/PDF Export", "Allows exporting results as clear, easy‑to‑share files."),
            ("i18n via Dictionaries", "Switch instantly between German and English."),
            # ––– Future –––
            ("ChromaDB / Weaviate (planned)", "New tech to search huge text collections in a blink."),
            ("OpenAI Function Calling", "Lets the AI perform predefined tasks reliably."),
            ("Streaming Responses", "Answers appear piece by piece without waiting."),
            ("Docker & GitHub Actions", "Automatically delivers new versions online."),
            ("Telemetry & Observability", "Helps keep performance and costs under control."),
        ],
    },
}

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
st.title("🛠️ Technologischer Überblick" if lang == "Deutsch" else "🛠️ Technology Overview")

intro = (
    "Nachfolgend findest du die Schlüsseltechnologien, die Vacalyser heute antreiben, "
    "sowie einen Ausblick darauf, welche Zukunftstechnologien bereits in der Planung sind."
    if lang == "Deutsch"
    else "Below you can explore the core technologies powering Vacalyser today, "
         "plus a glimpse into the future enhancements on our roadmap."
)

st.markdown(intro)

for tech, desc in technology_info[lang][audience]:
    st.markdown(f"### 🔹 {tech}\n{desc}")

st.divider()

footer = (
    "Diese modulare Architektur erlaubt schnelles Weiterentwickeln, einfache Wartung "
    "und bietet eine zukunftssichere Basis für neue Features."
    if lang == "Deutsch"
    else "This modular architecture enables rapid iteration, straightforward maintenance, "
         "and provides a future‑proof foundation for upcoming features."
)

st.info(footer)
