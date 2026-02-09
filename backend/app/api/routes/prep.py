"""Meeting preparation API routes with query classification."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List

from app.models.requests import PrepRequest, ClarifyRequest
from app.models.responses import (
    PrepResponse,
    BriefingResponse,
    DynamicResponse,
    ClarificationResponse,
    ClarificationOption,
    ResearchMetadata,
    ResearchSource,
)
from app.services.memory import SessionMemory
from app.services.llm import LLMClient
from app.services.linkup import LinkupClient
from app.services.pdf_parser import PDFParser
from app.core.planner import Planner
from app.core.executor import Executor, ExecutionState
from app.core.evaluator import Evaluator
from app.core.query_classifier import classify_query, QueryClassification
from app.services.vector_memory import get_vector_memory_service
from app.db.schema import SessionRepository


router = APIRouter()


def _build_research_metadata(
    plan, execution_results: dict, explicit_entities: Optional[List[str]] = None
) -> Optional[ResearchMetadata]:
    """Build research metadata from execution results and plan."""

    # Check if there was any research performed
    research_results = {}
    for step_id, result in execution_results.items():
        if isinstance(result, dict) and "research" in result:
            research_results.update(result["research"])

    if not research_results:
        return None

    # Build sources from research results
    sources = []
    entities = []

    for entity, info in research_results.items():
        entities.append(entity)
        if isinstance(info, dict):
            # Get sources from the linkup response
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

    # Check if user explicitly requested research (if explicit_entities is None, it was auto)
    is_auto = explicit_entities is None

    return ResearchMetadata(
        entities=entities or plan.entities_to_research,
        sources=sources,
        auto_researched=is_auto,
    )


@router.post("/prep")
async def prepare_meeting(
    request: PrepRequest, background_tasks: BackgroundTasks = None
):
    """Prepare response based on command (no files required)."""

    session_id = request.session_id
    command = request.command

    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    memory = SessionMemory(session_id)

    # Classify the query first
    file_names = []  # No files for this endpoint
    classification = classify_query(command, file_names)

    # If clarification needed, return early with options
    if classification.needs_clarification:
        return ClarificationResponse(
            status="needs_clarification",
            message=classification.clarification_message,
            suggested_types=[
                ClarificationOption(**opt)
                for opt in (classification.suggested_types or [])
            ],
            original_query=command,
        )

    llm = LLMClient()
    planner = Planner(llm)
    executor = Executor(llm, LinkupClient(), PDFParser(), session_id=session_id)
    evaluator = Evaluator(llm)

    vector_memory = get_vector_memory_service()
    long_term_context = vector_memory.query_memory(command)

    session_goal = session.user_goal or ""
    all_file_contents = {}  # No files for this endpoint

    # Clear any previous execution state
    Executor.clear_execution_status(session_id)

    # Enrich user goal with long-term context if available
    enriched_goal = command
    if long_term_context:
        enriched_goal += f"\n\nLong-term Memory Context:\n" + "\n".join(
            long_term_context
        )

    # Create plan with query type and explicit research entities if provided
    explicit_entities = request.research_entities if request.research_entities else None
    plan = await planner.plan(
        enriched_goal,
        classification.query_type.value,
        all_file_contents,
        session_goal,
        explicit_entities,
    )

    # Execute with user goal for context
    execution_result = await executor.run(plan, all_file_contents, command)

    evaluation = await evaluator.evaluate_completion(
        command, plan, execution_result["results"], execution_result["response"]
    )

    await memory.set_goal(command)

    # Save response to long-term memory
    if execution_result.get("response", {}).get("raw_response"):
        vector_memory.add_to_memory(execution_result["response"]["raw_response"])

    # Build research metadata
    research_metadata = _build_research_metadata(
        plan, execution_result["results"], explicit_entities
    )

    return PrepResponse(
        session_id=session_id,
        intent=plan.intent,
        query_type=plan.query_type,
        plan=plan.model_dump(),
        results=execution_result["results"],
        response=DynamicResponse(**execution_result["response"]),
        evaluation=evaluation,
        research_metadata=research_metadata,
    )


@router.post("/prep-with-files")
async def prepare_meeting_with_files(
    request: PrepRequest, background_tasks: BackgroundTasks = None
):
    """Prepare response based on command and uploaded files (files required)."""

    session_id = request.session_id
    command = request.command
    file_refs = request.file_refs or []

    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    memory = SessionMemory(session_id)

    all_file_contents = await memory.get_all_file_contents()

    if not all_file_contents:
        raise HTTPException(
            status_code=400, detail="No files uploaded for this session"
        )

    # Classify the query with file context
    file_names = list(all_file_contents.keys())
    classification = classify_query(command, file_names)

    # If clarification needed, return early with options
    if classification.needs_clarification:
        return ClarificationResponse(
            status="needs_clarification",
            message=classification.clarification_message,
            suggested_types=[
                ClarificationOption(**opt)
                for opt in (classification.suggested_types or [])
            ],
            original_query=command,
        )

    llm = LLMClient()
    planner = Planner(llm)
    executor = Executor(llm, LinkupClient(), PDFParser(), session_id=session_id)
    evaluator = Evaluator(llm)

    vector_memory = get_vector_memory_service()
    long_term_context = vector_memory.query_memory(command)

    session_goal = session.user_goal or ""

    # Clear any previous execution state
    Executor.clear_execution_status(session_id)

    # Enrich user goal with long-term context if available
    enriched_goal = command
    if long_term_context:
        enriched_goal += f"\n\nLong-term Memory Context:\n" + "\n".join(
            long_term_context
        )

    # Create plan with query type and explicit research entities if provided
    explicit_entities = request.research_entities if request.research_entities else None
    plan = await planner.plan(
        enriched_goal,
        classification.query_type.value,
        all_file_contents,
        session_goal,
        explicit_entities,
    )

    # Execute with user goal for context
    execution_result = await executor.run(plan, all_file_contents, command)

    evaluation = await evaluator.evaluate_completion(
        command, plan, execution_result["results"], execution_result["response"]
    )

    await memory.set_goal(command)

    # Save response to long-term memory
    if execution_result.get("response", {}).get("raw_response"):
        vector_memory.add_to_memory(execution_result["response"]["raw_response"])

    # Build research metadata
    research_metadata = _build_research_metadata(
        plan, execution_result["results"], explicit_entities
    )

    return PrepResponse(
        session_id=session_id,
        intent=plan.intent,
        query_type=plan.query_type,
        plan=plan.model_dump(),
        results=execution_result["results"],
        response=DynamicResponse(**execution_result["response"]),
        evaluation=evaluation,
        research_metadata=research_metadata,
    )


@router.post("/clarify")
async def clarify_query(request: ClarifyRequest):
    """Re-run query with user-selected clarification."""

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
    evaluator = Evaluator(llm)

    vector_memory = get_vector_memory_service()
    long_term_context = vector_memory.query_memory(original_command)

    session_goal = session.user_goal or ""

    # Clear any previous execution state
    Executor.clear_execution_status(session_id)

    # Enrich user goal
    enriched_goal = original_command
    if long_term_context:
        enriched_goal += f"\n\nLong-term Memory Context:\n" + "\n".join(
            long_term_context
        )

    # Create plan with user-confirmed query type (no explicit entities in clarify flow)
    plan = await planner.plan(
        enriched_goal, selected_type, all_file_contents, session_goal, None
    )

    # Execute with original command
    execution_result = await executor.run(plan, all_file_contents, original_command)

    evaluation = await evaluator.evaluate_completion(
        original_command,
        plan,
        execution_result["results"],
        execution_result["response"],
    )

    await memory.set_goal(original_command)

    # Save response to long-term memory
    if execution_result.get("response", {}).get("raw_response"):
        vector_memory.add_to_memory(execution_result["response"]["raw_response"])

    # Build research metadata (always auto-researched for clarify flow)
    research_metadata = _build_research_metadata(
        plan, execution_result["results"], None
    )

    return PrepResponse(
        session_id=session_id,
        intent=plan.intent,
        query_type=plan.query_type,
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


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its files."""
    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await SessionRepository.delete_session(session_id)
    return {"message": "Session deleted successfully"}


@router.get("/sessions/{session_id}/execution-status")
async def get_execution_status(session_id: str):
    """Get the current execution status for a session."""
    status = Executor.get_execution_status(session_id)

    if not status:
        return {
            "session_id": session_id,
            "current_step": "Waiting",
            "reasoning": "No active execution",
            "progress": 0.0,
            "complete": False,
        }

    return {
        "session_id": status.session_id,
        "current_step": status.current_step,
        "reasoning": status.reasoning,
        "progress": status.progress,
        "complete": status.complete,
        "timestamp": status.timestamp.isoformat() if status.timestamp else None,
    }
