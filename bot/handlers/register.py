from aiogram import Dispatcher, Router
from loguru import logger

from bot.handlers.admin.admins import router as admin_admins_router
from bot.handlers.admin.dates import router as admin_dates_router
from bot.handlers.user.dates import router as user_dates_router
from bot.handlers.user.start import router as start_router
from bot.middlewares.admin import AdminMiddleware


def register_all_routers(dp: Dispatcher) -> None:
    """Регистрирует все роутеры в диспетчере.

    Пользовательские роутеры регистрируются напрямую.
    Adminские роутеры оборачиваются в отдельный роутер с AdminMiddleware.

    Args:
        dp: Диспетчер aiogram.
    """
    logger.debug("Registering routers")

    dp.include_router(start_router)
    dp.include_router(user_dates_router)
    logger.debug("User routers registered: start_router, user_dates_router")

    logger.debug("Initializing admin router with AdminMiddleware")
    admin_router = Router()

    logger.debug("AdminMiddleware attached to admin router")
    admin_router.message.middleware(AdminMiddleware())
    admin_router.callback_query.middleware(AdminMiddleware())

    logger.debug("Admin routers registered: admin_dates_router, admin_admins_router")
    admin_router.include_router(admin_dates_router)
    admin_router.include_router(admin_admins_router)
    dp.include_router(admin_router)
    logger.info("All routers registered successfully")
