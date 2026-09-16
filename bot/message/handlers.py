"""Хендлеры просмотра и изменения текста рассылки."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State as FSMState
from aiogram.fsm.state import StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from core.errors import ValidationError
from core.ui import MESSAGE_MENU, back_button, back_keyboard, edit
from message.service import MAX_MESSAGE_LENGTH, MessageService

router = Router(name="message")

EDIT = "message:edit"


class MessageForm(StatesGroup):
    """Ожидание нового текста рассылки."""

    waiting_for_text = FSMState()


def _menu_text(service: MessageService) -> str:
    if service.is_empty:
        return "✏️ Сообщение\n\nТекст не задан."
    return f"✏️ Сообщение ({len(service.text)} символов)\n\n{service.text}"


def _menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить", callback_data=EDIT)],
            [back_button()],
        ]
    )


@router.callback_query(F.data == MESSAGE_MENU)
async def open_menu(
    callback: CallbackQuery, state: FSMContext, message_service: MessageService
) -> None:
    await state.clear()
    await edit(callback, _menu_text(message_service), _menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == EDIT)
async def ask_text(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(MessageForm.waiting_for_text)
    await edit(
        callback,
        f"✏️ Пришлите новый текст рассылки (до {MAX_MESSAGE_LENGTH} символов).",
        back_keyboard(MESSAGE_MENU),
    )
    await callback.answer()


@router.message(MessageForm.waiting_for_text)
async def save_text(
    message: Message, state: FSMContext, message_service: MessageService
) -> None:
    try:
        text = message_service.update(message.text)
    except ValidationError as exc:
        await message.answer(
            f"⚠️ {exc}\n\nПопробуйте ещё раз.", reply_markup=back_keyboard(MESSAGE_MENU)
        )
        return
    await state.clear()
    await message.answer(
        f"✅ Текст обновлён и уйдёт со следующей отправки.\n\n{text}",
        reply_markup=_menu_keyboard(),
    )
