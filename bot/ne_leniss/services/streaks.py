from datetime import date, datetime


def compute_streaks(
    days: list[dict],
    habits: list[tuple[str, str]],
) -> list[dict]:
    """Given days sorted by date ASC, compute current+best streak per habit.

    A streak of N = N consecutive days where checked=True.
    Current streak is counted ending on the latest date in `days`
    (if that date has check=True) — gaps reset streak to 0.
    """
    if not days:
        return [{"key": k, "label": l, "current": 0, "best": 0} for k, l in habits]

    sorted_days = sorted(days, key=lambda d: d["date"])
    parsed = [(_to_date(d["date"]), d.get("checks", {})) for d in sorted_days]

    result = []
    for key, label in habits:
        best = 0
        running = 0
        prev_date: date | None = None
        for d, checks in parsed:
            if prev_date is not None and (d - prev_date).days > 1:
                running = 0
            if checks.get(key):
                running += 1
                best = max(best, running)
            else:
                running = 0
            prev_date = d
        last_date = parsed[-1][0]
        last_checks = parsed[-1][1]
        current = running if last_checks.get(key) else 0
        result.append({"key": key, "label": label, "current": current, "best": best})
    return result


def _to_date(value) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))
