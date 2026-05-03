from __future__ import annotations

from aiogram import Bot, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from bot.keyboards.user import crypto_invoice
from bot.repositories.orders import OrderRepository
from bot.repositories.products import ProductRepository
from bot.services.delivery import send_file_or_notice
from bot.services.payments import CryptoBotService

router = Router()


@router.callback_query(lambda c: c.data.startswith("buy_stars:"))
async def buy_stars(callback: CallbackQuery, bot: Bot, products: ProductRepository) -> None:
    product_id = int(callback.data.split(":")[1])
    product = await products.get(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=product["title"],
        description=product["description"][:255],
        payload=f"product:{product_id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=product["title"], amount=product["price"])],
    )
    await callback.answer("Счёт отправлен в личные сообщения.")


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(lambda m: m.successful_payment is not None)
async def successful_payment(message: Message, bot: Bot, products: ProductRepository, orders: OrderRepository) -> None:
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("product:"):
        await message.answer("Оплата получена, но товар не распознан. Напишите в поддержку.")
        return

    product_id = int(payload.split(":")[1])
    product = await products.get(product_id)
    if not product:
        await message.answer("Оплата получена, но товар уже недоступен. Напишите в поддержку.")
        return

    await orders.add_purchase(
        user_id=message.from_user.id,
        product_id=product_id,
        amount=product["price"],
        provider="telegram_stars",
        payload=message.successful_payment.telegram_payment_charge_id,
    )
    await send_file_or_notice(bot, message.from_user.id, product["full_file_path"], f"✅ Полная версия: {product['title']}")
    if product["is_extra"] and product["restore_file_path"]:
        await send_file_or_notice(bot, message.from_user.id, product["restore_file_path"], "♻️ Файл/инструкция для отката настроек")


@router.callback_query(lambda c: c.data.startswith("buy_crypto:"))
async def buy_crypto(
    callback: CallbackQuery,
    products: ProductRepository,
    orders: OrderRepository,
    cryptobot: CryptoBotService,
) -> None:
    if not cryptobot.enabled:
        await callback.answer("CryptoBot не настроен.", show_alert=True)
        return

    product_id = int(callback.data.split(":")[1])
    product = await products.get(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    invoice = await cryptobot.create_invoice(
        amount=product["price"],
        description=f"Покупка {product['title']}",
        payload=f"{callback.from_user.id}:{product_id}",
    )
    await orders.create_crypto_invoice(invoice.invoice_id, callback.from_user.id, product_id, product["price"])
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

    await orders.mark_crypto_paid(invoice_id)
    await orders.add_purchase(callback.from_user.id, product["id"], product["price"], "cryptobot", invoice_id)
    await send_file_or_notice(bot, callback.from_user.id, product["full_file_path"], f"✅ Полная версия: {product['title']}")
    if product["is_extra"] and product["restore_file_path"]:
        await send_file_or_notice(bot, callback.from_user.id, product["restore_file_path"], "♻️ Файл/инструкция для отката настроек")
    await callback.answer("Оплата подтверждена, файл отправлен.")
