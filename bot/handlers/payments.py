from __future__ import annotations

from aiogram import Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Message, PreCheckoutQuery

from bot.keyboards.user import crypto_invoice, topup_crypto_invoice
from bot.repositories.orders import OrderRepository
from bot.repositories.products import ProductRepository
from bot.repositories.promos import PromoRepository, apply_discount
from bot.repositories.users import UserRepository
from bot.services.delivery import send_file_or_notice
from bot.services.payments import CryptoBotService

router = Router()


@router.callback_query(lambda c: c.data.startswith("buy_stars:"))
async def buy_stars(callback: CallbackQuery, bot: Bot, products: ProductRepository, promos: PromoRepository, state: FSMContext) -> None:
    await state.clear()
    _, product_id_raw, promo_code = callback.data.split(":")
    product_id = int(product_id_raw)
    product = await products.get(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    final_price = product["price"]
    payload_promo = "none"
    if promo_code != "none":
        promo, error = await promos.validate(promo_code)
        if error:
            await callback.answer(error, show_alert=True)
            return
        final_price = apply_discount(product["price"], promo["discount_percent"])
        payload_promo = promo["code"]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=product["title"],
        description=product["description"][:255],
        payload=f"product:{product_id}:{payload_promo}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=product["title"], amount=final_price)],
    )
    await bot.send_message(
        callback.from_user.id,
        "Если сейчас не получается оплатить, можно вернуться к товару или отменить действие.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад к товару", callback_data=f"product:{product_id}")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="main")],
            ]
        ),
    )
    await callback.answer("Счёт отправлен в личные сообщения.")


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(lambda m: m.successful_payment is not None)
async def successful_payment(
    message: Message,
    bot: Bot,
    products: ProductRepository,
    orders: OrderRepository,
    promos: PromoRepository,
    users: UserRepository,
) -> None:
    payload = message.successful_payment.invoice_payload
    if payload.startswith("topup:"):
        _, balance_type, amount_raw = payload.split(":")
        amount = int(amount_raw)
        charge_id = message.successful_payment.telegram_payment_charge_id
        if not await users.has_topup_payload(charge_id):
            await users.add_topup(message.from_user.id, balance_type, amount, "telegram_stars", charge_id)
        suffix = "₽" if balance_type == "rub" else "⭐"
        await message.answer(
            f"✅ Баланс пополнен на {amount} {suffix}.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")]]
            ),
        )
        return

    if not payload.startswith("product:"):
        await message.answer("Оплата получена, но товар не распознан. Напишите в поддержку.")
        return

    parts = payload.split(":")
    product_id = int(parts[1])
    promo_code = parts[2] if len(parts) > 2 and parts[2] != "none" else None
    product = await products.get(product_id)
    if not product:
        await message.answer("Оплата получена, но товар уже недоступен. Напишите в поддержку.")
        return

    discount_percent = 0
    if promo_code:
        promo, error = await promos.validate(promo_code)
        if not error:
            discount_percent = promo["discount_percent"]

    purchase_id = await orders.add_purchase(
        user_id=message.from_user.id,
        product_id=product_id,
        amount=message.successful_payment.total_amount,
        provider="telegram_stars",
        payload=message.successful_payment.telegram_payment_charge_id,
        original_amount=product["price"],
        discount_percent=discount_percent,
        promo_code=promo_code,
    )
    if purchase_id and promo_code:
        await promos.redeem(promo_code, message.from_user.id, product_id, purchase_id)
    await send_file_or_notice(bot, message.from_user.id, product["full_file_path"], f"✅ Полная версия: {product['title']}")
    if product["is_extra"] and product["restore_file_path"]:
        await send_file_or_notice(bot, message.from_user.id, product["restore_file_path"], "♻️ Файл/инструкция для отката настроек")
    await message.answer(
        "Если хотите оставить отзыв о товаре, зайдите в раздел «Мои покупки», выберите купленный товар и нажмите «Оставить отзыв».",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🧾 Мои покупки", callback_data="purchase_history")]]
        ),
    )


@router.callback_query(lambda c: c.data.startswith("buy_crypto:"))
async def buy_crypto(
    callback: CallbackQuery,
    products: ProductRepository,
    orders: OrderRepository,
    cryptobot: CryptoBotService,
    promos: PromoRepository,
    state: FSMContext,
) -> None:
    await state.clear()
    if not cryptobot.enabled:
        await callback.answer("CryptoBot не настроен.", show_alert=True)
        return

    _, product_id_raw, promo_code = callback.data.split(":")
    product_id = int(product_id_raw)
    product = await products.get(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    final_price = product["price"]
    payload_promo = None
    if promo_code != "none":
        promo, error = await promos.validate(promo_code)
        if error:
            await callback.answer(error, show_alert=True)
            return
        final_price = apply_discount(product["price"], promo["discount_percent"])
        payload_promo = promo["code"]

    invoice = await cryptobot.create_invoice(
        amount=final_price,
        description=f"Покупка {product['title']}",
        payload=f"{callback.from_user.id}:{product_id}",
    )
    await orders.create_crypto_invoice(invoice.invoice_id, callback.from_user.id, product_id, final_price, payload_promo)
    await callback.message.edit_text(
        "💎 Счёт CryptoBot создан.\n\nПосле оплаты нажмите «Проверить оплату».",
        reply_markup=crypto_invoice(invoice.pay_url, invoice.invoice_id),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("check_crypto:"))
async def check_crypto(
    callback: CallbackQuery,
    bot: Bot,
    products: ProductRepository,
    orders: OrderRepository,
    cryptobot: CryptoBotService,
    promos: PromoRepository,
) -> None:
    invoice_id = callback.data.split(":")[1]
    invoice = await orders.get_crypto_invoice(invoice_id)
    if not invoice or invoice["user_id"] != callback.from_user.id:
        await callback.answer("Счёт не найден.", show_alert=True)
        return

    status = await cryptobot.get_invoice_status(invoice_id)
    if status != "paid":
        await callback.answer(f"Оплата пока не найдена. Статус: {status}", show_alert=True)
        return

    product = await products.get(invoice["product_id"])
    if not product:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    discount_percent = 0
    promo_code = invoice["promo_code"]
    if promo_code:
        promo, error = await promos.validate(promo_code)
        if not error:
            discount_percent = promo["discount_percent"]

    await orders.mark_crypto_paid(invoice_id)
    purchase_id = await orders.add_purchase(
        callback.from_user.id,
        product["id"],
        invoice["amount"],
        "cryptobot",
        invoice_id,
        original_amount=product["price"],
        discount_percent=discount_percent,
        promo_code=promo_code,
    )
    if purchase_id and promo_code:
        await promos.redeem(promo_code, callback.from_user.id, product["id"], purchase_id)
    await send_file_or_notice(bot, callback.from_user.id, product["full_file_path"], f"✅ Полная версия: {product['title']}")
    if product["is_extra"] and product["restore_file_path"]:
        await send_file_or_notice(bot, callback.from_user.id, product["restore_file_path"], "♻️ Файл/инструкция для отката настроек")
    await bot.send_message(
        callback.from_user.id,
        "Если хотите оставить отзыв о товаре, зайдите в раздел «Мои покупки», выберите купленный товар и нажмите «Оставить отзыв».",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🧾 Мои покупки", callback_data="purchase_history")]]
        ),
    )
    await callback.answer("Оплата подтверждена, файл отправлен.")


@router.callback_query(lambda c: c.data.startswith("topup_stars:"))
async def topup_stars(callback: CallbackQuery, bot: Bot, users: UserRepository, state: FSMContext) -> None:
    await state.clear()
    _, balance_type, amount_raw = callback.data.split(":")
    amount = int(amount_raw)
    suffix = "рублей" if balance_type == "rub" else "Stars"

    await users.get_or_create(callback.from_user.id)
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=f"Пополнение баланса: {amount} {suffix}",
        description=f"После оплаты на баланс будет зачислено {amount} {'₽' if balance_type == 'rub' else '⭐'}.",
        payload=f"topup:{balance_type}:{amount}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{amount} {suffix}", amount=amount)],
    )
    await bot.send_message(
        callback.from_user.id,
        "Если сейчас не получается оплатить, можно отменить пополнение.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад к пополнению", callback_data="topup")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="profile")],
            ]
        ),
    )
    await callback.answer("Счёт отправлен в личные сообщения.")


@router.callback_query(lambda c: c.data.startswith("topup_crypto:"))
async def topup_crypto(
    callback: CallbackQuery,
    users: UserRepository,
    cryptobot: CryptoBotService,
    state: FSMContext,
) -> None:
    await state.clear()
    if not cryptobot.enabled:
        await callback.answer("CryptoBot не настроен.", show_alert=True)
        return

    _, balance_type, amount_raw = callback.data.split(":")
    amount = int(amount_raw)
    await users.get_or_create(callback.from_user.id)
    suffix = "₽" if balance_type == "rub" else "⭐"
    invoice = await cryptobot.create_invoice(
        amount=amount,
        description=f"Пополнение баланса на {amount} {suffix}",
        payload=f"topup:{callback.from_user.id}:{balance_type}:{amount}",
    )
    await users.create_topup_crypto_invoice(invoice.invoice_id, callback.from_user.id, balance_type, amount)
    await callback.message.edit_text(
        f"💎 Счёт CryptoBot создан.\n\nПосле оплаты будет зачислено {amount} {suffix}.",
        reply_markup=topup_crypto_invoice(invoice.pay_url, invoice.invoice_id),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("check_topup_crypto:"))
async def check_topup_crypto(
    callback: CallbackQuery,
    users: UserRepository,
    cryptobot: CryptoBotService,
) -> None:
    invoice_id = callback.data.split(":")[1]
    invoice = await users.get_topup_crypto_invoice(invoice_id)
    if not invoice or invoice["user_id"] != callback.from_user.id:
        await callback.answer("Счёт не найден.", show_alert=True)
        return

    status = await cryptobot.get_invoice_status(invoice_id)
    if status != "paid":
        await callback.answer(f"Оплата пока не найдена. Статус: {status}", show_alert=True)
        return

    if invoice["status"] != "paid":
        await users.mark_topup_crypto_paid(invoice_id)
        await users.add_topup(
            callback.from_user.id,
            invoice["balance_type"],
            invoice["amount"],
            "cryptobot",
            invoice_id,
        )

    suffix = "₽" if invoice["balance_type"] == "rub" else "⭐"
    await callback.message.edit_text(
        f"✅ Баланс пополнен на {invoice['amount']} {suffix}.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")]]
        ),
    )
    await callback.answer("Пополнение подтверждено.")
