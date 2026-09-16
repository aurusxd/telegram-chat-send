"""Ограничение доступа: бот слушает только владельца."""

from __future__ import annotations

from aiogram import Dispatcher
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from loguru import logger


class OwnerOnly(BaseFilter):
    """Пропускает апдейты только от владельца бота."""

    def __init__(self, owner_id: int) -> None:
        self.owner_id = owner_id

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = event.from_user
        if user is not None and user.id == self.owner_id:
            return True
        logger.warning(
            "Отклонён апдейт от постороннего пользователя: id={}",
            getattr(user, "id", None),
        )
        return False


def protect(dispatcher: Dispatcher, owner_id: int) -> None:
    """Вешает проверку владельца на все апдейты сразу."""
    owner_only = OwnerOnly(owner_id)
    dispatcher.message.filter(owner_only)
    dispatcher.callback_query.filter(owner_only)
