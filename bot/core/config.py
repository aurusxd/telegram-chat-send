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
LOG_PATH = LOGS_DIR / "bot.log"


DEFAULT_LOG_LEVEL = "INFO"

#: Интервал по умолчанию, если он не задан ни в .env, ни в state.json.
DEFAULT_INTERVAL_MINUTES = 15


class ConfigError(RuntimeError):
    """Конфигурация отсутствует или некорректна."""


@dataclass(frozen=True)
class Config:
    """Значения из .env, необходимые для запуска."""

    api_id: int
    api_hash: str
    bot_token: str
    owner_id: int
    default_message_text: str
    default_interval_minutes: int
    log_level: str


def ensure_dirs() -> None:
    """Создаёт каталоги для сессии, состояния и логов."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _require(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise ConfigError(f"В .env не задана переменная {name}")
    return value


def _optional(name: str, fallback: str = "") -> str:
    return (os.getenv(name) or "").strip() or fallback


def _require_int(name: str, *, minimum: int | None = None) -> int:
    raw = _require(name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} должен быть целым числом, получено: {raw!r}") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} должен быть не меньше {minimum}, получено: {value}")
    return value


def _optional_int(name: str, fallback: int, *, minimum: int = 1) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return fallback
    return _require_int(name, minimum=minimum)


def load_config() -> Config:
    """Читает .env и валидирует значения до старта приложения."""
    load_dotenv(BASE_DIR / ".env")
    return Config(
        api_id=_require_int("API_ID", minimum=1),
        api_hash=_require("API_HASH"),
        bot_token=_require("BOT_TOKEN"),
        owner_id=_require_int("OWNER_ID", minimum=1),
        default_message_text=_optional("MESSAGE_TEXT"),
        default_interval_minutes=_optional_int("INTERVAL_MINUTES", DEFAULT_INTERVAL_MINUTES),
        log_level=_optional("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
    )
