"""Хендлеры главного меню: /start и возврат «Назад»."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from core.state import State
from core.ui import MENU_ROOT, main_menu_keyboard, main_menu_text, show_main_menu

router = Router(name="menu")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, app_state: State) -> None:
    await state.clear()
    await message.answer(
        main_menu_text(app_state), reply_markup=main_menu_keyboard(app_state)
    )


@router.callback_query(F.data == MENU_ROOT)
async def back_to_menu(
    callback: CallbackQuery, state: FSMContext, app_state: State
) -> None:
    await state.clear()
    await show_main_menu(callback, app_state)
    await callback.answer()
