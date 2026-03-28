# 🏗️ Архитектура и план реализации

## Принципы архитектуры

- **Хендлер** — только принимает апдейт и вызывает сервис. Никакой логики, никакого SQL.
- **Сервис** — бизнес-логика. Знает что делать, но не знает про Telegram.
- **Репозиторий** — только SQL. Сервис вызывает репозиторий, не Session напрямую.
- **Клавиатуры** — отдельный слой, хендлер не строит InlineKeyboard сам.

```bash
Апдейт → Middleware → Handler → Service → Repository → DB
                         ↓
                      Keyboard
```

---

## Структура проекта (детально)

```bash
bot/
│
├── main.py                  # точка входа: инициализация dp, bot, db, запуск polling
├── config.py                # pydantic-settings, читает .env
├── states.py                # все FSM StatesGroup в одном файле
│
├── db/
│   ├── __init__.py          ← всегда пустой
│   ├── base.py              # engine, async_session factory, Base, init_db
│   ├── models.py            # SQLAlchemy модели
│   └── repository.py        # все методы работы с БД
│
├── services/
│   ├── __init__.py          ← всегда пустой
│   ├── date_service.py      # логика: найти рандомное, лайкнуть, отметить посещённым
│   └── user_service.py      # регистрация юзера, проверка/управление админами
│
├── handlers/
│   ├── __init__.py          ← всегда пустой
│   ├── user/
│   │   ├── __init__.py      ← всегда пустой
│   │   ├── start.py         # /start
│   │   └── dates.py         # поиск свидания, кнопки лайк/сходили/другое
│   └── admin/
│       ├── __init__.py      ← всегда пустой
│       ├── dates.py         # FSM добавления свидания
│       └── admins.py        # добавление/удаление/список админов
│
├── keyboards/
│   ├── __init__.py          ← всегда пустой
│   ├── user.py              # кнопки для пользователя
│   └── admin.py             # кнопки для админа (FSM-шаги, управление)
│
└── middlewares/
    ├── __init__.py          ← всегда пустой
    ├── admin.py             # проверка is_admin перед admin-хендлерами
    └── database.py          # открытие AsyncSession на каждый апдейт
```

---

## config.py

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    FIRST_ADMIN_ID: int | None = None   # если задан и в БД нет ни одного админа — создаётся автоматически
    DB_PATH: str = "bot.db"
    TELEGRAM_PROXY: str | None = None   # например socks5://user:pass@host:port

    class Config:
        env_file = ".env"

settings = Settings()
```

`.env`:

```bash
BOT_TOKEN=your_token_here
```

---

## db/base.py

Используем **асинхронный** SQLAlchemy (aiogram 3.x — asyncio-based).

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine("sqlite+aiosqlite:///bot.db")
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

Сессия пробрасывается через **middleware** в `handler → service → repository`,
чтобы не открывать новую сессию на каждый вызов репозитория.

---

## db/models.py

```python
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class Date(Base):
    __tablename__ = "dates"

    id:          Mapped[int]      = mapped_column(Integer, primary_key=True)
    description: Mapped[str]      = mapped_column(String)
    cash:        Mapped[int]      = mapped_column(Integer)           # 1-3
    time:        Mapped[int]      = mapped_column(Integer)           # часов
    is_home:     Mapped[bool]     = mapped_column(Boolean)
    photo_file_id: Mapped[str]    = mapped_column(String)

class User(Base):
    __tablename__ = "users"

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True)  # tg user_id
    username:      Mapped[str|None] = mapped_column(String, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_admin:      Mapped[bool]     = mapped_column(Boolean, default=False)

class UserHistory(Base):
    __tablename__ = "user_history"
    __table_args__ = (UniqueConstraint("user_id", "date_id"),)

    id:         Mapped[int]           = mapped_column(Integer, primary_key=True)
    user_id:    Mapped[int]           = mapped_column(ForeignKey("users.id"))
    date_id:    Mapped[int]           = mapped_column(ForeignKey("dates.id"))
    is_liked:   Mapped[bool]          = mapped_column(Boolean, default=False)
    dropped_at: Mapped[datetime|None] = mapped_column(DateTime, nullable=True)
```

---

## db/repository.py

Все методы принимают `session: AsyncSession`. Никакой логики — только SQL.

```python
class DateRepository:
    def __init__(self, session: AsyncSession): ...

    async def get_random(self, user_id, cash, time, is_home) -> Date | None:
        # SELECT ... WHERE ... AND id NOT IN (visited) ORDER BY RANDOM() LIMIT 1

    async def get_by_id(self, date_id) -> Date | None: ...
    async def add(self, date: Date) -> Date: ...

class UserRepository:
    def __init__(self, session: AsyncSession): ...

    async def get_or_create(self, user_id, username) -> User: ...
    async def get_by_id(self, user_id) -> User | None: ...
    async def set_admin(self, user_id, value: bool): ...
    async def get_all_admins(self) -> list[User]: ...

class HistoryRepository:
    def __init__(self, session: AsyncSession): ...

    async def get_or_create(self, user_id, date_id) -> UserHistory: ...
    async def toggle_like(self, user_id, date_id): ...
    async def mark_visited(self, user_id, date_id): ...
```

---

## services/

Сервисы не знают про Telegram. Принимают сессию, возвращают данные.

```python
# date_service.py
class DateService:
    def __init__(self, session: AsyncSession):
        self.dates = DateRepository(session)
        self.history = HistoryRepository(session)

    async def find_random(self, user_id, cash, time, is_home) -> Date | None:
        return await self.dates.get_random(user_id, cash, time, is_home)

    async def toggle_like(self, user_id, date_id) -> bool:
        # возвращает новое значение is_liked
        return await self.history.toggle_like(user_id, date_id)

    async def mark_visited(self, user_id, date_id):
        await self.history.mark_visited(user_id, date_id)

    async def add_date(self, description, cash, time, is_home, photo_file_id) -> Date:
        date = Date(...)
        return await self.dates.add(date)

# user_service.py
class UserService:
    def __init__(self, session: AsyncSession):
        self.users = UserRepository(session)

    async def register(self, user_id, username) -> User: ...
    async def add_admin(self, user_id) -> bool: ...      # False если юзер не найден
    async def remove_admin(self, user_id): ...
    async def list_admins(self) -> list[User]: ...
```

---

## middlewares/admin.py

```python
class AdminMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        session = data["session"]                  # сессия из DatabaseMiddleware
        db_user = await UserRepository(session).get_by_id(user.id)

        if not db_user or not db_user.is_admin:
            if hasattr(event, "answer"):
                await event.answer("⛔ Нет доступа")
            return                                 # не передаём управление хендлеру

        return await handler(event, data)
```

Вешается **только** на admin-роутер, не глобально.

---

## Сессия в хендлерах — через middleware

Создаём `DatabaseMiddleware`, который открывает сессию на каждый апдейт и кладёт в `data["session"]`.
    Все хендлеры получают сессию через аргумент:

```python
async def cmd_start(message: Message, session: AsyncSession):
    service = UserService(session)
    await service.register(message.from_user.id, message.from_user.username)
    ...
```

---

## states.py

```python
from aiogram.fsm.state import State, StatesGroup

class AddDateFSM(StatesGroup):
    description = State()
    cash        = State()
    time        = State()
    is_home     = State()
    photo       = State()

class SearchFSM(StatesGroup):
    is_home  = State()
    cash     = State()
    time     = State()
    browsing = State()   # активен пока пользователь листает карточки

class AddAdminFSM(StatesGroup):
    telegram_id = State()

class RemoveAdminFSM(StatesGroup):
    telegram_id = State()
```

---

## keyboards/user.py — пример

```python
def search_location_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🏠 Дома",    callback_data="loc:home"),
        InlineKeyboardButton(text="🌆 Вне дома", callback_data="loc:outside"),
    ]])

def date_card_kb(date_id: int, is_liked: bool) -> InlineKeyboardMarkup:
    like_text = "❤️ Лайк" if not is_liked else "💔 Убрать лайк"
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=like_text,    callback_data=f"like:{date_id}"),
        InlineKeyboardButton(text="✅ Сходили", callback_data=f"visited:{date_id}"),
        InlineKeyboardButton(text="🔄 Другое",  callback_data="next"),
    ]])
```

---

## Callback data — соглашение

Все callback_data строятся по схеме `действие:аргумент`:

| callback_data | Действие |
| --- | --- |
| `loc:home` / `loc:outside` | Выбор локации в поиске |
| `cash:1` / `cash:2` / `cash:3` | Выбор бюджета |
| `time:1` / `time:2` / `time:3` / `time:4` | Выбор времени |
| `like:{date_id}` | Тоггл лайка |
| `visited:{date_id}` | Отметить посещённым |
| `next` | Показать другое свидание |
| `fsm:back` / `fsm:cancel` | Назад/отмена в FSM |

---

## Как хранятся фильтры между шагами поиска

Фильтры накапливаются в **FSM state data** (не в БД):

```python
# шаг 1: пользователь выбрал "дома"
await state.update_data(is_home=True)
await state.set_state(SearchFSM.cash)

# шаг 3: все данные собраны
data = await state.get_data()
date = await DateService(session).find_random(
    user_id=message.from_user.id,
    cash=data["cash"],
    time=data["time"],
    is_home=data["is_home"],
)
await state.clear()
```

---

## Регистрация роутеров

Все роутеры регистрируются явно в `main.py`. Файлы `__init__.py` **всегда пустые**.

```python
# main.py
from bot.handlers.user.start import router as start_router
from bot.handlers.user.dates import router as user_dates_router
from bot.handlers.admin.dates import router as admin_dates_router
from bot.handlers.admin.admins import router as admin_admins_router
from bot.middlewares.admin import AdminMiddleware
from bot.middlewares.database import DatabaseMiddleware
```

---

## main.py

```python
async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    await init_db()

    dp.update.middleware(DatabaseMiddleware())   # сессия в каждый апдейт

    # Регистрируем роутеры напрямую в main.py — __init__.py всегда пустые
    dp.include_router(start_router)
    dp.include_router(user_dates_router)

    admin_router = Router()
    admin_router.message.middleware(AdminMiddleware())
    admin_router.callback_query.middleware(AdminMiddleware())
    admin_router.include_router(admin_dates_router)
    admin_router.include_router(admin_admins_router)
    dp.include_router(admin_router)

    await dp.start_polling(bot)

asyncio.run(main())
```

---
