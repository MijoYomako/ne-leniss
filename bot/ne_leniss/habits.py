import json
import re
from unicodedata import normalize

DEFAULT_HABITS: list[tuple[str, str]] = [
    ("sport", "Спорт"),
    ("meditation", "Медитация"),
    ("reading", "Чтение"),
    ("water", "Вода"),
    ("sleep_7h", "Сон 7+"),
    ("no_alcohol", "Без алкоголя"),
]

MOOD_OPTIONS: list[tuple[str, str]] = [
    ("good", "😊 Хороший"),
    ("productive", "⚡ Продуктивный"),
    ("could_be_better", "🤔 Так себе"),
    ("bad", "😞 Плохой"),
    ("relaxing", "🌿 Расслабленный"),
]
MOOD_KEY_TO_NAME: dict[str, str] = {
    "good": "Good",
    "productive": "Productive",
    "could_be_better": "Could be better",
    "bad": "Bad",
    "relaxing": "Relaxing",
}

_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _slugify(label: str) -> str:
    s = normalize("NFKC", label).strip().lower()
    out = []
    for ch in s:
        if ch in _TRANSLIT:
            out.append(_TRANSLIT[ch])
        elif ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch.isspace() or ch in ".,/":
            out.append("_")
    slug = "".join(out)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "habit"


def parse_habits_input(raw: str) -> list[tuple[str, str]]:
    """User-typed habits separated by commas. Returns list of (key, label).
    Deduplicates by key; preserves first-seen order; trims and limits to 12.
    """
    items: list[tuple[str, str]] = []
    seen_keys: set[str] = set()
    seen_labels: set[str] = set()
    for chunk in raw.split(","):
        label = chunk.strip()
        if not label:
            continue
        label = re.sub(r"\s+", " ", label)[:40]
        label_norm = label.lower()
        if label_norm in seen_labels:
            continue
        key = _slugify(label)
        if not key or key in seen_keys:
            key = f"{key}_{len(items)}"
        seen_keys.add(key)
        seen_labels.add(label_norm)
        items.append((key, label))
        if len(items) >= 12:
            break
    return items


def encode_habits(habits: list[tuple[str, str]]) -> str:
    return json.dumps([{"key": k, "label": l} for k, l in habits], ensure_ascii=False)


def decode_habits(blob: str | None) -> list[tuple[str, str]] | None:
    if not blob:
        return None
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return None
    out: list[tuple[str, str]] = []
    for item in data:
        if isinstance(item, dict) and "key" in item and "label" in item:
            out.append((str(item["key"]), str(item["label"])))
    return out or None


def user_habits_or_default(user_habits_json: str | None) -> list[tuple[str, str]]:
    """Always returns a non-empty habits list. Falls back to DEFAULT_HABITS."""
    decoded = decode_habits(user_habits_json)
    return decoded if decoded else DEFAULT_HABITS
