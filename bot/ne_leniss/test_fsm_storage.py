import asyncio
import tempfile
from pathlib import Path

from aiogram.fsm.storage.base import StorageKey

from ne_leniss.fsm_storage import JsonFileStorage


async def test_state_and_data_survive_reload() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fsm_state.json"
        key = StorageKey(bot_id=1, chat_id=2, user_id=2)

        storage = JsonFileStorage(path)
        await storage.set_state(key, "MorningStates:awaiting_checkboxes")
        await storage.set_data(key, {"checkboxes": {"sport": True}})

        # simulate a process restart: fresh instance reading the same file
        reloaded = JsonFileStorage(path)
        assert await reloaded.get_state(key) == "MorningStates:awaiting_checkboxes"
        assert await reloaded.get_data(key) == {"checkboxes": {"sport": True}}


async def test_missing_key_returns_defaults() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        storage = JsonFileStorage(Path(tmp) / "fsm_state.json")
        key = StorageKey(bot_id=1, chat_id=2, user_id=2)
        assert await storage.get_state(key) is None
        assert await storage.get_data(key) == {}


async def test_clearing_state_removes_it() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fsm_state.json"
        key = StorageKey(bot_id=1, chat_id=2, user_id=2)
        storage = JsonFileStorage(path)
        await storage.set_state(key, "some_state")
        await storage.set_state(key, None)
        assert await storage.get_state(key) is None


async def _run() -> None:
    await test_state_and_data_survive_reload()
    await test_missing_key_returns_defaults()
    await test_clearing_state_removes_it()
    print("ok")


if __name__ == "__main__":
    asyncio.run(_run())
