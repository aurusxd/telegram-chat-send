"""Логика работы с интервалом рассылки."""

from __future__ import annotations

from collections.abc import Callable

from loguru import logger

from core.errors import ValidationError
from core.state import State, save_state

#: Пресеты для кнопок, минуты.
PRESETS = (15, 30, 60, 120)

MIN_INTERVAL_MINUTES = 1
#: Неделя — разумный потолок, выше которого значение почти наверняка опечатка.
MAX_INTERVAL_MINUTES = 7 * 24 * 60


class IntervalService:
    """Просмотр и изменение интервала между рассылками."""

    def __init__(self, state: State, save: Callable[[State], None] = save_state) -> None:
        self._state = state
        self._save = save

    @property
    def minutes(self) -> int:
        return self._state.interval_minutes

    @staticmethod
    def parse(raw: str | int | None) -> int:
        """Разбирает интервал из ввода пользователя или из callback-данных."""
        if raw is None or isinstance(raw, bool):
            raise ValidationError("Интервал должен быть целым числом минут.")
        if isinstance(raw, int):
            value = raw
        else:
            text = raw.strip()
            try:
                value = int(text)
            except ValueError as exc:
                raise ValidationError(
                    f"Интервал должен быть целым числом минут. Получено: {text}"
                ) from exc
        if not MIN_INTERVAL_MINUTES <= value <= MAX_INTERVAL_MINUTES:
            raise ValidationError(
                f"Интервал должен быть от {MIN_INTERVAL_MINUTES} до "
                f"{MAX_INTERVAL_MINUTES} минут. Получено: {value}"
            )
        return value

    def update(self, raw: str | int | None) -> int:
        """Сохраняет новый интервал."""
        value = self.parse(raw)
        self._state.interval_minutes = value
        self._save(self._state)
        logger.info("Интервал изменён: {} мин", value)
        return value
