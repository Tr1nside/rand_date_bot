from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_fsm_nav_kb(show_back: bool = True) -> InlineKeyboardMarkup:
    """Возвращает навигационную клавиатуру для FSM-шагов администратора.

    Args:
        show_back: Если True — показывает кнопку «← Назад».

    Returns:
        InlineKeyboardMarkup с кнопками навигации.
    """
    row = []
    if show_back:
        row.append(InlineKeyboardButton(text="← Назад", callback_data="fsm:back"))
    row.append(InlineKeyboardButton(text="✖ Отмена", callback_data="fsm:cancel"))
    return InlineKeyboardMarkup(inline_keyboard=[row])


def admin_cash_kb() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора уровня затрат при добавлении свидания."""
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


def admin_time_kb() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора длительности при добавлении свидания."""
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


def admin_location_kb() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора места при добавлении свидания."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 Дома", callback_data="loc:home"),
                InlineKeyboardButton(text="🌆 Вне дома", callback_data="loc:outside"),
            ],
            [
                InlineKeyboardButton(text="← Назад", callback_data="fsm:back"),
                InlineKeyboardButton(text="✖ Отмена", callback_data="fsm:cancel"),
            ],
        ]
    )
