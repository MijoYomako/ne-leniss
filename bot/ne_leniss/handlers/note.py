from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ne_leniss.repository import Repository

router = Router()

USAGE = "Использование: /note <текст заметки>"


@router.message(Command("note"))
async def cmd_note(message: Message, repo: Repository) -> None:
    text = (message.text or "").removeprefix("/note").strip()
    if not text:
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
    await repo.append_journal(user.tg_id, today, text)
    await message.answer("✓ записал")
