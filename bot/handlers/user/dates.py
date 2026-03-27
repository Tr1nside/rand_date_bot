from contextlib import suppress

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InaccessibleMessage, InputMediaPhoto
from loguru import logger
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


async def _cleanup_and_send(query: CallbackQuery, text: str, **kwargs) -> None:
    """Удаляет предыдущее сообщение и отправляет новое."""
    if query.message and not isinstance(query.message, InaccessibleMessage):
        with suppress(Exception):
            try:
                await query.message.delete()
            except Exception as e:
                logger.debug("Failed to delete message: {}", e)
        await query.message.answer(text, **kwargs)
    else:
        await query.answer(text, show_alert=True)


# ──────────────────────────────────────────────
# Шаг 1: старт поиска — выбор локации
# ──────────────────────────────────────────────


@router.callback_query(F.data == "loc:start")
async def cb_search_start(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Начинает сценарий поиска: регистрирует пользователя и показывает выбор локации."""
    service = UserService(session)

    logger.info(
        "User {} started search FSM (username={})", query.from_user.id, query.from_user.username
    )
    await service.register(query.from_user.id, query.from_user.username)

    await state.set_state(SearchFSM.is_home)
    await _cleanup_and_send(
        query,
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
    """Сохраняет выбранную локацию и переходит к выбору бюджета."""
    is_home = query.data == "loc:home"
    logger.debug(
        "User {} selected location: {}", query.from_user.id, "home" if is_home else "outside"
    )
    await state.update_data(is_home=is_home)
    await state.set_state(SearchFSM.cash)

    await _cleanup_and_send(
        query,
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
    """Сохраняет выбранный бюджет и переходит к выбору длительности."""
    if not query.data:
        return
    cash = int(query.data.split(":")[1])
    logger.debug("User {} selected cash: {}", query.from_user.id, cash)
    await state.update_data(cash=cash)
    await state.set_state(SearchFSM.time)

    await _cleanup_and_send(
        query,
        "⏱ <b>Сколько времени?</b>",
        reply_markup=search_time_kb(),
        parse_mode="HTML",
    )
    await query.answer()


# ──────────────────────────────────────────────
# Шаг 4: показать карточку
# ──────────────────────────────────────────────


@router.callback_query(SearchFSM.time, F.data.startswith("time:"))
async def cb_search_time(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Сохраняет время, завершает сбор фильтров и отображает карточку свидания."""
    if not query.data or not query.message:
        return
    time_value = TIME_MAP[query.data.split(":")[1]]
    logger.debug("User {} selected time: {}", query.from_user.id, time_value)
    await state.update_data(time=time_value)
    data = await state.get_data()

    await state.set_state(SearchFSM.browsing)

    service = DateService(session)
    logger.info(
        "User {} searching date (cash={}, time={}, is_home={})",
        query.from_user.id,
        data["cash"],
        data["time"],
        data["is_home"],
    )
    try:
        date = await service.find_random(
            query.from_user.id, data["cash"], data["time"], data["is_home"]
        )
    except Exception:
        logger.exception("Search failed for user {}", query.from_user.id)
        raise

    if date is None:
        logger.info(
            "No date found for user {} (cash={}, time={}, is_home={})",
            query.from_user.id,
            data["cash"],
            data["time"],
            data["is_home"],
        )
        await _cleanup_and_send(
            query,
            "😔  <b>Ничего не найдено.</b>\n\nПопробуй изменить параметры поиска.",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
        await query.answer()
        return

    logger.info("User {} received date {}", query.from_user.id, date.id)
    is_liked = await service.get_like_status(query.from_user.id, date.id)
    location_text = "🏠 Дома" if date.is_home else "🌆 Вне дома"
    cash_text = "💸" * date.cash
    caption = f"{date.description}\n\n{location_text} · {cash_text} · ⏱ {date.time} ч"

    # 🔹 Отправляем фото или текст в зависимости от наличия фото
    if query.message and not isinstance(query.message, InaccessibleMessage):
        with suppress(Exception):
            await query.message.delete()

        if date.photo_file_id:
            await query.message.answer_photo(
                photo=date.photo_file_id,
                caption=caption,
                reply_markup=date_card_kb(date.id, is_liked),
                parse_mode="HTML",
            )
        else:
            await query.message.answer(
                caption,
                reply_markup=date_card_kb(date.id, is_liked),
                parse_mode="HTML",
            )
    else:
        if date.photo_file_id:
            await query.message.answer_photo(
                photo=date.photo_file_id,
                caption=caption,
                reply_markup=date_card_kb(date.id, is_liked),
                parse_mode="HTML",
            )
        else:
            await query.message.answer(
                caption,
                reply_markup=date_card_kb(date.id, is_liked),
                parse_mode="HTML",
            )
    await query.answer()


# ──────────────────────────────────────────────
# Навигация: Назад / Отмена в поиске
# ──────────────────────────────────────────────


@router.callback_query(SearchFSM.cash, F.data == "fsm:cancel")
@router.callback_query(SearchFSM.time, F.data == "fsm:cancel")
async def cb_search_cancel(query: CallbackQuery, state: FSMContext) -> None:
    """Отменяет поиск и возвращает в главное меню."""
    await state.clear()
    await _cleanup_and_send(
        query,
        "Поиск отменён. Возвращаемся в меню 👇",
        reply_markup=main_menu_kb(),
    )
    await query.answer()


@router.callback_query(SearchFSM.time, F.data == "fsm:back")
async def cb_search_back_to_cash(query: CallbackQuery, state: FSMContext) -> None:
    """Возвращает к выбору бюджета с шага выбора времени."""
    await state.set_state(SearchFSM.cash)
    await _cleanup_and_send(
        query,
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
    """Переключает лайк на свидании и обновляет клавиатуру карточки."""
    if not query.data:
        return
    date_id = int(query.data.split(":")[1])
    service = DateService(session)
    new_is_liked = await service.toggle_like(query.from_user.id, date_id)
    logger.info("User {} toggled like for date {} -> {}", query.from_user.id, date_id, new_is_liked)

    # Редактируем клавиатуру только если сообщение доступно
    if query.message and not isinstance(query.message, InaccessibleMessage):
        await query.message.edit_reply_markup(reply_markup=date_card_kb(date_id, new_is_liked))
    await query.answer("❤️ Лайк!" if new_is_liked else "💔 Лайк убран")


@router.callback_query(F.data.startswith("visited:"))
async def cb_visited(query: CallbackQuery, session: AsyncSession) -> None:
    """Отмечает свидание как посещённое и убирает карточку."""
    if not query.data:
        return
    date_id = int(query.data.split(":")[1])
    service = DateService(session)
    await service.mark_visited(query.from_user.id, date_id)
    logger.info("User {} marked date {} as visited", query.from_user.id, date_id)

    # Удаляем карточку, если сообщение доступно
    if query.message and not isinstance(query.message, InaccessibleMessage):
        with suppress(Exception):
            await query.message.delete()
        await query.message.answer(
            "✅ <b>Отлично! Надеемся, было здорово 🎉</b>\n\nХочешь ещё одно свидание?",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
    else:
        await query.answer("✅ Отлично! Надеемся, было здорово 🎉", show_alert=True)
    await query.answer()


@router.callback_query(SearchFSM.browsing, F.data == "next")
async def cb_next(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Показывает другое свидание с теми же фильтрами."""
    data = await state.get_data()
    cash = data.get("cash")
    time = data.get("time")
    is_home = data.get("is_home")
    logger.debug(
        "User {} requested next date (cash={}, time={}, is_home={})",
        query.from_user.id,
        cash,
        time,
        is_home,
    )

    if cash is None or time is None or is_home is None:
        logger.warning("User {} lost FSM filters in browsing", query.from_user.id)
        await _cleanup_and_send(
            query,
            "Фильтры устарели. Начни поиск заново 👇",
            reply_markup=main_menu_kb(),
        )
        await query.answer()
        return

    service = DateService(session)

    try:
        date = await service.find_random(query.from_user.id, cash, time, is_home)
    except Exception:
        logger.exception("Search failed for user {}", query.from_user.id)
        raise

    if date is None:
        logger.info(
            "No more dates for user {} (cash={}, time={}, is_home={})",
            query.from_user.id,
            cash,
            time,
            is_home,
        )
        await _cleanup_and_send(
            query,
            "😔  <b>Ничего не найдено.</b>\n\nПопробуй изменить параметры поиска.",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
        await query.answer()
        return

    is_liked = await service.get_like_status(query.from_user.id, date.id)
    location_text = "🏠 Дома" if date.is_home else "🌆 Вне дома"
    cash_text = "💸" * date.cash
    caption = f"{date.description}\n\n{location_text} · {cash_text} · ⏱ {date.time} ч"

    if query.message and not isinstance(query.message, InaccessibleMessage):
        if date.photo_file_id:
            await query.message.edit_media(
                media=InputMediaPhoto(media=date.photo_file_id, caption=caption, parse_mode="HTML"),
                reply_markup=date_card_kb(date.id, is_liked),
            )
        else:
            await query.message.edit_text(
                text=caption,
                reply_markup=date_card_kb(date.id, is_liked),
                parse_mode="HTML",
            )
    else:
        if date.photo_file_id and query.message:
            await query.message.answer_photo(
                photo=date.photo_file_id,
                caption=caption,
                reply_markup=date_card_kb(date.id, is_liked),
                parse_mode="HTML",
            )
        else:
            if query.message:
                await query.message.answer(
                    caption,
                    reply_markup=date_card_kb(date.id, is_liked),
                    parse_mode="HTML",
                )
    await query.answer()
