# Ne Leniss

Multi-user Telegram habit tracker with a Mini App. Sends a morning checklist
of 6 habits, asks for yesterday's mood, accepts plans for any future day,
journals free-form notes. Mini App shows a 90-day heatmap calendar and current
streaks per habit.

Bot: [@ne_leniss_bot](https://t.me/ne_leniss_bot)

## Stack

- **bot/** — Python 3.11, aiogram 3, FastAPI, APScheduler, SQLAlchemy 2 async,
  SQLite. One process: long polling + HTTP API + cron jobs.
- **web/** — React 19 + Vite + TypeScript + Tailwind + TanStack Query.
  Telegram Mini App auth via `initData` HMAC.

## Hosting

- Bot + API on Railway (`bot/railway.toml`).
- Frontend on GitHub Pages via GitHub Actions (`.github/workflows/deploy-web.yml`).
- SQLite database on a Railway volume at `/app/data/state.sqlite`.

## Local dev

```bash
# Bot + API
cd bot
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env  # fill BOT_TOKEN, set DEBUG_BYPASS_AUTH=1 for dev
python -m ne_leniss.main

# Mini App (in another terminal)
cd web
npm install
npm run dev   # http://localhost:5173 — uses ?uid=42 against backend
```

## Deploy (one-time)

Bot+API to Railway:

```bash
cd bot
railway init --name ne-leniss
railway add --service bot
railway volume add --mount-path /app/data
railway variables --set "BOT_TOKEN=..." --set "DB_URL=sqlite+aiosqlite:////app/data/state.sqlite" \
  --set "PORT=8000" --set "WEBAPP_URL=https://<your-gh-username>.github.io/ne-leniss/"
railway up
```

Frontend to GitHub Pages:

1. Push this repo to GitHub.
2. Settings → Pages → Source = GitHub Actions.
3. Set repo secret `VITE_API_URL` to your Railway public URL.
4. Push to `main` — workflow builds and deploys `web/`.

Hook up the Mini App in Telegram:

- @BotFather → bot → Bot Settings → Menu Button → set URL to your Pages URL.
- Or POST to Bot API `/setChatMenuButton` with `MenuButtonWebApp`.

## License

MIT
