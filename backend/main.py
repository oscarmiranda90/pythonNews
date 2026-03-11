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

# ── Scheduled fetcher ────────────────────────────────────────────────────────
def run_fetcher() -> None:
    """Run the news fetcher. Called by APScheduler daily at 06:00 VET."""
    try:
        from fetcher.main import main as fetcher_main
        fetcher_main()
        logger.info("Scheduled fetcher completed successfully.")
    except Exception as exc:
        logger.error("Scheduled fetcher failed: %s", exc)


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


@app.post("/api/fetch-now")
def fetch_now():
    """Manually trigger the fetcher (for testing)."""
    import threading
    threading.Thread(target=run_fetcher, daemon=True).start()
    return {"status": "triggered"}
