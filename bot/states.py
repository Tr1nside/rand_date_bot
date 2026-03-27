from aiogram.fsm.state import State, StatesGroup


class SearchFSM(StatesGroup):
    is_home = State()
    cash = State()
    time = State()
    browsing = State()


class AddDateFSM(StatesGroup):
    """FSM для добавления нового свидания администратором."""

    description = State()
    cash = State()
    time = State()
    is_home = State()
    photo = State()


class AddAdminFSM(StatesGroup):
    """FSM для добавления нового администратора."""

    telegram_id = State()


class RemoveAdminFSM(StatesGroup):
    """FSM для удаления администратора."""

    telegram_id = State()
