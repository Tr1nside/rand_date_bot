# Contributing

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone <repo-url>
cd <repo>
```

### 2. Создать окружение и установить зависимости

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 3. Настроить переменные окружения

```bash
cp .env.example .env
# Заполнить .env
```

### 4. Установить pre-commit хуки

```bash
pre-commit install
```

### 5. Запустить

```bash
python main.py
```

---

## Структура проекта

Подробно — в [`Architecture.md`](Architecture.md).

---

## Соглашения по коду

Подробно — в [`AI.md`](AI.md). Кратко:

- Линтер: `ruff` + WPS (`wemake-python-styleguide`). Нарушения WPS — блокируют коммит.
- Типы аннотируются везде. Используй `X | None` вместо `Optional[X]`.
- Импорты — только абсолютные, только в начале файла.
- `__init__.py` — всегда пустые.
- Логирование — через `loguru`, не `print`, не `logging`.

Проверить вручную:

```bash
ruff check .
ruff format .
```

---

## Соглашения по коммитам

Используем [Conventional Commits](https://www.conventionalcommits.org/).

### Формат

```bash
<тип>(<scope>): <описание>

[тело — опционально]

[футер — опционально]
```

### Типы

| Тип        | Когда использовать                              |
|------------|-------------------------------------------------|
| `feat`     | Новая функциональность                          |
| `fix`      | Исправление бага                                |
| `refactor` | Рефакторинг без изменения поведения             |
| `docs`     | Только документация                             |
| `chore`    | Тулинг, зависимости, конфиги (не влияет на код) |
| `style`    | Форматирование, линтер (не влияет на логику)    |
| `test`     | Добавление или правка тестов                    |

### Примеры

```bash
feat(handlers): add browsing state to SearchFSM
fix(db): handle missing photo_file_id in date card
refactor(handlers): move register_all_routers to handlers/register.py
docs(ai): document empty __init__.py policy and WPS rules
chore: update pre-commit hooks
```

### Правила

- Описание — на русском или английском, но одним языком в одном коммите.
- Строчные буквы, без точки в конце.
- Тема — до 72 символов.
- Если коммит большой — пиши тело через редактор (`git commit` без `-m`).

---

## Pre-commit хуки

Хуки запускаются автоматически перед каждым коммитом.
Запустить вручную на всех файлах:

```bash
pre-commit run --all-files
```

Если хук упал — почини, затем снова `git add` и `git commit`.
