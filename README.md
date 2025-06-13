# Vacalyser
## Setup

Install dependencies before running the app:

```bash
pip install -r requirements.txt
```

Create any needed folders (e.g. `uploads/`, `logs/`) before starting Streamlit:

```bash
streamlit run app.py
```

### API Keys

AI-powered features require an OpenAI API key. Set `OPENAI_API_KEY` in your `.env` file or in `secrets.toml` so the wizard can extract information automatically.

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

## ESCO API Prompt Templates

A collection of ready-made prompts for querying the ESCO API is available in [docs/esco_api_prompts.md](docs/esco_api_prompts.md).
