from langchain.tools import tool

@tool(
    name="scrape_company_site",
    description="Fetches <title> and meta description from a company homepage.",
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
