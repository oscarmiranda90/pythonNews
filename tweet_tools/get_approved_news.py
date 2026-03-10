"""
tweet_tools/get_approved_news.py — CLI helper for OpenClaw Agent 2
──────────────────────────────────────────────────────────────────
Fetches today's (or a given date's) approved news items from the backend
and prints them as JSON to stdout. OpenClaw Agent 2 runs this to know
which stories need tweets generated.

Usage:
    python tweet_tools/get_approved_news.py
    python tweet_tools/get_approved_news.py --date 2026-03-10

Output (stdout):
    JSON array of approved news items, e.g.:
    [
      {
        "id": "...",
        "title": "...",
        "url": "...",
        "source": "...",
        "category": "...",
        "summary": "..."
      },
      ...
    ]

Exit codes:
    0 — success (even if 0 items)
    1 — request failed or backend unreachable
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch approved news for a date")
    parser.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    try:
        resp = requests.get(
            f"{BACKEND_URL}/api/news/approved",
            params={"date": args.date},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)

    items = resp.json()
    # Output only the fields Agent 2 needs to generate tweets
    output = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "url": item.get("url"),
            "source": item.get("source"),
            "category": item.get("category"),
            "summary": item.get("summary"),
        }
        for item in items
    ]

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
