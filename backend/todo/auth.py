from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework.request import Request

from .models import UserProfile

User = get_user_model()


class TelegramUserAuthentication(authentication.BaseAuthentication):
    """
    Header-based authentication for Telegram bot traffic.

    - Ожидает заголовок X-Telegram-User-Id.
    - Пытается найти профиль по telegram_user_id, чтобы не плодить пользователей.
    - Если профиля нет — создаёт/берёт пользователя с username вида tg_<id>.
    """

    header_name = "HTTP_X_TELEGRAM_USER_ID"

    def authenticate(self, request: Request) -> Optional[Tuple[User, None]]:
        raw_id = request.META.get(self.header_name)
        if not raw_id:
            return None

        try:
            normalized_id = int(raw_id)
        except (TypeError, ValueError):
            return None

        profile = UserProfile.objects.select_related("user").filter(telegram_user_id=normalized_id).first()
        if profile:
            return profile.user, None

        username = f"tg_{normalized_id}"
        user, _ = User.objects.get_or_create(username=username)
        return user, None



