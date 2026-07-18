from ne_leniss.habits import MOOD_KEY_TO_NAME, MOOD_OPTIONS

STREAK_CALLOUT_THRESHOLD = 7
WEEK_LENGTH = 7


def build_weekly_summary(
    habits: list[tuple[str, str]],
    week_days: list[dict],
    streaks: list[dict],
) -> str:
    """`week_days` is `repo.query_days_range` output for the Mon-Sun that just
    ended. `streaks` is `compute_streaks` output over a wider lookback."""
    habit_counts = {key: 0 for key, _ in habits}
    mood_counts: dict[str, int] = {}
    for day in week_days:
        checks = day.get("checks", {})
        for key in habit_counts:
            if checks.get(key):
                habit_counts[key] += 1
        mood = day.get("mood")
        if mood:
            mood_counts[mood] = mood_counts.get(mood, 0) + 1

    lines = ["📊 Итоги прошлой недели", ""]
    for key, label in habits:
        lines.append(f"{label}: {habit_counts[key]}/{WEEK_LENGTH}")

    hot_streaks = [s for s in streaks if s["current"] >= STREAK_CALLOUT_THRESHOLD]
    if hot_streaks:
        lines.append("")
        for s in hot_streaks:
            lines.append(f"🔥 {s['label']}: стрик {s['current']} дней подряд — красава!")

    if mood_counts:
        # Iterate the week's actual mood values, not MOOD_OPTIONS: a mood
        # option can be retired later while past weeks still logged it, and
        # that history shouldn't silently disappear from the tally.
        mood_labels = {MOOD_KEY_TO_NAME[key]: label for key, label in MOOD_OPTIONS}
        lines.append("")
        lines.append("Настроение за неделю:")
        for name, count in mood_counts.items():
            lines.append(f"{mood_labels.get(name, name)} — {count}")

    return "\n".join(lines)
