# src/agents/vacancy_agent.py

from __future__ import annotations
import os
import json
import logging
import time
from typing import Any, Dict, Iterator, List
import requests
from src.models.job_models import JobSpec  # Pydantic model for job spec
from src.tools.scraping_tools import scrape_company_site
from src.tools.file_tools import extract_text_from_file
from src.utils.summarize import summarize_text
+import openai
+import streamlit as st
+import src.config as config

# Set OpenAI API key from Streamlit secrets
USE_LOCAL_MODEL = config.USE_LOCAL_MODE

# Expose LocalLLMClient for external use
__all__ = ["LocalLLMClient"]

# Custom exception for Ollama errors
class _OllamaError(RuntimeError):
    """Raised when the Ollama server returns an error message."""

# Local Ollama client for LLM
class LocalLLMClient:
    """Small wrapper for Ollama's HTTP generate endpoint (non-streaming and streaming)."""
    def __init__(self, model_name: str, host: str = "localhost", port: int = 11434,
                 request_timeout: int = 120, log_level: int = logging.INFO) -> None:
        self.model = model_name
        self.base_url = f"http://{host}:{port}/api"
        self.timeout = request_timeout
        logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")
        self._log = logging.getLogger("LocalLLMClient")

    def generate(self, text: str, system: str | None = None, **params) -> str:
        """Perform a single completion request (no streaming)."""
        payload = self._build_payload(text, system, stream=False, **params)
        data = self._post("/generate", payload)
        return data.get("response", "").rstrip()

    def generate_iter(self, text: str, system: str | None = None, **params) -> Iterator[str]:
        """Stream completion tokens as they arrive (yields one chunk at a time)."""
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
            "stream": stream,
        }
        payload.update(extra)  # e.g., temperature, top_p
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

# Determine runtime mode (OpenAI API vs LocalAI) from environment variable
USE_LOCAL_MODEL = os.getenv("VACALYSER_LOCAL_MODE", "0") == "1"

# Initialize the appropriate LLM client based on mode
if USE_LOCAL_MODEL:
    # Using local LLaMA 3.2 model via Ollama
    local_client = LocalLLMClient(model_name="llama3.2-3b")
else:
    # Using OpenAI API (make sure API key is set)
    import openai
    openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY") or st.secrets["openai"]["OPENAI_API_KEY"])

# Define available tools for the assistant (for OpenAI function calling)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "scrape_company_site",
            "description": "Fetch basic company info (title and meta description) from a company website.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL of the company homepage."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
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
    }
    # (Note: In OpenAI’s Python SDK, we could pass actual function objects via function_call,
    # but here we define the schema explicitly for clarity.)
]

# System role prompt defining the assistant’s identity and primary task
SYSTEM_MESSAGE = (
    "You are Vacalyser, an AI assistant for recruiters. "
    "Your job is to extract detailed, structured job vacancy information from input text (job ads) or websites. "
    "Return the information as JSON that matches the schema of the JobSpec model, with no extra commentary."
)

def auto_fill_job_spec(input_url: str = "", file_bytes: bytes = None, file_name: str = "", 
                       summary_quality: str = "standard") -> Dict[str, Any]:
    """
    Analyze a job description from a URL or file and return extracted fields as a dict.
    - input_url: URL of a job advertisement webpage (if provided).
    - file_bytes: Raw bytes of an uploaded job description file.
    - file_name: Filename of the uploaded file.
    - summary_quality: {"economy", "standard", "high"} – how much to compress the content if it's large.
    """
    # Validate input
    if not input_url and not file_bytes:
        raise ValueError("auto_fill_job_spec requires either a URL or a file input.")
    if input_url and file_bytes:
        # If both URL and file are provided, prioritize URL and ignore file to avoid confusion
        file_bytes = None
        file_name = ""

    # Prepare user message for the LLM
    user_message = ""
    if input_url:
        user_message += f"The job ad is located at this URL: {input_url}\n"
    if file_bytes:
        user_message += "A job ad file is provided. Please analyze its contents carefully.\n"
    user_message += "Extract all relevant job information and return it in JSON format matching the JobSpec schema."

    # If the input text is very long, consider summarizing to conserve token context for the model
    if file_bytes and file_name:
        try:
            text_length = len(file_bytes)
        except Exception:
            text_length = 0
        # If file >100KB, summarize content depending on quality setting
        if text_length > 100_000:  # ~100 KB
            extracted_text = extract_text_from_file(file_content=file_bytes.decode('utf-8', errors='ignore'), 
                                                   filename=file_name)
            if isinstance(extracted_text, str) and len(extracted_text) > 5000:
                summary = summarize_text(extracted_text, quality=summary_quality)
                # Instruct the assistant to use the summary instead of full text
                user_message = (
                    "The job ad text was summarized due to length. "
                    "Please extract job info from the following summary:\n"
                    f"{summary}\nReturn the info as JSON per JobSpec."
                )
    # If using local model, we can't rely on function calling – handle URL content upfront
    if USE_LOCAL_MODEL:
        if input_url:
            try:
                site_info = scrape_company_site(url=input_url)
                # Append site info (title/description) to assist the local model
                if site_info.get("title") or site_info.get("description"):
                    user_message += "\n"
                    user_message += f"(Website summary: {site_info.get('title','')}: {site_info.get('description','')})"
            except Exception as e:
                logging.warning(f"Website scraping failed: {e}")

    # Call the appropriate LLM (local or OpenAI) to get the job spec JSON
    if USE_LOCAL_MODEL:
        # Local LLM mode
        try:
            response_text = local_client.generate(text=user_message, system=SYSTEM_MESSAGE)
        except Exception as e:
            logging.error(f"Local model generation failed: {e}")
            return {}
        content = response_text
    else:
        # OpenAI API mode
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4-0613",  # GPT-4 with function calling support
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": user_message}
                ],
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=1500
            )
        except Exception as api_error:
            logging.error(f"OpenAI API error in auto_fill_job_spec: {api_error}")
            return {}
        # Extract the assistant's message (after any function calls)
        try:
            content = response.choices[0].message.content
        except Exception as e:
            logging.error(f"Unexpected response structure: {e}")
            return {}
        if not content:
            # Handle case where assistant used tools but gave no final message
            content = ""
            if hasattr(response, "choices") and response.choices:
                try:
                    # Try to capture any tool call results (if present)
                    tool_calls = response.choices[0].finish_reason
                except Exception:
                    tool_calls = None
                content = str(tool_calls) or ""
            if not content:
                return {}

    # Now 'content' should be a JSON string representing JobSpec. Validate and parse it.
    content_str = content.strip()
    if content_str.startswith("```"):
        # Remove Markdown formatting if present
        content_str = content_str.strip("``` \n")
    if content_str == "":
        return {}
    try:
        job_spec = JobSpec.model_validate_json(content_str)
    except Exception as e:
        logging.error(f"Vacalyser assistant returned invalid JSON. Error: {e}")
        # If JSON invalid, attempt a fix by asking the model to correct its output
        if not USE_LOCAL_MODEL and openai_client:
            repair_system_msg = "Your previous output was not valid JSON. Only output a valid JSON matching JobSpec now."
            try:
                repair_resp = openai_client.chat.completions.create(
                    model="gpt-4-0613",
                    messages=[
                        {"role": "system", "content": SYSTEM_MESSAGE},
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": content_str},
                        {"role": "system", "content": repair_system_msg}
                    ],
                    tools=[],
                    temperature=0,
                    max_tokens=1200
                )
                content_str = repair_resp.choices[0].message.content.strip()
                job_spec = JobSpec.model_validate_json(content_str)
            except Exception as e:
                logging.error(f"Repair attempt failed: {e}")
                return {}
        else:
            return {}
    # Return the parsed job spec as a dictionary
    return job_spec.model_dump()
