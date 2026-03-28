from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from bot.config import settings
from bot.db.models import User

engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.DB_PATH}",
    echo=False,
)
logger.info("Initializing database engine with SQLite at {}", settings.DB_PATH)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """Базовый класс для всех SQLAlchemy-моделей."""


async def init_db() -> None:
    """Инициализирует базу данных: создаёт таблицы и первого администратора.

    Последовательно выполняет:
    1. Создание всех таблиц по метаданным SQLAlchemy.
    2. Создание записи первого администратора, если задан FIRST_ADMIN_ID
       и в БД отсутствует хотя бы один админ.

    Raises:
        Exception: Если не удалось создать таблицы БД (ошибка пробрасывается дальше).
    """
    logger.info("Initializing database (creating tables)")

    await _create_tables()

    await _ensure_initial_admin()


async def _create_tables() -> None:
    """Создаёт все таблицы в БД через Base.metadata.create_all.

    Использует engine.begin() для безопасного получения соединения.
    Ошибки логируются и пробрасываются выше для корректной остановки бота.

    Raises:
        Exception: При ошибке создания таблиц.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        logger.exception("Failed to create database tables")
        raise
    else:
        logger.info("Database tables created successfully")


async def _ensure_initial_admin() -> None:
    """Создаёт первого администратора, если это необходимо.

    Проверяет наличие settings.FIRST_ADMIN_ID.
    Если значение задано и в БД нет ни одного пользователя с is_admin=True —
    создаёт новую запись администратора.

    Использует отдельную сессию для безопасной работы с БД.
    """

    if not settings.FIRST_ADMIN_ID:
        logger.debug("FIRST_ADMIN_ID not set, skipping initial admin creation")
        return

    logger.debug("FIRST_ADMIN_ID is set: {}", settings.FIRST_ADMIN_ID)

    async with async_session() as session:
        try:
            admin_find_result = await session.execute(
                select(User).where(User.is_admin == True).limit(1)  # noqa: E712
            )
            existing_admin = admin_find_result.scalar_one_or_none()

            if existing_admin:
                logger.debug("Admin already exists, skipping creation")
            else:
                logger.info(
                    "No admin found. Creating initial admin with id {}",
                    settings.FIRST_ADMIN_ID,
                )
                admin = User(
                    id=settings.FIRST_ADMIN_ID,
                    username=None,
                    is_admin=True,
                )
                session.add(admin)
                await session.commit()
                logger.info("Initial admin created successfully")

        except Exception:
            logger.exception("Failed to create initial admin")
