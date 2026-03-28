from datetime import datetime
from typing import TypedDict

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Date, User, UserHistory

TOP_DATES_LIMIT = 5


class DateRepository:
    """Репозиторий для работы со свиданиями в базе данных."""

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
        visited_subq = (
            select(UserHistory.date_id)
            .where(
                UserHistory.user_id == user_id,
                UserHistory.dropped_at.isnot(None),
            )
            .scalar_subquery()
        )

        stmt = (
            select(Date)
            .where(
                Date.cash <= cash,
                Date.time <= time,
                Date.is_home == is_home,
                Date.id.not_in(visited_subq),
            )
            .order_by(func.random())
            .limit(1)
        )

        execute_result = await self._session.execute(stmt)
        scalar_result = execute_result.scalar_one_or_none()
        if scalar_result is None:
            logger.info(
                "No date found for user {} (cash={}, time={}, is_home={})",
                user_id,
                cash,
                time,
                is_home,
            )
        return scalar_result

    async def get_by_id(self, date_id: int) -> Date | None:
        """Возвращает свидание по его ID.

        Args:
            date_id: Идентификатор свидания.

        Returns:
            Объект Date или None если не найдено.
        """
        execute_result = await self._session.execute(select(Date).where(Date.id == date_id))
        return execute_result.scalar_one_or_none()

    async def add(self, date: Date) -> Date:
        """Добавляет новое свидание в базу данных.

        Args:
            date: Объект свидания для сохранения.

        Returns:
            Сохранённый объект Date с присвоенным ID.
        """
        self._session.add(date)
        await self._session.commit()
        await self._session.refresh(date)
        logger.info(
            "Date created (id={}, cash={}, time={}, is_home={})",
            date.id,
            date.cash,
            date.time,
            date.is_home,
        )
        return date


class UserRepository:
    """Репозиторий для работы с пользователями в базе данных."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, user_id: int, username: str | None) -> User:
        """Возвращает существующего пользователя или создаёт нового.

        Args:
            user_id: Telegram ID пользователя.
            username: Telegram-юзернейм пользователя.

        Returns:
            Объект User.
        """
        execute_result = await self._session.execute(select(User).where(User.id == user_id))
        user = execute_result.scalar_one_or_none()

        if user is None:
            user = User(id=user_id, username=username)
            self._session.add(user)
            await self._session.commit()
            await self._session.refresh(user)
            logger.info("New user created: {} (username={})", user_id, username)
        else:
            logger.debug("User {} fetched from DB", user_id)

        return user

    async def get_by_id(self, user_id: int) -> User | None:
        """Возвращает пользователя по его Telegram ID.

        Args:
            user_id: Telegram ID пользователя.

        Returns:
            Объект User или None если не найден.
        """
        execute_result = await self._session.execute(select(User).where(User.id == user_id))
        return execute_result.scalar_one_or_none()

    async def set_admin(self, user_id: int, action_value: bool) -> bool:
        """Устанавливает или снимает права администратора.

        Args:
            user_id: Telegram ID пользователя.
            action_value: True — назначить, False — снять.

        Returns:
            True если пользователь найден и обновлён, False если не найден.
        """
        user = await self.get_by_id(user_id)
        if user is None:
            logger.warning("Attempt to set admin for non-existing user {}", user_id)
            return False
        user.is_admin = action_value
        logger.info("User {} admin status changed to {}", user_id, action_value)
        await self._session.commit()
        return True

    async def get_all_admins(self) -> list[User]:
        """Возвращает список всех администраторов."""
        execute_result = await self._session.execute(select(User).where(User.is_admin.is_(True)))
        return list(execute_result.scalars().all())


class HistoryRepository:
    """Репозиторий для работы с историей взаимодействий пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, user_id: int, date_id: int) -> UserHistory:
        """Возвращает запись истории или создаёт новую для пары (user_id, date_id).

        Args:
            user_id: Telegram ID пользователя.
            date_id: Идентификатор свидания.

        Returns:
            Объект UserHistory.
        """
        execute_result = await self._session.execute(
            select(UserHistory).where(
                UserHistory.user_id == user_id,
                UserHistory.date_id == date_id,
            )
        )
        record = execute_result.scalar_one_or_none()

        if record is None:
            record = UserHistory(user_id=user_id, date_id=date_id)
            self._session.add(record)
            await self._session.commit()
            await self._session.refresh(record)

        return record

    async def toggle_like(self, user_id: int, date_id: int) -> bool:
        """Переключает состояние лайка для пары (user_id, date_id).

        Args:
            user_id: Telegram ID пользователя.
            date_id: Идентификатор свидания.

        Returns:
            Новое значение is_liked после переключения.
        """
        record = await self.get_or_create(user_id, date_id)
        record.is_liked = not record.is_liked
        await self._session.commit()
        logger.info("User {} toggled like for date {} -> {}", user_id, date_id, record.is_liked)
        return record.is_liked

    async def mark_visited(self, user_id: int, date_id: int) -> None:
        """Отмечает свидание как посещённое (устанавливает dropped_at = now).

        Args:
            user_id: Telegram ID пользователя.
            date_id: Идентификатор свидания.
        """
        record = await self.get_or_create(user_id, date_id)
        record.dropped_at = datetime.utcnow()
        logger.info("User {} marked date {} as visited", user_id, date_id)
        await self._session.commit()

    async def get_like_status(self, user_id: int, date_id: int) -> bool:
        """Возвращает текущий статус лайка для пары (user_id, date_id).

        Args:
            user_id: Telegram ID пользователя.
            date_id: Идентификатор свидания.

        Returns:
            True если свидание лайкнуто, иначе False.
        """
        execute_result = await self._session.execute(
            select(UserHistory).where(
                UserHistory.user_id == user_id,
                UserHistory.date_id == date_id,
            )
        )
        record = execute_result.scalar_one_or_none()
        return record.is_liked if record else False


class DateFilterStats(TypedDict):
    """Разбивка свиданий по фильтрам is_home и cash.

    Attributes:
        home_count: Количество свиданий дома.
        outside_count: Количество свиданий вне дома.
        cash_breakdown: Словарь вида {уровень_бюджета: количество}.
    """

    home_count: int
    outside_count: int
    cash_breakdown: dict[int, int]


class StatsRepository:
    """Репозиторий для получения агрегированной статистики бота.

    Предоставляет методы для сбора счётчиков по свиданиям и пользователям.
    Не содержит бизнес-логики — только SQL-агрегации.

    Attributes:
        _session: Асинхронная сессия SQLAlchemy.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_total_dates(self) -> int:
        """Возвращает общее количество свиданий в базе."""
        result = await self._session.execute(select(func.count(Date.id)))
        return result.scalar_one()

    async def get_top_liked(
        self,
        limit: int = TOP_DATES_LIMIT,
    ) -> list[tuple[Date, int]]:
        """Возвращает топ свиданий по количеству лайков.

        Args:
            limit: Максимальное количество записей в результате.

        Returns:
            Список кортежей (Date, количество_лайков), отсортированных по убыванию.
        """
        likes_count = func.count(UserHistory.id).label("likes_count")
        stmt = (
            select(Date, likes_count)
            .join(UserHistory, UserHistory.date_id == Date.id)
            .where(UserHistory.is_liked.is_(True))
            .group_by(Date.id)
            .order_by(func.count(UserHistory.id).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [(date, count) for date, count in result.all()]

    async def get_top_visited(
        self,
        limit: int = TOP_DATES_LIMIT,
    ) -> list[tuple[Date, int]]:
        """Возвращает топ свиданий по количеству посещений.

        Args:
            limit: Максимальное количество записей в результате.

        Returns:
            Список кортежей (Date, количество_посещений), отсортированных по убыванию.
        """
        visits_count = func.count(UserHistory.id).label("visits_count")
        stmt = (
            select(Date, visits_count)
            .join(UserHistory, UserHistory.date_id == Date.id)
            .where(UserHistory.dropped_at.isnot(None))
            .group_by(Date.id)
            .order_by(func.count(UserHistory.id).desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [(date, count) for date, count in result.all()]

    async def get_dates_count_by_filter(self) -> DateFilterStats:
        """Возвращает разбивку свиданий по месту и уровню бюджета.

        Returns:
            DateFilterStats с полями home_count, outside_count и cash_breakdown.
        """
        home_result = await self._session.execute(
            select(Date.is_home, func.count(Date.id)).group_by(Date.is_home)
        )
        home_rows = home_result.all()
        home_count = next((cnt for flag, cnt in home_rows if flag), 0)
        outside_count = next((cnt for flag, cnt in home_rows if not flag), 0)

        cash_result = await self._session.execute(
            select(Date.cash, func.count(Date.id)).group_by(Date.cash)
        )
        cash_breakdown: dict[int, int] = {}
        for level, cnt in cash_result.all():
            cash_breakdown[level] = cnt

        return DateFilterStats(
            home_count=home_count,
            outside_count=outside_count,
            cash_breakdown=cash_breakdown,
        )

    async def get_users_total(self) -> int:
        """Возвращает общее количество зарегистрированных пользователей."""
        result = await self._session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def get_active_users_count(self) -> int:
        """Возвращает количество пользователей хотя бы с одним посещением."""
        subq = (
            select(UserHistory.user_id)
            .where(UserHistory.dropped_at.isnot(None))
            .distinct()
            .subquery()
        )
        result = await self._session.execute(select(func.count()).select_from(subq))
        return result.scalar_one()

    async def get_admins_count(self) -> int:
        """Возвращает количество администраторов."""
        result = await self._session.execute(
            select(func.count(User.id)).where(User.is_admin.is_(True))
        )
        return result.scalar_one()
