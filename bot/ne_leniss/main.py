import asyncio
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from ne_leniss.config import load_settings
from ne_leniss.db import (
    create_async_engine_from_url,
    init_db,
    sessionmaker_from_engine,
)
from ne_leniss.handlers import app as app_handler
from ne_leniss.handlers import morning as morning_handler
from ne_leniss.handlers import note as note_handler
from ne_leniss.handlers import plan as plan_handler
from ne_leniss.handlers import start as start_handler
from ne_leniss.repository import Repository
from ne_leniss.scheduler import build_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("ne_leniss")


async def main() -> None:
    settings = load_settings()
    engine = create_async_engine_from_url(settings.db_url)
    await init_db(engine)
    log.info("DB ready: %s", settings.db_url)

    bot = Bot(token=settings.bot_token)
    me = await bot.get_me()
    log.info("Telegram OK: @%s", me.username)

    repo = Repository(sessionmaker_from_engine(engine))

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start_handler.router)
    dp.include_router(note_handler.router)
    dp.include_router(plan_handler.router)
    dp.include_router(app_handler.router)
    dp.include_router(morning_handler.router)

    dp["repo"] = repo
    dp["settings"] = settings
    dp["bot"] = bot

    scheduler = build_scheduler(bot, repo, dp.fsm.storage)
    scheduler.start()
    log.info("Scheduler started (per-minute morning scan)")

    log.info("Starting polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
