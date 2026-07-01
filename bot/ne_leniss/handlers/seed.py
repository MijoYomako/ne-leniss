import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.types import Message

from ne_leniss.habits import MOOD_KEY_TO_NAME, user_habits_or_default
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
    habits = user_habits_or_default(user.habits_json)
    tz = ZoneInfo(user.timezone)
    today = datetime.now(tz).date()
    moods = list(MOOD_KEY_TO_NAME.values())

    rng = random.Random(user.tg_id + 17)
    sample_plans = [
        "зал в 19", "встреча в кафе", "позвонить родителям",
        "прочитать главу", "закончить проект", "прогулка вечером",
    ]
    sample_journal = [
        "хороший день", "много работал, устал", "новая идея для проекта",
        "погулял, расслабился", "встретился с другом",
    ]

    days_count = 7
    skip_recent = 2  # leave yesterday + day-before empty

    # Deterministic-diverse mood plan so demo shows all 5 varieties.
    mood_plan: list[str | None] = list(moods) + rng.sample(moods, 2)
    rng.shuffle(mood_plan)
    for i in rng.sample(range(len(mood_plan)), rng.randint(1, 2)):
        mood_plan[i] = None

    for i, days_back in enumerate(range(skip_recent + 1, days_count + skip_recent + 1)):
        d = today - timedelta(days=days_back)
        entry_id = await repo.find_or_create_day_entry(user.tg_id, d)
        base = 0.30 + 0.50 * (1 - days_back / (days_count + skip_recent))
        checks = {
            k: rng.random() < base + rng.uniform(-0.15, 0.15)
            for k, _ in habits
        }
        await repo.set_habit_checks(entry_id, habits, checks)
        if mood_plan[i] is not None:
            await repo.set_mood(entry_id, mood_plan[i])
        if rng.random() < 0.35:
            await repo.append_plan(user.tg_id, d, rng.choice(sample_plans))
        if rng.random() < 0.25:
            await repo.append_journal(user.tg_id, d, rng.choice(sample_journal))

    await message.answer(
        f"✓ заполнил {days_count} прошлых дней для примера "
        f"(вчера и позавчера оставил пустыми)."
    )
