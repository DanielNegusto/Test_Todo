from datetime import datetime
from typing import List

from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const, Format
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from .api import BackendAPI

DATE_FORMAT = "%Y-%m-%d %H:%M"
backend_api = BackendAPI()


class CreateTaskSG(StatesGroup):
    """Состояния диалога создания задачи."""

    title = State()
    description = State()
    due_date = State()
    categories = State()


async def start_title(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(CreateTaskSG.title)


async def process_title(message: Message, message_input: MessageInput, manager: DialogManager):
    manager.dialog_data["title"] = message.text.strip()
    await manager.next()


async def process_description(message: Message, message_input: MessageInput, manager: DialogManager):
    manager.dialog_data["description"] = message.text.strip() if message.text else ""
    await manager.next()


async def process_due_date(message: Message, message_input: MessageInput, manager: DialogManager):
    try:
        parsed = datetime.strptime(message.text.strip(), DATE_FORMAT)
    except ValueError:
        await message.answer(f"Некорректный формат даты. Используйте: {DATE_FORMAT}")
        return
    manager.dialog_data["due_date"] = parsed.isoformat()
    await manager.next()


async def process_categories(message: Message, message_input: MessageInput, manager: DialogManager):
    categories_raw = message.text or ""
    category_names: List[str] = [c.strip() for c in categories_raw.split(",") if c.strip()]
    dialog_data = manager.dialog_data

    try:
        await backend_api.create_task(
            telegram_user_id=message.from_user.id,
            title=dialog_data.get("title"),
            description=dialog_data.get("description", ""),
            due_date_iso=dialog_data.get("due_date"),
            categories=category_names,
        )
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Ошибка создания задачи: {exc}")
        await manager.done()
        return

    await message.answer("Задача создана ✅")
    await manager.done()


create_task_dialog = Dialog(
    Window(
        Const("Введите название задачи:"),
        MessageInput(process_title),
        state=CreateTaskSG.title,
    ),
    Window(
        Const("Введите описание (можно пропустить, отправив пустое сообщение):"),
        MessageInput(process_description),
        state=CreateTaskSG.description,
    ),
    Window(
        Const(f"Введите дедлайн в формате {DATE_FORMAT} (время в часовом поясе сервера):"),
        MessageInput(process_due_date),
        state=CreateTaskSG.due_date,
    ),
    Window(
        Const("Перечислите категории через запятую (можно оставить пустым):"),
        MessageInput(process_categories),
        Cancel(Const("Отмена")),
        state=CreateTaskSG.categories,
    ),
)


