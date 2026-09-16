"""Состояние рассылки и его хранение в JSON."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from core.config import DEFAULT_INTERVAL_MINUTES, STATE_PATH


@dataclass
class State:
    """Настройки рассылки и её текущий статус.

    `is_running` живёт только в памяти и на диск не сохраняется: после
    перезапуска процесса рассылка всегда считается остановленной.
    """

    channels: list[str] = field(default_factory=list)
    message_text: str = ""
    interval_minutes: int = DEFAULT_INTERVAL_MINUTES
    is_running: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "channels": list(self.channels),
            "message_text": self.message_text,
            "interval_minutes": self.interval_minutes,
        }

    @classmethod
    def from_dict(cls, raw: object, default: "State | None" = None) -> "State":
        """Собирает State из данных файла, игнорируя мусорные значения."""
        base = default or cls()
        if not isinstance(raw, dict):
            return cls(**base.to_dict())

        channels = raw.get("channels")
        if isinstance(channels, list):
            channels = [item.strip() for item in channels if isinstance(item, str) and item.strip()]
        else:
            channels = list(base.channels)

        message_text = raw.get("message_text")
        if not isinstance(message_text, str):
            message_text = base.message_text

        interval = raw.get("interval_minutes")
        if not isinstance(interval, int) or isinstance(interval, bool) or interval < 1:
            interval = base.interval_minutes

        return cls(channels=channels, message_text=message_text, interval_minutes=interval)


def load_state(path: Path = STATE_PATH, default: State | None = None) -> State:
    """Читает состояние с диска; при отсутствии или поломке файла — значения по умолчанию."""
    fallback = default or State()
    if not path.exists():
        logger.info("Файл состояния не найден, используются значения по умолчанию: {}", path)
        return State(**fallback.to_dict())
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Не удалось прочитать {}: {}. Беру значения по умолчанию", path, exc)
        return State(**fallback.to_dict())
    state = State.from_dict(raw, fallback)
    logger.info(
        "Состояние загружено: каналов {}, интервал {} мин", len(state.channels), state.interval_minutes
    )
    return state


def save_state(state: State, path: Path = STATE_PATH) -> None:
    """Атомарно сохраняет персистентную часть состояния."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp_path.write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(tmp_path, path)
    except OSError as exc:
        logger.error("Не удалось сохранить состояние в {}: {}", path, exc)
        tmp_path.unlink(missing_ok=True)
