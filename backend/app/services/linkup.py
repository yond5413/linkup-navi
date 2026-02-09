"""Linkup API client for web-based research."""

from typing import Optional, Dict, Any
from linkup import LinkupClient as SDKClient
from app.config import get_settings


class LinkupClient:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.linkup_api_key
        # Note: linkup-sdk doesn't explicitly take an api_url in the constructor in the quickstart, 
        # but we'll use the API key if available.
        self.client = SDKClient(api_key=self.api_key) if self.api_key and self.api_key != "your_linkup_api_key_here" else None

    async def search(self, query: str) -> Dict[str, Any]:
        """Perform a deep search using Linkup SDK."""
        if not self.client:
            return self._mock_search(query)

        # linkup-sdk search is likely synchronous or based on requests/httpx
        # Based on docs: response = client.search(query=..., depth="deep", output_type="sourcedAnswer")
        try:
            # The SDK might be synchronous, we'll run it in a way that doesn't block if needed, 
            # but for now let's follow the standard pattern.
            response = self.client.search(
                query=query, 
                depth="deep", 
                output_type="sourcedAnswer"
            )
            # The response object from SDK needs to be converted to dict or accessed appropriately
            # Returning as dict for consistency with current code
            return {
                "answer": getattr(response, 'answer', ''),
                "sources": [
                    {
                        "name": getattr(s, 'name', ''),
                        "url": getattr(s, 'url', ''),
                        "snippet": getattr(s, 'snippet', ''),
                        "favicon": getattr(s, 'favicon', '')
                    } for s in getattr(response, 'sources', [])
                ]
            }
        except Exception as e:
            print(f"Linkup API Error: {e}")
            return self._mock_search(query)

    async def get_company_info(self, company_name: str) -> Dict[str, Any]:
        """Retrieve detailed company information."""
        return await self.search(f"Detailed company information, recent news, and key metrics for {company_name}")

    def _mock_search(self, query: str) -> Dict[str, Any]:
        """Fallback mock response mimicking the Linkup SDK structure."""
        return {
            "answer": f"This is a mock search result for '{query}'. To see real results, please configure a valid LINKUP_API_KEY.",
            "sources": [
                {
                    "name": "Linkup Documentation",
                    "url": "https://docs.linkup.so",
                    "snippet": f"Linkup provides high-quality web data for LLMs. This is a placeholder for {query}.",
                    "favicon": "https://linkup.so/favicon.ico"
                }
            ]
        }


def create_linkup_client() -> LinkupClient:
    return LinkupClient()
