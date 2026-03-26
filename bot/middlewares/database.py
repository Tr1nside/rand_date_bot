from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from bot.db.base import async_session


class DatabaseMiddleware(BaseMiddleware):
    """Middleware, открывающий сессию БД на каждый апдейт.

    Создаёт AsyncSession, помещает в data["session"] и закрывает после обработки.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Открывает сессию, передаёт управление хендлеру, закрывает сессию.

        Args:
            handler: Следующий обработчик в цепочке.
            event: Telegram-апдейт.
            data: Словарь контекстных данных апдейта.

        Returns:
            Результат вызова следующего обработчика.
        """
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)
