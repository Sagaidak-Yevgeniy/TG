from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.types import Message
from aiogram.types import FSInputFile
from pathlib import Path

from bot.config import Settings
from bot.keyboards.user import (
    back_to_main,
    profile_menu,
    purchases_for_review,
    rating_keyboard,
    topup_amounts,
    topup_balance_type,
    topup_payment_options,
)
from bot.repositories.orders import OrderRepository
from bot.repositories.products import ProductRepository
from bot.repositories.reviews import ReviewRepository
from bot.repositories.section_photos import SectionPhotoRepository
from bot.repositories.subscriptions import SubscriptionRepository
from bot.repositories.users import UserRepository
from bot.services.section_display import edit_section
from bot.states import ReviewCreate, TopUpBalance

router = Router()


def _format_registered_at(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value).replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Yekaterinburg"))
    except ValueError:
        return value
    return dt.strftime("%H:%M:%S %d-%m-%Y")


@router.callback_query(lambda c: c.data == "profile")
async def profile(callback: CallbackQuery, users: UserRepository, section_photos: SectionPhotoRepository) -> None:
    user = await users.get_or_create(callback.from_user.id, callback.from_user.username)
    totals = await users.purchase_totals(callback.from_user.id)
    username = f" @{user['username']}" if user["username"] else ""
    await edit_section(
        callback,
        section_photos,
        "profile",
        f"👨‍💻 Мой ID: {user['telegram_id']}{username}\n"
        f"💰 Мой баланс: {user['balance']} ⭐ / {user['balance_rub']} ₽\n"
        f"🛒 Покупок: {user['purchases_count']}\n"
        f"👜 Сумма покупок: {totals['rub']} ₽ и {totals['stars']} ⭐\n"
        f"💸 Сумма пополнений: {user['total_topup_rub']} ₽ и {user['total_topup_stars']} ⭐\n"
        f"📅 Зарегистрирован: {_format_registered_at(user['registered_at'])}",
        reply_markup=profile_menu(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "topup")
async def topup(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "💳 Пополнение баланса\n\n"
        "Выберите, какой баланс хотите пополнить:",
        reply_markup=topup_balance_type(),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("topup_type:"))
async def topup_type(callback: CallbackQuery) -> None:
    balance_type = callback.data.split(":")[1]
    title = "рублях" if balance_type == "rub" else "Telegram Stars"
    await callback.message.edit_text(
        f"💳 Пополнение баланса в {title}\n\nВыберите сумму или введите свою:",
        reply_markup=topup_amounts(balance_type),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("topup_amount:"))
async def topup_amount(callback: CallbackQuery) -> None:
    _, balance_type, amount_raw = callback.data.split(":")
    amount = int(amount_raw)
    suffix = "₽" if balance_type == "rub" else "⭐"
    await callback.message.edit_text(
        f"💳 Пополнение на {amount} {suffix}\n\nВыберите способ оплаты:",
        reply_markup=topup_payment_options(balance_type, amount),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("topup_custom:"))
async def topup_custom(callback: CallbackQuery, state: FSMContext) -> None:
    balance_type = callback.data.split(":")[1]
    await state.set_state(TopUpBalance.amount)
    await state.update_data(balance_type=balance_type)
    suffix = "рублях" if balance_type == "rub" else "Telegram Stars"
    await callback.message.edit_text(f"Введите сумму пополнения в {suffix} числом:")
    await callback.answer()


@router.message(TopUpBalance.amount)
async def topup_custom_amount(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Сумма должна быть положительным числом.")
        return
    data = await state.get_data()
    await state.clear()
    balance_type = data["balance_type"]
    amount = int(message.text)
    suffix = "₽" if balance_type == "rub" else "⭐"
    await message.answer(
        f"💳 Пополнение на {amount} {suffix}\n\nВыберите способ оплаты:",
        reply_markup=topup_payment_options(balance_type, amount),
    )


@router.callback_query(lambda c: c.data == "purchase_history")
async def purchase_history(callback: CallbackQuery, orders: OrderRepository) -> None:
    rows = await orders.purchase_history(callback.from_user.id)
    if not rows:
        text = "🧾 История покупок пока пустая."
        markup = back_to_main()
    else:
        lines = ["🧾 Мои покупки\n"]
        for row in rows:
            discount = f", скидка {row['discount_percent']}%" if row["discount_percent"] else ""
            promo = f", промокод {row['promo_code']}" if row["promo_code"] else ""
            suffix = "₽" if row["amount_currency"] == "rub" else "⭐"
            lines.append(f"• {row['title']} — {row['amount']} {suffix}{discount}{promo}, {row['provider']}, {row['created_at']}")
        text = "\n".join(lines)
        markup = purchases_for_review(rows)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("review_start:"))
async def review_start(callback: CallbackQuery, orders: OrderRepository) -> None:
    product_id = int(callback.data.split(":")[1])
    if not await orders.has_purchase(callback.from_user.id, product_id):
        await callback.answer("Отзыв можно оставить только после покупки.", show_alert=True)
        return
    await callback.message.edit_text("Поставьте оценку товару от 1 до 5 звёзд:", reply_markup=rating_keyboard(product_id))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("review_rating:"))
async def review_rating(callback: CallbackQuery, state: FSMContext) -> None:
    _, _, product_id, rating = callback.data.split(":")
    await state.set_state(ReviewCreate.comment)
    await state.update_data(product_id=int(product_id), rating=int(rating))
    await callback.message.edit_text("Напишите комментарий к покупке одним сообщением:")
    await callback.answer()


@router.message(ReviewCreate.comment)
async def review_comment(
    message: Message,
    state: FSMContext,
    products: ProductRepository,
    reviews: ReviewRepository,
    settings: Settings,
) -> None:
    data = await state.get_data()
    product = await products.get(data["product_id"])
    if not product:
        await state.clear()
        await message.answer("Товар не найден.", reply_markup=back_to_main())
        return

    comment = message.text or ""
    await reviews.create(message.from_user.id, product["id"], data["rating"], comment)
    await state.clear()

    buyer_name = message.from_user.full_name
    buyer_username = f"@{message.from_user.username}" if message.from_user.username else "username не указан"
    caption = (
        "⭐ Новый отзыв о товаре\n\n"
        f"Покупатель: {buyer_name} ({buyer_username})\n"
        f"ID: {message.from_user.id}\n"
        f"Товар: {product['title']}\n"
        f"Оценка: {data['rating']} / 5\n"
        f"Комментарий: {comment}"
    )
    for admin_id in settings.admin_ids:
        if product["photo_path"] and Path(product["photo_path"]).exists():
            await message.bot.send_photo(admin_id, FSInputFile(product["photo_path"]), caption=caption)
        elif product["photo_file_id"]:
            await message.bot.send_photo(admin_id, product["photo_file_id"], caption=caption)
        else:
            await message.bot.send_message(admin_id, caption)

    await message.answer("Спасибо! Отзыв отправлен владельцу бота.", reply_markup=back_to_main())


@router.callback_query(lambda c: c.data == "my_subscriptions")
async def subscriptions(callback: CallbackQuery, subscriptions_repo: SubscriptionRepository, section_photos: SectionPhotoRepository) -> None:
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
    await edit_section(callback, section_photos, "subscriptions", text, reply_markup=back_to_main())
    await callback.answer()
