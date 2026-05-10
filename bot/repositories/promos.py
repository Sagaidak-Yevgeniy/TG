from __future__ import annotations

from datetime import datetime

from bot.database import Database


class PromoRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create(self, code: str, discount_percent: int, expires_at: str | None, usage_limit: int | None) -> None:
        await self.db.execute(
            """
            INSERT OR REPLACE INTO promo_codes (code, discount_percent, expires_at, usage_limit, used_count, is_active)
            VALUES (?, ?, ?, ?, COALESCE((SELECT used_count FROM promo_codes WHERE code = ?), 0), 1)
            """,
            (code.upper(), discount_percent, expires_at, usage_limit, code.upper()),
        )

    async def list_all(self):
        return await self.db.fetchall("SELECT * FROM promo_codes ORDER BY created_at DESC")

    async def get(self, code: str):
        return await self.db.fetchone("SELECT * FROM promo_codes WHERE code = ?", (code.upper(),))

    async def set_active(self, code: str, is_active: bool) -> None:
        await self.db.execute("UPDATE promo_codes SET is_active = ? WHERE code = ?", (1 if is_active else 0, code.upper()))

    async def delete(self, code: str) -> None:
        await self.db.execute("DELETE FROM promo_redemptions WHERE code = ?", (code.upper(),))
        await self.db.execute("DELETE FROM promo_codes WHERE code = ?", (code.upper(),))

    async def validate(self, code: str):
        promo = await self.get(code)
        if not promo:
            return None, "Промокод не найден."
        if not promo["is_active"]:
            return None, "Промокод отключён."
        if promo["expires_at"]:
            try:
                expires_at = datetime.fromisoformat(promo["expires_at"])
            except ValueError:
                return None, "У промокода неверный срок действия. Обратитесь в поддержку."
            if expires_at < datetime.now():
                return None, "Срок действия промокода истёк."
        if promo["usage_limit"] is not None and promo["used_count"] >= promo["usage_limit"]:
            return None, "Лимит использований промокода уже исчерпан."
        return promo, None

    async def redeem(self, code: str, user_id: int, product_id: int, purchase_id: int | None = None) -> None:
        promo = await self.get(code)
        if not promo:
            return
        await self.db.execute(
            """
            INSERT INTO promo_redemptions (code, user_id, product_id, purchase_id)
            VALUES (?, ?, ?, ?)
            """,
            (code.upper(), user_id, product_id, purchase_id),
        )
        await self.db.execute(
            "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?",
            (code.upper(),),
        )


def apply_discount(price: int, discount_percent: int) -> int:
    if discount_percent <= 0:
        return price
    discounted = round(price * (100 - discount_percent) / 100)
    return max(1, discounted)
