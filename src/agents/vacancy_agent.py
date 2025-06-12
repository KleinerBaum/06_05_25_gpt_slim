from __future__ import annotations
import json
import logging
import time
from typing import Any, Dict, Iterator, List

import requests
import openai

# Globale Konfiguration laden (Modellwahl, API-Schlüssel, usw.)
from src.config import config

# Logger konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Eigene Exception für Ollama-spezifische Fehler
class _OllamaError(RuntimeError):
    """Wird ausgelöst, wenn der Ollama-Server einen Fehler zurückgibt."""
    pass

# Client-Klasse für lokales LLM (Ollama)
class LocalLLMClient:
    """Wrapper für Ollamas HTTP-Endpunkt (non-streaming und streaming)."""
    def __init__(self, model_name: str, host: str = "localhost", port: int = 11434,
                 request_timeout: int = 120, log_level: int = logging.INFO) -> None:
        self.model = model_name
        self.base_url = f"http://{host}:{port}/api"
        self.timeout = request_timeout
        logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")
        self._log = logging.getLogger("LocalLLMClient")

    def generate(self, text: str, system: str | None = None, **params) -> str:
        """Führt eine einmalige Completion-Anfrage (kein Streaming) durch."""
        payload = self._build_payload(text, system, stream=False, **params)
        data = self._post("/generate", payload)
        return data.get("response", "").rstrip()

    def generate_iter(self, text: str, system: str | None = None, **params) -> Iterator[str]:
        """Streamt Completion-Ergebnisse tokenweise (Iterator über Teil-Ergebnisse)."""
        payload = self._build_payload(text, system, stream=True, **params)
        with requests.post(self.base_url + "/generate", json=payload, stream=True, timeout=self.timeout) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                part = json.loads(line.decode())
                if part.get("done"):
                    break
                yield part.get("response", "")

    def _build_payload(self, text: str, system: str | None, stream: bool, **extra) -> dict:
        prompt_parts: List[str] = []
        if system:
            prompt_parts.append(system.strip())
        prompt_parts.append(text.strip())
        prompt = "\n".join(prompt_parts)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }
        payload.update(extra)
        return payload

    def _post(self, path: str, json_body: dict) -> dict:
        url = self.base_url + path
        self._log.debug("POST %s", url)
        start = time.perf_counter()
        resp = requests.post(url, json=json_body, timeout=self.timeout)
        latency = time.perf_counter() - start
        self._log.debug("%.3fs – status %s", latency, resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise _OllamaError(data["error"])
        return data

# Modus festlegen (OpenAI vs. lokales Modell) basierend auf Konfiguration
USE_LOCAL_MODEL = config.USE_LOCAL_MODEL

# LLM-Client initialisieren
if USE_LOCAL_MODEL:
    # Lokales LLaMA-Modell über Ollama
    local_client = LocalLLMClient(model_name="llama3.2-3b")
else:
    # OpenAI-Modus (API-Key wird via config gesetzt)
    pass  # Keine spezielle Initialisierung notwendig

# Funktionen (Tools) für OpenAI Function Calling definieren
FUNCTIONS = [
    {
        "name": "scrape_company_site",
        "description": "Fetch basic company info (title and meta description) from a company website.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL of the company homepage."}
            },
            "required": ["url"]
        }
    },
    {
        "name": "extract_text_from_file",
        "description": "Extract readable text from an uploaded job-ad file (PDF, DOCX, or TXT).",
        "parameters": {
            "type": "object",
            "properties": {
                "file_content": {"type": "string", "description": "Base64-encoded file content."},
                "filename":    {"type": "string", "description": "Original filename with extension."}
            },
            "required": ["file_content", "filename"]
        }
    }
]

# System-Rollen-Nachricht für den Assistant
SYSTEM_MESSAGE = (
    "You are Vacalyser, an AI assistant for recruiters. "
    "Your job is to extract detailed, structured job vacancy information from input text (job ads) or websites. "
    "Return the information as JSON that matches the schema of the JobSpec model, with no extra commentary."
)

def auto_fill_job_spec(input_url: str = "", file_bytes: bytes = None, file_name: str = "",
                       summary_quality: str = "standard") -> Dict[str, Any]:
    """
    Analysiert eine Stellenanzeige von einer URL oder Datei und gibt die extrahierten Felder als Dict zurück.
    - input_url: URL einer Stellenanzeige (falls angegeben).
    - file_bytes: Rohbytes einer hochgeladenen Stellenbeschreibung.
    - file_name: Dateiname der hochgeladenen Datei.
    - summary_quality: {'economy', 'standard', 'high'} – bei sehr langen Texten wie stark zusammengefasst werden soll.
    """
    # Eingabe validieren
    if not input_url and not file_bytes:
        raise ValueError("auto_fill_job_spec erfordert entweder eine URL oder eine Datei als Eingabe.")
    if input_url and file_bytes:
        # Bei beiden Eingaben: URL priorisieren, Datei ignorieren
        file_bytes = None
        file_name = ""

    # Nutzeranweisung (Prompt) für das LLM vorbereiten
    user_message = ""
    if input_url:
        user_message += f"The job ad is located at this URL: {input_url}\n"
    if file_bytes:
        user_message += "A job ad file is provided. Please analyze its contents carefully.\n"
    user_message += "Extract all relevant job information and return it in JSON format matching the JobSpec schema."

    # Falls der Dateitext sehr lang ist: vorab zusammenfassen, um Tokens zu sparen
    if file_bytes and file_name:
        try:
            text_length = len(file_bytes)
        except Exception:
            text_length = 0
        if text_length > 100_000:  # ~100 KB
            from src.tools.file_tools import extract_text_from_file
            from src.utils.summarize import summarize_text
            extracted_text = extract_text_from_file(file_bytes, file_name)
            if isinstance(extracted_text, str) and len(extracted_text) > 5000:
                summary = summarize_text(extracted_text, quality=summary_quality)
                # Anweisung an Assistant zur Verwendung der Zusammenfassung anpassen
                user_message = (
                    "The job ad text was summarized due to length. "
                    "Please extract job info from the following summary:\n"
                    f"{summary}\nReturn the info as JSON per JobSpec."
                )

    # Bei lokalem Modell: HTML-Inhalt vorab holen, da kein Function Calling verfügbar
    if USE_LOCAL_MODEL:
        if input_url:
            try:
                from src.tools.scraping_tools import scrape_company_site
                site_info = scrape_company_site(url=input_url)
                if isinstance(site_info, dict) and (site_info.get("title") or site_info.get("description")):
                    user_message += "\n(Website summary: " + (site_info.get("title", "") or "") + ": " + (site_info.get("description", "") or "") + ")"
            except Exception as e:
                logger.warning(f"Website-Scraping fehlgeschlagen: {e}")

    # LLM-Aufruf durchführen (unterschieden nach Modus)
    content = ""
    if USE_LOCAL_MODEL:
        # Lokales LLM direkt mit zusammengesetztem Prompt nutzen
        try:
            content = local_client.generate(text=user_message, system=SYSTEM_MESSAGE)
        except Exception as e:
            logger.error(f"Lokale LLM-Generierung fehlgeschlagen: {e}")
            return {}
    else:
        # OpenAI API mit Function Calling
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": user_message}
        ]
        try:
            response = openai.ChatCompletion.create(
                model=config.OPENAI_MODEL,
                messages=messages,
                functions=FUNCTIONS,
                function_call="auto",
                temperature=0.2,
                max_tokens=1500
            )
        except Exception as api_error:
            logger.error(f"OpenAI API Fehler in auto_fill_job_spec: {api_error}")
            return {}
        first_message = response.choices[0].message
        if hasattr(first_message, "function_call") and first_message.function_call:
            # Wenn das LLM eine Tool-Funktion aufruft, diese ausführen
            func_name = first_message.function_call.name
            func_args = {}
            try:
                func_args = json.loads(first_message.function_call.arguments or "{}")
            except Exception:
                pass
            func_result = ""
            try:
                if func_name == "scrape_company_site":
                    from src.tools.scraping_tools import scrape_company_site
                    result_data = scrape_company_site(**func_args)
                    if isinstance(result_data, dict):
                        func_result = ((result_data.get("title") or "") + "\n" + (result_data.get("description") or "")).strip()
                    else:
                        func_result = str(result_data)
                elif func_name == "extract_text_from_file":
                    from src.tools.file_tools import extract_text_from_file
                    import base64
                    file_content_str = func_args.get("file_content", "")
                    filename = func_args.get("filename", "")
                    try:
                        file_bytes_input = base64.b64decode(file_content_str)
                    except Exception:
                        file_bytes_input = file_content_str.encode("utf-8", "ignore")
                    func_result = extract_text_from_file(file_bytes_input, filename) or ""
                    if not isinstance(func_result, str):
                        func_result = str(func_result)
            except Exception as e:
                logger.error(f"Fehler bei Tool-Ausführung {func_name}: {e}")
            # Ergebnis der Funktion als Assistant-Antwort hinzufügen und zweiten API-Call durchführen
            messages.append({"role": "function", "name": func_name, "content": func_result})
            try:
                second_response = openai.ChatCompletion.create(
                    model=config.OPENAI_MODEL,
                    messages=messages,
                    functions=FUNCTIONS,
                    function_call="auto",
                    temperature=0.2,
                    max_tokens=1500
                )
            except Exception as api_error:
                logger.error(f"OpenAI API Fehler beim zweiten Aufruf: {api_error}")
                return {}
            content = second_response.choices[0].message.content or ""
        else:
            # Das LLM hat direkt geantwortet (keine Funktion benötigt)
            content = first_message.content or ""
        if not content:
            return {}

    # 'content' sollte nun den JSON-String entsprechend JobSpec enthalten
    content_str = content.strip()
    if content_str.startswith("```"):
        # Etwaige Markdown-Formatierung entfernen
        content_str = content_str.strip("``` \n")
    if content_str == "":
        return {}
    # JSON-String in Pydantic-Modell JobSpec validieren und parsen
    try:
        from src.models.job_models import JobSpec
        job_spec = JobSpec.model_validate_json(content_str)
    except Exception as e:
        logger.error(f"Assistant lieferte kein gültiges JSON. Fehler: {e}")
        if not USE_LOCAL_MODEL:
            # Versuchen, das LLM sein Format korrigieren zu lassen
            repair_system_msg = "Your previous output was not valid JSON. Only output a valid JSON matching JobSpec now."
            try:
                repair_resp = openai.ChatCompletion.create(
                    model=config.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_MESSAGE},
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": content_str},
                        {"role": "system", "content": repair_system_msg}
                    ],
                    temperature=0,
                    max_tokens=1200
                )
                content_str = repair_resp.choices[0].message.content.strip()
                job_spec = JobSpec.model_validate_json(content_str)
            except Exception as e:
                logger.error(f"Reparaturversuch fehlgeschlagen: {e}")
                return {}
        else:
            return {}
    # Als Python-Dictionary zurückgeben
    return job_spec.model_dump()
