# 💘 Date Randomizer Bot

Telegram-бот, предлагающий случайные свидания по фильтрам пользователя.

## Стек

- **Python 3.11+**
- **aiogram 3.x** — Telegram-фреймворк
- **SQLAlchemy 2.0 (async)** + **aiosqlite** — база данных SQLite
- **pydantic-settings** — конфигурация через `.env`
- **loguru** — логирование

## Структура проекта

```
date_randomizer_bot/
├── main.py                  # точка входа
├── requirements.txt
├── .env.example
└── bot/
    ├── config.py
    ├── states.py
    ├── db/
    │   ├── base.py
    │   ├── models.py
    │   └── repository.py
    ├── services/
    │   ├── date_service.py
    │   └── user_service.py
    ├── handlers/
    │   ├── user/
    │   │   ├── start.py
    │   │   └── dates.py
    │   └── admin/
    │       ├── dates.py
    │       └── admins.py
    ├── keyboards/
    │   ├── user.py
    │   └── admin.py
    └── middlewares/
        ├── database.py
        └── admin.py
```

## Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone <repo>
cd date_randomizer_bot
```

### 2. Создать виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить `.env`

```bash
cp .env.example .env
```

Отредактируй `.env`:

```env
BOT_TOKEN=your_telegram_bot_token_here
FIRST_ADMIN_ID=123456789   # твой Telegram ID
DB_PATH=bot.db
```

> **Как узнать свой Telegram ID:** напиши боту [@userinfobot](https://t.me/userinfobot)

### 5. Запустить бота

```bash
python main.py
```

При первом запуске автоматически создадутся таблицы в `bot.db`.
Если указан `FIRST_ADMIN_ID` — этот пользователь сразу получит права администратора.

---

## Возможности

### Для пользователей

- `/start` — приветствие и главное меню
- Поиск свидания по фильтрам: место / бюджет / время
- ❤️ Лайк (тоггл), ✅ Сходили, 🔄 Другое — на карточке свидания

### Для администраторов

| Команда | Описание |
|---|---|
| `/add_date` | Добавить новое свидание (5-шаговый FSM с фото) |
| `/add_admin` | Назначить пользователя администратором |
| `/remove_admin` | Снять права администратора |
| `/list_admins` | Список всех администраторов |

> Пользователь должен написать `/start` боту, прежде чем его можно назначить администратором.

---

## Архитектура

```
Апдейт → Middleware → Handler → Service → Repository → DB
                         ↓
                      Keyboard
```

- **Handler** — принимает апдейт, вызывает сервис, отправляет ответ. Никакого SQL.
- **Service** — бизнес-логика. Не знает про Telegram.
- **Repository** — только SQL через AsyncSession.
- **Keyboard** — фабричные функции, возвращающие InlineKeyboardMarkup.
