# config.py
"""Globale Konfiguration für Vacalyser.

Lädt Einstellungen aus .env (lokal) oder st.secrets (Deployment)
und stellt zentrale Parameter zur Verfügung.
"""
import os
import streamlit as st

# .env-Datei laden (sofern vorhanden)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Allgemeine Umgebungsvariablen
STREAMLIT_ENV = os.getenv("STREAMLIT_ENV", "development")
LANGUAGE = os.getenv("LANGUAGE", "en")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "./vector_store")

# OpenAI Modell für ChatCompletion (mit Function Calling)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
# Lokales LLM Modell (für LocalLLMClient)
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "llama3.2-3b")
# Flag: Lokalen Modus verwenden (1/0 in Umgebungsvariable oder Boolean in secrets)
USE_LOCAL_MODE = False
# OpenAI API Key aus .env oder Streamlit Secrets
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Modellname für Gehaltsschätzung (OpenAI)
SALARY_ESTIMATION_MODEL = os.getenv("SALARY_ESTIMATION_MODEL", "gpt-4o-mini")

# Übernahme aus Streamlit Secrets (falls vorhanden)
if "openai" in st.secrets:
    secrets_data = st.secrets["openai"]
    # API-Key
    if secrets_data.get("OPENAI_API_KEY"):
        OPENAI_API_KEY = secrets_data["OPENAI_API_KEY"]
    # Modellnamen
    if secrets_data.get("OPENAI_MODEL"):
        OPENAI_MODEL = secrets_data["OPENAI_MODEL"]
    if secrets_data.get("LOCAL_MODEL"):
        LOCAL_MODEL = secrets_data["LOCAL_MODEL"]
    if secrets_data.get("SALARY_ESTIMATION_MODEL"):
        SALARY_ESTIMATION_MODEL = secrets_data["SALARY_ESTIMATION_MODEL"]
    # Lokaler Modus (als Bool oder "1"/"0")
    if secrets_data.get("USE_LOCAL_MODE") is not None:
        USE_LOCAL_MODE = bool(
            str(secrets_data["USE_LOCAL_MODE"]).strip()
            in {"1", "True", "true"}
        )

# Zusätzlich Umgebungsvariable VACALYSER_LOCAL_MODE (für Kompatibilität)
if os.getenv("VACALYSER_LOCAL_MODE", "") == "1":
    USE_LOCAL_MODE = True

# OpenAI API Key global setzen, falls vorhanden
if OPENAI_API_KEY:
    import openai

    openai.api_key = OPENAI_API_KEY

# Compatibility alias for modules expecting the old variable name
USE_LOCAL_MODEL = USE_LOCAL_MODE
