import logging
from typing import List

import httpx
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Task

logger = logging.getLogger(__name__)


@shared_task
def send_task_due_notifications() -> int:
    """
    Проверяет задачи с наступившим дедлайном и отправляет уведомления в Telegram.

    Возвращает количество обработанных задач.
    """

    now = timezone.now()
    tasks: List[Task] = (
        Task.objects.filter(is_completed=False, notification_sent=False, due_date__lte=now)
        .select_related("user", "user__profile")
        .prefetch_related("categories")
    )

    sent = 0
    for task in tasks:
        profile = getattr(task.user, "profile", None)
        if not profile or not profile.telegram_chat_id:
            continue

        message = _format_message(task)
        if _send_telegram_message(profile.telegram_chat_id, message):
            task.notification_sent = True
            task.save(update_fields=["notification_sent"])
            sent += 1
    return sent


def _format_message(task: Task) -> str:
    """Формирует текст уведомления о задаче."""
    tz = timezone.get_current_timezone()
    due_local = task.due_date.astimezone(tz).strftime("%Y-%m-%d %H:%M")
    categories = ", ".join(task.categories.values_list("name", flat=True)) or "без категории"
    return f"⏰ Дедлайн задачи\nНазвание: {task.title}\nКатегории: {categories}\nДедлайн: {due_local}"


def _send_telegram_message(chat_id: int, text: str) -> bool:
    """Отправляет сообщение через Telegram Bot API."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN не задан, уведомление не отправлено")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=payload)
            if response.status_code == 200:
                return True
            logger.error("Не удалось отправить сообщение в Telegram: %s", response.text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка отправки Telegram сообщения: %s", exc)
    return False


