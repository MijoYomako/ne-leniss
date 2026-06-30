# Ne Leniss — Design Spec

**Дата:** 2026-06-30
**Бот:** @ne_leniss_bot
**Статус:** approved → implementation plan
**Audience:** друзья lomikee (multi-user public bot)

---

## 1. Цель

Тот же daily habit tracker, что и [daily-bot](https://github.com/MijoYomako/daily-bot), но:
- **Multi-user**: любой может `/start` и пользоваться.
- **Свой backend**: SQLite, без Notion (Notion остаётся только для лично lomikee'а в другом боте).
- **Telegram Mini App**: визуальный календарь, streaks, детали дня — read-only.
- **MVP**: минимум фич, максимум скорости запуска.

---

## 2. Что бот делает

### 2.1 `/start` — auto-registration

- Новый user → INSERT в `users`, дефолтные настройки (TZ=Europe/Moscow, set из 6 habits, morning=09:00, digest=Sun 21:00). Welcome message.
- Existing user → help-сообщение.

### 2.2 Утренний триггер (каждый день, по локальному времени user'а)

Тот же UX, что в текущем daily-bot:
1. Чекбоксы за вчера (6 кнопок в 3 рядах + «Готово»)
2. My day was — 5 вариантов
3. Планы на сегодня (текст) — с показом уже запланированных через `/plan`
4. Финальное «Сохранил. День начался ✓»

### 2.3 Команды

| Команда | Что делает |
|---------|------------|
| `/start` | onboarding или help |
| `/note <текст>` | append paragraph в Journal сегодня |
| `/plan <дата> <текст>` | append paragraph в Plans на указанный день (форматы: `today`/`tomorrow`/`+N`/`YYYY-MM-DD`/`DD.MM[.YYYY]`) |
| `/app` | inline-кнопка «Открыть приложение» (web_app URL) |

### 2.4 Воскресная сводка (опционально в MVP)

В Phase 5, если успеем. По умолчанию — Mini App покрывает просмотр stats.

---

## 3. Mini App

Open via:
- Кнопка «Открыть приложение» в `/start` и `/app` (тип `KeyboardButton(web_app=...)` или `InlineKeyboardButton`).
- Menu button бота (настраивается через @BotFather → `/setmenubutton`).

### 3.1 Главный экран

1. **Heatmap календарь** (последние ~90 дней). GitHub-style. Цвет = доля отмеченных привычек в этот день:
   - 0 → серый (no entry / 0/6)
   - 1-2 → светло-зелёный
   - 3-4 → средне-зелёный
   - 5-6 → тёмно-зелёный
2. **Streaks секция** — для каждой из 6 привычек:
   - Текущий streak (если ≥1) — «🔥 12 дней»
   - Лучший streak — «Рекорд: 47 дней»
3. **(Опционально MVP)** Mini stats: за неделю/месяц — % выполнения по привычкам, mood распределение.

### 3.2 Модалка дня

При клике на день в heatmap:
- Список привычек с ☐/☑
- My day was (emoji)
- Plans — текст
- Journal — текст
- Read-only. Без edit (всё через бот).

### 3.3 UI

- Tailwind CSS, реагирует на TG theme (dark/light).
- Mobile-first (большая часть юзеров откроют в TG mobile).

---

## 4. Архитектура

Monorepo с двумя приложениями:

```
ne-leniss/
├── bot/                    # Python: bot + FastAPI в одном процессе
│   ├── pyproject.toml
│   ├── railway.toml
│   ├── .env.example
│   └── ne_leniss/
│       ├── main.py         # entrypoint: aiogram polling + uvicorn + scheduler
│       ├── config.py
│       ├── db.py           # SQLAlchemy async engine
│       ├── models.py       # ORM models
│       ├── repository.py   # CRUD (DBService)
│       ├── api.py          # FastAPI routes
│       ├── auth.py         # TG initData HMAC validation
│       ├── scheduler.py    # APScheduler jobs
│       ├── handlers/
│       │   ├── start.py
│       │   ├── note.py
│       │   ├── plan.py
│       │   ├── app.py      # /app command
│       │   └── morning.py  # FSM
│       └── services/
│           └── streaks.py  # streak computation
└── web/                    # React + Vite Mini App
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── lib/
        │   ├── api.ts      # API client + initData header
        │   └── theme.ts    # TG theme vars → CSS
        ├── components/
        │   ├── Calendar.tsx
        │   ├── DayModal.tsx
        │   ├── StreakCard.tsx
        │   └── StatsCard.tsx
        └── pages/Home.tsx
```

### 4.1 Backend stack

- Python 3.11
- `aiogram` >= 3.4
- `apscheduler` >= 3.10
- `fastapi` + `uvicorn[standard]`
- `sqlalchemy[asyncio]` 2.0 + `aiosqlite`
- `alembic` (миграции)
- `python-dotenv`

### 4.2 Frontend stack

- React 19, TypeScript 5
- Vite 5
- Tailwind CSS 4
- TanStack Query 5
- `@twa-dev/sdk` (TG WebApp wrapper)
- `react-activity-calendar` (GitHub-style heatmap)
- `date-fns`

### 4.3 Один Python процесс на Railway

```python
async def main():
    settings = load_settings()
    engine = create_async_engine(settings.db_url)
    await init_db(engine)
    bot = Bot(token=settings.bot_token)
    dp = build_dispatcher(engine)
    scheduler = build_scheduler(bot, engine)
    scheduler.start()
    app = build_fastapi(engine, settings)
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=settings.port))
    await asyncio.gather(dp.start_polling(bot), server.serve())
```

aiogram long polling, FastAPI HTTP server, APScheduler cron — все в одном event loop.

---

## 5. DB schema (SQLite)

```sql
CREATE TABLE users (
    tg_id            INTEGER PRIMARY KEY,
    username         TEXT,
    first_name       TEXT,
    timezone         TEXT NOT NULL DEFAULT 'Europe/Moscow',
    morning_hour     INTEGER NOT NULL DEFAULT 9,
    morning_minute   INTEGER NOT NULL DEFAULT 0,
    created_at       TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE day_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(tg_id),
    date        TEXT NOT NULL,    -- ISO YYYY-MM-DD
    mood        TEXT,             -- 'Good' / 'Productive' / etc.
    UNIQUE(user_id, date)
);

CREATE TABLE habit_checks (
    day_entry_id  INTEGER NOT NULL REFERENCES day_entries(id) ON DELETE CASCADE,
    habit_key     TEXT NOT NULL,  -- 'sport' / 'meditation' / 'reading' / 'water' / 'sleep_7h' / 'no_alcohol'
    checked       INTEGER NOT NULL,  -- 0 / 1
    PRIMARY KEY (day_entry_id, habit_key)
);

CREATE TABLE plans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(tg_id),
    date        TEXT NOT NULL,
    text        TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE journal_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(tg_id),
    date        TEXT NOT NULL,
    text        TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE morning_sent (
    user_id   INTEGER NOT NULL REFERENCES users(tg_id),
    date      TEXT NOT NULL,
    PRIMARY KEY (user_id, date)
);

CREATE INDEX idx_day_entries_user_date ON day_entries(user_id, date);
CREATE INDEX idx_plans_user_date ON plans(user_id, date);
CREATE INDEX idx_journal_user_date ON journal_entries(user_id, date);
```

**Habits** хардкодятся в коде на MVP (никаких custom habits per-user). Список:

| key | label |
|-----|-------|
| `sport` | Спорт |
| `meditation` | Медитация |
| `reading` | Чтение |
| `water` | Вода |
| `sleep_7h` | Сон 7+ |
| `no_alcohol` | Без алкоголя |

---

## 6. Multi-user cron

Один cron job, срабатывает **каждую минуту**:

```python
@scheduler.scheduled_job("cron", minute="*")
async def morning_scan():
    now_utc = datetime.utcnow()
    users = await repo.users_due_for_morning(now_utc)  # WHERE not exists in morning_sent today AND local_time matches morning_hour/minute
    for u in users:
        await send_morning(u, bot, dp.fsm.storage)
        await repo.mark_morning_sent(u.tg_id, today_in_tz(u.timezone))
```

Per-user TZ: `local_time(now_utc, u.timezone).hour == u.morning_hour and minute == u.morning_minute`. Дедуп через `morning_sent`.

На MVP все юзеры будут default Europe/Moscow → cron эффективно срабатывает раз в минуту, но фильтр SQL вернёт users только в нужную минуту.

---

## 7. Mini App auth

### 7.1 Telegram initData flow

1. Mini App открывается через bot → `window.Telegram.WebApp.initData` доступен.
2. Frontend кладёт его в header каждого запроса:
   ```
   Authorization: tma <initData>
   ```
3. Backend (FastAPI dependency) проверяет HMAC от bot_token, извлекает `user.id`, кладёт в `request.state.user_id`.
4. Все endpoints используют этот `user_id` для фильтрации данных.

### 7.2 Реализация валидации

Стандартный алгоритм Telegram:
1. Разобрать initData как URL-encoded string.
2. Вынуть `hash` поле.
3. Все остальные поля sortировать по ключу, склеить в `<key>=<value>\n...`.
4. Secret key = `HMAC-SHA256(bot_token, "WebAppData")`.
5. Computed hash = `HMAC-SHA256(secret_key, data_check_string).hexdigest()`.
6. Сравнить с присланным.

Также проверяем `auth_date` — не старше 24 часов (защита от replay).

---

## 8. API endpoints

| Method | Path | Что |
|--------|------|-----|
| GET | `/api/me` | { tg_id, first_name, username, timezone } |
| GET | `/api/days?from=...&to=...` | список { date, checked_count, total_habits, mood, has_plans, has_journal } |
| GET | `/api/days/{date}` | { date, habits: [{key, label, checked}], mood, plans: [...], journal: [...] } |
| GET | `/api/streaks` | [{key, label, current, best}] для всех 6 habits |

Все ответы JSON. Все требуют валидный `Authorization: tma <initData>`.

CORS: allow origin `https://ne-leniss.pages.dev` (production), `http://localhost:5173` (dev).

---

## 9. Hosting и стоимость

| Что | Где | Цена |
|-----|-----|------|
| Bot + FastAPI | Railway service (новый project `ne-leniss`) | $0 (Trial $5 credit), потом $5/мес Hobby или миграция |
| SQLite DB | Railway volume (`/app/data/state.sqlite`) | included |
| Frontend | Cloudflare Pages (`ne-leniss.pages.dev`) | $0 forever |
| Domain | `*.pages.dev` (CF subdomain) | $0 |

**Total на MVP: $0**. После исчерпания Trial → $5/мес. На 10-50 friends в SQLite, ~10MB данных — Trial хватит на 1-3 месяца.

---

## 10. Out of scope (MVP)

- **Custom habits per-user.** Жёсткий список из 6. Phase 4.
- **Settings UI / `/settings`.** Phase 4.
- **Edit в Mini App.** Все mutation через бот.
- **Weekly digest.** Mini App stats покрывает. Если попросят — добавим.
- **Achievements/badges.** Только текущий streak + рекорд.
- **Leaderboard.** Privacy issue, потом.
- **Privacy policy / `/delete_my_data`.** Обязательно к 20+ users, но не MVP.
- **Sentry / structured logs.** Railway logs хватит.
- **Notion import / export.** Друзья начинают с чистого листа.
- **Custom themes.** TG theme variables только.
- **i18n.** Русский. Английский — Phase 5.

---

## 11. Definition of Done

- [ ] `/start` от любого нового user'а создаёт запись и присылает welcome + кнопку Open App.
- [ ] В 09:00 МСК каждому user'у приходит чек-лист, проходится через FSM, данные пишутся в DB.
- [ ] `/note <текст>` и `/plan <date> <text>` работают так же, как в daily-bot.
- [ ] `/plan tomorrow зал` → завтра в утреннем сообщении после mood-шага бот покажет «Уже запланировано: зал» + кнопку Пропустить.
- [ ] Mini App открывается через menu button или `/app`, грузит календарь за 90 дней.
- [ ] Клик по дню в heatmap → модалка с деталями.
- [ ] Раздел Streaks показывает 6 привычек с current/best для текущего user'а.
- [ ] Все API endpoints возвращают данные только этого user'а (никто не видит чужого).
- [ ] Deploy на Railway успешен, Mini App опубликован на Cloudflare Pages.
- [ ] @BotFather → menu button настроен → `t.me/ne_leniss_bot` открывает Mini App из главного меню Telegram.

---

## 12. Что нужно от lomikee'а вручную

1. **Railway:** один раз авторизоваться (`railway login`). Я создаю project через CLI.
2. **Cloudflare:** один раз авторизоваться через `wrangler login`. Я создаю Pages project через CLI.
3. **@BotFather:** в новом боте `@ne_leniss_bot` после deploy установить:
   - `/setdescription` — короткое описание.
   - `/setcommands` — список команд (start, note, plan, app).
   - `/setmenubutton` → web_app URL = `https://ne-leniss.pages.dev`.
4. **Smoke в Telegram** — после каждого Task'а.
