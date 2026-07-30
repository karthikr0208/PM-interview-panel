"""FastAPI entrypoint. Scaffolding only — the real routes (/skeleton/*, /session/*,
/turn) arrive in stories 0.6 onward and Phase 1+. This file's only job right now
is to prove the app boots, serves /health, and enforces CORS.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="PM Interview Panel API")

# ALLOWED_ORIGINS is a comma-separated list in .env; config.py has already
# split and validated it. Wide open here would defeat the point of naming an
# allowlist at all.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
