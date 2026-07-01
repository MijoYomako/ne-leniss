import logging
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from ne_leniss.config import Settings
from ne_leniss.habits import (
    encode_habits,
    parse_habits_input,
    user_habits_or_default,
)
from ne_leniss.repository import Repository

router = Router()
log = logging.getLogger("ne_leniss.onboarding")


class OnboardingStates(StatesGroup):
    intro = State()
    awaiting_habits = State()


WELCOME = (
    "Привет 👋\n\n"
    "Я Мишок 🐻 — твой напарник по привычкам. Помогу тебе видеть как ты "
    "растёшь день за днём.\n\n"
    "Каждое утро в 09:00 я буду приходить с короткой рутиной:\n"
    "☑️ Чекбоксы привычек за вчера\n"
    "🌅 Какой был вчерашний день\n"
    "📝 Планы на сегодня\n\n"
    "В любое время:\n"
    "• /note — записать заметку в журнал\n"
    "• /plan — запланировать что-то на любой день\n\n"
    "А в меню снизу — твоё приложение с календарём и стриками 🔥"
)

ASK_HABITS = (
    "Какие привычки или антипривычки хочешь трекать каждый день?\n\n"
    "Так ты будешь легче держать обещания, которые часто теряются в "
    "суете будней. Через месяц у тебя появится картина — что ты "
    "реально делаешь, а не догадки. Через два — привычка возвращаться "
    "и отмечать.\n\n"
    "Напиши их через запятую. Вдохновиться можно этим:\n\n"
    "💡 <i>Спорт, Медитация, Чтение, Английский, 8ч сна, 2л воды, "
    "Без сахара, Без алкоголя, Без курения, Без соц.сетей, "
    "Прогулка, Дневник, Йога, Бег, Без фастфуда, "
    "Работа 4ч+, Учёба 1ч, Прогресс по проекту</i>\n\n"
    "⚠️ От 3 до 8 привычек — больше на старте не работает."
)

AFTER_HABITS_HEADER = "Отличные цели! Мишок верит в тебя 🏆\n\n"


def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Окей, погнали дальше →", callback_data="onb:continue")]
        ]
    )


async def start_onboarding(message: Message, state: FSMContext) -> None:
    await state.set_state(OnboardingStates.intro)
    await message.answer(WELCOME, reply_markup=welcome_keyboard())


@router.callback_query(OnboardingStates.intro, F.data == "onb:continue")
async def on_continue(query: CallbackQuery, state: FSMContext) -> None:
    await query.message.edit_text(WELCOME)  # remove button
    await query.message.answer(ASK_HABITS, parse_mode="HTML")
    await state.set_state(OnboardingStates.awaiting_habits)
    await query.answer()


@router.message(OnboardingStates.awaiting_habits)
async def on_habits_input(
    message: Message,
    state: FSMContext,
    bot: Bot,
    repo: Repository,
    settings: Settings,
) -> None:
    if message.from_user is None or not message.text:
        return
    habits = parse_habits_input(message.text)
    if len(habits) < 3:
        await message.answer(
            "Маловато 🙃 Напиши хотя бы 3 привычки через запятую."
        )
        return
    if len(habits) > 8:
        habits = habits[:8]
        await message.answer(
            "Взял первые 8 — этого достаточно для старта. Остальные добавим позже."
        )

    user = await repo.get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await repo.set_user_habits(user.tg_id, encode_habits(habits))

    # Seed background data (days 3..30 ago), preserving last 2 days empty.
    tz = ZoneInfo(user.timezone)
    today = datetime.now(tz).date()
    moods = ["Good", "Productive", "Could be better", "Bad", "Relaxing"]
    sample_plans = [
        "зал в 19", "встреча в кафе", "позвонить родителям",
        "прочитать главу", "закончить проект", "прогулка вечером",
    ]
    sample_journal = [
        "хороший день", "много работал, устал", "новая идея для проекта",
        "погулял, расслабился", "встретился с другом",
    ]
    rng = random.Random(user.tg_id)
    # Fill days 3..9 ago (7 days), keep yesterday & day-before empty so the
    # user doesn't start with a fake streak.
    for days_back in range(3, 10):
        d = today - timedelta(days=days_back)
        entry_id = await repo.find_or_create_day_entry(user.tg_id, d)
        base = 0.45 + 0.25 * (1 - days_back / 10)
        checks = {
            k: rng.random() < base + rng.uniform(-0.15, 0.15)
            for k, _ in habits
        }
        await repo.set_habit_checks(entry_id, habits, checks)
        if rng.random() < 0.75:
            await repo.set_mood(entry_id, rng.choice(moods))
        if rng.random() < 0.35:
            await repo.append_plan(user.tg_id, d, rng.choice(sample_plans))
        if rng.random() < 0.25:
            await repo.append_journal(user.tg_id, d, rng.choice(sample_journal))

    habits_list = "\n".join(f"• {label}" for _, label in habits)
    await message.answer(
        AFTER_HABITS_HEADER
        + f"Твои привычки:\n{habits_list}\n\n"
        "Если захочешь поменять список — команда /habits.\n\n"
        "А сейчас давай попробуем сразу — заполним чекбоксы за вчерашний "
        "день, отметим какой он был и запланируем сегодня 🚀"
    )
    await state.clear()

    # Hand off to morning flow as the first run (no "доброе утро", and we'll
    # congratulate after plans are saved)
    from ne_leniss.handlers.morning import send_morning_message

    fresh_user = await repo.get_user(user.tg_id)
    if fresh_user is not None:
        await send_morning_message(fresh_user, bot, repo, state.storage, is_first_run=True)


@router.message(F.text == "/reset_onboarding")
async def cmd_reset_onboarding(
    message: Message,
    repo: Repository,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return
    await repo.wipe_user_data(message.from_user.id)
    await state.clear()
    await message.answer(
        "🔄 Полный сброс — данные привычек, планов и заметок удалены. "
        "Жми /start чтобы пройти онбординг заново."
    )
