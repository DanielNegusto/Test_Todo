from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework.request import Request

User = get_user_model()


class TelegramUserAuthentication(authentication.BaseAuthentication):
    """
    Simple header-based authentication for Telegram bot traffic.

    The bot must send X-Telegram-User-Id header with the Telegram user id.
    A Django user with username derived from that id is created on first use.
    """

    header_name = "HTTP_X_TELEGRAM_USER_ID"

    def authenticate(self, request: Request) -> Optional[Tuple[User, None]]:
        telegram_user_id = request.META.get(self.header_name)
        if not telegram_user_id:
            return None

        username = f"tg_{telegram_user_id}"
        user, _ = User.objects.get_or_create(username=username)
        return user, None


