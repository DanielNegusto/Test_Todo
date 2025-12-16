import asyncio
import logging
from textwrap import shorten
from typing import List

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram_dialog import DialogManager, setup_dialogs

from api import BackendAPI
from config import settings
from dialogs import CreateTaskSG, create_task_dialog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
router = Router()
dp.include_router(router)
router.include_router(create_task_dialog)

backend_api = BackendAPI()
setup_dialogs(dp)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Приветствие и регистрация пользователя."""
    await _ensure_registered(message)
    await message.answer(
        "Привет! Я помогу управлять задачами.\n"
        "- /newtask — создать задачу\n"
        "- /tasks — показать список задач"
    )


@router.message(Command("newtask"))
async def cmd_newtask(message: Message, dialog_manager: DialogManager):
    """Запуск диалога создания задачи."""
    await _ensure_registered(message)
    await dialog_manager.start(CreateTaskSG.title)


@router.message(Command("tasks"))
async def cmd_tasks(message: Message):
    """Выводит список задач пользователя."""
    await _ensure_registered(message)
    try:
        tasks = await backend_api.list_tasks(message.from_user.id)
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Ошибка получения задач: {exc}")
        return

    if not tasks:
        await message.answer("У вас нет задач.")
        return

    lines: List[str] = []
    for task in tasks:
        cats = ", ".join(cat["name"] for cat in task.get("categories", [])) or "без категории"
        title = shorten(task["title"], width=50, placeholder="...")
        due = task["due_date"]
        status = "✅" if task["is_completed"] else "⏳"
        lines.append(f"{status} {title}\nКатегории: {cats}\nДедлайн: {due}\n---")

    await message.answer("\n".join(lines))


async def _ensure_registered(message: Message):
    """Гарантирует регистрацию пользователя на backend."""
    try:
        await backend_api.register_user(message.from_user.id, message.chat.id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка регистрации пользователя: %s", exc)
        await message.answer("Не удалось зарегистрировать вас на сервере. Попробуйте позже.")
        raise


async def main():
    if not settings.bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


