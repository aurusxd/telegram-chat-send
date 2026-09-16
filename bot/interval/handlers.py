"""Хендлеры просмотра и изменения интервала рассылки."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State as FSMState
from aiogram.fsm.state import StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from core.errors import ValidationError
from core.ui import INTERVAL_MENU, back_button, back_keyboard, edit
from interval.service import (
    MAX_INTERVAL_MINUTES,
    MIN_INTERVAL_MINUTES,
    PRESETS,
    IntervalService,
)

router = Router(name="interval")

CUSTOM = "interval:custom"
SET_PREFIX = "interval:set:"


class IntervalForm(StatesGroup):
    """Ожидание своего значения интервала."""

    waiting_for_minutes = FSMState()


def _menu_text(service: IntervalService) -> str:
    return (
        f"⏱ Интервал\n\nСейчас: {service.minutes} мин\n"
        "Выберите пресет или задайте своё значение."
    )


def _menu_keyboard(service: IntervalService) -> InlineKeyboardMarkup:
    presets = [
        InlineKeyboardButton(
            text=("✅ " if preset == service.minutes else "") + f"{preset} мин",
            callback_data=f"{SET_PREFIX}{preset}",
        )
        for preset in PRESETS
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            presets[:2],
            presets[2:],
            [InlineKeyboardButton(text="✏️ Своё значение", callback_data=CUSTOM)],
            [back_button()],
        ]
    )


async def _show_menu(callback: CallbackQuery, service: IntervalService) -> None:
    await edit(callback, _menu_text(service), _menu_keyboard(service))


@router.callback_query(F.data == INTERVAL_MENU)
async def open_menu(
    callback: CallbackQuery, state: FSMContext, interval_service: IntervalService
) -> None:
    await state.clear()
    await _show_menu(callback, interval_service)
    await callback.answer()


@router.callback_query(F.data.startswith(SET_PREFIX))
async def set_preset(callback: CallbackQuery, interval_service: IntervalService) -> None:
    raw = (callback.data or "")[len(SET_PREFIX) :]
    try:
        minutes = interval_service.update(raw)
    except ValidationError as exc:
        await callback.answer(str(exc), show_alert=True)
    else:
        await callback.answer(f"Интервал: {minutes} мин")
    await _show_menu(callback, interval_service)


@router.callback_query(F.data == CUSTOM)
async def ask_minutes(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(IntervalForm.waiting_for_minutes)
    await edit(
        callback,
        f"⏱ Пришлите интервал в минутах ({MIN_INTERVAL_MINUTES}-{MAX_INTERVAL_MINUTES}).",
        back_keyboard(INTERVAL_MENU),
    )
    await callback.answer()


@router.message(IntervalForm.waiting_for_minutes)
async def save_minutes(
    message: Message, state: FSMContext, interval_service: IntervalService
) -> None:
    try:
        minutes = interval_service.update(message.text)
    except ValidationError as exc:
        await message.answer(
            f"⚠️ {exc}\n\nПопробуйте ещё раз.", reply_markup=back_keyboard(INTERVAL_MENU)
        )
        return
    await state.clear()
    await message.answer(
        f"✅ Интервал изменён на {minutes} мин и применится со следующего цикла.",
        reply_markup=_menu_keyboard(interval_service),
    )
