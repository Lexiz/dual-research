"""Supabase Auth middleware — spec 0021.

Replaces the spec-0020 HTTP Basic stopgap. Gates `/api/*` requests (except
the public `/api/health` and `/api/config` endpoints) by:

1. Extracting `Authorization: Bearer <access_token>`. 401 if missing.
2. Validating the token via `client.auth.get_user(token)`. 401 if invalid.
3. Checking the email against the `approved_emails` table. 403 if missing.

Validation results are cached in-memory for 60 seconds keyed on a SHA-256
hash of the token. The cache stores the (email, approved) tuple so both
"valid but not approved" and "valid and approved" are remembered.

Static paths (everything outside /api) are always public — the JSX bundle
has no secrets and the sign-in screen needs to render before the user has
a token. Local mode (RUNS_BACKEND=fs) never attaches this middleware.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send


UNGATED_API_PATHS = frozenset({"/api/health", "/api/config"})
DEFAULT_CACHE_TTL_SECONDS = 60.0


class SupabaseAuthMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        client: Any,
        *,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        self._app = app
        self._client = client
        self._ttl = cache_ttl_seconds
        # token_hash → (email_or_None, approved, is_admin, expires_at)
        self._cache: dict[str, tuple[str | None, bool, bool, float]] = {}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if not path.startswith("/api/") or path in UNGATED_API_PATHS:
            await self._app(scope, receive, send)
            return

        token = self._extract_token(scope)
        if not token:
            await _send_json(send, 401, {"error": "missing_token"})
            return

        email, approved, is_admin = self._validate(token)
        if email is None:
            await _send_json(send, 401, {"error": "invalid_token"})
            return
        if not approved:
            await _send_json(send, 403, {"error": "email_not_approved", "email": email})
            return

        scope = dict(scope)
        scope["user"] = {"email": email, "is_admin": is_admin, "token": token}
        await self._app(scope, receive, send)

    # ─── internals ────────────────────────────────────────────────────────

    def _extract_token(self, scope: Scope) -> str | None:
        for name, value in scope.get("headers", ()):
            if name == b"authorization":
                parts = value.decode("latin-1", "replace").strip().split(None, 1)
                if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1]:
                    return parts[1]
        return None

    def _validate(self, token: str) -> tuple[str | None, bool, bool]:
        """Return (email, approved, is_admin). email is None when invalid."""
        key = hashlib.sha256(token.encode("utf-8")).hexdigest()
        now = time.monotonic()

        hit = self._cache.get(key)
        if hit is not None:
            email, approved, is_admin, expires_at = hit
            if now < expires_at:
                return email, approved, is_admin
            del self._cache[key]

        email = _get_user_email(self._client, token)
        if email is None:
            self._cache[key] = (None, False, False, now + self._ttl)
            return None, False, False

        approved, is_admin = _email_status(self._client, email)
        self._cache[key] = (email, approved, is_admin, now + self._ttl)
        return email, approved, is_admin


def _get_user_email(client: Any, token: str) -> str | None:
    """Call supabase-py's auth.get_user(token); return the email or None."""
    try:
        result = client.auth.get_user(token)
    except Exception:
        return None
    user = getattr(result, "user", None) or result
    email = getattr(user, "email", None)
    if not email:
        return None
    return str(email).strip().lower() or None


def _email_status(client: Any, email: str) -> tuple[bool, bool]:
    """Return (approved, is_admin) for the given email."""
    try:
        res = (
            client.table("approved_emails")
            .select("email,is_admin")
            .eq("email", email)
            .limit(1)
            .execute()
        )
    except Exception:
        return False, False
    rows = res.data or []
    if not rows:
        return False, False
    return True, bool(rows[0].get("is_admin"))


async def _send_json(send: Send, status: int, body: dict[str, Any]) -> None:
    import json

    payload = json.dumps(body).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(payload)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": payload})
