from __future__ import annotations

from bot.database import Database


class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_or_create(self, telegram_id: int, username: str | None = None):
        user = await self.db.fetchone("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        if user:
            if username and user["username"] != username:
                await self.db.execute("UPDATE users SET username = ? WHERE telegram_id = ?", (username, telegram_id))
                return await self.get(telegram_id)
            return user
        await self.db.execute("INSERT INTO users (telegram_id, username) VALUES (?, ?)", (telegram_id, username))
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
        await self.add_topup(telegram_id, "stars", amount, "manual", None)

    async def add_topup(
        self,
        telegram_id: int,
        balance_type: str,
        amount: int,
        provider: str,
        payload: str | None = None,
    ) -> None:
        if balance_type not in {"rub", "stars"}:
            raise ValueError("balance_type must be rub or stars")

        balance_column = "balance_rub" if balance_type == "rub" else "balance"
        topup_column = "total_topup_rub" if balance_type == "rub" else "total_topup_stars"
        await self.db.execute(
            f"UPDATE users SET {balance_column} = {balance_column} + ?, {topup_column} = {topup_column} + ? WHERE telegram_id = ?",
            (amount, amount, telegram_id),
        )

    async def grant_balance(
        self,
        telegram_id: int,
        balance_type: str,
        amount: int,
        admin_id: int,
    ) -> None:
        await self.get_or_create(telegram_id)
        await self.add_topup(telegram_id, balance_type, amount, "admin_grant", f"admin:{admin_id}")
        await self.db.execute(
            """
            INSERT INTO topups (user_id, balance_type, amount, provider, payment_payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (telegram_id, balance_type, amount, provider, payload),
        )

    async def purchase_totals(self, telegram_id: int) -> dict[str, int]:
        rows = await self.db.fetchall(
            """
            SELECT amount_currency, SUM(amount) AS total
            FROM purchases
            WHERE user_id = ?
            GROUP BY amount_currency
            """,
            (telegram_id,),
        )
        totals = {"rub": 0, "stars": 0}
        for row in rows:
            if row["amount_currency"] == "rub":
                totals["rub"] += int(row["total"] or 0)
            else:
                totals["stars"] += int(row["total"] or 0)
        return totals

    async def create_topup_crypto_invoice(self, invoice_id: str, user_id: int, balance_type: str, amount: int) -> None:
        await self.db.execute(
            """
            INSERT OR REPLACE INTO topup_crypto_invoices (invoice_id, user_id, balance_type, amount, status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (invoice_id, user_id, balance_type, amount),
        )

    async def get_topup_crypto_invoice(self, invoice_id: str):
        return await self.db.fetchone("SELECT * FROM topup_crypto_invoices WHERE invoice_id = ?", (invoice_id,))

    async def mark_topup_crypto_paid(self, invoice_id: str) -> None:
        await self.db.execute(
            "UPDATE topup_crypto_invoices SET status = 'paid' WHERE invoice_id = ?",
            (invoice_id,),
        )

    async def pending_topup_crypto_invoices(self):
        return await self.db.fetchall(
            "SELECT * FROM topup_crypto_invoices WHERE status = 'pending' ORDER BY created_at DESC LIMIT 100"
        )

    async def has_topup_payload(self, payload: str) -> bool:
        row = await self.db.fetchone(
            "SELECT 1 FROM topups WHERE payment_payload = ? LIMIT 1",
            (payload,),
        )
        return row is not None
