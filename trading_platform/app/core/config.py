from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()