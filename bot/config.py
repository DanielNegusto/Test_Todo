import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Настройки Telegram-бота и доступа к backend."""

    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    api_base_url: str = os.getenv("BACKEND_API_BASE_URL", "http://backend:8000")
    request_timeout: int = int(os.getenv("BOT_REQUEST_TIMEOUT", "15"))
    time_zone: str = os.getenv("TIME_ZONE", "America/Adak")


settings = Settings()


