from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import and_, delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from ne_leniss.models import (
    DayEntry,
    HabitCheck,
    JournalEntry,
    MorningSent,
    Plan,
    User,
)


class Repository:
    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        self._sm = sessionmaker

    # ---------- Users ----------

    async def get_or_create_user(
        self,
        tg_id: int,
        username: str | None,
        first_name: str | None,
        default_tz: str = "Europe/Moscow",
    ) -> User:
        async with self._sm() as s:
            existing = await s.get(User, tg_id)
            if existing is not None:
                changed = False
                if username and existing.username != username:
                    existing.username = username
                    changed = True
                if first_name and existing.first_name != first_name:
                    existing.first_name = first_name
                    changed = True
                if changed:
                    await s.commit()
                return existing
            user = User(
                tg_id=tg_id,
                username=username,
                first_name=first_name,
                timezone=default_tz,
            )
            s.add(user)
            await s.commit()
            await s.refresh(user)
            return user

    async def get_user(self, tg_id: int) -> User | None:
        async with self._sm() as s:
            return await s.get(User, tg_id)

    async def set_user_habits(self, tg_id: int, habits_json: str) -> None:
        async with self._sm() as s:
            user = await s.get(User, tg_id)
            if user is None:
                return
            user.habits_json = habits_json
            await s.commit()

    # ---------- Day entries ----------

    async def find_or_create_day_entry(self, user_id: int, target: date) -> int:
        date_iso = target.isoformat()
        async with self._sm() as s:
            existing = (
                await s.execute(
                    select(DayEntry).where(
                        and_(DayEntry.user_id == user_id, DayEntry.date == date_iso)
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                return existing.id
            entry = DayEntry(user_id=user_id, date=date_iso)
            s.add(entry)
            await s.commit()
            await s.refresh(entry)
            return entry.id

    async def set_habit_checks(
        self,
        day_entry_id: int,
        habits: list[tuple[str, str]],
        checks: dict[str, bool],
    ) -> None:
        """Overwrite habit_checks for a day. `habits` is the set of habits
        active for this day (used to persist labels for historical accuracy)."""
        async with self._sm() as s:
            await s.execute(
                delete(HabitCheck).where(HabitCheck.day_entry_id == day_entry_id)
            )
            for key, label in habits:
                s.add(
                    HabitCheck(
                        day_entry_id=day_entry_id,
                        habit_key=key,
                        label=label,
                        checked=checks.get(key, False),
                    )
                )
            await s.commit()

    async def set_mood(self, day_entry_id: int, mood: str) -> None:
        async with self._sm() as s:
            entry = await s.get(DayEntry, day_entry_id)
            if entry is None:
                raise RuntimeError(f"day_entry {day_entry_id} not found")
            entry.mood = mood
            await s.commit()

    # ---------- Plans / journal ----------

    async def append_plan(self, user_id: int, target: date, text: str) -> None:
        async with self._sm() as s:
            s.add(Plan(user_id=user_id, date=target.isoformat(), text=text))
            await s.commit()

    async def append_journal(self, user_id: int, target: date, text: str) -> None:
        async with self._sm() as s:
            s.add(JournalEntry(user_id=user_id, date=target.isoformat(), text=text))
            await s.commit()

    async def read_plans_text(self, user_id: int, target: date) -> str:
        async with self._sm() as s:
            rows = (
                await s.execute(
                    select(Plan.text)
                    .where(and_(Plan.user_id == user_id, Plan.date == target.isoformat()))
                    .order_by(Plan.created_at)
                )
            ).all()
            return "\n".join(r[0].strip() for r in rows if r[0].strip())

    # ---------- API queries ----------

    async def get_day_summary(
        self,
        user_id: int,
        target: date,
        current_habits: list[tuple[str, str]],
    ) -> dict:
        """current_habits is used as fallback for empty days (day exists but
        no habit_checks yet). Days that already have checks stored show
        their historical habit list, so past days keep the labels they had
        when the user filled them.
        """
        async with self._sm() as s:
            entry = (
                await s.execute(
                    select(DayEntry).where(
                        and_(DayEntry.user_id == user_id, DayEntry.date == target.isoformat())
                    )
                )
            ).scalar_one_or_none()

            habits_display: list[tuple[str, str]] = []
            checks_map: dict[str, bool] = {}

            if entry is not None:
                rows = (
                    await s.execute(
                        select(HabitCheck.habit_key, HabitCheck.label, HabitCheck.checked).where(
                            HabitCheck.day_entry_id == entry.id
                        )
                    )
                ).all()
                if rows:
                    for key, label, checked in rows:
                        habits_display.append((key, label or key))
                        checks_map[key] = bool(checked)

            if not habits_display:
                habits_display = list(current_habits)

            plans = (
                await s.execute(
                    select(Plan.text)
                    .where(and_(Plan.user_id == user_id, Plan.date == target.isoformat()))
                    .order_by(Plan.created_at)
                )
            ).all()
            journal = (
                await s.execute(
                    select(JournalEntry.text)
                    .where(and_(JournalEntry.user_id == user_id, JournalEntry.date == target.isoformat()))
                    .order_by(JournalEntry.created_at)
                )
            ).all()
            return {
                "date": target.isoformat(),
                "mood": entry.mood if entry else None,
                "habits": [
                    {"key": k, "label": label, "checked": checks_map.get(k, False)}
                    for k, label in habits_display
                ],
                "plans": [r[0] for r in plans],
                "journal": [r[0] for r in journal],
            }

    async def query_days_range(
        self,
        user_id: int,
        start: date,
        end: date,
        current_habits: list[tuple[str, str]],
    ) -> list[dict]:
        """Returns per-day summary. `checked_count`/`total_habits` reflect
        the habits recorded for that day (historical accuracy).
        For empty days we fall back to `current_habits` length so the tile
        still renders a max denominator.
        """
        start_iso, end_iso = start.isoformat(), end.isoformat()
        default_total = len(current_habits) or 1
        async with self._sm() as s:
            entries = (
                await s.execute(
                    select(DayEntry).where(
                        and_(
                            DayEntry.user_id == user_id,
                            DayEntry.date >= start_iso,
                            DayEntry.date <= end_iso,
                        )
                    )
                )
            ).scalars().all()
            entry_ids = [e.id for e in entries]
            checks_by_entry: dict[int, dict[str, bool]] = {eid: {} for eid in entry_ids}
            if entry_ids:
                rows = (
                    await s.execute(
                        select(HabitCheck.day_entry_id, HabitCheck.habit_key, HabitCheck.checked).where(
                            HabitCheck.day_entry_id.in_(entry_ids)
                        )
                    )
                ).all()
                for eid, key, val in rows:
                    checks_by_entry[eid][key] = bool(val)
            plan_dates = {
                r[0]
                for r in (
                    await s.execute(
                        select(Plan.date).where(
                            and_(
                                Plan.user_id == user_id,
                                Plan.date >= start_iso,
                                Plan.date <= end_iso,
                            )
                        ).distinct()
                    )
                ).all()
            }
            journal_dates = {
                r[0]
                for r in (
                    await s.execute(
                        select(JournalEntry.date).where(
                            and_(
                                JournalEntry.user_id == user_id,
                                JournalEntry.date >= start_iso,
                                JournalEntry.date <= end_iso,
                            )
                        ).distinct()
                    )
                ).all()
            }
            result = []
            for e in entries:
                day_checks = checks_by_entry.get(e.id, {})
                total = len(day_checks) if day_checks else default_total
                checked_count = sum(1 for v in day_checks.values() if v)
                result.append(
                    {
                        "date": e.date,
                        "checked_count": checked_count,
                        "total_habits": total,
                        "mood": e.mood,
                        "has_plans": e.date in plan_dates,
                        "has_journal": e.date in journal_dates,
                        "checks": day_checks,
                    }
                )
            return result

    # ---------- Morning scheduler ----------

    async def users_due_for_morning(self, now_utc: datetime) -> list[User]:
        async with self._sm() as s:
            all_users = (await s.execute(select(User))).scalars().all()
            due: list[User] = []
            for u in all_users:
                try:
                    local = now_utc.astimezone(ZoneInfo(u.timezone))
                except Exception:
                    continue
                if local.hour != u.morning_hour or local.minute != u.morning_minute:
                    continue
                if not u.habits_json:
                    # user hasn't completed onboarding — skip morning push
                    continue
                date_iso = local.date().isoformat()
                already = await s.get(MorningSent, (u.tg_id, date_iso))
                if already is None:
                    due.append(u)
            return due

    async def was_morning_sent(self, user_id: int, date_iso: str) -> bool:
        async with self._sm() as s:
            row = await s.get(MorningSent, (user_id, date_iso))
            return row is not None

    async def mark_morning_sent(self, user_id: int, date_iso: str) -> None:
        async with self._sm() as s:
            stmt = sqlite_insert(MorningSent).values(user_id=user_id, date=date_iso)
            stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "date"])
            await s.execute(stmt)
            await s.commit()
