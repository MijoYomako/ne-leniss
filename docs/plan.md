# Ne Leniss — Implementation Plan

> Реализация по spec'е `docs/spec.md`. Пять задач, после каждой — smoke-проверка с evidence.

## Global Constraints

- Python 3.11, Node 22+ (для Vite/React).
- Все time/cron — через `ZoneInfo`.
- Habits хардкодятся в `bot/ne_leniss/habits.py` единым источником истины (imported to scheduler, handlers, API).
- Никаких секретов в репо. `.env` всегда в `.gitignore`.
- Initial commit делаем чистым (без personal IDs/tokens).
- Bot token, который дал lomikee, идёт в `.env`. После публикации на GitHub юзер ротирует в @BotFather (best practice) или не публикует репо как public до ротации.

## Before You Start

1. Bot уже зарегистрирован: `@ne_leniss_bot`. Token в `.env`.
2. Cloudflare аккаунт — у lomikee есть (бесплатный).
3. Railway аккаунт — уже залогинен с предыдущего проекта.

---

## Task 1 — Repo scaffold + DB + bot core

**Файлы:**
- Create: monorepo structure (см. spec §4)
- Create: `bot/pyproject.toml`, `bot/.env.example`, `bot/.gitignore`, `bot/railway.toml`
- Create: `bot/ne_leniss/{__init__.py, config.py, db.py, models.py, repository.py, habits.py, main.py}`
- Create: `bot/alembic/` (или ручная schema init на startup — для MVP проще `Base.metadata.create_all` после connect)

**Interfaces:**
- `config.Settings`: bot_token, db_url, port, webapp_url
- `models.User`, `models.DayEntry`, `models.HabitCheck`, `models.Plan`, `models.JournalEntry`, `models.MorningSent`
- `repository.Repository(session_factory)`: методы CRUD под все нужды handlers и API
- `habits.HABITS: list[tuple[str, str]]` — 6 пар (key, label)
- `main.main() -> None` — async entrypoint

### Steps

- [ ] **Step 1**: Создать структуру папок и `pyproject.toml`:
  ```toml
  [project]
  name = "ne-leniss"
  version = "0.1.0"
  requires-python = ">=3.11"
  dependencies = [
      "aiogram>=3.4",
      "apscheduler>=3.10",
      "fastapi>=0.115",
      "uvicorn[standard]>=0.30",
      "sqlalchemy[asyncio]>=2.0",
      "aiosqlite>=0.20",
      "python-dotenv>=1.0",
  ]
  [build-system]
  requires = ["hatchling"]
  build-backend = "hatchling.build"
  [tool.hatch.build.targets.wheel]
  packages = ["ne_leniss"]
  ```

- [ ] **Step 2**: `bot/.env.example` (без значений). `bot/.gitignore`: `.env`, `data/`, `__pycache__/`, `.venv/`, `dist/`, `*.egg-info/`, `.railway/`.

- [ ] **Step 3**: `bot/.env` локально, заполнить реальные `BOT_TOKEN`, `DB_URL=sqlite+aiosqlite:///data/state.sqlite`, `PORT=8000`, `WEBAPP_URL=http://localhost:5173` (на старте).

- [ ] **Step 4**: `bot/ne_leniss/config.py` — frozen Settings dataclass + `load_settings()`.

- [ ] **Step 5**: `bot/ne_leniss/habits.py` — список из 6 пар.

- [ ] **Step 6**: `bot/ne_leniss/db.py` — `create_async_engine(...)`, `async_sessionmaker`, `init_db(engine)` создающий схему.

- [ ] **Step 7**: `bot/ne_leniss/models.py` — SQLAlchemy ORM models.

- [ ] **Step 8**: `bot/ne_leniss/repository.py` — методы:
  - `get_or_create_user(tg_id, username, first_name, default_tz)` → User
  - `find_or_create_day_entry(user_id, date)` → id
  - `set_habit_checks(day_entry_id, checks: dict[str, bool])`
  - `set_mood(day_entry_id, mood: str)`
  - `append_plan(user_id, date, text)`
  - `append_journal(user_id, date, text)`
  - `read_plans_text(user_id, date) -> str`
  - `get_day_summary(user_id, date) -> dict | None`
  - `query_days_range(user_id, start, end) -> list[dict]`
  - `users_due_for_morning(now_utc) -> list[User]` (multi-user cron)
  - `was_morning_sent(user_id, date_iso)` / `mark_morning_sent(user_id, date_iso)`

- [ ] **Step 9**: `bot/ne_leniss/main.py` — пустой `async def main()` пока что: load settings, init DB, log "ready".

- [ ] **Step 10**: Venv + `pip install -e .` + smoke:
  ```bash
  cd bot && python3.11 -m venv .venv && source .venv/bin/activate && pip install -e .
  python -c "
  import asyncio
  from dotenv import load_dotenv; load_dotenv()
  from ne_leniss.config import load_settings
  from ne_leniss.db import create_async_engine_from_url, init_db
  from ne_leniss.repository import Repository
  async def main():
      s = load_settings()
      engine = create_async_engine_from_url(s.db_url)
      await init_db(engine)
      print('DB initialised:', s.db_url)
  asyncio.run(main())
  "
  ```
  Expected: `DB initialised: sqlite+aiosqlite:///data/state.sqlite`. Файл `data/state.sqlite` создан.

- [ ] **Step 11**: smoke repository:
  ```bash
  python -c "
  import asyncio
  from datetime import date
  from dotenv import load_dotenv; load_dotenv()
  from ne_leniss.config import load_settings
  from ne_leniss.db import create_async_engine_from_url, init_db, sessionmaker_from_engine
  from ne_leniss.repository import Repository
  async def main():
      s = load_settings()
      e = create_async_engine_from_url(s.db_url); await init_db(e)
      repo = Repository(sessionmaker_from_engine(e))
      u = await repo.get_or_create_user(42, 'test', 'Test', 'Europe/Moscow')
      e_id = await repo.find_or_create_day_entry(u.tg_id, date.today())
      await repo.set_habit_checks(e_id, {'sport': True, 'meditation': True, 'reading': False, 'water': True, 'sleep_7h': False, 'no_alcohol': True})
      await repo.set_mood(e_id, 'Productive')
      await repo.append_plan(u.tg_id, date.today(), 'зал в 19')
      print('Plans:', await repo.read_plans_text(u.tg_id, date.today()))
      print('Summary:', await repo.get_day_summary(u.tg_id, date.today()))
  asyncio.run(main())
  "
  ```
  Expected: видим plan текст и dict с checks/mood/has_plans.

- [ ] **Step 12**: `git init && git add -A && git commit -m "scaffold: monorepo, bot core, db schema"`.

---

## Task 2 — Bot handlers + scheduler + onboarding

**Файлы:**
- Create: `bot/ne_leniss/handlers/{start, note, plan, app, morning}.py`
- Create: `bot/ne_leniss/scheduler.py`
- Modify: `bot/ne_leniss/main.py` (полный entrypoint)

**Interfaces:**
- `handlers.start.router` — `/start` auto-register + welcome + Open App
- `handlers.note.router` — `/note <text>`
- `handlers.plan.router` — `/plan <date> <text>` (с парсером дат от текущего бота)
- `handlers.app.router` — `/app` для retrigger кнопки Open App
- `handlers.morning.router` — FSM + `send_morning_message(user_id)` для scheduler
- `scheduler.build_scheduler(bot, repo) -> AsyncIOScheduler` — per-minute scan

### Steps

- [ ] **Step 1**: `handlers/start.py` — на `/start`:
  - `get_or_create_user(tg_id, username, first_name, 'Europe/Moscow')`
  - Welcome message + InlineKeyboard «🚀 Открыть приложение» (web_app)

- [ ] **Step 2**: `handlers/note.py` — порт из daily-bot, но `notion` → `repo`. Использует TZ user'а:
  ```python
  user = await repo.get_user(message.from_user.id)
  today = datetime.now(ZoneInfo(user.timezone)).date()
  await repo.append_journal(user.tg_id, today, text)
  ```

- [ ] **Step 3**: `handlers/plan.py` — порт из daily-bot, такой же парсер дат. `repo.append_plan(user_id, target_date, text)`.

- [ ] **Step 4**: `handlers/app.py` — `/app` шлёт сообщение «Открой приложение» с inline web_app button.

- [ ] **Step 5**: `handlers/morning.py` — full FSM (checkboxes/mood/plans). Импорты habits из `habits.py` для динамического keyboard на 6 кнопок. `send_morning_message(user_id, bot, repo, storage)` для scheduler.

- [ ] **Step 6**: `scheduler.py`:
  ```python
  def build_scheduler(bot, repo, storage):
      sch = AsyncIOScheduler()
      @sch.scheduled_job("cron", minute="*")
      async def morning_scan():
          now_utc = datetime.now(timezone.utc)
          users = await repo.users_due_for_morning(now_utc)
          for u in users:
              await send_morning_message(u, bot, repo, storage)
              await repo.mark_morning_sent(u.tg_id, today_in_tz(u.timezone))
      return sch
  ```

- [ ] **Step 7**: `main.py` собирает всё. Smoke checks: `bot.get_me()`. Запуск polling + scheduler параллельно (FastAPI добавим в Task 3).

- [ ] **Step 8**: Локальный run + `/start` от lomikee'а в Telegram (тот же chat_id, но против @ne_leniss_bot):
  - Бот отвечает welcome, видим Open App кнопку (не работает пока — URL placeholder).
  - DB: новая строка в users.
  - `/note test` → appendится журнал. Проверка через repo.

- [ ] **Step 9**: Dev-команда `/trigger_morning` — как в текущем боте, для отладки flow.

- [ ] **Step 10**: Smoke FSM: `/trigger_morning` → 6 чекбоксов в 3 ряда + Готово → mood → планы. Все данные сохраняются в DB.

- [ ] **Step 11**: `git commit -m "feat(bot): handlers, fsm, multi-user scheduler"`.

---

## Task 3 — FastAPI + initData auth + endpoints

**Файлы:**
- Create: `bot/ne_leniss/api.py`, `bot/ne_leniss/auth.py`
- Modify: `bot/ne_leniss/main.py` — добавить uvicorn

### Steps

- [ ] **Step 1**: `auth.py` — функция `verify_init_data(init_data: str, bot_token: str) -> int | None` возвращает `user_id` или None.

- [ ] **Step 2**: `api.py` — FastAPI app с dependency `current_user_id`:
  ```python
  async def current_user_id(request: Request, settings: Annotated[Settings, Depends(get_settings)]) -> int:
      header = request.headers.get("Authorization", "")
      if not header.startswith("tma "):
          raise HTTPException(401)
      init_data = header.removeprefix("tma ")
      user_id = verify_init_data(init_data, settings.bot_token)
      if user_id is None:
          raise HTTPException(401)
      return user_id
  ```

- [ ] **Step 3**: Endpoints:
  - `GET /api/me` — user info из DB
  - `GET /api/days?from=&to=` — list days
  - `GET /api/days/{date}` — day detail
  - `GET /api/streaks` — current + best per habit

- [ ] **Step 4**: CORS middleware — `allow_origins=["http://localhost:5173", "https://ne-leniss.pages.dev"]`.

- [ ] **Step 5**: `services/streaks.py` — функция `compute_streaks(day_entries: list, habits: list) -> list[dict]`. Чистая, без I/O.

- [ ] **Step 6**: `main.py` запускает uvicorn параллельно с aiogram polling.

- [ ] **Step 7**: Локальный smoke:
  ```bash
  curl http://localhost:8000/api/me  # → 401
  # Для теста временно подменим dependency или используем `?debug_user_id=<my_tg>` в DEV
  ```
  Можно сделать `DEBUG_BYPASS_AUTH=1` env var, который тогда читает `?uid=<int>` без HMAC. Включаем только при `--reload`/local dev.

- [ ] **Step 8**: Unit-smoke `compute_streaks`:
  ```bash
  python -c "
  from datetime import date, timedelta
  from ne_leniss.services.streaks import compute_streaks
  today = date(2026, 6, 30)
  days = [{'date': (today - timedelta(days=i)).isoformat(), 'habits': {'sport': i < 5, 'water': True}} for i in range(10)]
  print(compute_streaks(days, [('sport', 'Спорт'), ('water', 'Вода')]))
  "
  ```
  Expected: `[{key:sport, current:5, best:5}, {key:water, current:10, best:10}]`

- [ ] **Step 9**: `git commit -m "feat(api): fastapi, initData auth, endpoints, streaks"`.

---

## Task 4 — React Mini App

**Файлы:**
- Create: `web/{package.json, vite.config.ts, tsconfig.json, tailwind.config.ts, postcss.config.js, index.html, .gitignore, .env.example}`
- Create: `web/src/{main.tsx, App.tsx, index.css, lib/{api.ts, tg.ts}, components/{Calendar.tsx, DayModal.tsx, StreakCard.tsx}, pages/Home.tsx}`

### Steps

- [ ] **Step 1**: scaffold через Vite:
  ```bash
  cd web && npm create vite@latest . -- --template react-ts
  npm install
  npm install @twa-dev/sdk @tanstack/react-query date-fns react-activity-calendar
  npm install -D tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  ```

- [ ] **Step 2**: Tailwind setup. CSS variables для TG theme:
  ```css
  :root {
    --tg-bg: var(--tg-theme-bg-color, #ffffff);
    --tg-text: var(--tg-theme-text-color, #000000);
    --tg-hint: var(--tg-theme-hint-color, #999999);
    --tg-button: var(--tg-theme-button-color, #3b82f6);
  }
  ```

- [ ] **Step 3**: `lib/tg.ts` — обёртка над WebApp SDK:
  ```ts
  import WebApp from '@twa-dev/sdk';
  WebApp.ready();
  export const initData = WebApp.initData;
  export const tgUser = WebApp.initDataUnsafe.user;
  ```

- [ ] **Step 4**: `lib/api.ts` — fetch wrapper, добавляет `Authorization: tma <initData>`. Тщательно обрабатывает 401.

- [ ] **Step 5**: `App.tsx` — `QueryClientProvider` + Routes (одна страница для MVP).

- [ ] **Step 6**: `pages/Home.tsx`:
  - useQuery `/api/me`, `/api/days?from=-89d&to=today`, `/api/streaks`
  - Calendar component
  - StreakCard list
  - On day click — DayModal

- [ ] **Step 7**: `Calendar.tsx` — heatmap последних 90 дней. Можно через `react-activity-calendar` или собственный CSS-grid (для контроля над цветами и поведением клика).

- [ ] **Step 8**: `DayModal.tsx` — открывается на клик, fetches `/api/days/{date}` и рендерит детали.

- [ ] **Step 9**: `StreakCard.tsx` — 6 карточек привычек с current/best.

- [ ] **Step 10**: Dev-mode smoke:
  ```bash
  npm run dev  # http://localhost:5173
  # В другом терминале backend в DEBUG_BYPASS_AUTH mode
  # Открываем http://localhost:5173?uid=<my_tg_id>
  ```
  Видим календарь, streaks, можно тыкать дни.

- [ ] **Step 11**: Production build: `npm run build` → `dist/`.

- [ ] **Step 12**: `git commit -m "feat(web): mini app — calendar, day detail, streaks"`.

---

## Task 5 — Deploy

**Файлы:**
- Modify: `bot/railway.toml`
- Modify: `web/wrangler.toml` (опционально, для CF Pages CLI)

### Steps

- [ ] **Step 1**: `bot/railway.toml`:
  ```toml
  [build]
  builder = "NIXPACKS"
  buildCommand = "pip install -e ."
  [deploy]
  startCommand = "python -m ne_leniss.main"
  restartPolicyType = "ALWAYS"
  ```

- [ ] **Step 2**: GitHub repo:
  ```bash
  cd "/Users/lomikee/Documents/Claude/Projects/Ne Leniss"
  gh repo create ne-leniss --public --source=. --description "Multi-user Telegram habit tracker with Mini App" --push
  ```

- [ ] **Step 3**: Railway:
  ```bash
  cd bot
  railway init --name ne-leniss
  railway add --service bot
  railway volume add --mount-path /app/data
  railway variables --set "BOT_TOKEN=…" --set "DB_URL=sqlite+aiosqlite:///app/data/state.sqlite" --set "PORT=8000" --set "WEBAPP_URL=https://ne-leniss.pages.dev"
  railway up --detach
  ```

- [ ] **Step 4**: Settings → Networking → Generate Domain (Railway public URL). Сохранить → нужен для CORS и Mini App API endpoint.

- [ ] **Step 5**: Cloudflare Pages:
  ```bash
  npm install -g wrangler
  wrangler login
  cd ../web
  echo "VITE_API_URL=https://<railway-domain>" > .env.production
  npm run build
  wrangler pages project create ne-leniss --production-branch=main
  wrangler pages deploy dist --project-name=ne-leniss --branch=main
  ```

- [ ] **Step 6**: Apply env to bot:
  ```bash
  cd ../bot
  railway variables --set "WEBAPP_URL=https://ne-leniss.pages.dev"
  railway redeploy
  ```

- [ ] **Step 7**: @BotFather setup:
  - `/setdescription` → «Бот для трекинга привычек. Утром чек-лист, mini-app с календарём и streaks.»
  - `/setcommands` → `start - запустить / помощь`, `note - заметка в журнал`, `plan - запланировать`, `app - открыть приложение`.
  - `/setmenubutton` → text «Открыть приложение», url `https://ne-leniss.pages.dev`.

- [ ] **Step 8**: Production smoke:
  - `/start` от lomikee — welcome + Open App. Тапнуть кнопку — открывается Mini App.
  - Mini App: my-id виден, календарь пустой (новый user).
  - `/trigger_morning` → пройти FSM. Обновить Mini App — день сегодня в календаре с цветом, клик → детали.
  - `/plan tomorrow тест` → завтра увидим в утреннем сообщении.
  - Streaks секция показывает 6 привычек с current=0 или 1.

- [ ] **Step 9**: Friends test:
  - lomikee пересылает ссылку `t.me/ne_leniss_bot` другу.
  - Друг → `/start` → видит welcome + Open App. Открывает — видит свой пустой календарь.
  - Утром следующего дня в 09:00 МСК у обоих приходит чек-лист.

- [ ] **Step 10**: `git commit -m "deploy: railway + cloudflare pages"`. Push на GitHub.

---

## Definition of Done

См. spec §11. Все галочки проставлены после Task 5.
