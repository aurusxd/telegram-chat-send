"""Логика работы с текстом рассылки."""

from __future__ import annotations

from collections.abc import Callable

from loguru import logger

from core.errors import ValidationError
from core.state import State, save_state

#: Лимит Telegram на длину текстового сообщения.
MAX_MESSAGE_LENGTH = 4096


class MessageService:
    """Просмотр и изменение текста рассылки."""

    def __init__(self, state: State, save: Callable[[State], None] = save_state) -> None:
        self._state = state
        self._save = save

    @property
    def text(self) -> str:
        return self._state.message_text

    @property
    def is_empty(self) -> bool:
        return not self._state.message_text.strip()

    @staticmethod
    def validate(raw: str | None) -> str:
        """Проверяет текст перед сохранением."""
        text = (raw or "").strip()
        if not text:
            raise ValidationError("Текст не может быть пустым.")
        if len(text) > MAX_MESSAGE_LENGTH:
            raise ValidationError(
                f"Текст длиннее лимита Telegram: {len(text)} из {MAX_MESSAGE_LENGTH} символов."
            )
        return text

    def update(self, raw: str | None) -> str:
        """Сохраняет новый текст рассылки."""
        text = self.validate(raw)
        self._state.message_text = text
        self._save(self._state)
        logger.info("Текст рассылки изменён ({} символов)", len(text))
        return text
