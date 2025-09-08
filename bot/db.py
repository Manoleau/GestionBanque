from typing import Optional

import aiosqlite

INIT_SQL = """
-- Budget-related tables are created by the budget cog on_ready via executescript.
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
