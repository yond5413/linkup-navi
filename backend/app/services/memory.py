"""Session memory management with SQLite persistence."""

from typing import Optional
from datetime import datetime
from pathlib import Path

from app.db.schema import (
    SessionRepository,
    SessionFileRepository,
    SessionContextRepository,
    Session,
)


class SessionMemory:
    def __init__(self, session_id: str):
        self.session_id = session_id

    async def get_or_create(self) -> Session:
        session = await SessionRepository.get_session(self.session_id)
        if session is None:
            session = await SessionRepository.create_session()
        return session

    async def add_file(self, file_name: str, file_path: str, file_type: str) -> str:
        sf = await SessionFileRepository.create_file(
            self.session_id, file_name, file_path, file_type
        )
        return sf.id

    async def get_files(self) -> list:
        return await SessionFileRepository.get_files_by_session(self.session_id)

    async def set_goal(self, goal: str):
        await SessionRepository.update_goal(self.session_id, goal)

    async def get_goal(self) -> str:
        session = await SessionRepository.get_session(self.session_id)
        return session.user_goal if session else ""

    async def set_context(self, key: str, value: str):
        await SessionContextRepository.set_context(self.session_id, key, value)

    async def get_context(self) -> dict:
        return await SessionContextRepository.get_context(self.session_id)

    async def clear(self):
        await SessionRepository.delete_session(self.session_id)

    async def get_file_content(self, file_id: str) -> Optional[str]:
        files = await SessionFileRepository.get_files_by_session(self.session_id)
        for f in files:
            if f.id == file_id:
                path = Path(f.file_path)
                if path.exists():
                    return path.read_text(encoding="utf-8")
        return None

    async def get_all_file_contents(self) -> dict[str, str]:
        files = await SessionFileRepository.get_files_by_session(self.session_id)
        contents = {}
        for f in files:
            path = Path(f.file_path)
            if path.exists():
                contents[f.file_name] = path.read_text(encoding="utf-8")
        return contents


def create_memory(session_id: str) -> SessionMemory:
    return SessionMemory(session_id)
