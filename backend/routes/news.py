"""
backend/routes/news.py
News item endpoints:
  GET  /api/news                     — list news for a given date
  POST /api/news/batch               — bulk insert from fetcher
  GET  /api/news/approved            — approved items for a given date (for OpenClaw Agent 2)
  PATCH /api/news/{id}/status        — approve / reject / tweeeted
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from backend.database import get_supabase
from backend.models import (
    BatchRequest,
    BatchResponse,
    NewsItemIn,
    NewsItemOut,
    StatusPatch,
)

router = APIRouter(prefix="/api/news", tags=["news"])


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _to_db_row(item: NewsItemIn, today: str) -> dict:
    item_date = item.date or today
    return {
        "date": item_date,
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "category": item.category,
        "summary": item.summary,
        "image_url": item.image_url,
        "status": "pending",
    }


@router.get("", response_model=list[NewsItemOut])
def list_news(
    date_str: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD, defaults to today"),
):
    """Return all news items for a given day, newest first."""
    target_date = date_str or date.today().isoformat()
    sb = get_supabase()
    res = (
        sb.table("news_items")
        .select("*")
        .eq("date", target_date)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.post("/batch", response_model=BatchResponse)
def batch_insert(payload: BatchRequest):
    """
    Bulk-insert news items from the fetcher.
    Silently skips items whose URL already exists for that date (dedup via DB unique index).
    """
    sb = get_supabase()
    today = date.today().isoformat()
    rows = [_to_db_row(item, today) for item in payload.items if item.title and item.url]

    inserted = 0
    skipped = 0

    for row in rows:
        try:
            sb.table("news_items").insert(row).execute()
            inserted += 1
        except Exception as exc:
            # Unique constraint violation = duplicate URL for this date
            err_str = str(exc)
            if "duplicate" in err_str.lower() or "unique" in err_str.lower() or "23505" in err_str:
                skipped += 1
            else:
                # Re-raise unexpected errors
                raise HTTPException(status_code=500, detail=f"Insert error: {exc}") from exc

    return BatchResponse(inserted=inserted, skipped=skipped)


@router.get("/approved", response_model=list[NewsItemOut])
def get_approved(
    date_str: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD, defaults to today"),
):
    """Return approved news items for a day — called by OpenClaw Agent 2."""
    target_date = date_str or date.today().isoformat()
    sb = get_supabase()
    res = (
        sb.table("news_items")
        .select("*")
        .eq("date", target_date)
        .eq("status", "approved")
        .order("approved_at", desc=False)
        .execute()
    )
    return res.data


@router.patch("/{item_id}/status", response_model=NewsItemOut)
def update_status(item_id: UUID, patch: StatusPatch):
    """Approve, reject, or mark an item as tweeted."""
    sb = get_supabase()
    update: dict = {"status": patch.status}
    res = (
        sb.table("news_items")
        .update(update)
        .eq("id", str(item_id))
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="News item not found")
    return res.data[0]
