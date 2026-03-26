from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PhotoSize
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin import (
    admin_cash_kb,
    admin_fsm_nav_kb,
    admin_location_kb,
    admin_time_kb,
)
from bot.services.date_service import DateService
from bot.states import AddDateFSM

router = Router()

TIME_MAP: dict[str, int] = {"1": 1, "2": 2, "3": 3, "4": 4}


@router.message(Command("add_date"))
async def cmd_add_date(message: Message, state: FSMContext) -> None:
    """Запускает FSM добавления нового свидания.

    Args:
        message: Входящее сообщение с командой /add_date.
        state: FSM-контекст.
    """
    await state.set_state(AddDateFSM.description)
    await message.answer(
        "📝 <b>[1/5] Введите описание свидания:</b>",
        reply_markup=admin_fsm_nav_kb(show_back=False),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────
# Шаг 1 → 2: описание → бюджет
# ──────────────────────────────────────────────

@router.message(AddDateFSM.description, F.text)
async def fsm_add_description(message: Message, state: FSMContext) -> None:
    """Сохраняет описание и запрашивает уровень затрат.

    Args:
        message: Сообщение с описанием свидания.
        state: FSM-контекст.
    """
    await state.update_data(description=message.text)
    await state.set_state(AddDateFSM.cash)

    await message.answer(
        "💰 <b>[2/5] Укажите уровень затрат:</b>",
        reply_markup=admin_cash_kb(),
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────
# Шаг 2 → 3: бюджет → время
# ──────────────────────────────────────────────

@router.callback_query(AddDateFSM.cash, F.data.startswith("cash:"))
async def fsm_add_cash(query: CallbackQuery, state: FSMContext) -> None:
    """Сохраняет уровень затрат и запрашивает длительность.

    Args:
        query: Callback-запрос с уровнем затрат.
        state: FSM-контекст.
    """
    cash = int(query.data.split(":")[1])
    await state.update_data(cash=cash)
    await state.set_state(AddDateFSM.time)

    await query.message.answer(
        "⏱ <b>[3/5] Сколько часов займёт?</b>",
        reply_markup=admin_time_kb(),
        parse_mode="HTML",
    )
    await query.answer()


# ──────────────────────────────────────────────
# Шаг 3 → 4: время → локация
# ──────────────────────────────────────────────

@router.callback_query(AddDateFSM.time, F.data.startswith("time:"))
async def fsm_add_time(query: CallbackQuery, state: FSMContext) -> None:
    """Сохраняет длительность и запрашивает место проведения.

    Args:
        query: Callback-запрос с длительностью.
        state: FSM-контекст.
    """
    time_value = TIME_MAP[query.data.split(":")[1]]
    await state.update_data(time=time_value)
    await state.set_state(AddDateFSM.is_home)

    await query.message.answer(
        "🗺 <b>[4/5] Где проходит свидание?</b>",
        reply_markup=admin_location_kb(),
        parse_mode="HTML",
    )
    await query.answer()


# ──────────────────────────────────────────────
# Шаг 4 → 5: локация → фото
# ──────────────────────────────────────────────

@router.callback_query(AddDateFSM.is_home, F.data.in_({"loc:home", "loc:outside"}))
async def fsm_add_location(query: CallbackQuery, state: FSMContext) -> None:
    """Сохраняет место проведения и запрашивает фотографию.

    Args:
        query: Callback-запрос с выбором локации.
        state: FSM-контекст.
    """
    is_home = query.data == "loc:home"
    await state.update_data(is_home=is_home)
    await state.set_state(AddDateFSM.photo)

    await query.message.answer(
        "📷 <b>[5/5] Отправьте фото для свидания:</b>",
        reply_markup=admin_fsm_nav_kb(),
        parse_mode="HTML",
    )
    await query.answer()


# ──────────────────────────────────────────────
# Шаг 5: сохранение свидания
# ──────────────────────────────────────────────

@router.message(AddDateFSM.photo, F.photo)
async def fsm_add_photo(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Сохраняет фото, создаёт свидание в БД и завершает FSM.

    Args:
        message: Сообщение с фотографией.
        state: FSM-контекст с собранными данными.
        session: Асинхронная сессия БД.
    """
    photo: PhotoSize = message.photo[-1]
    data = await state.get_data()
    await state.clear()

    service = DateService(session)
    date = await service.add_date(
        description=data["description"],
        cash=data["cash"],
        time=data["time"],
        is_home=data["is_home"],
        photo_file_id=photo.file_id,
    )

    location_text = "🏠 Дома" if date.is_home else "🌆 Вне дома"
    cash_text = "💸" * date.cash

    await message.answer(
        f"✅ <b>Свидание добавлено!</b>\n\n"
        f"📋 {date.description}\n"
        f"{location_text} · {cash_text} · ⏱ {date.time} ч\n"
        f"ID: <code>{date.id}</code>",
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────
# Навигация: Назад / Отмена
# ──────────────────────────────────────────────

@router.callback_query(AddDateFSM.cash, F.data == "fsm:cancel")
@router.callback_query(AddDateFSM.time, F.data == "fsm:cancel")
@router.callback_query(AddDateFSM.is_home, F.data == "fsm:cancel")
@router.callback_query(AddDateFSM.photo, F.data == "fsm:cancel")
@router.message(AddDateFSM.description, F.data == "fsm:cancel")
async def fsm_add_cancel(
    event: Message | CallbackQuery, state: FSMContext
) -> None:
    """Отменяет добавление свидания и очищает FSM.

    Args:
        event: Message или CallbackQuery с командой отмены.
        state: FSM-контекст.
    """
    await state.clear()
    msg = event if isinstance(event, Message) else event.message
    await msg.answer("❌ Добавление свидания отменено.")
    if isinstance(event, CallbackQuery):
        await event.answer()


@router.callback_query(AddDateFSM.time, F.data == "fsm:back")
async def fsm_back_to_description(query: CallbackQuery, state: FSMContext) -> None:
    """Возвращает к шагу ввода уровня затрат.

    Args:
        query: Callback-запрос.
        state: FSM-контекст.
    """
    await state.set_state(AddDateFSM.cash)
    await query.message.answer(
        "💰 <b>[2/5] Укажите уровень затрат:</b>",
        reply_markup=admin_cash_kb(),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(AddDateFSM.is_home, F.data == "fsm:back")
async def fsm_back_to_cash(query: CallbackQuery, state: FSMContext) -> None:
    """Возвращает к шагу выбора длительности.

    Args:
        query: Callback-запрос.
        state: FSM-контекст.
    """
    await state.set_state(AddDateFSM.time)
    await query.message.answer(
        "⏱ <b>[3/5] Сколько часов займёт?</b>",
        reply_markup=admin_time_kb(),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(AddDateFSM.photo, F.data == "fsm:back")
async def fsm_back_to_location(query: CallbackQuery, state: FSMContext) -> None:
    """Возвращает к шагу выбора места проведения.

    Args:
        query: Callback-запрос.
        state: FSM-контекст.
    """
    await state.set_state(AddDateFSM.is_home)
    await query.message.answer(
        "🗺 <b>[4/5] Где проходит свидание?</b>",
        reply_markup=admin_location_kb(),
        parse_mode="HTML",
    )
    await query.answer()
