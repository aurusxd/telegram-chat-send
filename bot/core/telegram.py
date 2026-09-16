"""Создание Hydrogram-клиента: сессия, прокси, параметры подключения."""

from __future__ import annotations

from hydrogram import Client
from loguru import logger

from core.config import DATA_DIR, Config, ProxySettings, session_file


def _proxy_dict(proxy: ProxySettings | None) -> dict | None:
    """Переводит настройки прокси в формат Hydrogram."""
    if proxy is None:
        return None
    settings: dict[str, object] = {
        "scheme": proxy.kind,
        "hostname": proxy.host,
        "port": proxy.port,
    }
    if proxy.username:
        settings["username"] = proxy.username
    if proxy.password:
        settings["password"] = proxy.password
    return settings


def describe_connection(config: Config) -> str:
    """Строка для логов: как именно бот идёт в Telegram."""
    if config.proxy is None:
        return "напрямую"
    return f"через {config.proxy.kind} {config.proxy.host}:{config.proxy.port}"


def build_client(config: Config) -> Client:
    """Единая точка создания Hydrogram-клиента для бота и скриптов.

    Вызывать только внутри запущенного event loop: конструктор Hydrogram
    обращается к `asyncio.get_event_loop()`.
    """
    path = session_file(config.session_name)
    logger.info(
        "Клиент Telegram: сессия {} ({}), подключение {}",
        path,
        "найдена" if path.exists() else "будет создана",
        describe_connection(config),
    )
    return Client(
        name=config.session_name,
        api_id=config.api_id,
        api_hash=config.api_hash,
        workdir=str(DATA_DIR),
        proxy=_proxy_dict(config.proxy),
        # Бот только отправляет сообщения, входящие апдейты ему не нужны.
        no_updates=True,
    )
