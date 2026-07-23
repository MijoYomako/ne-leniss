import asyncio
import json
from pathlib import Path
from typing import Any, Mapping

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey


def _key_str(key: StorageKey) -> str:
    return (
        f"{key.bot_id}:{key.chat_id}:{key.user_id}:"
        f"{key.thread_id}:{key.business_connection_id}:{key.destiny}"
    )


class JsonFileStorage(BaseStorage):
    """FSM storage backed by a single JSON file, so state survives process restarts.

    A DB table or Redis would be overkill at this scale (a handful of users,
    a few writes a day) — this is just MemoryStorage's dict flushed to disk.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        self._store: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._store))
        tmp.replace(self._path)

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        async with self._lock:
            entry = self._store.setdefault(_key_str(key), {})
            state_str = state.state if isinstance(state, State) else state
            if state_str is None:
                entry.pop("state", None)
            else:
                entry["state"] = state_str
            self._save()

    async def get_state(self, key: StorageKey) -> str | None:
        async with self._lock:
            return self._store.get(_key_str(key), {}).get("state")

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        async with self._lock:
            entry = self._store.setdefault(_key_str(key), {})
            entry["data"] = dict(data)
            self._save()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        async with self._lock:
            return dict(self._store.get(_key_str(key), {}).get("data", {}))

    async def close(self) -> None:
        pass
