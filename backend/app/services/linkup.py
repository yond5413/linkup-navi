"""Linkup API client for web-based research."""

from typing import Optional
import httpx
from app.config import get_settings


class LinkupClient:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.linkup_api_key
        self.api_url = self.settings.linkup_api_url

    async def search(self, query: str) -> dict:
        if not self.api_key or self.api_key == "your_linkup_api_key_here":
            return self._mock_search(query)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/search",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"query": query, "num_results": 5},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_company_info(self, company_name: str) -> dict:
        if not self.api_key or self.api_key == "your_linkup_api_key_here":
            return self._mock_company_info(company_name)

        return await self.search(f"{company_name} company information news")

    def _mock_search(self, query: str) -> dict:
        return {
            "results": [
                {
                    "title": f"Mock result for: {query}",
                    "url": "https://example.com",
                    "snippet": f"This is a mock search result for '{query}'. Replace with real Linkup API key.",
                }
            ]
        }

    def _mock_company_info(self, company_name: str) -> dict:
        return {
            "company": company_name,
            "description": f"{company_name} is a fictional company used for demo purposes.",
            "recent_news": [
                {
                    "title": f"{company_name} announces new initiatives",
                    "date": "2025-01-15",
                    "summary": f"{company_name} has been making waves in the industry with recent developments.",
                }
            ],
            "note": "This is mock data. Set LINKUP_API_KEY in .env to use real Linkup API.",
        }


def create_linkup_client() -> LinkupClient:
    return LinkupClient()
