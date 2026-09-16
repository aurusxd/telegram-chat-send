"""Диагностика сессии и авторизации Hydrogram.

Показывает, жива ли сессия, а если нет — каким способом Telegram отправляет код,
не завершая вход.

Запуск:  python scripts/check_auth.py
         docker compose run --rm bot python scripts/check_auth.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bot"))

from hydrogram.enums import SentCodeType  # noqa: E402
from hydrogram.errors import (  # noqa: E402
    ApiIdInvalid,
    FloodWait,
    PhoneNumberBanned,
    PhoneNumberInvalid,
    RPCError,
)

from core.config import ConfigError, ensure_dirs, load_config, session_file  # noqa: E402
from core.telegram import build_client, describe_connection  # noqa: E402

#: Пояснение по каждому способу доставки кода.
DELIVERY_HINTS = {
    SentCodeType.APP: (
        "код отправлен В ПРИЛОЖЕНИЕ Telegram — ищите сообщение в чате «Telegram» "
        "(служебный аккаунт с галочкой), в том числе в папке «Архив»"
    ),
    SentCodeType.SMS: "код отправлен по SMS на указанный номер",
    SentCodeType.CALL: "Telegram позвонит и продиктует код голосом",
    SentCodeType.MISSED_CALL: (
        "будет сброшенный звонок — код это последние цифры номера, с которого звонили"
    ),
    SentCodeType.FLASH_CALL: "будет сброшенный звонок, код берётся из номера звонящего",
    SentCodeType.EMAIL_CODE: (
        "код отправлен НА ПОЧТУ, привязанную как login email — проверяйте email"
    ),
    SentCodeType.FRAGMENT_SMS: "код доставлен через Fragment (анонимный номер)",
}


def describe(code_type: SentCodeType | None) -> str:
    if code_type is None:
        return "—"
    hint = DELIVERY_HINTS.get(code_type, "способ доставки неизвестен этому скрипту")
    return f"{code_type.name}\n  → {hint}"


async def main() -> int:
    ensure_dirs()
    config = load_config()
    path = session_file(config.session_name)
    print(f"Файл сессии: {path} ({'есть' if path.exists() else 'нет'})")
    print(f"Подключение: {describe_connection(config)}")

    client = build_client(config)
    try:
        authorized = await client.connect()
    except OSError as exc:
        print(f"❌ Не удалось подключиться к Telegram: {exc}")
        print("   Похоже на блокировку соединения — попробуйте прокси или VPN.")
        return 1

    try:
        if authorized:
            me = await client.get_me()
            print(f"✅ Сессия рабочая: {me.first_name} (id={me.id}) — код не нужен")
            return 0

        phone = input("Номер в международном формате (например, +79991234567): ").strip()
        try:
            sent = await client.send_code(phone)
        except PhoneNumberInvalid:
            print("❌ Telegram считает номер некорректным. Нужен формат +<код страны><номер>.")
            return 1
        except PhoneNumberBanned:
            print("❌ Номер заблокирован в Telegram.")
            return 1
        except ApiIdInvalid:
            print("❌ Неверные API_ID / API_HASH — получите их на https://my.telegram.org")
            return 1
        except FloodWait as exc:
            print(f"❌ Флуд-контроль: повторный запрос кода возможен через {exc.value} с.")
            return 1
        except RPCError as exc:
            print(f"❌ Telegram вернул ошибку: {exc.__class__.__name__}: {exc}")
            return 1

        print(f"\nЗапрос кода принят.\nСпособ доставки: {describe(sent.type)}")
        if sent.next_type is not None:
            print(f"Резервный способ: {describe(sent.next_type)}")
        return 0
    finally:
        if client.is_connected:
            await client.disconnect()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}")
        raise SystemExit(1) from exc
