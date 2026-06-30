import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ne_leniss.repository import Repository

router = Router()

USAGE = (
    "Использование: /plan <дата> <текст>\n\n"
    "Дата: today/сегодня, tomorrow/завтра, +N (через N дней), "
    "YYYY-MM-DD или DD.MM[.YYYY]\n\n"
    "Примеры:\n"
    "/plan tomorrow зал в 19\n"
    "/plan +3 встреча с врачом\n"
    "/plan 2026-07-15 деньрожденье\n"
    "/plan 5.07 поездка"
)


def _parse_date(token: str, today: date) -> date | None:
    t = token.lower().strip()
    if t in ("today", "сегодня"):
        return today
    if t in ("tomorrow", "завтра"):
        return today + timedelta(days=1)
    if re.fullmatch(r"\+\d+", t):
        return today + timedelta(days=int(t[1:]))
    try:
        return date.fromisoformat(t)
    except ValueError:
        pass
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{2,4}))?", t)
    if m:
        try:
            day = int(m.group(1))
            month = int(m.group(2))
            year_str = m.group(3)
            if year_str:
                year = int(year_str)
                if year < 100:
                    year += 2000
            else:
                year = today.year
            return date(year, month, day)
        except ValueError:
            return None
    return None


@router.message(Command("plan"))
async def cmd_plan(message: Message, repo: Repository) -> None:
    raw = (message.text or "").removeprefix("/plan").strip()
    if not raw:
        await message.answer(USAGE)
        return
    parts = raw.split(None, 1)
    if len(parts) < 2:
        await message.answer(USAGE)
        return
    if message.from_user is None:
        return
    user = await repo.get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    today = datetime.now(ZoneInfo(user.timezone)).date()
    date_token, plan_text = parts
    target = _parse_date(date_token, today)
    if target is None:
        await message.answer(f"Не распознал дату «{date_token}».\n\n{USAGE}")
        return
    await repo.append_plan(user.tg_id, target, plan_text)
    await message.answer(f"✓ запланировал на {target.isoformat()}")
