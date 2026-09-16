"""Общие исключения приложения."""

from __future__ import annotations


class ValidationError(ValueError):
    """Пользовательский ввод не прошёл проверку.

    Текст исключения показывается владельцу в чате, поэтому пишется
    человеческим языком.
    """


class TelegramConnectionError(RuntimeError):
    """Не удалось подключиться к серверам Telegram."""
