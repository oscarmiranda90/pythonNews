"""
GitHub Trending scraper.
Scrapes https://github.com/trending (per language if configured) using
BeautifulSoup and returns repo info as normalised NewsItem dicts.
No API key required.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://github.com/trending"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_trending_page(html: str, language: str) -> list[dict]:
    """Parse a GitHub trending HTML page and extract repo data."""
    soup = BeautifulSoup(html, "html.parser")
    repos = soup.select("article.Box-row")

    items: list[dict] = []
    for repo in repos:
        try:
            # Full repo name: owner/name
            name_tag = repo.select_one("h2 a")
            if not name_tag:
                continue
            # href is like /owner/repo
            href = name_tag.get("href", "").strip()
            repo_url = f"https://github.com{href}"
            # Clean name: "  owner /\n  repo  " → "owner/repo"
            repo_name = " ".join(name_tag.get_text().split())

            # Description
            desc_tag = repo.select_one("p")
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            # Stars today
            stars_today_tag = repo.select_one("span.d-inline-block.float-sm-right")
            stars_today = ""
            if stars_today_tag:
                stars_today = stars_today_tag.get_text(strip=True)

            # Total stars
            total_stars_tag = repo.select_one('a[href$="/stargazers"]')
            total_stars = ""
            if total_stars_tag:
                total_stars = total_stars_tag.get_text(strip=True).replace(",", "").strip()

            # Language
            lang_tag = repo.select_one('span[itemprop="programmingLanguage"]')
            lang = lang_tag.get_text(strip=True) if lang_tag else language or "Unknown"

            summary_parts = []
            if description:
                summary_parts.append(description)
            if total_stars:
                summary_parts.append(f"⭐ {total_stars} stars")
            if stars_today:
                summary_parts.append(f"({stars_today})")
            if lang:
                summary_parts.append(f"[{lang}]")

            items.append({
                "title": f"{repo_name}",
                "url": repo_url,
                "source": "GitHub Trending",
                "category": "github",
                "summary": " • ".join(summary_parts) if summary_parts else repo_url,
                "image_url": None,
                "published": datetime.now(timezone.utc).isoformat(),
                "stars_today": stars_today,
                "language": lang,
            })
        except Exception as exc:
            logger.debug("Error parsing repo row: %s", exc)

    return items


def fetch_github_trending(config: dict) -> list[dict]:
    """
    Fetch GitHub trending repos based on config dict.
    Scrapes multiple language pages, merges, deduplicates, and caps at count.
    """
    enabled = config.get("enabled", True)
    if not enabled:
        logger.debug("GitHub trending is disabled, skipping.")
        return []

    count = config.get("count", 5)
    since = config.get("since", "daily")
    languages: list[str] = config.get("languages", [""])

    seen_urls: set[str] = set()
    all_items: list[dict] = []

    for lang in languages:
        params: dict[str, Any] = {"since": since}
        if lang:
            params["spoken_language_code"] = ""
            url = f"{BASE_URL}/{lang}"
        else:
            url = BASE_URL

        logger.info("Fetching GitHub Trending (lang=%r, since=%s)", lang or "all", since)
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("GitHub trending request failed (lang=%r): %s", lang, exc)
            time.sleep(1)
            continue

        items = _parse_trending_page(resp.text, lang)
        for item in items:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                all_items.append(item)

        time.sleep(1)  # polite delay between language pages

    # Sort by stars_today descending (best effort), then cap
    def stars_sort_key(item: dict) -> int:
        raw = item.get("stars_today", "")
        # "1,234 stars today" → 1234
        import re
        digits = re.sub(r"[^\d]", "", raw)
        return int(digits) if digits else 0

    all_items.sort(key=stars_sort_key, reverse=True)
    result = all_items[:count]
    logger.info("GitHub Trending: %d repos selected (from %d scraped)", len(result), len(all_items))
    return result
