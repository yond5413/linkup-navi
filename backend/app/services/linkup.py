"""Linkup API client for web-based research."""

import asyncio
from typing import Optional, Dict, Any
from linkup import LinkupClient as SDKClient
from app.config import get_settings


class LinkupClient:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.linkup_api_key
        self.client = SDKClient(api_key=self.api_key) if self.api_key else None

    async def search(self, query: str) -> Dict[str, Any]:
        """Perform a deep search using Linkup SDK."""
        if not self.client:
            return self._mock_search(query)

        try:
            response = self.client.search(
                query=query, depth="deep", output_type="sourcedAnswer"
            )
            return {
                "answer": response.answer,
                "sources": [
                    {
                        "name": s.name,
                        "url": s.url,
                        "snippet": s.snippet,
                        "favicon": s.favicon,
                    }
                    for s in response.sources
                ],
            }
        except Exception as e:
            print(f"Linkup API Error: {e}")
            return self._mock_search(query)

    async def get_company_info(self, company_name: str) -> Dict[str, Any]:
        """Retrieve detailed company information."""
        return await self.search(
            f"Detailed company information, recent news, and key metrics for {company_name}"
        )

    def _mock_search(self, query: str) -> Dict[str, Any]:
        """Fallback mock response mimicking the Linkup SDK structure."""
        return {
            "answer": f"This is a mock search result for '{query}'. To see real results, please configure a valid LINKUP_API_KEY.",
            "sources": [
                {
                    "name": "Linkup Documentation",
                    "url": "https://docs.linkup.so",
                    "snippet": f"Linkup provides high-quality web data for LLMs. This is a placeholder for {query}.",
                    "favicon": "https://linkup.so/favicon.ico",
                }
            ],
        }


def create_linkup_client() -> LinkupClient:
    return LinkupClient()
