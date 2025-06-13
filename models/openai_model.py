import os
import logging
import openai

class OpenAIModel:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        key_from_env = os.getenv("OPENAI_API_KEY")
        if key_from_env:
            openai.api_key = key_from_env
        if not openai.api_key:
            self.logger.warning(
                "OPENAI_API_KEY fehlt – OpenAI-Aufrufe schlagen fehl."
            )

    def generate(self, prompt: str, temperature: float = 0.2) -> str:
        if not openai.api_key:
            return "[Kein API‑Key – Demo‑Modus]"
        resp = openai.ChatCompletion.create(model="gpt-4o-mini",
                                            messages=[{"role": "user", "content": prompt}],
                                            temperature=temperature)
        return resp.choices[0].message.content.strip()
