"""
backend/routes/generate.py
POST /api/generate-tweets — proxy to OpenClaw Agent 2 (social).

The OpenClaw hooks token stays server-side; the browser never sees it.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class NewsPayloadItem(BaseModel):
    id: str
    title: str
    url: str
    summary: str | None = None
    category: str | None = None


class GenerateRequest(BaseModel):
    date: str
    news: list[NewsPayloadItem]


@router.post("/api/generate-tweets")
async def generate_tweets(body: GenerateRequest):
    gateway_url = os.getenv("OPENCLAW_GATEWAY_URL", "http://localhost:18789")
    hooks_token = os.getenv("OPENCLAW_HOOKS_TOKEN", "")
    agent_id = os.getenv("OPENCLAW_TWEET_AGENT_ID", "social")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not hooks_token:
        return JSONResponse(
            status_code=503,
            content={"detail": "OPENCLAW_HOOKS_TOKEN not configured — set it in Railway variables."},
        )

    news_block = json.dumps(
        [item.model_dump() for item in body.news],
        ensure_ascii=False,
        indent=2,
    )
    message = (
        f"@social\n\n"
        f"Fecha: {body.date}\n\n"
        f"NOTICIAS:\n{news_block}\n\n"
        "Genera threads de tweets en español para cada noticia según tu AGENTS.md "
        "y guárdalos vía POST /api/tweets/schedule."
    )

    payload: dict = {
        "message": message,
        "name": "TweetGenerator",
        "agentId": agent_id,
        "deliver": bool(chat_id),
    }
    if chat_id:
        payload["channel"] = "telegram"
        payload["to"] = chat_id

    # Fire-and-forget: return immediately, let OpenClaw run in background
    async def _fire() -> None:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{gateway_url}/hooks/agent",
                    json=payload,
                    headers={"Authorization": f"Bearer {hooks_token}"},
                )
                resp.raise_for_status()
                logger.info("OpenClaw accepted job for %s: %s", body.date, resp.text[:200])
        except Exception as exc:
            logger.error("OpenClaw fire-and-forget failed for %s: %s", body.date, exc)

    asyncio.create_task(_fire())
    return {"ok": True, "agent": agent_id, "items": len(body.news), "date": body.date}
