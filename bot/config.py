from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    db_path: Path
    required_channel: str
    required_channel_url: str | None
    reviews_channel_url: str
    support_username: str
    enable_telegram_stars: bool
    cryptobot_token: str | None
    cryptobot_api_url: str
    assets_dir: Path


def _parse_admin_ids(raw: str) -> set[int]:
    return {int(item.strip()) for item in raw.split(",") if item.strip().isdigit()}


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required. Copy .env.example to .env and fill it.")

    return Settings(
        bot_token=bot_token,
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        db_path=Path(os.getenv("DB_PATH", "data/bot.sqlite3")),
        required_channel=os.getenv("REQUIRED_CHANNEL", "@your_demo_channel").strip(),
        required_channel_url=(os.getenv("REQUIRED_CHANNEL_URL") or "").strip() or None,
        reviews_channel_url=os.getenv("REVIEWS_CHANNEL_URL", "https://t.me/your_reviews_channel").strip(),
        support_username=os.getenv("SUPPORT_USERNAME", "@your_admin_username").strip(),
        enable_telegram_stars=os.getenv("ENABLE_TELEGRAM_STARS", "true").lower() == "true",
        cryptobot_token=os.getenv("CRYPTOBOT_TOKEN") or None,
        cryptobot_api_url=os.getenv("CRYPTOBOT_API_URL", "https://pay.crypt.bot/api").rstrip("/"),
        assets_dir=Path(os.getenv("ASSETS_DIR", "data/assets")),
    )
