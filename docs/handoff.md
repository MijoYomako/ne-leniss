# Ne Leniss — Handoff / Project State

**Дата состояния:** 2026-07-01
**Bot:** [@ne_leniss_bot](https://t.me/ne_leniss_bot)
**Repo:** https://github.com/MijoYomako/ne-leniss

Этот документ — снапшот того, что построено и что дальше, чтобы можно было продолжить со свежей сессией без потери контекста.

---

## Production endpoints

| Что | Где | Как деплоится |
|-----|-----|----------------|
| Bot + FastAPI | https://bot-production-ea95.up.railway.app | `railway up --detach` из `bot/` |
| Mini App | https://mijoyomako.github.io/ne-leniss/ | `cd web && npm run deploy` (build + push to `gh-pages` branch) |
| DB | SQLite на Railway volume `/app/data/state.sqlite` | автоматом при deploy |
| Menu button | type `commands` (стандартный список команд) | однократно через Bot API |
| Bot description | «У всех есть штуки, которые хочется делать регулярно...» | однократно через `setMyDescription` |

⚠️ **Workflow `.github/workflows/deploy-web.yml` не в git** — OAuth scope `workflow` не активирован. Деплой фронта = вручную `npm run deploy`. Если хочется автомата: `gh auth refresh -s workflow --hostname github.com` (interactive) → committed workflow.

---

## Что уже сделано

### Backend (bot + API)
- Multi-user, изоляция по `user_id`
- Онбординг FSM: welcome → habits input → auto-seed 7 прошлых дней → сразу утренний flow с «first run» текстами (без "Доброе утро", с congrats и pin в конце)
- `/note` и `/plan` — wizard-режим когда без аргумента (диалог с /cancel)
- `/plan` парсит: `today`, `tomorrow`, `+N`, `YYYY-MM-DD`, `DD.MM[.YYYY]`
- `/habits` — смена привычек. Прошлые дни сохраняют старые labels (через `habit_checks.label`), streaks считаются только по актуальным
- `/seed` (dev) — 7 дней прошлого, вчера/позавчера пустые
- `/reset_onboarding` — полный wipe данных (day_entries, plans, journal, morning_sent) + `habits_json=NULL`
- `/pin` — рe-pin закреплённого сообщения с web_app кнопкой
- Multi-user cron: per-minute scan `users_due_for_morning` по локальному TZ каждого user'а. Дедуп через `morning_sent`
- Notion API не используется (это Ne Leniss, не daily-bot). Notion остался только в отдельном daily-bot проекте
- 5 ротирующих финальных сообщений после плана (про /note, /plan, «планы уже в чате»). Ротация: `(day_ordinal + user_id) % 5`
- Seed логика гарантирует все 5 mood представлены в demo (deterministic diverse pool)

### Frontend (Mini App)
- Header: «Салют, {name}» + сегодняшние планы bullets
- Monthly calendar с `‹ ›` nav, today ring, X/N счётчик в ячейке
- Mode toggle: «По чекбоксам» / «По настроению»
- Mood colors: Good grass-green, Productive emerald, Could be better amber, Bad red, Relaxing sky
- DayModal: «День был» (не «Настроение»), цветной блок mood, plans как bullets, journal как карточки
- Streak cards: 6 (или N — по актуальным habits) с current + best. Fire emoji при current ≥ 3
- Auth: TG initData HMAC (24h freshness check). Bypass в dev через `?uid=N` при `DEBUG_BYPASS_AUTH=1`
- Читаю `window.Telegram.WebApp.initData` напрямую (без @twa-dev/sdk из-за race condition)

### Инфраструктура
- Railway project `ne-leniss` (separate от `daily-bot`)
- SQLite migration через `_migrate_sqlite_users` (idempotent ALTER TABLE)
- CORS origin вычисляется из `WEBAPP_URL` через `urlparse` (только scheme+netloc)
- Локальный dev: backend в `bot/` через `python -m ne_leniss.main`, frontend `cd web && npm run dev` (Vite proxy `/api → :8000`)

---

## Ключевые дизайн-решения (не переизобретать)

1. **Menu button = `commands`, не `web_app`.** Приложение открывается через `/app` команду или через pinned message с inline web_app кнопкой. Причина: юзеру важен доступ к списку команд по одному тапу.

2. **Онбординг seed = 7 дней, не 30.** Вчера + позавчера пустые чтобы streak не был fake. Каждый seed показывает все 5 mood (deterministic).

3. **Historical habit labels.** При `/habits` смене прошлые дни хранят свои старые labels в `habit_checks.label`. Streak компонент фильтрует только по current habits. Это осознанное решение lomikee'а.

4. **Один pin в шапке чата вместо inline-кнопки в congrats.** Убрали дубль двух кнопок «Открыть приложение».

5. **Тон = Мишок 🐻, разговорный.** Никогда не звучать как AI. См. `.claude` memory: `feedback-copy-voice`.

6. **/reset_onboarding — полный wipe.** Он же самый честный способ протестировать демо на своём аккаунте.

---

## Что дальше (когда lomikee захочет продолжать)

**Быстрое (наименьший риск, самая большая польза):**
- [ ] `/today` команда — вернуть сегодняшние планы + вчерашние чекбоксы. Кажется что это value prop про «не обязательно в приложении смотреть»
- [ ] Мелкая копирайт-полировка отдельных сообщений (обычно приходит с скринами)
- [ ] Fresh setMyShortDescription (сейчас старое: «Трекер привычек с календарём»)

**Среднее:**
- [ ] Мигриация SQLite → Postgres если растёт база (>50 users или >100MB)
- [ ] `/tz Europe/Berlin` команда для друзей из других TZ (сейчас все МСК)
- [ ] Weekly digest (воскресный) — есть шаблон в daily-bot, портировать
- [ ] Sentry integration когда пойдут первые баги

**Крупное (Phase 4+):**
- [ ] Публикация в @BotFather каталог — нужна privacy policy + `/delete_my_data` + `/export`
- [ ] Achievements/badges — Milestones типа «30 дней подряд без X»
- [ ] Leaderboard среди друзей (opt-in, privacy-осторожно)
- [ ] Custom habits с иконками / категориями

---

## Known issues (не критично, но помнить)

- Telegram Desktop кэширует `setChatMenuButton` и `setMyCommands` до 10 минут. Cmd+Q помогает.
- Rare `TelegramNetworkError: Request timeout` при long polling — aiogram переподключается сам через ~30 сек. В логах видно как WARNING → INFO Connection established.
- GH Pages build 1-3 минуты. Первый deploy после долгого молчания может быть дольше.

---

## Локальные commands cheatsheet

```bash
# Стать в проект
cd "/Users/lomikee/Documents/Claude/Projects/Ne Leniss"

# Backend local dev
cd bot && source .venv/bin/activate
python -m ne_leniss.main

# Frontend local dev
cd web && npm run dev  # http://localhost:5173?uid=42

# Deploy frontend
cd web && npm run deploy

# Deploy backend
cd bot && railway up --detach

# Смотреть prod bot logs
cd bot && railway logs --deployment

# Обновить bot description / commands / menu button
# см. bash snippets в git history (grep "setMyDescription" / "setMyCommands" / "setChatMenuButton")
```

---

## Как понять что состояние здорово

```bash
# API alive
curl -s https://bot-production-ea95.up.railway.app/api/healthz  # → {"ok":true}

# Frontend alive
curl -s -o /dev/null -w "%{http_code}\n" https://mijoyomako.github.io/ne-leniss/  # → 200

# Bot metadata alive
curl -s "https://api.telegram.org/bot<TOKEN>/getMe" | python3 -m json.tool
```

Всё работает если:
1. Логи в Railway показывают `Scheduler started (per-minute morning scan)` и morning_scan executed successfully каждую минуту
2. `/start` от нового TG аккаунта запускает онбординг
3. Открытие Mini App через menu button → grid дней, стрики загружаются
