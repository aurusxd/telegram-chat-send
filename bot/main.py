"""Точка входа.

Слайс 1: рассылка настраивается через .env, управляющего бота ещё нет.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402
from telethon import TelegramClient  # noqa: E402

from broadcast.scheduler import Scheduler  # noqa: E402
from broadcast.sender import ChannelSender  # noqa: E402
from core.config import SESSION_PATH, ConfigError, ensure_dirs, load_config  # noqa: E402
from core.state import State  # noqa: E402


async def run() -> None:
    ensure_dirs()
    config = load_config()

    state = State(
        channels=[config.channel],
        message_text=config.message_text,
        interval_minutes=config.interval_minutes,
    )

    client = TelegramClient(str(SESSION_PATH), config.api_id, config.api_hash)
    # Первый запуск спросит телефон и код, дальше сессия переиспользуется.
    await client.start()
    logger.info("Telethon-клиент авторизован, сессия: {}.session", SESSION_PATH)

    scheduler = Scheduler(ChannelSender(client), state)
    scheduler.start()
    try:
        await scheduler.wait()
    finally:
        scheduler.stop()
        await client.disconnect()


def main() -> int:
    try:
        asyncio.run(run())
    except ConfigError as exc:
        logger.error("Ошибка конфигурации: {}", exc)
        return 1
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
