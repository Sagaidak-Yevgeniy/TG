from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.types import Message
from aiogram.types import FSInputFile
from pathlib import Path

from bot.config import Settings
from bot.keyboards.user import back_to_main, profile_menu, purchases_for_review, rating_keyboard
from bot.repositories.orders import OrderRepository
from bot.repositories.products import ProductRepository
from bot.repositories.reviews import ReviewRepository
from bot.repositories.section_photos import SectionPhotoRepository
from bot.repositories.subscriptions import SubscriptionRepository
from bot.repositories.users import UserRepository
from bot.services.section_display import edit_section
from bot.states import ReviewCreate

router = Router()


@router.callback_query(lambda c: c.data == "profile")
async def profile(callback: CallbackQuery, users: UserRepository, section_photos: SectionPhotoRepository) -> None:
    user = await users.get_or_create(callback.from_user.id)
    await edit_section(
        callback,
        section_photos,
        "profile",
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
        markup = back_to_main()
    else:
        lines = ["🧾 Мои покупки\n"]
        for row in rows:
            discount = f", скидка {row['discount_percent']}%" if row["discount_percent"] else ""
            promo = f", промокод {row['promo_code']}" if row["promo_code"] else ""
            lines.append(f"• {row['title']} — {row['amount']} ⭐{discount}{promo}, {row['provider']}, {row['created_at']}")
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
