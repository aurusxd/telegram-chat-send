"""Точка входа: собирает Telethon-клиент, управляющего бота и слайсы."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aiogram import Bot, Dispatcher  # noqa: E402
from aiogram.fsm.storage.memory import MemoryStorage  # noqa: E402
from loguru import logger  # noqa: E402

from broadcast import handlers as broadcast_handlers  # noqa: E402
from channels import handlers as channels_handlers  # noqa: E402
from channels.service import ChannelService  # noqa: E402
from broadcast.scheduler import Scheduler  # noqa: E402
from broadcast.sender import ChannelSender  # noqa: E402
from core import menu  # noqa: E402
from core.config import (  # noqa: E402
    DEFAULT_LOG_LEVEL,
    SESSION_PATH,
    Config,
    ConfigError,
    ensure_dirs,
    load_config,
)
from core.errors import TelegramConnectionError  # noqa: E402
from core.logger import setup_logging  # noqa: E402
from core.telegram import build_client  # noqa: E402
from core.security import protect  # noqa: E402
from core.state import State, load_state  # noqa: E402
from interval import handlers as interval_handlers  # noqa: E402
from interval.service import IntervalService  # noqa: E402
from message import handlers as message_handlers  # noqa: E402
from message.service import MessageService  # noqa: E402


class Application:
    """Связывает состояние, Telethon и управляющего бота."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._state = load_state(
            default=State(
                message_text=config.default_message_text,
                interval_minutes=config.default_interval_minutes,
            )
        )
        self._channel_service = ChannelService(self._state)
        self._message_service = MessageService(self._state)
        self._interval_service = IntervalService(self._state)
        self._client = build_client(config)
        self._scheduler = Scheduler(ChannelSender(self._client), self._state)
        self._bot = Bot(token=config.bot_token)
        self._dispatcher = self._build_dispatcher()

    def _build_dispatcher(self) -> Dispatcher:
        """Регистрирует зависимости и роутеры всех слайсов."""
        dispatcher = Dispatcher(storage=MemoryStorage())
        dispatcher["app_state"] = self._state
        dispatcher["scheduler"] = self._scheduler
        dispatcher["channel_service"] = self._channel_service
        dispatcher["message_service"] = self._message_service
        dispatcher["interval_service"] = self._interval_service
        protect(dispatcher, self._config.owner_id)
        dispatcher.include_router(menu.router)
        dispatcher.include_router(channels_handlers.router)
        dispatcher.include_router(message_handlers.router)
        dispatcher.include_router(interval_handlers.router)
        dispatcher.include_router(broadcast_handlers.router)
        return dispatcher

    async def run(self) -> None:
        # Первый запуск спросит телефон и код, дальше сессия переиспользуется.
        try:
            await self._client.start()
        except (OSError, EOFError, TimeoutError) as exc:
            raise TelegramConnectionError(
                f"соединение с Telegram оборвалось ({exc.__class__.__name__}: {exc})"
            ) from exc
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
    # Логи включаем до чтения .env, чтобы ошибки конфигурации тоже попали в файл.
    setup_logging()
    config = load_config()
    if config.log_level != DEFAULT_LOG_LEVEL:
        setup_logging(config.log_level)
    await Application(config).run()


def main() -> int:
    try:
        asyncio.run(run())
    except ConfigError as exc:
        logger.error("Ошибка конфигурации: {}", exc)
        return 1
    except TelegramConnectionError as exc:
        logger.error("Не удалось подключиться к Telegram: {}", exc)
        logger.error(
            "Похоже на блокировку трафика до серверов Telegram. Попробуйте "
            "CONNECTION_MODE=obfuscated или задайте прокси (PROXY_TYPE/PROXY_HOST/"
            "PROXY_PORT) в .env — подробности в README."
        )
        return 2
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
