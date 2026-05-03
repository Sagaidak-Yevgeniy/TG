from __future__ import annotations

from bot.database import Database


class SubscriptionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create(self, user_id: int, scope_type: str, scope_value: str) -> None:
        await self.db.execute(
            """
            INSERT INTO subscriptions (user_id, scope_type, scope_value, next_delivery_at)
            VALUES (?, ?, ?, datetime('now', '+1 month'))
            """,
            (user_id, scope_type, scope_value),
        )

    async def active_for_user(self, user_id: int):
        return await self.db.fetchall(
            "SELECT * FROM subscriptions WHERE user_id = ? AND is_active = 1 ORDER BY started_at DESC",
            (user_id,),
        )

    async def list_active(self):
        return await self.db.fetchall(
            "SELECT * FROM subscriptions WHERE is_active = 1 ORDER BY started_at DESC LIMIT 100"
        )

    async def cancel(self, subscription_id: int) -> None:
        await self.db.execute("UPDATE subscriptions SET is_active = 0 WHERE id = ?", (subscription_id,))
