import asyncio
from datetime import date

from ne_leniss.db import create_async_engine_from_url, init_db, sessionmaker_from_engine
from ne_leniss.repository import Repository


async def _make_repo() -> Repository:
    engine = create_async_engine_from_url("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    return Repository(sessionmaker_from_engine(engine))


async def test_read_journal_range_filters_and_orders() -> None:
    repo = await _make_repo()
    user_id = 1
    await repo.get_or_create_user(user_id, "u", "U")
    await repo.append_journal(user_id, date(2026, 7, 1), "too old")
    await repo.append_journal(user_id, date(2026, 7, 10), "second")
    await repo.append_journal(user_id, date(2026, 7, 5), "first")
    await repo.append_journal(user_id, date(2026, 7, 20), "too new")

    entries = await repo.read_journal_range(user_id, date(2026, 7, 5), date(2026, 7, 14))
    assert entries == [
        (date(2026, 7, 5), "first"),
        (date(2026, 7, 10), "second"),
    ], entries


async def test_read_journal_range_empty() -> None:
    repo = await _make_repo()
    entries = await repo.read_journal_range(1, date(2026, 7, 1), date(2026, 7, 14))
    assert entries == []


async def _run() -> None:
    await test_read_journal_range_filters_and_orders()
    await test_read_journal_range_empty()
    print("ok")


if __name__ == "__main__":
    asyncio.run(_run())
