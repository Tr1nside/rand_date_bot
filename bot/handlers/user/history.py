import math
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InaccessibleMessage, InlineKeyboardMarkup
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Date, UserHistory
from bot.keyboards.user import HISTORY_PAGE_SIZE, history_page_kb, main_menu_kb
from bot.services.date_service import DateService

router = Router(name="history")

_DESCRIPTION_MAX_LEN = 100
_CB_PAGE_PART_INDEX = 2
_HISTORY_EMPTY_TEXT = "📜 <b>История пуста.</b>\n\nВы ещё не отмечали посещённые свидания."


def _truncate(text: str, max_len: int) -> str:
    """Обрезает строку до заданной длины, добавляя многоточие при необходимости.

    Args:
        text: Исходная строка.
        max_len: Максимально допустимая длина.

    Returns:
        Строка длиной не более max_len символов.
    """
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}…"


def _format_entry(position: int, history: UserHistory, date: Date) -> str:
    """Форматирует одну запись истории для отображения в списке.

    Args:
        position: Порядковый номер в текущем списке (начиная с 1).
        history: Запись истории взаимодействия пользователя.
        date: Связанный объект свидания.

    Returns:
        Отформатированная строка в HTML-разметке.
    """
    description = _truncate(date.description, _DESCRIPTION_MAX_LEN)
    visited_at = history.dropped_at.strftime("%d.%m.%Y") if history.dropped_at else "—"
    like_mark = " ❤️" if history.is_liked else ""
    location = "🏠 Дома" if date.is_home else "🌆 Вне дома"
    cash_mark = "💸" * date.cash

    logger.debug(
        "Formatting history entry #{}: date_id={}, liked={}, visited_at={}",
        position,
        date.id,
        history.is_liked,
        visited_at,
    )

    title_line = f"<b>{position}. {description}{like_mark}</b>"
    details_line = f"{location} · {cash_mark} · ⏱ {date.time} ч"
    date_line = f"📅 {visited_at}"
    return "\n".join([title_line, details_line, date_line])


def _build_page_text(
    history_entries: list[tuple[UserHistory, Date]],
    page: int,
    total_pages: int,
    page_offset: int,
) -> str:
    """Собирает текст страницы истории из списка записей.

    Args:
        history_entries: Записи текущей страницы в виде кортежей (UserHistory, Date).
        page: Текущий номер страницы (начиная с 0).
        total_pages: Общее количество страниц.
        page_offset: Абсолютный номер первой записи на странице.

    Returns:
        Готовый HTML-текст для отправки пользователю.
    """
    logger.debug(
        "Building page text: page={}, total_pages={}, entries_count={}, offset={}",
        page,
        total_pages,
        len(history_entries),
        page_offset,
    )
    header = f"📜 <b>История свиданий</b> (стр. {page + 1}/{total_pages})\n\n"
    formatted = [
        _format_entry(page_offset + idx, history, date)
        for idx, (history, date) in enumerate(history_entries, start=1)
    ]
    return header + "\n\n".join(formatted)


async def _send_or_edit(
    query: CallbackQuery,
    text: str,
    keyboard: InlineKeyboardMarkup,
) -> None:
    """Редактирует текущее сообщение или логирует ошибку при недоступности.

    Args:
        query: Входящий callback-запрос.
        text: HTML-текст для отображения.
        keyboard: Клавиатура для прикрепления к сообщению.
    """
    if not query.message or isinstance(query.message, InaccessibleMessage):
        logger.warning(
            "Cannot edit message for user {}: message is missing or inaccessible",
            query.from_user.id,
        )
        return

    logger.debug(
        "Editing message {} for user {}",
        query.message.message_id,
        query.from_user.id,
    )

    with suppress(TelegramBadRequest):
        await query.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )


async def _show_empty_history(query: CallbackQuery, page: int, total: int) -> None:
    """Отправляет сообщение о пустой истории и завершает callback.

    Args:
        query: Входящий callback-запрос.
        page: Запрошенный номер страницы (для логирования).
        total: Общее количество записей (для логирования).
    """
    logger.info(
        "History is empty for user {} (page={}, total={})",
        query.from_user.id,
        page,
        total,
    )
    await _send_or_edit(query, _HISTORY_EMPTY_TEXT, main_menu_kb())
    await query.answer()


async def _show_history_page(
    query: CallbackQuery,
    history_entries: list[tuple[UserHistory, Date]],
    page: int,
    total: int,
) -> None:
    """Рендерит и отправляет страницу истории с пагинацией.

    Args:
        query: Входящий callback-запрос.
        history_entries: Записи текущей страницы.
        page: Текущий номер страницы (начиная с 0).
        total: Общее количество посещённых свиданий.
    """
    total_pages = math.ceil(total / HISTORY_PAGE_SIZE)
    page_offset = page * HISTORY_PAGE_SIZE + 1

    logger.debug(
        "Rendering history page {}/{} for user {} (offset={})",
        page + 1,
        total_pages,
        query.from_user.id,
        page_offset,
    )

    text = _build_page_text(history_entries, page, total_pages, page_offset)
    keyboard = history_page_kb(page, total_pages)

    await _send_or_edit(query, text, keyboard)
    await query.answer()

    logger.info(
        "History page {}/{} sent to user {}",
        page + 1,
        total_pages,
        query.from_user.id,
    )


@router.callback_query(F.data.startswith("history:page:"))
async def cb_history_page(query: CallbackQuery, session: AsyncSession) -> None:
    """Отображает страницу истории посещённых свиданий.

    Парсит номер страницы из callback_data, загружает соответствующий срез
    истории через сервис и обновляет сообщение с новым текстом и пагинацией.

    Args:
        query: Входящий callback-запрос с данными вида «history:page:{n}».
        session: Асинхронная сессия БД, пробрасываемая через DatabaseMiddleware.
    """
    logger.info(
        "cb_history_page triggered: user_id={}, callback_data={}",
        query.from_user.id,
        query.data,
    )

    if not query.data:
        logger.warning("cb_history_page: empty callback_data from user {}", query.from_user.id)
        await query.answer()
        return

    page = int(query.data.split(":")[_CB_PAGE_PART_INDEX])
    logger.info("User {} requested history page {}", query.from_user.id, page)

    service = DateService(session)
    history_entries, total = await service.get_history_page(
        query.from_user.id,
        page,
        HISTORY_PAGE_SIZE,
    )

    logger.info(
        "History loaded for user {}: total={}, entries_on_page={}",
        query.from_user.id,
        total,
        len(history_entries),
    )

    if not history_entries:
        await _show_empty_history(query, page, total)
        return

    await _show_history_page(query, history_entries, page, total)


@router.callback_query(F.data == "menu:main")
async def cb_menu_main(query: CallbackQuery) -> None:
    """Возвращает пользователя в главное меню.

    Args:
        query: Входящий callback-запрос с данными «menu:main».
    """
    logger.info("cb_menu_main triggered: user_id={}", query.from_user.id)

    if not query.message or isinstance(query.message, InaccessibleMessage):
        logger.warning(
            "Cannot return to menu for user {}: message inaccessible",
            query.from_user.id,
        )
        await query.answer()
        return

    logger.debug(
        "Editing message {} to main menu for user {}",
        query.message.message_id,
        query.from_user.id,
    )

    with suppress(TelegramBadRequest):
        await query.message.edit_text(
            "💘 <b>Главное меню</b>\n\nВыбери действие:",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )

    await query.answer()
    logger.info("User {} returned to main menu", query.from_user.id)
