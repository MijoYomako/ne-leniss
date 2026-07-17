import asyncio

from aiogram.fsm.storage.memory import MemoryStorage

from ne_leniss.handlers.morning import send_morning_message
from ne_leniss.models import User


class FakeBot:
    id = 1

    def __init__(self) -> None:
        self.edited: list[dict] = []
        self._next_message_id = 100

    async def send_message(self, **kwargs):
        self._next_message_id += 1
        return type("Msg", (), {"message_id": self._next_message_id})()

    async def edit_message_reply_markup(self, **kwargs):
        self.edited.append(kwargs)


class FakeRepo:
    async def find_or_create_day_entry(self, user_id: int, target) -> int:
        return 1


def make_user() -> User:
    return User(tg_id=42, timezone="Europe/Moscow", habits_json=None)


async def test_unfinished_checklist_gets_stripped_on_next_send() -> None:
    bot = FakeBot()
    storage = MemoryStorage()
    user = make_user()

    await send_morning_message(user, bot, FakeRepo(), storage)
    first_message_id = bot._next_message_id
    assert bot.edited == []

    await send_morning_message(user, bot, FakeRepo(), storage)
    assert bot.edited == [
        {"chat_id": 42, "message_id": first_message_id, "reply_markup": None}
    ]


async def test_completed_checklist_is_left_alone() -> None:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey

    from ne_leniss.handlers.morning import MorningStates

    bot = FakeBot()
    storage = MemoryStorage()
    user = make_user()

    await send_morning_message(user, bot, FakeRepo(), storage)

    key = StorageKey(bot_id=bot.id, chat_id=user.tg_id, user_id=user.tg_id)
    await FSMContext(storage=storage, key=key).set_state(MorningStates.awaiting_mood)

    await send_morning_message(user, bot, FakeRepo(), storage)
    assert bot.edited == []


async def _run() -> None:
    await test_unfinished_checklist_gets_stripped_on_next_send()
    await test_completed_checklist_is_left_alone()
    print("ok")


if __name__ == "__main__":
    asyncio.run(_run())
