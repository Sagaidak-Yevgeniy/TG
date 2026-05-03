from __future__ import annotations

from bot.database import Database


class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_or_create(self, telegram_id: int):
        user = await self.db.fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        if user:
            return user
        await self.db.execute("INSERT INTO users (telegram_id) VALUES (?)", (telegram_id,))
        return await self.db.fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))

    async def get(self, telegram_id: int):
        return await self.db.fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))

    async def list_users(self):
        return await self.db.fetchall("SELECT * FROM users ORDER BY registered_at DESC LIMIT 100")

    async def increment_purchases(self, telegram_id: int) -> None:
        await self.db.execute(
            "UPDATE users SET purchases_count = purchases_count + 1 WHERE telegram_id = ?",
            (telegram_id,),
        )

    async def add_balance(self, telegram_id: int, amount: int) -> None:
        await self.db.execute(
            "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
            (amount, telegram_id),
        )
