import hashlib

from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.name


class Task(models.Model):
    """
    Task with a deterministic custom primary key.

    The primary key is a short SHA256-based string derived from:
    - user id
    - title
    - due_date (ISO format)
    - created_at timestamp (seconds)
    """

    id = models.CharField(primary_key=True, max_length=32, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(editable=False)
    due_date = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    categories = models.ManyToManyField(Category, related_name="tasks", blank=True)
    notification_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.user})"

    def _build_pk_source(self) -> str:
        created_ts = int(self.created_at.timestamp())
        return f"{self.user_id}:{self.title}:{self.due_date.isoformat()}:{created_ts}"

    def save(self, *args, **kwargs) -> None:
        if not self.created_at:
            self.created_at = timezone.now()
        if not self.id:
            source = self._build_pk_source()
            digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
            self.id = digest[:32]
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    telegram_user_id = models.BigIntegerField(unique=True, null=True, blank=True)
    telegram_chat_id = models.BigIntegerField(unique=True, null=True, blank=True)

    def __str__(self) -> str:
        return f"Profile for {self.user}"


