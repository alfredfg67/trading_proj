from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # ... existing fields ...
    DATABASE_URL: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: Optional[str] = None

    # --- NEW JWT Settings ---
    JWT_SECRET_KEY: str = "your-secret-key-here"   # override in .env
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 10   # max requests per minute per IP
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()