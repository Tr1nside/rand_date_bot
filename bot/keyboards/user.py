from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

HISTORY_PAGE_SIZE = 5


def main_menu_kb() -> InlineKeyboardMarkup:
    """Возвращает главное меню с кнопками поиска свидания и истории."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💘 Найти свидание", callback_data="loc:start")],
            [InlineKeyboardButton(text="📜 История", callback_data="history:page:0")],
        ]
    )


def search_location_kb() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора места проведения свидания с кнопкой отмены."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 Дома", callback_data="loc:home"),
                InlineKeyboardButton(text="🌆 Вне дома", callback_data="loc:outside"),
            ],
            [InlineKeyboardButton(text="✖ Отмена", callback_data="fsm:cancel")],
        ]
    )


def search_cash_kb() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора уровня бюджета с кнопками назад и отмены."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💸", callback_data="cash:1"),
                InlineKeyboardButton(text="💸💸", callback_data="cash:2"),
                InlineKeyboardButton(text="💸💸💸", callback_data="cash:3"),
            ],
            [
                InlineKeyboardButton(text="← Назад", callback_data="fsm:back"),
                InlineKeyboardButton(text="✖ Отмена", callback_data="fsm:cancel"),
            ],
        ]
    )


def search_time_kb() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора длительности свидания."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 ч", callback_data="time:1"),
                InlineKeyboardButton(text="2 ч", callback_data="time:2"),
                InlineKeyboardButton(text="3 ч", callback_data="time:3"),
                InlineKeyboardButton(text="4+ ч", callback_data="time:4"),
            ],
            [
                InlineKeyboardButton(text="← Назад", callback_data="fsm:back"),
                InlineKeyboardButton(text="✖ Отмена", callback_data="fsm:cancel"),
            ],
        ]
    )


def date_card_kb(date_id: int, is_liked: bool) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру карточки свидания.

    Args:
        date_id: Идентификатор свидания.
        is_liked: Текущий статус лайка пользователя.

    Returns:
        InlineKeyboardMarkup с кнопками лайка, посещения, другого и главного меню.
    """
    like_text = "💔 Убрать лайк" if is_liked else "❤️ Лайк"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=like_text, callback_data=f"like:{date_id}"),
                InlineKeyboardButton(text="✅ Сходили", callback_data=f"visited:{date_id}"),
                InlineKeyboardButton(text="🔄 Другое", callback_data="next"),
            ],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")],
        ]
    )


def history_page_kb(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру пагинации для истории посещённых свиданий.

    Кнопки «← Назад» и «Вперёд →» показываются только при наличии
    соответствующей страницы. Кнопка «🏠 Главное меню» присутствует всегда.

    Args:
        page: Текущий номер страницы (начиная с 0).
        total_pages: Общее количество страниц.

    Returns:
        InlineKeyboardMarkup с кнопками навигации по истории.
    """
    nav_row: list[InlineKeyboardButton] = []

    if page > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="← Назад",
                callback_data=f"history:page:{page - 1}",
            )
        )

    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд →",
                callback_data=f"history:page:{page + 1}",
            )
        )

    menu_row = [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")]

    inline_keyboard: list[list[InlineKeyboardButton]] = []
    if nav_row:
        inline_keyboard.append(nav_row)
    inline_keyboard.append(menu_row)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
