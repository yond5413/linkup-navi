"""Meeting preparation API routes with query classification and agent support."""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
import json
import logging

from app.models.requests import PrepRequest, ClarifyRequest, SessionUpdateRequest
from app.models.responses import (
    PrepResponse,
    DynamicResponse,
    ClarificationResponse,
    ClarificationOption,
    ResearchMetadata,
    ResearchSource,
)
from app.services.memory import SessionMemory
from app.services.llm import LLMClient
from app.core.orchestrator import AgentOrchestrator
from app.core.query_classifier import classify_query
from app.db.schema import SessionRepository, MessageRepository

logger = logging.getLogger(__name__)


router = APIRouter()


async def _generate_session_name(command: str, llm: LLMClient) -> str:
    """Generate a descriptive session name from the user's first command."""
    prompt = f"""Generate a descriptive session name (4-8 words) for this user request.
Focus on the ACTION and TOPIC. Return only the name, nothing else.

Examples:
- "Help me prepare for my interview" → "Interview Preparation - General Tips"
- "Review my startup pitch deck" → "Pitch Deck Review - Startup Evaluation"
- "Analyze this contract for hidden fees" → "Contract Analysis - Hidden Fee Review"

User request: "{command}"

Session name:"""

    try:
        name = llm.generate(prompt).strip()
        name = name.strip('"').strip("'")
        if not name or len(name) < 3:
            return command[:40] + "..." if len(command) > 40 else command
        if len(name) > 50:
            name = name[:50].rsplit(" ", 1)[0] + "..."
        return name
    except Exception:
        return command[:40] + "..." if len(command) > 40 else command


def _build_research_metadata(
    plan, execution_results: dict, explicit_entities: Optional[List[str]] = None
) -> Optional[ResearchMetadata]:
    """Build research metadata from execution results and plan."""

    research_results = {}
    for step_id, result in execution_results.items():
        if isinstance(result, dict) and "research" in result:
            research_results.update(result["research"])

    if not research_results:
        return None

    sources = []
    entities = []

    for entity, info in research_results.items():
        entities.append(entity)
        if isinstance(info, dict):
            for source in info.get("sources", []):
                sources.append(
                    ResearchSource(
                        entity=entity,
                        url=source.get("url", ""),
                        title=source.get("name", entity),
                        snippet=source.get("snippet", ""),
                        favicon=source.get("favicon"),
                    )
                )

    is_auto = explicit_entities is None

    entities_to_use = entities
    if not entities_to_use and hasattr(plan, "entities_to_research"):
        entities_to_use = plan.entities_to_research

    return ResearchMetadata(
        entities=entities_to_use or [],
        sources=sources,
        auto_researched=is_auto,
    )


@router.post("/prep")
async def prepare_meeting(request: PrepRequest):
    """Prepare response based on command (no files required)."""

    session_id = request.session_id
    command = request.command
    mode = request.mode

    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    llm = LLMClient()

    if not session.user_goal:
        session_name = await _generate_session_name(command, llm)
        await SessionRepository.update_goal(session_id, session_name)
        session_goal = session_name
    else:
        session_goal = session.user_goal

    try:
        await MessageRepository.save_message(session_id, "user", command, "text")
    except Exception as e:
        logger.warning(f"Failed to save user message: {e}")

    memory = SessionMemory(session_id)
    all_file_contents = await memory.get_all_file_contents()
    file_contents = all_file_contents or {}

    orchestrator = AgentOrchestrator(llm=llm)

    result = await orchestrator.run(
        session_id=session_id,
        command=command,
        file_contents=file_contents,
        session_goal=session_goal,
        explicit_entities=request.research_entities,
        mode=mode,
    )

    if result.get("status") == "needs_clarification":
        classification = result.get("classification", {})
        return ClarificationResponse(
            status="needs_clarification",
            message=classification.get(
                "clarification_message", "Could you clarify your request?"
            ),
            suggested_types=[
                ClarificationOption(**opt)
                for opt in (classification.get("suggested_types") or [])
            ],
            original_query=command,
        )

    response_data = result.get("response", {})
    thought = result.get("thought", "")
    execution_trace = result.get("execution_trace", [])
    sections = response_data.get("sections", {})

    if isinstance(response_data, str):
        response_data = {
            "raw_response": response_data,
            "query_type": result.get("mode", "general"),
            "structured": len(sections) > 1,
            "sections": sections,
            "thought": thought,
            "execution_trace": execution_trace,
        }
    else:
        response_data["thought"] = thought
        response_data["execution_trace"] = execution_trace
        response_data["sections"] = sections
        response_data["structured"] = len(sections) > 1

    raw_response = response_data.get("raw_response", str(response_data))

    try:
        await MessageRepository.save_message(
            session_id, "assistant", raw_response, "text"
        )
        output_to_save = {
            **response_data,
            "intent": result.get("intent", command),
        }
        await MessageRepository.save_output(session_id, json.dumps(output_to_save))
    except Exception as e:
        logger.warning(f"Failed to save messages: {e}")

    return PrepResponse(
        session_id=session_id,
        intent=result.get("intent", command),
        query_type=response_data.get("query_type", result.get("mode", "general")),
        plan=result.get("plan", {}),
        results=result.get("results", {}),
        response=DynamicResponse(**response_data),
        evaluation=result.get("evaluation"),
        research_metadata=None,
        execution_trace=execution_trace,
    )


@router.post("/prep-with-files")
async def prepare_meeting_with_files(request: PrepRequest):
    """Prepare response based on command and uploaded files (files required)."""

    session_id = request.session_id
    command = request.command
    mode = request.mode

    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    memory = SessionMemory(session_id)
    llm = LLMClient()

    if not session.user_goal:
        session_name = await _generate_session_name(command, llm)
        await SessionRepository.update_goal(session_id, session_name)
        session_goal = session_name
    else:
        session_goal = session.user_goal

    all_file_contents = await memory.get_all_file_contents()
    if not all_file_contents:
        raise HTTPException(
            status_code=400, detail="No files uploaded for this session"
        )

    try:
        await MessageRepository.save_message(session_id, "user", command, "text")
    except Exception as e:
        logger.warning(f"Failed to save user message: {e}")

    orchestrator = AgentOrchestrator(llm=llm)

    result = await orchestrator.run(
        session_id=session_id,
        command=command,
        file_contents=all_file_contents,
        session_goal=session_goal,
        explicit_entities=request.research_entities,
        mode=mode,
    )

    if result.get("status") == "needs_clarification":
        classification = result.get("classification", {})
        return ClarificationResponse(
            status="needs_clarification",
            message=classification.get(
                "clarification_message", "Could you clarify your request?"
            ),
            suggested_types=[
                ClarificationOption(**opt)
                for opt in (classification.get("suggested_types") or [])
            ],
            original_query=command,
        )

    response_data = result.get("response", {})
    thought = result.get("thought", "")
    execution_trace = result.get("execution_trace", [])
    sections = response_data.get("sections", {})

    if isinstance(response_data, str):
        response_data = {
            "raw_response": response_data,
            "query_type": result.get("mode", "general"),
            "structured": len(sections) > 1,
            "sections": sections,
            "thought": thought,
            "execution_trace": execution_trace,
        }
    else:
        response_data["thought"] = thought
        response_data["execution_trace"] = execution_trace
        response_data["sections"] = sections
        response_data["structured"] = len(sections) > 1

    raw_response = response_data.get("raw_response", str(response_data))

    try:
        await MessageRepository.save_message(
            session_id, "assistant", raw_response, "text"
        )
        output_to_save = {
            **response_data,
            "intent": result.get("intent", command),
        }
        await MessageRepository.save_output(session_id, json.dumps(output_to_save))
    except Exception as e:
        logger.warning(f"Failed to save messages: {e}")

    return PrepResponse(
        session_id=session_id,
        intent=result.get("intent", command),
        query_type=response_data.get("query_type", result.get("mode", "general")),
        plan=result.get("plan", {}),
        results=result.get("results", {}),
        response=DynamicResponse(**response_data),
        evaluation=result.get("evaluation"),
        research_metadata=None,
        execution_trace=execution_trace,
    )


@router.post("/clarify")
async def clarify_query(request: ClarifyRequest):
    """Re-run query with user-selected clarification."""
    from app.core.planner import Planner, PlannerOutput
    from app.core.executor import Executor
    from app.core.evaluator import LegacyEvaluator
    from app.services.linkup import LinkupClient
    from app.services.pdf_parser import PDFParser

    session_id = request.session_id
    original_command = request.original_command
    selected_type = request.selected_type

    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    memory = SessionMemory(session_id)
    all_file_contents = await memory.get_all_file_contents()

    llm = LLMClient()
    planner = Planner(llm)
    executor = Executor(llm, LinkupClient(), PDFParser(), session_id=session_id)
    evaluator = LegacyEvaluator(llm)

    from app.services.vector_memory import get_vector_memory_service

    vector_memory = get_vector_memory_service()
    long_term_context = vector_memory.query_memory(original_command)

    session_goal = session.user_goal or ""

    Executor.clear_execution_status(session_id)

    enriched_goal = original_command
    if long_term_context:
        enriched_goal += f"\n\nLong-term Memory Context:\n" + "\n".join(
            long_term_context
        )

    plan = await planner.plan(
        enriched_goal, selected_type, all_file_contents, session_goal, None
    )

    execution_result = await executor.run(plan, all_file_contents, enriched_goal)

    evaluation = await evaluator.evaluate_completion(
        original_command,
        plan,
        execution_result["results"],
        execution_result["response"],
    )

    await memory.set_goal(original_command)

    research_metadata = _build_research_metadata(
        plan, execution_result["results"], None
    )

    return PrepResponse(
        session_id=session_id,
        intent=plan.intent,
        query_type=selected_type,
        plan=plan.model_dump(),
        results=execution_result["results"],
        response=DynamicResponse(**execution_result["response"]),
        evaluation=evaluation,
        research_metadata=research_metadata,
    )


@router.post("/sessions")
async def create_session():
    """Create a new session."""
    session = await SessionRepository.create_session()
    return {
        "id": session.id,
        "created_at": session.created_at,
        "message": "Session created successfully",
    }


@router.get("/sessions")
async def list_sessions():
    """List all sessions."""
    sessions = await SessionRepository.list_sessions()
    return {
        "sessions": [
            {
                "id": s.id,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
                "user_goal": s.user_goal,
            }
            for s in sessions
        ]
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details with files."""
    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    memory = SessionMemory(session_id)
    files = await memory.get_files()

    return {
        "id": session.id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "user_goal": session.user_goal,
        "files": [
            {
                "id": f.id,
                "file_name": f.file_name,
                "file_type": f.file_type,
                "uploaded_at": f.uploaded_at,
            }
            for f in files
        ],
    }


@router.put("/sessions/{session_id}")
async def update_session(session_id: str, request: SessionUpdateRequest):
    """Update session metadata."""
    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await SessionRepository.update_goal(session_id, request.user_goal)
    return {"message": "Session updated successfully"}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session, its files, and associated uploaded files from disk."""
    from app.db.schema import SessionFileRepository
    from app.config import get_settings
    import os

    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    settings = get_settings()

    files = await SessionFileRepository.get_files_by_session(session_id)
    for file in files:
        file_path = os.path.join(settings.uploads_dir, file.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

    await SessionRepository.delete_session(session_id)
    return {"message": "Session deleted successfully"}


@router.get("/sessions/{session_id}/execution-status")
async def get_execution_status(session_id: str):
    """Get the current execution status for a session."""
    from app.core.executor import Executor

    status = Executor.get_execution_status(session_id)

    if not status:
        return {
            "session_id": session_id,
            "current_step": "Waiting",
            "reasoning": "No active execution",
            "thought": "",
            "progress": 0.0,
            "complete": False,
        }

    return {
        "session_id": status.session_id,
        "current_step": status.current_step,
        "reasoning": status.reasoning,
        "thought": status.thought,
        "progress": status.progress,
        "complete": status.complete,
        "timestamp": status.timestamp.isoformat() if status.timestamp else None,
    }


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get all persisted chat messages for a session."""
    messages = await MessageRepository.get_messages(session_id)
    return {"messages": messages}


@router.get("/sessions/{session_id}/output")
async def get_session_output(session_id: str):
    """Get the latest persisted output for a session."""
    output_json = await MessageRepository.get_latest_output(session_id)
    if output_json:
        return {"output": json.loads(output_json)}
    return {"output": None}
