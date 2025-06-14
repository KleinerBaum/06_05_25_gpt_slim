# Vacalyser
## Setup

Install dependencies before running the app (includes `faiss-cpu` for the vector store):

```bash
pip install -r requirements.txt
```

Create any needed folders (e.g. `uploads/`, `logs/`) before starting Streamlit:

```bash
streamlit run app.py
```

### API Keys

AI-powered features require an OpenAI API key. Create a `.streamlit/secrets.toml` file and add your credentials there. Example:

```toml
[openai]
OPENAI_API_KEY = "YOUR_OPENAI_KEY"
OPENAI_ORG_ID = "YOUR_OPENAI_ORG_ID"

[database]
DATABASE_URL = "postgresql://user:password@host/db"

[general]
SECRET_KEY = "replace-me"
```

You can also place these values in a `.env` file and load them in Python via
`os.getenv`.

### Environment Variables

| Variable | Example | Purpose |
| --- | --- | --- |
| STREAMLIT_ENV | development | environment switch |
| LANGUAGE | en | default UI language |
| DEFAULT_MODEL | gpt-4o | base model name |
| VECTOR_STORE_PATH | ./vector_store | path to vector DB |

## Project Structure

```
./
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

### Features

- Start discovery page can scrape basic company information when a website URL is provided.

## ESCO API Prompt Templates

A collection of ready-made prompts for querying the ESCO API is available in [docs/esco_api_prompts.md](docs/esco_api_prompts.md).
