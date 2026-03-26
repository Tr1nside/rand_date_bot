from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin import admin_fsm_nav_kb
from bot.services.user_service import UserService
from bot.states import AddAdminFSM, RemoveAdminFSM

router = Router()


@router.message(Command("list_admins"))
async def cmd_list_admins(message: Message, session: AsyncSession) -> None:
    """Отправляет список всех администраторов бота.

    Args:
        message: Входящее сообщение с командой /list_admins.
        session: Асинхронная сессия БД.
    """
    service = UserService(session)
    admins = await service.list_admins()

    if not admins:
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
    if not message.text.strip().lstrip("-").isdigit():
        await message.answer("⚠️ Введите корректный числовой Telegram ID.")
        return

    target_id = int(message.text.strip())
    await state.clear()

    service = UserService(session)
    success = await service.add_admin(target_id)

    if success:
        await message.answer(
            f"✅ Пользователь <code>{target_id}</code> назначен администратором.",
            parse_mode="HTML",
        )
    else:
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
    if not message.text.strip().lstrip("-").isdigit():
        await message.answer("⚠️ Введите корректный числовой Telegram ID.")
        return

    target_id = int(message.text.strip())

    if target_id == message.from_user.id:
        await message.answer("⚠️ Нельзя снять права администратора у самого себя.")
        return

    await state.clear()

    service = UserService(session)
    success = await service.remove_admin(target_id)

    if success:
        await message.answer(
            f"✅ Права администратора у <code>{target_id}</code> сняты.",
            parse_mode="HTML",
        )
    else:
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
    await state.clear()
    await message.answer("❌ Операция отменена.")
