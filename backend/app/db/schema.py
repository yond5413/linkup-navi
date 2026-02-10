"""SQLAlchemy-like schema using aiosqlite."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field, asdict
import aiosqlite
import json
from pathlib import Path

from app.config import get_settings


@dataclass
class Session:
    id: str
    created_at: str
    updated_at: str
    user_goal: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class SessionFile:
    id: str
    session_id: str
    file_name: str
    file_path: str
    file_type: str
    uploaded_at: str

    def to_dict(self):
        return asdict(self)


@dataclass
class SessionContext:
    id: str
    session_id: str
    key: str
    value: str
    created_at: str

    def to_dict(self):
        return asdict(self)


@dataclass
class Task:
    id: str
    session_id: str
    user_input: str
    inferred_intent: str
    tools_used: str
    status: str
    created_at: str

    def to_dict(self):
        return asdict(self)


@dataclass
class SessionMessage:
    id: str
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    msg_type: str  # "text", "status", "clarification"
    created_at: str

    def to_dict(self):
        return asdict(self)


@dataclass
class SessionOutput:
    id: str
    session_id: str
    output_json: str  # JSON string of the full output
    created_at: str

    def to_dict(self):
        return asdict(self)


DATABASE_PATH = get_settings().db_path


async def init_db():
    db = await aiosqlite.connect(str(DATABASE_PATH))
    await db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            user_goal TEXT DEFAULT ''
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS session_files (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT NOT NULL,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS session_context (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_input TEXT NOT NULL,
            inferred_intent TEXT NOT NULL,
            tools_used TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS session_messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            msg_type TEXT NOT NULL DEFAULT 'text',
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS session_outputs (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            output_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        )
    """)
    await db.commit()
    await db.close()


async def get_connection() -> aiosqlite.Connection:
    return await aiosqlite.connect(str(DATABASE_PATH))


class SessionRepository:
    @staticmethod
    async def create_session() -> Session:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        session_id = str(uuid.uuid4())
        session = Session(
            id=session_id,
            created_at=now,
            updated_at=now,
            user_goal="",
        )
        db = await get_connection()
        await db.execute(
            "INSERT INTO sessions (id, created_at, updated_at, user_goal) VALUES (?, ?, ?, ?)",
            (session.id, session.created_at, session.updated_at, session.user_goal),
        )
        await db.commit()
        await db.close()
        return session

    @staticmethod
    async def get_session(session_id: str) -> Optional[Session]:
        db = await get_connection()
        cursor = await db.execute(
            "SELECT id, created_at, updated_at, user_goal FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        await db.close()
        if row:
            return Session(
                id=row[0], created_at=row[1], updated_at=row[2], user_goal=row[3]
            )
        return None

    @staticmethod
    async def list_sessions() -> list[Session]:
        db = await get_connection()
        cursor = await db.execute(
            "SELECT id, created_at, updated_at, user_goal FROM sessions ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        await db.close()
        return [
            Session(id=row[0], created_at=row[1], updated_at=row[2], user_goal=row[3])
            for row in rows
        ]

    @staticmethod
    async def update_goal(session_id: str, goal: str):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        db = await get_connection()
        await db.execute(
            "UPDATE sessions SET user_goal = ?, updated_at = ? WHERE id = ?",
            (goal, now, session_id),
        )
        await db.commit()
        await db.close()

    @staticmethod
    async def delete_session(session_id: str):
        db = await get_connection()
        await db.execute(
            "DELETE FROM session_files WHERE session_id = ?", (session_id,)
        )
        await db.execute(
            "DELETE FROM session_context WHERE session_id = ?", (session_id,)
        )
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
        await db.close()


class SessionFileRepository:
    @staticmethod
    async def create_file(
        session_id: str, file_name: str, file_path: str, file_type: str
    ) -> SessionFile:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        file_id = str(uuid.uuid4())
        sf = SessionFile(
            id=file_id,
            session_id=session_id,
            file_name=file_name,
            file_path=file_path,
            file_type=file_type,
            uploaded_at=now,
        )
        db = await get_connection()
        await db.execute(
            "INSERT INTO session_files (id, session_id, file_name, file_path, file_type, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                sf.id,
                sf.session_id,
                sf.file_name,
                sf.file_path,
                sf.file_type,
                sf.uploaded_at,
            ),
        )
        await db.commit()
        await db.close()
        return sf

    @staticmethod
    async def get_files_by_session(session_id: str) -> list[SessionFile]:
        db = await get_connection()
        cursor = await db.execute(
            "SELECT id, session_id, file_name, file_path, file_type, uploaded_at FROM session_files WHERE session_id = ?",
            (session_id,),
        )
        rows = await cursor.fetchall()
        await db.close()
        return [
            SessionFile(
                id=row[0],
                session_id=row[1],
                file_name=row[2],
                file_path=row[3],
                file_type=row[4],
                uploaded_at=row[5],
            )
            for row in rows
        ]

    @staticmethod
    async def get_all_files() -> list[SessionFile]:
        db = await get_connection()
        cursor = await db.execute(
            "SELECT id, session_id, file_name, file_path, file_type, uploaded_at FROM session_files ORDER BY uploaded_at DESC"
        )
        rows = await cursor.fetchall()
        await db.close()
        return [
            SessionFile(
                id=row[0],
                session_id=row[1],
                file_name=row[2],
                file_path=row[3],
                file_type=row[4],
                uploaded_at=row[5],
            )
            for row in rows
        ]

    @staticmethod
    async def get_file_by_id(file_id: str) -> Optional[SessionFile]:
        db = await get_connection()
        cursor = await db.execute(
            "SELECT id, session_id, file_name, file_path, file_type, uploaded_at FROM session_files WHERE id = ?",
            (file_id,),
        )
        row = await cursor.fetchone()
        await db.close()
        if row:
            return SessionFile(
                id=row[0],
                session_id=row[1],
                file_name=row[2],
                file_path=row[3],
                file_type=row[4],
                uploaded_at=row[5],
            )
        return None

    @staticmethod
    async def get_files_by_name(file_name: str) -> list[SessionFile]:
        db = await get_connection()
        cursor = await db.execute(
            "SELECT id, session_id, file_name, file_path, file_type, uploaded_at FROM session_files WHERE file_name = ?",
            (file_name,),
        )
        rows = await cursor.fetchall()
        await db.close()
        return [
            SessionFile(
                id=row[0],
                session_id=row[1],
                file_name=row[2],
                file_path=row[3],
                file_type=row[4],
                uploaded_at=row[5],
            )
            for row in rows
        ]

    @staticmethod
    async def delete_file(file_id: str):
        db = await get_connection()
        await db.execute("DELETE FROM session_files WHERE id = ?", (file_id,))
        await db.commit()
        await db.close()


class SessionContextRepository:
    @staticmethod
    async def set_context(session_id: str, key: str, value: str):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        context_id = str(uuid.uuid4())
        db = await get_connection()
        await db.execute(
            "INSERT INTO session_context (id, session_id, key, value, created_at) VALUES (?, ?, ?, ?, ?)",
            (context_id, session_id, key, value, now),
        )
        await db.commit()
        await db.close()

    @staticmethod
    async def get_context(session_id: str) -> dict[str, str]:
        db = await get_connection()
        cursor = await db.execute(
            "SELECT key, value FROM session_context WHERE session_id = ?",
            (session_id,),
        )
        rows = await cursor.fetchall()
        await db.close()
        return {row[0]: row[1] for row in rows}

    @staticmethod
    async def clear_context(session_id: str):
        db = await get_connection()
        await db.execute(
            "DELETE FROM session_context WHERE session_id = ?", (session_id,)
        )
        await db.commit()
        await db.close()


class TaskRepository:
    @staticmethod
    async def create_task(
        session_id: str,
        user_input: str,
        inferred_intent: str,
        tools_used: str,
        status: str = "pending",
    ) -> Task:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            session_id=session_id,
            user_input=user_input,
            inferred_intent=inferred_intent,
            tools_used=tools_used,
            status=status,
            created_at=now,
        )
        db = await get_connection()
        await db.execute(
            "INSERT INTO tasks (id, session_id, user_input, inferred_intent, tools_used, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                task.id,
                task.session_id,
                task.user_input,
                task.inferred_intent,
                task.tools_used,
                task.status,
                task.created_at,
            ),
        )
        await db.commit()
        await db.close()
        return task

    @staticmethod
    async def get_recent_tasks(limit: int = 50) -> list[dict]:
        db = await get_connection()
        cursor = await db.execute(
            "SELECT id, session_id, user_input, inferred_intent, tools_used, status, created_at FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        await db.close()
        return [
            {
                "task_id": row[0],
                "session_id": row[1],
                "user_input": row[2],
                "inferred_intent": row[3],
                "tools_used": row[4],
                "status": row[5],
                "timestamp": row[6],
            }
            for row in rows
        ]

    @staticmethod
    async def update_task_status(task_id: str, status: str):
        db = await get_connection()
        await db.execute(
            "UPDATE tasks SET status = ? WHERE id = ?",
            (status, task_id),
        )
        await db.commit()
        await db.close()

    @staticmethod
    async def update_task(task_id: str, inferred_intent: str, tools_used: str):
        db = await get_connection()
        await db.execute(
            "UPDATE tasks SET inferred_intent = ?, tools_used = ? WHERE id = ?",
            (inferred_intent, tools_used, task_id),
        )
        await db.commit()
        await db.close()


class MessageRepository:
    @staticmethod
    async def save_message(
        session_id: str, role: str, content: str, msg_type: str = "text"
    ) -> SessionMessage:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        msg_id = str(uuid.uuid4())
        msg = SessionMessage(
            id=msg_id,
            session_id=session_id,
            role=role,
            content=content,
            msg_type=msg_type,
            created_at=now,
        )
        db = await get_connection()
        await db.execute(
            "INSERT INTO session_messages (id, session_id, role, content, msg_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (msg.id, msg.session_id, msg.role, msg.content, msg.msg_type, msg.created_at),
        )
        await db.commit()
        await db.close()
        return msg

    @staticmethod
    async def get_messages(session_id: str) -> list[dict]:
        db = await get_connection()
        cursor = await db.execute(
            "SELECT id, session_id, role, content, msg_type, created_at FROM session_messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        )
        rows = await cursor.fetchall()
        await db.close()
        return [
            {
                "id": row[0],
                "role": row[2],
                "content": row[3],
                "type": row[4],
            }
            for row in rows
        ]

    @staticmethod
    async def save_output(session_id: str, output_json: str) -> SessionOutput:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        output_id = str(uuid.uuid4())
        output = SessionOutput(
            id=output_id,
            session_id=session_id,
            output_json=output_json,
            created_at=now,
        )
        db = await get_connection()
        # Upsert: delete old output for this session and insert new one
        await db.execute(
            "DELETE FROM session_outputs WHERE session_id = ?", (session_id,)
        )
        await db.execute(
            "INSERT INTO session_outputs (id, session_id, output_json, created_at) VALUES (?, ?, ?, ?)",
            (output.id, output.session_id, output.output_json, output.created_at),
        )
        await db.commit()
        await db.close()
        return output

    @staticmethod
    async def get_latest_output(session_id: str) -> Optional[str]:
        db = await get_connection()
        cursor = await db.execute(
            "SELECT output_json FROM session_outputs WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        )
        row = await cursor.fetchone()
        await db.close()
        if row:
            return row[0]
        return None
