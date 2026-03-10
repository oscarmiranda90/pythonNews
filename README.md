# AI News Pipeline

> Self-hosted daily news pipeline with a Kanban dashboard, Telegram digest, and automatic tweet posting.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is this?

A fully automated system that runs on your own machine or VPS and does five things:

1. **Fetches** ~25 news stories every day from RSS feeds, GitHub Trending, and Hacker News
2. **Stores** them in Supabase and shows them in a **Kanban dashboard** grouped by day
3. **Sends a Telegram message** every morning at 7am with a link to the dashboard
4. **Lets you approve** which stories are worth tweeting — right from the dashboard
5. **Posts tweet threads** to X (Twitter) for your approved stories via the X API

No paid services. No vendor lock-in. You own the data.

---

## Demo flow

```
06:30  python -m fetcher.main         # fetches ~25 stories → Supabase
07:00  Telegram bot fires             # "25 new stories ready — open dashboard"
       You open dashboard             # Kanban board, last 7 days
       You approve / reject stories   # one click per card
       You click "Generate tweets"    # your AI agent writes the threads
       python tweet_tools/tweet_poster.py  # posts to X
```

---

## Stack

| Layer | Tech |
|---|---|
| Database | [Supabase](https://supabase.com) (free tier works) |
| Backend API | FastAPI + Python 3.11+ |
| Dashboard | Next.js 14 + Tailwind CSS |
| Telegram bot | python-telegram-bot + APScheduler |
| Tweet poster | Tweepy (OAuth 1.0a) |
| AI tweet writer | [OpenClaw](https://openclaw.ai) (local AI agent gateway) |
| News sources | RSS feeds + GitHub Trending + Hacker News Algolia API |

---

## Architecture

```
[Fetcher] ─► Supabase ─► [FastAPI :8000]
                               │
                    ┌──────────┴──────────┐
             [Next.js :3000]        [Telegram bot]
             Kanban dashboard       fires at 07:00
                    │
             [AI agent / webhook]
             generates tweet threads
                    │
             [tweet_poster.py] ─► X (Twitter)
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- A free [Supabase](https://supabase.com) account
- A Telegram bot token (create one via [@BotFather](https://t.me/BotFather) in 2 minutes)
- An X (Twitter) Developer account with OAuth 1.0a keys _(only needed for tweet posting)_

---

## Quick start

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/news-pipeline.git
cd news-pipeline
```

### 2. Set up Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r fetcher/requirements.txt
pip install -r backend/requirements.txt
pip install -r telegram_bot/requirements.txt
pip install -r tweet_tools/requirements.txt
```

### 3. Set up the database

Go to your Supabase project → **SQL Editor** → paste and run the contents of `supabase/schema.sql`. This creates the `news_items` and `tweets` tables (one time only).

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

| Variable | Where to find it |
|---|---|
| `SUPABASE_URL` | Supabase → Project Settings → API |
| `SUPABASE_KEY` | Supabase → Project Settings → API → **service_role** key |
| `TELEGRAM_BOT_TOKEN` | Message [@BotFather](https://t.me/BotFather) → `/newbot` |
| `TELEGRAM_CHAT_ID` | Message your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` → copy `chat.id` |
| `DASHBOARD_URL` | URL where your dashboard is hosted (or `http://localhost:3000`) |
| `X_API_KEY` | [X Developer Portal](https://developer.twitter.com) → Your App → Keys and Tokens |
| `X_API_SECRET` | Same as above |
| `X_ACCESS_TOKEN` | Same as above (must have read+write permissions) |
| `X_ACCESS_TOKEN_SECRET` | Same as above |

### 5. Set up the frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SITE_NAME=My News Pipeline
NEXT_PUBLIC_DASHBOARD_URL=https://your-domain.com   # optional
```

### 6. Set up OpenClaw (AI tweet generation)

OpenClaw is a free, local AI agent gateway. It runs on your machine and is what writes the tweet threads when you click **Generar tweets**.

**a) Install and start the gateway**

Follow the [OpenClaw install guide](https://docs.openclaw.ai) — it runs a local server at `http://localhost:18789`.

**b) Create both agent workspaces**

```bash
openclaw agents add agent1
openclaw agents add social
```

**c) Copy the agent instructions**

```bash
cp openclaw/agent1-fetcher/AGENTS.md ~/.openclaw/workspace-agent1/AGENTS.md
cp openclaw/agent2-social/AGENTS.md ~/.openclaw/workspace-social/AGENTS.md
```

**d) Add your token to `.env`**

Find your hooks token in `~/.openclaw/openclaw.json` and add it to `.env`:

```
OPENCLAW_GATEWAY_URL=http://localhost:18789
OPENCLAW_HOOKS_TOKEN=<value of hooks.token in ~/.openclaw/openclaw.json>
OPENCLAW_TWEET_AGENT_ID=social
```

**e) Register the cron jobs** (optional — automates daily fetch + hourly tweet posting)

Replace `<YOUR_TELEGRAM_CHAT_ID>` with your chat ID, then run:

```bash
# Daily news fetcher at 07:00 VET
openclaw cron add \
  --name "Daily News Fetcher" \
  --cron "0 7 * * *" \
  --tz "America/Caracas" \
  --session isolated \
  --message "Run the daily news fetcher. Follow your AGENTS.md." \
  --announce --channel telegram --to "<YOUR_TELEGRAM_CHAT_ID>" \
  --agent agent1

# Hourly tweet poster
openclaw cron add \
  --name "Tweet Poster" \
  --cron "0 * * * *" \
  --tz "America/Caracas" \
  --session isolated \
  --message "Run: cd $(pwd) && source .venv/bin/activate && python tweet_tools/tweet_poster.py. Report how many tweets were posted." \
  --announce --channel telegram --to "<YOUR_TELEGRAM_CHAT_ID>" \
  --agent agent1
```

> **Without OpenClaw:** The dashboard still works fully — you can fetch, review, and post tweets manually. OpenClaw only adds AI-assisted thread writing.

---

## Running

Start each service in its own terminal from the project root:

```bash
# Terminal 1 — API backend
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Dashboard
cd frontend && npm run dev

# Terminal 3 — Telegram bot (long-running, fires daily at 07:00)
source .venv/bin/activate
python telegram_bot/bot.py
```

Send a test Telegram message immediately:

```bash
python telegram_bot/bot.py --test
```

---

## Daily workflow

### Fetch news

Run this once a day (e.g. schedule it with cron at 06:30):

```bash
source .venv/bin/activate
python -m fetcher.main
```

Saves stories to `data/YYYY-MM-DD.json` (local backup) and inserts them into Supabase.

### Review in dashboard

Open `http://localhost:3000`. You'll see a Kanban board with one column per day. Each card shows the story title, source, and category. Click **✓ Aprobar** to approve or **✗ Rechazar** to reject.

### Generate tweet threads

Once you've approved stories, click **Generar tweets** on the day column. The dashboard calls `POST /api/generate-tweets` on the backend, which proxies the request to your local OpenClaw `social` agent. The agent writes Spanish tweet threads and saves each one via `POST /api/tweets/schedule`.

You can also inspect what the agent will receive:

```bash
python tweet_tools/get_approved_news.py              # today
python tweet_tools/get_approved_news.py --date 2026-03-10
```

> Requires OpenClaw running with the `social` agent configured (see [Setup step 6](#6-set-up-openclaw-ai-tweet-generation)).

### Post to X

```bash
python tweet_tools/tweet_poster.py            # post all pending threads now
python tweet_tools/tweet_poster.py --dry-run  # preview without posting
```

---

## Customising news sources

All sources are in `fetcher/config/sources.yaml`. No code changes needed — just edit the YAML.

```yaml
rss_sources:
  - name: "My Custom Blog"
    url: "https://example.com/feed.xml"
    category: "ai"
    enabled: true
```

Set `enabled: false` to disable a source without deleting it.

**Default sources (16 active):**
- **AI / Tech:** TechCrunch AI, VentureBeat, The Verge, Wired, MIT Tech Review, Ars Technica, HuggingFace Blog, Google DeepMind, The Decoder
- **LATAM / Venezuela 🇻🇪:** Caraota Digital, Runrun.es, El Nacional, La Patilla, Hipertextual, FayerWayer, Enter.co, Genbeta, La Nación (ARG)
- **GitHub Trending:** Python, JavaScript, All languages
- **Hacker News:** AI, LLM, machine learning, SaaS, open source (min 50 points)

---

## Deploying on a VPS

```bash
# Clone and install (same as Quick start above)
git clone https://github.com/YOUR_USERNAME/news-pipeline.git
cd news-pipeline
# ... follow Quick start steps 2–5 ...

# Build frontend for production
cd frontend && npm run build && cd ..

# Run everything with screen or tmux (or use systemd units)
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
cd frontend && npm start &
cd .. && python telegram_bot/bot.py &
```

### nginx reverse proxy (optional)

```nginx
server {
    server_name news.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Then get free HTTPS: `sudo certbot --nginx -d news.your-domain.com`

### Schedule the fetcher with cron

```bash
crontab -e
# Fetch news every day at 06:30 local time
30 6 * * * cd /path/to/news-pipeline && .venv/bin/python -m fetcher.main >> logs/fetcher.log 2>&1
```

---

## Project structure

```
news-pipeline/
├── .env.example               ← copy to .env and fill in values
├── supabase/schema.sql        ← run once in Supabase SQL Editor
│
├── fetcher/                   ← news fetching scripts (Python)
│   ├── config/sources.yaml    ← edit this to add/remove sources
│   ├── sources/rss.py
│   ├── sources/github_trending.py
│   ├── sources/hackernews.py
│   └── main.py                ← python -m fetcher.main
│
├── backend/                   ← FastAPI REST API
│   ├── main.py                ← uvicorn backend.main:app --port 8000
│   ├── routes/news.py
│   └── routes/tweets.py
│
├── frontend/                  ← Next.js 14 Kanban dashboard
│   └── components/KanbanBoard.tsx
│
├── telegram_bot/
│   └── bot.py                 ← python telegram_bot/bot.py
│
├── tweet_tools/
│   ├── get_approved_news.py   ← JSON output for your AI agent
│   └── tweet_poster.py        ← posts threads to X
│
└── data/                      ← daily JSON backups (gitignored)
```

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/news?date=YYYY-MM-DD` | All news for a day |
| `POST` | `/api/news/batch` | Bulk insert (used by fetcher) |
| `GET` | `/api/news/approved?date=YYYY-MM-DD` | Approved stories only |
| `PATCH` | `/api/news/{id}/status` | Approve / reject / mark tweeted |
| `POST` | `/api/tweets/schedule` | Save a tweet thread |
| `GET` | `/api/tweets/pending` | Threads ready to post |
| `PATCH` | `/api/tweets/{id}/posted` | Mark thread as posted |
| `PATCH` | `/api/tweets/{id}/failed` | Log posting failure |
| `POST` | `/api/generate-tweets` | Proxy approved news to OpenClaw `social` agent |

---

## Contributing

Pull requests welcome. To add new news sources, edit `fetcher/config/sources.yaml` — no Python changes needed.

## License

[MIT](LICENSE)


---

## Architecture

```
[Fetcher] ──► Supabase ──► [FastAPI backend]
                                  │
                         ┌────────┴────────┐
                  [Next.js dashboard]   [Telegram bot]
                         │
                  [OpenClaw Agent 2]
                         │
                  [tweet_poster.py] ──► X (Twitter)
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase project (free tier works)
- Telegram bot token (from [@BotFather](https://t.me/BotFather))
- X Developer account with OAuth 1.0a keys (for posting)

---

## Setup

### Option A — Run locally on your Mac/Linux machine

### Option B — Deploy on a VPS (Ubuntu/Debian)

```bash
# On your server
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git news-pipeline
cd news-pipeline

# Python env
python3 -m venv .venv
source .venv/bin/activate
pip install -r fetcher/requirements.txt
pip install -r backend/requirements.txt
pip install -r telegram_bot/requirements.txt
pip install -r tweet_tools/requirements.txt

# Node env
cd frontend && npm install && npm run build && cd ..

# Configure
cp .env.example .env && nano .env        # fill in all values
cp frontend/.env.local.example frontend/.env.local  # if it exists, or edit directly

# Run backend (use screen/tmux or systemd to keep it alive)
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# Run frontend
cd frontend && npm start &

# Run Telegram bot
cd .. && source .venv/bin/activate
python telegram_bot/bot.py &
```

> **Tip:** For production use, put the backend behind nginx with a domain/HTTPS. See the [nginx config example](#nginx-optional) below.

---

### 1. Clone & create virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r fetcher/requirements.txt
pip install -r backend/requirements.txt
pip install -r telegram_bot/requirements.txt
pip install -r tweet_tools/requirements.txt
```

### 2. Supabase schema

Run `supabase/schema.sql` in your Supabase project's **SQL Editor** (one time only).

### 3. Environment variables

Copy `.env.example` to `.env` and fill in all values:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `SUPABASE_URL` | From Supabase → Project Settings → API |
| `SUPABASE_KEY` | Service role key (starts with `sb_secret_`) |
| `BACKEND_URL` | `http://localhost:8000` |
| `CORS_ORIGINS` | `http://localhost:3000,https://your-domain.com` |
| `FETCH_MAX_ITEMS` | Max news items per day (default: `25`) |
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `TELEGRAM_CHAT_ID` | Your personal or group chat ID |
| `DASHBOARD_URL` | `https://your-domain.com` |
| `X_API_KEY` | X Developer App — API Key |
| `X_API_SECRET` | X Developer App — API Secret |
| `X_ACCESS_TOKEN` | X Developer App — Access Token |
| `X_ACCESS_TOKEN_SECRET` | X Developer App — Access Token Secret |
| `OPENCLAW_GATEWAY_URL` | OpenClaw gateway URL (default: `http://localhost:18789`) |
| `OPENCLAW_HOOKS_TOKEN` | Value of `hooks.token` in `~/.openclaw/openclaw.json` |
| `OPENCLAW_TWEET_AGENT_ID` | OpenClaw agent ID for tweet generation (default: `social`) |

**How to get your Telegram Chat ID:** Message your bot, then visit:  
`https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `result[0].message.chat.id`

### 4. Frontend env

```bash
cp frontend/.env.local.example frontend/.env.local  # or edit directly
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` (the OpenClaw token is never needed in the frontend — the backend handles it).

### 5. Install frontend deps

```bash
cd frontend && npm install
```

---

## Running

Start all services (each in its own terminal, from project root):

```bash
# Terminal 1 — FastAPI backend
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Next.js dashboard
cd frontend && npm run dev

# Terminal 3 — Telegram bot (stays running, fires at 07:00 VET)
source .venv/bin/activate
python telegram_bot/bot.py
```

---

## Daily workflow

### Step 1 — Fetch news (run once/day, e.g. 06:30)

```bash
source .venv/bin/activate
python -m fetcher.main
```

Fetches ~25 items from RSS feeds, GitHub Trending, and Hacker News. Saves to `data/YYYY-MM-DD.json` and POSTs to the backend → Supabase.

### Step 2 — Telegram digest (automatic at 07:00 VET)

The bot sends a message to your chat with the item count and a link to the dashboard.

### Step 3 — Review in dashboard

Open `http://localhost:3000`. Use the Kanban board to **Approve** or **Reject** each story.

### Step 4 — Generate tweets

Click **Generar tweets** on a day column. The FastAPI backend proxies the request to your local OpenClaw `social` agent (your `OPENCLAW_HOOKS_TOKEN` never touches the browser). The agent reads the approved stories, writes Spanish tweet threads, and saves each one via `POST /api/tweets/schedule`.

Once done, the threads appear in the **Tweet Preview** dashboard at `http://localhost:3000/tweets`.

### Step 5 — Post tweets

```bash
source .venv/bin/activate
python tweet_tools/tweet_poster.py           # post all pending threads
python tweet_tools/tweet_poster.py --dry-run # preview without posting
```

---

## Sources

Edit `fetcher/config/sources.yaml` to add/remove/disable sources. No code changes needed.

**Active sources (16):** TechCrunch AI, VentureBeat, The Verge, Wired, MIT Tech Review, Ars Technica, HuggingFace Blog, Google DeepMind, The Decoder AI, Hipertextual, FayerWayer, Enter.co, Genbeta, Caraota Digital 🇻🇪, Runrun.es 🇻🇪, El Nacional 🇻🇪, La Patilla 🇻🇪, La Nación Arg 🇦🇷, GitHub Trending (Python/JS/All), Hacker News (AI/LLM queries)

---

## Project structure

```
pythonNews/
├── .env                        # secrets (never commit)
├── .env.example
├── .gitignore
├── supabase/
│   └── schema.sql              # run once in Supabase SQL Editor
├── fetcher/
│   ├── config/sources.yaml
│   ├── sources/rss.py
│   ├── sources/github_trending.py
│   ├── sources/hackernews.py
│   ├── main.py                 # python -m fetcher.main
│   └── requirements.txt
├── backend/
│   ├── main.py                 # uvicorn backend.main:app
│   ├── database.py
│   ├── models.py
│   ├── routes/news.py
│   ├── routes/tweets.py
│   ├── routes/generate.py      # POST /api/generate-tweets (OpenClaw proxy)
│   └── requirements.txt
├── frontend/                   # Next.js 14 + Tailwind
│   ├── app/
│   ├── components/
│   ├── lib/api.ts
│   └── package.json
├── telegram_bot/
│   ├── bot.py                  # python telegram_bot/bot.py
│   └── requirements.txt
├── tweet_tools/
│   ├── get_approved_news.py    # stdout JSON for OpenClaw Agent 2
│   ├── tweet_poster.py         # posts pending threads to X
│   └── requirements.txt
├── openclaw/
│   ├── agent1-fetcher/
│   │   └── AGENTS.md           # copy to ~/.openclaw/workspace-agent1/
│   └── agent2-social/
│       └── AGENTS.md           # copy to ~/.openclaw/workspace-social/
└── data/
    └── YYYY-MM-DD.json         # daily backup of fetched items
```

---

## nginx (optional)

If you're running on a VPS with a real domain, add this to your nginx config:

```nginx
# /etc/nginx/sites-available/news-pipeline
server {
    server_name news.your-domain.com;

    # Next.js dashboard
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Then run `certbot --nginx -d news.your-domain.com` for free HTTPS.

---

## Contributing

Pull requests welcome. To add new news sources, edit `fetcher/config/sources.yaml` — no Python changes needed.

## License

[MIT](LICENSE)
