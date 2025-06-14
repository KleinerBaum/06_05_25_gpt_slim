from __future__ import annotations
import json
import logging
from typing import Any, Dict, cast

import openai  # type: ignore
from utils import config

openai = cast(Any, openai)

# Logger konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default prompt for skills extraction used by llm_utils.get_role_skills
SKILLS_ASSISTANT_PROMPT = (
    "You are an expert career advisor. The user will provide a job title. "
    "List the top {num_skills} must-have skills (technical skills and core competencies) "
    "that an ideal candidate for the '{job_title}' role should possess. "
    "Provide the list as bullet points or a comma-separated list, without any additional commentary."
)


# Funktionen (Tools) für OpenAI Function Calling definieren
FUNCTIONS = [
    {
        "name": "scrape_company_site",
        "description": "Fetch basic company info (title and meta description) from a company website.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the company homepage.",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "extract_text_from_file",
        "description": "Extract readable text from an uploaded job-ad file (PDF, DOCX, or TXT).",
        "parameters": {
            "type": "object",
            "properties": {
                "file_content": {
                    "type": "string",
                    "description": "Base64-encoded file content.",
                },
                "filename": {
                    "type": "string",
                    "description": "Original filename with extension.",
                },
            },
            "required": ["file_content", "filename"],
        },
    },
]

# System-Rollen-Nachricht für den Assistant
SYSTEM_MESSAGE = (
    "You are Vacalyser, an AI assistant for recruiters. "
    "Your job is to extract detailed, structured job vacancy information from input text (job ads) or websites. "
    "Return the information as JSON that matches the schema of the JobSpec model, with no extra commentary."
)


def auto_fill_job_spec(
    input_url: str = "",
    file_bytes: bytes | None = None,
    file_name: str = "",
    summary_quality: str = "standard",
) -> Dict[str, Any]:
    """Analyse a job ad from URL or file and return parsed fields.

    Args:
        input_url: Optional URL to the job advertisement.
        file_bytes: Raw bytes of an uploaded job-ad file.
        file_name: File name of the uploaded document.
        summary_quality: Level of summarization for long documents.

    Returns:
        Dictionary matching the ``JobSpec`` schema with extracted values.
    """
    # Eingabe validieren
    if not input_url and not file_bytes:
        raise ValueError(
            "auto_fill_job_spec erfordert entweder eine URL oder eine Datei als Eingabe."
        )
    if input_url and file_bytes:
        # Bei beiden Eingaben: URL priorisieren, Datei ignorieren
        file_bytes = None
        file_name = ""

    # Nutzeranweisung (Prompt) für das LLM vorbereiten
    user_message = ""
    if input_url:
        user_message += f"The job ad is located at this URL: {input_url}\n"
    if file_bytes:
        user_message += (
            "A job ad file is provided. Please analyze its contents carefully.\n"
        )
    user_message += "Extract all relevant job information and return it in JSON format matching the JobSpec schema."

    # Falls der Dateitext sehr lang ist: vorab zusammenfassen, um Tokens zu sparen
    if file_bytes and file_name:
        try:
            text_length = len(file_bytes)
        except Exception:
            text_length = 0
        if text_length > 100_000:  # ~100 KB
            from logic.file_tools import extract_text_from_file
            from utils.summarize import summarize_text

            extracted_text = extract_text_from_file(file_bytes, file_name)
            if isinstance(extracted_text, str) and len(extracted_text) > 5000:
                summary = summarize_text(extracted_text, quality=summary_quality)
                # Anweisung an Assistant zur Verwendung der Zusammenfassung anpassen
                user_message = (
                    "The job ad text was summarized due to length. "
                    "Please extract job info from the following summary:\n"
                    f"{summary}\nReturn the info as JSON per JobSpec."
                )

    # OpenAI API mit Function Calling
    content = ""
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": user_message},
    ]
    try:
        response = openai.chat.completions.create(  # type: ignore
            model=config.OPENAI_MODEL,
            messages=messages,
            functions=FUNCTIONS,
            function_call="auto",
            temperature=0.2,
            max_tokens=1500,
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
                from services.scraping_tools import scrape_company_site

                result_data = scrape_company_site(**func_args)
                if isinstance(result_data, dict):
                    func_result = (
                        (result_data.get("title") or "")
                        + "\n"
                        + (result_data.get("description") or "")
                    ).strip()
                else:
                    func_result = str(result_data)
            elif func_name == "extract_text_from_file":
                from logic.file_tools import extract_text_from_file
                import base64

                # Prefer bytes provided to ``auto_fill_job_spec``
                file_bytes_input = file_bytes or b""
                filename_input = file_name or ""

                if not file_bytes_input:
                    file_content_str = func_args.get("file_content", "")
                    try:
                        file_bytes_input = base64.b64decode(file_content_str)
                    except Exception:
                        file_bytes_input = file_content_str.encode("utf-8", "ignore")

                if not filename_input:
                    filename_input = func_args.get("filename", "")

                func_result = (
                    extract_text_from_file(file_bytes_input, filename_input) or ""
                )
                if not isinstance(func_result, str):
                    func_result = str(func_result)
        except Exception as e:
            logger.error(f"Fehler bei Tool-Ausführung {func_name}: {e}")
        # Ergebnis der Funktion als Assistant-Antwort hinzufügen und zweiten API-Call durchführen
        messages.append({"role": "function", "name": func_name, "content": func_result})
        try:
            second_response = openai.chat.completions.create(  # type: ignore
                model=config.OPENAI_MODEL,
                messages=messages,
                functions=FUNCTIONS,
                function_call="auto",
                temperature=0.2,
                max_tokens=1500,
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
        from models.job_models import JobSpec

        job_spec = JobSpec.model_validate_json(content_str)
    except Exception as e:
        logger.error(f"Assistant lieferte kein gültiges JSON. Fehler: {e}")
        # Versuchen, das LLM sein Format korrigieren zu lassen
        repair_system_msg = "Your previous output was not valid JSON. Only output a valid JSON matching JobSpec now."
        try:
            repair_resp = openai.chat.completions.create(  # type: ignore
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": content_str},
                    {"role": "system", "content": repair_system_msg},
                ],
                temperature=0,
                max_tokens=1200,
            )
            content_str = (repair_resp.choices[0].message.content or "").strip()
            job_spec = JobSpec.model_validate_json(content_str)
        except Exception as e:
            logger.error(f"Reparaturversuch fehlgeschlagen: {e}")
            return {}
    # Als Python-Dictionary zurückgeben
    return job_spec.model_dump()


def fix_json_output(raw_json: str) -> dict:
    """Attempt to repair a JSON string so it validates as ``JobSpec``.

    Args:
        raw_json: JSON string returned by the LLM.

    Returns:
        Parsed dictionary if successful, otherwise an empty dict.
    """
    from models.job_models import JobSpec

    try:
        return JobSpec.model_validate_json(raw_json).model_dump()
    except Exception:
        repair_prompt = (
            "Fix the following JSON so it matches the JobSpec schema and is valid:"
            "\n" + raw_json
        )
        try:
            resp = openai.chat.completions.create(  # type: ignore
                model=config.OPENAI_MODEL,
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0,
                max_tokens=1200,
            )
            content = (resp.choices[0].message.content or "").strip()
            return JobSpec.model_validate_json(content).model_dump()
        except Exception as err:
            logger.error(f"JSON repair failed: {err}")
            return {}
