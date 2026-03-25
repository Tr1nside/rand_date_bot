# AI.md — Правила работы с проектом Date Randomizer Bot

## Контекст проекта

Telegram-бот на **aiogram 3.x + asyncio**, который предлагает случайные свидания по фильтрам пользователя.
Полная архитектура описана в `DESIGN.md` и `Architecture.md` — читай их перед началом работы.

---

## Стек

| Слой | Инструмент |
| --- | --- |
| Telegram | `aiogram >= 3.0` |
| БД | `SQLite` + `SQLAlchemy >= 2.0` (async) |
| Драйвер SQLite | `aiosqlite` |
| Конфиг | `pydantic-settings` |
| Логирование | `loguru` |
| Линтер | `ruff` + `WPS` |
| Форматирование | `pre-commit` + `markdownlint` |

---

## Архитектурные правила

Слои строго изолированы. Данные идут только в одну сторону:

```
Апдейт → Middleware → Handler → Service → Repository → DB
                         ↓
                      Keyboard
```

### Handler

- Принимает апдейт, извлекает данные, вызывает сервис, отправляет ответ.
- **Никакой бизнес-логики.** Никакого SQL. Никаких прямых обращений к `session`.
- Получает `session: AsyncSession` через аргумент (пробрасывается `DatabaseMiddleware`).

### Service

- Содержит бизнес-логику.
- Не знает про Telegram (нет импортов `aiogram`).
- Принимает `session: AsyncSession` в `__init__`, создаёт нужные репозитории.

### Repository

- Только SQL-запросы через `AsyncSession`.
- Никакой логики — только чтение/запись в БД.
- Принимает `session: AsyncSession` в `__init__`.

### Keyboard

- Отдельный слой. Хендлер **не строит** `InlineKeyboardMarkup` сам.
- Функция-фабрика принимает параметры, возвращает готовую клавиатуру.

---

## Правила кода

### Общие

- Язык — **Python 3.11+**.
- Весь код — **асинхронный** (`async/await`), синхронных вызовов к БД нет.
- Типы аннотируются везде: аргументы функций, возвращаемые значения, поля классов.
- Используй `X | None` вместо `Optional[X]`.
- Используй `X | Y` вместо `Union[X, Y]`.

### Именование

- Файлы и модули — `snake_case`.
- Классы — `PascalCase`.
- Функции, методы, переменные — `snake_case`.
- Константы — `UPPER_SNAKE_CASE`.
- FSM-классы — суффикс `FSM` (пример: `AddDateFSM`, `SearchFSM`).
- Репозитории — суффикс `Repository` (пример: `DateRepository`).
- Сервисы — суффикс `Service` (пример: `DateService`).

### Callback data

Строго по схеме `действие:аргумент`:

```
loc:home / loc:outside
cash:1 / cash:2 / cash:3
time:1 / time:2 / time:3 / time:4
like:{date_id}
visited:{date_id}
next
fsm:back / fsm:cancel
```

---

## Документирование кода

### Главное правило: только Google-style docstrings. Никаких других комментариев

**Запрещено:**

```python
# Получаем пользователя из БД
user = await repo.get_by_id(user_id)
x = x + 1  # инкремент
```

**Правильно:**

```python
user = await repo.get_by_id(user_id)
```

Если нужно объяснение — оно идёт в docstring функции или класса. Код должен быть самодокументируемым через имена.

---

### Google-style docstring — формат

#### Функция / метод

```python
async def find_random(
    self,
    user_id: int,
    cash: int,
    time: int,
    is_home: bool,
) -> Date | None:
    """Возвращает случайное свидание по фильтрам, исключая посещённые.

    Args:
        user_id: Telegram ID пользователя.
        cash: Максимальный уровень затрат (1–3).
        time: Максимальная длительность в часах.
        is_home: True — дома, False — вне дома.

    Returns:
        Объект Date, если найдено подходящее свидание, иначе None.
    """
```

#### Класс

```python
class DateService:
    """Сервис для работы со свиданиями.

    Инкапсулирует бизнес-логику: поиск, лайки, отметка посещённых.
    Не знает про Telegram — принимает и возвращает только доменные объекты.

    Attributes:
        dates: Репозиторий свиданий.
        history: Репозиторий истории взаимодействий пользователя.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует сервис с переданной сессией БД.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.dates = DateRepository(session)
        self.history = HistoryRepository(session)
```

#### Исключения

Если метод может поднять исключение — документируй в секции `Raises`:

```python
    """...

    Raises:
        ValueError: Если cash выходит за пределы 1–3.
    """
```

#### Короткие очевидные методы

Для совсем простых геттеров или методов без аргументов достаточно однострочного docstring:

```python
async def get_all_admins(self) -> list[User]:
    """Возвращает список всех администраторов."""
```

---

### Что документировать обязательно

| Что | Нужен docstring |
| --- | --- |
| Все публичные функции и методы | ✅ |
| Все классы | ✅ |
| Все `__init__` с нетривиальной логикой | ✅ |
| Приватные методы (`_method`) | ✅ если логика не очевидна |
| `__init__` только с `self.x = x` | ❌ не нужен |
| Однострочные лямбды | ❌ не нужен |

---

## Структура файлов

Строго следуй структуре из `Architecture.md`. Не добавляй новые модули без необходимости:

```
bot/
├── main.py
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
│   ├── __init__.py        ← регистрирует все роутеры
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
    └── admin.py
```

---

## Работа с БД

- Сессия открывается **один раз на апдейт** через `DatabaseMiddleware` и передаётся через `data["session"]`.
- Репозитории **не открывают** новую сессию сами.
- `Base.metadata.create_all()` используется вместо Alembic (MVP).
- Движок: `sqlite+aiosqlite:///bot.db`.

---

## FSM

- Все `StatesGroup` — в одном файле `states.py`.
- Фильтры поиска хранятся в **FSM state data**, не в БД.
- На каждом шаге FSM доступны кнопки `← Назад` и `✖ Отмена`.
- После завершения сценария — `await state.clear()`.

---

## Логирование

Используй только `loguru`. Стандартный `logging` не использовать.

```python
from loguru import logger

logger.info("Бот запущен")
logger.error("Ошибка при добавлении свидания: {}", e)
```

---

## Что не входит в MVP — не реализовывай

- Alembic-миграции
- Docker / деплой
- Webhook (только polling)
- Хранение пользовательских предпочтений между сессиями
- Алгоритм рекомендаций
- Статистика для админа
