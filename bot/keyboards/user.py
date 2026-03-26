from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    """Возвращает главное меню с кнопкой поиска свидания."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💘 Найти свидание", callback_data="loc:start")]
        ]
    )


def search_location_kb() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора места проведения свидания."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 Дома", callback_data="loc:home"),
                InlineKeyboardButton(text="🌆 Вне дома", callback_data="loc:outside"),
            ]
        ]
    )


def search_cash_kb() -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора уровня бюджета."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💸", callback_data="cash:1"),
                InlineKeyboardButton(text="💸💸", callback_data="cash:2"),
                InlineKeyboardButton(text="💸💸💸", callback_data="cash:3"),
            ],
            [InlineKeyboardButton(text="✖ Отмена", callback_data="fsm:cancel")],
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
        InlineKeyboardMarkup с кнопками лайка, посещения и поиска другого.
    """
    like_text = "💔 Убрать лайк" if is_liked else "❤️ Лайк"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=like_text, callback_data=f"like:{date_id}"),
                InlineKeyboardButton(
                    text="✅ Сходили", callback_data=f"visited:{date_id}"
                ),
                InlineKeyboardButton(text="🔄 Другое", callback_data="next"),
            ]
        ]
    )
