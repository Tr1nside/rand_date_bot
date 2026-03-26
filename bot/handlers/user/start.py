from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.user import main_menu_kb
from bot.services.user_service import UserService

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    """Обрабатывает команду /start: регистрирует пользователя и показывает меню.

    Args:
        message: Входящее сообщение с командой /start.
        session: Асинхронная сессия БД, пробрасываемая через DatabaseMiddleware.
    """
    service = UserService(session)
    await service.register(message.from_user.id, message.from_user.username)

    await message.answer(
        "💘 <b>Привет! Я Date Randomizer Bot.</b>\n\n"
        "Я предложу тебе случайное свидание под твои параметры.\n"
        "Укажи фильтры — и вперёд! 🚀",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
