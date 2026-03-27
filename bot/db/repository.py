from datetime import datetime

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Date, User, UserHistory


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
                "No date found for user %s (cash=%s, time=%s, is_home=%s)",
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
            "Date created (id=%s, cash=%s, time=%s, is_home=%s)",
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
            logger.info("New user created: %s (username=%s)", user_id, username)
        else:
            logger.debug("User %s fetched from DB", user_id)

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
            value: True — назначить, False — снять.

        Returns:
            True если пользователь найден и обновлён, False если не найден.
        """
        user = await self.get_by_id(user_id)
        if user is None:
            logger.warning("Attempt to set admin for non-existing user %s", user_id)
            return False
        user.is_admin = action_value
        logger.info("User %s admin status changed to %s", user_id, action_value)
        await self._session.commit()
        return True

    async def get_all_admins(self) -> list[User]:
        """Возвращает список всех администраторов."""
        execute_result = await self._session.execute(
            select(User).where(User.is_admin == True)  # noqa: E712
        )
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
        logger.info("User %s toggled like for date %s -> %s", user_id, date_id, record.is_liked)
        return record.is_liked

    async def mark_visited(self, user_id: int, date_id: int) -> None:
        """Отмечает свидание как посещённое (устанавливает dropped_at = now).

        Args:
            user_id: Telegram ID пользователя.
            date_id: Идентификатор свидания.
        """
        record = await self.get_or_create(user_id, date_id)
        record.dropped_at = datetime.utcnow()
        logger.info("User %s marked date %s as visited", user_id, date_id)
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
