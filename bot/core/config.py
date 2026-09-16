"""Пути проекта и загрузка конфигурации из .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
SESSION_PATH = DATA_DIR / "session"
STATE_PATH = DATA_DIR / "state.json"


class ConfigError(RuntimeError):
    """Конфигурация отсутствует или некорректна."""


@dataclass(frozen=True)
class Config:
    """Значения из .env, необходимые для запуска."""

    api_id: int
    api_hash: str
    channel: str
    message_text: str
    interval_minutes: int


def ensure_dirs() -> None:
    """Создаёт каталоги для сессии, состояния и логов."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _require(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise ConfigError(f"В .env не задана переменная {name}")
    return value


def _require_int(name: str, *, minimum: int | None = None) -> int:
    raw = _require(name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} должен быть целым числом, получено: {raw!r}") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} должен быть не меньше {minimum}, получено: {value}")
    return value


def load_config() -> Config:
    """Читает .env и валидирует значения до старта приложения."""
    load_dotenv(BASE_DIR / ".env")
    return Config(
        api_id=_require_int("API_ID", minimum=1),
        api_hash=_require("API_HASH"),
        channel=_require("CHANNEL"),
        message_text=_require("MESSAGE_TEXT"),
        interval_minutes=_require_int("INTERVAL_MINUTES", minimum=1),
    )
