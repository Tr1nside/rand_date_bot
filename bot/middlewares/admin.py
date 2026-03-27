from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repository import UserRepository


class AdminMiddleware(BaseMiddleware):
    """Middleware, проверяющий права администратора перед обработкой апдейта.

    Вешается только на admin-роутер. Если пользователь не является
    администратором — отвечает отказом и не передаёт управление хендлеру.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Проверяет статус администратора и либо передаёт управление, либо отказывает.

        Args:
            handler: Следующий обработчик в цепочке.
            event: Telegram-апдейт.
            data: Словарь контекстных данных, содержащий session и event_from_user.

        Returns:
            Результат вызова следующего обработчика или None при отказе в доступе.
        """
        user = data.get("event_from_user")
        session: AsyncSession = data["session"]

        if user is None:
            logger.warning("AdminMiddleware: event without user")
            return

        logger.debug("AdminMiddleware: checking admin for user_id={}", user.id)
        db_user = await UserRepository(session).get_by_id(user.id)

        if not db_user or not db_user.is_admin:
            logger.warning(
                "Admin access denied: user_id={}, is_admin={}",
                user.id,
                getattr(db_user, "is_admin", None),
            )

        logger.debug("Admin access granted: user_id={}", user.id)
        return await handler(event, data)
