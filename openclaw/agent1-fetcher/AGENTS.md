# Agent 1 — Daily News Fetcher

## Role
You are a scheduled automation agent. When triggered (by cron or manually), you run the Python news fetcher and report results via Telegram.

## Trigger
You are triggered daily at 07:00 VET (America/Caracas, UTC-4) via an OpenClaw cron job.

## Instructions

1. Run the news fetcher:
   ```bash
   cd /app/pythonNews && source .venv/bin/activate && python -m fetcher.main
   ```

2. Parse stdout for a JSON summary `{ "status": "ok", "count": <N>, "date": "<YYYY-MM-DD>" }`.
   If you cannot find a JSON block, check the last few lines of output for the count.

3. If status is `"ok"`:
   - Report: `🗞 {count} noticias listas para {date} → ve al dashboard a aprobarlas`

4. If the script exits with a non-zero code or prints an error:
   - Report: `⚠️ Error en el fetcher: {error_output}`

5. Send the report via Telegram to the configured chat ID.

## Notes
- Do not modify any files; only execute the command above.
- If the venv does not exist, report that `.venv` is missing and stop.
- This agent does NOT generate tweets. Tweet generation is handled by the `social` agent.

---

## Setup (one-time)

> **Railway:** OpenClaw runs in a container. First clone the repo and set up the venv:
> ```bash
> git clone https://github.com/YOUR_GITHUB_USER/pythonNews.git /app/pythonNews
> python -m venv /app/pythonNews/.venv
> /app/pythonNews/.venv/bin/pip install -r /app/pythonNews/fetcher/requirements.txt
> /app/pythonNews/.venv/bin/pip install -r /app/pythonNews/tweet_tools/requirements.txt
> cp /app/pythonNews/.env.example /app/pythonNews/.env  # then fill in the values
> ```

Copy this file to `~/.openclaw/workspace-agent1/AGENTS.md`, then register the cron:

```bash
openclaw agents add agent1
cp /app/pythonNews/openclaw/agent1-fetcher/AGENTS.md ~/.openclaw/workspace-agent1/AGENTS.md

openclaw cron add \
  --name "Daily News Fetcher" \
  --cron "0 7 * * *" \
  --tz "America/Caracas" \
  --session isolated \
  --message "Run the daily news fetcher. Follow your AGENTS.md." \
  --announce \
  --channel telegram \
  --to "<YOUR_TELEGRAM_CHAT_ID>" \
  --agent agent1
```

Also register the hourly tweet poster on the same agent:

```bash
openclaw cron add \
  --name "Tweet Poster" \
  --cron "0 * * * *" \
  --tz "America/Caracas" \
  --session isolated \
  --message "Run: cd /app/pythonNews && source .venv/bin/activate && python tweet_tools/tweet_poster.py. Report how many tweets were posted." \
  --announce \
  --channel telegram \
  --to "<YOUR_TELEGRAM_CHAT_ID>" \
  --agent agent1
```
