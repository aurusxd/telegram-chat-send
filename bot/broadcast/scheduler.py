"""Цикл периодической рассылки."""

from __future__ import annotations

import asyncio

from loguru import logger

from broadcast.sender import ChannelSender
from core.state import State


class Scheduler:
    """Управляет фоновой задачей рассылки: start / stop."""

    def __init__(self, sender: ChannelSender, state: State) -> None:
        self._sender = sender
        self._state = state
        self._task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> bool:
        """Запускает цикл. Возвращает False, если он уже запущен."""
        if self.is_running:
            return False
        self._task = asyncio.create_task(self._loop())
        self._state.is_running = True
        logger.info(
            "Рассылка запущена: каналов {}, интервал {} мин",
            len(self._state.channels),
            self._state.interval_minutes,
        )
        return True

    def stop(self) -> bool:
        """Останавливает цикл. Возвращает False, если он и так стоял."""
        if self._task is None:
            self._state.is_running = False
            return False
        self._task.cancel()
        self._task = None
        self._state.is_running = False
        logger.info("Рассылка остановлена")
        return True

    async def wait(self) -> None:
        """Ждёт завершения задачи рассылки (используется точкой входа)."""
        if self._task is not None:
            await asyncio.shield(self._task)

    async def _loop(self) -> None:
        try:
            while True:
                report = await self._sender.send_to_all(
                    list(self._state.channels), self._state.message_text
                )
                logger.info("Проход рассылки завершён: {}", report.summary())
                await asyncio.sleep(max(1, self._state.interval_minutes) * 60)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — задача не должна умирать молча
            logger.exception("Цикл рассылки аварийно завершился: {}", exc)
            self._state.is_running = False
            raise
