"""Диагностика авторизации Telethon.

Запрашивает код и показывает, каким способом Telegram его отправил,
не завершая вход. Помогает понять, почему код «не приходит».

Запуск из корня проекта:  python scripts/check_auth.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bot"))

from telethon.errors import (  # noqa: E402
    ApiIdInvalidError,
    FloodWaitError,
    PhoneNumberBannedError,
    PhoneNumberInvalidError,
    RPCError,
)

from core.config import ConfigError, ensure_dirs, load_config  # noqa: E402
from core.telegram import build_client, describe_connection  # noqa: E402

#: Пояснение по каждому способу доставки кода.
DELIVERY_HINTS = {
    "SentCodeTypeApp": (
        "код отправлен В ПРИЛОЖЕНИЕ Telegram — ищите сообщение в чате «Telegram» "
        "(служебный аккаунт с галочкой), в том числе в папке «Архив»"
    ),
    "SentCodeTypeSms": "код отправлен по SMS на указанный номер",
    "SentCodeTypeSmsWord": "код придёт по SMS одним словом",
    "SentCodeTypeSmsPhrase": "код придёт по SMS фразой из нескольких слов",
    "SentCodeTypeCall": "Telegram позвонит и продиктует код голосом",
    "SentCodeTypeMissedCall": (
        "будет сброшенный звонок — код это последние цифры номера, с которого звонили"
    ),
    "SentCodeTypeFlashCall": "будет сброшенный звонок, код берётся из номера звонящего",
    "SentCodeTypeEmailCode": (
        "код отправлен НА ПОЧТУ, привязанную как login email — проверяйте email, "
        "а не Telegram"
    ),
    "SentCodeTypeSetUpEmailRequired": (
        "Telegram требует сначала привязать login email через официальное приложение"
    ),
    "SentCodeTypeFragmentSms": "код доставлен через Fragment (анонимный номер)",
    "SentCodeTypeFirebaseSms": "код доставлен через Firebase SMS",
}


def describe(sent_code_type: object) -> str:
    name = type(sent_code_type).__name__
    hint = DELIVERY_HINTS.get(name, "способ доставки неизвестен этому скрипту")
    details = []
    for attribute in ("length", "email_pattern", "url"):
        value = getattr(sent_code_type, attribute, None)
        if value:
            details.append(f"{attribute}={value}")
    suffix = f" ({', '.join(details)})" if details else ""
    return f"{name}{suffix}\n  → {hint}"


async def main() -> int:
    ensure_dirs()
    config = load_config()
    phone = input("Номер в международном формате (например, +79991234567): ").strip()

    client = build_client(config)
    print(f"Способ подключения: {describe_connection(config)}")
    try:
        await client.connect()
    except OSError as exc:
        print(f"❌ Не удалось подключиться к Telegram: {exc}")
        print("   Похоже на блокировку соединения — попробуйте прокси или VPN.")
        return 1
    print(f"Подключение к Telegram: DC {client.session.dc_id}")

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Сессия уже авторизована: {me.first_name} (id={me.id}) — код не нужен")
        await client.disconnect()
        return 0

    try:
        sent = await client.send_code_request(phone)
    except PhoneNumberInvalidError:
        print("❌ Telegram считает номер некорректным. Нужен формат +<код страны><номер>.")
        return 1
    except PhoneNumberBannedError:
        print("❌ Номер заблокирован в Telegram.")
        return 1
    except ApiIdInvalidError:
        print("❌ Неверные API_ID / API_HASH — получите их на https://my.telegram.org")
        return 1
    except FloodWaitError as exc:
        print(f"❌ Флуд-контроль: повторный запрос кода возможен через {exc.seconds} с.")
        return 1
    except RPCError as exc:
        print(f"❌ Telegram вернул ошибку: {exc.__class__.__name__}: {exc}")
        return 1
    finally:
        if client.is_connected():
            await client.disconnect()

    print("\nЗапрос кода принят Telegram.")
    print(f"Способ доставки: {describe(sent.type)}")
    if sent.next_type is not None:
        print(f"Резервный способ: {describe(sent.next_type)}")
    if sent.timeout:
        print(f"Повторный запрос можно сделать через {sent.timeout} с.")
    print("\nЕсли код так и не пришёл — см. раздел «Код не приходит» в README.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}")
        raise SystemExit(1) from exc
