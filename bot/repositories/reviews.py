from __future__ import annotations

from bot.database import Database


class ReviewRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create(self, user_id: int, product_id: int, rating: int, comment: str) -> int:
        async with self.db.connect() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO reviews (user_id, product_id, rating, comment)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, product_id, rating, comment),
            )
            await conn.commit()
            return int(cursor.lastrowid)
