"""Intelligent retrieval service with LLM-driven evaluation."""

from typing import List, Dict, Any, Optional
import json
from app.services.vector_memory import get_vector_memory_service
from app.services.llm import LLMClient
from app.services.memory_cache import get_memory_query_cache
from app.utils.vector_utils import process_memory_results, get_max_similarity


class IntelligentRetrievalService:
    """
    AI-Native retrieval service that uses LLM to evaluate memory sufficiency.

    Pattern: Retrieve → Evaluate → Decide
    - Retrieve: Semantic search from vector memory
    - Evaluate: LLM assesses if retrieved content sufficiently answers query
    - Decide: LLM determines research strategy and identifies gaps
    """

    def __init__(self, llm: Optional[LLMClient] = None, use_cache: bool = True):
        self.llm = llm or LLMClient()
        self.vector_memory = get_vector_memory_service()
        self.cache = get_memory_query_cache()
        self.use_cache = use_cache

    async def retrieve_and_evaluate(
        self,
        query: str,
        top_k: int = 5,
        query_context: Optional[str] = None,
        use_cache: bool = None,
    ) -> Dict[str, Any]:
        """
        Retrieve memory chunks and evaluate sufficiency with LLM.

        Args:
            query: User query
            top_k: Number of memory chunks to retrieve
            query_context: Additional context about the query intent
            use_cache: Override instance cache setting

        Returns:
            Dict with strategy, confidence, reasoning, and processed results
        """
        # Determine if caching should be used
        should_use_cache = use_cache if use_cache is not None else self.use_cache

        # Define the query function for caching
        async def _execute_query(q: str, k: int) -> Dict[str, Any]:
            # Step 1: Retrieve from vector memory
            raw_results = self.vector_memory.query_memory_with_scores(q, top_k=k)

            if not raw_results:
                return {"raw_results": [], "query": q, "has_results": False}

            # Step 2: Process results (convert L2 to cosine)
            processed_results = process_memory_results(raw_results)

            return {"raw_results": processed_results, "query": q, "has_results": True}

        # Execute with caching
        query_result = await self.cache.get_or_query(
            query=query,
            query_func=_execute_query,
            top_k=top_k,
            use_cache=should_use_cache,
        )

        # Check if we got results
        if not query_result.get("has_results"):
            return {
                "strategy": "full_research",
                "confidence": 0.0,
                "reasoning": "No relevant memory found",
                "memory_results": [],
                "max_similarity": 0.0,
                "research_gaps": ["No prior context available"],
                "source": "no_memory",
                "_cache_info": {
                    "hit": query_result.get("_cache_hit", False),
                    "source": query_result.get("_source", "unknown"),
                },
            }

        processed_results = query_result["raw_results"]
        max_similarity = get_max_similarity(processed_results)

        # Step 3: LLM Evaluation (don't cache this - it's query-specific)
        evaluation = await self._evaluate_with_llm(
            query=query,
            memory_chunks=processed_results,
            max_similarity=max_similarity,
            query_context=query_context,
        )

        # Step 4: Determine strategy based on LLM evaluation
        if (
            evaluation.get("sufficient", False)
            and evaluation.get("confidence", 0) > 0.85
        ):
            strategy = "memory_only"
        elif evaluation.get("research_gaps"):
            strategy = "memory_enhanced"
        else:
            strategy = "full_research"

        return {
            "strategy": strategy,
            "confidence": evaluation.get("confidence", 0.0),
            "reasoning": evaluation.get("reasoning", ""),
            "memory_results": processed_results,
            "max_similarity": max_similarity,
            "research_gaps": evaluation.get("research_gaps", []),
            "extracted_entities": evaluation.get("extracted_entities", []),
            "source": "vector_memory",
            "_cache_info": {
                "hit": query_result.get("_cache_hit", False),
                "source": query_result.get("_source", "unknown"),
            },
        }

    async def _evaluate_with_llm(
        self,
        query: str,
        memory_chunks: List[Dict[str, Any]],
        max_similarity: float,
        query_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Use LLM to evaluate if retrieved memory sufficiently answers the query.

        Returns:
            {
                "sufficient": bool,
                "confidence": float (0-1),
                "reasoning": str,
                "research_gaps": list of str,
                "extracted_entities": list of str
            }
        """
        # Format memory chunks for LLM
        memory_text = "\n\n---\n\n".join(
            [
                f"[Similarity: {chunk.get('cosine_similarity', 0):.2f}] {chunk.get('text', '')}"
                for chunk in memory_chunks[:3]  # Top 3 for evaluation
            ]
        )

        system_prompt = """You are an intelligent retrieval evaluator. Your job is to:
1. Determine if retrieved memory sufficiently answers the user's query
2. Identify what information is missing (research gaps)
3. Extract any important entities mentioned that might need additional research
4. Provide confidence score (0-1) and reasoning

Return ONLY a JSON object in this exact format:
{
    "sufficient": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "explanation of your decision",
    "research_gaps": ["list of missing information"],
    "extracted_entities": ["entities mentioned"]
}"""

        context_info = f"\nQuery Context: {query_context}" if query_context else ""

        prompt = f"""User Query: {query}{context_info}

Retrieved Memory (with similarity scores):
{memory_text}

Max Cosine Similarity: {max_similarity:.2f}

Evaluate:
1. Does this memory sufficiently answer the query? (sufficient: true/false)
2. What is your confidence in this assessment? (confidence: 0-1)
3. What reasoning led to this decision? (reasoning: string)
4. What research gaps exist, if any? (research_gaps: list)
5. What important entities are mentioned? (extracted_entities: list)

Respond with valid JSON only."""

        try:
            response = self.llm.generate(prompt, system=system_prompt)

            # Parse JSON response
            evaluation = json.loads(response.strip())

            # Validate required fields
            required_fields = [
                "sufficient",
                "confidence",
                "reasoning",
                "research_gaps",
                "extracted_entities",
            ]
            for field in required_fields:
                if field not in evaluation:
                    evaluation[field] = (
                        []
                        if field in ["research_gaps", "extracted_entities"]
                        else False
                        if field == "sufficient"
                        else 0.0
                        if field == "confidence"
                        else ""
                    )

            return evaluation

        except json.JSONDecodeError as e:
            # Fallback if LLM doesn't return valid JSON
            return {
                "sufficient": max_similarity > 0.85,
                "confidence": max_similarity,
                "reasoning": f"Fallback to similarity-based decision. Raw response: {response[:100]}",
                "research_gaps": []
                if max_similarity > 0.85
                else ["Insufficient memory context"],
                "extracted_entities": [],
            }
        except Exception as e:
            # Error fallback
            return {
                "sufficient": False,
                "confidence": 0.0,
                "reasoning": f"Error in LLM evaluation: {str(e)}",
                "research_gaps": ["Error occurred, defaulting to full research"],
                "extracted_entities": [],
            }


def create_intelligent_retrieval_service(
    llm: Optional[LLMClient] = None, use_cache: bool = True
) -> IntelligentRetrievalService:
    """Factory function for IntelligentRetrievalService."""
    return IntelligentRetrievalService(llm, use_cache=use_cache)
