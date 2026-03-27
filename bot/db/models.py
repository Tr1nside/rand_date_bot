from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class Date(Base):
    """Модель свидания.

    Attributes:
        id: Первичный ключ.
        description: Текстовое описание свидания.
        cash: Уровень затрат от 1 до 3.
        time: Длительность в часах.
        is_home: True — дома, False — вне дома.
        photo_file_id: Telegram file_id фотографии.
    """

    __tablename__ = "dates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String)
    cash: Mapped[int] = mapped_column(Integer)
    time: Mapped[int] = mapped_column(Integer)
    is_home: Mapped[bool] = mapped_column(Boolean)
    photo_file_id: Mapped[str] = mapped_column(String)


class User(Base):
    """Модель пользователя Telegram.

    Attributes:
        id: Telegram user_id, является первичным ключом.
        username: Telegram-юзернейм, может отсутствовать.
        registered_at: Дата и время первой регистрации.
        is_admin: Признак наличия прав администратора.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class UserHistory(Base):
    """Модель истории взаимодействий пользователя со свиданиями.

    Хранит лайки и отметки о посещении. Пара (user_id, date_id) уникальна.

    Attributes:
        id: Первичный ключ.
        user_id: FK на пользователя.
        date_id: FK на свидание.
        is_liked: True если пользователь поставил лайк.
        dropped_at: Дата и время отметки «сходили»; None — ещё не посещено.
    """

    __tablename__ = "user_history"
    __table_args__ = (UniqueConstraint("user_id", "date_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date_id: Mapped[int] = mapped_column(ForeignKey("dates.id"))
    is_liked: Mapped[bool] = mapped_column(Boolean, default=False)
    dropped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
