from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from ne_leniss.habits import MOOD_KEY_TO_NAME, MOOD_OPTIONS, user_habits_or_default
from ne_leniss.models import User
from ne_leniss.repository import Repository

router = Router()


class MorningStates(StatesGroup):
    awaiting_checkboxes = State()
    awaiting_mood = State()
    awaiting_plans = State()


def build_checkbox_keyboard(
    habits: list[tuple[str, str]],
    checkboxes: dict[str, bool],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(habits), 2):
        row = []
        for key, label in habits[i : i + 2]:
            icon = "☑" if checkboxes.get(key, False) else "☐"
            row.append(
                InlineKeyboardButton(
                    text=f"{icon} {label}",
                    callback_data=f"chk:{key}",
                )
            )
        rows.append(row)
    rows.append([InlineKeyboardButton(text="✅ Готово", callback_data="chk:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_mood_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"mood:{key}")]
            for key, label in MOOD_OPTIONS
        ]
    )


async def send_morning_message(
    user: User,
    bot: Bot,
    repo: Repository,
    storage: BaseStorage,
) -> None:
    tz = ZoneInfo(user.timezone)
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)
    await repo.find_or_create_day_entry(user.tg_id, today)
    await repo.find_or_create_day_entry(user.tg_id, yesterday)

    habits = user_habits_or_default(user.habits_json)
    initial = {key: False for key, _ in habits}
    state_key = StorageKey(bot_id=bot.id, chat_id=user.tg_id, user_id=user.tg_id)
    state = FSMContext(storage=storage, key=state_key)
    await state.set_state(MorningStates.awaiting_checkboxes)
    await state.update_data(checkboxes=initial, habit_keys=[k for k, _ in habits])

    await bot.send_message(
        chat_id=user.tg_id,
        text="Доброе утро 🌅\n\nЧекни вчерашний день:",
        reply_markup=build_checkbox_keyboard(habits, initial),
    )


@router.callback_query(MorningStates.awaiting_checkboxes, F.data.startswith("chk:"))
async def on_checkbox_callback(
    query: CallbackQuery,
    state: FSMContext,
    repo: Repository,
) -> None:
    assert query.data is not None
    action = query.data.split(":", 1)[1]
    data = await state.get_data()
    checkboxes: dict[str, bool] = data.get("checkboxes", {})

    if query.from_user is None:
        await query.answer()
        return
    user = await repo.get_user(query.from_user.id)
    if user is None:
        await query.answer()
        return
    habits = user_habits_or_default(user.habits_json)

    if action == "done":
        tz = ZoneInfo(user.timezone)
        yesterday = (datetime.now(tz) - timedelta(days=1)).date()
        entry_id = await repo.find_or_create_day_entry(user.tg_id, yesterday)
        await repo.set_habit_checks(entry_id, checkboxes)
        await query.message.edit_text("Чекбоксы за вчера сохранены ✓")
        await query.message.answer(
            "Каким был вчерашний день?",
            reply_markup=build_mood_keyboard(),
        )
        await state.set_state(MorningStates.awaiting_mood)
        await query.answer()
        return

    if action not in checkboxes:
        await query.answer()
        return
    checkboxes[action] = not checkboxes[action]
    await state.update_data(checkboxes=checkboxes)
    await query.message.edit_reply_markup(reply_markup=build_checkbox_keyboard(habits, checkboxes))
    await query.answer()


@router.callback_query(MorningStates.awaiting_mood, F.data.startswith("mood:"))
async def on_mood_callback(
    query: CallbackQuery,
    state: FSMContext,
    repo: Repository,
) -> None:
    assert query.data is not None
    key = query.data.split(":", 1)[1]
    if key not in MOOD_KEY_TO_NAME or query.from_user is None:
        await query.answer()
        return
    user = await repo.get_user(query.from_user.id)
    if user is None:
        await query.answer()
        return
    tz = ZoneInfo(user.timezone)
    yesterday = (datetime.now(tz) - timedelta(days=1)).date()
    yesterday_id = await repo.find_or_create_day_entry(user.tg_id, yesterday)
    mood_name = MOOD_KEY_TO_NAME[key]
    label = next(l for k, l in MOOD_OPTIONS if k == key)
    await repo.set_mood(yesterday_id, mood_name)
    await query.message.edit_text(f"Вчера: {label} ✓")

    today = datetime.now(tz).date()
    await repo.find_or_create_day_entry(user.tg_id, today)
    existing = await repo.read_plans_text(user.tg_id, today)
    if existing:
        prompt = (
            "Уже запланировано на сегодня:\n\n"
            f"{existing}\n\n"
            "Что добавить? Пиши текстом — или жми «Пропустить»."
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⏭ Пропустить", callback_data="plans:skip")]]
        )
        await query.message.answer(prompt, reply_markup=kb)
    else:
        await query.message.answer(
            "Какие планы на сегодня? Пиши свободным текстом или строками."
        )
    await state.set_state(MorningStates.awaiting_plans)
    await query.answer()


@router.callback_query(MorningStates.awaiting_plans, F.data == "plans:skip")
async def on_plans_skip(query: CallbackQuery, state: FSMContext) -> None:
    await query.message.edit_text("День начался ✓")
    await state.clear()
    await query.answer()


@router.message(MorningStates.awaiting_plans)
async def on_plans_text(message: Message, state: FSMContext, repo: Repository) -> None:
    if message.from_user is None:
        return
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return
    user = await repo.get_user(message.from_user.id)
    if user is None:
        return
    today = datetime.now(ZoneInfo(user.timezone)).date()
    await repo.append_plan(user.tg_id, today, text)
    await message.answer("Сохранил. День начался ✓")
    await state.clear()


@router.message(F.text == "/trigger_morning")
async def cmd_trigger_morning(
    message: Message,
    bot: Bot,
    repo: Repository,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return
    user = await repo.get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await send_morning_message(user, bot, repo, state.storage)
