"""
fetcher/main.py — News Fetcher Orchestrator
─────────────────────────────────────────────
Run manually or by OpenClaw Agent 1:
    python -m fetcher.main
    python fetcher/main.py

What it does:
  1. Loads sources.yaml config
  2. Fetches RSS, GitHub Trending, and Hacker News
  3. Deduplicates and caps to FETCH_MAX_ITEMS total
  4. Saves results to data/YYYY-MM-DD.json (local backup)
  5. POSTs the batch to the FastAPI backend → Supabase
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

# Allow running as `python fetcher/main.py` from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fetcher.sources.rss import fetch_all_rss
from fetcher.sources.github_trending import fetch_github_trending
from fetcher.sources.hackernews import fetch_hackernews

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fetcher.main")

# ── Config paths ──────────────────────────────────────────────────────────────
ENV_FILE = PROJECT_ROOT / ".env"
SOURCES_CONFIG = PROJECT_ROOT / "fetcher" / "config" / "sources.yaml"
DATA_DIR = PROJECT_ROOT / "data"


def load_config() -> dict:
    with open(SOURCES_CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def deduplicate(items: list[dict]) -> list[dict]:
    """Remove items sharing the same URL (keep first occurrence)."""
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(item)
    return unique


def enrich_with_date(items: list[dict], today: date) -> list[dict]:
    """Add the canonical fetch date to every item."""
    for item in items:
        item["date"] = today.isoformat()
    return items


def save_json(items: list[dict], today: date) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{today.isoformat()}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    logger.info("Saved %d items → %s", len(items), path)
    return path


def post_to_backend(items: list[dict], backend_url: str) -> bool:
    """POST the batch to the FastAPI backend. Returns True on success."""
    endpoint = f"{backend_url.rstrip('/')}/api/news/batch"
    payload = {"items": items}
    try:
        resp = requests.post(endpoint, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        logger.info(
            "Backend accepted: %d inserted, %d skipped (duplicates)",
            result.get("inserted", 0),
            result.get("skipped", 0),
        )
        return True
    except requests.exceptions.ConnectionError:
        logger.warning(
            "Backend not reachable at %s — items saved locally only.", endpoint
        )
        return False
    except requests.RequestException as exc:
        logger.error("Failed to POST to backend: %s", exc)
        return False


def run() -> tuple[list[dict], list[dict]]:
    load_dotenv(ENV_FILE)

    max_items = int(os.getenv("FETCH_MAX_ITEMS", "20"))
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    today = date.today()
    errors: list[dict] = []

    logger.info("═══ News Fetcher starting for %s ═══", today.isoformat())

    config = load_config()

    # ── 1. RSS ────────────────────────────────────────────────────────────────
    rss_sources = config.get("rss_sources", [])
    try:
        rss_items = fetch_all_rss(rss_sources)
    except Exception as exc:
        logger.error("RSS fetch failed: %s", exc)
        errors.append({"source": "RSS", "url": "", "error": str(exc)})
        rss_items = []

    # ── 2. GitHub Trending ────────────────────────────────────────────────────
    gh_config = config.get("github", {})
    try:
        github_items = fetch_github_trending(gh_config)
    except Exception as exc:
        logger.error("GitHub trending fetch failed: %s", exc)
        errors.append({"source": "GitHub Trending", "url": "https://github.com/trending", "error": str(exc)})
        github_items = []

    # ── 3. Hacker News ────────────────────────────────────────────────────────
    hn_config = config.get("hackernews", {})
    try:
        hn_items = fetch_hackernews(hn_config)
    except Exception as exc:
        logger.error("HackerNews fetch failed: %s", exc)
        errors.append({"source": "HackerNews", "url": "https://news.ycombinator.com", "error": str(exc)})
        hn_items = []

    # ── 4. Merge, deduplicate, cap ────────────────────────────────────────────
    # Order: GitHub first (high signal), then HN, then RSS
    combined = github_items + hn_items + rss_items
    unique = deduplicate(combined)
    final = enrich_with_date(unique[:max_items], today)

    logger.info(
        "Total: %d unique items (GitHub=%d, HN=%d, RSS=%d) — capped at %d",
        len(final),
        len(github_items),
        len(hn_items),
        len(rss_items),
        max_items,
    )

    # ── 5. Save JSON locally ──────────────────────────────────────────────────
    save_json(final, today)

    # ── 6. POST to backend ────────────────────────────────────────────────────
    post_to_backend(final, backend_url)

    logger.info("═══ Fetcher done ═══")
    return final, errors


def run_with_errors() -> tuple[list[dict], list[dict]]:
    """Like run() but always returns (items, errors) even on top-level failure."""
    try:
        return run()
    except Exception as exc:
        return [], [{"source": "fetcher", "url": "", "error": str(exc)}]


if __name__ == "__main__":
    items, _ = run()
    # Print summary to stdout so OpenClaw Agent 1 can read it
    print(json.dumps({"status": "ok", "count": len(items), "date": date.today().isoformat()}))
