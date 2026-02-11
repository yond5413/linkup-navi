"""Database migration script for adding app_settings table."""

import asyncio
from app.db.schema import get_connection


async def migrate():
    db = await get_connection()
    await db.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    await db.commit()
    await db.close()
    print("Migration complete: app_settings table created")


if __name__ == "__main__":
    asyncio.run(migrate())
