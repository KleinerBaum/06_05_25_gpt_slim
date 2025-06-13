# Optional decorator (works even without tool_registry)
try:
    from vacalyser.utils.tool_registry import tool
except (ImportError, ModuleNotFoundError):  # Fallback decorator

    def tool(_func=None, **_kwargs):  # type: ignore
        def decorator(func):
            return func

        return decorator if _func is None else decorator(_func)


@tool(
    name="scrape_company_site",
    description=("Fetches <title> and meta description from a company homepage."),
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Company homepage URL"}
        },
        "required": ["url"],
    },
    return_type="object",
)
def scrape_company_site(url: str) -> dict:
    """Return the title and meta description of the given URL."""
    import requests  # type: ignore
    from bs4 import BeautifulSoup

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception:
        return {}
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    descr_tag = soup.find("meta", attrs={"name": "description"})  # type: ignore[assignment]
    description = (
        descr_tag["content"].strip() if descr_tag and descr_tag.get("content") else ""
    )
    return {"title": title, "description": description}
