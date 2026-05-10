from __future__ import annotations

from pathlib import Path

from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, Message

from bot.repositories.section_photos import SectionPhotoRepository


async def answer_section(
    message: Message,
    section_photos: SectionPhotoRepository,
    section_key: str,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    photo = await section_photos.get(section_key)
    if photo and Path(photo["file_path"]).exists():
        await message.answer_photo(FSInputFile(photo["file_path"]), caption=text, reply_markup=reply_markup)
    else:
        await message.answer(text, reply_markup=reply_markup)


async def edit_section(
    callback: CallbackQuery,
    section_photos: SectionPhotoRepository,
    section_key: str,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    photo = await section_photos.get(section_key)
    if photo and Path(photo["file_path"]).exists():
        await callback.message.answer_photo(FSInputFile(photo["file_path"]), caption=text, reply_markup=reply_markup)
        await callback.message.delete()
    else:
        await callback.message.edit_text(text, reply_markup=reply_markup)
