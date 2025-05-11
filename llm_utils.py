# llm_utils.py
# ─────────────────────────────────────────────────────────────────────────────
"""Utilities for LLM interactions (OpenAI API and local Ollama models).
Includes local LLM client, OpenAI client initialization, tool definitions, and
functions to generate structured job specs from input sources."""

from __future__ import annotations
import os, json, logging, base64, time
import requests

# Optional Streamlit secrets integration for API keys
try:
    import streamlit as st
    _openai_api_key = os.getenv("OPENAI_API_KEY") or st.secrets["openai"]["OPENAI_API_KEY"]
except Exception:
    _openai_api_key = os.getenv("OPENAI_API_KEY", "")

import openai
if _openai_api_key:
    openai.api_key = _openai_api_key

# Import Pydantic model for schema validation
from src.models.job_models import JobSpec

# Import tool functions for scraping and file text extraction
from src.scraping_tools import scrape_company_site
from src.file_tools import extract_text_from_file

# Optional text summarization utility
try:
    from src.summarize import summarize_text
except ImportError:
    summarize_text = None

# Determine runtime mode (OpenAI API vs local Ollama) using environment variable
USE_LOCAL_MODEL: bool = os.getenv("VACALYSER_LOCAL_MODE", "0") == "1"

class _OllamaError(RuntimeError):
    """Raised when the local Ollama server returns an error."""
    pass

class LocalLLMClient:
    """Client for local LLM via Ollama's HTTP API (non-streaming requests)."""
    def __init__(self, model_name: str, host: str = "localhost", port: int = 11434,
                 request_timeout: int = 120, log_level: int = logging.INFO) -> None:
        self.model = model_name
        self.base_url = f"http://{host}:{port}/api"
        self.timeout = request_timeout
        logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")
        self._log = logging.getLogger("LocalLLMClient")

    def generate(self, text: str, system: str | None = None, **params) -> str:
        """Generate a completion for the given prompt (optionally with system context)."""
        payload = self._build_payload(text, system, stream=False, **params)
        data = self._post("/generate", payload)
        # The local API returns a JSON with 'response'
        return data.get("response", "").rstrip()

    def generate_iter(self, text: str, system: str | None = None, **params):
        """Stream completion chunks for the given prompt (generator)."""
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
        # Construct prompt with optional system role content
        parts: list[str] = []
        if system:
            parts.append(system.strip())
        parts.append(text.strip())
        prompt = "\n".join(parts)
        payload = {"model": self.model, "prompt": prompt, "stream": stream}
        payload.update(extra)  # add parameters like temperature, etc.
        return payload

    def _post(self, path: str, json_body: dict) -> dict:
        url = self.base_url + path
        self._log.debug(f"POST {url}")
        start = time.perf_counter()
        resp = requests.post(url, json=json_body, timeout=self.timeout)
        latency = time.perf_counter() - start
        self._log.debug(f"{latency:.3f}s – status {resp.status_code}")
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise _OllamaError(data["error"])
        return data

# Initialize local or OpenAI client based on mode
local_client: LocalLLMClient | None = None
if USE_LOCAL_MODEL:
    local_client = LocalLLMClient(model_name="llama2-7b")

# Define available tools for OpenAI function calling
TOOLS = [
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
        "description": "Extract readable text from an uploaded job ad file (PDF, DOCX, or TXT).",
        "parameters": {
            "type": "object",
            "properties": {
                "file_content": {"type": "string", "description": "Base64-encoded file content."},
                "filename":    {"type": "string", "description": "Original filename including extension."}
            },
            "required": ["file_content", "filename"]
        }
    }
]

# System role prompt guiding the assistant's behavior
SYSTEM_MESSAGE: str = (
    "You are Vacalyser, an AI assistant for recruiters. "
    "Extract detailed, structured job vacancy information from the provided input (job ad text or website). "
    "Return only a JSON output that matches the schema of the JobSpec model, with no extra commentary."
)

def extract_job_spec(input_url: str = "", file_bytes: bytes = None, file_name: str = "", summary_quality: str = "standard") -> dict:
    """
    Analyze a job advertisement from a URL or uploaded file and return extracted fields as a dict.
    At least one of input_url or file_bytes must be provided.
    """
    if not input_url and not file_bytes:
        raise ValueError("No input provided to extract_job_spec. Please provide a URL or file.")
    if input_url and file_bytes:
        # Prioritize URL over file if both given
        file_bytes = None
        file_name = ""

    # Build the user prompt
    user_message = ""
    if input_url:
        user_message += f"The job ad is located at this URL: {input_url}\n"
    if file_bytes:
        user_message += "A job ad file is provided. Please analyze its contents carefully.\n"
    user_message += "Extract all relevant job information and return it in JSON format matching the JobSpec schema."

    # Handle potentially large input: summarize if needed
    long_text_summary_mode = False
    if file_bytes and file_name:
        try:
            file_size = len(file_bytes)
        except Exception:
            file_size = 0
        # If file is large, extract text and summarize to reduce prompt length
        if file_size > 100_000:  # >100KB
            text = extract_text_from_file(file_bytes, file_name)
            if summarize_text and isinstance(text, str) and len(text) > 5000:
                summary = summarize_text(text, quality=summary_quality)
                user_message = (
                    "The job ad text was summarized due to length. "
                    "Please extract job info from the following summary:\n"
                    f"{summary}\nReturn the info as JSON per the JobSpec schema."
                )
                long_text_summary_mode = True

    # Choose LLM path: local model or OpenAI API
    try:
        if USE_LOCAL_MODEL:
            # Local mode: handle URL/file content upfront since no function calling
            if input_url:
                try:
                    info = scrape_company_site(url=input_url)
                    if info.get("title") or info.get("description"):
                        user_message += "\n(Note: Website info – {title}: {desc})".format(
                            title=info.get("title", ""), desc=info.get("description", "")
                        )
                except Exception as e:
                    user_message += f"\n(Note: Could not scrape site: {e})"
            if file_bytes and file_name and not long_text_summary_mode:
                try:
                    text = extract_text_from_file(file_bytes, file_name)
                    if summarize_text and text and len(text) > 5000:
                        text = summarize_text(text, quality=summary_quality)
                    if text:
                        user_message += "\nFile content:\n" + text[:10000]
                except Exception as e:
                    user_message += f"\n(Note: Could not extract file text: {e})"
            # Query the local model
            response_text = local_client.generate(text=user_message, system=SYSTEM_MESSAGE)
            content = response_text.strip()
        else:
            # OpenAI API path
            if long_text_summary_mode:
                # Already replaced user_message with summary content
                messages = [
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": user_message}
                ]
                response = openai.ChatCompletion.create(
                    model="gpt-4-0613",
                    messages=messages,
                    temperature=0.2,
                    max_tokens=1500
                )
                content = response.choices[0].message.content if response.choices else ""
            else:
                # Use function calling to let the model fetch URL or file content as needed
                messages = [
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": user_message}
                ]
                response = openai.ChatCompletion.create(
                    model="gpt-4-0613",
                    messages=messages,
                    functions=TOOLS,
                    function_call="auto",
                    temperature=0.2,
                    max_tokens=1500
                )
                # Handle a potential function call
                content = ""
                if response.choices:
                    msg = response.choices[0].message
                    if msg.get("function_call"):
                        # Model requested a tool function
                        func_name = msg["function_call"]["name"]
                        func_args = msg["function_call"].get("arguments", {})
                        try:
                            if func_name == "scrape_company_site":
                                args = json.loads(func_args) if isinstance(func_args, str) else func_args
                                result = scrape_company_site(**args)
                                function_output = json.dumps(result)
                            elif func_name == "extract_text_from_file":
                                args = json.loads(func_args) if isinstance(func_args, str) else func_args
                                file_content_b64 = args.get("file_content", "")
                                filename = args.get("filename", "")
                                file_data = base64.b64decode(file_content_b64) if file_content_b64 else b""
                                extracted = extract_text_from_file(file_data, filename)
                                function_output = extracted if isinstance(extracted, str) else str(extracted)
                            else:
                                function_output = ""
                        except Exception as tool_exc:
                            function_output = f"Function execution error: {tool_exc}"
                        # Include the function result and ask the model for final answer
                        messages.append({
                            "role": "function",
                            "name": func_name,
                            "content": function_output
                        })
                        second_resp = openai.ChatCompletion.create(
                            model="gpt-4-0613",
                            messages=messages,
                            temperature=0.2,
                            max_tokens=1500
                        )
                        content = second_resp.choices[0].message.content if second_resp.choices else ""
                    else:
                        # No function call, got direct answer
                        content = msg.get("content", "") or ""
                else:
                    content = ""
            content = content.strip() if content else ""
    except Exception as e:
        logging.error(f"LLM generation failed: {e}")
        return {}
    # If content is missing or not JSON, attempt a repair (OpenAI only)
    if not content or not content.startswith("{"):
        if USE_LOCAL_MODEL:
            return {}
        repair_prompt = "Your previous output was not valid JSON. Only output a valid JSON matching the JobSpec schema now."
        try:
            repair_response = openai.ChatCompletion.create(
                model="gpt-4-0613",
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": content},
                    {"role": "system", "content": repair_prompt}
                ],
                temperature=0.0,
                max_tokens=1200
            )
            content_fixed = repair_response.choices[0].message.content.strip() if repair_response.choices else ""
            content = content_fixed
        except Exception as e2:
            logging.error(f"JSON repair attempt failed: {e2}")
            return {}
    # Validate JSON content against JobSpec schema
    content_str = content.strip().strip("` ")
    if not content_str:
        return {}
    try:
        job_spec = JobSpec.model_validate_json(content_str)
    except Exception as schema_err:
        logging.warning(f"Validation of JSON failed: {schema_err}")
        return {}
    # Return as a plain dictionary
    return job_spec.model_dump()

def call_with_retry(func, *args, max_attempts: int = 3, **kwargs):
    """Call a function with retries on exception (simple retry utility)."""
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_attempts - 1:
                # Last attempt, re-raise exception
                raise
            time.sleep(1)  # wait a bit before retrying
