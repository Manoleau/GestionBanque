import aiosqlite
from typing import Optional

INIT_SQL = """
CREATE TABLE IF NOT EXISTS user_notes (
    user_id TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

class Database:
    def __init__(self, path: str):
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self._conn = await aiosqlite.connect(self.path)
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.execute(INIT_SQL)
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._conn

    async def add_note(self, user_id: int, note: str):
        await self.conn.execute(
            "INSERT INTO user_notes (user_id, note) VALUES (?, ?)",
            (str(user_id), note),
        )
        await self.conn.commit()

    async def list_notes(self, user_id: int):
        async with self.conn.execute(
            "SELECT note, created_at FROM user_notes WHERE user_id = ? ORDER BY created_at DESC",
            (str(user_id),),
        ) as cursor:
            return await cursor.fetchall()
