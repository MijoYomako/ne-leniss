from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from ne_leniss.config import Settings
from ne_leniss.habits import MOOD_KEY_TO_NAME, MOOD_OPTIONS, user_habits_or_default
from ne_leniss.models import User
from ne_leniss.repository import Repository
from ne_leniss.services.streaks import compute_streaks
from ne_leniss.services.weekly_summary import build_weekly_summary

router = Router()


class MorningStates(StatesGroup):
    awaiting_checkboxes = State()
    awaiting_mood = State()
    awaiting_plans = State()


def build_checkbox_keyboard(
    habits: list[tuple[str, str]],
    checkboxes: dict[str, bool],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(habits), 2):
        row = []
        for key, label in habits[i : i + 2]:
            icon = "☑" if checkboxes.get(key, False) else "☐"
            row.append(
                InlineKeyboardButton(
                    text=f"{icon} {label}",
                    callback_data=f"chk:{key}",
                )
            )
        rows.append(row)
    rows.append([InlineKeyboardButton(text="✅ Готово", callback_data="chk:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_mood_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"mood:{key}")]
            for key, label in MOOD_OPTIONS
        ]
    )


async def send_morning_message(
    user: User,
    bot: Bot,
    repo: Repository,
    storage: BaseStorage,
    is_first_run: bool = False,
) -> None:
    tz = ZoneInfo(user.timezone)
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)
    await repo.find_or_create_day_entry(user.tg_id, today)
    await repo.find_or_create_day_entry(user.tg_id, yesterday)

    habits = user_habits_or_default(user.habits_json)
    initial = {key: False for key, _ in habits}
    state_key = StorageKey(bot_id=bot.id, chat_id=user.tg_id, user_id=user.tg_id)
    state = FSMContext(storage=storage, key=state_key)

    # Previous checklist never got a "Готово" — its buttons are still live
    # and share this same FSM state. Strip them so the user can't tap a
    # stale message and hijack the flow meant for the new one.
    if await state.get_state() == MorningStates.awaiting_checkboxes.state:
        stale_message_id = (await state.get_data()).get("checkbox_message_id")
        if stale_message_id:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=user.tg_id, message_id=stale_message_id, reply_markup=None
                )
            except TelegramBadRequest:
                pass

    await state.set_state(MorningStates.awaiting_checkboxes)
    await state.update_data(
        checkboxes=initial,
        habit_keys=[k for k, _ in habits],
        is_first_run=is_first_run,
    )

    header = "Поехали 🚀\n\nЧекни вчерашний день:" if is_first_run else "Доброе утро 🌅\n\nЧекни вчерашний день:"
    sent = await bot.send_message(
        chat_id=user.tg_id,
        text=header,
        reply_markup=build_checkbox_keyboard(habits, initial),
    )
    await state.update_data(checkbox_message_id=sent.message_id)


@router.callback_query(MorningStates.awaiting_checkboxes, F.data.startswith("chk:"))
async def on_checkbox_callback(
    query: CallbackQuery,
    state: FSMContext,
    repo: Repository,
) -> None:
    assert query.data is not None
    action = query.data.split(":", 1)[1]
    data = await state.get_data()
    checkboxes: dict[str, bool] = data.get("checkboxes", {})

    if query.from_user is None:
        await query.answer()
        return
    user = await repo.get_user(query.from_user.id)
    if user is None:
        await query.answer()
        return
    habits = user_habits_or_default(user.habits_json)

    if action == "done":
        tz = ZoneInfo(user.timezone)
        yesterday = (datetime.now(tz) - timedelta(days=1)).date()
        entry_id = await repo.find_or_create_day_entry(user.tg_id, yesterday)
        await repo.set_habit_checks(entry_id, habits, checkboxes)
        await query.message.edit_text("Чекбоксы за вчера сохранены ✓")
        await query.message.answer(
            "Каким был вчерашний день? Отмечай как чувствуешь",
            reply_markup=build_mood_keyboard(),
        )
        await state.set_state(MorningStates.awaiting_mood)
        await query.answer()
        return

    if action not in checkboxes:
        await query.answer()
        return
    checkboxes[action] = not checkboxes[action]
    await state.update_data(checkboxes=checkboxes)
    await query.message.edit_reply_markup(reply_markup=build_checkbox_keyboard(habits, checkboxes))
    await query.answer()


@router.callback_query(MorningStates.awaiting_mood, F.data.startswith("mood:"))
async def on_mood_callback(
    query: CallbackQuery,
    state: FSMContext,
    repo: Repository,
) -> None:
    assert query.data is not None
    key = query.data.split(":", 1)[1]
    if key not in MOOD_KEY_TO_NAME or query.from_user is None:
        await query.answer()
        return
    user = await repo.get_user(query.from_user.id)
    if user is None:
        await query.answer()
        return
    tz = ZoneInfo(user.timezone)
    yesterday = (datetime.now(tz) - timedelta(days=1)).date()
    yesterday_id = await repo.find_or_create_day_entry(user.tg_id, yesterday)
    mood_name = MOOD_KEY_TO_NAME[key]
    label = next(l for k, l in MOOD_OPTIONS if k == key)
    await repo.set_mood(yesterday_id, mood_name)
    await query.message.edit_text(f"Вчера: {label} ✓")

    if yesterday.weekday() == 6:  # Sunday just filled in → past week is complete
        habits = user_habits_or_default(user.habits_json)
        week_days = await repo.query_days_range(
            user.tg_id, yesterday - timedelta(days=6), yesterday, habits
        )
        streak_days = await repo.query_days_range(
            user.tg_id, yesterday - timedelta(days=89), yesterday, habits
        )
        streaks = compute_streaks(streak_days, habits)
        await query.message.answer(build_weekly_summary(habits, week_days, streaks))

    today = datetime.now(tz).date()
    await repo.find_or_create_day_entry(user.tg_id, today)
    existing = await repo.read_plans_text(user.tg_id, today)
    if existing:
        prompt = (
            "Уже запланировано на сегодня:\n\n"
            f"{existing}\n\n"
            "Что добавить? Пиши текстом — или жми «Пропустить»."
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⏭ Пропустить", callback_data="plans:skip")]]
        )
        await query.message.answer(prompt, reply_markup=kb)
    else:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🙅 Нет планов", callback_data="plans:skip")]]
        )
        await query.message.answer(
            "Какие планы на сегодня? Пиши свободным текстом или строками — или жми «Нет планов».",
            reply_markup=kb,
        )
    await state.set_state(MorningStates.awaiting_plans)
    await query.answer()


FIRST_RUN_CONGRATS = (
    "🎉 С первым заполненным днём!\n\n"
    "Прошлые 7 дней я заполнил случайными данными — открой Календарь "
    "чуть ниже 👇 и посмотри, как это будет выглядеть у тебя через пару "
    "недель регулярного трекинга.\n\n"
    "Завтра в 09:00 я приду снова 🐻"
)


# Rotating final messages after plans are saved. Rotate per day+user so the
# same person doesn't see the same tip 3 days in a row.
FINAL_MESSAGES: list[str] = [
    "Записал. День начался, и слава Богу...",
    (
        "Сохранил. Хорошего дня ✨\n\n"
        "Одна из важных фич бота — /note, заметка.\n\n"
        "Это может быть какая-то мысль, которую не хочешь потерять, или "
        "фильм, который тебе посоветовали. Кто-то ведёт дневник "
        "благодарностей, кто-то просто рассказывает о своём дне.\n\n"
        "Вообще, ведение дневника — мощный инструмент: он позволяет легче "
        "фиксироваться на своих достижениях (или неудачах), чтобы извлекать "
        "из них уроки, а не проживать одни и те же ситуации по кругу. Когда "
        "мысли остаются только в голове, они склонны повторяться, "
        "искажаться и обрастать эмоциями — а на бумаге (или в заметках) они "
        "становятся конкретными фактами, которые можно спокойно "
        "проанализировать: что сработало, что нет и почему.\n\n"
        "Мишок верит в тебя 🐻"
    ),
    (
        "Готово.\n\n"
        "День официально начался, обратной дороги нет, разве что снова лечь "
        "спать — но мы туда не пойдём."
    ),
    (
        "Готово. Продуктивного дня 💪\n\n"
        "Через /plan можно запланировать задачу на любой день. Например: "
        "<code>/plan 5.08 Зубной в 14:00</code> — когда наступит 5 августа, "
        "я покажу этот план в утреннем сообщении. Это быстрее, чем "
        "поставить напоминалку."
    ),
    (
        "Готово\n\n"
        "Марк Аврелий вставал утром и напоминал себе, что сегодня встретит "
        "ленивых, неблагодарных и лживых людей — и всё равно шёл делать "
        "свою работу, потому что это была его работа, а не реакция на "
        "чужую. План на сегодня — то же самое: не жди, что день будет "
        "удобным. Просто делай то, что в списке, независимо от того, как "
        "он сложится."
    ),
    (
        "Сохранил ✓\n\n"
        "Планы на день не обязательно трекать в приложении. Ты в любой "
        "момент можешь зайти в этот чат и посмотреть, что запланировал "
        "сегодня утром. Кайф? Кайф."
    ),
    (
        "Записал.\n\n"
        "А Сенека писал, что мы не потому не решаемся, что вещи трудны, а "
        "вещи трудны, потому что мы не решаемся начать. Первый пункт плана "
        "обычно самый неприятный именно поэтому — не потому что он "
        "объективно сложный. Начни с него, и остальное покажется легче."
    ),
    (
        "Хорошего дня, привет от меня 🐻\n\n"
        "Кстати, если Спорт и Чтение уже не кажутся амбициозными "
        "чекбоксами, ты всегда можешь поменять список отслеживаемых "
        "привычек через /habits."
    ),
    (
        "Сохранил ✨\n\n"
        "Планирование дня — это акт, а не гарантия. Ты не подписываешь "
        "контракт с вселенной, что всё пройдёт гладко. Ты просто говоришь "
        "себе, куда смотреть в следующие несколько часов, если станет "
        "непонятно, чем заняться."
    ),
    (
        "Сохранил. Пусть день пройдёт по плану ✓\n\n"
        "Через /note можно вести дневник — короткие мысли, впечатления, "
        "цитаты. Всё уйдёт в календарь этого дня, и ты сможешь вернуться "
        "к ним через месяц."
    ),
    (
        "Готово, день начался 🍃\n\n"
        "Хорошее настроение иногда прячется не в мыслях, а в теле — в том, "
        "чтобы попить воды, выйти на воздух, размяться, если давно сидишь. "
        "Прежде чем разбираться, что не так с головой, стоит на секунду "
        "проверить, что не так с телом."
    ),
    (
        "Готово, погнали ✓\n\n"
        "Не забыть бы поздравить тётю в воскресенье... <code>/plan</code> "
        "запомнит за тебя. Например: "
        "<code>/plan 08.09 ДР Тётя Мотя</code>"
    ),
    (
        "Готово\n\n"
        "Один пропущенный день почти ничего не решает статистически. "
        "Опасен не пропуск, а история, которую ты себе после него "
        "рассказываешь — «ну всё, сорвался, смысла продолжать нет». "
        "Пропустил — просто вернись завтра, без драмы.\n\n"
        "Мишок верит в тебя 🐻"
    ),
    (
        "Сохранил. День начался\n\n"
        "«Размышления» Марка Аврелия — это вообще-то не книга, которую он "
        "писал для читателей. Это его личный дневник, заметки самому себе, "
        "которые он вёл, чтобы разобраться в собственной голове. То, что "
        "ты сейчас делаешь, — та же практика, просто на 2000 лет позже.\n\n"
        "Можешь в любое время написать заметку через /note."
    ),
    (
        "Готово, погнали ✓\n\n"
        "Совершенно нормально, если привычка сегодня выполнена «на "
        "минимум» — вместо часа пять минут, вместо статьи один абзац. "
        "Смысл не в объёме, а в том, чтобы не прервать цепочку и не "
        "создать себе повод для истории про провал. Маленькое сделанное "
        "почти всегда лучше большого отложенного."
    ),
    (
        "Сохранил, поехали 🚙\n\n"
        "Если сегодня будет момент, когда захочется поругать себя за "
        "что-то мелкое — за пропущенную тренировку, несделанный звонок, "
        "лишний час в телефоне — можно попробовать сказать себе то же "
        "самое, что сказал бы другу в такой ситуации. Обычно это звучит "
        "гораздо мягче.\n\n"
        "Лошок"
    ),
    (
        "Зафиксировал ✅\n\n"
        "Леонардо да Винчи носил с собой блокнот и записывал вообще всё — "
        "от инженерных идей до списка покупок. Не потому что каждая мысль "
        "была гениальной, а потому что не угадаешь заранее, какая из них "
        "окажется важной.\n\n"
        "/note — чтобы оставить заметку на сегодняшний день."
    ),
]


def _pick_final_message(user_id: int, today: date) -> str:
    idx = (today.toordinal() + user_id) % len(FINAL_MESSAGES)
    return FINAL_MESSAGES[idx]


async def _send_congrats_if_first(
    message: Message, state_data: dict, settings: Settings
) -> None:
    if not state_data.get("is_first_run"):
        return
    await message.answer(FIRST_RUN_CONGRATS)
    # Pin a persistent app shortcut so the user always has one-tap access.
    from ne_leniss.handlers.app import pin_app_shortcut

    await pin_app_shortcut(message, settings)


@router.callback_query(MorningStates.awaiting_plans, F.data == "plans:skip")
async def on_plans_skip(
    query: CallbackQuery,
    state: FSMContext,
    settings: Settings,
) -> None:
    data = await state.get_data()
    await query.message.edit_text("Окей, оставил как есть ✓")
    # If it's the first run, only send the congratulation; otherwise pick a
    # rotating hint about /note or /plan.
    if data.get("is_first_run"):
        await _send_congrats_if_first(query.message, data, settings)
    elif query.from_user:
        tip = _pick_final_message(query.from_user.id, date.today())
        await query.message.answer(tip, parse_mode="HTML")
    await state.clear()
    await query.answer()


@router.message(MorningStates.awaiting_plans)
async def on_plans_text(
    message: Message,
    state: FSMContext,
    repo: Repository,
    settings: Settings,
) -> None:
    if message.from_user is None:
        return
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return
    user = await repo.get_user(message.from_user.id)
    if user is None:
        return
    today = datetime.now(ZoneInfo(user.timezone)).date()
    await repo.append_plan(user.tg_id, today, text)
    data = await state.get_data()
    if data.get("is_first_run"):
        await message.answer("Сохранил ✓")
        await _send_congrats_if_first(message, data, settings)
    else:
        tip = _pick_final_message(message.from_user.id, today)
        await message.answer(tip, parse_mode="HTML")
    await state.clear()


@router.message(F.text == "/trigger_morning")
async def cmd_trigger_morning(
    message: Message,
    bot: Bot,
    repo: Repository,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return
    user = await repo.get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await send_morning_message(user, bot, repo, state.storage)
