# Vacalyser

This repository contains a slim demo of the Vacalyser app. The app uses Streamlit and relies on a few environment variables for configuration.

## Environment Variables

Set these variables in a `.env` file or your deployment environment. Read them in Python via `os.environ.get("VAR_NAME")`.

- `STREAMLIT_ENV` – `development` or `production` to toggle features.
- `LANGUAGE` – default UI language (`en` or `de`).
- `DEFAULT_MODEL` – OpenAI model name (e.g. `gpt-4o`).
- `VECTOR_STORE_PATH` – path to the vector database directory.

| Variable | Example | Purpose |
| --- | --- | --- |
| STREAMLIT_ENV | development | environment switch |
| LANGUAGE | en | default UI language |
| DEFAULT_MODEL | gpt-4o | base model name |
| VECTOR_STORE_PATH | ./vector_store | path to vector DB |


## Secrets

Sensitive values must never be committed. Use `secrets.toml` (for Streamlit) or your cloud secret manager for:

- `OPENAI_API_KEY`
- `OPENAI_ORG_ID`
- `DATABASE_URL`
- `SECRET_KEY`

Ensure `secrets.toml` is excluded via `.gitignore`.

## Setup

Install dependencies before running the app:

```bash
pip install -r requirements.txt
```

Create any needed folders (e.g. `uploads/`, `logs/`) before starting Streamlit:

```bash
streamlit run vacalyser/app.py
```

## Project Structure

```
vacalyser/
├── app.py
├── pages/
├── components/
├── logic/
├── services/
├── models/
├── state/
├── utils/
└── tests/
```

## ESCO API Prompt Templates

A collection of ready-made prompts for querying the ESCO API is available in [docs/esco_api_prompts.md](docs/esco_api_prompts.md).
