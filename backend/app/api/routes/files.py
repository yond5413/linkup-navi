"""File upload and management API routes."""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pathlib import Path
import shutil
import uuid

from app.models.requests import UploadRequest
from app.models.responses import UploadResponse
from app.services.memory import SessionMemory
from app.services.vector_memory import get_vector_memory_service
from app.services.pdf_parser import PDFParser
from app.db.schema import SessionRepository


router = APIRouter()


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_file(
    session_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload a file to a session with duplicate detection."""

    session = await SessionRepository.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from app.db.schema import SessionFileRepository
    existing_files = await SessionFileRepository.get_files_by_name(file.filename)

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

    # Add background task for indexing in vector memory
    if file_ext == ".pdf":
        background_tasks.add_task(index_document, str(file_path), file.filename)

    message = "File uploaded successfully"
    if existing_files:
        message += f" (Note: {len(existing_files)} other version(s) of this file already exist in the knowledge base)"

    return UploadResponse(
        file_id=file_id,
        file_name=file.filename,
        session_id=session_id,
        message=message,
    )

async def index_document(file_path: str, filename: str):
    """Extract text from PDF and add to long-term memory."""
    try:
        text = PDFParser.extract_text(file_path)
        if text:
            vector_memory = get_vector_memory_service()
            # Add chunks of text to memory if it's long
            chunk_size = 2000; overlap = 200; chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size - overlap)]
            for chunk in chunks:
                vector_memory.add_to_memory(f"Document '{filename}': {chunk}")
    except Exception as e:
        print(f"Error indexing document {filename}: {e}")


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


@router.get("/knowledge/files")
async def list_all_files():
    """List all unique files uploaded across all sessions."""
    from app.db.schema import SessionFileRepository
    files = await SessionFileRepository.get_all_files()
    
    # Filter to show unique file names if needed, or just show everything
    # Let's show everything for now
    return {
        "files": [
            {
                "id": f.id,
                "session_id": f.session_id,
                "file_name": f.file_name,
                "file_type": f.file_type,
                "uploaded_at": f.uploaded_at,
            }
            for f in files
        ]
    }


@router.delete("/knowledge/files/{file_id}")
async def delete_knowledge_file(file_id: str):
    """Delete a file from the knowledge base and disk."""
    from app.db.schema import SessionFileRepository
    import os
    
    file_info = await SessionFileRepository.get_file_by_id(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Delete from disk
    if os.path.exists(file_info.file_path):
        os.remove(file_info.file_path)
        
    # Delete from DB
    await SessionFileRepository.delete_file(file_id)
    
    return {"message": "File deleted successfully"}


@router.get("/knowledge/memory-status")
async def get_memory_status():
    """Get status of the long-term vector memory."""
    vector_memory = get_vector_memory_service()
    return {
        "total_chunks": vector_memory.index.ntotal if vector_memory.index else 0,
        "index_name": vector_memory.index_name,
    }
