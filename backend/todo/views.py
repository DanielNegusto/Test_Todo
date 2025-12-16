from typing import Any, Dict

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Task, UserProfile
from .serializers import CategorySerializer, TaskSerializer, UserProfileSerializer

User = get_user_model()


class CategoryViewSet(viewsets.ModelViewSet):
    """CRUD для категорий текущего пользователя."""

    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).order_by("name")


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD для задач текущего пользователя."""

    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Task.objects.filter(user=self.request.user)
            .select_related("user")
            .prefetch_related("categories")
            .order_by("-created_at")
        )

    def perform_create(self, serializer: TaskSerializer):
        serializer.save(user=self.request.user)


class TelegramRegisterView(APIView):
    """
    Регистрирует или обновляет связь Telegram-пользователя с Django-пользователем.

    Ожидает заголовок X-Telegram-User-Id для аутентификации (см. custom auth).
    Тело запроса:
    - telegram_chat_id (обязательно)
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        telegram_chat_id = request.data.get("telegram_chat_id")
        if not telegram_chat_id:
            return Response({"detail": "telegram_chat_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        telegram_user_id = getattr(request.user.profile, "telegram_user_id", None) or request.META.get(
            "HTTP_X_TELEGRAM_USER_ID"
        )
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


