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

You can also set the variables via a `.env` file during local development.

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
- Vacancy agent includes automatic JSON repair to ensure outputs match the JobSpec schema (tested in `tests/test_vacancy_agent.py`).

## ESCO API Prompt Templates

A collection of ready-made prompts for querying the ESCO API is available in [docs/esco_api_prompts.md](docs/esco_api_prompts.md).
