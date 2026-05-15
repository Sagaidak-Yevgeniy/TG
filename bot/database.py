from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def connect(self) -> aiosqlite.Connection:
        db = await aiosqlite.connect(self.path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        return db

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        async with await self.connect() as db:
            await db.execute(query, params)
            await db.commit()

    async def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
        async with await self.connect() as db:
            cursor = await db.execute(query, params)
            return await cursor.fetchone()

    async def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        async with await self.connect() as db:
            cursor = await db.execute(query, params)
            return await cursor.fetchall()


async def init_db(db: Database) -> None:
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        telegram_id INTEGER PRIMARY KEY,
        registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        purchases_count INTEGER NOT NULL DEFAULT 0,
        balance INTEGER NOT NULL DEFAULT 0,
        balance_rub INTEGER NOT NULL DEFAULT 0,
        total_topup_stars INTEGER NOT NULL DEFAULT 0,
        total_topup_rub INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        optimization_type TEXT NOT NULL,
        game TEXT,
        price INTEGER NOT NULL,
        badge TEXT,
        before_fps INTEGER NOT NULL,
        after_fps INTEGER NOT NULL,
        photo_path TEXT,
        screenshot_path TEXT,
        full_file_path TEXT NOT NULL,
        demo_file_path TEXT NOT NULL,
        is_extra INTEGER NOT NULL DEFAULT 0,
        restore_file_path TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        original_amount INTEGER,
        discount_percent INTEGER NOT NULL DEFAULT 0,
        promo_code TEXT,
        amount INTEGER NOT NULL,
        provider TEXT NOT NULL,
        payment_payload TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(telegram_id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS demo_downloads (
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, product_id),
        FOREIGN KEY(user_id) REFERENCES users(telegram_id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        scope_type TEXT NOT NULL,
        scope_value TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        next_delivery_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(telegram_id)
    );

    CREATE TABLE IF NOT EXISTS crypto_invoices (
        invoice_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        promo_code TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS topups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        balance_type TEXT NOT NULL,
        amount INTEGER NOT NULL,
        provider TEXT NOT NULL,
        payment_payload TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(telegram_id)
    );

    CREATE TABLE IF NOT EXISTS topup_crypto_invoices (
        invoice_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        balance_type TEXT NOT NULL,
        amount INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS promo_codes (
        code TEXT PRIMARY KEY,
        discount_percent INTEGER NOT NULL,
        expires_at TEXT,
        usage_limit INTEGER,
        used_count INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS promo_redemptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        purchase_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(code) REFERENCES promo_codes(code)
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(telegram_id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    );

    CREATE TABLE IF NOT EXISTS section_photos (
        section_key TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_id TEXT,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """
    async with await db.connect() as conn:
        await conn.executescript(schema)
        await _apply_migrations(conn)
        await conn.commit()


async def _apply_migrations(conn: aiosqlite.Connection) -> None:
    """Small SQLite migrations for databases created by earlier project versions."""
    table_columns = {
        "purchases": {
            "original_amount": "INTEGER",
            "discount_percent": "INTEGER NOT NULL DEFAULT 0",
            "promo_code": "TEXT",
        },
        "crypto_invoices": {
            "promo_code": "TEXT",
        },
        "users": {
            "balance_rub": "INTEGER NOT NULL DEFAULT 0",
            "total_topup_stars": "INTEGER NOT NULL DEFAULT 0",
            "total_topup_rub": "INTEGER NOT NULL DEFAULT 0",
        },
    }

    for table, columns in table_columns.items():
        cursor = await conn.execute(f"PRAGMA table_info({table})")
        existing = {row["name"] for row in await cursor.fetchall()}
        for column, definition in columns.items():
            if column not in existing:
                await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
