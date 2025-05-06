import streamlit as st
from utils.session_keys import init_session_state
from models.model_selector import get_model

st.set_page_config(page_title="VACalyser – KI‑Job‑Wizard", page_icon="🧩", layout="wide")

# Alle Session‑Keys anlegen
aaa = init_session_state()

# Seitenleiste ➜ Modellwahl
st.sidebar.title("⚙️ Einstellungen")
use_openai = st.sidebar.toggle("OpenAI GPT‑4 nutzen", value=False)
model = get_model(use_openai=use_openai)
st.session_state['model'] = model

st.sidebar.info("Wähle eine Seite (Home, Wizard …) im Seitenmenü oben links.")

st.markdown("""
## Willkommen bei **VACalyser**  
Dein KI‑Assistent für strukturierte Recruiting‑Bedarfsanalysen.
""")
