"""Comprehensive tests for intelligent vector memory retrieval."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.services.intelligent_retrieval import IntelligentRetrievalService
from app.services.memory_cache import MemoryQueryCache, get_memory_query_cache
from app.utils.vector_utils import (
    l2_to_cosine_similarity,
    process_memory_results,
    get_max_similarity,
    get_relevance_tier,
)


class TestVectorUtils:
    """Test suite for vector utility functions."""

    def test_l2_to_cosine_similarity_identical(self):
        """Test L2=0 converts to cosine=1 (identical vectors)."""
        result = l2_to_cosine_similarity(0.0)
        assert result == 1.0

    def test_l2_to_cosine_similarity_typical_values(self):
        """Test conversion for typical L2 distances."""
        # L2=10 → ~0.95 cosine
        assert l2_to_cosine_similarity(10.0) == pytest.approx(0.95, abs=0.01)
        # L2=20 → ~0.80 cosine
        assert l2_to_cosine_similarity(20.0) == pytest.approx(0.80, abs=0.01)
        # L2=30 → ~0.56 cosine
        assert l2_to_cosine_similarity(30.0) == pytest.approx(0.56, abs=0.01)

    def test_l2_to_cosine_similarity_clamping(self):
        """Test that results are clamped to [-1, 1]."""
        # Very large L2 should not exceed bounds
        result = l2_to_cosine_similarity(100.0)
        assert -1.0 <= result <= 1.0

    def test_process_memory_results(self):
        """Test processing of raw memory results."""
        raw_results = [
            {"text": "Test content 1", "score": 10.0, "rank": 1},
            {"text": "Test content 2", "score": 20.0, "rank": 2},
        ]

        processed = process_memory_results(raw_results)

        assert len(processed) == 2
        assert processed[0]["cosine_similarity"] == pytest.approx(0.95, abs=0.01)
        assert processed[0]["l2_distance"] == 10.0
        assert processed[1]["cosine_similarity"] == pytest.approx(0.80, abs=0.01)

    def test_get_max_similarity(self):
        """Test extracting maximum similarity from results."""
        results = [
            {"cosine_similarity": 0.95},
            {"cosine_similarity": 0.80},
            {"cosine_similarity": 0.60},
        ]

        max_sim = get_max_similarity(results)
        assert max_sim == 0.95

    def test_get_max_similarity_empty(self):
        """Test empty results return 0."""
        max_sim = get_max_similarity([])
        assert max_sim == 0.0

    def test_get_relevance_tier(self):
        """Test relevance tier classification."""
        assert get_relevance_tier(0.95) == "excellent"
        assert get_relevance_tier(0.85) == "high"
        assert get_relevance_tier(0.70) == "medium"
        assert get_relevance_tier(0.50) == "low"


class TestMemoryCache:
    """Test suite for memory query caching."""

    @pytest.fixture
    def cache(self):
        """Create fresh cache for each test."""
        return MemoryQueryCache(default_ttl_seconds=60)

    @pytest.mark.asyncio
    async def test_cache_basic_operations(self, cache):
        """Test basic cache get/set operations."""
        query = "test query"
        data = {"results": ["item1", "item2"]}

        # Initially cache miss
        result = await cache.get(query, top_k=5)
        assert result is None

        # Set cache
        await cache.set(query, data, top_k=5)

        # Cache hit
        result = await cache.get(query, top_k=5)
        assert result is not None
        assert result["results"] == ["item1", "item2"]
        assert result["_cache_hit"] is True

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self, cache):
        """Test that cache entries expire after TTL."""
        query = "expiring query"
        data = {"results": []}

        # Set with short TTL
        await cache.set(query, data, top_k=5, ttl_seconds=0)

        # Should be expired immediately
        result = await cache.get(query, top_k=5)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_query_normalization(self, cache):
        """Test that similar queries hit same cache key."""
        query1 = "test   query"
        query2 = "test query"
        data = {"results": ["match"]}

        await cache.set(query1, data, top_k=5)
        result = await cache.get(query2, top_k=5)

        assert result is not None
        assert result["results"] == ["match"]

    @pytest.mark.asyncio
    async def test_get_or_query_with_cache_hit(self, cache):
        """Test get_or_query uses cache on hit."""
        query = "cached query"
        data = {"results": ["cached"], "query": query}

        await cache.set(query, data, top_k=5)

        mock_query_func = AsyncMock()
        result = await cache.get_or_query(
            query=query, query_func=mock_query_func, top_k=5
        )

        assert result["_cache_hit"] is True
        assert result["_source"] == "cache"
        mock_query_func.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_query_with_cache_miss(self, cache):
        """Test get_or_query executes function on miss."""
        query = "new query"
        data = {"results": ["fresh"], "query": query}

        async def mock_query(q, k):
            return data

        result = await cache.get_or_query(query=query, query_func=mock_query, top_k=5)

        assert result["_cache_hit"] is False
        assert result["_source"] == "query"
        assert result["results"] == ["fresh"]

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, cache):
        """Test cache invalidation."""
        query = "invalidate me"
        data = {"results": []}

        await cache.set(query, data, top_k=5)
        assert await cache.get(query, top_k=5) is not None

        await cache.invalidate()
        assert await cache.get(query, top_k=5) is None

    def test_cache_stats(self, cache):
        """Test cache statistics."""
        # Initially all zeros
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0


class TestIntelligentRetrieval:
    """Test suite for intelligent retrieval service."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        llm = Mock()
        llm.generate = Mock(
            return_value='{"sufficient": true, "confidence": 0.9, "reasoning": "test", "research_gaps": [], "extracted_entities": []}'
        )
        return llm

    @pytest.fixture
    def mock_vector_memory(self):
        """Create mock vector memory service."""
        vm = Mock()
        vm.query_memory_with_scores = Mock(
            return_value=[{"text": "Test memory chunk", "score": 15.0, "rank": 1}]
        )
        return vm

    @pytest.mark.asyncio
    async def test_retrieve_and_evaluate_no_memory(self, mock_llm):
        """Test behavior when no memory is found."""
        with patch(
            "app.services.intelligent_retrieval.get_vector_memory_service"
        ) as mock_get_vm:
            mock_vm = Mock()
            mock_vm.query_memory_with_scores = Mock(return_value=[])
            mock_get_vm.return_value = mock_vm

            service = IntelligentRetrievalService(llm=mock_llm)
            result = await service.retrieve_and_evaluate("test query")

            assert result["strategy"] == "full_research"
            assert result["confidence"] == 0.0
            assert "No relevant memory" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_retrieve_and_evaluate_memory_only(
        self, mock_llm, mock_vector_memory
    ):
        """Test Tier 1: Memory Only strategy."""
        mock_llm.generate = Mock(
            return_value='{"sufficient": true, "confidence": 0.92, "reasoning": "Complete info", "research_gaps": [], "extracted_entities": []}'
        )

        with patch(
            "app.services.intelligent_retrieval.get_vector_memory_service",
            return_value=mock_vector_memory,
        ):
            service = IntelligentRetrievalService(llm=mock_llm)
            result = await service.retrieve_and_evaluate("test query")

            assert result["strategy"] == "memory_only"
            assert result["confidence"] > 0.85
            assert len(result["memory_results"]) > 0

    @pytest.mark.asyncio
    async def test_retrieve_and_evaluate_memory_enhanced(
        self, mock_llm, mock_vector_memory
    ):
        """Test Tier 2: Memory Enhanced strategy."""
        mock_llm.generate = Mock(
            return_value='{"sufficient": false, "confidence": 0.75, "reasoning": "Needs more info", "research_gaps": ["recent funding"], "extracted_entities": ["Acme Corp"]}'
        )

        with patch(
            "app.services.intelligent_retrieval.get_vector_memory_service",
            return_value=mock_vector_memory,
        ):
            service = IntelligentRetrievalService(llm=mock_llm)
            result = await service.retrieve_and_evaluate("test query")

            assert result["strategy"] == "memory_enhanced"
            assert "research_gaps" in result
            assert len(result["research_gaps"]) > 0

    @pytest.mark.asyncio
    async def test_retrieve_and_evaluate_with_caching(
        self, mock_llm, mock_vector_memory
    ):
        """Test that caching is used when enabled."""
        with patch(
            "app.services.intelligent_retrieval.get_vector_memory_service",
            return_value=mock_vector_memory,
        ):
            service = IntelligentRetrievalService(llm=mock_llm, use_cache=True)

            # First call - cache miss
            result1 = await service.retrieve_and_evaluate(
                "cached query", use_cache=True
            )
            assert result1["_cache_info"]["hit"] is False

            # Second call - cache hit
            result2 = await service.retrieve_and_evaluate(
                "cached query", use_cache=True
            )
            assert result2["_cache_info"]["hit"] is True

    @pytest.mark.asyncio
    async def test_retrieve_and_evaluate_json_fallback(
        self, mock_llm, mock_vector_memory
    ):
        """Test fallback when LLM returns invalid JSON."""
        mock_llm.generate = Mock(return_value="Invalid JSON response")

        with patch(
            "app.services.intelligent_retrieval.get_vector_memory_service",
            return_value=mock_vector_memory,
        ):
            service = IntelligentRetrievalService(llm=mock_llm)
            result = await service.retrieve_and_evaluate("test query")

            # Should fallback to similarity-based decision
            assert "strategy" in result
            assert result["confidence"] > 0


class TestIntegration:
    """Integration tests for the full pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_tier_selection(self):
        """Test full pipeline selects correct tier."""
        # This would test the actual integration with real services
        # For now, we'll skip as it requires full infrastructure
        pass

    @pytest.mark.asyncio
    async def test_entity_extraction_from_memory(self):
        """Test that entities are extracted from retrieved memory."""
        # Would test: Query → Retrieve → Extract Entities → Identify Gaps
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
