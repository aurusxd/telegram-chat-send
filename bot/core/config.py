"""Пути проекта и загрузка конфигурации из .env."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
STATE_PATH = DATA_DIR / "state.json"
LOG_PATH = LOGS_DIR / "bot.log"

DEFAULT_LOG_LEVEL = "INFO"

#: Интервал по умолчанию, если он не задан ни в .env, ни в state.json.
DEFAULT_INTERVAL_MINUTES = 15

#: Имя файла сессии Hydrogram внутри data/ (без расширения .session).
DEFAULT_SESSION_NAME = "session"
_SESSION_NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

#: Типы прокси, поддерживаемые Hydrogram (MTProxy он не умеет).
PROXY_TYPES = ("socks5", "socks4", "http")


class ConfigError(RuntimeError):
    """Конфигурация отсутствует или некорректна."""


@dataclass(frozen=True)
class ProxySettings:
    """Параметры прокси для подключения к Telegram."""

    kind: str
    host: str
    port: int
    username: str | None = None
    password: str | None = None


@dataclass(frozen=True)
class Config:
    """Значения из .env, необходимые для запуска."""

    api_id: int
    api_hash: str
    bot_token: str
    owner_id: int
    session_name: str
    default_message_text: str
    default_interval_minutes: int
    log_level: str
    proxy: ProxySettings | None


def session_file(session_name: str) -> Path:
    """Путь к файлу сессии Hydrogram."""
    return DATA_DIR / f"{session_name}.session"


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
    if not (os.getenv(name) or "").strip():
        return fallback
    return _require_int(name, minimum=minimum)


def _session_name() -> str:
    """Имя сессии; лишнее расширение .session отбрасывается."""
    name = _optional("SESSION_NAME", DEFAULT_SESSION_NAME)
    if name.endswith(".session"):
        name = name[: -len(".session")]
    if not _SESSION_NAME_RE.match(name):
        raise ConfigError(
            "SESSION_NAME может содержать только латиницу, цифры, точку, дефис и «_». "
            f"Получено: {name}"
        )
    return name


def _load_proxy() -> ProxySettings | None:
    """Собирает настройки прокси; пустой PROXY_TYPE значит «без прокси»."""
    kind = _optional("PROXY_TYPE").lower()
    if not kind:
        return None
    if kind not in PROXY_TYPES:
        raise ConfigError(
            f"PROXY_TYPE должен быть одним из {', '.join(PROXY_TYPES)}. Получено: {kind}"
        )
    return ProxySettings(
        kind=kind,
        host=_require("PROXY_HOST"),
        port=_require_int("PROXY_PORT", minimum=1),
        username=_optional("PROXY_USER") or None,
        password=_optional("PROXY_PASS") or None,
    )


def load_config() -> Config:
    """Читает .env и валидирует значения до старта приложения."""
    load_dotenv(BASE_DIR / ".env")
    return Config(
        api_id=_require_int("API_ID", minimum=1),
        api_hash=_require("API_HASH"),
        bot_token=_require("BOT_TOKEN"),
        owner_id=_require_int("OWNER_ID", minimum=1),
        session_name=_session_name(),
        default_message_text=_optional("MESSAGE_TEXT"),
        default_interval_minutes=_optional_int("INTERVAL_MINUTES", DEFAULT_INTERVAL_MINUTES),
        log_level=_optional("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
        proxy=_load_proxy(),
    )
