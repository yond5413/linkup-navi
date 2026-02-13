import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.entity_extractor import EntityExtractor, Entity


class TestEntityExtraction:
    def test_extract_acme_from_roadmap(self):
        text = """
        Q4 2024 Roadmap
        
        Key concern: Acme Corp's $50M Series B and AI platform launch (March         creates first-m2024) 
over advantage risk. Our differentiation: enterprise focus 
        vs their SMB play.
        """

        extractor = EntityExtractor()
        entities = extractor._extract_by_pattern(text)

        assert len(entities) >= 1
        acme = next((e for e in entities if "Acme" in e.name), None)
        assert acme is not None
        assert acme.significance > 0.7
        assert "Series B" in acme.context

    def test_extract_multiple_companies(self):
        text = """
        Competitive landscape: Acme Corp raised $50M, Beta Inc was acquired,
        and Gamma LLC announced IPO.
        """

        extractor = EntityExtractor()
        entities = extractor._extract_by_pattern(text)

        names = [e.name for e in entities]
        assert any("Acme" in n for n in names)
        assert any("Beta" in n for n in names)
        assert any("Gamma" in n for n in names)

    def test_case_insensitive_extraction(self):
        text = "acme corp raised $50M series B funding"

        extractor = EntityExtractor()
        entities = extractor._extract_by_pattern(text)

        assert len(entities) >= 1
        assert entities[0].name == "Acme Corp"

    def test_normalize_name_to_title_case(self):
        extractor = EntityExtractor()

        assert extractor._normalize_name("acme corp") == "Acme Corp"
        assert extractor._normalize_name("ACME INC") == "Acme Inc"
        assert extractor._normalize_name("beta llc") == "Beta LLC"

    @pytest.mark.asyncio
    async def test_generate_funding_query(self):
        entity = Entity(
            name="Acme Corp",
            context="Acme Corp's $50M Series B creates risk",
            significance=0.9,
        )

        extractor = EntityExtractor()
        queries = await extractor.generate_queries(entity, max_queries=2)

        assert len(queries) <= 2
        assert any("Acme Corp" in q for q in queries)

    @pytest.mark.asyncio
    async def test_generate_acquisition_query(self):
        entity = Entity(
            name="Beta Inc",
            context="Beta Inc was acquired by TechGiant",
            significance=0.8,
        )

        extractor = EntityExtractor()
        queries = await extractor.generate_queries(entity)

        assert any(
            "acquisition" in q.lower() or "acquired" in q.lower() or "Beta Inc" in q
            for q in queries
        )

    @pytest.mark.asyncio
    async def test_generate_launch_query(self):
        entity = Entity(
            name="Gamma LLC",
            context="Gamma LLC announced new product platform launch",
            significance=0.6,
        )

        extractor = EntityExtractor()
        queries = await extractor.generate_queries(entity)

        assert len(queries) >= 1

    def test_significance_scoring_high(self):
        extractor = EntityExtractor()

        high = "Acme Corp raised $50M Series B funding"
        high_score = extractor._score(high)

        assert high_score > 0.5

    def test_significance_scoring_low(self):
        extractor = EntityExtractor()

        low = "Acme Corp is a company"
        low_score = extractor._score(low)

        assert low_score < 0.3

    def test_significance_scoring_comparison(self):
        extractor = EntityExtractor()

        high = "Acme Corp raised $50M Series B funding"
        low = "Acme Corp is a company"

        high_score = extractor._score(high)
        low_score = extractor._score(low)

        assert high_score > low_score
        assert high_score > 0.5

    def test_limit_top_3_entities(self):
        text = """
        Alpha Corp funding. Beta Inc IPO. Gamma LLC launch. 
        Delta Corp acquisition. Epsilon Inc partnership.
        """

        extractor = EntityExtractor()
        entities = extractor._extract_by_pattern(text)

        assert len(entities) >= 5

        top_3 = extractor.get_top_entities(entities, limit=3)
        assert len(top_3) == 3

    def test_deduplicate_entities(self):
        text = """
        Acme Corp is a leader. Acme Corp raised $50M.
        """

        extractor = EntityExtractor()
        entities = extractor._extract_by_pattern(text)

        names = [e.name for e in entities]
        assert names.count("Acme Corp") == 1

    def test_recency_bonus(self):
        extractor = EntityExtractor()

        with_year = "Acme Corp funding 2024"
        without_year = "Acme Corp funding"

        with_year_score = extractor._score(with_year)
        without_year_score = extractor._score(without_year)

        assert with_year_score > without_year_score

    def test_empty_text(self):
        extractor = EntityExtractor()
        entities = extractor._extract_by_pattern("")

        assert len(entities) == 0


class TestEntityIntegration:
    @pytest.mark.asyncio
    async def test_llm_fallback_when_no_patterns(self):
        text = "The startup called QuantumAI raised significant funding"

        extractor = EntityExtractor()
        entities = await extractor.extract(text)

        assert len(entities) >= 1

    @pytest.mark.asyncio
    async def test_extract_returns_sorted_by_significance(self):
        text = """
        Acme Corp raised $50M. Beta Inc is a small company. 
        Gamma LLC had a major $100M acquisition.
        """

        extractor = EntityExtractor()
        entities = await extractor.extract(text)

        if len(entities) >= 2:
            for i in range(len(entities) - 1):
                assert entities[i].significance >= entities[i + 1].significance
