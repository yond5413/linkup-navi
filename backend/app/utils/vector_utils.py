"""Vector utility functions for similarity calculations."""

from typing import List, Dict, Any


def l2_to_cosine_similarity(l2_distance: float, dimensions: int = 1024) -> float:
    """
    Convert L2 distance to cosine similarity for normalized vectors.

    For normalized vectors: cos_sim = 1 - (L2^2 / 2)
    Range: -1 to 1 (but typically 0 to 1 for semantic similarity)

    Args:
        l2_distance: Euclidean distance from FAISS
        dimensions: Vector dimensionality (default 1024 for Cohere embed-english-v3.0)

    Returns:
        Cosine similarity score between -1 and 1
    """
    # For normalized vectors, cosine similarity can be derived from L2 distance
    # cos_sim = 1 - (L2_distance^2 / 2)
    cosine_sim = 1 - (l2_distance**2) / 2

    # Clamp to valid range
    return max(-1.0, min(1.0, cosine_sim))


def process_memory_results(
    results: List[Dict[str, Any]], dimensions: int = 1024
) -> List[Dict[str, Any]]:
    """
    Process memory query results and add cosine similarity scores.

    Args:
        results: List of results from query_memory_with_scores
        dimensions: Vector dimensionality

    Returns:
        Results with added 'cosine_similarity' and 'l2_distance' fields
    """
    processed = []
    for result in results:
        l2_dist = result.get("score", 0)
        cosine_sim = l2_to_cosine_similarity(l2_dist, dimensions)

        processed.append(
            {**result, "l2_distance": l2_dist, "cosine_similarity": cosine_sim}
        )

    return processed


def get_max_similarity(results: List[Dict[str, Any]]) -> float:
    """Get the maximum cosine similarity from processed results."""
    if not results:
        return 0.0
    return max(r.get("cosine_similarity", 0) for r in results)


def get_relevance_tier(cosine_similarity: float) -> str:
    """
    Determine relevance tier based on cosine similarity.

    Tiers:
    - excellent: > 0.90 (identical/near-identical)
    - high: 0.80-0.90 (same topic/entity)
    - medium: 0.60-0.80 (related concepts)
    - low: < 0.60 (weakly related)
    """
    if cosine_similarity > 0.90:
        return "excellent"
    elif cosine_similarity > 0.80:
        return "high"
    elif cosine_similarity > 0.60:
        return "medium"
    else:
        return "low"
