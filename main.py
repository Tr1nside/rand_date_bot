import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from loguru import logger

from bot.config import settings
from bot.db.base import init_db
from bot.handlers.register import register_all_routers
from bot.middlewares.database import DatabaseMiddleware


def _make_bot() -> Bot:
    """Создаёт экземпляр бота с опциональным прокси.

    Если в конфиге задан TELEGRAM_PROXY — подключается через него.
    Поддерживаются socks5://, socks4://, http://.

    Returns:
        Готовый экземпляр Bot.
    """
    default = DefaultBotProperties(parse_mode=ParseMode.HTML)

    if settings.TELEGRAM_PROXY:
        session = AiohttpSession(proxy=settings.TELEGRAM_PROXY)
        logger.info("Прокси включён: {}", settings.TELEGRAM_PROXY)
        return Bot(token=settings.BOT_TOKEN, session=session, default=default)

    return Bot(token=settings.BOT_TOKEN, default=default)


async def set_bot_commands(bot: Bot) -> None:
    """Устанавливает список команд бота в меню Telegram.

    Args:
        bot: Экземпляр бота aiogram.
    """
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="add_date", description="Добавить свидание (админ)"),
        BotCommand(command="add_admin", description="Добавить администратора (админ)"),
        BotCommand(command="remove_admin", description="Удалить администратора (админ)"),
        BotCommand(command="list_admins", description="Список администраторов (админ)"),
    ]
    await bot.set_my_commands(commands)


async def on_startup(bot: Bot) -> None:
    """Выполняется при старте polling: устанавливает команды меню.

    Ошибка сети не прерывает запуск бота — только логируется предупреждение.

    Args:
        bot: Экземпляр бота aiogram.
    """
    try:
        await set_bot_commands(bot)
        logger.info("Команды бота установлены.")
    except Exception as e:
        logger.warning("Не удалось установить команды бота: {}", e)


async def main() -> None:
    """Точка входа: инициализирует БД, настраивает бот и запускает polling."""
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("База данных готова.")

    bot = _make_bot()
    dp = Dispatcher()

    dp.update.middleware(DatabaseMiddleware())
    register_all_routers(dp)
    dp.startup.register(on_startup)

    logger.info("Бот запущен. Начинаю polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
