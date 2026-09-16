"""Отправка сообщений в каналы через Telethon."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from loguru import logger
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError

#: Пауза между каналами, чтобы не упереться во флуд-контроль Telegram.
SEND_DELAY_SECONDS = 1.0


@dataclass
class SendReport:
    """Итог одного прохода рассылки по списку каналов."""

    sent: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.sent) + len(self.failed)

    def summary(self) -> str:
        return f"отправлено {len(self.sent)}/{self.total}, ошибок {len(self.failed)}"


class ChannelSender:
    """Единственная точка, где приложение разговаривает с Telethon."""

    def __init__(self, client: TelegramClient, send_delay: float = SEND_DELAY_SECONDS) -> None:
        self._client = client
        self._send_delay = send_delay

    async def send(self, channel: str, text: str) -> str | None:
        """Отправляет сообщение в один канал.

        Возвращает `None` при успехе или описание ошибки — исключения
        наружу не пробрасываются, чтобы цикл рассылки не падал.
        """
        try:
            await self._client.send_message(channel, text)
        except FloodWaitError as exc:
            reason = f"флуд-контроль, нужно подождать {exc.seconds} c"
        except RPCError as exc:
            reason = f"ошибка Telegram: {exc.__class__.__name__}"
        except (ValueError, TypeError) as exc:
            reason = f"канал недоступен: {exc}"
        except Exception as exc:  # noqa: BLE001 — цикл рассылки не должен падать
            reason = f"неожиданная ошибка: {exc.__class__.__name__}: {exc}"
        else:
            logger.info("Сообщение отправлено в {}", channel)
            return None

        logger.error("Не удалось отправить в {}: {}", channel, reason)
        return reason

    async def send_to_all(self, channels: list[str], text: str) -> SendReport:
        """Проходит по всем каналам и собирает отчёт об отправке."""
        report = SendReport()
        for index, channel in enumerate(channels):
            error = await self.send(channel, text)
            if error is None:
                report.sent.append(channel)
            else:
                report.failed.append((channel, error))
            if index < len(channels) - 1:
                await asyncio.sleep(self._send_delay)
        return report
