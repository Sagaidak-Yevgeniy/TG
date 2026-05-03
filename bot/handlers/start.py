from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.keyboards.user import back_to_main, main_menu
from bot.repositories.users import UserRepository

router = Router()


@router.message(CommandStart())
async def start(message: Message, users: UserRepository, settings: Settings) -> None:
    await users.get_or_create(message.from_user.id)
    await message.answer(
        "Привет! Здесь можно купить файлы оптимизации ПК для игр, получить демо и выбрать подписку под свои задачи.",
        reply_markup=main_menu(message.from_user.id in settings.admin_ids),
    )


@router.callback_query(lambda c: c.data == "main")
async def main(callback: CallbackQuery, users: UserRepository, settings: Settings) -> None:
    await users.get_or_create(callback.from_user.id)
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_menu(callback.from_user.id in settings.admin_ids),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "faq")
async def faq(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📘 FAQ\n\n"
        "❓ Что это за файлы?\n"
        "Это готовые наборы настроек, конфигов и инструкций для повышения FPS, снижения задержки и стабилизации игр.\n\n"
        "❓ Безопасно ли это для системы?\n"
        "Обычные пакеты используют мягкие настройки. Экстро оптимизация отдельно предупреждает о рисках и содержит restore-файл.\n\n"
        "❓ Как установить оптимизацию?\n"
        "После покупки бот выдаёт файл и инструкцию. Перед применением рекомендуется создать точку восстановления Windows.\n\n"
        "❓ Чем отличается демо-версия от полной?\n"
        "Демо ограничено по функционалу и применяет не все настройки. Полный файл даёт больший прирост FPS и стабильности.",
        reply_markup=back_to_main(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "support")
async def support(callback: CallbackQuery, settings: Settings) -> None:
    await callback.message.edit_text(
        "💬 Поддержка / Помощь с выбором\n\n"
        f"Напишите администратору: {settings.support_username}\n"
        "Опишите процессор, видеокарту, ОЗУ, Windows и игру, для которой нужна оптимизация.",
        reply_markup=back_to_main(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "reviews")
async def reviews(callback: CallbackQuery, settings: Settings) -> None:
    await callback.message.edit_text(
        "⭐ Отзывы\n\n"
        f"Канал с отзывами, скриншотами результатов и примерами до/после:\n{settings.reviews_channel_url}",
        reply_markup=back_to_main(),
    )
    await callback.answer()
