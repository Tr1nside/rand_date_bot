from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения.

    Attributes:
        BOT_TOKEN: Токен Telegram-бота.
        DB_PATH: Путь к файлу SQLite-базы данных.
        FIRST_ADMIN_ID: Telegram ID первого администратора, создаётся при инициализации БД.
    """

    BOT_TOKEN: str
    DB_PATH: str = "bot.db"
    FIRST_ADMIN_ID: int | None = None

    model_config = {"env_file": ".env"}


settings = Settings()
