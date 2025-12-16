from django.contrib import admin

from .models import Category, Task, UserProfile


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Настройки админки для категорий."""

    list_display = ("id", "name", "user")
    search_fields = ("name", "user__username")
    list_filter = ("user",)
    autocomplete_fields = ("user",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Настройки админки для задач."""

    list_display = ("id", "title", "user", "due_date", "is_completed", "created_at")
    list_filter = ("is_completed", "due_date", "created_at", "categories")
    search_fields = ("title", "description", "user__username")
    autocomplete_fields = ("user", "categories")
    readonly_fields = ("id", "created_at")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Настройки админки для профилей пользователей."""

    list_display = ("user", "telegram_user_id", "telegram_chat_id")
    search_fields = ("user__username", "telegram_user_id", "telegram_chat_id")



