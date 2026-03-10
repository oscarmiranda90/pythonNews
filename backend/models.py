"""
backend/models.py
Pydantic v2 models for request/response validation.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, HttpUrl, field_validator


# ── Inbound: item from the fetcher ────────────────────────────────────────────

class NewsItemIn(BaseModel):
    title: str
    url: str
    source: str
    category: str = "general"
    summary: Optional[str] = None
    image_url: Optional[str] = None
    published: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD; orchestrator sets this

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        allowed = {"ai", "github", "latam", "saas", "general"}
        return v if v in allowed else "general"


class BatchRequest(BaseModel):
    items: list[NewsItemIn]


# ── Outbound: item returned to dashboard ──────────────────────────────────────

class NewsItemOut(BaseModel):
    id: UUID
    date: date
    title: str
    url: str
    source: str
    category: str
    summary: Optional[str]
    image_url: Optional[str]
    status: str
    created_at: datetime
    approved_at: Optional[datetime]


class BatchResponse(BaseModel):
    inserted: int
    skipped: int


# ── Status patch ──────────────────────────────────────────────────────────────

class StatusPatch(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = {"pending", "approved", "rejected", "tweeted"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v


# ── Tweets ────────────────────────────────────────────────────────────────────

class TweetScheduleRequest(BaseModel):
    news_id: UUID
    content: list[str]          # thread: up to 5 tweets
    scheduled_at: Optional[datetime] = None


class TweetOut(BaseModel):
    id: UUID
    news_id: UUID
    content: list[str]
    scheduled_at: Optional[datetime]
    posted_at: Optional[datetime]
    x_tweet_id: Optional[str]
    x_thread_ids: Optional[list[str]]
    status: str
    error_msg: Optional[str]
    created_at: datetime


class TweetPostedPatch(BaseModel):
    x_tweet_id: str
    x_thread_ids: Optional[list[str]] = None
    posted_at: Optional[datetime] = None
