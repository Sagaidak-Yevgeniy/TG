from __future__ import annotations

from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from bot.services.media import is_url


async def send_file_or_notice(bot: Bot, chat_id: int, path: str | None, caption: str) -> None:
    if is_url(path):
        await bot.send_message(chat_id, f"{caption}\n\nСсылка на товар:\n{path}")
        return

    if path and Path(path).exists():
        await bot.send_document(chat_id, FSInputFile(path), caption=caption)
        return

    await bot.send_message(
        chat_id,
        f"{caption}\n\nФайл пока не найден на сервере: `{path or 'не указан'}`",
        parse_mode="Markdown",
    )
