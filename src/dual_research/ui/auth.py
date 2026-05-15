"""HTTP Basic auth middleware — stopgap until spec 0021 ships Google OAuth.

Active only when `UI_BASIC_AUTH_PASSWORD` is set in the environment. Local
invocations of `dual-research serve` don't set it, so they remain ungated.
Hosted (Fly) deployments set it via `fly secrets set`, so every request is
gated until the user provides credentials.

Username is hardcoded to `dual-research`. Password is the env var value.
Browsers cache Basic credentials per origin, so users authenticate once
per session. Spec 0021 removes this whole file.
"""

from __future__ import annotations

import base64
import hmac
from typing import Awaitable, Callable

from starlette.types import ASGIApp, Receive, Scope, Send


USERNAME = "dual-research"
REALM = "dual-research monitor"

# Paths that bypass the auth gate. /api/health is probed by Fly's machine
# health-checker without credentials, so a 401 there would mark the machine
# unhealthy and Fly would never serve real traffic.
UNGATED_PATHS = frozenset({"/api/health"})


class BasicAuthMiddleware:
    def __init__(self, app: ASGIApp, expected_password: str):
        self._app = app
        self._expected_password = expected_password

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        if scope.get("path") in UNGATED_PATHS or self._authorized(scope):
            await self._app(scope, receive, send)
            return

        await self._send_401(send)

    def _authorized(self, scope: Scope) -> bool:
        for name, value in scope.get("headers", ()):
            if name == b"authorization":
                return self._check(value.decode("latin-1", "replace"))
        return False

    def _check(self, header: str) -> bool:
        parts = header.strip().split(None, 1)
        if len(parts) != 2 or parts[0].lower() != "basic":
            return False
        try:
            decoded = base64.b64decode(parts[1], validate=True).decode("utf-8", "replace")
        except (ValueError, UnicodeDecodeError):
            return False
        username, _, password = decoded.partition(":")
        if username != USERNAME:
            return False
        return hmac.compare_digest(password, self._expected_password)

    async def _send_401(self, send: Send) -> None:
        body = b"Authentication required.\n"
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"www-authenticate", f'Basic realm="{REALM}"'.encode("latin-1")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
