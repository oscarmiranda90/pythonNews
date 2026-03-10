"""
RSS feed fetcher using feedparser.
Pulls articles from configured sources, normalises them into the shared
NewsItem dict schema, and deduplicates by URL.

Handles malformed/bozo feeds (e.g. Webedia CMS — Xataka, Genbeta) by
fetching raw bytes, stripping invalid XML control characters, and re-parsing.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

logger = logging.getLogger(__name__)

# Matches XML control characters that are illegal in XML 1.0
_INVALID_XML_CHARS = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f"
    r"\ud800-\udfff\ufffe\uffff]"
)

_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NewsFetcherBot/1.0)"
    ),
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
}


def _fetch_raw(url: str, timeout: int = 15) -> bytes | None:
    """Fetch raw feed bytes via requests. Returns None on error."""
    try:
        resp = requests.get(url, headers=_FETCH_HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.content
    except requests.RequestException as exc:
        logger.warning("HTTP fetch failed for %s: %s", url, exc)
        return None


def _clean_xml(raw: bytes) -> bytes:
    """Strip illegal XML 1.0 characters from raw feed bytes."""
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        text = raw.decode("latin-1", errors="replace")
    cleaned = _INVALID_XML_CHARS.sub("", text)
    return cleaned.encode("utf-8")


def _entry_to_item(entry: Any, source_name: str, category: str) -> dict:
    """Convert a feedparser entry into our normalised NewsItem dict."""
    # Title
    title = entry.get("title", "").strip()

    # URL — prefer the actual link, fall back to id
    url = entry.get("link") or entry.get("id", "")

    # Summary — strip HTML tags
    summary_raw = (
        entry.get("summary")
        or entry.get("description")
        or ""
    )
    summary = re.sub(r"<[^>]+>", "", summary_raw).strip()
    # Truncate long summaries
    if len(summary) > 400:
        summary = summary[:397] + "…"

    # Image URL — try media_thumbnail, then enclosures, then media_content
    image_url = None
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        image_url = entry.media_thumbnail[0].get("url")
    elif entry.get("enclosures"):
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/"):
                image_url = enc.get("url")
                break
    elif hasattr(entry, "media_content") and entry.media_content:
        image_url = entry.media_content[0].get("url")

    # Published date — normalise to ISO string
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_parsed:
        pub_dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
        published = pub_dt.isoformat()
    else:
        published = datetime.now(timezone.utc).isoformat()

    return {
        "title": title,
        "url": url,
        "source": source_name,
        "category": category,
        "summary": summary,
        "image_url": image_url,
        "published": published,
    }


def fetch_rss_source(source: dict) -> list[dict]:
    """
    Fetch and parse a single RSS source config dict.
    Strategy:
      1. Fetch raw bytes via requests (sets proper User-Agent, handles redirects)
      2. Strip invalid XML control characters (fixes Webedia CMS feeds: Xataka, Genbeta)
      3. Parse cleaned bytes with feedparser
      4. On any failure, log and return []
    Returns a list of normalised NewsItem dicts (up to max_items).
    """
    name = source["name"]
    url = source["url"]
    category = source.get("category", "general")
    max_items = source.get("max_items", 3)
    enabled = source.get("enabled", True)

    if not enabled:
        logger.debug("Source '%s' is disabled, skipping.", name)
        return []

    logger.info("Fetching RSS: %s", name)

    raw = _fetch_raw(url)
    if raw is None:
        return []

    cleaned = _clean_xml(raw)
    try:
        feed = feedparser.parse(cleaned)
    except Exception as exc:
        logger.warning("feedparser failed for '%s': %s", name, exc)
        return []

    if feed.bozo:
        if not feed.entries:
            logger.warning("Feed '%s' bozo error, no entries: %s", name, feed.bozo_exception)
            return []
        # Bozo but has entries — proceed (common with Webedia/CDN feeds)
        logger.debug("Feed '%s' bozo but has %d entries, continuing.", name, len(feed.entries))

    items: list[dict] = []
    for entry in feed.entries[:max_items]:
        try:
            item = _entry_to_item(entry, name, category)
            if item["title"] and item["url"]:
                items.append(item)
        except Exception as exc:
            logger.debug("Could not parse entry from '%s': %s", name, exc)

    logger.info("  → %d items from %s", len(items), name)
    return items


def fetch_all_rss(sources: list[dict], delay_seconds: float = 0.5) -> list[dict]:
    """
    Fetch all RSS sources sequentially (be polite to servers).
    Returns combined, deduplicated list of NewsItem dicts.
    """
    seen_urls: set[str] = set()
    all_items: list[dict] = []

    for source in sources:
        items = fetch_rss_source(source)
        for item in items:
            url = item["url"]
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_items.append(item)
        if items:
            time.sleep(delay_seconds)

    logger.info("RSS total: %d unique items from %d sources", len(all_items), len(sources))
    return all_items
