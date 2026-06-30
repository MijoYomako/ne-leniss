import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from ne_leniss.repository import Repository

router = Router()


class PlanStates(StatesGroup):
    awaiting_text = State()


WIZARD_PROMPT = (
    "📅 На какой день и что планируешь?\n\n"
    "Формат: <code>дата текст</code>\n\n"
    "Где дата:\n"
    "• <code>05.07</code> — день и месяц\n"
    "• <code>tomorrow</code> или <code>завтра</code>\n"
    "• <code>+3</code> — через 3 дня\n"
    "• <code>2026-07-15</code>\n\n"
    "Примеры:\n"
    "<code>05.07 встреча с врачом 11:00</code>\n"
    "<code>tomorrow зал в 19</code>\n"
    "<code>+3 родители в гости</code>\n\n"
    "Передумал — /cancel"
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


async def _save_plan(user_id: int, message: Message, repo: Repository, raw: str) -> bool:
    user = await repo.get_or_create_user(
        tg_id=user_id,
        username=message.from_user.username if message.from_user else None,
        first_name=message.from_user.first_name if message.from_user else None,
    )
    parts = raw.split(None, 1)
    if len(parts) < 2:
        await message.answer(
            f"Не понял. Нужно: <code>дата текст</code>.\n\n{WIZARD_PROMPT}",
            parse_mode="HTML",
        )
        return False
    date_token, plan_text = parts
    today = datetime.now(ZoneInfo(user.timezone)).date()
    target = _parse_date(date_token, today)
    if target is None:
        await message.answer(
            f"Не распознал дату «{date_token}».\n\n{WIZARD_PROMPT}",
            parse_mode="HTML",
        )
        return False
    await repo.append_plan(user.tg_id, target, plan_text)
    months = ["янв", "фев", "мар", "апр", "мая", "июн",
              "июл", "авг", "сен", "окт", "ноя", "дек"]
    pretty = f"{target.day} {months[target.month - 1]}"
    await message.answer(f"✓ запланировал на {pretty}")
    return True


@router.message(Command("plan"))
async def cmd_plan(message: Message, repo: Repository, state: FSMContext) -> None:
    if message.from_user is None:
        return
    raw = (message.text or "").removeprefix("/plan").strip()
    if raw:
        await _save_plan(message.from_user.id, message, repo, raw)
        return
    await state.set_state(PlanStates.awaiting_text)
    await message.answer(WIZARD_PROMPT, parse_mode="HTML")


@router.message(PlanStates.awaiting_text, F.text == "/cancel")
async def on_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Окей, отменил.")


@router.message(PlanStates.awaiting_text)
async def on_plan_text(message: Message, repo: Repository, state: FSMContext) -> None:
    if message.from_user is None or not message.text:
        return
    if message.text.startswith("/"):
        await message.answer("Похоже на команду. Если передумал — /cancel.")
        return
    ok = await _save_plan(message.from_user.id, message, repo, message.text)
    if ok:
        await state.clear()
