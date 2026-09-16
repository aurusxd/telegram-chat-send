"""Создание Telethon-клиента: транспорт, прокси, параметры переподключения."""

from __future__ import annotations

from loguru import logger
from telethon import TelegramClient
from telethon.network import (
    ConnectionTcpAbridged,
    ConnectionTcpFull,
    ConnectionTcpIntermediate,
    ConnectionTcpMTProxyRandomizedIntermediate,
    ConnectionTcpObfuscated,
)

from core.config import SESSION_PATH, Config, ProxySettings

#: Имя режима из .env -> класс транспорта Telethon.
CONNECTION_CLASSES = {
    "full": ConnectionTcpFull,
    "abridged": ConnectionTcpAbridged,
    "intermediate": ConnectionTcpIntermediate,
    "obfuscated": ConnectionTcpObfuscated,
}

#: Сколько раз Telethon пробует переподключиться, прежде чем сдаться.
CONNECTION_RETRIES = 5
RETRY_DELAY_SECONDS = 2
CONNECT_TIMEOUT_SECONDS = 20


def _proxy_kwargs(proxy: ProxySettings | None, connection_mode: str) -> dict:
    """Готовит аргументы транспорта и прокси для TelegramClient."""
    if proxy is None:
        return {"connection": CONNECTION_CLASSES[connection_mode]}

    if proxy.is_mtproxy:
        # MTProxy работает только со своим транспортом.
        return {
            "connection": ConnectionTcpMTProxyRandomizedIntermediate,
            "proxy": (proxy.host, proxy.port, proxy.secret),
        }

    settings: dict[str, object] = {
        "proxy_type": proxy.kind,
        "addr": proxy.host,
        "port": proxy.port,
        "rdns": True,
    }
    if proxy.username:
        settings["username"] = proxy.username
    if proxy.password:
        settings["password"] = proxy.password
    return {"connection": CONNECTION_CLASSES[connection_mode], "proxy": settings}


def describe_connection(config: Config) -> str:
    """Строка для логов: как именно бот идёт в Telegram."""
    if config.proxy is None:
        return f"напрямую, транспорт {config.connection_mode}"
    proxy = config.proxy
    transport = "mtproxy" if proxy.is_mtproxy else config.connection_mode
    return f"через {proxy.kind} {proxy.host}:{proxy.port}, транспорт {transport}"


def build_client(config: Config) -> TelegramClient:
    """Единая точка создания Telethon-клиента для бота и скриптов."""
    logger.info("Подключение к Telegram: {}", describe_connection(config))
    return TelegramClient(
        str(SESSION_PATH),
        config.api_id,
        config.api_hash,
        connection_retries=CONNECTION_RETRIES,
        retry_delay=RETRY_DELAY_SECONDS,
        timeout=CONNECT_TIMEOUT_SECONDS,
        **_proxy_kwargs(config.proxy, config.connection_mode),
    )
