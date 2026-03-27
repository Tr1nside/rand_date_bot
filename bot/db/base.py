from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from bot.config import settings

engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.DB_PATH}",
    echo=False,
)
logger.info("Initializing database engine with SQLite at {}", settings.DB_PATH)

async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """Базовый класс для всех SQLAlchemy-моделей."""


async def init_db() -> None:
    """Создаёт все таблицы в базе данных и инициализирует первого администратора.

    Использует Base.metadata.create_all для создания таблиц.
    Если задан FIRST_ADMIN_ID в конфиге и в БД нет ни одного администратора —
    создаёт запись первого администратора.
    """
    logger.info("Initializing database (creating tables)")
    from bot.config import settings
    from bot.db.models import User

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception:
        logger.exception("Failed to create database tables")
        raise

    if settings.FIRST_ADMIN_ID:
        logger.debug("FIRST_ADMIN_ID is set: {}", settings.FIRST_ADMIN_ID)
        async with async_session() as session:
            from sqlalchemy import select

            admin_find_result = await session.execute(
                select(User).where(User.is_admin == True).limit(1)  # noqa: E712
            )
            existing_admin = admin_find_result.scalar_one_or_none()

            if not existing_admin:
                logger.info(
                    "No admin found. Creating initial admin with id {}", settings.FIRST_ADMIN_ID
                )
                admin = User(
                    id=settings.FIRST_ADMIN_ID,
                    username=None,
                    is_admin=True,
                )
                session.add(admin)
                await session.commit()
                logger.info("Initial admin created successfully")
            else:
                logger.debug("Admin already exists, skipping creation")
