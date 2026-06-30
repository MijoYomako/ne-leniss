import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.fsm.storage.base import BaseStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ne_leniss.handlers.morning import send_morning_message
from ne_leniss.repository import Repository

log = logging.getLogger("ne_leniss.scheduler")


def build_scheduler(bot: Bot, repo: Repository, storage: BaseStorage) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=timezone.utc)

    async def morning_scan() -> None:
        now_utc = datetime.now(timezone.utc)
        try:
            users = await repo.users_due_for_morning(now_utc)
        except Exception:
            log.exception("users_due_for_morning failed")
            return
        for user in users:
            try:
                await send_morning_message(user, bot, repo, storage)
                date_iso = now_utc.astimezone(ZoneInfo(user.timezone)).date().isoformat()
                await repo.mark_morning_sent(user.tg_id, date_iso)
                log.info("morning sent to user %s for %s", user.tg_id, date_iso)
            except Exception:
                log.exception("send_morning_message failed for user %s", user.tg_id)

    scheduler.add_job(morning_scan, "cron", minute="*")
    return scheduler
