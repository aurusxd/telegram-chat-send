"""Точка входа: собирает Telethon-клиент, управляющего бота и слайсы."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402
from loguru import logger  # noqa: E402
from telethon import TelegramClient  # noqa: E402

from broadcast import handlers as broadcast_handlers  # noqa: E402
from broadcast.scheduler import Scheduler  # noqa: E402
from broadcast.sender import ChannelSender  # noqa: E402
from core import menu  # noqa: E402
from core.config import SESSION_PATH, Config, ConfigError, ensure_dirs, load_config  # noqa: E402
from core.security import protect  # noqa: E402
from core.state import State  # noqa: E402


class Application:
    """Связывает состояние, Telethon и управляющего бота."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._state = State(
            channels=[config.channel],
            message_text=config.message_text,
            interval_minutes=config.interval_minutes,
        )
        self._client = TelegramClient(str(SESSION_PATH), config.api_id, config.api_hash)
        self._scheduler = Scheduler(ChannelSender(self._client), self._state)
        self._bot = Bot(token=config.bot_token)
        self._dispatcher = self._build_dispatcher()

    def _build_dispatcher(self) -> Dispatcher:
        """Регистрирует зависимости и роутеры всех слайсов."""
        dispatcher = Dispatcher(storage=MemoryStorage())
        dispatcher["app_state"] = self._state
        dispatcher["scheduler"] = self._scheduler
        protect(dispatcher, self._config.owner_id)
        dispatcher.include_router(menu.router)
        dispatcher.include_router(broadcast_handlers.router)
        return dispatcher

    async def run(self) -> None:
        # Первый запуск спросит телефон и код, дальше сессия переиспользуется.
        await self._client.start()
        logger.info("Telethon-клиент авторизован, сессия: {}.session", SESSION_PATH)
        logger.info("Управляющий бот запущен, владелец: {}", self._config.owner_id)
        try:
            await self._dispatcher.start_polling(self._bot)
        finally:
            await self._shutdown()

    async def _shutdown(self) -> None:
        self._scheduler.stop()
        await self._client.disconnect()
        await self._bot.session.close()
        logger.info("Приложение остановлено")


async def run() -> None:
    ensure_dirs()
    await Application(load_config()).run()


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
