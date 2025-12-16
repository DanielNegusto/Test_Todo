from typing import List

from django.utils import timezone
from rest_framework import serializers

from .models import Category, Task, UserProfile


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор категорий, привязанных к пользователю."""

    class Meta:
        model = Category
        fields = ["id", "name"]

    def create(self, validated_data: dict) -> Category:
        user = self.context["request"].user
        return Category.objects.create(user=user, **validated_data)

    def validate_name(self, value: str) -> str:
        user = self.context["request"].user
        if Category.objects.filter(user=user, name=value).exists():
            raise serializers.ValidationError("Категория с таким именем уже существует.")
        return value


class TaskSerializer(serializers.ModelSerializer):
    """Сериализатор задач с поддержкой назначения категорий по именам."""

    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        required=False,
        queryset=Category.objects.all(),
        help_text="Список идентификаторов категорий пользователя",
    )
    category_names = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        write_only=True,
        help_text="Названия категорий; будут созданы при отсутствии",
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "due_date",
            "is_completed",
            "notification_sent",
            "categories",
            "category_ids",
            "category_names",
        ]
        read_only_fields = ["id", "created_at", "notification_sent"]

    def _get_or_create_categories(self, names: List[str]) -> List[Category]:
        user = self.context["request"].user
        created = []
        for name in names:
            category, _ = Category.objects.get_or_create(user=user, name=name.strip())
            created.append(category)
        return created

    def validate_category_ids(self, categories: List[Category]) -> List[Category]:
        user = self.context["request"].user
        for category in categories:
            if category.user_id != user.id:
                raise serializers.ValidationError("Категории должны принадлежать пользователю.")
        return categories

    def validate_due_date(self, value):
        instance = getattr(self, "instance", None)
        if instance and value == instance.due_date:
            return value
        if value <= timezone.now():
            raise serializers.ValidationError("due_date должен быть в будущем.")
        return value

    def create(self, validated_data: dict) -> Task:
        user = self.context["request"].user
        category_ids = validated_data.pop("category_ids", [])
        category_names = validated_data.pop("category_names", [])

        task = Task.objects.create(user=user, **validated_data)

        categories = list(category_ids)
        if category_names:
            categories.extend(self._get_or_create_categories(category_names))

        if categories:
            task.categories.set(categories)
        return task

    def update(self, instance: Task, validated_data: dict) -> Task:
        category_ids = validated_data.pop("category_ids", None)
        category_names = validated_data.pop("category_names", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        categories_to_set = []
        if category_ids is not None:
            categories_to_set.extend(category_ids)
        if category_names is not None:
            categories_to_set.extend(self._get_or_create_categories(category_names))

        if categories_to_set:
            self.validate_category_ids(categories_to_set)
            instance.categories.set(categories_to_set)
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор профиля Telegram <-> Django."""

    class Meta:
        model = UserProfile
        fields = ["telegram_user_id", "telegram_chat_id"]


