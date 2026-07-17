from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from ne_leniss.repository import Repository

router = Router()

MONTHS = [
    "янв", "фев", "мар", "апр", "мая", "июн",
    "июл", "авг", "сен", "окт", "ноя", "дек",
]


class NoteStates(StatesGroup):
    awaiting_text = State()


async def _save_note(user_id: int, text: str, repo: Repository, message: Message) -> None:
    user = await repo.get_or_create_user(
        tg_id=user_id,
        username=message.from_user.username if message.from_user else None,
        first_name=message.from_user.first_name if message.from_user else None,
    )
    today = datetime.now(ZoneInfo(user.timezone)).date()
    await repo.append_journal(user.tg_id, today, text)
    await message.answer("✓ записал в журнал сегодня")


@router.message(Command("note"))
async def cmd_note(message: Message, repo: Repository, state: FSMContext) -> None:
    if message.from_user is None:
        return
    text = (message.text or "").removeprefix("/note").strip()
    if text:
        await _save_note(message.from_user.id, text, repo, message)
        return
    await state.set_state(NoteStates.awaiting_text)
    await message.answer(
        "📝 Что записать в журнал?\n\n"
        "Пиши следующим сообщением — сохраню в журнал сегодня.\n"
        "Передумал — /cancel"
    )


@router.message(Command("summary_note_14"))
async def cmd_summary_note_14(message: Message, repo: Repository) -> None:
    if message.from_user is None:
        return
    user = await repo.get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    today = datetime.now(ZoneInfo(user.timezone)).date()
    entries = await repo.read_journal_range(user.tg_id, today - timedelta(days=13), today)
    if not entries:
        await message.answer("За последние 14 дней заметок нет. Записать что-нибудь? /note")
        return
    lines = ["📔 Заметки за 14 дней", ""]
    lines.extend(f"{d.day} {MONTHS[d.month - 1]}: {text}" for d, text in entries)
    await message.answer("\n".join(lines))


@router.message(NoteStates.awaiting_text, F.text == "/cancel")
async def on_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Окей, отменил.")


@router.message(NoteStates.awaiting_text)
async def on_note_text(message: Message, repo: Repository, state: FSMContext) -> None:
    if message.from_user is None or not message.text:
        return
    if message.text.startswith("/"):
        await message.answer("Похоже на команду, а не на заметку. Если передумал — /cancel.")
        return
    await _save_note(message.from_user.id, message.text, repo, message)
    await state.clear()
