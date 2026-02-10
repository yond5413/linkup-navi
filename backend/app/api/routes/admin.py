"""Admin routes for debugging and inspection."""

from fastapi import APIRouter, HTTPException
from app.db.schema import TaskRepository
from app.services.vector_memory import get_vector_memory_service

router = APIRouter()


@router.get("/admin/tasks")
async def get_recent_tasks(limit: int = 50):
    """Get recent agent tasks for admin/debug inspection."""
    tasks = await TaskRepository.get_recent_tasks(limit=limit)
    return {"tasks": tasks}


@router.get("/admin/memory/stats")
async def get_memory_stats():
    """Memory statistics endpoint.

    Returns:
    - total_vectors: Count of embedded chunks in FAISS
    - index_name: Name of the FAISS index
    - cohere_configured: Whether Cohere API is available
    """
    service = get_vector_memory_service()
    return {
        "total_vectors": service.get_vector_count(),
        "index_name": service.index_name,
        "cohere_configured": service.co is not None,
    }


@router.get("/admin/memory/recent")
async def get_recent_chunks(limit: int = 10):
    """Retrieve the most recent memory chunks.

    Useful for debugging what the agent has remembered recently.
    Chunks are returned in chronological order (oldest first)
    from the requested window.
    """
    service = get_vector_memory_service()
    chunks = service.get_recent_chunks(limit)
    return {"chunks": chunks}


@router.post("/admin/memory/search")
async def search_memory(query: str, k: int = 5):
    """Semantic search endpoint.

    Embeds the query using Cohere and searches FAISS for
    the most similar chunks. Returns results sorted by
    L2 distance (most similar first).
    """
    service = get_vector_memory_service()

    if not service.co:
        raise HTTPException(
            status_code=503,
            detail="Cohere API not configured. Cannot perform semantic search.",
        )

    if service.index.ntotal == 0:
        raise HTTPException(
            status_code=400, detail="Memory index is empty. No chunks to search."
        )

    results = service.query_memory_with_scores(query, k)
    return {"query": query, "results": results}
