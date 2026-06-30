from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from ne_leniss.models import Base


def create_async_engine_from_url(url: str) -> AsyncEngine:
    if url.startswith("sqlite+aiosqlite:///"):
        rel = url.removeprefix("sqlite+aiosqlite:///")
        if not rel.startswith("/"):
            Path(rel).parent.mkdir(parents=True, exist_ok=True)
    return create_async_engine(url, echo=False, future=True)


def sessionmaker_from_engine(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
