from ne_leniss.services.streaks import compute_streaks

HABITS = [("water", "Вода")]


def test_today_placeholder_does_not_zero_the_streak() -> None:
    days = [
        {"date": "2026-07-14", "checks": {"water": True}},
        {"date": "2026-07-15", "checks": {"water": True}},
        {"date": "2026-07-16", "checks": {"water": True}},
        {"date": "2026-07-17", "checks": {}},  # today's empty placeholder
    ]
    assert compute_streaks(days, HABITS) == [
        {"key": "water", "label": "Вода", "current": 3, "best": 3}
    ]


def test_explicit_unchecked_day_still_breaks_streak() -> None:
    days = [
        {"date": "2026-07-14", "checks": {"water": True}},
        {"date": "2026-07-15", "checks": {"water": True}},
        {"date": "2026-07-16", "checks": {"water": False}},
    ]
    assert compute_streaks(days, HABITS) == [
        {"key": "water", "label": "Вода", "current": 0, "best": 2}
    ]


def test_no_days() -> None:
    assert compute_streaks([], HABITS) == [
        {"key": "water", "label": "Вода", "current": 0, "best": 0}
    ]


def test_only_placeholder_days() -> None:
    assert compute_streaks([{"date": "2026-07-17", "checks": {}}], HABITS) == [
        {"key": "water", "label": "Вода", "current": 0, "best": 0}
    ]


def test_single_checked_day_reports_actual_count() -> None:
    days = [{"date": "2026-07-16", "checks": {"water": True}}]
    assert compute_streaks(days, HABITS) == [
        {"key": "water", "label": "Вода", "current": 1, "best": 1}
    ]


if __name__ == "__main__":
    test_today_placeholder_does_not_zero_the_streak()
    test_explicit_unchecked_day_still_breaks_streak()
    test_no_days()
    test_only_placeholder_days()
    test_single_checked_day_reports_actual_count()
    print("ok")
