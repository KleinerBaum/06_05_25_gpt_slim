"""Helpers to fetch external insights via web search."""

from __future__ import annotations

from typing import List

from ace_tools import web  # type: ignore

WEB_TOPICS = {
    "gehaltbenchmarks": "average salary data Germany 2024 by job title",
    "branchentrends": "latest industry trends AI/IT hiring 2024",
    "regionale_arbeitsmarkt": "labour market statistics Bavaria software engineers 2024",
    "konkurrenz_analyse": "competitor job ads Data Engineer Berlin 2024",
    "seo_keywords": "most searched job keywords 'data scientist' Germany",
}


def fetch_external_insight(
    topic: str, recency_days: int = 30, domains: List[str] | None = None
) -> List:
    """Return top web search results for a given topic.

    Parameters
    ----------
    topic:
        Keyword defined in ``WEB_TOPICS``.
    recency_days:
        Optional freshness filter in days.
    domains:
        Optional list of domains to restrict the search.

    Returns
    -------
    list
        Search results as returned by ``ace_tools.web.run``.
    """

    if topic not in WEB_TOPICS:
        raise ValueError("unknown topic")
    query = {
        "search_query": [
            {"q": WEB_TOPICS[topic], "recency": recency_days, "domains": domains}
        ],
        "response_length": "short",
    }
    return web.run(query)["results"]
