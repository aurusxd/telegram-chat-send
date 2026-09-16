"""Кнопки «Старт» и «Стоп»."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from broadcast.scheduler import Scheduler
from core.state import State
from core.ui import BROADCAST_START, BROADCAST_STOP, show_main_menu

router = Router(name="broadcast")


@router.callback_query(F.data == BROADCAST_START)
async def start_broadcast(
    callback: CallbackQuery, app_state: State, scheduler: Scheduler
) -> None:
    started = scheduler.start()
    await callback.answer("Рассылка запущена" if started else "Рассылка уже идёт")
    await show_main_menu(callback, app_state)


@router.callback_query(F.data == BROADCAST_STOP)
async def stop_broadcast(
    callback: CallbackQuery, app_state: State, scheduler: Scheduler
) -> None:
    stopped = scheduler.stop()
    await callback.answer("Рассылка остановлена" if stopped else "Рассылка не запущена")
    await show_main_menu(callback, app_state)
