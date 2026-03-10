"""
backend/main.py
FastAPI application entry point.

Run with:
    source .venv/bin/activate
    uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.generate import router as generate_router
from backend.routes.news import router as news_router
from backend.routes.tweets import router as tweets_router

load_dotenv()

app = FastAPI(
    title="UltraMare News API",
    description="News aggregation, approval, and tweet scheduling API",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(generate_router)
app.include_router(news_router)
app.include_router(tweets_router)


@app.get("/health")
def health():
    return {"status": "ok"}
