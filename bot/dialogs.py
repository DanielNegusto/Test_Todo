from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from aiogram import types
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Row, Select
from aiogram_dialog.widgets.text import Const, Format
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from dateutil import parser

from api import BackendAPI
from config import settings

backend_api = BackendAPI()
TZ = ZoneInfo(settings.time_zone)


class CreateTaskSG(StatesGroup):
    """Состояния диалога создания задачи."""

    title = State()
    category_select = State()
    category_new = State()
    deadline_date = State()
    deadline_time = State()


# ----------------------------- helpers ----------------------------- #

async def _load_categories(dialog_manager: DialogManager, **kwargs) -> Dict[str, List[Dict[str, str]]]:
    """Возвращает категории пользователя для отображения в списке."""
    user_id = dialog_manager.event.from_user.id
    try:
        categories = await backend_api.list_categories(user_id)
    except Exception:
        categories = []
    return {"categories": categories}


def _set_date(dialog_manager: DialogManager, selected_date: date) -> None:
    dialog_manager.dialog_data["due_date_date"] = selected_date


def _set_time_and_finish(dialog_manager: DialogManager, selected_time: time) -> None:
    dialog_manager.dialog_data["due_date_time"] = selected_time


def _build_due_iso(dialog_manager: DialogManager) -> str:
    selected_date: date = dialog_manager.dialog_data.get("due_date_date")
    selected_time: time = dialog_manager.dialog_data.get("due_date_time")
    dt = datetime.combine(selected_date, selected_time, tzinfo=TZ)
    return dt.isoformat()


async def _create_task(message: Message, dialog_manager: DialogManager, categories: Optional[List[str]]):
    """Создаёт задачу через backend и закрывает диалог."""
    due_iso = _build_due_iso(dialog_manager)
    try:
        await backend_api.create_task(
            telegram_user_id=message.from_user.id,
            title=dialog_manager.dialog_data.get("title"),
            description=dialog_manager.dialog_data.get("description", ""),
            due_date_iso=due_iso,
            categories=categories,
        )
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Ошибка создания задачи: {exc}")
        await dialog_manager.done()
        return

    human_dt = parser.isoparse(due_iso).astimezone(TZ).strftime("%Y-%m-%d %H:%M %Z")
    await message.answer(f"Задача создана ✅\nДедлайн: {human_dt}", reply_markup=_main_menu_kb())
    await dialog_manager.done()


def _main_menu_kb() -> ReplyKeyboardMarkup:
    """Клавиатура главного меню (дублируется для показа после диалога)."""
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="📝 Создать задачу"), KeyboardButton(text="📋 Мои задачи")],
            [KeyboardButton(text="❌ Отмена")],
        ],
    )


# ----------------------------- handlers ----------------------------- #

async def on_title(message: Message, _: MessageInput, manager: DialogManager):
    """Сохраняет название и переходит к выбору категории."""
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Введите название задачи.")
        return
    manager.dialog_data["title"] = title
    await manager.next()


async def on_category_pick(callback: types.CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Выбор существующей категории."""
    manager.dialog_data["categories"] = [item_id]
    await callback.answer(f"Категория: {item_id}")
    await manager.switch_to(CreateTaskSG.deadline_date)


async def on_new_category(message: Message, _: MessageInput, manager: DialogManager):
    """Создаёт новую категорию и возвращается к выбору даты."""
    name = (message.text or "").strip()
    if not name:
        await message.answer("Название категории не может быть пустым.")
        return
    try:
        await backend_api.create_category(message.from_user.id, name)
    except Exception as exc:  # noqa: BLE001
        await message.answer(f"Не удалось создать категорию: {exc}")
        return

    manager.dialog_data["categories"] = [name]
    await manager.next()


async def on_skip_categories(callback: types.CallbackQuery, _: Button, manager: DialogManager):
    """Пропускает выбор категорий."""
    manager.dialog_data["categories"] = []
    await callback.answer("Без категории")
    await manager.switch_to(CreateTaskSG.deadline_date)


async def on_date_today(callback: types.CallbackQuery, _: Button, manager: DialogManager):
    """Устанавливает дедлайн на сегодня."""
    _set_date(manager, datetime.now(TZ).date())
    await callback.answer("Дата: сегодня")
    await manager.next()


async def on_date_tomorrow(callback: types.CallbackQuery, _: Button, manager: DialogManager):
    """Устанавливает дедлайн на завтра."""
    _set_date(manager, (datetime.now(TZ) + timedelta(days=1)).date())
    await callback.answer("Дата: завтра")
    await manager.next()


async def on_date_custom(message: Message, _: TextInput, manager: DialogManager, value: str):
    """Парсит произвольную дату."""
    try:
        parsed = parser.parse(value).date()
    except Exception:  # noqa: BLE001
        await message.answer("Не удалось разобрать дату. Пример: 2025-12-31")
        return
    _set_date(manager, parsed)
    await manager.next()


async def on_back_to_categories(callback: types.CallbackQuery, _: Button, manager: DialogManager):
    """Возврат к выбору категорий из других шагов."""
    await manager.switch_to(CreateTaskSG.category_select)
    await callback.answer()


async def on_back_to_title(callback: types.CallbackQuery, _: Button, manager: DialogManager):
    """Возврат к вводу названия задачи из окна выбора категорий."""
    await manager.switch_to(CreateTaskSG.title)
    await callback.answer()


async def on_back_to_date(callback: types.CallbackQuery, _: Button, manager: DialogManager):
    """Возврат к выбору даты."""
    await manager.switch_to(CreateTaskSG.deadline_date)
    await callback.answer()


async def on_time_preset(callback: types.CallbackQuery, _: Button, manager: DialogManager, time_str: str):
    """Выбирает готовое время и создаёт задачу."""
    hours, minutes = map(int, time_str.split(":"))
    _set_time_and_finish(manager, time(hour=hours, minute=minutes))
    categories = manager.dialog_data.get("categories", [])
    await callback.answer(f"Время: {time_str}")
    await _create_task(callback.message, manager, categories)


async def on_time_custom(message: Message, _: TextInput, manager: DialogManager, value: str):
    """Парсит произвольное время и создаёт задачу."""
    try:
        dt = parser.parse(value)
        if dt.tzinfo:
            dt = dt.astimezone(TZ)
        parsed_time = dt.time()
    except Exception:  # noqa: BLE001
        await message.answer("Не удалось разобрать время. Пример: 18:30")
        return
    _set_time_and_finish(manager, parsed_time)
    categories = manager.dialog_data.get("categories", [])
    await _create_task(message, manager, categories)


# ----------------------------- dialog ----------------------------- #

create_task_dialog = Dialog(
    Window(
        Const("📝 Введите название задачи:"),
        MessageInput(on_title),
        Cancel(Const("❌ Отмена")),
        state=CreateTaskSG.title,
    ),
    Window(
        Const("📁 Выберите категорию или создайте новую:"),
        Select(
            Format("📂 {item[name]}"),
            id="cat_select",
            item_id_getter=lambda item: item["name"],
            items="categories",
            on_click=on_category_pick,
        ),
        Row(
            Button(Const("➕ Новая категория"), id="cat_new", on_click=lambda c, b, m: m.next()),
            Button(Const("Пропустить"), id="cat_skip", on_click=on_skip_categories),
        ),
        Row(
            Button(Const("⬅️ Назад"), id="back_categories", on_click=on_back_to_title),
            Cancel(Const("❌ Отмена")),
        ),
        getter=_load_categories,
        state=CreateTaskSG.category_select,
    ),
    Window(
        Const("Введите название новой категории:"),
        MessageInput(on_new_category),
        Row(
            Button(Const("⬅️ Назад"), id="back_from_new_category", on_click=on_back_to_categories),
            Cancel(Const("❌ Отмена")),
        ),
        state=CreateTaskSG.category_new,
    ),
    Window(
        Const("⏰ Выберите дату дедлайна:"),
        Row(
            Button(Const("Сегодня"), id="date_today", on_click=on_date_today),
            Button(Const("Завтра"), id="date_tomorrow", on_click=on_date_tomorrow),
        ),
        TextInput(
            id="date_custom",
            type_factory=str,
            on_success=on_date_custom,
            prompt=Const("Или введите дату (например 2025-12-31):"),
        ),
        Row(
            Button(Const("⬅️ Назад"), id="back_to_categories", on_click=on_back_to_categories),
            Cancel(Const("❌ Отмена")),
        ),
        state=CreateTaskSG.deadline_date,
    ),
    Window(
        Const("⏰ Выберите время дедлайна:"),
        Row(
            Button(Const("09:00"), id="time_0900", on_click=lambda c, b, m: on_time_preset(c, b, m, "09:00")),
            Button(Const("12:00"), id="time_1200", on_click=lambda c, b, m: on_time_preset(c, b, m, "12:00")),
            Button(Const("18:00"), id="time_1800", on_click=lambda c, b, m: on_time_preset(c, b, m, "18:00")),
        ),
        Row(
            Button(Const("21:00"), id="time_2100", on_click=lambda c, b, m: on_time_preset(c, b, m, "21:00")),
        ),
        TextInput(
            id="time_custom",
            type_factory=str,
            on_success=on_time_custom,
            prompt=Const("Введите время, например 18:30 или 18:30+03:00:"),
        ),
        Row(
            Button(Const("⬅️ Назад"), id="back_to_date", on_click=on_back_to_date),
            Cancel(Const("❌ Отмена")),
        ),
        state=CreateTaskSG.deadline_time,
    ),
)
