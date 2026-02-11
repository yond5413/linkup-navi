from .base import ToolResult, ToolContext
from .registry import tool


@tool(description="Search web via Linkup API")
async def linkup_search(query: str, session_id: str) -> dict:
    from app.services.linkup import LinkupClient

    client = LinkupClient()
    results = await client.search(query)
    return {"results": results}


@tool(description="Get company info via Linkup")
async def get_company_info(company_name: str, session_id: str) -> dict:
    from app.services.linkup import LinkupClient

    client = LinkupClient()
    info = await client.get_company_info(company_name)
    return info


@tool(description="Search and format web research")
async def web_research(query: str, session_id: str) -> dict:
    results = await linkup_search(query, session_id)
    return {
        "query": query,
        "answer": results.get("results", []),
        "source_count": len(results.get("results", [])),
    }
