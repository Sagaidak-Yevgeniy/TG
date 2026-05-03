from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить товар", callback_data="admin_add_product")
    builder.button(text="📦 Список товаров", callback_data="admin_products")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="💰 Продажи", callback_data="admin_sales")
    builder.button(text="🔔 Подписки", callback_data="admin_subscriptions")
    builder.button(text="⬅️ Главное меню", callback_data="main")
    builder.adjust(1)
    return builder.as_markup()
