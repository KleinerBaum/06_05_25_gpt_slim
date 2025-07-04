from __future__ import annotations
import asyncio
import json
import logging
import os
from typing import Any, Dict, cast

from logic.search_helpers import run_file_search
from services.external_data import fetch_external_insight

import openai  # type: ignore
from utils import config

try:
    from agents import Agent, Runner, function_tool
except Exception:  # pragma: no cover - optional dependency
    Agent = Runner = function_tool = None  # type: ignore

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
FUNCTION_DEFS: list[dict] = [
    {
        "name": "extract_text_from_file",
        "description": "Extracts raw or structured text from an uploaded document (PDF, DOCX, TXT).",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "Upload ID returned by file_tools",
                },
                "file_type": {"type": "string", "enum": ["pdf", "docx", "txt"]},
                "page_range": {
                    "type": "string",
                    "description": "Optional page selection, e.g. '1-3,5'",
                },
                "return_format": {
                    "type": "string",
                    "enum": ["plain", "markdown", "html"],
                    "default": "plain",
                },
            },
            "required": ["file_id", "file_type"],
        },
    },
    {
        "name": "scrape_company_site",
        "description": "Crawls a given company URL and returns meta-information such as mission, products, locations, head-count.",
        "parameters": {
            "type": "object",
            "properties": {
                "company_url": {"type": "string", "format": "uri"},
                "max_depth": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 3,
                    "default": 1,
                },
                "include_html": {"type": "boolean", "default": False},
            },
            "required": ["company_url"],
        },
    },
    {
        "name": "retrieve_esco_skills",
        "description": "Returns ESCO-standardised skills for a given job title or free-text description.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_title": {"type": "string"},
                "description": {
                    "type": "string",
                    "description": "Optional extra context",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 15,
                },
                "language": {"type": "string", "default": "en"},
            },
            "required": ["job_title"],
        },
    },
    {
        "name": "update_salary_range",
        "description": "Estimates a competitive salary range based on role, location and seniority.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_title": {"type": "string"},
                "location": {"type": "string"},
                "seniority": {
                    "type": "string",
                    "enum": ["junior", "mid", "senior", "lead"],
                },
                "currency": {"type": "string", "default": "EUR"},
                "spread_pct": {
                    "type": "number",
                    "description": "Desired ±% spread around midpoint",
                    "default": 10,
                },
            },
            "required": ["job_title", "location"],
        },
    },
    {
        "name": "interview_prep_generator",
        "description": "Creates tailored interview questions & scorecard rubrics from a JobSpec object.",
        "parameters": {
            "type": "object",
            "properties": {
                "job_spec": {
                    "type": "string",
                    "description": "Full job specification JSON/text",
                },
                "num_questions": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "default": 10,
                },
                "language": {"type": "string", "default": "de"},
            },
            "required": ["job_spec"],
        },
    },
    {
        "name": "vector_search_candidates",
        "description": "Searches the vector store for best-matching candidate profiles.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-text query (role & skills)",
                },
                "top_k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
                "vector_store_id": {
                    "type": "string",
                    "const": "vs_67e40071e7608191a62ab06cacdcdd10",
                    "description": "ID of the Vacalyser vector store",
                },
            },
            "required": ["query"],
        },
    },
]

# System-Rollen-Nachricht für den Assistant
SYSTEM_MESSAGE = (
    "You are Vacalyser, an AI assistant for recruiters. "
    "Your job is to extract detailed, structured job vacancy information from input text (job ads) or websites. "
    "Return the information as JSON that matches the schema of the JobSpec model, with no extra commentary."
)

# Optional: Agent-based execution using the OpenAI Agents SDK
USE_AGENTS_SDK = os.getenv("USE_AGENTS_SDK", "0") == "1"
# Use the Assistants/Responses API with built-in tools if enabled
USE_ASSISTANTS_API = os.getenv("USE_ASSISTANTS_API", "0") == "1"

if Agent is not None:

    @function_tool
    def _agent_scrape_company_site(
        company_url: str, max_depth: int = 1, include_html: bool = False
    ) -> str:
        from services.scraping_tools import scrape_company_site

        data = scrape_company_site(
            company_url, max_depth=max_depth, include_html=include_html
        )
        if isinstance(data, dict):
            return (
                (data.get("title") or "") + "\n" + (data.get("description") or "")
            ).strip()
        return str(data)

    @function_tool
    def _agent_extract_text_from_file(file_content: bytes, filename: str) -> str:
        from logic.file_tools import extract_text_from_file

        return extract_text_from_file(file_content, filename)

    @function_tool
    def _agent_retrieve_esco_skills(
        job_title: str,
        description: str | None = None,
        max_results: int = 15,
        language: str = "en",
    ) -> list[str]:
        from services.new_tools import retrieve_esco_skills

        return retrieve_esco_skills(job_title, description, max_results, language)

    @function_tool
    def _agent_update_salary_range(
        job_title: str,
        location: str,
        seniority: str | None = None,
        currency: str = "EUR",
        spread_pct: float = 10,
    ) -> str:
        from services.new_tools import update_salary_range

        return update_salary_range(job_title, location, seniority, currency, spread_pct)

    @function_tool
    def _agent_interview_prep_generator(
        job_spec: str, num_questions: int = 10, language: str = "de"
    ) -> list[str]:
        from services.new_tools import interview_prep_generator

        return interview_prep_generator(job_spec, num_questions, language)

    @function_tool
    def _agent_vector_search_candidates(
        query: str, top_k: int = 5, vector_store_id: str | None = None
    ) -> list[str]:
        from services.new_tools import vector_search_candidates

        return vector_search_candidates(query, top_k, vector_store_id)


async def _assistants_completion(user_message: str) -> str:
    """Run a prompt via the Assistants API with built-in tools.

    Args:
        user_message: Chat message from the caller.

    Returns:
        Assistant response text, or an empty string on failure.
    """
    try:
        assistant = openai.beta.assistants.create(  # type: ignore[arg-type]
            name="Vacalyser",
            model=config.OPENAI_MODEL,
            instructions=SYSTEM_MESSAGE,
            tools=[{"type": "retrieval"}, {"type": "code_interpreter"}],  # type: ignore[arg-type,list-item,misc]
        )
        thread = openai.beta.threads.create()
        openai.beta.threads.messages.create(
            thread.id, role="user", content=user_message
        )
        run = openai.beta.threads.runs.create(thread.id, assistant_id=assistant.id)
        while run.status not in {"completed", "failed", "cancelled"}:
            await asyncio.sleep(0.5)
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread.id, run_id=run.id
            )  # type: ignore[call-arg]
        if run.status != "completed":
            logger.error("Assistants run failed: %s", run.status)
            return ""
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        return messages.data[-1].content[0].text.value  # type: ignore[attr-defined,union-attr]
    except Exception as api_error:  # pragma: no cover - network errors
        logger.error(f"Assistants API error: {api_error}")
        return ""


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

    # Füge Kontext aus Datei- oder Websuche hinzu
    search_context = ""
    if file_bytes and file_name:
        try:
            results = run_file_search([file_name])
            snippets = results.get("skill_extraction", [])
            if snippets:
                search_context = "\n".join(str(s) for s in snippets[:3])
        except Exception as err:  # pragma: no cover - network errors
            logger.error("File search failed: %s", err)
    elif input_url:
        try:
            web_data = fetch_external_insight("branchentrends")
            if web_data:
                search_context = "\n".join(str(r) for r in web_data[:3])
        except Exception as err:  # pragma: no cover - network errors
            logger.error("Web search failed: %s", err)

    if search_context:
        user_message += f"\nAdditional context:\n{search_context}"

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

    # OpenAI API mit Function Calling oder optional Agents SDK
    content = ""
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": user_message},
    ]
    if USE_AGENTS_SDK and Agent is not None:
        agent_tools = [
            _agent_scrape_company_site,
            _agent_extract_text_from_file,
            _agent_retrieve_esco_skills,
            _agent_update_salary_range,
            _agent_interview_prep_generator,
            _agent_vector_search_candidates,
        ]
        agent = Agent(name="Vacalyser", instructions=SYSTEM_MESSAGE, tools=agent_tools)
        try:
            run_result = asyncio.run(Runner.run(agent, input=user_message))
            content = run_result.final_output or ""
        except Exception as api_error:  # pragma: no cover - network errors
            logger.error(f"Agents SDK Fehler in auto_fill_job_spec: {api_error}")
            return {}
        first_message = None
    elif USE_ASSISTANTS_API:
        content = asyncio.run(_assistants_completion(user_message))
        first_message = None
    else:
        try:
            response = openai.chat.completions.create(  # type: ignore
                model=config.OPENAI_MODEL,
                messages=messages,
                functions=FUNCTION_DEFS,
                function_call="auto",
                temperature=0.2,
                max_tokens=1500,
            )
        except Exception as api_error:
            logger.error(f"OpenAI API Fehler in auto_fill_job_spec: {api_error}")
            return {}
        first_message = response.choices[0].message
    if (
        first_message is not None
        and hasattr(first_message, "function_call")
        and first_message.function_call
    ):
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
            elif func_name == "retrieve_esco_skills":
                from services.new_tools import retrieve_esco_skills

                func_res = retrieve_esco_skills(**func_args)
                func_result = json.dumps(func_res)
            elif func_name == "update_salary_range":
                from services.new_tools import update_salary_range

                func_result = update_salary_range(**func_args)
            elif func_name == "interview_prep_generator":
                from services.new_tools import interview_prep_generator

                func_result = json.dumps(interview_prep_generator(**func_args))
            elif func_name == "vector_search_candidates":
                from services.new_tools import vector_search_candidates

                func_result = json.dumps(vector_search_candidates(**func_args))
        except Exception as e:
            logger.error(f"Fehler bei Tool-Ausführung {func_name}: {e}")
        # Ergebnis der Funktion als Assistant-Antwort hinzufügen und zweiten API-Call durchführen
        messages.append({"role": "function", "name": func_name, "content": func_result})
        try:
            second_response = openai.chat.completions.create(  # type: ignore
                model=config.OPENAI_MODEL,
                messages=messages,
                functions=FUNCTION_DEFS,
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
        if first_message is not None:
            content = first_message.content or ""
    if not content:
        return {}

    # 'content' sollte nun den JSON-String entsprechend JobSpec enthalten
    content_str = content.strip()
    if content_str.startswith("```") and content_str.endswith("```"):
        # remove surrounding code fences and optional language hints
        content_str = content_str[3:-3].strip()
        if content_str.lower().startswith("json"):
            content_str = content_str[4:].strip()
    elif content_str.startswith("```"):
        content_str = content_str.strip("` \n")
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
