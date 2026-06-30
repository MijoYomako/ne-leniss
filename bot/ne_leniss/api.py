import logging
from datetime import date, timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from ne_leniss.auth import verify_init_data
from ne_leniss.config import Settings
from ne_leniss.habits import HABITS
from ne_leniss.repository import Repository
from ne_leniss.services.streaks import compute_streaks

log = logging.getLogger("ne_leniss.api")


def build_fastapi(repo: Repository, settings: Settings) -> FastAPI:
    app = FastAPI(title="Ne Leniss API", version="0.1.0")

    cors_origins = [settings.webapp_url, "http://localhost:5173"]
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
        if not header.startswith("tma "):
            raise HTTPException(status_code=401, detail="missing tma authorization")
        init_data = header.removeprefix("tma ")
        uid = verify_init_data(init_data, settings.bot_token)
        if uid is None:
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
        return {
            "tg_id": user.tg_id,
            "username": user.username,
            "first_name": user.first_name,
            "timezone": user.timezone,
        }

    @app.get("/api/days")
    async def days(
        user_id: Annotated[int, Depends(current_user_id)],
        from_: Annotated[str | None, Query(alias="from")] = None,
        to: str | None = None,
    ) -> list[dict]:
        today = date.today()
        start = date.fromisoformat(from_) if from_ else (today - timedelta(days=89))
        end = date.fromisoformat(to) if to else today
        rows = await repo.query_days_range(user_id, start, end)
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
        summary = await repo.get_day_summary(user_id, target)
        return summary or {"date": date_iso, "habits": [], "mood": None, "plans": [], "journal": []}

    @app.get("/api/streaks")
    async def streaks(user_id: Annotated[int, Depends(current_user_id)]) -> list[dict]:
        today = date.today()
        rows = await repo.query_days_range(user_id, today - timedelta(days=89), today)
        return compute_streaks(rows, HABITS)

    return app
