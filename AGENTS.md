# Vacalyser Contributor Guide

This document contains mandatory instructions for all Codex agents and human developers.
It covers environment configuration, coding style, and special AI prompt rules.

## 1. Environment Setup
- **Python**: Version 3.10 or newer is required.
- Install dependencies and the package in editable mode:

```bash
pip install -r requirements.txt
pip install -e .
```

- Create directories `uploads/`, `logs/` and `vector_store/` before running `streamlit run app.py`.

## 2. Environment Variables
Store non‑secret values in `.env` and read them with `os.getenv()`.
Typical variables:

| Variable | Example | Description |
| --- | --- | --- |
| `STREAMLIT_ENV` | `development` | environment switch |
| `LANGUAGE` | `en` | default UI language |
| `DEFAULT_MODEL` | `gpt-4o` | base model name |
| `VECTOR_STORE_PATH` | `./vector_store` | path to vector DB |

## 3. Secrets
Secrets are kept **out of version control**. Use `secrets.toml` or environment variables.
Required secrets include:

- `OPENAI_API_KEY`
- `OPENAI_ORG_ID`

Secrets such as `DATABASE_URL` and `SECRET_KEY` are optional and not required for
local development. Never log or print secret values.

## 4. Coding Standards
- Follow PEP 8 with type hints. All functions and classes need Google‑style
docstrings.
- Run `ruff .`, `black --check .`, `mypy .` and `pytest -q` before committing.
- Use the following branch and commit conventions:
  - Feature branches: `feat/<short-description>`
  - Commits follow **Conventional Commits** (`feat:`, `fix:`, `docs:`, `chore:` …) with
    a subject line of at most 60 characters.
  - Pull requests target the `dev` branch.
- Update the README or changelog and add a migration script if models change.

## 5. Special AI Prompt Guidance
- Retrieve context snippets via `services/vector_search.VectorStore.search()`
  instead of sending whole documents to the LLM.
- Validate every agent response against `models.VacancyProfile`. If parsing fails,
  log the error and reprompt for a corrected response.
- When implementing new tool calls, start with a unit test using a dummy
  response before enabling the real API call.
- Never hard‑code API keys. Access them with `os.getenv`.
- Support multiple languages by loading prompt templates from `utils/prompts.py`
  without overwriting existing templates.

## 6. Project Structure
Key folders and files:

```
app.py               # Streamlit entry point
components/          # UI building blocks
logic/               # Business logic
services/            # External integrations
models/              # Pydantic schemas
state/               # Session handling
utils/               # Prompts & helpers
tests/               # Pytest suite
```

Follow this guide to ensure a consistent and secure workflow.
