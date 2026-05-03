from __future__ import annotations

from pathlib import Path

from aiogram import Bot, Router
from aiogram.types import CallbackQuery, FSInputFile

from bot.config import Settings
from bot.keyboards.user import (
    back_to_main,
    catalog_categories,
    demo_requirements,
    extra_confirmed_actions,
    optimization_types,
    product_actions,
    products as products_keyboard,
    subcategories,
)
from bot.repositories.orders import OrderRepository
from bot.repositories.products import ProductRepository
from bot.repositories.subscriptions import SubscriptionRepository
from bot.services.catalog_seed import DEMO_NOTE
from bot.services.delivery import send_file_or_notice
from bot.utils.callback_cache import get

router = Router()


def _product_text(product) -> str:
    badge = f"{product['badge']}\n" if product["badge"] else ""
    extra_warning = (
        "\n\n⚠️ Данный файл может изменить системные настройки и повлиять на работу Windows. "
        "Используйте на свой страх и риск.\n"
        "Перед покупкой нужно нажать кнопку «⚠️ Я понимаю риски».\n"
        "В комплекте предусмотрена инструкция по откату или restore-файл."
        if product["is_extra"]
        else ""
    )
    return (
        f"{badge}📦 {product['title']}\n\n"
        f"{product['description']}\n\n"
        f"🎮 Игры: {product['game'] or product['subcategory']}\n"
        f"📊 До/после FPS: {product['before_fps']} → {product['after_fps']}\n"
        f"💰 Цена: {product['price']} ⭐{extra_warning}"
    )


async def _show_product(callback: CallbackQuery, product, settings: Settings) -> None:
    text = _product_text(product)
    markup = product_actions(product["id"], bool(product["is_extra"]), bool(settings.cryptobot_token))
    photo_path = product["photo_path"]
    screenshot_path = product["screenshot_path"]

    if photo_path and Path(photo_path).exists():
        await callback.message.answer_photo(FSInputFile(photo_path), caption=text, reply_markup=markup)
        if screenshot_path and Path(screenshot_path).exists():
            await callback.message.answer_photo(FSInputFile(screenshot_path), caption="📊 Реальный скриншот результата")
        await callback.message.delete()
    else:
        await callback.message.edit_text(
            f"{text}\n\n📸 Фото/скриншоты подключаются через поля товара: `{photo_path}`, `{screenshot_path}`",
            parse_mode="Markdown",
            reply_markup=markup,
        )


@router.callback_query(lambda c: c.data in {"catalog", "demo_catalog"})
async def catalog(callback: CallbackQuery, products: ProductRepository) -> None:
    rows = await products.categories()
    prefix = "demo_cat" if callback.data == "demo_catalog" else "cat"
    await callback.message.edit_text(
        "Выберите раздел. Логика везде одинаковая: раздел → подкатегория → тип оптимизации → товар.",
        reply_markup=catalog_categories(rows, prefix=prefix),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("cat:") or c.data.startswith("demo_cat:"))
async def category(callback: CallbackQuery, products: ProductRepository) -> None:
    prefix, key = callback.data.split(":", 1)
    category_name = get(key)
    if not category_name:
        await callback.answer("Кнопка устарела. Откройте каталог заново.", show_alert=True)
        return
    rows = await products.subcategories(category_name)
    sub_prefix = "demo_sub" if prefix == "demo_cat" else "sub"
    await callback.message.edit_text(f"{category_name}\n\nВыберите подкатегорию или игру:", reply_markup=subcategories(rows, category_name, sub_prefix))
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("sub:") or c.data.startswith("demo_sub:"))
async def subcategory(callback: CallbackQuery, products: ProductRepository) -> None:
    prefix, key = callback.data.split(":", 1)
    value = get(key)
    if not value:
        await callback.answer("Кнопка устарела. Откройте каталог заново.", show_alert=True)
        return
    category_name, subcategory_name = value
    rows = await products.optimization_types(category_name, subcategory_name)
    type_prefix = "demo_type" if prefix == "demo_sub" else "type"
    await callback.message.edit_text(
        f"{category_name} → {subcategory_name}\n\nВыберите тип оптимизации:",
        reply_markup=optimization_types(rows, category_name, subcategory_name, type_prefix),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("type:") or c.data.startswith("demo_type:"))
async def optimization_type(callback: CallbackQuery, products: ProductRepository) -> None:
    prefix, key = callback.data.split(":", 1)
    value = get(key)
    if not value:
        await callback.answer("Кнопка устарела. Откройте каталог заново.", show_alert=True)
        return
    category_name, subcategory_name, optimization_name = value
    rows = await products.by_path(category_name, subcategory_name, optimization_name)
    await callback.message.edit_text(
        f"{category_name} → {subcategory_name} → {optimization_name}\n\nВыберите товар:",
        reply_markup=products_keyboard(rows, category_name, subcategory_name, optimization_name, demo=prefix == "demo_type"),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("product:"))
async def product(callback: CallbackQuery, products: ProductRepository, settings: Settings) -> None:
    product_id = int(callback.data.split(":")[1])
    item = await products.get(product_id)
    if not item:
        await callback.answer("Товар не найден", show_alert=True)
        return
    await _show_product(callback, item, settings)
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("risk_ok:"))
async def risk_ok(callback: CallbackQuery, products: ProductRepository, settings: Settings) -> None:
    product_id = int(callback.data.split(":")[1])
    item = await products.get(product_id)
    if not item or not item["is_extra"]:
        await callback.answer("Товар не найден", show_alert=True)
        return
    await callback.message.edit_text(
        "⚠️ Вы подтвердили, что понимаете риски.\n\n"
        "Данный файл может изменить системные настройки и повлиять на работу Windows. "
        "Используйте на свой страх и риск. После покупки будет выдан основной файл и restore-инструкция/файл.",
        reply_markup=extra_confirmed_actions(product_id, bool(settings.cryptobot_token)),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("demo_product:"))
async def demo_product(callback: CallbackQuery, products: ProductRepository, settings: Settings) -> None:
    product_id = int(callback.data.split(":")[1])
    item = await products.get(product_id)
    if not item:
        await callback.answer("Товар не найден", show_alert=True)
        return
    await callback.message.edit_text(
        f"🎁 Демо для {item['title']}\n\n{DEMO_NOTE}\n\n"
        "Для получения демо нужно подписаться на Telegram-канал бота.",
        reply_markup=demo_requirements(settings.required_channel, product_id),
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("check_demo:"))
async def check_demo(
    callback: CallbackQuery,
    bot: Bot,
    products: ProductRepository,
    orders: OrderRepository,
    settings: Settings,
) -> None:
    product_id = int(callback.data.split(":")[1])
    item = await products.get(product_id)
    if not item:
        await callback.answer("Товар не найден", show_alert=True)
        return

    try:
        member = await bot.get_chat_member(settings.required_channel, callback.from_user.id)
        is_member = member.status in {"member", "administrator", "creator"}
    except Exception:
        is_member = False

    if not is_member:
        await callback.answer("Сначала подпишитесь на канал, затем нажмите проверку снова.", show_alert=True)
        return

    if await orders.has_demo(callback.from_user.id, product_id):
        await callback.answer("Демо уже выдавалось ранее.", show_alert=True)
        return

    await orders.add_demo(callback.from_user.id, product_id)
    await send_file_or_notice(bot, callback.from_user.id, item["demo_file_path"], f"🎁 Демо-файл: {item['title']}\n\n{DEMO_NOTE}")
    await callback.answer("Демо отправлено в личные сообщения.")


@router.callback_query(lambda c: c.data.startswith("subscribe_product:"))
async def subscribe_product(callback: CallbackQuery, products: ProductRepository, subscriptions_repo: SubscriptionRepository) -> None:
    product_id = int(callback.data.split(":")[1])
    item = await products.get(product_id)
    if not item:
        await callback.answer("Товар не найден", show_alert=True)
        return
    await subscriptions_repo.create(callback.from_user.id, "product", item["title"])
    await callback.message.edit_text(
        "🔔 Подписка оформлена.\n\n"
        f"Вы будете получать новые файлы для «{item['title']}» каждый месяц. "
        "В обновлениях будет указано: «обновление под новый патч игры».",
        reply_markup=back_to_main(),
    )
    await callback.answer()
