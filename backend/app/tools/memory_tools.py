from typing import List
from .base import ToolResult, ToolContext
from .registry import tool


@tool(description="Query long-term memory for relevant context")
async def query_memory(query: str, session_id: str, top_k: int = 5) -> dict:
    from app.services.vector_memory import get_vector_memory_service

    vmem = get_vector_memory_service()
    results = vmem.query(query, top_k=top_k)
    return {"results": results}


@tool(description="Store item in long-term memory")
async def store_memory(content: str, session_id: str, metadata: dict = None) -> dict:
    from app.services.vector_memory import get_vector_memory_service

    vmem = get_vector_memory_service()
    embedding_id = vmem.add(content, metadata or {})
    return {"embedding_id": embedding_id}


@tool(description="Get session context")
async def get_session_context(session_id: str) -> dict:
    from app.services.memory import create_memory

    memory = create_memory(session_id)
    files = await memory.get_files()
    goal = await memory.get_goal()
    context = await memory.get_context()
    return {"files": [f.to_dict() for f in files], "goal": goal, "context": context}


@tool(description="Add message to conversation history")
async def add_message(session_id: str, role: str, content: str) -> dict:
    from app.db.schema import MessageRepository

    await MessageRepository.save_message(session_id, role, content)
    return {"success": True}


@tool(description="Get conversation history")
async def get_messages(session_id: str, limit: int = 50) -> dict:
    from app.db.schema import MessageRepository

    messages = await MessageRepository.get_messages(session_id)
    return {"messages": messages[-limit:]}
