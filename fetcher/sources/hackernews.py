"""
Hacker News fetcher via Algolia HN Search API.
No API key required. Filters by keyword queries, recency, and minimum points.
https://hn.algolia.com/api
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

ALGOLIA_BASE = "https://hn.algolia.com/api/v1/search"


def _fetch_query(query: str, hours_back: int, min_points: int) -> list[dict]:
    """Fetch HN stories matching a single keyword query via Algolia."""
    import time as _time
    cutoff_ts = int(_time.time()) - hours_back * 3600

    params = {
        "query": query,
        "tags": "story",
        "numericFilters": f"created_at_i>{cutoff_ts},points>{min_points}",
        "hitsPerPage": 20,
    }

    try:
        resp = requests.get(ALGOLIA_BASE, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("HN Algolia request failed (query=%r): %s", query, exc)
        return []

    items: list[dict] = []
    for hit in data.get("hits", []):
        title = hit.get("title", "").strip()
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        points = hit.get("points", 0)
        num_comments = hit.get("num_comments", 0)
        author = hit.get("author", "")
        created_at = hit.get("created_at", "")

        # Prefer the story's own URL; if missing, use HN discussion link
        hn_url = f"https://news.ycombinator.com/item?id={hit.get('objectID')}"

        summary = f"🔥 {points} pts • 💬 {num_comments} comments • by {author}"

        if title and url:
            items.append({
                "title": title,
                "url": url,
                "source": "Hacker News",
                "category": "ai",
                "summary": summary,
                "image_url": None,
                "published": created_at or datetime.now(timezone.utc).isoformat(),
                "hn_url": hn_url,
                "points": points,
            })

    return items


def fetch_hackernews(config: dict) -> list[dict]:
    """
    Fetch top HN stories matching configured queries.
    Deduplicates by URL, sorts by points, caps at count.
    """
    enabled = config.get("enabled", True)
    if not enabled:
        logger.debug("HN fetcher is disabled, skipping.")
        return []

    count = config.get("count", 4)
    queries: list[str] = config.get("queries", ["AI", "LLM"])
    min_points: int = config.get("min_points", 50)
    hours_back: int = config.get("hours_back", 24)

    seen_urls: set[str] = set()
    all_items: list[dict] = []

    for query in queries:
        logger.info("Fetching HN stories for query=%r", query)
        items = _fetch_query(query, hours_back, min_points)
        for item in items:
            url = item["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                all_items.append(item)
        time.sleep(0.3)  # gentle rate limiting

    # Sort by points descending and cap
    all_items.sort(key=lambda x: x.get("points", 0), reverse=True)
    result = all_items[:count]
    logger.info("HN: %d stories selected (from %d fetched)", len(result), len(all_items))
    return result
