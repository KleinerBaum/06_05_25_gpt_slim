"""File and web search helpers for trigger engine tasks."""

from __future__ import annotations

from typing import Any, Dict, List

from ace_tools import file_search  # type: ignore

USE_CASE_QUERIES: Dict[str, List[str]] = {
    "label_matching": ["Requirements:", "Responsibilities:", "Benefits:"],
    "skill_extraction": ["python OR aws OR kubernetes OR 'machine learning'"],
    "benefit_check": ["vacation OR pto OR insurance OR 'flexible hours'"],
    "contact_infos": ["@ OR phone OR Tel."],
    "compliance_passages": ["§ OR GDPR OR 'Equal Opportunity' OR 'M/F/D'"],
    "format_validation": ["Job Title OR Employment Type OR Location"],
    "versioning_diff": ["### REVISION"],
    "template_bank": ["Template-ID OR Layout-Guideline"],
    "reuse_phrases": ["'We are looking for'"],
    "qa_sampling": ["TODO OR TBA OR 'lorem ipsum'"],
}


def run_file_search(doc_ids: List[str]) -> Dict[str, List[Any]]:
    """Run predefined semantic searches against uploaded documents.

    Parameters
    ----------
    doc_ids:
        List of document IDs returned by the upload step.

    Returns
    -------
    dict[str, list]
        Dictionary mapping use-case tags to matched text chunks.
    """

    results: Dict[str, List[Any]] = {}

    for tag, queries in USE_CASE_QUERIES.items():
        query_list = [{"queries": [q]} for q in queries]
        chunk_hits: List[Any] = []
        for q in query_list:
            out = file_search.msearch(q)
            chunk_hits.extend(out.get("results", []))
        results[tag] = chunk_hits
    return results
