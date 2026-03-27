from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Date
from bot.db.repository import DateRepository, HistoryRepository


class DateService:
    """Сервис для работы со свиданиями.

    Инкапсулирует бизнес-логику: поиск, лайки, отметка посещённых, добавление.
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
