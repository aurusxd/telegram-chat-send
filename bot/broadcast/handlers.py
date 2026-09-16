"""Кнопки «Старт» и «Стоп»."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from loguru import logger

from broadcast.scheduler import Scheduler
from broadcast.service import format_problems, readiness_problems
from core.state import State
from core.ui import BROADCAST_START, BROADCAST_STOP, edit, main_menu_keyboard, main_menu_text, show_main_menu

router = Router(name="broadcast")


@router.callback_query(F.data == BROADCAST_START)
async def start_broadcast(
    callback: CallbackQuery, app_state: State, scheduler: Scheduler
) -> None:
    problems = readiness_problems(app_state)
    if problems:
        logger.warning("Старт отклонён: {}", "; ".join(problems))
        await callback.answer(format_problems(problems), show_alert=True)
        await edit(
            callback,
            f"{main_menu_text(app_state)}\n\n{format_problems(problems)}",
            main_menu_keyboard(app_state),
        )
        return

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
