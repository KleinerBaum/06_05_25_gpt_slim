# Vacalyser

This repository contains a slim demo of the Vacalyser app. The app uses Streamlit and relies on a few environment variables for configuration.

## Environment Variables

Set these variables in a `.env` file or your deployment environment. Read them in Python via `os.environ.get("VAR_NAME")`.

- `STREAMLIT_ENV` – `development` or `production` to toggle features.
- `LANGUAGE` – default UI language (`en` or `de`).
- `MODEL_PROVIDER` – which LLM backend to use (`openai` or `ollama`).
- `DEFAULT_MODEL` – model name used by the provider (e.g. `gpt-4o`).
- `VECTOR_STORE_PATH` – path to the vector database directory.

## Secrets

Sensitive values must never be committed. Use `secrets.toml` (for Streamlit) or your cloud secret manager for:

- `OPENAI_API_KEY`
- `OPENAI_ORG_ID`
- `OLLAMA_API_KEY`
- `DATABASE_URL`
- `SECRET_KEY`

Ensure `secrets.toml` is excluded via `.gitignore`.

## Setup

Install dependencies and prepare local models before running the app:

```bash
pip install -r requirements.txt
python scripts/download_models.py  # if models are required
```

Create any needed folders (e.g. `uploads/`, `logs/`) before starting Streamlit:

```bash
streamlit run app.py
```
