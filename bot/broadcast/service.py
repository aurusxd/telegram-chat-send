"""Проверка готовности рассылки к запуску."""

from __future__ import annotations

from core.state import State


def readiness_problems(app_state: State) -> list[str]:
    """Возвращает список причин, по которым рассылку нельзя запустить."""
    problems: list[str] = []
    if not app_state.channels:
        problems.append("не добавлено ни одного канала")
    if not app_state.message_text.strip():
        problems.append("не задан текст сообщения")
    return problems


def is_ready(app_state: State) -> bool:
    return not readiness_problems(app_state)


def format_problems(problems: list[str]) -> str:
    """Человекочитаемое перечисление того, чего не хватает."""
    listing = "\n".join(f"• {problem}" for problem in problems)
    return f"⚠️ Нельзя запустить рассылку:\n{listing}"
