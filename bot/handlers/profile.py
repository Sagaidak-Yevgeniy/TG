from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery

from bot.keyboards.user import back_to_main, profile_menu
from bot.repositories.orders import OrderRepository
from bot.repositories.subscriptions import SubscriptionRepository
from bot.repositories.users import UserRepository

router = Router()


@router.callback_query(lambda c: c.data == "profile")
async def profile(callback: CallbackQuery, users: UserRepository) -> None:
    user = await users.get_or_create(callback.from_user.id)
    await callback.message.edit_text(
        "👤 Личный кабинет\n\n"
        f"ID пользователя: `{user['telegram_id']}`\n"
        f"Дата регистрации: {user['registered_at']}\n"
        f"Количество покупок: {user['purchases_count']}\n"
        f"Баланс: {user['balance']} ⭐",
        parse_mode="Markdown",
        reply_markup=profile_menu(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "topup")
async def topup(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "💳 Пополнение баланса\n\n"
        "В этой версии покупка товара работает напрямую через Telegram Stars или CryptoBot. "
        "Баланс оставлен в профиле для будущих промокодов и ручных начислений администратором.",
        reply_markup=back_to_main(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "purchase_history")
async def purchase_history(callback: CallbackQuery, orders: OrderRepository) -> None:
    rows = await orders.purchase_history(callback.from_user.id)
    if not rows:
        text = "🧾 История покупок пока пустая."
    else:
        lines = ["🧾 История покупок\n"]
        for row in rows:
            lines.append(f"• {row['title']} — {row['amount']} ⭐, {row['provider']}, {row['created_at']}")
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=back_to_main())
    await callback.answer()


@router.callback_query(lambda c: c.data == "my_subscriptions")
async def subscriptions(callback: CallbackQuery, subscriptions_repo: SubscriptionRepository) -> None:
    rows = await subscriptions_repo.active_for_user(callback.from_user.id)
    if not rows:
        text = "🔔 Активных подписок нет."
    else:
        lines = ["🔔 Активные подписки\n"]
        for row in rows:
            lines.append(
                f"• {row['scope_type']}: {row['scope_value']}\n"
                f"  Следующая выдача: {row['next_delivery_at']} — обновление под новый патч игры"
            )
        text = "\n".join(lines)
    await callback.message.edit_text(text, reply_markup=back_to_main())
    await callback.answer()
