"""
backend/routes/generate.py
POST /api/generate-tweets — proxy to OpenClaw Agent 2 (social).

The OpenClaw hooks token stays server-side; the browser never sees it.
"""
from __future__ import annotations

import json
import os

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{gateway_url}/hooks/agent",
                json=payload,
                headers={"Authorization": f"Bearer {hooks_token}"},
            )
            resp.raise_for_status()
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={"detail": f"OpenClaw gateway timed out at {gateway_url}."},
        )
    except httpx.ConnectError:
        return JSONResponse(
            status_code=502,
            content={"detail": f"Cannot reach OpenClaw gateway at {gateway_url}. Is it running?"},
        )
    except httpx.HTTPStatusError as exc:
        return JSONResponse(
            status_code=502,
            content={"detail": f"OpenClaw returned {exc.response.status_code}: {exc.response.text}"},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Unexpected error: {exc}"},
        )

    return {"ok": True, "agent": agent_id, "items": len(body.news), "date": body.date}
