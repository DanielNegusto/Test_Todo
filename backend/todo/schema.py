from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme


class TelegramUserAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    Описывает заголовок X-Telegram-User-Id для схемы OpenAPI.

    Это не классическая Bearer-аутентификация, но в документации
    отображается как отдельная схема безопасности.
    """

    target_class = "todo.auth.TelegramUserAuthentication"
    name = "TelegramUserAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-Telegram-User-Id",
            "description": "Идентификатор Telegram-пользователя, используемый ботом.",
        }


