import re
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Entity:
    name: str
    context: str
    significance: float
    source_file: Optional[str] = None


class EntityExtractor:
    """Extract and score entities from text using pattern matching + LLM fallback."""

    PATTERNS = [
        r"\b([A-Za-z][a-zA-Z]*(?:\s+[A-Za-z][a-zA-Z]*)*)\s+(Corp|Inc|LLC|Ltd|Company|Co\.?|Group|Holdings|Partners)\b",
    ]

    HIGH_VALUE = [
        "$",
        "million",
        "billion",
        "funding",
        "raised",
        "series",
        "investment",
        "acquired",
        "ipo",
    ]
    MEDIUM_VALUE = [
        "risk",
        "threat",
        "competitive",
        "launch",
        "announced",
        "partnership",
        "product",
        "platform",
    ]

    QUERY_GENERATION_PROMPT = """You are a query generation expert. Given an entity and its context, generate 2-4 highly specific search queries that will retrieve accurate, up-to-date information about this entity.

Entity: {name}
Context: {context}

Instructions:
1. Generate queries that focus on the most important aspects mentioned in the context
2. Include the current year ({year}) in each query for freshness
3. Make queries specific enough to find relevant information but general enough to get broad results
4. If context is empty or vague, generate queries about recent news and company updates

Return ONLY a JSON array of strings (queries), no other text.
Example format: ["query 1", "query 2", "query 3"]"""

    def __init__(self):
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]

    async def extract(
        self, text: str, source_file: Optional[str] = None
    ) -> List[Entity]:
        """Extract entities with context and significance."""
        entities = self._extract_by_pattern(text, source_file)

        if not entities:
            entities = await self._extract_by_llm(text, source_file)

        return sorted(entities, key=lambda x: x.significance, reverse=True)

    def _extract_by_pattern(
        self, text: str, source_file: Optional[str] = None
    ) -> List[Entity]:
        """Extract entities using regex patterns."""
        entities = []

        for pattern in self._compiled_patterns:
            for match in pattern.finditer(text):
                full_match = match.group(0)
                name = self._normalize_name(full_match)
                start = max(0, match.start() - 150)
                end = min(len(text), match.end() + 150)
                context = text[start:end].strip()

                significance = self._score(context)

                entities.append(
                    Entity(
                        name=name,
                        context=context,
                        significance=significance,
                        source_file=source_file,
                    )
                )

        return self._deduplicate(entities)

    async def _extract_by_llm(
        self, text: str, source_file: Optional[str] = None
    ) -> List[Entity]:
        """Fallback: Use LLM to extract companies when patterns fail."""
        from app.services.llm import LLMClient

        llm = LLMClient()
        prompt = f"""Extract company names from the following text. 
Return a JSON array of objects with 'name' and 'context' fields.
Focus on companies mentioned with significant events (funding, acquisition, product launches, partnerships).

Text:
{text[:3000]}

Respond with JSON array only. Example: [{{"name": "Company Name", "context": "relevant context"}}]"""

        try:
            response = llm.generate(
                prompt, system="You extract company names from text."
            )
            entities = []

            try:
                companies = json.loads(response)
                for c in companies:
                    entities.append(
                        Entity(
                            name=self._normalize_name(c.get("name", "")),
                            context=c.get("context", "")[:300],
                            significance=self._score(c.get("context", "")),
                            source_file=source_file,
                        )
                    )
            except json.JSONDecodeError:
                pass

            return entities
        except Exception:
            return []

    def _normalize_name(self, name: str) -> str:
        """Normalize company name to title case."""
        words = name.split()
        result = []
        acronyms = {"llc", "llp", "lp", "co"}
        for word in words:
            if word.lower() in acronyms:
                result.append(word.upper())
            else:
                result.append(word.capitalize())
        return " ".join(result)

    def _deduplicate(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicates, keeping highest significance."""
        seen = {}
        for e in entities:
            if e.name not in seen or e.significance > seen[e.name].significance:
                seen[e.name] = e
        return list(seen.values())

    def _score(self, context: str) -> float:
        """Score 0-1 based on importance."""
        score = 0.0
        context_lower = context.lower()

        high_matches = sum(1 for kw in self.HIGH_VALUE if kw in context_lower)
        score += min(high_matches * 0.3, 0.6)

        medium_matches = sum(1 for kw in self.MEDIUM_VALUE if kw in context_lower)
        score += min(medium_matches * 0.15, 0.3)

        if re.search(
            r"2024|2025|january|february|march|april|may|june|july|august|september|october|november|december",
            context_lower,
        ):
            score += 0.1

        return min(score, 1.0)

    async def generate_queries(self, entity: Entity, max_queries: int = 4) -> List[str]:
        """Generate specific search queries using LLM-first approach."""
        year = datetime.now().year

        prompt = self.QUERY_GENERATION_PROMPT.format(
            name=entity.name, context=entity.context, year=year
        )

        try:
            from app.services.llm import LLMClient

            llm = LLMClient()
            response = llm.generate(
                prompt, system="You generate search queries for entity research."
            )

            queries = self._parse_queries_response(response)
            if queries:
                return queries[:max_queries]
        except Exception:
            pass

        return self._generate_fallback_queries(entity, max_queries)

    def _parse_queries_response(self, response: str) -> List[str]:
        """Parse LLM response into list of queries."""
        try:
            queries = json.loads(response)
            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                return queries
        except json.JSONDecodeError:
            pass

        try:
            match = re.search(r"\[[\s\S]*\]", response)
            if match:
                queries = json.loads(match.group())
                if isinstance(queries, list) and all(
                    isinstance(q, str) for q in queries
                ):
                    return queries
        except json.JSONDecodeError:
            pass

        return []

    def _generate_fallback_queries(self, entity: Entity, max_queries: int) -> List[str]:
        """Rule-based fallback when LLM fails."""
        name = entity.name
        context = entity.context.lower()
        year = datetime.now().year
        queries = []

        queries.append(f"{name} recent news {year}")

        if any(kw in context for kw in ["acquired", "acquisition", "acquiring"]):
            queries.append(f"{name} acquisition buyer {year}")
        if any(kw in context for kw in ["ipo", "went public", "public"]):
            queries.append(f"{name} IPO stock valuation {year}")
        if any(kw in context for kw in ["partnership", "partner", "collaboration"]):
            queries.append(f"{name} partnership collaboration {year}")
        if any(kw in context for kw in ["product", "platform", "launch"]):
            queries.append(f"{name} product launch features {year}")
        if any(kw in context for kw in ["funding", "raised", "series", "investment"]):
            queries.append(f"{name} funding investment {year}")

        if not queries:
            queries.append(f"{name} company news updates {year}")

        return queries[:max_queries]

    def get_top_entities(self, entities: List[Entity], limit: int = 3) -> List[Entity]:
        """Get top entities by significance."""
        return sorted(entities, key=lambda x: x.significance, reverse=True)[:limit]
