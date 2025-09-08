from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional, Tuple

import aiosqlite

SCHEMA_SQL = """
             CREATE TABLE IF NOT EXISTS subscriptions
             (
                 id
                 INTEGER
                 PRIMARY
                 KEY
                 AUTOINCREMENT,
                 user_id
                 TEXT
                 NOT
                 NULL,
                 name
                 TEXT
                 NOT
                 NULL,
                 amount_cents
                 INTEGER
                 NOT
                 NULL,
                 day_of_month
                 INTEGER
                 NOT
                 NULL
                 CHECK
             (
                 day_of_month
                 BETWEEN
                 1
                 AND
                 28
             ),
                 active INTEGER NOT NULL DEFAULT 1,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                 );

             CREATE TABLE IF NOT EXISTS manual_expenses
             (
                 id
                 INTEGER
                 PRIMARY
                 KEY
                 AUTOINCREMENT,
                 user_id
                 TEXT
                 NOT
                 NULL,
                 name
                 TEXT
                 NOT
                 NULL,
                 amount_cents
                 INTEGER
                 NOT
                 NULL,
                 due_date
                 DATE
                 NOT
                 NULL,
                 paid
                 INTEGER
                 NOT
                 NULL
                 DEFAULT
                 0,
                 created_at
                 TIMESTAMP
                 DEFAULT
                 CURRENT_TIMESTAMP
             );

             CREATE TABLE IF NOT EXISTS balances
             (
                 user_id
                 TEXT
                 PRIMARY
                 KEY,
                 balance_cents
                 INTEGER
                 NOT
                 NULL
                 DEFAULT
                 0
             );

             CREATE TABLE IF NOT EXISTS user_reminders
             (
                 user_id
                 TEXT
                 PRIMARY
                 KEY,
                 mode
                 TEXT
                 NOT
                 NULL
                 CHECK (
                 mode
                 IN
             (
                 'dm',
                 'channel'
             )),
                 channel_id TEXT
                 ); \
             """


@dataclass(frozen=True)
class Subscription:
    id: int
    user_id: str
    name: str
    amount_cents: int
    day_of_month: int
    active: int


@dataclass(frozen=True)
class Expense:
    id: int
    user_id: str
    name: str
    amount_cents: int
    due_date: str
    paid: int


class BudgetService:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def ensure_schema(self) -> None:
        await self.conn.executescript(SCHEMA_SQL)
        await self.conn.commit()

    async def set_reminder_pref(self, user_id: int | str, mode: str, channel_id: int | str | None = None) -> None:
        mode = mode.lower()
        if mode not in ("dm", "channel"):
            raise ValueError("mode must be 'dm' or 'channel'")
        chan = str(channel_id) if channel_id is not None else None
        await self.conn.execute(
            "INSERT INTO user_reminders(user_id, mode, channel_id) VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET mode=excluded.mode, channel_id=excluded.channel_id",
            (str(user_id), mode, chan),
        )
        await self.conn.commit()

    async def get_reminder_pref(self, user_id: int | str) -> Optional[tuple[str, Optional[str]]]:
        async with self.conn.execute(
                "SELECT mode, channel_id FROM user_reminders WHERE user_id=?",
                (str(user_id),),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        return row[0], row[1]

    async def list_reminder_prefs(self) -> list[tuple[str, str, Optional[str]]]:
        async with self.conn.execute(
                "SELECT user_id, mode, channel_id FROM user_reminders",
        ) as cur:
            rows = await cur.fetchall()
        return [(str(r[0]), str(r[1]), (str(r[2]) if r[2] is not None else None)) for r in rows]

    async def add_subscription(self, user_id: int | str, name: str, amount_cents: int, day_of_month: int) -> None:
        await self.conn.execute(
            "INSERT INTO subscriptions (user_id, name, amount_cents, day_of_month) VALUES (?,?,?,?)",
            (str(user_id), name, amount_cents, int(day_of_month)),
        )
        await self.conn.commit()

    async def list_subscriptions(self, user_id: int | str) -> Iterable[Subscription]:
        async with self.conn.execute(
                "SELECT id, user_id, name, amount_cents, day_of_month, active FROM subscriptions WHERE user_id=? ORDER BY day_of_month, name",
                (str(user_id),),
        ) as cur:
            rows = await cur.fetchall()
        return [Subscription(*row) for row in rows]

    async def delete_subscription(self, user_id: int | str, sub_id: int) -> None:
        await self.conn.execute("DELETE FROM subscriptions WHERE id=? AND user_id=?", (sub_id, str(user_id)))
        await self.conn.commit()

    async def add_expense(self, user_id: int | str, name: str, amount_cents: int, due_date: str) -> None:
        await self.conn.execute(
            "INSERT INTO manual_expenses (user_id, name, amount_cents, due_date) VALUES (?,?,?,?)",
            (str(user_id), name, amount_cents, due_date),
        )
        await self.conn.commit()

    async def list_unpaid_expenses(self, user_id: int | str) -> Iterable[Expense]:
        async with self.conn.execute(
                "SELECT id, user_id, name, amount_cents, due_date, paid FROM manual_expenses WHERE user_id=? AND paid=0 ORDER BY due_date, name",
                (str(user_id),),
        ) as cur:
            rows = await cur.fetchall()
        return [Expense(*row) for row in rows]

    async def mark_expense_paid(self, user_id: int | str, expense_id: int) -> None:
        await self.conn.execute(
            "UPDATE manual_expenses SET paid=1 WHERE id=? AND user_id=?",
            (expense_id, str(user_id)),
        )
        await self.conn.commit()

    async def delete_expense(self, user_id: int | str, expense_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM manual_expenses WHERE id=? AND user_id=?",
            (expense_id, str(user_id)),
        )
        await self.conn.commit()

    async def get_balance(self, user_id: int | str) -> int:
        async with self.conn.execute(
                "SELECT balance_cents FROM balances WHERE user_id=?",
                (str(user_id),),
        ) as cur:
            row = await cur.fetchone()
        return int(row[0]) if row else 0

    async def set_balance(self, user_id: int | str, cents: int) -> None:
        await self.conn.execute(
            "INSERT INTO balances(user_id, balance_cents) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance_cents=excluded.balance_cents",
            (str(user_id), cents),
        )
        await self.conn.commit()

    async def add_to_balance(self, user_id: int | str, delta_cents: int) -> int:
        await self.conn.execute(
            "INSERT INTO balances(user_id, balance_cents) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance_cents=balance_cents+?",
            (str(user_id), delta_cents, delta_cents),
        )
        await self.conn.commit()
        return await self.get_balance(user_id)

    async def sub_from_balance(self, user_id: int | str, delta_cents: int) -> int:
        await self.conn.execute(
            "INSERT INTO balances(user_id, balance_cents) VALUES (?, 0) ON CONFLICT(user_id) DO UPDATE SET balance_cents=balance_cents-?",
            (str(user_id), delta_cents),
        )
        await self.conn.commit()
        return await self.get_balance(user_id)

    async def remaining_for_month(self, user_id: int | str, today: Optional[date] = None) -> Tuple[
        int, list[tuple[str, int, int]], list[tuple[str, int, str]]]:
        """Retourne (total_cents, subs_due, expenses_due)
        subs_due: liste de (name, amount_cents, day_of_month)
        expenses_due: liste de (name, amount_cents, due_date)
        """
        from datetime import datetime, timezone
        if today is None:
            today = datetime.now(timezone.utc).date()
        async with self.conn.execute(
                "SELECT name, amount_cents, day_of_month FROM subscriptions WHERE user_id=? AND active=1",
                (str(user_id),),
        ) as cur:
            subs = await cur.fetchall()
        subs_due = [(name, cents, dom) for (name, cents, dom) in subs if int(dom) >= int(today.day)]
        subs_total = sum(c for _, c, _ in subs_due)
        async with self.conn.execute(
                "SELECT name, amount_cents, due_date FROM manual_expenses WHERE user_id=? AND paid=0 AND due_date>=? AND substr(due_date,1,7)=?",
                (str(user_id), today.isoformat(), today.strftime("%Y-%m")),
        ) as cur:
            mans = await cur.fetchall()
        man_total = sum(r[1] for r in mans)
        total = subs_total + man_total
        return total, subs_due, mans
