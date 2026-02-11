"""Migration script to convert session_files to content_items.

Migrates existing file records from session_files table to the new
content_items unified storage system.
"""

import asyncio
from datetime import datetime, timezone
from typing import List

from app.db.schema import get_connection, SessionFile
from app.models.content_item import ContentItem, SourceType
from app.services.content_store import ContentStore


async def migrate_to_content_items():
    """Migrate existing session_files to content_items table.
    
    This migration:
    1. Reads all records from session_files table
    2. Converts PDF files to ContentItem records
    3. Stores them in content_items table with embeddings
    4. Deletes old session_files records (data not important)
    
    Returns:
        dict with migration statistics
    """
    db = await get_connection()
    
    # Get all existing session files
    cursor = await db.execute(
        "SELECT id, session_id, file_name, file_path, file_type, uploaded_at FROM session_files"
    )
    rows = await cursor.fetchall()
    
    if not rows:
        print("No session files to migrate")
        await db.close()
        return {"migrated": 0, "errors": 0}
    
    print(f"Found {len(rows)} session files to migrate")
    
    # Create ContentStore instance
    store = ContentStore()
    
    migrated = 0
    errors = 0
    
    for row in rows:
        try:
            file_id, session_id, file_name, file_path, file_type, uploaded_at = row
            
            # Only migrate PDF files (others can be added manually later)
            if file_type.lower() != 'pdf':
                print(f"Skipping non-PDF file: {file_name}")
                continue
            
            # Try to read PDF content
            content = ""
            try:
                from app.services.pdf_parser import PDFParser
                parser = PDFParser()
                content = parser.extract_text(file_path)
            except Exception as e:
                print(f"Warning: Could not extract text from {file_name}: {e}")
                content = f"[PDF file: {file_name}]"
            
            # Create ContentItem
            item = ContentItem(
                id=file_id,  # Preserve original ID
                session_id=session_id,
                source_type=SourceType.PDF,
                title=file_name,
                content=content,
                metadata={"migrated_from": "session_files", "original_file_type": file_type},
                file_path=file_path,
                timestamp=datetime.fromisoformat(uploaded_at.replace('Z', '+00:00')) if uploaded_at else datetime.now(timezone.utc),
                thread_id=None,
                embedded_at=None,
                embedding_id=None
            )
            
            # Store with auto-embedding
            await store.add(item)
            migrated += 1
            print(f"Migrated: {file_name}")
            
        except Exception as e:
            errors += 1
            print(f"Error migrating file {row[2] if len(row) > 2 else 'unknown'}: {e}")
    
    # Delete old session_files records (data not important per requirements)
    if migrated > 0:
        await db.execute("DELETE FROM session_files")
        print(f"Deleted {len(rows)} old session_files records")
    
    await db.commit()
    await db.close()
    
    print(f"\nMigration complete:")
    print(f"  - Migrated: {migrated}")
    print(f"  - Errors: {errors}")
    
    return {"migrated": migrated, "errors": errors}


async def main():
    """Main entry point for migration."""
    print("Starting session_files to content_items migration...")
    result = await migrate_to_content_items()
    print(f"\nResult: {result}")


if __name__ == "__main__":
    asyncio.run(main())
