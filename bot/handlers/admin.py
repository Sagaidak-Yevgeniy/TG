from __future__ import annotations

from datetime import datetime
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.config import Settings
from bot.keyboards.admin import (
    admin_menu,
    grant_balance_type,
    photo_step,
    promo_actions,
    promos as promos_keyboard,
    section_photo_actions,
    section_photo_targets,
    static_choice,
)
from bot.keyboards.user import back_to_main
from bot.repositories.orders import OrderRepository
from bot.repositories.products import ProductRepository
from bot.repositories.promos import PromoRepository
from bot.repositories.section_photos import SectionPhotoRepository
from bot.repositories.subscriptions import SubscriptionRepository
from bot.repositories.users import UserRepository
from bot.services.media import save_message_photo
from bot.states import AddProduct, GrantBalance, PromoCreate, SectionPhotoEdit
from bot.utils.callback_cache import get

router = Router()

DEFAULT_CATEGORIES = [
    ("🕹 Оптимизация для игр", "🕹 Оптимизация для игр"),
    ("⚙️ Настройки для приложений", "⚙️ Настройки для приложений"),
    ("📘 Гайды", "📘 Гайды"),
    ("🎮 Файлы от про-игроков", "🎮 Файлы от про-игроков"),
    ("⚠️ Экстро оптимизация", "⚠️ Экстро оптимизация"),
]
DEFAULT_SUBCATEGORIES = [
    ("🎯 CS2", "🎯 CS2"),
    ("🔫 Valorant", "🔫 Valorant"),
    ("🪖 Warzone", "🪖 Warzone"),
    ("🏰 Fortnite", "🏰 Fortnite"),
    ("🚗 GTA V", "🚗 GTA V"),
    ("➕ Другие игры", "➕ Другие игры"),
    ("🪟 Windows", "🪟 Windows"),
    ("🌐 Сеть и пинг", "🌐 Сеть и пинг"),
]
DEFAULT_TYPES = [
    ("⚡ FPS BOOST", "⚡ FPS BOOST"),
    ("🎯 LOW INPUT LAG", "🎯 LOW INPUT LAG"),
    ("🧠 STABILITY", "🧠 STABILITY"),
    ("🏆 COMPETITIVE PRESET", "🏆 COMPETITIVE PRESET"),
]
BADGES = [
    ("Без метки", ""),
    ("🔥 Популярное", "🔥 Популярное"),
    ("🆕 Новинка", "🆕 Новинка"),
    ("💎 Рекомендуем", "💎 Рекомендуем"),
]


def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


@router.callback_query(lambda c: c.data == "admin")
async def admin(callback: CallbackQuery, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.message.edit_text("🛠 Админ-панель", reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_products")
async def admin_products(callback: CallbackQuery, products: ProductRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    rows = await products.list_active()
    body = "\n".join(
        f"#{row['id']} {row['title']} — {row['category']} / {row['subcategory']} / {row['optimization_type']} — "
        f"{row['price']} {'₽' if row['price_currency'] == 'rub' else '⭐'}"
        for row in rows[:50]
    )
    text = f"📦 Товары\n\n{body}" if body else "📦 Товаров нет."
    await callback.message.edit_text(text or "Товаров нет.", reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_users")
async def admin_users(callback: CallbackQuery, users: UserRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    rows = await users.list_users()
    lines = ["👥 Пользователи\n"]
    for row in rows:
        lines.append(
            f"• {row['telegram_id']} @{row['username'] or '-'} | рег: {row['registered_at']} | покупки: {row['purchases_count']} | баланс: {row['balance']} ⭐ / {row['balance_rub']} ₽"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_sales")
async def admin_sales(callback: CallbackQuery, orders: OrderRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    rows = await orders.list_sales()
    lines = ["💰 Продажи\n"]
    for row in rows:
        lines.append(
            f"#{row['id']} | user {row['user_id']} | {row['title']} | {row['amount']} {'₽' if row['amount_currency'] == 'rub' else '⭐'} | "
            f"скидка {row['discount_percent']}% | {row['promo_code'] or '-'} | {row['provider']} | {row['created_at']}"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_subscriptions")
async def admin_subscriptions(callback: CallbackQuery, subscriptions_repo: SubscriptionRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    rows = await subscriptions_repo.list_active()
    lines = ["🔔 Активные подписки\n"]
    for row in rows:
        lines.append(
            f"#{row['id']} | user {row['user_id']} | {row['scope_type']}: {row['scope_value']} | next: {row['next_delivery_at']}"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_grant_balance")
async def admin_grant_balance(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await state.clear()
    await state.set_state(GrantBalance.user_id)
    await callback.message.edit_text("Введите Telegram ID пользователя, которому нужно выдать баланс:")
    await callback.answer()


@router.message(GrantBalance.user_id)
async def grant_user_id(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.isdigit():
        await message.answer("ID должен быть числом.")
        return
    await state.update_data(user_id=int(message.text))
    await state.set_state(GrantBalance.balance_type)
    await message.answer("Что выдать пользователю?", reply_markup=grant_balance_type())


@router.callback_query(GrantBalance.balance_type, lambda c: c.data.startswith("grant_type:"))
async def grant_type(callback: CallbackQuery, state: FSMContext) -> None:
    balance_type = callback.data.split(":")[1]
    await state.update_data(balance_type=balance_type)
    await state.set_state(GrantBalance.amount)
    suffix = "звёзд" if balance_type == "stars" else "рублей"
    await callback.message.edit_text(f"Введите количество {suffix}:")
    await callback.answer()


@router.message(GrantBalance.amount)
async def grant_amount(message: Message, state: FSMContext, users: UserRepository) -> None:
    if not message.text or not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Сумма должна быть положительным числом.")
        return
    data = await state.get_data()
    await users.grant_balance(data["user_id"], data["balance_type"], int(message.text), message.from_user.id)
    await state.clear()
    suffix = "⭐" if data["balance_type"] == "stars" else "₽"
    await message.answer(f"✅ Пользователю {data['user_id']} выдано {int(message.text)} {suffix}.", reply_markup=admin_menu())


@router.callback_query(lambda c: c.data == "admin_add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await state.clear()
    await state.set_state(AddProduct.title)
    await callback.message.edit_text("➕ Добавление товара\n\nВведите продающее название товара:")
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("Действие отменено.", reply_markup=admin_menu())
    await callback.answer()


@router.message(AddProduct.title)
async def add_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text)
    await state.set_state(AddProduct.description)
    await message.answer("Введите описание:")


@router.message(AddProduct.description)
async def add_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text)
    await state.set_state(AddProduct.category)
    await message.answer("Выберите раздел товара:", reply_markup=static_choice(DEFAULT_CATEGORIES, "add_category"))


@router.callback_query(AddProduct.category, lambda c: c.data.startswith("add_category:"))
async def add_category_choice(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 1)[1]
    if key == "custom":
        await callback.message.edit_text("Введите свой раздел одним сообщением:")
        await callback.answer()
        return
    value = get(key)
    if not value:
        await callback.answer("Кнопка устарела. Начните добавление товара заново.", show_alert=True)
        return
    await state.update_data(category=value)
    await state.set_state(AddProduct.subcategory)
    await callback.message.edit_text("Выберите подкатегорию или игру:", reply_markup=static_choice(DEFAULT_SUBCATEGORIES, "add_subcategory"))
    await callback.answer()


@router.message(AddProduct.category)
async def add_category_custom(message: Message, state: FSMContext) -> None:
    await state.update_data(category=message.text)
    await state.set_state(AddProduct.subcategory)
    await message.answer("Выберите подкатегорию или игру:", reply_markup=static_choice(DEFAULT_SUBCATEGORIES, "add_subcategory"))


@router.callback_query(AddProduct.subcategory, lambda c: c.data.startswith("add_subcategory:"))
async def add_subcategory_choice(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 1)[1]
    if key == "custom":
        await callback.message.edit_text("Введите свою подкатегорию или игру одним сообщением:")
        await callback.answer()
        return
    value = get(key)
    if not value:
        await callback.answer("Кнопка устарела. Начните добавление товара заново.", show_alert=True)
        return
    await state.update_data(subcategory=value)
    await state.set_state(AddProduct.optimization_type)
    await callback.message.edit_text("Выберите тип оптимизации:", reply_markup=static_choice(DEFAULT_TYPES, "add_type"))
    await callback.answer()


@router.message(AddProduct.subcategory)
async def add_subcategory_custom(message: Message, state: FSMContext) -> None:
    await state.update_data(subcategory=message.text)
    await state.set_state(AddProduct.optimization_type)
    await message.answer("Выберите тип оптимизации:", reply_markup=static_choice(DEFAULT_TYPES, "add_type"))


@router.callback_query(AddProduct.optimization_type, lambda c: c.data.startswith("add_type:"))
async def add_optimization_type_choice(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 1)[1]
    if key == "custom":
        await callback.message.edit_text("Введите свой тип оптимизации одним сообщением:")
        await callback.answer()
        return
    value = get(key)
    if not value:
        await callback.answer("Кнопка устарела. Начните добавление товара заново.", show_alert=True)
        return
    await state.update_data(optimization_type=value)
    await state.set_state(AddProduct.game)
    await callback.message.edit_text("Выберите игру/назначение:", reply_markup=static_choice(DEFAULT_SUBCATEGORIES, "add_game"))
    await callback.answer()


@router.message(AddProduct.optimization_type)
async def add_optimization_type_custom(message: Message, state: FSMContext) -> None:
    await state.update_data(optimization_type=message.text)
    await state.set_state(AddProduct.game)
    await message.answer("Выберите игру/назначение:", reply_markup=static_choice(DEFAULT_SUBCATEGORIES, "add_game"))


@router.callback_query(AddProduct.game, lambda c: c.data.startswith("add_game:"))
async def add_game_choice(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 1)[1]
    if key == "custom":
        await callback.message.edit_text("Введите игру или назначение одним сообщением:")
        await callback.answer()
        return
    value = get(key)
    if not value:
        await callback.answer("Кнопка устарела. Начните добавление товара заново.", show_alert=True)
        return
    await state.update_data(game=value)
    await state.set_state(AddProduct.price_currency)
    await callback.message.edit_text(
        "Выберите валюту цены товара:",
        reply_markup=static_choice([("⭐ Telegram Stars", "stars"), ("₽ Рубли", "rub")], "add_price_currency"),
    )
    await callback.answer()


@router.message(AddProduct.game)
async def add_game_custom(message: Message, state: FSMContext) -> None:
    await state.update_data(game=message.text)
    await state.set_state(AddProduct.price_currency)
    await message.answer(
        "Выберите валюту цены товара:",
        reply_markup=static_choice([("⭐ Telegram Stars", "stars"), ("₽ Рубли", "rub")], "add_price_currency"),
    )


@router.callback_query(AddProduct.price_currency, lambda c: c.data.startswith("add_price_currency:"))
async def add_price_currency(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 1)[1]
    currency = get(key)
    if not currency:
        await callback.answer("Кнопка устарела. Начните добавление товара заново.", show_alert=True)
        return
    await state.update_data(price_currency=currency)
    await state.set_state(AddProduct.price)
    suffix = "рублях" if currency == "rub" else "Telegram Stars"
    await callback.message.edit_text(f"Введите цену в {suffix} числом:")
    await callback.answer()


@router.message(AddProduct.price)
async def add_price(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("Цена должна быть числом.")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(AddProduct.badge)
    await message.answer("Выберите метку товара:", reply_markup=static_choice(BADGES, "add_badge"))


@router.callback_query(AddProduct.badge, lambda c: c.data.startswith("add_badge:"))
async def add_badge(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 1)[1]
    value = get(key)
    if value is None:
        await callback.answer("Кнопка устарела. Начните добавление товара заново.", show_alert=True)
        return
    await state.update_data(badge=value or "")
    await state.set_state(AddProduct.before_fps)
    await callback.message.edit_text("Введите FPS до оптимизации:")
    await callback.answer()


@router.message(AddProduct.before_fps)
async def add_before_fps(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("FPS должен быть числом.")
        return
    await state.update_data(before_fps=int(message.text))
    await state.set_state(AddProduct.after_fps)
    await message.answer("Введите FPS после оптимизации:")


@router.message(AddProduct.after_fps)
async def add_after_fps(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("FPS должен быть числом.")
        return
    await state.update_data(after_fps=int(message.text))
    await state.set_state(AddProduct.photo)
    await message.answer("Отправьте фото товара прямо в чат.", reply_markup=photo_step("add_photo_skip"))


@router.callback_query(AddProduct.photo, lambda c: c.data == "add_photo_skip")
async def add_photo_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(photo_path="", photo_file_id="")
    await state.set_state(AddProduct.screenshot)
    await callback.message.edit_text("Отправьте скриншот результата до/после.", reply_markup=photo_step("add_screenshot_skip"))
    await callback.answer()


@router.message(AddProduct.photo, F.photo)
async def add_photo_upload(message: Message, bot: Bot, state: FSMContext, settings: Settings) -> None:
    file_path, file_id = await save_message_photo(bot, message, settings, "products")
    await state.update_data(photo_path=file_path, photo_file_id=file_id)
    await state.set_state(AddProduct.screenshot)
    await message.answer("Фото товара сохранено. Теперь отправьте скриншот результата до/после.", reply_markup=photo_step("add_screenshot_skip"))


@router.callback_query(AddProduct.screenshot, lambda c: c.data == "add_screenshot_skip")
async def add_screenshot_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(screenshot_path="", screenshot_file_id="")
    await state.set_state(AddProduct.full_link)
    await callback.message.edit_text("Вставьте ссылку на полную версию товара:")
    await callback.answer()


@router.message(AddProduct.screenshot, F.photo)
async def add_screenshot_upload(message: Message, bot: Bot, state: FSMContext, settings: Settings) -> None:
    file_path, file_id = await save_message_photo(bot, message, settings, "product_results")
    await state.update_data(screenshot_path=file_path, screenshot_file_id=file_id)
    await state.set_state(AddProduct.full_link)
    await message.answer("Скриншот сохранён. Вставьте ссылку на полную версию товара:")


@router.message(AddProduct.full_link)
async def add_full_link(message: Message, state: FSMContext) -> None:
    await state.update_data(full_file_path=message.text)
    await state.set_state(AddProduct.demo_link)
    await message.answer("Вставьте ссылку на демо-версию товара:")


@router.message(AddProduct.demo_link)
async def add_demo_link(message: Message, state: FSMContext) -> None:
    await state.update_data(demo_file_path=message.text)
    await state.set_state(AddProduct.is_extra)
    await message.answer(
        "Это экстро оптимизация?",
        reply_markup=static_choice([("Да, показать предупреждение", "1"), ("Нет", "0")], "add_extra"),
    )


@router.callback_query(AddProduct.is_extra, lambda c: c.data.startswith("add_extra:"))
async def add_is_extra(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.split(":", 1)[1]
    value = get(key)
    if value is None:
        await callback.answer("Кнопка устарела. Начните добавление товара заново.", show_alert=True)
        return
    await state.update_data(is_extra=int(value or 0))
    await state.set_state(AddProduct.restore_link)
    await callback.message.edit_text("Вставьте ссылку на restore-файл/инструкцию или отправьте «-»:")
    await callback.answer()


@router.message(AddProduct.restore_link)
async def add_restore_file_path(message: Message, state: FSMContext, products: ProductRepository) -> None:
    await state.update_data(restore_file_path="" if message.text == "-" else message.text)
    data = await state.get_data()
    product_id = await products.create(data)
    await state.clear()
    await message.answer(f"✅ Товар #{product_id} добавлен.", reply_markup=back_to_main())


@router.callback_query(lambda c: c.data == "admin_promos")
async def admin_promos(callback: CallbackQuery, promos: PromoRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    rows = await promos.list_all()
    await callback.message.edit_text("🎟 Промокоды", reply_markup=promos_keyboard(rows))
    await callback.answer()


@router.callback_query(lambda c: c.data == "promo_create")
async def promo_create(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await state.set_state(PromoCreate.code)
    await callback.message.edit_text("Введите код промокода, например BOOST20:")
    await callback.answer()


@router.message(PromoCreate.code)
async def promo_code(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip().upper()
    if not code or ":" in code or len(code) > 32:
        await message.answer("Код не может быть пустым, длиннее 32 символов или содержать двоеточие.")
        return
    await state.update_data(code=code)
    await state.set_state(PromoCreate.discount_percent)
    await message.answer("Введите процент скидки от 1 до 99:")


@router.message(PromoCreate.discount_percent)
async def promo_discount(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit() or not 1 <= int(message.text) <= 99:
        await message.answer("Скидка должна быть числом от 1 до 99.")
        return
    await state.update_data(discount_percent=int(message.text))
    await state.set_state(PromoCreate.expires_day)
    await message.answer("Введите день окончания промокода числом от 1 до 31 или «-» без срока:")


@router.message(PromoCreate.expires_day)
async def promo_expires_day(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if raw == "-":
        await state.update_data(expires_at=None)
        await state.set_state(PromoCreate.usage_limit)
        await message.answer("Введите лимит использований числом или «-» без лимита:")
        return
    if not raw.isdigit() or not 1 <= int(raw) <= 31:
        await message.answer("День должен быть числом от 1 до 31 или «-».")
        return
    await state.update_data(expires_day=int(raw))
    await state.set_state(PromoCreate.expires_month)
    await message.answer("Введите месяц окончания промокода числом от 1 до 12:")


@router.message(PromoCreate.expires_month)
async def promo_expires_month(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= 12:
        await message.answer("Месяц должен быть числом от 1 до 12.")
        return
    await state.update_data(expires_month=int(raw))
    await state.set_state(PromoCreate.expires_year)
    await message.answer("Введите год окончания промокода, например 2026:")


@router.message(PromoCreate.expires_year)
async def promo_expires_year(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) < datetime.now().year:
        await message.answer("Год должен быть числом не меньше текущего года.")
        return
    data = await state.get_data()
    try:
        expires_at = datetime(int(raw), data["expires_month"], data["expires_day"], 23, 59, 59).isoformat()
    except ValueError:
        await message.answer("Такой даты не существует. Введите день заново.")
        await state.set_state(PromoCreate.expires_day)
        return
    await state.update_data(expires_at=expires_at)
    await state.set_state(PromoCreate.usage_limit)
    await message.answer("Введите лимит использований числом или «-» без лимита:")


@router.message(PromoCreate.usage_limit)
async def promo_limit(message: Message, state: FSMContext, promos: PromoRepository) -> None:
    raw = (message.text or "").strip()
    if raw != "-" and not raw.isdigit():
        await message.answer("Лимит должен быть числом или «-».")
        return
    data = await state.get_data()
    await promos.create(data["code"], data["discount_percent"], data["expires_at"], None if raw == "-" else int(raw))
    await state.clear()
    await message.answer(f"✅ Промокод {data['code']} создан.", reply_markup=admin_menu())


@router.callback_query(lambda c: c.data.startswith("promo_view:"))
async def promo_view(callback: CallbackQuery, promos: PromoRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    code = callback.data.split(":", 1)[1]
    promo = await promos.get(code)
    if not promo:
        await callback.answer("Промокод не найден.", show_alert=True)
        return
    await callback.message.edit_text(
        f"🎟 {promo['code']}\n\n"
        f"Скидка: {promo['discount_percent']}%\n"
        f"Активен: {'да' if promo['is_active'] else 'нет'}\n"
        f"Использований: {promo['used_count']} / {promo['usage_limit'] if promo['usage_limit'] is not None else '∞'}\n"
        f"Срок: {promo['expires_at'] or 'без срока'}",
        reply_markup=promo_actions(promo["code"], bool(promo["is_active"])),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("promo_toggle:"))
async def promo_toggle(callback: CallbackQuery, promos: PromoRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    code = callback.data.split(":", 1)[1]
    promo = await promos.get(code)
    if promo:
        await promos.set_active(code, not bool(promo["is_active"]))
    await callback.answer("Готово.")
    await admin_promos(callback, promos, settings)


@router.callback_query(lambda c: c.data.startswith("promo_delete:"))
async def promo_delete(callback: CallbackQuery, promos: PromoRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await promos.delete(callback.data.split(":", 1)[1])
    await callback.answer("Промокод удалён.")
    await admin_promos(callback, promos, settings)


@router.callback_query(lambda c: c.data == "admin_section_photos")
async def admin_section_photos(callback: CallbackQuery, products: ProductRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    static_items = [
        ("🏠 Главное меню", "main"),
        ("👤 Профиль", "profile"),
        ("🔔 Подписки", "subscriptions"),
        ("💬 Поддержка", "support"),
        ("⭐ Отзывы", "reviews"),
        ("📜 Правила", "rules"),
    ]
    categories = [(f"📁 Категория: {row['category']}", f"category:{row['category']}") for row in await products.categories()]
    subcats = []
    for row in await products.distinct_values("subcategory"):
        subcats.append((f"📂 Подкатегория: {row['value']}", f"subcategory:{row['value']}"))
    await callback.message.edit_text(
        "🖼 Фото разделов\n\nВыберите раздел, категорию или подкатегорию:",
        reply_markup=section_photo_targets(static_items, categories + subcats),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("section_photo:"))
async def section_photo(callback: CallbackQuery, section_photos: SectionPhotoRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    value = get(callback.data.split(":", 1)[1])
    if not value:
        await callback.answer("Кнопка устарела.", show_alert=True)
        return
    section_key, title = value
    current = await section_photos.get(section_key)
    text = f"🖼 {title}\n\nТекущее фото: {'есть' if current else 'не задано'}"
    await callback.message.edit_text(text, reply_markup=section_photo_actions(section_key))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("section_photo_upload:"))
async def section_photo_upload(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    section_key = get(callback.data.split(":", 1)[1])
    await state.set_state(SectionPhotoEdit.photo)
    await state.update_data(section_key=section_key, title=section_key)
    await callback.message.edit_text("Отправьте новое фото для выбранного раздела.")
    await callback.answer()


@router.message(SectionPhotoEdit.photo, F.photo)
async def section_photo_save(
    message: Message,
    bot: Bot,
    state: FSMContext,
    settings: Settings,
    section_photos: SectionPhotoRepository,
) -> None:
    data = await state.get_data()
    file_path, file_id = await save_message_photo(bot, message, settings, "sections")
    await section_photos.set_photo(data["section_key"], data["title"], file_path, file_id)
    await state.clear()
    await message.answer("✅ Фото раздела сохранено.", reply_markup=admin_menu())


@router.callback_query(lambda c: c.data.startswith("section_photo_view:"))
async def section_photo_view(callback: CallbackQuery, section_photos: SectionPhotoRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    section_key = get(callback.data.split(":", 1)[1])
    photo = await section_photos.get(section_key)
    if not photo:
        await callback.answer("Фото не задано.", show_alert=True)
        return
    if Path(photo["file_path"]).exists():
        await callback.message.answer_photo(FSInputFile(photo["file_path"]), caption=photo["title"])
    elif photo["file_id"]:
        await callback.message.answer_photo(photo["file_id"], caption=photo["title"])
    else:
        await callback.message.answer(f"Фото записано в базе, но файл не найден: {photo['file_path']}")
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("section_photo_delete:"))
async def section_photo_delete(callback: CallbackQuery, section_photos: SectionPhotoRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    section_key = get(callback.data.split(":", 1)[1])
    await section_photos.delete(section_key)
    await callback.answer("Фото удалено.")
    await callback.message.edit_text("Фото раздела удалено.", reply_markup=admin_menu())
