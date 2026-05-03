from __future__ import annotations

from bot.repositories.products import ProductRepository


DEMO_NOTE = (
    "Это облегчённая версия — полный файл даёт значительно большый прирост FPS и стабильности"
)


SEED_PRODUCTS: list[dict] = [
    {
        "title": "FPS BOOST PRO V3",
        "badge": "🔥 Популярное",
        "category": "🕹 Оптимизация для игр",
        "subcategory": "🎯 CS2",
        "optimization_type": "⚡ FPS BOOST",
        "game": "CS2",
        "price": 149,
        "before_fps": 145,
        "after_fps": 238,
        "description": (
            "Пакет поднимает средний FPS, отключает лишние фоновые задержки Windows и стабилизирует frametime. "
            "Подходит для CS2 на слабых и средних ПК. Ожидаемый результат: +30-70 FPS и меньше просадок."
        ),
        "photo_path": "data/assets/photos/cs2_fps_boost.jpg",
        "screenshot_path": "data/assets/photos/cs2_fps_boost_result.jpg",
        "full_file_path": "data/assets/full/cs2_fps_boost_pro_v3.zip",
        "demo_file_path": "data/assets/demo/cs2_fps_boost_demo.zip",
        "is_extra": 0,
        "restore_file_path": "",
    },
    {
        "title": "LOW LATENCY PACK",
        "badge": "💎 Рекомендуем",
        "category": "🕹 Оптимизация для игр",
        "subcategory": "🔫 Valorant",
        "optimization_type": "🎯 LOW INPUT LAG",
        "game": "Valorant",
        "price": 129,
        "before_fps": 180,
        "after_fps": 224,
        "description": (
            "Настройки для снижения input lag, оптимизации сети и отклика мыши. "
            "Подходит для Valorant, CS2, Fortnite. Ожидаемый результат: плавнее стрельба и ниже задержка ввода."
        ),
        "photo_path": "data/assets/photos/valorant_latency.jpg",
        "screenshot_path": "data/assets/photos/valorant_latency_result.jpg",
        "full_file_path": "data/assets/full/low_latency_pack.zip",
        "demo_file_path": "data/assets/demo/low_latency_pack_demo.zip",
        "is_extra": 0,
        "restore_file_path": "",
    },
    {
        "title": "ULTIMATE GAMING TWEAK",
        "badge": "🆕 Новинка",
        "category": "🕹 Оптимизация для игр",
        "subcategory": "🏰 Fortnite",
        "optimization_type": "🏆 COMPETITIVE PRESET",
        "game": "Fortnite",
        "price": 199,
        "before_fps": 110,
        "after_fps": 190,
        "description": (
            "Соревновательный пресет для Fortnite: чистит лишние эффекты, улучшает стабильность и снижает микрофризы. "
            "Ожидаемый результат: стабильнее FPS в файтах и меньше статтеров."
        ),
        "photo_path": "data/assets/photos/fortnite_competitive.jpg",
        "screenshot_path": "data/assets/photos/fortnite_competitive_result.jpg",
        "full_file_path": "data/assets/full/ultimate_gaming_tweak.zip",
        "demo_file_path": "data/assets/demo/ultimate_gaming_tweak_demo.zip",
        "is_extra": 0,
        "restore_file_path": "",
    },
    {
        "title": "PING DOWN GUIDE",
        "badge": "💎 Рекомендуем",
        "category": "📘 Гайды",
        "subcategory": "🌐 Сеть и пинг",
        "optimization_type": "🎯 LOW INPUT LAG",
        "game": "CS2 / Valorant / Warzone",
        "price": 79,
        "before_fps": 120,
        "after_fps": 132,
        "description": (
            "PDF-гайд по снижению пинга: DNS, роутер, Windows network stack, выбор сервера и проверка потерь пакетов. "
            "Подходит для онлайн-шутеров. Ожидаемый результат: меньше jitter и стабильнее соединение."
        ),
        "photo_path": "data/assets/photos/ping_guide.jpg",
        "screenshot_path": "data/assets/photos/ping_guide_result.jpg",
        "full_file_path": "data/assets/full/ping_down_guide.pdf",
        "demo_file_path": "data/assets/demo/ping_down_guide_demo.pdf",
        "is_extra": 0,
        "restore_file_path": "",
    },
    {
        "title": "PRO PLAYER CFG PACK",
        "badge": "🔥 Популярное",
        "category": "🎮 Файлы от про-игроков",
        "subcategory": "🎯 CS2",
        "optimization_type": "🏆 COMPETITIVE PRESET",
        "game": "CS2",
        "price": 249,
        "before_fps": 160,
        "after_fps": 215,
        "description": (
            "Комплект CFG и launch-настроек в стиле киберспортсменов: видимость, отклик, FPS, стабильные бинды. "
            "Подходит для CS2. Ожидаемый результат: удобнее соревновательная игра и выше стабильность."
        ),
        "photo_path": "data/assets/photos/pro_cfg.jpg",
        "screenshot_path": "data/assets/photos/pro_cfg_result.jpg",
        "full_file_path": "data/assets/full/pro_player_cfg_pack.zip",
        "demo_file_path": "data/assets/demo/pro_player_cfg_pack_demo.zip",
        "is_extra": 0,
        "restore_file_path": "",
    },
    {
        "title": "EXTREME WINDOWS FPS MAX",
        "badge": "💎 Рекомендуем",
        "category": "⚠️ Экстро оптимизация",
        "subcategory": "🪟 Windows",
        "optimization_type": "⚡ FPS BOOST",
        "game": "Все игры",
        "price": 299,
        "before_fps": 95,
        "after_fps": 175,
        "description": (
            "Агрессивные настройки системы: службы, план питания, автозагрузка, визуальные эффекты и сетевые параметры. "
            "Только для опытных пользователей. Возможны побочные эффекты в Windows."
        ),
        "photo_path": "data/assets/photos/extreme_windows.jpg",
        "screenshot_path": "data/assets/photos/extreme_windows_result.jpg",
        "full_file_path": "data/assets/full/extreme_windows_fps_max.zip",
        "demo_file_path": "data/assets/demo/extreme_windows_demo.zip",
        "is_extra": 1,
        "restore_file_path": "data/assets/full/extreme_windows_restore.zip",
    },
]


async def seed_catalog(products: ProductRepository) -> None:
    if await products.count() > 0:
        return
    for product in SEED_PRODUCTS:
        await products.create(product)
