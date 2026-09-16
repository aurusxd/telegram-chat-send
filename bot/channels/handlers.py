"""Хендлеры управления списком каналов."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State as FSMState
from aiogram.fsm.state import StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from channels.service import ChannelService
from core.errors import ValidationError
from core.ui import CHANNELS_MENU, back_button, back_keyboard, edit

router = Router(name="channels")

ADD = "channels:add"
REMOVE_MENU = "channels:remove"
REMOVE_PREFIX = "channels:remove:"


class ChannelForm(StatesGroup):
    """Ожидание ввода username/ID канала."""

    waiting_for_channel = FSMState()


def _menu_text(service: ChannelService) -> str:
    channels = service.channels
    if not channels:
        return "📋 Каналы\n\nСписок пуст — добавьте хотя бы один канал."
    listing = "\n".join(f"{number}. {channel}" for number, channel in enumerate(channels, 1))
    return f"📋 Каналы ({len(channels)})\n\n{listing}"


def _menu_keyboard(service: ChannelService) -> InlineKeyboardMarkup:
    actions = [InlineKeyboardButton(text="➕ Добавить", callback_data=ADD)]
    if service.channels:
        actions.append(InlineKeyboardButton(text="🗑 Удалить", callback_data=REMOVE_MENU))
    return InlineKeyboardMarkup(inline_keyboard=[actions, [back_button()]])


def _remove_keyboard(service: ChannelService) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"🗑 {channel}", callback_data=f"{REMOVE_PREFIX}{channel}")]
        for channel in service.channels
    ]
    rows.append([back_button(CHANNELS_MENU)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _show_menu(callback: CallbackQuery, service: ChannelService) -> None:
    await edit(callback, _menu_text(service), _menu_keyboard(service))


@router.callback_query(F.data == CHANNELS_MENU)
async def open_menu(
    callback: CallbackQuery, state: FSMContext, channel_service: ChannelService
) -> None:
    await state.clear()
    await _show_menu(callback, channel_service)
    await callback.answer()


@router.callback_query(F.data == ADD)
async def ask_channel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ChannelForm.waiting_for_channel)
    await edit(
        callback,
        "➕ Пришлите @username канала, ссылку t.me/... или числовой ID.",
        back_keyboard(CHANNELS_MENU),
    )
    await callback.answer()


@router.message(ChannelForm.waiting_for_channel)
async def add_channel(
    message: Message, state: FSMContext, channel_service: ChannelService
) -> None:
    try:
        channel = channel_service.add(message.text or "")
    except ValidationError as exc:
        await message.answer(f"⚠️ {exc}\n\nПопробуйте ещё раз.", reply_markup=back_keyboard(CHANNELS_MENU))
        return
    await state.clear()
    await message.answer(
        f"✅ Канал {channel} добавлен.\n\n{_menu_text(channel_service)}",
        reply_markup=_menu_keyboard(channel_service),
    )


@router.callback_query(F.data == REMOVE_MENU)
async def ask_removal(callback: CallbackQuery, channel_service: ChannelService) -> None:
    if not channel_service.channels:
        await callback.answer("Список уже пуст")
        await _show_menu(callback, channel_service)
        return
    await edit(callback, "🗑 Выберите канал для удаления:", _remove_keyboard(channel_service))
    await callback.answer()


@router.callback_query(F.data.startswith(REMOVE_PREFIX))
async def remove_channel(callback: CallbackQuery, channel_service: ChannelService) -> None:
    raw = (callback.data or "")[len(REMOVE_PREFIX) :]
    try:
        channel = channel_service.remove(raw)
    except ValidationError as exc:
        await callback.answer(str(exc), show_alert=True)
    else:
        await callback.answer(f"Канал {channel} удалён")
    await _show_menu(callback, channel_service)
