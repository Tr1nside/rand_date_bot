from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User
from bot.db.repository import UserRepository


class UserService:
    """Сервис для управления пользователями и администраторами.

    Инкапсулирует логику регистрации и управления правами доступа.
    Не знает про Telegram — работает только с доменными объектами.

    Attributes:
        users: Репозиторий пользователей.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует сервис с переданной сессией БД.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.users = UserRepository(session)

    async def register(self, user_id: int, username: str | None) -> User:
        """Регистрирует пользователя, если он ещё не существует.

        Args:
            user_id: Telegram ID пользователя.
            username: Telegram-юзернейм пользователя.

        Returns:
            Объект User (новый или существующий).
        """
        return await self.users.get_or_create(user_id, username)

    async def add_admin(self, user_id: int) -> bool:
        """Назначает пользователя администратором.

        Args:
            user_id: Telegram ID пользователя.

        Returns:
            True если пользователь найден и обновлён, False если не найден.
        """
        user = await self.users.get_by_id(user_id)
        if not user:
            logger.warning("Attempted to change admin rights for non-existent user {}", user_id)
            return False

        result = await self.users.set_admin(user_id, True)
        if result:
            logger.info("User {} granted admin rights", user_id)
        else:
            logger.warning("Failed to grant admin rights: user {} not found", user_id)
        return result

    async def remove_admin(self, user_id: int) -> bool:
        """Снимает с пользователя права администратора.

        Args:
            user_id: Telegram ID пользователя.

        Returns:
            True если пользователь найден и обновлён, False если не найден.
        """
        user = await self.users.get_by_id(user_id)
        if not user:
            logger.warning("Attempted to change admin rights for non-existent user {}", user_id)
            return False
        result = await self.users.set_admin(user_id, False)
        if result:
            logger.info("User {} have been revoked admin rights", user_id)
        else:
            logger.warning("Failed to revoked admin rights: user {} not found", user_id)
        return result

    async def list_admins(self) -> list[User]:
        """Возвращает список всех администраторов."""
        return await self.users.get_all_admins()

    async def is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором.

        Args:
            user_id: Telegram ID пользователя.

        Returns:
            True если пользователь является администратором, иначе False.
        """
        user = await self.users.get_by_id(user_id)
        return user is not None and user.is_admin
