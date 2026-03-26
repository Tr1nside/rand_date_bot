from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.user import (
    date_card_kb,
    main_menu_kb,
    search_cash_kb,
    search_location_kb,
    search_time_kb,
)
from bot.services.date_service import DateService
from bot.services.user_service import UserService
from bot.states import SearchFSM

router = Router()

TIME_MAP: dict[str, int] = {"1": 1, "2": 2, "3": 3, "4": 4}


async def _send_date_card(
    query: CallbackQuery,
    session: AsyncSession,
    user_id: int,
    cash: int,
    time: int,
    is_home: bool,
) -> None:
    """Ищет случайное свидание и отправляет карточку пользователю.

    Если свиданий не найдено — отправляет сообщение об отсутствии вариантов.

    Args:
        query: Callback-запрос от пользователя.
        session: Асинхронная сессия БД.
        user_id: Telegram ID пользователя.
        cash: Максимальный уровень затрат.
        time: Максимальная длительность в часах.
        is_home: True — дома, False — вне дома.
    """
    service = DateService(session)
    date = await service.find_random(user_id, cash, time, is_home)

    if date is None:
        await query.message.answer(
            "😔 <b>Ничего не найдено.</b>\n\n"
            "Попробуй изменить параметры поиска.",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
        return

    is_liked = await service.get_like_status(user_id, date.id)
    location_text = "🏠 Дома" if date.is_home else "🌆 Вне дома"
    cash_text = "💸" * date.cash

    caption = (
        f"{date.description}\n\n"
        f"{location_text} · {cash_text} · ⏱ {date.time} ч"
    )

    await query.message.answer_photo(
        photo=date.photo_file_id,
        caption=caption,
        reply_markup=date_card_kb(date.id, is_liked),
    )


# ──────────────────────────────────────────────
# Шаг 1: старт поиска — выбор локации
# ──────────────────────────────────────────────

@router.callback_query(F.data == "loc:start")
async def cb_search_start(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Начинает сценарий поиска: регистрирует пользователя и показывает выбор локации.

    Args:
        query: Callback-запрос.
        state: FSM-контекст.
        session: Асинхронная сессия БД.
    """
    service = UserService(session)
    await service.register(query.from_user.id, query.from_user.username)

    await state.set_state(SearchFSM.is_home)
    await query.message.answer(
        "🗺 <b>Где проведём свидание?</b>",
        reply_markup=search_location_kb(),
        parse_mode="HTML",
    )
    await query.answer()


# ──────────────────────────────────────────────
# Шаг 2: выбор бюджета
# ──────────────────────────────────────────────

@router.callback_query(SearchFSM.is_home, F.data.in_({"loc:home", "loc:outside"}))
async def cb_search_location(query: CallbackQuery, state: FSMContext) -> None:
    """Сохраняет выбранную локацию и переходит к выбору бюджета.

    Args:
        query: Callback-запрос с данными о локации.
        state: FSM-контекст.
    """
    is_home = query.data == "loc:home"
    await state.update_data(is_home=is_home)
    await state.set_state(SearchFSM.cash)

    await query.message.answer(
        "💰 <b>Какой бюджет?</b>",
        reply_markup=search_cash_kb(),
        parse_mode="HTML",
    )
    await query.answer()


# ──────────────────────────────────────────────
# Шаг 3: выбор времени
# ──────────────────────────────────────────────

@router.callback_query(SearchFSM.cash, F.data.startswith("cash:"))
async def cb_search_cash(query: CallbackQuery, state: FSMContext) -> None:
    """Сохраняет выбранный бюджет и переходит к выбору длительности.

    Args:
        query: Callback-запрос с уровнем затрат.
        state: FSM-контекст.
    """
    cash = int(query.data.split(":")[1])
    await state.update_data(cash=cash)
    await state.set_state(SearchFSM.time)

    await query.message.answer(
        "⏱ <b>Сколько времени?</b>",
        reply_markup=search_time_kb(),
        parse_mode="HTML",
    )
    await query.answer()


# ──────────────────────────────────────────────
# Шаг 4: показать карточку
# ──────────────────────────────────────────────

@router.callback_query(SearchFSM.time, F.data.startswith("time:"))
async def cb_search_time(
    query: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Сохраняет время, завершает сбор фильтров и отображает карточку свидания.

    Args:
        query: Callback-запрос с длительностью.
        state: FSM-контекст.
        session: Асинхронная сессия БД.
    """
    time_value = TIME_MAP[query.data.split(":")[1]]
    await state.update_data(time=time_value)

    data = await state.get_data()
    await state.clear()

    await _send_date_card(
        query=query,
        session=session,
        user_id=query.from_user.id,
        cash=data["cash"],
        time=data["time"],
        is_home=data["is_home"],
    )
    await query.answer()


# ──────────────────────────────────────────────
# Навигация: Назад / Отмена в поиске
# ──────────────────────────────────────────────

@router.callback_query(SearchFSM.cash, F.data == "fsm:cancel")
@router.callback_query(SearchFSM.time, F.data == "fsm:cancel")
async def cb_search_cancel(query: CallbackQuery, state: FSMContext) -> None:
    """Отменяет поиск и возвращает в главное меню.

    Args:
        query: Callback-запрос.
        state: FSM-контекст.
    """
    await state.clear()
    await query.message.answer(
        "Поиск отменён. Возвращаемся в меню 👇",
        reply_markup=main_menu_kb(),
    )
    await query.answer()


@router.callback_query(SearchFSM.time, F.data == "fsm:back")
async def cb_search_back_to_cash(query: CallbackQuery, state: FSMContext) -> None:
    """Возвращает к выбору бюджета с шага выбора времени.

    Args:
        query: Callback-запрос.
        state: FSM-контекст.
    """
    await state.set_state(SearchFSM.cash)
    await query.message.answer(
        "💰 <b>Какой бюджет?</b>",
        reply_markup=search_cash_kb(),
        parse_mode="HTML",
    )
    await query.answer()


# ──────────────────────────────────────────────
# Карточка: лайк, посещение, другое
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("like:"))
async def cb_like(query: CallbackQuery, session: AsyncSession) -> None:
    """Переключает лайк на свидании и обновляет клавиатуру карточки.

    Args:
        query: Callback-запрос с ID свидания.
        session: Асинхронная сессия БД.
    """
    date_id = int(query.data.split(":")[1])
    service = DateService(session)
    new_is_liked = await service.toggle_like(query.from_user.id, date_id)

    await query.message.edit_reply_markup(
        reply_markup=date_card_kb(date_id, new_is_liked)
    )
    await query.answer("❤️ Лайк!" if new_is_liked else "💔 Лайк убран")


@router.callback_query(F.data.startswith("visited:"))
async def cb_visited(query: CallbackQuery, session: AsyncSession) -> None:
    """Отмечает свидание как посещённое и убирает карточку.

    Args:
        query: Callback-запрос с ID свидания.
        session: Асинхронная сессия БД.
    """
    date_id = int(query.data.split(":")[1])
    service = DateService(session)
    await service.mark_visited(query.from_user.id, date_id)

    await query.message.edit_reply_markup(reply_markup=None)
    await query.message.answer(
        "✅ <b>Отлично! Надеемся, было здорово 🎉</b>\n\n"
        "Хочешь ещё одно свидание?",
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
    await query.answer()


@router.callback_query(F.data == "next")
async def cb_next(
    query: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """Показывает другое свидание с теми же фильтрами из FSM state.

    Если фильтры в state отсутствуют — предлагает начать поиск заново.

    Args:
        query: Callback-запрос.
        state: FSM-контекст с сохранёнными фильтрами.
        session: Асинхронная сессия БД.
    """
    data = await state.get_data()
    cash = data.get("cash")
    time = data.get("time")
    is_home = data.get("is_home")

    if cash is None or time is None or is_home is None:
        await query.message.answer(
            "Фильтры устарели. Начни поиск заново 👇",
            reply_markup=main_menu_kb(),
        )
        await query.answer()
        return

    await _send_date_card(
        query=query,
        session=session,
        user_id=query.from_user.id,
        cash=cash,
        time=time,
        is_home=is_home,
    )
    await query.answer()
