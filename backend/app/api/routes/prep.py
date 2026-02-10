"""Meeting preparation API routes with query classification."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List
import json

from app.models.requests import PrepRequest, ClarifyRequest, SessionUpdateRequest
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
from app.db.schema import SessionRepository, MessageRepository
from app.core.orchestrator import AgentOrchestrator


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

    llm = LLMClient()

    if not session.user_goal:
        session_name = await _generate_session_name(command, llm)
        await SessionRepository.update_goal(session_id, session_name)
        session_goal = session_name
    else:
        session_goal = session.user_goal

    orchestrator = AgentOrchestrator(llm=llm)
    
    # Run Orchestrator
    result = await orchestrator.run(
        session_id=session_id,
        command=command,
        file_contents={},
        session_goal=session_goal,
        explicit_entities=request.research_entities
    )
    
    if result["status"] == "needs_clarification":
        classification = result["classification"]
        return ClarificationResponse(
            status="needs_clarification",
            message=classification.clarification_message,
            suggested_types=[
                ClarificationOption(**opt)
                for opt in (classification.suggested_types or [])
            ],
            original_query=command,
        )

    # Build research metadata
    research_metadata = _build_research_metadata(
        PlannerOutput(**result["plan"]), result["results"], request.research_entities
    )

    # Persist messages and output to DB for session recovery
    try:
        await MessageRepository.save_message(session_id, "user", command, "text")
        # Ensure we don't block main response if persistence fails
        await MessageRepository.save_message(session_id, "assistant", "Briefing manifested in your workspace.", "text")
        
        # Prepare output for persistence (merge response + metadata)
        output_to_save = result["response"].copy()
        if "thought" in result.get("plan", {}):
            output_to_save["thought"] = result["plan"]["thought"]
        
        if hasattr(research_metadata, "model_dump"):
            output_to_save["research_metadata"] = research_metadata.model_dump()
        else:
            output_to_save["research_metadata"] = research_metadata
            
        await MessageRepository.save_output(session_id, json.dumps(output_to_save))
    except Exception as e:
        print(f"Failed to persist session state: {e}")

    return PrepResponse(
        session_id=session_id,
        intent=result["intent"],
        query_type=result["query_type"],
        plan=result["plan"],
        results=result["results"],
        response=DynamicResponse(**result["response"]),
        evaluation=result["evaluation"],
        research_metadata=research_metadata,
    )


@router.post("/prep-with-files")
async def prepare_meeting_with_files(
    request: PrepRequest, background_tasks: BackgroundTasks = None
):
    """Prepare response based on command and uploaded files (files required)."""

    session_id = request.session_id
    command = request.command

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
        raise HTTPException(status_code=400, detail="No files uploaded for this session")

    orchestrator = AgentOrchestrator(llm=llm)
    
    # Run Orchestrator
    result = await orchestrator.run(
        session_id=session_id,
        command=command,
        file_contents=all_file_contents,
        session_goal=session_goal,
        explicit_entities=request.research_entities
    )
    
    if result["status"] == "needs_clarification":
        classification = result["classification"]
        return ClarificationResponse(
            status="needs_clarification",
            message=classification.clarification_message,
            suggested_types=[
                ClarificationOption(**opt)
                for opt in (classification.suggested_types or [])
            ],
            original_query=command,
        )

    # Build research metadata
    research_metadata = _build_research_metadata(
        PlannerOutput(**result["plan"]), result["results"], request.research_entities
    )

    # Persist messages and output to DB for session recovery
    try:
        await MessageRepository.save_message(session_id, "user", command, "text")
        await MessageRepository.save_message(session_id, "assistant", "Briefing manifested in your workspace.", "text")
        
        # Prepare output for persistence (merge response + metadata)
        output_to_save = result["response"].copy()
        if "thought" in result.get("plan", {}):
            output_to_save["thought"] = result["plan"]["thought"]
        
        if hasattr(research_metadata, "model_dump"):
            output_to_save["research_metadata"] = research_metadata.model_dump()
        else:
            output_to_save["research_metadata"] = research_metadata
            
        await MessageRepository.save_output(session_id, json.dumps(output_to_save))
    except Exception as e:
        print(f"Failed to persist session state: {e}")

    return PrepResponse(
        session_id=session_id,
        intent=result["intent"],
        query_type=result["query_type"],
        plan=result["plan"],
        results=result["results"],
        response=DynamicResponse(**result["response"]),
        evaluation=result["evaluation"],
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
    execution_result = await executor.run(plan, all_file_contents, enriched_goal)

    evaluation = await evaluator.evaluate_completion(
        original_command,
        plan,
        execution_result["results"],
        execution_result["response"],
    )

    await memory.set_goal(original_command)

    # Save response to long-term memory
    # if execution_result.get("response", {}).get("raw_response"):
    # vector_memory.add_to_memory(execution_result["response"]["raw_response"])

    # Build research metadata (manual construction since no orchestrator here)
    research_metadata = ResearchMetadata(
        entities=[],  # No explicit entities in clarification flow usually
        sources=[],   # Linkup sources would need to be extracted from results if needed
        auto_researched=False
    )

    # Persist messages and output to DB for session recovery
    try:
        await MessageRepository.save_message(session_id, "user", f"I meant: {selected_type}", "text")
        await MessageRepository.save_message(session_id, "assistant", "Briefing manifested in your workspace.", "text")
        
        # Prepare output for persistence
        output_to_save = execution_result["response"].copy()
        output_to_save["research_metadata"] = research_metadata.model_dump()
            
        await MessageRepository.save_output(session_id, json.dumps(output_to_save))
    except Exception as e:
        print(f"Failed to persist session state: {e}")

    return PrepResponse(
        session_id=session_id,
        intent=plan.intent,
        query_type=selected_type or "clarification", # Assuming selected_type is the query_type for persistence
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
    """Update session metadata (e.g., user_goal/session name)."""
    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await SessionRepository.update_goal(session_id, request.user_goal)
    return {"message": "Session updated successfully"}


from app.db.schema import SessionRepository, SessionFileRepository
from app.config import get_settings
import os


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session, its files, and associated uploaded files from disk."""
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
