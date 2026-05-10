from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.callback_cache import put


def admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить товар", callback_data="admin_add_product")
    builder.button(text="📦 Список товаров", callback_data="admin_products")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="💰 Продажи", callback_data="admin_sales")
    builder.button(text="🔔 Подписки", callback_data="admin_subscriptions")
    builder.button(text="🎟 Промокоды", callback_data="admin_promos")
    builder.button(text="🖼 Фото разделов", callback_data="admin_section_photos")
    builder.button(text="⬅️ Главное меню", callback_data="main")
    builder.adjust(1)
    return builder.as_markup()


def value_choice(values, callback_prefix: str, allow_custom: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in values:
        value = row["value"]
        builder.button(text=value, callback_data=f"{callback_prefix}:{put(value)}")
    if allow_custom:
        builder.button(text="➕ Ввести вручную", callback_data=f"{callback_prefix}:custom")
    builder.button(text="❌ Отмена", callback_data="admin_cancel")
    builder.adjust(1)
    return builder.as_markup()


def static_choice(items: list[tuple[str, str]], callback_prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for title, value in items:
        builder.button(text=title, callback_data=f"{callback_prefix}:{put(value)}")
    builder.button(text="❌ Отмена", callback_data="admin_cancel")
    builder.adjust(1)
    return builder.as_markup()


def photo_step(skip_callback: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить", callback_data=skip_callback)
    builder.button(text="❌ Отмена", callback_data="admin_cancel")
    builder.adjust(1)
    return builder.as_markup()


def promos(rows) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать промокод", callback_data="promo_create")
    for row in rows:
        status = "✅" if row["is_active"] else "⛔"
        builder.button(text=f"{status} {row['code']} -{row['discount_percent']}%", callback_data=f"promo_view:{row['code']}")
    builder.button(text="⬅️ Админ-панель", callback_data="admin")
    builder.adjust(1)
    return builder.as_markup()


def promo_actions(code: str, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⛔ Отключить" if is_active else "✅ Включить", callback_data=f"promo_toggle:{code}")
    builder.button(text="🗑 Удалить", callback_data=f"promo_delete:{code}")
    builder.button(text="⬅️ Промокоды", callback_data="admin_promos")
    builder.adjust(1)
    return builder.as_markup()


def section_photo_targets(static_items: list[tuple[str, str]], dynamic_items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for title, key in static_items + dynamic_items:
        builder.button(text=title, callback_data=f"section_photo:{put((key, title))}")
    builder.button(text="⬅️ Админ-панель", callback_data="admin")
    builder.adjust(1)
    return builder.as_markup()


def section_photo_actions(section_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🖼 Изменить фото", callback_data=f"section_photo_upload:{put(section_key)}")
    builder.button(text="👁 Посмотреть текущее", callback_data=f"section_photo_view:{put(section_key)}")
    builder.button(text="🗑 Удалить фото", callback_data=f"section_photo_delete:{put(section_key)}")
    builder.button(text="⬅️ Список разделов", callback_data="admin_section_photos")
    builder.adjust(1)
    return builder.as_markup()
