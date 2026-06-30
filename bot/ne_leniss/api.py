import logging
from datetime import date, timedelta
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from ne_leniss.auth import verify_init_data
from ne_leniss.config import Settings
from ne_leniss.habits import user_habits_or_default
from ne_leniss.repository import Repository
from ne_leniss.services.streaks import compute_streaks

log = logging.getLogger("ne_leniss.api")


def build_fastapi(repo: Repository, settings: Settings) -> FastAPI:
    app = FastAPI(title="Ne Leniss API", version="0.1.0")

    parsed = urlparse(settings.webapp_url)
    webapp_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else settings.webapp_url
    cors_origins = [webapp_origin, "http://localhost:5173"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET"],
        allow_headers=["Authorization", "Content-Type"],
    )

    async def current_user_id(request: Request) -> int:
        if settings.debug_bypass_auth:
            uid = request.query_params.get("uid")
            if uid and uid.isdigit():
                return int(uid)
        header = request.headers.get("Authorization", "")
        origin = request.headers.get("Origin", "-")
        if not header.startswith("tma "):
            log.warning("auth: no tma header, origin=%s path=%s", origin, request.url.path)
            raise HTTPException(status_code=401, detail="missing tma authorization")
        init_data = header.removeprefix("tma ")
        uid = verify_init_data(init_data, settings.bot_token)
        if uid is None:
            log.warning("auth: HMAC failed, origin=%s path=%s", origin, request.url.path)
            raise HTTPException(status_code=401, detail="invalid initData")
        return uid

    @app.get("/api/healthz")
    async def healthz() -> dict:
        return {"ok": True}

    @app.get("/api/me")
    async def me(user_id: Annotated[int, Depends(current_user_id)]) -> dict:
        user = await repo.get_user(user_id)
        if user is None:
            user = await repo.get_or_create_user(user_id, None, None)
        habits = user_habits_or_default(user.habits_json)
        return {
            "tg_id": user.tg_id,
            "username": user.username,
            "first_name": user.first_name,
            "timezone": user.timezone,
            "onboarded": user.habits_json is not None,
            "habits": [{"key": k, "label": l} for k, l in habits],
        }

    @app.get("/api/days")
    async def days(
        user_id: Annotated[int, Depends(current_user_id)],
        from_: Annotated[str | None, Query(alias="from")] = None,
        to: str | None = None,
    ) -> list[dict]:
        user = await repo.get_user(user_id)
        habits = user_habits_or_default(user.habits_json if user else None)
        today = date.today()
        start = date.fromisoformat(from_) if from_ else (today - timedelta(days=89))
        end = date.fromisoformat(to) if to else today
        rows = await repo.query_days_range(user_id, start, end, habits)
        return [
            {
                "date": r["date"],
                "checked_count": r["checked_count"],
                "total_habits": r["total_habits"],
                "mood": r["mood"],
                "has_plans": r["has_plans"],
                "has_journal": r["has_journal"],
            }
            for r in rows
        ]

    @app.get("/api/days/{date_iso}")
    async def day_detail(
        date_iso: str,
        user_id: Annotated[int, Depends(current_user_id)],
    ) -> dict:
        try:
            target = date.fromisoformat(date_iso)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid date")
        user = await repo.get_user(user_id)
        habits = user_habits_or_default(user.habits_json if user else None)
        return await repo.get_day_summary(user_id, target, habits)

    @app.get("/api/streaks")
    async def streaks(user_id: Annotated[int, Depends(current_user_id)]) -> list[dict]:
        user = await repo.get_user(user_id)
        habits = user_habits_or_default(user.habits_json if user else None)
        today = date.today()
        rows = await repo.query_days_range(user_id, today - timedelta(days=89), today, habits)
        return compute_streaks(rows, habits)

    return app
