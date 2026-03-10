"""
tweet_tools/tweet_poster.py — Scheduled tweet thread poster
────────────────────────────────────────────────────────────
Reads pending tweet threads from the backend (`GET /api/tweets/pending`)
and posts them to X (Twitter) via Tweepy OAuth 1.0a. Supports threads
(reply chaining). Reports success/failure back to the backend.

Requires in .env:
    X_API_KEY
    X_API_SECRET
    X_ACCESS_TOKEN
    X_ACCESS_TOKEN_SECRET
    BACKEND_URL=http://localhost:8000

Usage:
    python tweet_tools/tweet_poster.py           # post all pending now
    python tweet_tools/tweet_poster.py --dry-run # print threads, don't post
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import requests
import tweepy
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tweet_poster")

BACKEND_URL         = os.getenv("BACKEND_URL", "http://localhost:8000")
X_API_KEY           = os.getenv("X_API_KEY", "")
X_API_SECRET        = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN      = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "")


# ── Backend helpers ───────────────────────────────────────────────────────────

def get_pending_tweets() -> list[dict]:
    resp = requests.get(f"{BACKEND_URL}/api/tweets/pending", timeout=10)
    resp.raise_for_status()
    return resp.json()


def mark_posted(tweet_id: str, x_tweet_id: str, x_thread_ids: list[str]) -> None:
    requests.patch(
        f"{BACKEND_URL}/api/tweets/{tweet_id}/posted",
        json={"x_tweet_id": x_tweet_id, "x_thread_ids": x_thread_ids},
        timeout=10,
    ).raise_for_status()


def mark_failed(tweet_id: str, error_msg: str) -> None:
    requests.patch(
        f"{BACKEND_URL}/api/tweets/{tweet_id}/failed",
        params={"error_msg": error_msg[:500]},
        timeout=10,
    ).raise_for_status()


# ── Tweepy client ─────────────────────────────────────────────────────────────

def get_client() -> tweepy.Client:
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        logger.error(
            "Missing X API credentials. Set X_API_KEY, X_API_SECRET, "
            "X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET in .env"
        )
        sys.exit(1)
    return tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )


# ── Thread posting ────────────────────────────────────────────────────────────

def post_thread(client: tweepy.Client, tweets: list[str], dry_run: bool = False) -> list[str]:
    """
    Post a list of tweet texts as a thread (each reply to the previous).
    Returns list of posted tweet IDs in order.
    """
    posted_ids: list[str] = []
    reply_to: str | None = None

    for i, text in enumerate(tweets):
        if dry_run:
            label = "tweet" if i == 0 else f"reply {i}"
            print(f"  [{label}] {text}")
            posted_ids.append(f"dry-run-{i}")
            continue

        kwargs: dict = {"text": text}
        if reply_to:
            kwargs["in_reply_to_tweet_id"] = reply_to

        response = client.create_tweet(**kwargs)
        tweet_id = str(response.data["id"])
        posted_ids.append(tweet_id)
        reply_to = tweet_id
        logger.info("Posted tweet %s: %s", tweet_id, text[:60])

    return posted_ids


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Post pending tweet threads to X")
    parser.add_argument("--dry-run", action="store_true", help="Print tweets without posting")
    args = parser.parse_args()

    pending = get_pending_tweets()
    if not pending:
        logger.info("No pending tweets to post.")
        return

    logger.info("Found %d pending tweet thread(s).", len(pending))
    client = None if args.dry_run else get_client()

    for thread in pending:
        tweet_id = thread["id"]
        content: list[str] = thread.get("content", [])

        if not content:
            logger.warning("Thread %s has no content, skipping.", tweet_id)
            continue

        if args.dry_run:
            print(f"\n── Thread {tweet_id} ──")

        try:
            posted_ids = post_thread(client, content, dry_run=args.dry_run)
            if not args.dry_run:
                mark_posted(tweet_id, posted_ids[0], posted_ids)
                logger.info("Thread %s posted successfully (%d tweets).", tweet_id, len(posted_ids))
        except tweepy.TweepyException as exc:
            error = str(exc)
            logger.error("Failed to post thread %s: %s", tweet_id, error)
            if not args.dry_run:
                try:
                    mark_failed(tweet_id, error)
                except Exception as backend_exc:
                    logger.warning("Could not mark thread as failed: %s", backend_exc)
        except requests.RequestException as exc:
            logger.error("Backend error for thread %s: %s", tweet_id, exc)


if __name__ == "__main__":
    main()
