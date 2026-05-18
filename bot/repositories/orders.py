from __future__ import annotations

from bot.database import Database


class OrderRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def has_purchase(self, user_id: int, product_id: int) -> bool:
        row = await self.db.fetchone(
            "SELECT id FROM purchases WHERE user_id = ? AND product_id = ? LIMIT 1",
            (user_id, product_id),
        )
        return row is not None

    async def add_purchase(
        self,
        user_id: int,
        product_id: int,
        amount: int,
        amount_currency: str,
        provider: str,
        payload: str | None = None,
        original_amount: int | None = None,
        discount_percent: int = 0,
        promo_code: str | None = None,
    ) -> int | None:
        if await self.has_purchase(user_id, product_id):
            return None
        async with self.db.connect() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO purchases
                    (user_id, product_id, original_amount, discount_percent, promo_code, amount, amount_currency, provider, payment_payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, product_id, original_amount or amount, discount_percent, promo_code, amount, amount_currency, provider, payload),
            )
            await conn.commit()
            purchase_id = int(cursor.lastrowid)
        await self.db.execute(
            "UPDATE users SET purchases_count = purchases_count + 1 WHERE telegram_id = ?",
            (user_id,),
        )
        return purchase_id

    async def purchase_history(self, user_id: int):
        return await self.db.fetchall(
            """
            SELECT
                purchases.id,
                purchases.product_id,
                p.title,
                p.price,
                p.price_currency,
                p.photo_path,
                p.photo_file_id,
                purchases.amount,
                purchases.amount_currency,
                purchases.discount_percent,
                purchases.promo_code,
                purchases.provider,
                purchases.created_at
            FROM purchases
            JOIN products p ON p.id = purchases.product_id
            WHERE purchases.user_id = ?
            ORDER BY purchases.created_at DESC
            """,
            (user_id,),
        )

    async def list_sales(self):
        return await self.db.fetchall(
            """
            SELECT purchases.id, purchases.user_id, products.title, purchases.amount, purchases.amount_currency, purchases.discount_percent, purchases.promo_code, purchases.provider, purchases.created_at
            FROM purchases
            JOIN products ON products.id = purchases.product_id
            ORDER BY purchases.created_at DESC
            LIMIT 100
            """
        )

    async def has_demo(self, user_id: int, product_id: int) -> bool:
        row = await self.db.fetchone(
            "SELECT 1 FROM demo_downloads WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        )
        return row is not None

    async def add_demo(self, user_id: int, product_id: int) -> None:
        await self.db.execute(
            "INSERT OR IGNORE INTO demo_downloads (user_id, product_id) VALUES (?, ?)",
            (user_id, product_id),
        )

    async def create_crypto_invoice(self, invoice_id: str, user_id: int, product_id: int, amount: int, amount_currency: str, promo_code: str | None = None) -> None:
        await self.db.execute(
            """
            INSERT OR REPLACE INTO crypto_invoices (invoice_id, user_id, product_id, amount, amount_currency, promo_code, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (invoice_id, user_id, product_id, amount, amount_currency, promo_code),
        )

    async def get_crypto_invoice(self, invoice_id: str):
        return await self.db.fetchone("SELECT * FROM crypto_invoices WHERE invoice_id = ?", (invoice_id,))

    async def mark_crypto_paid(self, invoice_id: str) -> None:
        await self.db.execute("UPDATE crypto_invoices SET status = 'paid' WHERE invoice_id = ?", (invoice_id,))
