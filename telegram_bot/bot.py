"""
telegram_bot/bot.py — Daily news digest bot
─────────────────────────────────────────────
Sends a morning message every day at 07:00 Venezuela time (America/Caracas, UTC-4)
with a count of today's news and a link to the dashboard.

Run with:
    source .venv/bin/activate
    python telegram_bot/bot.py

For OpenClaw: run this as a long-lived background process (not a cron job).
It uses APScheduler internally to fire at the right time every day.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import date
from pathlib import Path

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# ── Setup ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("telegram_bot")

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID      = os.getenv("TELEGRAM_CHAT_ID", "")
BACKEND_URL  = os.getenv("BACKEND_URL", "http://localhost:8000")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:3000")

SEND_HOUR   = 7   # 07:00
SEND_MINUTE = 0
TIMEZONE    = "America/Caracas"  # UTC-4 (VET — Venezuela time)


def get_news_count(target_date: str) -> int:
    """Ask the backend how many items exist for a given date."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/api/news",
            params={"date": target_date},
            timeout=10,
        )
        resp.raise_for_status()
        return len(resp.json())
    except Exception as exc:
        logger.warning("Could not fetch news count: %s", exc)
        return 0


def build_message(count: int, today: str) -> str:
    """Build the Telegram message text."""
    if count == 0:
        return (
            "🗞 *¡Buenos días!*\n\n"
            "No se encontraron noticias nuevas para hoy. "
            "Verifica que el fetcher haya corrido correctamente.\n\n"
            f"📊 Dashboard: {DASHBOARD_URL}"
        )

    news_word = "noticia" if count == 1 else "noticias"
    return (
        f"🗞 *¡Aquí están las noticias del día\\!* 📰\n\n"
        f"📅 {today}\n"
        f"📌 *{count} {news_word}* listas para revisar\\.\n\n"
        f"👉 Abre el dashboard, aprueba las que quieres tuitear y presiona "
        f"*Generar tweets*\\.\n\n"
        f"🔗 {DASHBOARD_URL}"
    )


async def send_daily_digest() -> None:
    """Fetch count and send the morning Telegram message."""
    today = date.today().isoformat()
    logger.info("Sending daily digest for %s", today)

    count = get_news_count(today)
    message = build_message(count, today)

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode="MarkdownV2",
            disable_web_page_preview=False,
        )
        logger.info("Daily digest sent (%d items).", count)
    except TelegramError as exc:
        logger.error("Telegram send failed: %s", exc)


async def send_test_message() -> None:
    """Send an immediate test message to verify bot config."""
    today = date.today().isoformat()
    count = get_news_count(today)
    message = build_message(count, today)

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=message,
            parse_mode="MarkdownV2",
            disable_web_page_preview=False,
        )
        print(f"✓ Test message sent to chat {CHAT_ID} ({count} items today)")
    except TelegramError as exc:
        print(f"✗ Telegram error: {exc}")
        sys.exit(1)


async def main() -> None:
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set in .env")
        sys.exit(1)
    if not CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID is not set in .env")
        sys.exit(1)

    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        send_daily_digest,
        trigger=CronTrigger(
            hour=SEND_HOUR,
            minute=SEND_MINUTE,
            timezone=TIMEZONE,
        ),
        id="daily_digest",
        name="Daily news digest",
        replace_existing=True,
    )
    scheduler.start()

    next_run = scheduler.get_job("daily_digest").next_run_time
    logger.info(
        "Telegram bot started. Daily digest scheduled at %02d:%02d %s. Next run: %s",
        SEND_HOUR,
        SEND_MINUTE,
        TIMEZONE,
        next_run,
    )

    # Keep the event loop alive
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
        scheduler.shutdown()


if __name__ == "__main__":
    # Pass --test to send an immediate message and exit
    if "--test" in sys.argv:
        asyncio.run(send_test_message())
    else:
        asyncio.run(main())
