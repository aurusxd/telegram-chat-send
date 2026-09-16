"""Отправка сообщений в каналы через Hydrogram."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from hydrogram import Client
from hydrogram.errors import FloodWait, RPCError
from loguru import logger

#: Пауза между каналами, чтобы не упереться во флуд-контроль Telegram.
SEND_DELAY_SECONDS = 1.0


def to_peer(channel: str) -> int | str:
    """Приводит канал к типу, который ждёт Hydrogram.

    Числовой ID нужно передавать именно `int`: строку из цифр Hydrogram
    принимает за номер телефона и не находит получателя.
    """
    value = channel.strip()
    if value.lstrip("-").isdigit():
        return int(value)
    return value


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
    """Единственная точка, где приложение разговаривает с Hydrogram."""

    def __init__(self, client: Client, send_delay: float = SEND_DELAY_SECONDS) -> None:
        self._client = client
        self._send_delay = send_delay
        self._peers_warmed = False

    async def _warm_up_peers(self) -> None:
        """Подтягивает диалоги, чтобы Hydrogram знал access_hash каналов.

        Нужно, когда канал задан числовым ID или сессия принесена из другого
        проекта: без локального кеша пиров Telegram отвечает PeerIdInvalid.
        """
        if self._peers_warmed:
            return
        self._peers_warmed = True
        try:
            count = 0
            async for _ in self._client.get_dialogs():
                count += 1
            logger.info("Кеш диалогов обновлён: {} чатов", count)
        except Exception as exc:  # noqa: BLE001 — прогрев не должен ломать рассылку
            logger.warning("Не удалось обновить кеш диалогов: {}", exc)

    async def send(self, channel: str, text: str) -> str | None:
        """Отправляет сообщение в один канал.

        Возвращает `None` при успехе или описание ошибки — исключения
        наружу не пробрасываются, чтобы цикл рассылки не падал.
        """
        for attempt in (1, 2):
            try:
                await self._client.send_message(to_peer(channel), text)
            except FloodWait as exc:
                return f"флуд-контроль, нужно подождать {exc.value} c"
            except KeyError:
                # Пир не найден в локальном кеше — обновляем его и пробуем ещё раз.
                if attempt == 1 and not self._peers_warmed:
                    await self._warm_up_peers()
                    continue
                reason = "канал не найден: проверьте username/ID и доступ аккаунта"
            except RPCError as exc:
                if attempt == 1 and not self._peers_warmed and "PEER_ID_INVALID" in str(exc):
                    await self._warm_up_peers()
                    continue
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

        return "не удалось отправить после повторной попытки"

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
