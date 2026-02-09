"""Meeting preparation API routes."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional

from app.models.requests import PrepRequest
from app.models.responses import PrepResponse, BriefingResponse
from app.services.memory import SessionMemory
from app.services.llm import LLMClient
from app.services.linkup import LinkupClient
from app.services.pdf_parser import PDFParser
from app.core.planner import Planner
from app.core.executor import Executor
from app.core.evaluator import Evaluator
from app.db.schema import SessionRepository


router = APIRouter()


@router.post("/prep")
async def prepare_meeting(
    request: PrepRequest, background_tasks: BackgroundTasks = None
):
    """Main endpoint: Prepare for a meeting based on command and uploaded files."""

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

    llm = LLMClient()
    planner = Planner(llm)
    executor = Executor(llm, LinkupClient(), PDFParser())
    evaluator = Evaluator()

    session_goal = session.user_goal or ""
    plan = await planner.plan(command, all_file_contents, session_goal)

    execution_result = await executor.run(plan, all_file_contents)

    evaluation = await evaluator.evaluate_completion(
        command, plan, execution_result["results"], execution_result["briefing"]
    )

    await memory.set_goal(command)

    return PrepResponse(
        session_id=session_id,
        intent=plan.intent,
        plan=plan.model_dump(),
        results=execution_result["results"],
        briefing=BriefingResponse(**execution_result["briefing"]),
        evaluation=evaluation,
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
