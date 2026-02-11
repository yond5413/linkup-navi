from pathlib import Path
from .base import ToolResult, ToolContext
from .registry import tool


@tool(description="Read file content")
async def read_file(file_path: str, session_id: str) -> dict:
    path = Path(file_path)
    if path.exists():
        return {"content": path.read_text(encoding="utf-8")}
    return {"error": "File not found"}


@tool(description="List files in directory")
async def list_files(directory: str = ".") -> dict:
    path = Path(directory)
    return {"files": [p.name for p in path.iterdir() if p.is_file()]}


@tool(description="Search files by pattern")
async def search_files(pattern: str, directory: str = ".") -> dict:
    path = Path(directory)
    files = list(path.rglob(pattern))
    return {"files": [str(f) for f in files]}
