from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # --- Telegram ---
    BOT_TOKEN: SecretStr

    # --- Database ---
    DB_PATH: str = "bot.db"

    # --- First admin (bootstrapping) ---
    # Telegram user_id первого администратора.
    # Используется в init_db(): если в таблице users нет ни одного админа —
    # создаётся запись с этим id и is_admin=True.
    FIRST_ADMIN_ID: int

    @property
    def db_url(self) -> str:
        """Асинхронный DSN для SQLAlchemy."""
        return f"sqlite+aiosqlite:///{self.DB_PATH}"


settings = Settings()
