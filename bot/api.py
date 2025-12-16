from typing import Any, Dict, List, Optional

import httpx

from config import settings


class BackendAPI:
    """Асинхронный клиент для обращения к Django REST API."""

    def __init__(self):
        self.base_url = settings.api_base_url.rstrip("/")
        self.timeout = settings.request_timeout

    def _headers(self, telegram_user_id: int) -> Dict[str, str]:
        return {"X-Telegram-User-Id": str(telegram_user_id)}

    async def register_user(self, telegram_user_id: int, telegram_chat_id: int) -> Dict[str, Any]:
        url = f"{self.base_url}/api/telegram/register/"
        payload = {"telegram_chat_id": telegram_chat_id}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=self._headers(telegram_user_id))
            resp.raise_for_status()
            return resp.json()

    async def list_tasks(self, telegram_user_id: int) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/tasks/"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=self._headers(telegram_user_id))
            resp.raise_for_status()
            return resp.json()

    async def create_task(
        self,
        telegram_user_id: int,
        title: str,
        description: str,
        due_date_iso: str,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/tasks/"
        payload: Dict[str, Any] = {
            "title": title,
            "description": description,
            "due_date": due_date_iso,
            "category_names": categories or [],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload, headers=self._headers(telegram_user_id))
            resp.raise_for_status()
            return resp.json()


