"""Backend-to-Supabase transport: Auth, PostgREST, and Storage over raw HTTP
with `httpx`, deliberately not `supabase-py`. A single-file upload and a
couple of REST calls do not justify pulling in supabase-py's five transitive
packages. See DEV-STATE.md § Decisions, story 1.2.

Every call here authenticates as the service role and therefore bypasses
RLS — this module IS the backend's privileged write path. The one exception
is `validate_bearer_token`, which deliberately uses the caller's own token
(never the service key) against `/auth/v1/user`, because its entire purpose
is finding out who the caller actually is.
"""

from __future__ import annotations

import httpx

from app.config import settings

_TIMEOUT = 15.0
_STORAGE_TIMEOUT = 30.0  # file bodies, not just JSON


class AuthTokenError(ValueError):
    """Raised when a bearer token is missing, malformed, or Supabase Auth
    rejects it. Callers translate this to HTTP 401."""


async def validate_bearer_token(authorization_header: str) -> str:
    """Resolves an `Authorization: Bearer <token>` header to the caller's
    `auth.users.id`, by asking Supabase Auth rather than trusting a
    client-supplied uid. This is the only way to populate `sessions.user_id`
    correctly: the backend connects with the service role, which bypasses
    RLS, so nothing else would stop it inserting a session for anyone.
    See PHASE-1-SPEC.md 1.2.
    """
    token = authorization_header.removeprefix("Bearer ").strip()
    if not token:
        raise AuthTokenError("Missing bearer token.")

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {token}"},
        )
    if resp.status_code != 200:
        raise AuthTokenError(f"Invalid or expired session token ({resp.status_code}).")

    user_id = resp.json().get("id")
    if not user_id:
        raise AuthTokenError("Could not resolve a user from the provided token.")
    return user_id


def _service_headers(*, json: bool = False) -> dict[str, str]:
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    if json:
        headers["Content-Type"] = "application/json"
    return headers


async def rest_insert(table: str, payload: dict) -> dict:
    """Inserts one row as the service role (bypasses RLS) and returns it.
    `Prefer: return=representation` is what makes PostgREST hand the row
    back instead of an empty 201 body."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{settings.supabase_url}/rest/v1/{table}",
            headers={**_service_headers(json=True), "Prefer": "return=representation"},
            json=payload,
        )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if isinstance(rows, list) else rows


async def rest_select_one(table: str, column: str, value: str, *, select: str = "*") -> dict | None:
    """One row matching `column = value`, or None if there is no match or the
    value is malformed (e.g. not a valid uuid — PostgREST returns 400 for
    that, which reads identically to "not found" for our purposes here)."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            f"{settings.supabase_url}/rest/v1/{table}",
            headers=_service_headers(),
            params={column: f"eq.{value}", "select": select},
        )
    if resp.status_code == 400:
        return None
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


async def rest_update(table: str, column: str, value: str, payload: dict) -> None:
    """Updates every row matching `column = value` as the service role
    (bypasses RLS). No return value -- every caller today (writing
    `resumes.profile` and `sessions.level`) already has the value it wrote
    and has no use for PostgREST echoing the row back."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.patch(
            f"{settings.supabase_url}/rest/v1/{table}",
            headers=_service_headers(json=True),
            params={column: f"eq.{value}"},
            json=payload,
        )
    resp.raise_for_status()


class StorageError(RuntimeError):
    """Raised when a Supabase Storage call does not succeed. Callers
    translate this to HTTP 502 — the client's file was fine, our upstream
    storage call was not."""


async def upload_object(bucket: str, path: str, content: bytes, content_type: str) -> None:
    """Uploads to the private `resumes` bucket as the service role. The
    browser never receives a public URL — signed URLs, minted with the
    service key, are how a candidate's own resume would later be served
    back, but no route does that yet in this story."""
    async with httpx.AsyncClient(timeout=_STORAGE_TIMEOUT) as client:
        resp = await client.post(
            f"{settings.supabase_url}/storage/v1/object/{bucket}/{path}",
            headers={**_service_headers(), "Content-Type": content_type, "x-upsert": "true"},
            content=content,
        )
    if resp.status_code not in (200, 201):
        raise StorageError(f"upload to {bucket}/{path} failed: {resp.status_code} {resp.text}")


async def delete_object(bucket: str, path: str) -> None:
    """Best-effort cleanup for the case where the DB write after a successful
    upload fails — without this, a failed request would still leave an
    orphan object in storage. Failures here are swallowed deliberately: the
    caller is already handling a more important error, and this module's
    test suite verifies bucket residue independently."""
    async with httpx.AsyncClient(timeout=_STORAGE_TIMEOUT) as client:
        try:
            await client.delete(
                f"{settings.supabase_url}/storage/v1/object/{bucket}/{path}",
                headers=_service_headers(),
            )
        except httpx.HTTPError:
            pass
