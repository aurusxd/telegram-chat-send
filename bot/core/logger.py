"""Настройка loguru: консоль + файл с ротацией."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from core.config import DEFAULT_LOG_LEVEL, LOG_PATH

CONSOLE_FORMAT = "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}"
FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"


def setup_logging(level: str = DEFAULT_LOG_LEVEL, log_path: Path = LOG_PATH) -> None:
    """Включает вывод в консоль и в файл с ротацией и хранением 14 дней."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=level, format=CONSOLE_FORMAT)
    logger.add(
        log_path,
        level=level,
        format=FILE_FORMAT,
        rotation="10 MB",
        retention="14 days",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )
    logger.info("Логирование настроено: {} (уровень {})", log_path, level)
