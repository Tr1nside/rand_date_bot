from aiogram import Dispatcher, Router

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
    dp.include_router(start_router)
    dp.include_router(user_dates_router)

    admin_router = Router()
    admin_router.message.middleware(AdminMiddleware())
    admin_router.callback_query.middleware(AdminMiddleware())
    admin_router.include_router(admin_dates_router)
    admin_router.include_router(admin_admins_router)
    dp.include_router(admin_router)
