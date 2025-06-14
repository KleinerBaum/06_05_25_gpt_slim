# Vacalyser – Recruitment Need Analysis Wizard

Vacalyser is an AI powered Streamlit app that turns unstructured job adverts
(PDF, DOCX or URLs) into a structured job specification. It guides hiring
managers step by step from a rough idea to a polished job posting using
OpenAI's GPT models.

## Key Features

- **AI-driven extraction** of existing job descriptions or URLs.
- **Interactive eight-step wizard** available in English and German.
- **Skill suggestions** button in step 5 recommends additional technical and
  soft skills not found in the job ad.
- **Trigger Engine** built on a dependency graph that auto-updates related
  fields as you change inputs.
- **Prompt library and `@tool` functions** for text extraction and web
  scraping.
- **FAISS based vector search** for storing and querying extracted text.
- **Helper utilities** such as `build_boolean_query`,
  `generate_interview_questions` and `summarize_job_ad`.
- **Discovery page** can scrape basic company information from a provided URL.

## Prerequisites

- Python 3.10+
- Streamlit
- OpenAI API key (GPT‑4/GPT‑3.5 access)
- Git for development

## Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/your-org/vacalyser.git
cd vacalyser
pip install -r requirements.txt
pip install -e .
```

Create required directories before running the app:

```bash
mkdir uploads logs vector_store
```

## Configuration

Vacalyser reads non sensitive settings from a `.env` file and secrets from
`secrets.toml` or Streamlit secrets.

| Variable | Default | Description |
| --- | --- | --- |
| STREAMLIT_ENV | development | environment switch |
| LANGUAGE | en | default UI language |
| DEFAULT_MODEL | gpt-4o | base model name |
| VECTOR_STORE_PATH | ./vector_store | path to vector DB |

Example `secrets.toml`:

```toml
[openai]
OPENAI_API_KEY = "YOUR_OPENAI_KEY"
OPENAI_ORG_ID = "YOUR_ORG_ID"
OPENAI_MODEL = "gpt-4o"
SALARY_ESTIMATION_MODEL = "gpt-4o-mini"

[general]
SECRET_KEY = "replace-me"
DATABASE_URL = "postgresql://user:pass@host/db"
```
Replace `YOUR_OPENAI_KEY` with your actual key or set the
`OPENAI_API_KEY` environment variable. Streamlit will read the
environment variable when the key is not present in `secrets.toml`.

## Running the App

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

## Project Structure

```
./
├── app.py               # Streamlit entry point
├── pages/               # Static pages
├── components/          # UI building blocks
├── logic/               # Business logic & processors
├── services/            # External integrations
├── models/              # Pydantic schemas
├── state/               # Session handling
├── utils/               # Prompts, config, helpers
└── tests/               # Pytest suite
```

## Prompt & Tool Registry

Custom `@tool` functions are registered in
`utils/tool_registry.py` and can be listed for OpenAI
function calling. Prompt templates including ESCO API snippets
live in `docs/esco_api_prompts.md` and `utils/`.

## Testing

Run formatting, type checks and unit tests before committing:

```bash
ruff .
black --check .
mypy .
pytest --maxfail=1 --disable-warnings -q
```

## Contributing

1. Fork the repository and create a feature branch.
2. Commit using Conventional Commits (e.g. `feat:` or `fix:`).
3. Ensure lints and tests pass and update the README when necessary.
4. Open a pull request against the `dev` branch.

## License

Vacalyser is released under the MIT License.
