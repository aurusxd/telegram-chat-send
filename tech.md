# ТЗ: Telegram-бот для автопостинга в каналы

## Общая идея

Локальный бот на Telethon, который с заданным интервалом отправляет одно и то же сообщение сразу во все выбранные Telegram-каналы. Управление происходит через отдельного Telegram-бота с кнопками.

## Технический стек

- Python
- Telethon для отправки сообщений через юзер-аккаунт (авторизация по номеру телефона)
- aiogram или python-telegram-bot для управляющего интерфейса
- Хранение состояния: JSON-файл (каналы, текст сообщения, интервал)
- loguru для логирования
- Docker / docker-compose для развёртывания на сервере

## Требования к коду

- **ООП**: каждая сущность (State, Scheduler, ChannelSender) — отдельный класс с чёткой ответственностью, без god-объектов
- **DRY**: общая логика (загрузка/сохранение state, отправка сообщений, обработка ошибок Telethon) выносится в переиспользуемые методы/сервисы, не дублируется между слайсами
- **Безопасность**:
  - `API_ID`, `API_HASH`, `BOT_TOKEN` только через `.env`, нигде не хардкодятся и не коммитятся (`.env` в `.gitignore`)
  - `session.session` и `state.json` не попадают в git (в `.gitignore`)
  - Управляющий бот реагирует только на своего владельца (проверка `user_id` в хендлерах), чтобы никто чужой не мог управлять рассылкой
  - Ввод пользователя (текст сообщения, username канала, интервал) валидируется перед сохранением в state

## Стадии разработки (слайсами)

Каждый слайс — законченный рабочий инкремент, после которого систему можно запустить и проверить.

### Слайс 1: Минимальный отправитель

Цель: Telethon-скрипт отправляет захардкоженное сообщение в один захардкоженный канал раз в N минут. Без управляющего бота.

Входит:
- `broadcast/sender.py`, `broadcast/scheduler.py`
- `main.py` без бота-управления, значения берутся из `.env`

DoD:
- [ ] Скрипт стабильно отправляет сообщение раз в N минут в тестовый канал
- [ ] Интервал задаётся через `.env`
- [ ] Ошибка отправки не роняет процесс (try/except в цикле)
- [ ] Telethon-сессия сохраняется и переиспользуется между запусками

### Слайс 2: Управляющий бот + Старт/Стоп

Цель: рассылкой управляют через Telegram-бота, а не через ручной запуск скрипта.

Входит:
- `broadcast/handlers.py` (кнопки "Старт" / "Стоп")
- `main.py` собирает управляющего бота (aiogram/PTB)

DoD:
- [ ] По кнопке "Старт" запускается цикл рассылки, по "Стоп" останавливается
- [ ] После перезапуска процесса бот в состоянии "остановлен"
- [ ] Повторное нажатие "Старт" не создаёт дублирующую задачу

### Слайс 3: Управление каналами

Цель: список каналов редактируется через бота, а не хардкодится в `.env`.

Входит:
- `channels/handlers.py`, `channels/service.py`
- `core/state.py`: поле `channels`, персист в `state.json`

DoD:
- [ ] Можно добавить канал через бота
- [ ] Можно удалить канал через бота
- [ ] Список каналов сохраняется между перезапусками
- [ ] При старте рассылка уходит во все каналы из списка

### Слайс 4: Управление сообщением

Цель: текст рассылки редактируется через бота.

Входит:
- `message/handlers.py`, `message/service.py`

DoD:
- [ ] Можно посмотреть текущий текст
- [ ] Можно изменить текст через бота
- [ ] Новый текст сохраняется в `state.json` и используется со следующей отправки

### Слайс 5: Управление интервалом

Цель: интервал редактируется через бота.

Входит:
- `interval/handlers.py`, `interval/service.py`

DoD:
- [ ] Можно посмотреть текущий интервал
- [ ] Можно изменить интервал через бота
- [ ] Новый интервал применяется со следующего цикла без перезапуска бота

### Слайс 6: Валидация перед стартом

Цель: защититься от запуска с пустой конфигурацией.

DoD:
- [ ] Нельзя нажать "Старт", если список каналов пуст
- [ ] Нельзя нажать "Старт", если текст сообщения пуст
- [ ] Бот явно сообщает, чего не хватает

### Слайс 7: Логирование (loguru)

Цель: все действия и ошибки логируются в файл.

Входит:
- `core/logger.py`

DoD:
- [ ] Логи пишутся в `logs/bot.log` с ротацией и хранением 14 дней
- [ ] Логируются: старт/стоп, каждая успешная отправка, ошибки отправки, изменения конфигурации

### Слайс 8: Docker / docker-compose

Цель: бот разворачивается на сервере одной командой.

Входит:
- `Dockerfile`, `docker-compose.yml`, `.env.example`

DoD:
- [ ] `docker-compose up -d` поднимает бота
- [ ] `state.json`, `session.session` и `logs/` сохраняются между пересборками (volumes)
- [ ] Секреты (`API_ID`, `API_HASH`, `BOT_TOKEN`) берутся из `.env`, не захардкожены
- [ ] После `docker-compose restart` бот в состоянии "остановлен", требует ручного "Старт"

## Архитектура (vertical slices)

Каждая фича — отдельный слайс со своими хендлерами и логикой, без общего слоя "handlers.py на всё".

```
bot/
  main.py               # точка входа, сборка всех слайсов и клиентов
  core/
    state.py             # dataclass State, load_state() / save_state()
    logger.py            # настройка loguru
  channels/
    handlers.py           # команды: добавить/удалить/показать каналы
    service.py             # логика работы со списком каналов
  message/
    handlers.py           # команды: показать/изменить текст сообщения
    service.py
  interval/
    handlers.py           # команды: показать/изменить интервал
    service.py
  broadcast/
    handlers.py           # кнопки старт/стоп
    scheduler.py           # класс Scheduler: start(), stop(), цикл рассылки
    sender.py              # класс ChannelSender: отправка через Telethon
data/
  state.json             # сохраняемое состояние
  session.session         # Telethon-сессия
logs/
  bot.log
Dockerfile
docker-compose.yml
requirements.txt
.env
```

Каждый слайс (`channels`, `message`, `interval`, `broadcast`) самодостаточен: свои хендлеры и своя логика внутри одной папки. Общий `State` и `logger` лежат в `core/`, так как используются всеми слайсами.

## Модель данных

```python
@dataclass
class State:
    channels: list[str]        # username/ID каналов
    message_text: str
    interval_minutes: int
    is_running: bool = False    # только in-memory, не сохраняется на диск
```

На диске хранятся: `channels`, `message_text`, `interval_minutes`.

## Интерфейс бота

Главное меню:
```
📋 Каналы
✏️ Сообщение
⏱ Интервал
▶️ Старт / ⏹ Стоп
```

**Каналы**
- Добавить → бот просит прислать username/ID, добавляет в список
- Удалить → список с кнопками удаления
- Показать список

**Сообщение**
- Показать текущий текст
- Изменить → ввод нового текста, замена `message_text`

**Интервал**
- Показать текущий интервал
- Изменить → ввод числа в минутах или пресеты (15 / 30 / 60 / 120)

**Старт/Стоп**
- "Старт": если каналы и текст заданы, запускает `asyncio.Task` с циклом рассылки, кнопка меняется на "Стоп"
- "Стоп": отменяет задачу (`task.cancel()`), кнопка возвращается в "Старт"

## Цикл рассылки

```python
class Scheduler:
    def __init__(self, sender: ChannelSender, state: State):
        self.sender = sender
        self.state = state
        self.task: asyncio.Task | None = None

    def start(self):
        if self.task is None:
            self.task = asyncio.create_task(self._loop())
            self.state.is_running = True

    def stop(self):
        if self.task:
            self.task.cancel()
            self.task = None
            self.state.is_running = False

    async def _loop(self):
        while True:
            await self.sender.send_to_all(self.state.channels, self.state.message_text)
            await asyncio.sleep(self.state.interval_minutes * 60)
```

## Логирование (loguru)

`core/logger.py`:

```python
from loguru import logger

logger.add(
    "logs/bot.log",
    rotation="10 MB",
    retention="14 days",
    level="INFO",
    encoding="utf-8",
)
```

## Docker / docker-compose

`Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot/main.py"]
```

`docker-compose.yml`:

```yaml
version: "3.9"

services:
  bot:
    build: .
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

`.env` (пример):

```
API_ID=...
API_HASH=...
BOT_TOKEN=...
```

Замечания:
- `data/` и `logs/` монтируются как volume, чтобы состояние и логи не терялись при пересборке контейнера
- `restart: unless-stopped` держит бота живым, но при рестарте контейнера `is_running` всё равно сбрасывается в `False` — это осознанное поведение по ТЗ
- Telethon-сессия (`session.session`) тоже должна лежать в примонтированном `data/`, иначе при пересборке контейнера придётся заново авторизовываться
