import re
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

            import json

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

    def generate_queries(self, entity: Entity, max_queries: int = 2) -> List[str]:
        """Generate specific search queries."""
        name = entity.name
        context = entity.context.lower()
        queries = []

        queries.append(f"{name} recent news 2024")

        if "acquired" in context or "acquisition" in context:
            queries.append(f"{name} acquisition buyer 2024")
        elif "ipo" in context:
            queries.append(f"{name} IPO stock valuation 2024")
        elif "partnership" in context or "partner" in context:
            queries.append(f"{name} partnership collaboration 2024")
        elif "product" in context or "platform" in context or "launch" in context:
            queries.append(f"{name} product launch features 2024")
        elif any(
            kw in context
            for kw in ["funding", "raised", "series", "$", "million", "billion"]
        ):
            queries.append(f"{name} funding Series investment 2024")
        else:
            queries.append(f"{name} company news updates 2024")

        return queries[:max_queries]

    def get_top_entities(self, entities: List[Entity], limit: int = 3) -> List[Entity]:
        """Get top entities by significance."""
        return sorted(entities, key=lambda x: x.significance, reverse=True)[:limit]
