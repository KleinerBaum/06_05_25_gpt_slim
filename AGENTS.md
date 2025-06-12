# Vacalyser AGENTS Guide

This project is a slim demonstration of the Vacalyser workflow. Use this file as a quick reference for environment setup and contributor rules.

## Environment Variables
Set non-secret configuration in a `.env` file and read them using `os.environ.get()` in Python. Typical variables:

- `STREAMLIT_ENV` – switch between `development` and `production`.
- `LANGUAGE` – default UI language (`en` or `de`).
- `MODEL_PROVIDER` – model backend (`openai` or `ollama`).
- `DEFAULT_MODEL` – default model name for the provider.
- `VECTOR_STORE_PATH` – path to your vector database directory.


| Variable | Example | Purpose |
| --- | --- | --- |
| STREAMLIT_ENV | development | environment switch |
| LANGUAGE | en | default UI language |
| MODEL_PROVIDER | openai | LLM backend |
| DEFAULT_MODEL | gpt-4o | base model name |
| VECTOR_STORE_PATH | ./vector_store | path to vector DB |

Use these variables for conditional logic or configuration switching.

## Secrets
Keep secrets out of version control. Store them in `secrets.toml` (for Streamlit) or a cloud secret manager.

Required secrets include:

- `OPENAI_API_KEY`
- `OPENAI_ORG_ID`
- `OLLAMA_API_KEY`
- `DATABASE_URL`
- `SECRET_KEY`

Never log or print these values.

## Setup Script
Before running the app locally:

```bash
pip install -r requirements.txt
python scripts/download_models.py    # if models are needed
```

Ensure directories such as `uploads/` and `logs/` exist. Then start the app with `streamlit run app.py`.


## Special AI Prompt Guidance
- Provide clear context about the job role and known session data.
- Use structured prompts like "Extract all available keys ..." for extraction tasks.
- When a key is missing, generate a follow-up question using wording from `data/question_nodes.yml`.
- Include company, team and skill requirements in candidate sourcing prompts.
- Adapt prompts to the chosen LANGUAGE if the job ad is multilingual.

