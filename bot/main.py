import asyncio
import logging
from textwrap import shorten
from typing import List
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram_dialog import DialogManager, setup_dialogs
from aiogram_dialog.manager.protocols import StartMode
from dateutil import parser

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
TZ = ZoneInfo(settings.time_zone)


def main_menu() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру главного меню."""
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="📝 Создать задачу"), KeyboardButton(text="📋 Мои задачи")],
            [KeyboardButton(text="❌ Отмена")],
        ],
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Приветствие и показ главного меню."""
    await _ensure_registered(message)
    await message.answer(
        "Привет! Я помогу управлять задачами.\nВыберите действие:",
        reply_markup=main_menu(),
    )


@router.message(Command("newtask"))
@router.message(lambda m: m.text == "📝 Создать задачу")
async def cmd_newtask(message: Message, dialog_manager: DialogManager):
    """Запуск диалога создания задачи."""
    await _ensure_registered(message)
    await dialog_manager.start(CreateTaskSG.title, mode=StartMode.RESET_STACK)


@router.message(Command("tasks"))
@router.message(lambda m: m.text == "📋 Мои задачи")
async def cmd_tasks(message: Message):
    """Выводит список задач пользователя."""
    await _ensure_registered(message)
    try:
        tasks = await backend_api.list_tasks(message.from_user.id)
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Ошибка получения задач: {exc}", reply_markup=main_menu())
        return

    if not tasks:
        await message.answer("У вас нет задач.", reply_markup=main_menu())
        return

    lines: List[str] = []
    for idx, task in enumerate(tasks, start=1):
        cats = ", ".join(cat["name"] for cat in task.get("categories", [])) or "без категории"
        title = shorten(task["title"], width=60, placeholder="...")
        created = _format_dt(task.get("created_at"))
        due = _format_dt(task["due_date"])
        status = "✅" if task["is_completed"] else "⏳"
        lines.append(f"{idx}. {status} {title}\nКатегории: {cats}\nСоздано: {created}\nДедлайн: {due}")

    await message.answer("\n\n".join(lines), reply_markup=main_menu())


@router.message(lambda m: m.text == "❌ Отмена")
async def cmd_cancel(message: Message, dialog_manager: DialogManager):
    """Отмена текущего диалога и показ меню."""
    await dialog_manager.reset_stack()
    await message.answer("Действие отменено.", reply_markup=main_menu())


async def _ensure_registered(message: Message):
    """Гарантирует регистрацию пользователя на backend."""
    try:
        await backend_api.register_user(message.from_user.id, message.chat.id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ошибка регистрации пользователя: %s", exc)
        await message.answer("Не удалось зарегистрировать вас на сервере. Попробуйте позже.", reply_markup=main_menu())
        raise


def _format_dt(raw: str) -> str:
    """Форматирует дату/время с учётом таймзоны бота."""
    try:
        dt = parser.isoparse(raw).astimezone(TZ)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw


async def main():
    if not settings.bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


