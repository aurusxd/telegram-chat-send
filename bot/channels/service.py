"""Логика работы со списком каналов."""

from __future__ import annotations

import re
from collections.abc import Callable

from loguru import logger

from core.errors import ValidationError
from core.state import State, save_state

MAX_CHANNELS = 100

_LINK_PREFIXES = ("https://t.me/", "http://t.me/", "t.me/")
_USERNAME_RE = re.compile(r"^[a-z][a-z0-9_]{3,30}[a-z0-9]$")


class ChannelService:
    """Добавление, удаление и хранение списка каналов."""

    def __init__(self, state: State, save: Callable[[State], None] = save_state) -> None:
        self._state = state
        self._save = save

    @property
    def channels(self) -> list[str]:
        return list(self._state.channels)

    @staticmethod
    def normalize(raw: str) -> str:
        """Приводит ввод к `@username` или числовому id.

        Поднимает ValidationError с понятным текстом, если ввод не похож
        ни на username, ни на id канала.
        """
        value = (raw or "").strip()
        if not value:
            raise ValidationError("Пустой ввод. Пришлите @username или ID канала.")

        lowered = value.lower()
        for prefix in _LINK_PREFIXES:
            if lowered.startswith(prefix):
                value = value[len(prefix) :]
                break

        value = value.strip().lstrip("@")
        if not value:
            raise ValidationError("Пустой ввод. Пришлите @username или ID канала.")

        if value.lstrip("-").isdigit():
            try:
                return str(int(value))
            except ValueError as exc:  # pragma: no cover — отсекается isdigit()
                raise ValidationError(f"Некорректный ID канала: {value}") from exc

        username = value.lower()
        if not _USERNAME_RE.match(username):
            raise ValidationError(
                "Username должен быть длиной 5–32 символа: латиница, цифры и «_», "
                f"начинаться с буквы. Получено: {raw.strip()}"
            )
        return f"@{username}"

    def add(self, raw: str) -> str:
        """Добавляет канал в список и сохраняет состояние."""
        channel = self.normalize(raw)
        if channel in self._state.channels:
            raise ValidationError(f"Канал {channel} уже в списке.")
        if len(self._state.channels) >= MAX_CHANNELS:
            raise ValidationError(f"Достигнут лимит в {MAX_CHANNELS} каналов.")
        self._state.channels.append(channel)
        self._save(self._state)
        logger.info("Канал добавлен: {} (всего {})", channel, len(self._state.channels))
        return channel

    def remove(self, channel: str) -> str:
        """Удаляет канал из списка и сохраняет состояние."""
        value = (channel or "").strip()
        if value not in self._state.channels:
            value = self.normalize(channel)
        if value not in self._state.channels:
            raise ValidationError(f"Канала {value} нет в списке.")
        self._state.channels.remove(value)
        self._save(self._state)
        logger.info("Канал удалён: {} (осталось {})", value, len(self._state.channels))
        return value
