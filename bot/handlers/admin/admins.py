from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin import admin_fsm_nav_kb
from bot.services.date_service import BotStats, DateService
from bot.services.user_service import UserService
from bot.states import AddAdminFSM, RemoveAdminFSM

router = Router()

MAX_DESCRIPTION_LENGTH = 45
CASH_LABELS = {1: "💸", 2: "💸💸", 3: "💸💸💸"}


def _truncate_description(text: str) -> str:
    """Обрезает описание свидания до допустимой длины.

    Args:
        text: Исходный текст описания.

    Returns:
        Текст длиной не более MAX_DESCRIPTION_LENGTH символов.
    """
    if len(text) <= MAX_DESCRIPTION_LENGTH:
        return text
    return text[:MAX_DESCRIPTION_LENGTH] + "…"


def _format_stats_message(stats: BotStats) -> str:
    """Формирует HTML-сообщение со статистикой бота.

    Args:
        stats: DTO с агрегированной статистикой.

    Returns:
        Отформатированная строка для отправки с parse_mode='HTML'.
    """
    lines: list[str] = []

    lines.append("📊 <b>Статистика бота</b>\n")

    lines.append("📅 <b>Свидания</b>")
    lines.append(f"Всего в базе: <b>{stats['total_dates']}</b>\n")

    lines.append("❤️ <b>Топ-5 по лайкам:</b>")
    if stats["top_liked"]:
        for idx, (date, count) in enumerate(stats["top_liked"], start=1):
            desc = _truncate_description(date.description)
            lines.append(f"{idx}. {desc} — <b>{count}</b> лайк(ов)")
    else:
        lines.append("Нет данных")

    lines.append("")
    lines.append("✅ <b>Топ-5 по посещениям:</b>")
    if stats["top_visited"]:
        for idx, (date, count) in enumerate(stats["top_visited"], start=1):
            desc = _truncate_description(date.description)
            lines.append(f"{idx}. {desc} — <b>{count}</b> посещений")
    else:
        lines.append("Нет данных")

    lines.append("")
    lines.append("🏠 <b>По месту:</b>")
    lines.append(f"• Дома: <b>{stats['home_count']}</b>")
    lines.append(f"• Вне дома: <b>{stats['outside_count']}</b>")

    lines.append("")
    lines.append("💸 <b>По бюджету:</b>")
    for level in (1, 2, 3):
        count = stats["cash_breakdown"].get(level, 0)
        label = CASH_LABELS[level]
        lines.append(f"• {label}: <b>{count}</b>")

    lines.append("")
    lines.append("👥 <b>Пользователи</b>")
    lines.append(f"• Всего: <b>{stats['total_users']}</b>")
    lines.append(f"• Активных: <b>{stats['active_users']}</b>")
    lines.append(f"• Администраторов: <b>{stats['admins_count']}</b>")

    return "\n".join(lines)


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    """Отправляет агрегированную статистику бота администратору.

    Args:
        message: Входящее сообщение с командой /stats.
        session: Асинхронная сессия БД.
    """
    if message.from_user:
        logger.info("User {} requested bot stats", message.from_user.id)

    service = DateService(session)
    try:
        stats = await service.get_stats()
    except Exception as exc:
        logger.exception(
            "Failed to fetch stats for user {}: {}", message.from_user and message.from_user.id, exc
        )
        await message.answer("⚠️ Не удалось получить статистику. Попробуйте позже.")
        return

    await message.answer(_format_stats_message(stats), parse_mode="HTML")


@router.message(Command("list_admins"))
async def cmd_list_admins(message: Message, session: AsyncSession) -> None:
    """Отправляет список всех администраторов бота.

    Args:
        message: Входящее сообщение с командой /list_admins.
        session: Асинхронная сессия БД.
    """
    if message.from_user:
        logger.info("User {} requested admin list", message.from_user.id)
    service = UserService(session)
    admins = await service.list_admins()

    if not admins:
        logger.warning("Admin list requested but no admins found")
        await message.answer("Администраторов пока нет.")
        return

    lines = []
    for admin in admins:
        name = f"@{admin.username}" if admin.username else f"ID: {admin.id}"
        lines.append(f"• {name} (<code>{admin.id}</code>)")

    await message.answer(
        "👑 <b>Администраторы:</b>\n\n" + "\n".join(lines),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────
# Добавление администратора
# ──────────────────────────────────────────────


@router.message(Command("add_admin"))
async def cmd_add_admin(message: Message, state: FSMContext) -> None:
    """Запускает FSM добавления нового администратора.

    Args:
        message: Входящее сообщение с командой /add_admin.
        state: FSM-контекст.
    """
    if message.from_user:
        logger.info("User {} started add_admin FSM", message.from_user.id)
    await state.set_state(AddAdminFSM.telegram_id)
    await message.answer(
        "👤 Введите <b>Telegram ID</b> нового администратора:",
        reply_markup=admin_fsm_nav_kb(show_back=False),
        parse_mode="HTML",
    )


@router.message(AddAdminFSM.telegram_id, F.text)
async def fsm_add_admin_id(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обрабатывает ввод Telegram ID и назначает пользователя администратором.

    Args:
        message: Сообщение с Telegram ID нового администратора.
        state: FSM-контекст.
        session: Асинхронная сессия БД.
    """
    if message.from_user is None:
        logger.warning("User data in message is None")
        return
    if message.text is None:
        await message.answer("⚠️ Введите корректный числовой Telegram ID.")
        return
    if not message.text.strip().lstrip("-").isdigit():
        logger.warning("User {} entered invalid admin ID: {}", message.from_user.id, message.text)
        await message.answer("⚠️ Введите корректный числовой Telegram ID.")
        return

    target_id = int(message.text.strip())

    logger.info("User {} attempting to add admin {}", message.from_user.id, target_id)
    await state.clear()

    service = UserService(session)
    success = await service.add_admin(target_id)

    if success:
        await message.answer(
            f"✅ Пользователь <code>{target_id}</code> назначен администратором.",
            parse_mode="HTML",
        )
    else:
        logger.warning(
            "User {} tried to add non-existing user {} as admin", message.from_user.id, target_id
        )
        await message.answer(
            f"⚠️ Пользователь <code>{target_id}</code> не найден в базе.\n"
            "Он должен сначала написать /start боту.",
            parse_mode="HTML",
        )


# ──────────────────────────────────────────────
# Удаление администратора
# ──────────────────────────────────────────────


@router.message(Command("remove_admin"))
async def cmd_remove_admin(message: Message, state: FSMContext) -> None:
    """Запускает FSM удаления администратора.

    Args:
        message: Входящее сообщение с командой /remove_admin.
        state: FSM-контекст.
    """
    if message.from_user:
        logger.info("User {} started remove_admin FSM", message.from_user.id)
    await state.set_state(RemoveAdminFSM.telegram_id)
    await message.answer(
        "👤 Введите <b>Telegram ID</b> администратора для удаления:",
        reply_markup=admin_fsm_nav_kb(show_back=False),
        parse_mode="HTML",
    )


@router.message(RemoveAdminFSM.telegram_id, F.text)
async def fsm_remove_admin_id(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Обрабатывает ввод Telegram ID и снимает права администратора.

    Args:
        message: Сообщение с Telegram ID удаляемого администратора.
        state: FSM-контекст.
        session: Асинхронная сессия БД.
    """
    if message.from_user is None:
        logger.warning("User data in message is None")
        return
    if message.text is None:
        await message.answer("⚠️ Введите корректный числовой Telegram ID.")
        return
    if not message.text.strip().lstrip("-").isdigit():
        logger.warning(
            "User {} entered invalid admin ID for removal: {}", message.from_user.id, message.text
        )
        await message.answer("⚠️ Введите корректный числовой Telegram ID.")
        return

    target_id = int(message.text.strip())
    if message.from_user and target_id == message.from_user.id:
        logger.warning(
            "User {} попытался снять права администратора у самого себя", message.from_user.id
        )
        await message.answer("⚠️ Нельзя снять права администратора у самого себя.")
        return

    await state.clear()

    service = UserService(session)
    logger.info("User {} attempting to remove admin {}", message.from_user.id, target_id)
    success = await service.remove_admin(target_id)

    if success:
        logger.info("User {} removed admin {}", message.from_user.id, target_id)
        await message.answer(
            f"✅ Права администратора у <code>{target_id}</code> сняты.",
            parse_mode="HTML",
        )
    else:
        logger.warning(
            "User {} tried to remove non-existing admin {}", message.from_user.id, target_id
        )
        await message.answer(
            f"⚠️ Пользователь <code>{target_id}</code> не найден в базе.",
            parse_mode="HTML",
        )


# ──────────────────────────────────────────────
# Отмена FSM
# ──────────────────────────────────────────────


@router.message(AddAdminFSM.telegram_id, F.data == "fsm:cancel")
@router.message(RemoveAdminFSM.telegram_id, F.data == "fsm:cancel")
async def fsm_admin_cancel(message: Message, state: FSMContext) -> None:
    """Отменяет текущий FSM-сценарий управления администраторами.

    Args:
        message: Входящее сообщение с командой отмены.
        state: FSM-контекст.
    """
    if message.from_user:
        logger.info("User {} canceled admin FSM", message.from_user.id)
    await state.clear()
    await message.answer("❌ Операция отменена.")
