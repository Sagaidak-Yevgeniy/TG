from __future__ import annotations

from secrets import token_urlsafe
from time import time
from typing import Any

_CACHE: dict[str, tuple[float, Any]] = {}
TTL_SECONDS = 60 * 60


def put(value: Any) -> str:
    cleanup()
    key = token_urlsafe(6)
    _CACHE[key] = (time() + TTL_SECONDS, value)
    return key


def get(key: str) -> Any | None:
    item = _CACHE.get(key)
    if not item:
        return None
    expires_at, value = item
    if expires_at < time():
        _CACHE.pop(key, None)
        return None
    return value


def cleanup() -> None:
    now = time()
    expired = [key for key, (expires_at, _) in _CACHE.items() if expires_at < now]
    for key in expired:
        _CACHE.pop(key, None)
