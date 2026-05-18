from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.keyboards.user import back_to_main, main_menu
from bot.repositories.section_photos import SectionPhotoRepository
from bot.repositories.users import UserRepository
from bot.services.section_display import answer_section, edit_section

router = Router()


@router.message(CommandStart())
async def start(message: Message, users: UserRepository, settings: Settings, section_photos: SectionPhotoRepository) -> None:
    await users.get_or_create(message.from_user.id, message.from_user.username)
    await answer_section(
        message,
        section_photos,
        "main",
        "Привет! Здесь можно купить файлы оптимизации ПК для игр, получить демо и выбрать подписку под свои задачи.",
        reply_markup=main_menu(message.from_user.id in settings.admin_ids),
    )


@router.callback_query(lambda c: c.data == "main")
async def main(callback: CallbackQuery, users: UserRepository, settings: Settings, section_photos: SectionPhotoRepository) -> None:
    await users.get_or_create(callback.from_user.id, callback.from_user.username)
    await edit_section(
        callback,
        section_photos,
        "main",
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


@router.callback_query(lambda c: c.data == "rules")
async def rules(callback: CallbackQuery, section_photos: SectionPhotoRepository) -> None:
    await edit_section(
        callback,
        section_photos,
        "rules",
        "📜 ПРАВИЛА STREETS SHOP\n\n"
        "1. Совершая покупку, пользователь автоматически соглашается с правилами магазина.\n\n"
        "2. Возврат средств возможен только в случае проблемы со стороны магазина.\n\n"
        "3. После выдачи товара ответственность за дальнейшее использование товара несёт покупатель.\n\n"
        "4. Запрещено пытаться обмануть магазин, подделывать доказательства или заниматься мошенничеством.\n\n"
        "5. Оскорбления, спам и неадекватное поведение в сторону администрации или поддержки запрещены.\n\n"
        "6. Время ответа поддержки может зависеть от загруженности, но администрация старается отвечать максимально быстро.\n\n"
        "7. Магазин имеет право отказать в обслуживании пользователю при нарушении правил.\n\n"
        "8. Все отзывы должны быть настоящими. Фейковые отзывы или попытки накрутки запрещены.\n\n"
        "9. Покупатель обязан внимательно читать описание товара перед покупкой.\n\n"
        "10. Перед покупкой рекомендуется проверить отзывы и при необходимости уточнить информацию у поддержки.\n\n"
        "11. Попытки слива товаров, перепродажи с целью обмана или распространения данных магазина запрещены.\n\n"
        "12. Правила могут обновляться или изменяться без предварительного уведомления.\n\n"
        "📞 Поддержка — @EndikEZZ",
        reply_markup=back_to_main(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "support")
async def support(callback: CallbackQuery, settings: Settings, section_photos: SectionPhotoRepository) -> None:
    await edit_section(
        callback,
        section_photos,
        "support",
        "💬 Поддержка / Помощь с выбором\n\n"
        f"Напишите администратору: {settings.support_username}\n"
        "Опишите процессор, видеокарту, ОЗУ, Windows и игру, для которой нужна оптимизация.",
        reply_markup=back_to_main(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "reviews")
async def reviews(callback: CallbackQuery, settings: Settings, section_photos: SectionPhotoRepository) -> None:
    await edit_section(
        callback,
        section_photos,
        "reviews",
        "⭐ Отзывы\n\n"
        f"Канал с отзывами, скриншотами результатов и примерами до/после:\n{settings.reviews_channel_url}",
        reply_markup=back_to_main(),
    )
    await callback.answer()
