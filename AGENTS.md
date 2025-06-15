# Vacalyser AGENTS Guide  
_A quick-reference for anyone wiring up, extending, or testing the LLM-powered workflow._

---

## 1&nbsp;·&nbsp;Purpose

This file collects **all “How do I talk to / wire up the Vacalyser agents?” know-how** in one concise place.  
Keep it updated whenever you add a new tool, model, or environment knob.

---

## 2&nbsp;·&nbsp;Project recap (TL;DR)

```text
vacalyser/
├─ app.py                    # Streamlit entry-point (Landing + Wizard)
├─ components/               # Re-usable Streamlit widgets
├─ logic/                    # Business logic + processors + DAG
├─ models/                   # Pydantic schemas (JobSpec, SalaryBand…)
├─ services/
│   ├─ vacancy_agent.py      # ↖️  LLM orchestration / Function-calling
│   └─ vector_search.py      # FAISS wrapper (skills, benchmarks)
└─ utils/                    # Config, prompt templates, tool_registry …
The agent lives in services/vacancy_agent.py and uses OpenAI function-calling to:

Decide which tool to call (scrape_company_site, extract_text_from_file, …)

Receive tool results as a function message

Respond with JSON matching models.JobSpec (validated & repaired here)

3 · Environment variables
Variable	Example	Purpose
STREAMLIT_ENV	development	Toggle debug / prod settings
LANGUAGE	en / de	Default UI language
DEFAULT_MODEL	gpt-4o	Fallback model if none is provided
VECTOR_STORE_PATH	./vector_store	Path to FAISS directory
OPENAI_MODEL	gpt-4o-mini	Main chat model for extraction / enrichment
SALARY_ESTIMATION_MODEL	gpt-4o-mini	Fast model for salary benchmarks

Tip: Load from .env locally, but rely on Streamlit secrets.toml in prod:

toml
Kopieren
Bearbeiten
# .streamlit/secrets.toml
[openai]
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL   = "gpt-4o"
4 · Secrets (never commit)
OPENAI_API_KEY

OPENAI_ORG_ID (optional)

DATABASE_URL (optional for future persistence)

SECRET_KEY (if you add Flask/Django endpoints)

5 · Installing & running
bash
Kopieren
Bearbeiten
pip install -r requirements.txt
streamlit run app.py          # launches the wizard
Create empty folders the first time:

bash
Kopieren
Bearbeiten
mkdir -p uploads logs vector_store
6 · Agent design guidelines
6.1 Registered tools
Add a new callable like so:

python
Kopieren
Bearbeiten
from vacalyser.utils.tool_registry import tool

@tool(
    name="my_cool_fetcher",
    description="Fetches XYZ data from an internal API.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term"}
        },
        "required": ["query"],
    },
    return_type="string",
)
def my_cool_fetcher(query: str) -> str:
    ...
It will auto-appear in tool_registry.list_openai_functions() and therefore be available to the agent.

6.2 LLM rules of thumb
Task	Model	Temp	Max tokens	Comment
Parsing raw ads → JobSpec	gpt-4o	0.2	1500	High accuracy, function-calling enabled
Quick suggestions (tasks, skills)	gpt-4o-mini	0.3	200	Cheap & fast
Final polished job-ad generation	gpt-4o (or 4o-high)	0.5	1200	Richer language, multilingual

Always ask for structured JSON when possible; unstructured markdown costs more to post-process.

7 · Mock / offline mode
When STREAMLIT_ENV=development and OPENAI_API_KEY is absent,
services/vacancy_agent.py will automatically fall back to local mocks:

scrape_company_site → returns {title: "ACME GmbH", description: "We build rockets"}

extract_text_from_file → parses file but skips LLM post-processing

LLM calls → replaced by fixtures in tests/mocks/

Use this to write fast CI tests without external calls.

8 · Prompt patterns
Extraction –
"Extract ALL fields defined in JobSpec as JSON. Omit commentary. If unknown, set value to null."

Follow-up questions –
"For every missing ★ field, formulate ONE concise question in {LANGUAGE}. Use terminology from data/question_nodes.yml"

Skill enrichment –
"Given must_have_skills, suggest 3 complementary nice_to_have_skills via ESCO synonyms."

Generation –
"Write a {ad_length_preference} job ad in {language_of_ad}…" (template in utils/prompts.py)

Keep temperature low for deterministic JSON, higher for creative text.

9 · Testing & CI
Unit tests – target processors & file parsers (pytest -q).

Streamlit smoke test – streamlit run app.py --server.headless true in GitHub Actions.

Lint / Type-check – flake8 + black --check + mypy .

Remember to mock the OpenAI module (unittest.mock.patch("openai.responses.create", …)).

10 · Contributing checklist
 New tool decorated with @tool, documented here

 Model changes mirrored in JobSpec and wizard keys

 Added/updated tests

 pre-commit run --all-files passes

 Updated this file if behaviour or env-vars changed
