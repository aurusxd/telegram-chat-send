"""Состояние рассылки, общее для всех слайсов."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class State:
    """Настройки рассылки и её текущий статус.

    `is_running` живёт только в памяти: после перезапуска процесса
    рассылка всегда считается остановленной.
    """

    channels: list[str] = field(default_factory=list)
    message_text: str = ""
    interval_minutes: int = 15
    is_running: bool = False
