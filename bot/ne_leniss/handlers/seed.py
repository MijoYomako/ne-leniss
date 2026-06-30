import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.types import Message

from ne_leniss.habits import HABIT_KEYS, MOOD_KEY_TO_NAME
from ne_leniss.repository import Repository

router = Router()


@router.message(F.text == "/seed")
async def cmd_seed(message: Message, repo: Repository) -> None:
    if message.from_user is None:
        return
    user = await repo.get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    tz = ZoneInfo(user.timezone)
    today = datetime.now(tz).date()

    rng = random.Random(user.tg_id)
    moods = list(MOOD_KEY_TO_NAME.values())
    days_count = 30

    sample_plans = [
        "зал в 19",
        "встреча в кафе",
        "позвонить родителям",
        "прочитать главу",
        "закончить проект",
    ]
    sample_journal = [
        "хороший день",
        "много работал, устал",
        "новая идея для проекта",
        "погулял, расслабился",
        "посмотрел фильм с друзьями",
    ]

    for days_back in range(1, days_count + 1):
        d = today - timedelta(days=days_back)
        entry_id = await repo.find_or_create_day_entry(user.tg_id, d)
        # newer days more likely checked; older — less
        base_prob = 0.35 + 0.45 * (1 - days_back / days_count)
        checks = {
            key: rng.random() < (base_prob + rng.uniform(-0.15, 0.15))
            for key in HABIT_KEYS
        }
        await repo.set_habit_checks(entry_id, checks)
        if rng.random() < 0.75:
            await repo.set_mood(entry_id, rng.choice(moods))
        if rng.random() < 0.4:
            await repo.append_plan(user.tg_id, d, rng.choice(sample_plans))
        if rng.random() < 0.3:
            await repo.append_journal(user.tg_id, d, rng.choice(sample_journal))

    await message.answer(
        f"✓ заполнил {days_count} дней задним числом для примера.\n"
        "Сегодняшний день не трогал — заполняй сам через /trigger_morning или жди утра."
    )
