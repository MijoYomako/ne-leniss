HABITS: list[tuple[str, str]] = [
    ("sport", "Спорт"),
    ("meditation", "Медитация"),
    ("reading", "Чтение"),
    ("water", "Вода"),
    ("sleep_7h", "Сон 7+"),
    ("no_alcohol", "Без алкоголя"),
]

HABIT_KEYS: list[str] = [key for key, _ in HABITS]
HABIT_LABELS: dict[str, str] = {key: label for key, label in HABITS}

MOOD_OPTIONS: list[tuple[str, str]] = [
    ("good", "😊 Good"),
    ("productive", "⚡ Productive"),
    ("could_be_better", "🤔 Could be better"),
    ("bad", "😞 Bad"),
    ("relaxing", "🌿 Relaxing"),
]
MOOD_KEY_TO_NAME: dict[str, str] = {
    "good": "Good",
    "productive": "Productive",
    "could_be_better": "Could be better",
    "bad": "Bad",
    "relaxing": "Relaxing",
}
