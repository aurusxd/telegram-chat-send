"""Общие элементы интерфейса: главное меню и помощники для клавиатур."""

from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from core.state import State

MENU_ROOT = "menu:root"
CHANNELS_MENU = "channels:menu"
MESSAGE_MENU = "message:menu"
INTERVAL_MENU = "interval:menu"
BROADCAST_START = "broadcast:start"
BROADCAST_STOP = "broadcast:stop"

#: Сколько символов текста рассылки показывать в главном меню.
PREVIEW_LIMIT = 60


def back_button(callback_data: str = MENU_ROOT, text: str = "◀️ Назад") -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def back_keyboard(callback_data: str = MENU_ROOT) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[back_button(callback_data)]])


def preview(text: str, limit: int = PREVIEW_LIMIT) -> str:
    """Короткая однострочная выжимка текста рассылки."""
    if not text:
        return "не задан"
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def main_menu_keyboard(app_state: State) -> InlineKeyboardMarkup:
    run_button = (
        InlineKeyboardButton(text="⏹ Стоп", callback_data=BROADCAST_STOP)
        if app_state.is_running
        else InlineKeyboardButton(text="▶️ Старт", callback_data=BROADCAST_START)
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Каналы", callback_data=CHANNELS_MENU),
                InlineKeyboardButton(text="✏️ Сообщение", callback_data=MESSAGE_MENU),
            ],
            [InlineKeyboardButton(text="⏱ Интервал", callback_data=INTERVAL_MENU)],
            [run_button],
        ]
    )


def main_menu_text(app_state: State) -> str:
    status = "▶️ запущена" if app_state.is_running else "⏹ остановлена"
    return (
        "🤖 Автопостинг\n\n"
        f"Статус: {status}\n"
        f"Каналов: {len(app_state.channels)}\n"
        f"Интервал: {app_state.interval_minutes} мин\n"
        f"Текст: {preview(app_state.message_text)}"
    )


async def show_main_menu(callback: CallbackQuery, app_state: State) -> None:
    """Перерисовывает главное меню в том же сообщении."""
    await edit(callback, main_menu_text(app_state), main_menu_keyboard(app_state))


async def edit(callback: CallbackQuery, text: str, keyboard: InlineKeyboardMarkup) -> None:
    """Редактирует сообщение, молча проглатывая «message is not modified»."""
    message = callback.message
    if message is None:
        return
    try:
        await message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise
