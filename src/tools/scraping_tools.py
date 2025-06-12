# Optional decorator (works even without tool_registry)
try:
    from src.utils.tool_registry import tool
except (ImportError, ModuleNotFoundError):  # Fallback decorator
    def tool(_func=None, **_kwargs):  # type: ignore
        def decorator(func):
            return func
        return decorator if _func is None else decorator(_func)


@tool(
    name="scrape_company_site",
    description=(
        "Fetches <title> and meta description from a company homepage."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Company homepage URL"}
        },
        "required": ["url"]
    },
    return_type="object"
)
def scrape_company_site(url: str) -> dict:
    ...
