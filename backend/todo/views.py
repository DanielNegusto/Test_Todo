from typing import Any, Dict

from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Task, UserProfile
from .serializers import CategorySerializer, TaskSerializer, UserProfileSerializer


@extend_schema_view(
    list=extend_schema(
        summary="Список категорий",
        description="Возвращает список категорий, принадлежащих текущему пользователю.",
    ),
    create=extend_schema(
        summary="Создать категорию",
        description="Создаёт новую категорию для текущего пользователя.",
    ),
    retrieve=extend_schema(
        summary="Получить категорию",
        description="Возвращает категорию по идентификатору, если она принадлежит текущему пользователю.",
    ),
    update=extend_schema(
        summary="Обновить категорию",
        description="Полностью обновляет категорию текущего пользователя.",
    ),
    partial_update=extend_schema(
        summary="Частично обновить категорию",
        description="Частично обновляет категорию текущего пользователя.",
    ),
    destroy=extend_schema(
        summary="Удалить категорию",
        description="Удаляет категорию текущего пользователя.",
        responses={204: OpenApiResponse(description="Категория удалена")},
    ),
)
class CategoryViewSet(viewsets.ModelViewSet):
    """CRUD для категорий текущего пользователя."""

    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Возвращает queryset категорий, отфильтрованных по текущему пользователю."""
        return Category.objects.filter(user=self.request.user).order_by("name")


@extend_schema_view(
    list=extend_schema(
        summary="Список задач",
        description="Возвращает список задач, принадлежащих текущему пользователю.",
    ),
    create=extend_schema(
        summary="Создать задачу",
        description="Создаёт новую задачу для текущего пользователя с указанием дедлайна и категорий.",
    ),
    retrieve=extend_schema(
        summary="Получить задачу",
        description="Возвращает задачу по идентификатору, если она принадлежит текущему пользователю.",
    ),
    update=extend_schema(
        summary="Обновить задачу",
        description="Полностью обновляет задачу текущего пользователя.",
    ),
    partial_update=extend_schema(
        summary="Частично обновить задачу",
        description="Частично обновляет задачу текущего пользователя.",
    ),
    destroy=extend_schema(
        summary="Удалить задачу",
        description="Удаляет задачу текущего пользователя.",
        responses={204: OpenApiResponse(description="Задача удалена")},
    ),
)
class TaskViewSet(viewsets.ModelViewSet):
    """CRUD для задач текущего пользователя."""

    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Возвращает queryset задач текущего пользователя с оптимизированными связями."""
        return (
            Task.objects.filter(user=self.request.user)
            .select_related("user")
            .prefetch_related("categories")
            .order_by("-created_at")
        )


class TelegramRegisterView(APIView):
    """
    Регистрирует или обновляет связь Telegram-пользователя с Django-пользователем.

    Ожидает заголовок X-Telegram-User-Id для аутентификации (см. custom auth).
    Тело запроса:
    - telegram_chat_id (обязательно)
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Регистрация Telegram-пользователя",
        description=(
            "Создаёт или обновляет профиль пользователя, связывая его с Telegram user id и chat id.\n\n"
            "Используется Telegram-ботом для последующей отправки уведомлений."
        ),
        request=UserProfileSerializer,
        responses={200: UserProfileSerializer},
    )
    def post(self, request, *args, **kwargs):
        telegram_chat_id = request.data.get("telegram_chat_id")
        if not telegram_chat_id:
            return Response({"detail": "telegram_chat_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        profile = UserProfile.objects.filter(user=request.user).first()
        telegram_user_id = profile.telegram_user_id if profile else None
        if not telegram_user_id:
            telegram_user_id = request.META.get("HTTP_X_TELEGRAM_USER_ID")
        if not telegram_user_id:
            return Response({"detail": "Не найден Telegram user id"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            profile, _ = UserProfile.objects.select_for_update().get_or_create(user=request.user)
            profile.telegram_user_id = int(telegram_user_id)
            profile.telegram_chat_id = int(telegram_chat_id)
            profile.save()

        serializer = UserProfileSerializer(profile)
        payload: Dict[str, Any] = {
            "user_id": request.user.id,
            "username": request.user.username,
            "profile": serializer.data,
        }
        return Response(payload, status=status.HTTP_200_OK)


