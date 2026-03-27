from pathlib import Path

from loguru import logger
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


LOG_PATH = Path(__file__).parent.parent / "logs" / "recent.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
LOG_PATH.touch()

logger.add(
    LOG_PATH,
    level=5,
    rotation="500 MB",
    retention="1 week",
    compression="zip",
    enqueue=True,
)


settings = Settings()  # type: ignore
