from typing import TypedDict

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Date
from bot.db.repository import DateRepository, HistoryRepository, StatsRepository


class BotStats(TypedDict):
    """DTO с агрегированной статистикой бота.

    Attributes:
        total_dates: Общее количество свиданий в базе.
        top_liked: Топ свиданий по лайкам — список кортежей (Date, количество).
        top_visited: Топ свиданий по посещениям — список кортежей (Date, количество).
        home_count: Количество домашних свиданий.
        outside_count: Количество свиданий вне дома.
        cash_breakdown: Разбивка по уровню бюджета {уровень: количество}.
        total_users: Общее число зарегистрированных пользователей.
        active_users: Число пользователей хотя бы с одним посещением.
        admins_count: Количество администраторов.
    """

    total_dates: int
    top_liked: list[tuple[Date, int]]
    top_visited: list[tuple[Date, int]]
    home_count: int
    outside_count: int
    cash_breakdown: dict[int, int]
    total_users: int
    active_users: int
    admins_count: int


class DateService:
    """Сервис для работы со свиданиями.

    Инкапсулирует бизнес-логику: поиск, лайки, отметка посещённых, добавление,
    а также агрегация статистики.
    Не знает про Telegram — принимает и возвращает только доменные объекты.

    Attributes:
        dates: Репозиторий свиданий.
        history: Репозиторий истории взаимодействий пользователя.
        stats: Репозиторий агрегированной статистики.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует сервис с переданной сессией БД.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.dates = DateRepository(session)
        self.history = HistoryRepository(session)
        self.stats = StatsRepository(session)

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
            Объект Date если найдено подходящее свидание, иначе None.
        """
        return await self.dates.get_random(user_id, cash, time, is_home)

    async def toggle_like(self, user_id: int, date_id: int) -> bool:
        """Переключает лайк пользователя на свидании.

        Args:
            user_id: Telegram ID пользователя.
            date_id: Идентификатор свидания.

        Returns:
            Новое значение is_liked после переключения.
        """
        new_status = await self.history.toggle_like(user_id, date_id)

        logger.info(
            "User {} toggled like on date {} → {}",
            user_id,
            date_id,
            "liked" if new_status else "unliked",
        )
        return new_status

    async def mark_visited(self, user_id: int, date_id: int) -> None:
        """Отмечает свидание как посещённое пользователем.

        Args:
            user_id: Telegram ID пользователя.
            date_id: Идентификатор свидания.
        """
        await self.history.mark_visited(user_id, date_id)

    async def get_like_status(self, user_id: int, date_id: int) -> bool:
        """Возвращает текущий статус лайка.

        Args:
            user_id: Telegram ID пользователя.
            date_id: Идентификатор свидания.

        Returns:
            True если свидание лайкнуто, иначе False.
        """
        return await self.history.get_like_status(user_id, date_id)

    async def add_date(
        self,
        description: str,
        cash: int,
        time: int,
        is_home: bool,
        photo_file_id: str,
    ) -> Date:
        """Создаёт и сохраняет новое свидание.

        Args:
            description: Текстовое описание свидания.
            cash: Уровень затрат (1–3).
            time: Длительность в часах.
            is_home: True — дома, False — вне дома.
            photo_file_id: Telegram file_id фотографии.

        Returns:
            Созданный объект Date с присвоенным ID.

        Raises:
            ValueError: Если cash выходит за пределы 1–3 или time меньше 1.
        """
        if cash not in (1, 2, 3):
            raise ValueError(f"Invalid cash: {cash}")
        if time < 1:
            raise ValueError(f"Invalid time: {time}")
        date = Date(
            description=description,
            cash=cash,
            time=time,
            is_home=is_home,
            photo_file_id=photo_file_id,
        )
        try:
            saved_date = await self.dates.add(date)
            logger.info("New date added: id={}, desc={}", saved_date.id, description)
            return saved_date
        except Exception as _:
            logger.exception("Failed to add date: {}", description)
            raise

    async def get_stats(self) -> BotStats:
        """Собирает и возвращает агрегированную статистику бота.

        Выполняет параллельные запросы к StatsRepository и собирает
        результаты в единый DTO.

        Returns:
            BotStats со всеми разделами статистики.
        """
        filter_stats = await self.stats.get_dates_count_by_filter()
        return BotStats(
            total_dates=await self.stats.get_total_dates(),
            top_liked=await self.stats.get_top_liked(),
            top_visited=await self.stats.get_top_visited(),
            home_count=filter_stats["home_count"],
            outside_count=filter_stats["outside_count"],
            cash_breakdown=filter_stats["cash_breakdown"],
            total_users=await self.stats.get_users_total(),
            active_users=await self.stats.get_active_users_count(),
            admins_count=await self.stats.get_admins_count(),
        )
