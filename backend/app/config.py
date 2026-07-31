"""Environment configuration. Fails loudly, naming every missing variable, at import time.

Loaded once when this module is first imported — deliberately not lazy, so a
misconfigured deploy fails before the first request instead of on the first
agent call, ten minutes into a demo.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List
from urllib.parse import urlsplit

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

# override=False (the library default, made explicit here): a variable already
# present in the process environment — e.g. injected by Render at deploy time,
# or set by a test harness — wins over whatever is in the .env file. .env is a
# local-dev convenience, never the source of truth in production.
load_dotenv(ENV_PATH, override=False)

# No single NVIDIA_MODEL var. fast / deep / backup are three separate roles:
# `thinking` is GLM-specific and Nemotron 3 rejects it with HTTP 400, so model
# choice is the latency-vs-quality lever instead of a request parameter.
# See DEV-STATE.md 2026-07-29.
REQUIRED_VARS = [
    # Groq replaced NVIDIA NIM on 2026-07-31. NVIDIA's endpoint returns None
    # from with_structured_output once the system prompt passes roughly
    # 1500-2800 characters, on all three of its models, which is the shape
    # every agent in this product uses. See DEV-STATE § Decisions 2026-07-31.
    "GROQ_API_KEY",
    "GROQ_BASE_URL",
    "GROQ_MODEL_FAST",
    "GROQ_MODEL_DEEP",
    "GROQ_MODEL_BACKUP",
    "SUPABASE_DB_URL",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "ALLOWED_ORIGINS",
    "LOG_LEVEL",
]


class ConfigError(RuntimeError):
    """Raised when required environment variables are missing or malformed.

    Always names the offending variable(s) — "config is broken" is not
    actionable at 23:00 the night before a demo, "NVIDIA_MODEL_DEEP" is.
    """


def _read_required() -> dict[str, str]:
    missing = [name for name in REQUIRED_VARS if not (os.environ.get(name) or "").strip()]
    if missing:
        raise ConfigError(
            "Missing required environment variable(s): " + ", ".join(missing) +
            f". Set them in {ENV_PATH} (see backend/.env.example for the full list)."
        )
    return {name: os.environ[name].strip() for name in REQUIRED_VARS}


def _check_db_url(db_url: str) -> None:
    """Session pooler only, port 5432.

    Transaction pooler (6543) recycles connections between transactions and
    breaks psycopg prepared statements with DuplicatePreparedStatement — a
    failure that surfaces mid-interview, not at startup, if it isn't caught
    here. The direct connection (db.<ref>.supabase.co) is IPv6-only and
    unreachable from Render's free tier; catching "not a pooler host" also
    catches that case.
    """
    parsed = urlsplit(db_url)
    if parsed.port == 6543:
        raise ConfigError(
            "SUPABASE_DB_URL uses port 6543 (the transaction pooler). This breaks "
            "LangGraph's checkpointer with DuplicatePreparedStatement once connections "
            "are reused. Use the session pooler on port 5432: "
            "postgresql://postgres.<ref>:<pw>@aws-<region>.pooler.supabase.com:5432/postgres"
        )
    if "pooler.supabase.com" not in (parsed.hostname or ""):
        raise ConfigError(
            f"SUPABASE_DB_URL host '{parsed.hostname}' is not a Supabase pooler host. "
            "The direct connection (db.<ref>.supabase.co) is IPv6-only and unreachable "
            "from Render's free tier. Use the session pooler on port 5432."
        )


@dataclass(frozen=True)
class Settings:
    groq_api_key: str
    groq_base_url: str
    groq_model_fast: str
    groq_model_deep: str
    groq_model_backup: str
    supabase_db_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    allowed_origins: List[str]
    log_level: str


def load_settings() -> Settings:
    """Reads and validates the environment. Called once at import time below,
    but exposed as a function so tests can call it inside a subprocess with a
    variable deliberately unset, without touching the real .env file."""
    values = _read_required()
    _check_db_url(values["SUPABASE_DB_URL"])
    origins = [o.strip() for o in values["ALLOWED_ORIGINS"].split(",") if o.strip()]
    if not origins:
        raise ConfigError("ALLOWED_ORIGINS is set but contains no usable origin.")
    return Settings(
        groq_api_key=values["GROQ_API_KEY"],
        groq_base_url=values["GROQ_BASE_URL"],
        groq_model_fast=values["GROQ_MODEL_FAST"],
        groq_model_deep=values["GROQ_MODEL_DEEP"],
        groq_model_backup=values["GROQ_MODEL_BACKUP"],
        supabase_db_url=values["SUPABASE_DB_URL"],
        supabase_url=values["SUPABASE_URL"],
        supabase_anon_key=values["SUPABASE_ANON_KEY"],
        supabase_service_role_key=values["SUPABASE_SERVICE_ROLE_KEY"],
        allowed_origins=origins,
        log_level=values["LOG_LEVEL"].upper(),
    )


settings = load_settings()
