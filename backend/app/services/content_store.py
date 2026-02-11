"""Content store service for unified content management."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

from app.models.content_item import ContentItem, SourceType
from app.services.vector_memory import get_vector_memory_service
from app.db.schema import get_connection


class ContentStore:
    def __init__(self):
        self.vector_service = get_vector_memory_service()

    async def add_pdf(
        self,
        content: str,
        file_path: str,
        title: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ContentItem:
        if title is None:
            title = Path(file_path).name
        item = await self._create_content_item(
            source_type=SourceType.PDF,
            title=title,
            content=content,
            session_id=session_id,
            file_path=file_path,
        )
        return item

    async def add_email(
        self,
        subject: str,
        sender: str,
        body: str,
        recipients: Optional[List[str]] = None,
        thread_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        session_id: Optional[str] = None,
    ) -> ContentItem:
        item = await self._create_content_item(
            source_type=SourceType.EMAIL,
            title=subject,
            content=body,
            session_id=session_id,
            sender=sender,
            recipients=recipients or [],
            thread_id=thread_id,
            timestamp=timestamp,
        )
        return item

    async def add_message(
        self,
        content: str,
        sender: str,
        title: Optional[str] = None,
        recipients: Optional[List[str]] = None,
        thread_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        session_id: Optional[str] = None,
    ) -> ContentItem:
        item = await self._create_content_item(
            source_type=SourceType.MESSAGE,
            title=title or "Message",
            content=content,
            session_id=session_id,
            sender=sender,
            recipients=recipients or [],
            thread_id=thread_id,
            timestamp=timestamp,
        )
        return item

    async def add_research(
        self,
        query: str,
        result: Dict[str, Any],
        title: Optional[str] = None,
        thread_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ContentItem:
        content = json.dumps(result, indent=2)
        item = await self._create_content_item(
            source_type=SourceType.RESEARCH,
            title=title or f"Research: {query}",
            content=content,
            session_id=session_id,
            thread_id=thread_id,
            metadata={"query": query},
        )
        return item

    async def add_note(
        self,
        title: str,
        content: str,
        thread_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContentItem:
        item = await self._create_content_item(
            source_type=SourceType.NOTE,
            title=title,
            content=content,
            session_id=session_id,
            thread_id=thread_id,
            metadata=metadata or {},
        )
        return item

    async def _create_content_item(
        self,
        source_type: SourceType,
        title: str,
        content: str,
        session_id: Optional[str] = None,
        file_path: Optional[str] = None,
        sender: Optional[str] = None,
        recipients: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContentItem:
        item_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        item = ContentItem(
            id=item_id,
            session_id=session_id,
            source_type=source_type,
            title=title,
            content=content,
            metadata=metadata or {},
            file_path=file_path,
            sender=sender,
            recipients=recipients,
            timestamp=timestamp or now,
            thread_id=thread_id,
        )

        embedding_text = f"{title}\n\n{content}"
        self.vector_service.add_to_memory(embedding_text)
        embedding_id = self.vector_service.get_vector_count() - 1

        item.embedded_at = now
        item.embedding_id = embedding_id

        await self._persist_item(item)
        return item

    async def _persist_item(self, item: ContentItem):
        db = await get_connection()

        await db.execute("""
            CREATE TABLE IF NOT EXISTS content_items (
                id TEXT PRIMARY KEY, session_id TEXT, source_type TEXT NOT NULL,
                title TEXT NOT NULL, content TEXT NOT NULL, metadata TEXT NOT NULL,
                file_path TEXT, sender TEXT, recipients TEXT, timestamp TEXT,
                thread_id TEXT, embedded_at TEXT, embedding_id INTEGER
            )
        """)

        await db.execute(
            """
            INSERT INTO content_items 
            (id, session_id, source_type, title, content, metadata, file_path, 
             sender, recipients, timestamp, thread_id, embedded_at, embedding_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                item.id,
                item.session_id,
                item.source_type.value,
                item.title,
                item.content,
                json.dumps(item.metadata),
                item.file_path,
                item.sender,
                json.dumps(item.recipients) if item.recipients else None,
                item.timestamp.isoformat() if item.timestamp else None,
                item.thread_id,
                item.embedded_at.isoformat() if item.embedded_at else None,
                item.embedding_id,
            ),
        )

        await db.commit()
        await db.close()

    async def add(self, item: ContentItem) -> str:
        if not item.id:
            item.id = str(uuid.uuid4())
        if not item.embedded_at:
            embedding_text = f"{item.title}\n\n{item.content}"
            self.vector_service.add_to_memory(embedding_text)
            item.embedding_id = self.vector_service.get_vector_count() - 1
            item.embedded_at = datetime.now(timezone.utc)
        await self._persist_item(item)
        return item.id

    async def get_by_id(self, item_id: str) -> Optional[ContentItem]:
        db = await get_connection()
        cursor = await db.execute(
            """SELECT id, session_id, source_type, title, content, metadata, 
               file_path, sender, recipients, timestamp, thread_id, 
               embedded_at, embedding_id FROM content_items WHERE id = ?""",
            (item_id,),
        )
        row = await cursor.fetchone()
        await db.close()
        return self._row_to_content_item(row) if row else None

    async def query_by_source(self, source_type: SourceType) -> List[ContentItem]:
        db = await get_connection()
        cursor = await db.execute(
            """SELECT id, session_id, source_type, title, content, metadata, 
               file_path, sender, recipients, timestamp, thread_id, 
               embedded_at, embedding_id FROM content_items WHERE source_type = ? ORDER BY timestamp DESC""",
            (source_type.value,),
        )
        rows = await cursor.fetchall()
        await db.close()
        return [self._row_to_content_item(row) for row in rows]

    async def query_by_thread(self, thread_id: str) -> List[ContentItem]:
        db = await get_connection()
        cursor = await db.execute(
            """SELECT id, session_id, source_type, title, content, metadata, 
               file_path, sender, recipients, timestamp, thread_id, 
               embedded_at, embedding_id FROM content_items WHERE thread_id = ? ORDER BY timestamp ASC""",
            (thread_id,),
        )
        rows = await cursor.fetchall()
        await db.close()
        return [self._row_to_content_item(row) for row in rows]

    async def query_by_session(self, session_id: str) -> List[ContentItem]:
        db = await get_connection()
        cursor = await db.execute(
            """SELECT id, session_id, source_type, title, content, metadata, 
               file_path, sender, recipients, timestamp, thread_id, 
               embedded_at, embedding_id FROM content_items WHERE session_id = ? ORDER BY timestamp DESC""",
            (session_id,),
        )
        rows = await cursor.fetchall()
        await db.close()
        return [self._row_to_content_item(row) for row in rows]

    async def query_semantic(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[ContentItem]:
        """Perform semantic search across all content using vector embeddings.

        1. Embed the query using Cohere
        2. Search FAISS index for similar content
        3. Match results back to ContentItems via text similarity
        4. Return top_k results sorted by relevance

        Args:
            query: Natural language search query
            top_k: Maximum number of results to return (default 5)

        Returns:
            List of ContentItems sorted by semantic similarity
        """
        vector_results = self.vector_service.query_memory(query, top_k * 2)

        if not vector_results:
            return []

        db = await get_connection()

        results = []
        seen_ids = set()

        for text_chunk in vector_results:
            cursor = await db.execute(
                """SELECT id, session_id, source_type, title, content, metadata, 
                   file_path, sender, recipients, timestamp, thread_id, 
                   embedded_at, embedding_id FROM content_items 
                   WHERE content LIKE ? OR title LIKE ? LIMIT 1""",
                (f"%{text_chunk[:100]}%", f"%{text_chunk[:100]}%"),
            )
            row = await cursor.fetchone()
            if row:
                item = self._row_to_content_item(row)
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    results.append(item)
                    if len(results) >= top_k:
                        break

        await db.close()
        return results

    def _row_to_content_item(self, row: tuple) -> ContentItem:
        """Convert database row to ContentItem."""
        return ContentItem(
            id=row[0],
            session_id=row[1],
            source_type=SourceType(row[2]),
            title=row[3],
            content=row[4],
            metadata=json.loads(row[5]) if row[5] else {},
            file_path=row[6],
            sender=row[7],
            recipients=json.loads(row[8]) if row[8] else None,
            timestamp=datetime.fromisoformat(row[9]) if row[9] else None,
            thread_id=row[10],
            embedded_at=datetime.fromisoformat(row[11]) if row[11] else None,
            embedding_id=row[12],
        )


def create_content_store() -> ContentStore:
    """Create ContentStore instance."""
    return ContentStore()
