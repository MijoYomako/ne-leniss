from ne_leniss.services.weekly_summary import build_weekly_summary

HABITS = [("reading", "Чтение"), ("sport", "Спорт")]


def test_habit_ratios_and_mood_tally() -> None:
    week_days = [
        {"date": "2026-07-06", "checks": {"reading": True, "sport": False}, "mood": "Good"},
        {"date": "2026-07-07", "checks": {"reading": True, "sport": True}, "mood": "Good"},
        {"date": "2026-07-08", "checks": {"reading": True, "sport": False}, "mood": None},
        {"date": "2026-07-09", "checks": {"reading": False, "sport": False}, "mood": "Bad"},
    ]
    text = build_weekly_summary(HABITS, week_days, streaks=[])
    assert "Чтение: 3/7" in text
    assert "Спорт: 1/7" in text
    assert "😊 Хороший — 2" in text
    assert "😞 Плохой — 1" in text
    assert "🔥" not in text


def test_streak_callout_only_above_threshold() -> None:
    streaks = [
        {"key": "reading", "label": "Чтение", "current": 9, "best": 9},
        {"key": "sport", "label": "Спорт", "current": 2, "best": 5},
    ]
    text = build_weekly_summary(HABITS, [], streaks)
    assert "🔥 Чтение: стрик 9 дней подряд" in text
    assert "Спорт: стрик" not in text


def test_no_moods_this_week_omits_section() -> None:
    week_days = [{"date": "2026-07-06", "checks": {}, "mood": None}]
    text = build_weekly_summary(HABITS, week_days, streaks=[])
    assert "Настроение" not in text


if __name__ == "__main__":
    test_habit_ratios_and_mood_tally()
    test_streak_callout_only_above_threshold()
    test_no_moods_this_week_omits_section()
    print("ok")
