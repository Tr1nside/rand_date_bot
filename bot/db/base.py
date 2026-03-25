from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from bot.config import settings

engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.DB_PATH}",
    echo=False,
)

async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Базовый класс для всех SQLAlchemy-моделей проекта."""


async def init_db() -> None:
    """Создаёт все таблицы в БД и инициализирует первого администратора.

    При первом запуске применяет `Base.metadata.create_all`, затем
    проверяет наличие хотя бы одного администратора. Если админов нет
    и в конфиге задан `FIRST_ADMIN_ID` — создаёт пользователя-администратора.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _seed_first_admin()


async def _seed_first_admin() -> None:
    """Создаёт первого администратора из конфига, если в БД нет ни одного.

    Импорт репозитория выполняется внутри функции, чтобы избежать
    циклической зависимости на уровне модулей.
    """
    from bot.db.repository import UserRepository  # noqa: PLC0415

    if settings.FIRST_ADMIN_ID is None:
        return

    async with async_session() as session:
        repo = UserRepository(session)
        admins = await repo.get_all_admins()

        if not admins:
            user = await repo.get_or_create(
                user_id=settings.FIRST_ADMIN_ID,
                username=None,
            )
            await repo.set_admin(user_id=user.id, value=True)
            await session.commit()
