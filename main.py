from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_settings
from bot.database import Database, init_db
from bot.handlers import admin, catalog, payments, profile, start
from bot.middleware import DependencyMiddleware
from bot.repositories.orders import OrderRepository
from bot.repositories.products import ProductRepository
from bot.repositories.subscriptions import SubscriptionRepository
from bot.repositories.users import UserRepository
from bot.services.catalog_seed import seed_catalog
from bot.services.payments import CryptoBotService


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    settings = load_settings()
    database = Database(settings.db_path)
    await init_db(database)

    users = UserRepository(database)
    products = ProductRepository(database)
    orders = OrderRepository(database)
    subscriptions = SubscriptionRepository(database)
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
        cryptobot=cryptobot,
    )
    dispatcher.update.middleware(dependencies)

    dispatcher.include_router(start.router)
    dispatcher.include_router(profile.router)
    dispatcher.include_router(catalog.router)
    dispatcher.include_router(payments.router)
    dispatcher.include_router(admin.router)

    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
