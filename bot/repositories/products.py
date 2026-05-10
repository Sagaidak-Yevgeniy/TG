from __future__ import annotations

from typing import Any

from bot.database import Database


class ProductRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create(self, data: dict[str, Any]) -> int:
        fields = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        async with await self.db.connect() as conn:
            cursor = await conn.execute(
                f"INSERT INTO products ({fields}) VALUES ({placeholders})",
                tuple(data.values()),
            )
            await conn.commit()
            return int(cursor.lastrowid)

    async def list_active(self):
        return await self.db.fetchall("SELECT * FROM products WHERE is_active = 1 ORDER BY category, subcategory, title")

    async def get(self, product_id: int):
        return await self.db.fetchone("SELECT * FROM products WHERE id = ? AND is_active = 1", (product_id,))

    async def categories(self):
        return await self.db.fetchall("SELECT DISTINCT category FROM products WHERE is_active = 1 ORDER BY category")

    async def subcategories(self, category: str):
        return await self.db.fetchall(
            "SELECT DISTINCT subcategory FROM products WHERE category = ? AND is_active = 1 ORDER BY subcategory",
            (category,),
        )

    async def optimization_types(self, category: str, subcategory: str):
        return await self.db.fetchall(
            """
            SELECT DISTINCT optimization_type
            FROM products
            WHERE category = ? AND subcategory = ? AND is_active = 1
            ORDER BY optimization_type
            """,
            (category, subcategory),
        )

    async def by_path(self, category: str, subcategory: str, optimization_type: str):
        return await self.db.fetchall(
            """
            SELECT *
            FROM products
            WHERE category = ? AND subcategory = ? AND optimization_type = ? AND is_active = 1
            ORDER BY badge DESC, title
            """,
            (category, subcategory, optimization_type),
        )

    async def count(self) -> int:
        row = await self.db.fetchone("SELECT COUNT(*) AS count FROM products")
        return int(row["count"])

    async def distinct_values(self, column: str):
        allowed = {"category", "subcategory", "optimization_type", "game", "badge"}
        if column not in allowed:
            raise ValueError(f"Unsupported column: {column}")
        return await self.db.fetchall(
            f"SELECT DISTINCT {column} AS value FROM products WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}"
        )
