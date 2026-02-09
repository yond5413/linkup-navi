"""Database connection utilities."""

import aiosqlite
from app.config import get_settings


async def get_db():
    settings = get_settings()
    db = await aiosqlite.connect(str(settings.db_path))
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """Initialize the database with schema."""
    from app.db.schema import init_db as _init_db

    await _init_db()
