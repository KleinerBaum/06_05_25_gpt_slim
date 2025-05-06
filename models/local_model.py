import logging
from typing import Generator

class LocalLLM:
    """Sehr vereinfachtes, lokales Mock‑LLM."""
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        self.logger.info("Lokales LLM – Prompt len=%d", len(prompt))
        return "Lokale LLM‑Antwort (Demo)"

    def stream_generate(self, prompt: str, temperature: float = 0.2) -> Generator[str, None, None]:
        for tok in ["Lokale", " ", "Streaming‑", "Antwort"]:
            yield tok
