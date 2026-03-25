from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Date, User, UserHistory


class DateRepository:
    """Репозиторий для работы со свиданиями.

    Содержит только SQL-операции над таблицей `dates`.
    Никакой бизнес-логики.

    Attributes:
        session: Асинхронная сессия SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_random(
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
        visited_subquery = (
            select(UserHistory.date_id)
            .where(
                UserHistory.user_id == user_id,
                UserHistory.dropped_at.is_not(None),
            )
            .scalar_subquery()
        )

        stmt = (
            select(Date)
            .where(
                Date.cash <= cash,
                Date.time <= time,
                Date.is_home == is_home,
                Date.id.not_in(visited_subquery),
            )
            .order_by(func.random())
            .limit(1)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, date_id: int) -> Date | None:
        """Возвращает свидание по его ID.

        Args:
            date_id: Первичный ключ свидания.

        Returns:
            Объект Date или None, если не найдено.
        """
        return await self._session.get(Date, date_id)

    async def add(self, date: Date) -> Date:
        """Добавляет новое свидание в базу данных.

        Args:
            date: Объект Date для сохранения.

        Returns:
            Сохранённый объект Date с присвоенным id.
        """
        self._session.add(date)
        await self._session.flush()
        await self._session.refresh(date)
        return date


class UserRepository:
    """Репозиторий для работы с пользователями.

    Содержит только SQL-операции над таблицей `users`.
    Никакой бизнес-логики.

    Attributes:
        _session: Асинхронная сессия SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, user_id: int, username: str | None) -> User:
        """Возвращает пользователя по ID или создаёт нового.

        Args:
            user_id: Telegram ID пользователя.
            username: Telegram username без @, может быть None.

        Returns:
            Существующий или только что созданный объект User.
        """
        user = await self._session.get(User, user_id)

        if user is None:
            user = User(id=user_id, username=username)
            self._session.add(user)
            await self._session.flush()

        return user

    async def get_by_id(self, user_id: int) -> User | None:
        """Возвращает пользователя по Telegram ID.

        Args:
            user_id: Telegram ID пользователя.

        Returns:
            Объект User или None, если не найден.
        """
        return await self._session.get(User, user_id)

    async def set_admin(self, user_id: int, value: bool) -> None:
        """Устанавливает или снимает флаг администратора у пользователя.

        Args:
            user_id: Telegram ID пользователя.
            value: True — назначить админом, False — снять права.
        """
        user = await self._session.get(User, user_id)
        if user is not None:
            user.is_admin = value
            await self._session.flush()

    async def get_all_admins(self) -> list[User]:
        """Возвращает список всех администраторов."""
        stmt = select(User).where(User.is_admin.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class HistoryRepository:
    """Репозиторий для работы с историей взаимодействий.

    Содержит только SQL-операции над таблицей `user_history`.
    Никакой бизнес-логики.

    Attributes:
        _session: Асинхронная сессия SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, user_id: int, date_id: int) -> UserHistory:
        """Возвращает запись истории или создаёт новую.

        Args:
            user_id: Telegram ID пользователя.
            date_id: ID свидания.

        Returns:
            Существующий или только что созданный объект UserHistory.
        """
        stmt = select(UserHistory).where(
            UserHistory.user_id == user_id,
            UserHistory.date_id == date_id,
        )
        result = await self._session.execute(stmt)
        history = result.scalar_one_or_none()

        if history is None:
            history = UserHistory(user_id=user_id, date_id=date_id)
            self._session.add(history)
            await self._session.flush()

        return history

    async def toggle_like(self, user_id: int, date_id: int) -> bool:
        """Переключает лайк пользователя на свидание.

        Args:
            user_id: Telegram ID пользователя.
            date_id: ID свидания.

        Returns:
            Новое значение флага is_liked после переключения.
        """
        history = await self.get_or_create(user_id=user_id, date_id=date_id)
        history.is_liked = not history.is_liked
        await self._session.flush()
        return history.is_liked

    async def mark_visited(self, user_id: int, date_id: int) -> None:
        """Отмечает свидание как посещённое — устанавливает dropped_at.

        Args:
            user_id: Telegram ID пользователя.
            date_id: ID свидания.
        """
        history = await self.get_or_create(user_id=user_id, date_id=date_id)
        history.dropped_at = datetime.utcnow()
        await self._session.flush()
