from __future__ import annotations

from bot.database import Database


class SectionPhotoRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def set_photo(self, section_key: str, title: str, file_path: str, file_id: str | None) -> None:
        await self.db.execute(
            """
            INSERT INTO section_photos (section_key, title, file_path, file_id, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(section_key) DO UPDATE SET
                title = excluded.title,
                file_path = excluded.file_path,
                file_id = excluded.file_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (section_key, title, file_path, file_id),
        )

    async def get(self, section_key: str):
        return await self.db.fetchone("SELECT * FROM section_photos WHERE section_key = ?", (section_key,))

    async def delete(self, section_key: str) -> None:
        await self.db.execute("DELETE FROM section_photos WHERE section_key = ?", (section_key,))

    async def list_all(self):
        return await self.db.fetchall("SELECT * FROM section_photos ORDER BY section_key")
