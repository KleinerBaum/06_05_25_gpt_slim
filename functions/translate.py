import re

def detect_language(text: str) -> str:
    return "de" if re.search(r"[äöüßÄÖÜ]", text) else "en"

def translate_text(text: str, target_lang: str) -> str:
    return f"[Übersetzt zu {target_lang}]:\n{text}"
