from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aiogram import Bot
from aiogram.types import Message

from bot.config import Settings


async def save_message_photo(bot: Bot, message: Message, settings: Settings, folder: str) -> tuple[str, str]:
    if not message.photo:
        raise ValueError("Сообщение не содержит фото.")

    photo = message.photo[-1]
    target_dir = settings.assets_dir / "photos" / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid4().hex}.jpg"
    await bot.download(photo, destination=target)
    return str(Path(target)), photo.file_id


def is_url(value: str | None) -> bool:
    return bool(value and value.startswith(("http://", "https://", "tg://")))
