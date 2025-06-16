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
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "./vector_store")

# OpenAI Modell für ChatCompletion (mit Function Calling)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
# OpenAI API Key aus .env oder Streamlit Secrets
# Surrounding quotes in `.env` will be trimmed automatically
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip("\"' ")
# Modellname für Gehaltsschätzung (OpenAI)
SALARY_ESTIMATION_MODEL = os.getenv("SALARY_ESTIMATION_MODEL", "gpt-4o-mini")

# Übernahme aus Streamlit Secrets (falls vorhanden)
try:
    secrets_data = st.secrets.get("openai")
except st.errors.StreamlitSecretNotFoundError:
    secrets_data = None

if secrets_data:
    # API-Key
    if secrets_data.get("OPENAI_API_KEY"):
        OPENAI_API_KEY = secrets_data["OPENAI_API_KEY"]
    # Modellnamen
    if secrets_data.get("OPENAI_MODEL"):
        OPENAI_MODEL = secrets_data["OPENAI_MODEL"]
    if secrets_data.get("SALARY_ESTIMATION_MODEL"):
        SALARY_ESTIMATION_MODEL = secrets_data["SALARY_ESTIMATION_MODEL"]

# OpenAI API Key global setzen, falls vorhanden
if OPENAI_API_KEY:
    from typing import Any, cast
    import openai  # type: ignore

    openai = cast(Any, openai)

    openai.api_key = OPENAI_API_KEY
