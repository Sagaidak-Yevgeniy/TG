from __future__ import annotations

import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import Settings
from bot.config import load_settings
from bot.database import Database, init_db
from bot.handlers import admin, catalog, payments, profile, start
from bot.middleware import DependencyMiddleware
from bot.repositories.orders import OrderRepository
from bot.repositories.products import ProductRepository
from bot.repositories.promos import PromoRepository
from bot.repositories.reviews import ReviewRepository
from bot.repositories.section_photos import SectionPhotoRepository
from bot.repositories.subscriptions import SubscriptionRepository
from bot.repositories.users import UserRepository
from bot.services.catalog_seed import seed_catalog
from bot.services.payments import CryptoBotService


async def poll_crypto_topups(bot: Bot, users: UserRepository, cryptobot: CryptoBotService) -> None:
    if not cryptobot.enabled:
        return
    while True:
        try:
            invoices = await users.pending_topup_crypto_invoices()
            for invoice in invoices:
                status = await cryptobot.get_invoice_status(invoice["invoice_id"])
                if status != "paid":
                    continue
                if not await users.has_topup_payload(invoice["invoice_id"]):
                    await users.add_topup(
                        invoice["user_id"],
                        invoice["balance_type"],
                        invoice["amount"],
                        "cryptobot",
                        invoice["invoice_id"],
                    )
                await users.mark_topup_crypto_paid(invoice["invoice_id"])
                suffix = "₽" if invoice["balance_type"] == "rub" else "⭐"
                await bot.send_message(invoice["user_id"], f"✅ Баланс автоматически пополнен на {invoice['amount']} {suffix}.")
        except Exception:
            logging.exception("CryptoBot topup polling failed")
        await asyncio.sleep(30)


def create_health_app() -> web.Application:
    async def health(_: web.Request) -> web.Response:
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    return app


async def start_health_server() -> web.AppRunner:
    app = create_health_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "10000")))
    await site.start()
    return runner


async def start_webhook_server(bot: Bot, dispatcher: Dispatcher, settings: Settings) -> None:
    app = create_health_app()
    SimpleRequestHandler(dispatcher=dispatcher, bot=bot).register(app, path=settings.webhook_path)
    setup_application(app, dispatcher, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "10000")))
    await site.start()

    webhook_url = f"{settings.webhook_url}{settings.webhook_path}"
    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    logging.info("Webhook started at %s", webhook_url)

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    settings = load_settings()
    database = Database(settings.db_path)
    await init_db(database)

    users = UserRepository(database)
    products = ProductRepository(database)
    orders = OrderRepository(database)
    subscriptions = SubscriptionRepository(database)
    promos = PromoRepository(database)
    reviews = ReviewRepository(database)
    section_photos = SectionPhotoRepository(database)
    cryptobot = CryptoBotService(settings)
    await seed_catalog(products)

    bot = Bot(settings.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())

    dependencies = DependencyMiddleware(
        settings=settings,
        users=users,
        products=products,
        orders=orders,
        subscriptions_repo=subscriptions,
        promos=promos,
        reviews=reviews,
        section_photos=section_photos,
        cryptobot=cryptobot,
    )
    dispatcher.update.middleware(dependencies)

    dispatcher.include_router(start.router)
    dispatcher.include_router(profile.router)
    dispatcher.include_router(catalog.router)
    dispatcher.include_router(payments.router)
    dispatcher.include_router(admin.router)

    asyncio.create_task(poll_crypto_topups(bot, users, cryptobot))

    if settings.webhook_url:
        await start_webhook_server(bot, dispatcher, settings)
    else:
        health_runner = await start_health_server()
        try:
            await dispatcher.start_polling(bot)
        finally:
            await health_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
