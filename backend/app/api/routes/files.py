"""File upload and management API routes."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import uuid

from app.models.requests import UploadRequest
from app.models.responses import UploadResponse
from app.services.memory import SessionMemory
from app.db.schema import SessionRepository


router = APIRouter()


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_file(
    session_id: str,
    file: UploadFile = File(...),
):
    """Upload a file to a session."""

    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    file_id = str(uuid.uuid4())
    file_ext = Path(file.filename).suffix.lower()
    safe_filename = f"{session_id}_{file_id}{file_ext}"
    file_path = UPLOAD_DIR / safe_filename

    content = await file.read()
    file_path.write_bytes(content)

    memory = SessionMemory(session_id)
    await memory.add_file(
        file_name=file.filename,
        file_path=str(file_path),
        file_type=file_ext.lstrip("."),
    )

    return UploadResponse(
        file_id=file_id,
        file_name=file.filename,
        session_id=session_id,
        message="File uploaded successfully",
    )


@router.get("/sessions/{session_id}/files")
async def list_session_files(session_id: str):
    """List files in a session."""
    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    memory = SessionMemory(session_id)
    files = await memory.get_files()

    return {
        "files": [
            {
                "id": f.id,
                "file_name": f.file_name,
                "file_type": f.file_type,
                "uploaded_at": f.uploaded_at,
                "file_path": f.file_path,
            }
            for f in files
        ]
    }
