"""
backend/main.py
FastAPI application entry point.

Run with:
    source .venv/bin/activate
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.generate import router as generate_router
from backend.routes.news import router as news_router
from backend.routes.tweets import router as tweets_router

load_dotenv()

logger = logging.getLogger("backend.scheduler")

app = FastAPI(
    title="UltraMare News API",
    description="News aggregation, approval, and tweet scheduling API",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Scrape log (in-memory, keyed by date string) ────────────────────────────
# Each entry: {scraped_at, duration_s, count, errors: [{source, url, error}]}
SCRAPE_LOG: dict[str, dict] = {}

# ── Scheduled fetcher ────────────────────────────────────────────────────────
def _send_telegram(text: str) -> None:
    """Fire-and-forget Telegram message. Silently ignores errors."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    import httpx
    try:
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as exc:
        logger.warning("Telegram notify failed: %s", exc)


def run_fetcher() -> None:
    """Run the news fetcher. Called by APScheduler daily at 06:00 VET."""
    import time as _time
    from datetime import datetime, timezone, date as date_type
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    t0 = _time.monotonic()
    try:
        from fetcher.main import run_with_errors
        items, errors = run_with_errors()
        count = len(items)

        # Insert directly into Supabase — no HTTP round-trip to self
        if items:
            from backend.database import get_supabase
            sb = get_supabase()
            inserted = 0
            skipped = 0
            for item in items:
                row = {
                    "date": item.get("date", date_type.today().isoformat()),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", ""),
                    "category": item.get("category", "general"),
                    "summary": item.get("summary"),
                    "image_url": item.get("image_url"),
                    "status": "pending",
                }
                try:
                    sb.table("news_items").insert(row).execute()
                    inserted += 1
                except Exception as exc:
                    err_str = str(exc)
                    if "duplicate" in err_str.lower() or "unique" in err_str.lower() or "23505" in err_str:
                        skipped += 1
                    else:
                        errors.append({"source": item.get("source", ""), "url": item.get("url", ""), "error": err_str})
            logger.info("Inserted %d, skipped %d duplicates.", inserted, skipped)

        duration = round(_time.monotonic() - t0, 1)
        SCRAPE_LOG[today] = {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "duration_s": duration,
            "count": count,
            "errors": errors,
        }
        logger.info("Scheduled fetcher completed: %d items in %.1fs.", count, duration)
        dashboard_url = os.getenv("DASHBOARD_URL", "https://frontend-ventech.web.app")
        error_summary = f"\n⚠️ {len(errors)} errores durante el scraping." if errors else ""
        _send_telegram(
            f"🗞 <b>{count} noticias scrapeadas</b>{error_summary}\n"
            f"Por favor apruébalas para generar los tweets de hoy:\n"
            f"{dashboard_url}"
        )
    except Exception as exc:
        duration = round(_time.monotonic() - t0, 1)
        from datetime import datetime, timezone
        SCRAPE_LOG[today] = {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "duration_s": duration,
            "count": 0,
            "errors": [{"source": "fetcher", "url": "", "error": str(exc)}],
        }
        logger.error("Scheduled fetcher failed: %s", exc)
        _send_telegram(f"⚠️ El fetcher falló: {exc}")


scheduler = AsyncIOScheduler(timezone="America/Caracas")
scheduler.add_job(
    run_fetcher,
    CronTrigger(hour=6, minute=0, timezone="America/Caracas"),
    id="daily_fetcher",
    name="Daily News Fetcher",
    replace_existing=True,
)


@app.on_event("startup")
async def startup_event():
    scheduler.start()
    logger.info("APScheduler started — fetcher runs daily at 06:00 VET.")


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown(wait=False)


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(generate_router)
app.include_router(news_router)
app.include_router(tweets_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/ping-openclaw")
async def ping_openclaw():
    """Debug: test connectivity to OpenClaw gateway."""
    import httpx
    gateway_url = os.getenv("OPENCLAW_GATEWAY_URL", "http://localhost:18789")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{gateway_url}/health")
            return {"ok": True, "status": resp.status_code, "url": gateway_url, "body": resp.text[:200]}
    except Exception as exc:
        return {"ok": False, "url": gateway_url, "error": str(exc)}


@app.post("/api/fetch-now")
def fetch_now():
    """Manually trigger the fetcher (for testing)."""
    import threading
    threading.Thread(target=run_fetcher, daemon=True).start()
    return {"status": "triggered"}


@app.get("/api/scrape-status")
def scrape_status(date: str | None = None):
    """Return last scrape log entry for a given date (defaults to today)."""
    from datetime import date as date_type
    target = date or date_type.today().isoformat()
    return SCRAPE_LOG.get(target, None)
