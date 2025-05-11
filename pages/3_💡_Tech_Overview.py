# pages/tech_overview.py
"""Streamlit‑Seite: Technology Deep Dive & Wizard Flow

Für IT‑Spezialisten und Entscheider bietet diese Seite einen kompakten, aber
technisch fundierten Überblick über den *Vacalyser*‑Stack sowie eine visuelle
Darstellung des mehrstufigen Wizard‑Flows (Discovery‑Process).
Ein Sprach‑ und Zielgruppenumschalter sorgt dafür, dass Texte sowohl für ein
Fach‑Publikum (Tech‑interessiert/Tech‑savvy) als auch für nicht‑technische
Stakeholder (Allgemein verständlich/General public) optimal angepasst werden.
"""

from __future__ import annotations
import streamlit as st

# ---------------------------------------------------------------------------
# Sprach‑ und Zielgruppenumschalter
# ---------------------------------------------------------------------------
lang = st.radio("🌐 Sprache / Language", ("Deutsch", "English"), horizontal=True, key="lang_toggle")
audience = st.radio(
    "🎯 Zielgruppe / Audience",
    ("Tech‑interessiert", "Allgemein verständlich") if lang == "Deutsch" else ("Tech‑savvy", "General public"),
    horizontal=True,
    key="audience_toggle"
)

TECH = "Tech‑interessiert" if lang == "Deutsch" else "Tech‑savvy"

# ---------------------------------------------------------------------------
# Technologie‑Kacheln je Sprache & Zielgruppe
# ---------------------------------------------------------------------------
tech_info: dict[str, dict[str, list[tuple[str, str]]]] = {
    "Deutsch": {
        # ——— Tiefer technischer Einblick für IT‑Spezialisten ———
        "Tech‑interessiert": [
            ("Retrieval‑Augmented Generation (RAG)",
             "FAISS bzw. künftig ChromaDB/Weaviate liefern Vektor‑Suche über mehr
             als 400 k ESCO‑Skills & Domain‑Korpora; RAG‑Pipelines werden über
             LangChain orchestriert."),
            ("LangChain Agents + OpenAI Function Calling",
             "Deterministische Tool‑Aufrufe (PDF‑Parser, ESCO‑Lookup,
             Markdown‑Renderer) mit JSON‑Schemas für robustes Error‑Handling."),
            ("Embedding‑Model",
             "OpenAI *text‑embedding‑3‑small* (8 k‑Dim) – alternative
             Selbst‑Hosting via *e5‑large‑v2* ist vorbereitet."),
            ("Streaming Responses",
             "Tokenweises UI‑Streaming (< 300 ms TTFB) für flüssige Nutzer‑Erfahrung."),
            ("CI/CD Pipeline",
             "GitHub Actions → Docker → Terraform; Canary‑Deployments auf
             Kubernetes (Hetzner Cloud) mit automatischem Rollback."),
            ("Observability & Kosten‑Tracking",
             "OpenTelemetry Tracing + Prometheus /Grafana; Token‑Kosten pro
             Request in st.session_state."),
            ("Security Layer",
             "OIDC‑basiertes Secrets‑Management (GitHub → Vault) & zweistufige
             Rollen‑Logik (Recruiter vs. Admin)."),
            ("Event‑Driven Wizard Flow",
             "State‑Maschine (XState‑Pattern) triggert dynamische Fragen und
             persistiert Zwischenergebnisse als JSON Graph."),
            ("Infrastructure as Code",
             "Komplette Cloud‑Provisionierung in Terraform 1.7 mit automatischen
             Drift‑Detections."),
        ],
        # ——— Vereinfachte Beschreibung für Business‑Lesende ———
        "Allgemein verständlich": [
            ("Künstliche Intelligenz",
             "Vacalyser nutzt modernste KI, um Stellenanforderungen präzise zu
             verstehen und passende Kompetenzen vorzuschlagen."),
            ("Schlaue Suche",
             "Eine Spezial‑Suche findet blitzschnell relevante Fähigkeiten & Aufgaben."),
            ("Fließende Antworten",
             "Antworten erscheinen Stück für Stück – Wartezeiten verkürzen sich."),
            ("Automatische Updates",
             "Neue Versionen werden im Hintergrund eingespielt, ohne Ausfallzeiten."),
            ("Sicherheit & Datenschutz",
             "Aktuelle Standards schützen vertrauliche Daten konsequent."),
        ],
    },
    "English": {
        "Tech‑savvy": [
            ("Retrieval‑Augmented Generation (RAG)",
             "FAISS – future upgrade to ChromaDB/Weaviate – provides vector search
             across 400 k+ ESCO skills & domain corpora; orchestrated via LangChain."),
            ("LangChain Agents & OpenAI Function Calling",
             "Deterministic tool invocation (PDF parser, ESCO lookup, Markdown renderer)
             using strict JSON schemas for resilient error handling."),
            ("Embedding Model",
             "OpenAI *text‑embedding‑3‑small* (8 k dim); self‑hosted fallback with
             *e5‑large‑v2* prepared."),
            ("Streaming Responses",
             "Sub‑300 ms TTFB with token‑level UI streaming for a snappy UX."),
            ("CI/CD Pipeline",
             "GitHub Actions → Docker → Terraform; canary deployments on Kubernetes
             (Hetzner Cloud) with auto‑rollback."),
            ("Observability & Cost Governance",
             "OpenTelemetry tracing + Prometheus/Grafana; token cost per request
             surfaced in st.session_state."),
            ("Security Layer",
             "OIDC‑backed secret management (GitHub → Vault) & dual role model (Recruiter vs. Admin)."),
            ("Event‑Driven Wizard Flow",
             "Finite‑state machine (XState pattern) triggers dynamic questions and
             stores interim results as a JSON graph."),
            ("Infrastructure as Code",
             "Full cloud provisioning in Terraform 1.7 with automatic drift detection."),
        ],
        "General public": [
            ("Artificial Intelligence",
             "Vacalyser uses cutting‑edge AI to understand job requirements and
             suggest matching skills."),
            ("Smart Search",
             "A specialised search engine instantly finds relevant skills and tasks."),
            ("Live Answers",
             "Replies appear gradually, so you don't have to wait."),
            ("Automatic Updates",
             "New versions are rolled out silently with no downtime."),
            ("Security & Privacy",
             "Modern standards keep your data safe at every step."),
        ],
    },
}

# ---------------------------------------------------------------------------
# Wizard‑Flow (Graph) – nur für Tech‑Publikum
# ---------------------------------------------------------------------------
wizard_steps = [
    ("Intake", "Job‑Titel & Dokumente" if lang == "Deutsch" else "Job title & docs"),
    ("Parse", "AI‑Parsing"),
    ("Enrich", "ESCO‑Mapping"),
    ("QA", "Dynamic Q&A"),
    ("Draft", "Profil‑Entwurf" if lang == "Deutsch" else "Draft profile"),
    ("Review", "Freigabe" if lang == "Deutsch" else "Review"),
    ("Export", "Export (PDF/MD)"),
]

def render_wizard_graph() -> None:
    dot = "digraph wizard {\n  rankdir=LR;\n  node [shape=box style=\"rounded,filled\" fontname=Helvetica color=#5b8def fillcolor=#eef4ff];\n"  # noqa: E501
    for step, label in wizard_steps:
        dot += f'  {step} [label="{label}"];\n'
    for i in range(len(wizard_steps) - 1):
        dot += f"  {wizard_steps[i][0]} -> {wizard_steps[i + 1][0]};\n"
    dot += "}"
    st.graphviz_chart(dot)

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
if audience == TECH:
    title = "🛠️ Technology Deep Dive" if lang == "English" else "🛠️ Technischer Deep Dive"
else:
    title = "🛠️ Technology Overview" if lang == "English" else "🛠️ Technologischer Überblick"

st.title(title)

intro_de = "Nachfolgend findest du die Schlüsseltechnologien, die Vacalyser antreiben, " \
          "sowie einen Graphen, der den Discovery‑Prozess Schritt für Schritt veranschaulicht."
intro_en = "Below you can explore the core technologies powering Vacalyser and a graph " \
          "visualising each step of the discovery process."

st.markdown(intro_de if lang == "Deutsch" else intro_en)

# ——— Technologie‑Kacheln ———
for tech, desc in tech_info[lang][audience]:
    st.markdown(f"### 🔹 {tech}\n{desc}")

# ——— Wizard‑Flow‑Graph nur für Tech‑Publikum ———
if audience == TECH:
    st.divider()
    graph_head_de = "#### 🔄 Wizard‑Flow & Zustands­maschine"
    graph_head_en = "#### 🔄 Wizard flow & state machine"
    st.markdown(graph_head_de if lang == "Deutsch" else graph_head_en)
    render_wizard_graph()

st.divider()

footer_de = "Die gezeigte Architektur ist modular erweiterbar und bildet eine " \
            "zukunftssichere Basis für hochskalierbare Recruiting‑Workflows."
footer_en = "The presented stack is modular and future‑proof, enabling scalable " \
            "recruiting workflows with low operational overhead."

st.info(footer_de if lang == "Deutsch" else footer_en)
