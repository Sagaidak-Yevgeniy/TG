from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.callback_cache import put


def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Каталог товаров", callback_data="catalog")
    builder.button(text="🎁 Демо / Бесплатные файлы", callback_data="demo_catalog")
    builder.button(text="👤 Личный кабинет", callback_data="profile")
    builder.button(text="📘 FAQ", callback_data="faq")
    builder.button(text="💬 Поддержка / Помощь с выбором", callback_data="support")
    builder.button(text="⭐ Отзывы", callback_data="reviews")
    if is_admin:
        builder.button(text="🛠 Админ-панель", callback_data="admin")
    builder.adjust(1)
    return builder.as_markup()


def profile_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Пополнить баланс", callback_data="topup")
    builder.button(text="🧾 История покупок", callback_data="purchase_history")
    builder.button(text="🔔 Подписки", callback_data="my_subscriptions")
    builder.button(text="⬅️ Главное меню", callback_data="main")
    builder.adjust(1)
    return builder.as_markup()


def back_to_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main")]]
    )


def catalog_categories(rows, prefix: str = "cat") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.button(text=row["category"], callback_data=f"{prefix}:{put(row['category'])}")
    builder.button(text="⬅️ Главное меню", callback_data="main")
    builder.adjust(1)
    return builder.as_markup()


def subcategories(rows, category: str, prefix: str = "sub") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.button(text=row["subcategory"], callback_data=f"{prefix}:{put((category, row['subcategory']))}")
    builder.button(text="⬅️ Назад к разделам", callback_data="demo_catalog" if prefix.startswith("demo") else "catalog")
    builder.adjust(1)
    return builder.as_markup()


def optimization_types(rows, category: str, subcategory: str, prefix: str = "type") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in rows:
        builder.button(
            text=row["optimization_type"],
            callback_data=f"{prefix}:{put((category, subcategory, row['optimization_type']))}",
        )
    back_prefix = "demo_cat" if prefix.startswith("demo") else "cat"
    builder.button(text="⬅️ Назад", callback_data=f"{back_prefix}:{put(category)}")
    builder.adjust(1)
    return builder.as_markup()


def products(rows, category: str, subcategory: str, optimization_type: str, demo: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    action = "demo_product" if demo else "product"
    for row in rows:
        badge = f"{row['badge']} " if row["badge"] else ""
        builder.button(text=f"{badge}{row['title']} - {row['price']} ⭐", callback_data=f"{action}:{row['id']}")
    back_prefix = "demo_type" if demo else "type"
    builder.button(text="⬅️ Назад", callback_data=f"{back_prefix}:{put((category, subcategory, optimization_type))}")
    builder.adjust(1)
    return builder.as_markup()


def product_actions(product_id: int, is_extra: bool, crypto_enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Получить демо", callback_data=f"demo_product:{product_id}")
    if is_extra:
        builder.button(text="⚠️ Я понимаю риски", callback_data=f"risk_ok:{product_id}")
    else:
        builder.button(text="⭐ Купить за Telegram Stars", callback_data=f"buy_stars:{product_id}")
        if crypto_enabled:
            builder.button(text="💎 Купить через CryptoBot", callback_data=f"buy_crypto:{product_id}")
    builder.button(text="🔔 Оформить подписку", callback_data=f"subscribe_product:{product_id}")
    builder.button(text="⬅️ Каталог", callback_data="catalog")
    builder.adjust(1)
    return builder.as_markup()


def extra_confirmed_actions(product_id: int, crypto_enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Купить за Telegram Stars", callback_data=f"buy_stars:{product_id}")
    if crypto_enabled:
        builder.button(text="💎 Купить через CryptoBot", callback_data=f"buy_crypto:{product_id}")
    builder.button(text="⬅️ К товару", callback_data=f"product:{product_id}")
    builder.adjust(1)
    return builder.as_markup()


def demo_requirements(channel: str, product_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    url = f"https://t.me/{channel.removeprefix('@')}" if channel.startswith("@") else None
    if url:
        builder.button(text="📢 Подписаться на канал", url=url)
    builder.button(text="✅ Проверить подписку", callback_data=f"check_demo:{product_id}")
    builder.button(text="⬅️ К товару", callback_data=f"product:{product_id}")
    builder.adjust(1)
    return builder.as_markup()


def crypto_invoice(pay_url: str, invoice_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 Оплатить CryptoBot", url=pay_url)
    builder.button(text="✅ Проверить оплату", callback_data=f"check_crypto:{invoice_id}")
    builder.adjust(1)
    return builder.as_markup()
