from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из .env файла.

    Attributes:
        BOT_TOKEN: Токен Telegram-бота.
        FIRST_ADMIN_ID: Telegram ID первого администратора.
        DB_PATH: Путь к файлу базы данных SQLite.
        TELEGRAM_PROXY: URL прокси-сервера, например socks5://user:pass@host:port.
    """

    BOT_TOKEN: str
    FIRST_ADMIN_ID: int | None = None
    DB_PATH: str = "bot.db"
    TELEGRAM_PROXY: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()  # type: ignore
