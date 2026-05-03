from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.keyboards.admin import admin_menu
from bot.keyboards.user import back_to_main
from bot.repositories.orders import OrderRepository
from bot.repositories.products import ProductRepository
from bot.repositories.subscriptions import SubscriptionRepository
from bot.repositories.users import UserRepository
from bot.states import AddProduct

router = Router()


def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


@router.callback_query(lambda c: c.data == "admin")
async def admin(callback: CallbackQuery, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.message.edit_text("🛠 Админ-панель", reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_products")
async def admin_products(callback: CallbackQuery, products: ProductRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    rows = await products.list_active()
    text = "📦 Товары\n\n" + "\n".join(
        f"#{row['id']} {row['title']} — {row['category']} / {row['subcategory']} / {row['optimization_type']} — {row['price']} ⭐"
        for row in rows[:50]
    )
    await callback.message.edit_text(text or "Товаров нет.", reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_users")
async def admin_users(callback: CallbackQuery, users: UserRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    rows = await users.list_users()
    lines = ["👥 Пользователи\n"]
    for row in rows:
        lines.append(
            f"• {row['telegram_id']} | рег: {row['registered_at']} | покупки: {row['purchases_count']} | баланс: {row['balance']} ⭐"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_sales")
async def admin_sales(callback: CallbackQuery, orders: OrderRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    rows = await orders.list_sales()
    lines = ["💰 Продажи\n"]
    for row in rows:
        lines.append(
            f"#{row['id']} | user {row['user_id']} | {row['title']} | {row['amount']} ⭐ | {row['provider']} | {row['created_at']}"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_subscriptions")
async def admin_subscriptions(callback: CallbackQuery, subscriptions_repo: SubscriptionRepository, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    rows = await subscriptions_repo.list_active()
    lines = ["🔔 Активные подписки\n"]
    for row in rows:
        lines.append(
            f"#{row['id']} | user {row['user_id']} | {row['scope_type']}: {row['scope_value']} | next: {row['next_delivery_at']}"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=admin_menu())
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin_add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await state.clear()
    await state.set_state(AddProduct.title)
    await callback.message.edit_text("➕ Добавление товара\n\nВведите название:")
    await callback.answer()


@router.message(AddProduct.title)
async def add_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text)
    await state.set_state(AddProduct.description)
    await message.answer("Введите описание:")


@router.message(AddProduct.description)
async def add_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text)
    await state.set_state(AddProduct.category)
    await message.answer("Введите раздел, например: 🕹 Оптимизация для игр")


@router.message(AddProduct.category)
async def add_category(message: Message, state: FSMContext) -> None:
    await state.update_data(category=message.text)
    await state.set_state(AddProduct.subcategory)
    await message.answer("Введите подкатегорию или игру, например: 🎯 CS2")


@router.message(AddProduct.subcategory)
async def add_subcategory(message: Message, state: FSMContext) -> None:
    await state.update_data(subcategory=message.text)
    await state.set_state(AddProduct.optimization_type)
    await message.answer("Введите тип оптимизации, например: ⚡ FPS BOOST")


@router.message(AddProduct.optimization_type)
async def add_optimization_type(message: Message, state: FSMContext) -> None:
    await state.update_data(optimization_type=message.text)
    await state.set_state(AddProduct.game)
    await message.answer("Введите игры, для которых подходит товар:")


@router.message(AddProduct.game)
async def add_game(message: Message, state: FSMContext) -> None:
    await state.update_data(game=message.text)
    await state.set_state(AddProduct.price)
    await message.answer("Введите цену в Telegram Stars числом:")


@router.message(AddProduct.price)
async def add_price(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("Цена должна быть числом.")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(AddProduct.badge)
    await message.answer("Введите метку: 🔥 Популярное / 🆕 Новинка / 💎 Рекомендуем / -")


@router.message(AddProduct.badge)
async def add_badge(message: Message, state: FSMContext) -> None:
    await state.update_data(badge="" if message.text == "-" else message.text)
    await state.set_state(AddProduct.before_fps)
    await message.answer("Введите FPS до оптимизации:")


@router.message(AddProduct.before_fps)
async def add_before_fps(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("FPS должен быть числом.")
        return
    await state.update_data(before_fps=int(message.text))
    await state.set_state(AddProduct.after_fps)
    await message.answer("Введите FPS после оптимизации:")


@router.message(AddProduct.after_fps)
async def add_after_fps(message: Message, state: FSMContext) -> None:
    if not message.text.isdigit():
        await message.answer("FPS должен быть числом.")
        return
    await state.update_data(after_fps=int(message.text))
    await state.set_state(AddProduct.photo_path)
    await message.answer("Введите путь к фото товара или -:")


@router.message(AddProduct.photo_path)
async def add_photo_path(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_path="" if message.text == "-" else message.text)
    await state.set_state(AddProduct.screenshot_path)
    await message.answer("Введите путь к скриншоту результата или -:")


@router.message(AddProduct.screenshot_path)
async def add_screenshot_path(message: Message, state: FSMContext) -> None:
    await state.update_data(screenshot_path="" if message.text == "-" else message.text)
    await state.set_state(AddProduct.full_file_path)
    await message.answer("Введите путь к полной версии файла:")


@router.message(AddProduct.full_file_path)
async def add_full_file_path(message: Message, state: FSMContext) -> None:
    await state.update_data(full_file_path=message.text)
    await state.set_state(AddProduct.demo_file_path)
    await message.answer("Введите путь к демо-файлу:")


@router.message(AddProduct.demo_file_path)
async def add_demo_file_path(message: Message, state: FSMContext) -> None:
    await state.update_data(demo_file_path=message.text)
    await state.set_state(AddProduct.is_extra)
    await message.answer("Это экстро оптимизация? Введите да/нет:")


@router.message(AddProduct.is_extra)
async def add_is_extra(message: Message, state: FSMContext) -> None:
    is_extra = message.text.lower() in {"да", "yes", "y", "1"}
    await state.update_data(is_extra=1 if is_extra else 0)
    await state.set_state(AddProduct.restore_file_path)
    await message.answer("Введите путь к restore-файлу/инструкции или -:")


@router.message(AddProduct.restore_file_path)
async def add_restore_file_path(message: Message, state: FSMContext, products: ProductRepository) -> None:
    await state.update_data(restore_file_path="" if message.text == "-" else message.text)
    data = await state.get_data()
    product_id = await products.create(data)
    await state.clear()
    await message.answer(f"✅ Товар #{product_id} добавлен.", reply_markup=back_to_main())
