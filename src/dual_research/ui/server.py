"""FastAPI server that exposes the UI aggregator over HTTP + SSE.

Boots with::

    dual-research serve [--port 6173] [--host 127.0.0.1] [--runs-dir PATH]

Endpoints
---------

- ``GET  /api/health``                                  liveness + version
- ``GET  /api/runs``                                    list rows
- ``GET  /api/runs/{run_id}``                           full Run snapshot
- ``GET  /api/runs/{run_id}/stream``                    SSE; full snapshot per
                                                        transcript-file change
- ``GET  /api/runs/{run_id}/files/{path:path}``         markdown body
- ``GET  /``  + ``/static/*``                           UI bundle (spec 0011)

JSON wire format
----------------

Python uses snake_case throughout. The wire format is camelCase, applied as a
recursive translation at the JSON boundary. ``TokenUsage.in_`` becomes ``in``.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator

import base64
import mimetypes

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

try:
    from watchfiles import awatch  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover — dependency declared in pyproject
    awatch = None  # type: ignore[assignment]

from dual_research import __version__
from dual_research.config import resolve_paths
from dual_research.ui import load_run_snapshot, summarize_run
from dual_research.ui.auth import SupabaseAuthMiddleware
from dual_research.ui.cache import BoundedLRU, MISSING
from dual_research.ui.datasource import SupabaseSessionData, latest_event_seq
from dual_research.ui.labels import display_id, derive_run_status, phase_to_int
from dual_research.ui.models import RunListRow, to_jsonable

# ─── Spec 0079 — per-process LRU for immutable per-turn artifacts ─────────────
# `inputs/<key>.json` and `searches/<key>.json` are append-only-immutable in
# session_files (retries get new turn keys; rows are never updated in place).
# Cap at 100 entries per cache; LRU eviction on insert; process restart on
# deploy clears them. Module-level so all uvicorn workers in this process
# share a single cache.
_INPUT_BUNDLE_CACHE = BoundedLRU(maxsize=100)
_SEARCH_AUDIT_CACHE = BoundedLRU(maxsize=100)

# ─── Spec 0081 — full run-snapshot cache keyed by (run_id, latest_event_seq) ──
# `/api/runs/{id}` was running `SupabaseSessionData.materialize()` on every
# request — a full paginated dump of session_files + transcript + blobs into
# a tmp dir, then a re-read. Multi-second per call for a real run. The
# snapshot is a pure function of `run_id` + `max(events.seq)`, so caching by
# that compound key is correct for both done runs (seq is fixed → permanent
# hit) and live runs (cache hit between event ticks; one re-materialise per
# new event no matter how many viewers).
_RUN_SNAPSHOT_CACHE = BoundedLRU(maxsize=50)

_IMMUTABLE_CACHE_CONTROL = "public, max-age=86400, immutable"

# ─── Spec 0082 — runs hidden from the frontend (supabase mode) ────────────────
# Rows stay in the database — every run is still reachable via the
# orchestrator, the recompute/reconcile CLIs, and direct SQL — but the hosted
# UI's list view, search, and per-run endpoints all behave as if these IDs
# don't exist. Add to this set to retire a run from the public surface.
#
# Spec 0122 follow-up (2026-05-20) — every run that landed before the parser
# tolerance + transcript bridge + replay-from-disk fixes shipped is now stale
# from a UI standpoint: their snapshots were rendered against a broken
# aggregator pipeline and their lifecycle counters under-reported reality.
# The data is preserved server-side; the hosted UI hides them so the next
# run starts against a clean list.
HIDDEN_RUN_IDS: frozenset[str] = frozenset({
    # Pre-spec-0082 retirements.
    "20260515-111151-asyncio-vs-goroutines",          # 38f9
    "20260515-112634-p2-asyncio-vs-goroutines",       # 1ab9
    "20260515-114303-full-e2e",                       # 5455
    "20260515-120623-prod-postgres-vs-sqlite",        # 76e1
    "20260515-122538-prod-cached-e2e",                # 48b1
    "20260515-124552-cache-multi-round",              # 009f
    "20260515-163105-live-integration-test",          # 70e3
    "20260515-171500-live-verify-webcomp-catalogue",  # db46
    "20260516-023449-web-components-catalogue",       # bcd3

    # Spec 0122 follow-up — pre-parser-fix runs, hidden so the hosted
    # UI presents a clean slate for fresh end-to-end runs.
    "20260516-035048-partner-vetting-arch-critique",
    "20260518-065852-backend-language-choice-briefing-for-dual-research",
    "20260518-083618-backend-language-choice",
    "20260519-132908-backend-language-choice",
    "20260520-025406-pv-backend-language-choice",
})


def _clear_caches_for_test() -> None:
    """Drop all LRUs. Tests call this between cases to keep them hermetic."""
    _INPUT_BUNDLE_CACHE.clear()
    _SEARCH_AUDIT_CACHE.clear()
    _RUN_SNAPSHOT_CACHE.clear()


class _GZipMiddlewareSkipStream(GZipMiddleware):
    """Spec 0081 — skip gzip for SSE paths.

    `GZipMiddleware` buffers response chunks to decide whether the total body
    is above `minimum_size` worth compressing. For an SSE stream of tiny
    per-event payloads that decision is never satisfied and the middleware
    can hold the response open waiting for more bytes — breaking the
    realtime delivery contract. Skipping at the path level is the cleanest
    fix; gzip on JSON / markdown still applies elsewhere.
    """

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") == "http" and scope.get("path", "").endswith("/stream"):
            await self.app(scope, receive, send)
            return
        await super().__call__(scope, receive, send)

# ─── App + state ──────────────────────────────────────────────────────────────


def _make_app(runs_dir: Path) -> FastAPI:
    """Build a FastAPI app bound to a specific ``runs_dir``.

    Factory style so tests can spin up multiple apps over tmp directories
    without leaking state between tests.

    Local (fs) mode is never auth-gated — this is the laptop dev path.
    """
    app = FastAPI(
        title="dual-research UI",
        version=__version__,
        docs_url=None,  # no Swagger UI in v1; the API surface is small
        redoc_url=None,
    )
    app.state.runs_dir = runs_dir
    # Spec 0079 — gzip JSON + markdown responses above 1 KB. Skips small
    # auth-error bodies where compression CPU would dominate.
    app.add_middleware(_GZipMiddlewareSkipStream, minimum_size=1024)

    # ─── API routes ───────────────────────────────────────────────────────────

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "runsDir": str(runs_dir),
        }

    # Spec 0126 — serve spec markdown for the Changelog tab's "Open spec ↗"
    # modal. Available in both fs and supabase modes.
    @app.get("/api/specs/{spec_id}")
    async def get_spec_markdown_fs(spec_id: str) -> PlainTextResponse:
        return _serve_spec_markdown(spec_id)

    @app.get("/api/runs")
    async def list_runs() -> JSONResponse:
        rows: list[dict[str, Any]] = []
        if runs_dir.exists():
            for entry in sorted(runs_dir.iterdir(), reverse=True):
                if not entry.is_dir():
                    continue
                if not (entry / "state.json").exists() and not (entry / "brief.md").exists():
                    # Not a session dir — skip stray folders.
                    continue
                try:
                    row = summarize_run(entry)
                    rows.append(_to_camel(dataclasses.asdict(row)))
                except Exception:
                    # Defensive: one malformed session dir shouldn't 500 the list.
                    continue
        return JSONResponse(rows)

    # ─── Spec 0060 — cross-run search ───────────────────────────────────
    @app.get("/api/search")
    async def search_runs_fs(request: Request) -> JSONResponse:
        q = (request.query_params.get("q") or "").strip().lower()
        if not q:
            return JSONResponse([])
        results = _search_runs_fs(runs_dir, q)
        return JSONResponse(results)

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str) -> JSONResponse:
        session = _resolve_session(runs_dir, run_id)
        run = load_run_snapshot(session)
        return JSONResponse(_to_camel(to_jsonable(run)))

    @app.get("/api/runs/{run_id}/stream")
    async def stream_run(run_id: str, request: Request) -> EventSourceResponse:
        session = _resolve_session(runs_dir, run_id)
        return EventSourceResponse(_run_event_stream(session, request))

    # ─── Spec 0048 — reconcile snapshots ──────────────────────────────────
    # GET /api/reconcile/index   → list of dates with snapshots
    # GET /api/reconcile/{date}  → latest ReconcileReport for date, or 404

    @app.get("/api/reconcile/index")
    async def list_reconcile_fs() -> JSONResponse:
        from dual_research.audit.reconcile import reconcile_dir as _rdir
        rdir = _rdir(runs_dir.parent)
        if not rdir.exists():
            return JSONResponse([])
        dates = sorted(
            p.stem for p in rdir.glob("*.json") if len(p.stem) == 10
        )
        return JSONResponse(dates)

    @app.get("/api/reconcile/{date}")
    async def get_reconcile_fs(date: str) -> JSONResponse:
        # Date validation — only accept YYYY-MM-DD to avoid path tricks.
        if len(date) != 10 or date[4] != "-" or date[7] != "-":
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
        from dual_research.audit.reconcile import read_reconcile_json
        report = read_reconcile_json(runs_dir.parent, date)
        if report is None:
            raise HTTPException(status_code=404, detail=f"no reconcile snapshot for {date}")
        return JSONResponse(_to_camel(dataclasses.asdict(report)))

    @app.get("/api/runs/{run_id}/files/{path:path}")
    async def get_file(run_id: str, path: str) -> PlainTextResponse:
        session = _resolve_session(runs_dir, run_id)
        body = _read_scoped_file(session, path)
        return PlainTextResponse(body, media_type="text/plain; charset=utf-8")

    @app.get("/api/runs/{run_id}/attachments")
    async def list_attachments(run_id: str) -> JSONResponse:
        session = _resolve_session(runs_dir, run_id)
        return JSONResponse(_read_attachments_index(session))

    # ─── Spec 0033 input bundles ──────────────────────────────────────────
    # GET /api/runs/{run_id}/inputs/index    → list of available turn-keys
    # GET /api/runs/{run_id}/inputs/{key}    → full per-turn input bundle

    @app.get("/api/runs/{run_id}/inputs/index")
    async def list_inputs_fs(run_id: str) -> JSONResponse:
        session = _resolve_session(runs_dir, run_id)
        return JSONResponse({"keys": _list_input_bundle_keys_fs(session)})

    @app.get("/api/runs/{run_id}/inputs/{turn_key}")
    async def get_input_bundle_fs(run_id: str, turn_key: str) -> JSONResponse:
        session = _resolve_session(runs_dir, run_id)
        payload = _read_input_bundle_fs(session, turn_key)
        if payload is None:
            raise HTTPException(status_code=404, detail="not found")
        return JSONResponse(
            payload, headers={"Cache-Control": _IMMUTABLE_CACHE_CONTROL}
        )

    # ─── Spec 0036 search audit ───────────────────────────────────────────
    # GET /api/runs/{run_id}/searches/index   → list of available turn-keys
    # GET /api/runs/{run_id}/searches/{key}   → full per-turn search audit

    @app.get("/api/runs/{run_id}/searches/index")
    async def list_searches_fs(run_id: str, request: Request) -> JSONResponse:
        session = _resolve_session(runs_dir, run_id)
        keys = _list_search_audit_keys_fs(session)
        if request.query_params.get("include") == "summary":
            return JSONResponse({
                "keys": keys,
                "summary": _search_audit_summary_fs(session, keys),
            })
        return JSONResponse({"keys": keys})

    @app.get("/api/runs/{run_id}/searches/{turn_key}")
    async def get_search_audit_fs(run_id: str, turn_key: str) -> JSONResponse:
        session = _resolve_session(runs_dir, run_id)
        payload = _read_search_audit_fs(session, turn_key)
        if payload is None:
            raise HTTPException(status_code=404, detail="not found")
        return JSONResponse(
            payload, headers={"Cache-Control": _IMMUTABLE_CACHE_CONTROL}
        )

    @app.get("/api/runs/{run_id}/attachment-blobs/{rel_path:path}")
    async def get_attachment_blob(run_id: str, rel_path: str) -> Response:
        session = _resolve_session(runs_dir, run_id)
        if not _safe_attachment_path(rel_path):
            raise HTTPException(status_code=404, detail="not found")
        target = (session / rel_path).resolve()
        base = session.resolve()
        if not str(target).startswith(str(base) + os.sep):
            raise HTTPException(status_code=404, detail="not found")
        if not target.is_file():
            raise HTTPException(status_code=404, detail="not found")
        mime, _ = mimetypes.guess_type(target.name)
        try:
            data = target.read_bytes()
        except OSError:
            raise HTTPException(status_code=404, detail="not found")
        return Response(content=data, media_type=mime or "application/octet-stream")

    # ─── Static UI ────────────────────────────────────────────────────────────

    # Mount LAST so it doesn't shadow the API routes above.
    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


# ─── Supabase-backed app (spec 0020) ──────────────────────────────────────────


SUPABASE_STREAM_POLL_SECONDS = 5.0


def _make_supabase_app(
    client: Any,
    *,
    supabase_url: str | None = None,
    supabase_anon_key: str | None = None,
) -> FastAPI:
    """Build a FastAPI app that reads runs from Supabase instead of disk.

    Used when ``RUNS_BACKEND=supabase``. The ``runs`` table powers the list
    view directly; the run-detail and stream paths materialize a tmp dir from
    ``session_files`` and hand it to the existing aggregator.

    The Supabase Auth middleware (spec 0021) gates `/api/*` requests except
    `/api/health` and `/api/config`. Tests can omit the URL + anon key — the
    `/api/config` endpoint just returns empty strings then.
    """
    app = FastAPI(
        title="dual-research UI",
        version=__version__,
        docs_url=None,
        redoc_url=None,
    )
    app.state.backend = "supabase"
    app.add_middleware(SupabaseAuthMiddleware, client=client)
    # Spec 0079 — gzip outermost (last add_middleware is first in onion order
    # in Starlette). Compresses JSON bundle bodies (often 100 KB+) and the
    # markdown/text payloads from /files; minimum_size skips tiny error
    # bodies + /api/health where compression CPU outweighs wire savings.
    app.add_middleware(_GZipMiddlewareSkipStream, minimum_size=1024)

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "version": __version__, "backend": "supabase"}

    # Spec 0126 — serve spec markdown for the Changelog tab's "Open spec ↗"
    # modal. Auth gate: any authenticated user can read specs.
    @app.get("/api/specs/{spec_id}")
    async def get_spec_markdown_sb(request: Request, spec_id: str) -> PlainTextResponse:
        user = request.scope.get("user") or {}
        if not user.get("email"):
            raise HTTPException(status_code=401, detail="unauthenticated")
        return _serve_spec_markdown(spec_id)

    @app.get("/api/config")
    async def config() -> dict[str, str]:
        return {
            "supabaseUrl": supabase_url or "",
            "supabaseAnonKey": supabase_anon_key or "",
        }

    @app.get("/api/me")
    async def me(request: Request) -> dict[str, Any]:
        user = request.scope.get("user") or {}
        token = user.get("token")
        avatar_url: str | None = None
        full_name: str | None = None
        if token:
            try:
                u = client.auth.get_user(token).user
                meta = getattr(u, "user_metadata", None) or {}
                avatar_url = meta.get("avatar_url") or meta.get("picture")
                full_name = meta.get("full_name") or meta.get("name")
            except Exception:
                pass
        # Spec 0125 — bump last_seen_at on every /api/me call so admins can
        # see who's active. Best-effort: silently skip if the column doesn't
        # exist yet (migration not yet applied).
        caller_email = (user.get("email") or "").lower()
        if caller_email:
            try:
                client.table("approved_emails").update(
                    {"last_seen_at": datetime.now(timezone.utc).isoformat()}
                ).eq("email", caller_email).execute()
            except Exception:
                pass
        return {
            "email": user.get("email") or "",
            "isAdmin": bool(user.get("is_admin")),
            "avatarUrl": avatar_url,
            "fullName": full_name,
        }

    @app.get("/api/approved-emails")
    async def list_approved_emails(request: Request) -> JSONResponse:
        _require_admin(request)
        res = (
            client.table("approved_emails")
            .select("email,is_admin,added_at")
            .order("added_at", desc=True)
            .execute()
        )
        return JSONResponse(_to_camel(res.data or []))

    @app.post("/api/approved-emails")
    async def add_approved_email(request: Request) -> JSONResponse:
        _require_admin(request)
        body = await request.json()
        email = (body or {}).get("email", "").strip().lower()
        is_admin_flag = bool((body or {}).get("isAdmin"))
        if not _looks_like_email(email):
            raise HTTPException(status_code=400, detail="invalid email")
        row = {"email": email, "is_admin": is_admin_flag}
        client.table("approved_emails").upsert([row], on_conflict="email").execute()
        return JSONResponse(_to_camel(row), status_code=201)

    @app.delete("/api/approved-emails/{email}")
    async def delete_approved_email(request: Request, email: str) -> JSONResponse:
        caller_email = _require_admin(request)
        target = email.strip().lower()
        if target == caller_email:
            raise HTTPException(status_code=409, detail="cannot remove yourself")

        # Look up target row to check admin status.
        target_res = (
            client.table("approved_emails")
            .select("email,is_admin")
            .eq("email", target)
            .limit(1)
            .execute()
        )
        target_rows = target_res.data or []
        if not target_rows:
            raise HTTPException(status_code=404, detail="email not on allowlist")

        if target_rows[0].get("is_admin"):
            admin_count = _count_admins(client)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=409,
                    detail="cannot remove the only remaining admin",
                )

        client.table("approved_emails").delete().eq("email", target).execute()
        return JSONResponse({"deleted": target})

    # ─── Spec 0125 — Users + onboarding state + system settings ─────────

    # The spec 0125 columns on approved_emails: onboarded_at,
    # onboarded_at_version, tour_step, tour_force_reset_at, last_seen_at.
    # Endpoints are defensive — if the migration hasn't been applied yet,
    # they fall back to selecting only the pre-0124 columns and surface
    # null for the new fields. Once the migration lands, the same code
    # picks up the new columns automatically.

    _USER_COLS_FULL = (
        "email,is_admin,added_at,onboarded_at,onboarded_at_version,"
        "tour_step,tour_force_reset_at,last_seen_at"
    )
    _USER_COLS_LEGACY = "email,is_admin,added_at"

    def _select_users() -> list[dict[str, Any]]:
        """Return all approved-emails rows with new columns when available."""
        try:
            res = (
                client.table("approved_emails")
                .select(_USER_COLS_FULL)
                .order("added_at", desc=True)
                .execute()
            )
            return res.data or []
        except Exception:
            # Migration not yet applied — fall back to legacy columns.
            res = (
                client.table("approved_emails")
                .select(_USER_COLS_LEGACY)
                .order("added_at", desc=True)
                .execute()
            )
            rows = res.data or []
            for r in rows:
                r.setdefault("onboarded_at", None)
                r.setdefault("onboarded_at_version", None)
                r.setdefault("tour_step", 1)
                r.setdefault("tour_force_reset_at", None)
                r.setdefault("last_seen_at", None)
            return rows

    def _compute_must_restart(row: dict[str, Any]) -> bool:
        force = row.get("tour_force_reset_at")
        if not force:
            return False
        onboarded = row.get("onboarded_at")
        if not onboarded:
            return True
        # Both are ISO-8601 strings from PostgREST; lexicographic compare is
        # sound for UTC timestamps in this format.
        return force > onboarded

    @app.get("/api/users")
    async def list_users(request: Request) -> JSONResponse:
        _require_admin(request)
        rows = _select_users()
        for r in rows:
            r["must_restart"] = _compute_must_restart(r)
        return JSONResponse(_to_camel(rows))

    @app.post("/api/users/{email}/reset-onboarding")
    async def reset_onboarding_for_user(request: Request, email: str) -> JSONResponse:
        _require_admin(request)
        target = email.strip().lower()
        # Confirm the user exists in the allowlist.
        check = (
            client.table("approved_emails")
            .select("email")
            .eq("email", target)
            .limit(1)
            .execute()
        )
        if not (check.data or []):
            raise HTTPException(status_code=404, detail="email not on allowlist")
        ts = datetime.now(timezone.utc).isoformat()
        try:
            client.table("approved_emails").update(
                {"tour_force_reset_at": ts}
            ).eq("email", target).execute()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=(
                    "onboarding columns not migrated yet — apply spec 0125 "
                    "migration in Supabase Studio"
                ),
            ) from e
        return JSONResponse({"ok": True, "tourForceResetAt": ts})

    @app.post("/api/users/bulk-reset-onboarding")
    async def bulk_reset_onboarding(request: Request) -> JSONResponse:
        _require_admin(request)
        body = await request.json()
        emails = [
            (e or "").strip().lower()
            for e in (body or {}).get("emails", [])
            if (e or "").strip()
        ]
        if not emails:
            raise HTTPException(status_code=400, detail="emails array is required")
        ts = datetime.now(timezone.utc).isoformat()
        reset_count = 0
        try:
            for e in emails:
                res = (
                    client.table("approved_emails")
                    .update({"tour_force_reset_at": ts})
                    .eq("email", e)
                    .execute()
                )
                reset_count += len(res.data or [])
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=(
                    "onboarding columns not migrated yet — apply spec 0125 "
                    "migration in Supabase Studio"
                ),
            ) from e
        return JSONResponse({"ok": True, "reset": reset_count, "at": ts})

    @app.post("/api/onboarding/broadcast-reset")
    async def broadcast_reset_onboarding(request: Request) -> JSONResponse:
        _require_admin(request)
        ts = datetime.now(timezone.utc).isoformat()
        try:
            # neq("email", "") matches every row; PostgREST refuses
            # filter-free updates as a safety guard, mirrored by our fake.
            res = (
                client.table("approved_emails")
                .update({"tour_force_reset_at": ts})
                .neq("email", "")
                .execute()
            )
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=(
                    "onboarding columns not migrated yet — apply spec 0125 "
                    "migration in Supabase Studio"
                ),
            ) from e
        return JSONResponse({"ok": True, "reset": len(res.data or []), "at": ts})

    @app.get("/api/onboarding/state")
    async def get_onboarding_state(request: Request) -> JSONResponse:
        user = request.scope.get("user") or {}
        email = (user.get("email") or "").lower()
        if not email:
            raise HTTPException(status_code=401, detail="unauthenticated")
        try:
            res = (
                client.table("approved_emails")
                .select(
                    "tour_step,onboarded_at,onboarded_at_version,tour_force_reset_at"
                )
                .eq("email", email)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if not rows:
                return JSONResponse({
                    "tourStep": 1,
                    "onboardedAt": None,
                    "onboardedAtVersion": None,
                    "mustRestart": False,
                })
            row = rows[0]
            return JSONResponse({
                "tourStep": row.get("tour_step") or 1,
                "onboardedAt": row.get("onboarded_at"),
                "onboardedAtVersion": row.get("onboarded_at_version"),
                "mustRestart": _compute_must_restart(row),
            })
        except Exception:
            # Migration not yet applied — return defaults so the client falls
            # back to localStorage-driven behaviour.
            return JSONResponse({
                "tourStep": 1,
                "onboardedAt": None,
                "onboardedAtVersion": None,
                "mustRestart": False,
            })

    @app.put("/api/onboarding/state")
    async def put_onboarding_state(request: Request) -> JSONResponse:
        user = request.scope.get("user") or {}
        email = (user.get("email") or "").lower()
        if not email:
            raise HTTPException(status_code=401, detail="unauthenticated")
        body = await request.json() or {}
        patch: dict[str, Any] = {}
        if "tourStep" in body:
            try:
                step = int(body["tourStep"])
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="tourStep must be int")
            if not 1 <= step <= 16:  # generous upper bound
                raise HTTPException(status_code=400, detail="tourStep out of range")
            patch["tour_step"] = step
        if "onboardedAt" in body:
            val = body["onboardedAt"]
            if val is None or isinstance(val, str):
                patch["onboarded_at"] = val
                if val:
                    patch["onboarded_at_version"] = __version__
            else:
                raise HTTPException(
                    status_code=400, detail="onboardedAt must be ISO-8601 string or null"
                )
        if not patch:
            return JSONResponse({"ok": True})
        try:
            client.table("approved_emails").update(patch).eq("email", email).execute()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=(
                    "onboarding columns not migrated yet — apply spec 0125 "
                    "migration in Supabase Studio"
                ),
            ) from e
        return JSONResponse({"ok": True})

    @app.get("/api/system-settings")
    async def get_system_settings(request: Request) -> JSONResponse:
        # Any authed user can read system flags (the client uses them to
        # decide whether to gate the tour). Only admins can write.
        user = request.scope.get("user") or {}
        if not user.get("email"):
            raise HTTPException(status_code=401, detail="unauthenticated")
        try:
            res = (
                client.table("system_settings")
                .select("onboarding_required")
                .eq("id", 1)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if not rows:
                return JSONResponse({"onboardingRequired": False})
            return JSONResponse({"onboardingRequired": bool(rows[0].get("onboarding_required"))})
        except Exception:
            # Migration not yet applied.
            return JSONResponse({"onboardingRequired": False})

    @app.put("/api/system-settings")
    async def put_system_settings(request: Request) -> JSONResponse:
        caller = _require_admin(request)
        body = await request.json() or {}
        if "onboardingRequired" not in body:
            raise HTTPException(
                status_code=400, detail="onboardingRequired field is required"
            )
        flag = bool(body["onboardingRequired"])
        patch = {
            "id": 1,
            "onboarding_required": flag,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": caller,
        }
        try:
            client.table("system_settings").upsert([patch], on_conflict="id").execute()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=(
                    "system_settings table not migrated yet — apply spec 0125 "
                    "migration in Supabase Studio"
                ),
            ) from e
        return JSONResponse({"ok": True, "onboardingRequired": flag})

    @app.get("/api/runs")
    async def list_runs() -> JSONResponse:
        rows = _supabase_list_runs(client)
        return JSONResponse([_to_camel(dataclasses.asdict(r)) for r in rows])

    # ─── Spec 0060 — cross-run search (hosted) ──────────────────────────
    @app.get("/api/search")
    async def search_runs_sb(request: Request) -> JSONResponse:
        q = (request.query_params.get("q") or "").strip().lower()
        if not q:
            return JSONResponse([])
        results = _search_runs_supabase(client, q)
        return JSONResponse(results)

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str) -> JSONResponse:
        _require_run_exists(client, run_id)
        payload = _materialize_snapshot_supabase(client, run_id)
        return JSONResponse(payload)

    @app.get("/api/runs/{run_id}/stream")
    async def stream_run(run_id: str, request: Request) -> EventSourceResponse:
        _require_run_exists(client, run_id)
        return EventSourceResponse(_supabase_event_stream(client, run_id, request))

    # ─── Spec 0048 — reconcile snapshots (hosted mode) ────────────────────

    @app.get("/api/reconcile/index")
    async def list_reconcile_supabase() -> JSONResponse:
        try:
            res = (
                client.table("reconcile_results")
                .select("date")
                .order("date", desc=True)
                .execute()
            )
        except Exception:
            return JSONResponse([])
        rows = res.data or []
        return JSONResponse([r["date"] for r in rows])

    @app.get("/api/reconcile/{date}")
    async def get_reconcile_supabase(date: str) -> JSONResponse:
        if len(date) != 10 or date[4] != "-" or date[7] != "-":
            raise HTTPException(status_code=400, detail="date must be YYYY-MM-DD")
        try:
            res = (
                client.table("reconcile_results")
                .select("payload")
                .eq("date", date)
                .limit(1)
                .execute()
            )
        except Exception:
            raise HTTPException(status_code=404, detail=f"no reconcile snapshot for {date}")
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=404, detail=f"no reconcile snapshot for {date}")
        payload = rows[0].get("payload") or {}
        return JSONResponse(_to_camel(payload))

    @app.get("/api/runs/{run_id}/files/{path:path}")
    async def get_file(run_id: str, path: str) -> PlainTextResponse:
        if not _safe_rel_path(path):
            raise HTTPException(status_code=404, detail="not found")
        res = (
            client.table("session_files")
            .select("content")
            .eq("run_id", run_id)
            .eq("path", path)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="not found")
        body = rows[0]["content"]
        # Spec 0034: same block-id injection for hosted serves.
        if path.endswith(".md"):
            try:
                from dual_research.protocol.blocks import assign_block_ids
                body, _ = assign_block_ids(body)
            except Exception:
                pass
        return PlainTextResponse(body, media_type="text/plain; charset=utf-8")

    @app.get("/api/runs/{run_id}/attachments")
    async def list_attachments(run_id: str) -> JSONResponse:
        _require_run_exists(client, run_id)
        res = (
            client.table("session_files")
            .select("content")
            .eq("run_id", run_id)
            .eq("path", "attachments.json")
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return JSONResponse({"attachments": []})
        try:
            data = json.loads(rows[0]["content"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return JSONResponse({"attachments": []})
        return JSONResponse(data)

    # ─── Spec 0033 input bundles ──────────────────────────────────────────
    # GET /api/runs/{run_id}/inputs/index    → list of available turn-keys
    # GET /api/runs/{run_id}/inputs/{key}    → full per-turn input bundle

    @app.get("/api/runs/{run_id}/inputs/index")
    async def list_inputs_sb(run_id: str) -> JSONResponse:
        _require_run_exists(client, run_id)
        return JSONResponse({"keys": _list_input_bundle_keys_supabase(client, run_id)})

    @app.get("/api/runs/{run_id}/inputs/{turn_key}")
    async def get_input_bundle_sb(run_id: str, turn_key: str) -> JSONResponse:
        _require_run_exists(client, run_id)
        payload = _read_input_bundle_supabase(client, run_id, turn_key)
        if payload is None:
            raise HTTPException(status_code=404, detail="not found")
        return JSONResponse(
            payload, headers={"Cache-Control": _IMMUTABLE_CACHE_CONTROL}
        )

    # ─── Spec 0036 search audit (hosted) ──────────────────────────────────
    @app.get("/api/runs/{run_id}/searches/index")
    async def list_searches_sb(run_id: str, request: Request) -> JSONResponse:
        _require_run_exists(client, run_id)
        keys = _list_search_audit_keys_supabase(client, run_id)
        if request.query_params.get("include") == "summary":
            return JSONResponse({
                "keys": keys,
                "summary": _search_audit_summary_supabase(client, run_id, keys),
            })
        return JSONResponse({"keys": keys})

    @app.get("/api/runs/{run_id}/searches/{turn_key}")
    async def get_search_audit_sb(run_id: str, turn_key: str) -> JSONResponse:
        _require_run_exists(client, run_id)
        payload = _read_search_audit_supabase(client, run_id, turn_key)
        if payload is None:
            raise HTTPException(status_code=404, detail="not found")
        return JSONResponse(
            payload, headers={"Cache-Control": _IMMUTABLE_CACHE_CONTROL}
        )

    @app.get("/api/runs/{run_id}/attachment-blobs/{rel_path:path}")
    async def get_attachment_blob(run_id: str, rel_path: str) -> Response:
        _require_run_exists(client, run_id)
        if not _safe_attachment_path(rel_path):
            raise HTTPException(status_code=404, detail="not found")
        res = (
            client.table("attachment_blobs")
            .select("mime,content_b64")
            .eq("run_id", run_id)
            .eq("rel_path", rel_path)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="not found")
        row = rows[0]
        try:
            payload = base64.b64decode(row["content_b64"])
        except (TypeError, ValueError):
            raise HTTPException(status_code=404, detail="not found")
        return Response(content=payload, media_type=row.get("mime") or "application/octet-stream")

    # Static UI bundle — same as fs mode.
    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ─── Spec 0126 — spec markdown serving ────────────────────────────────────────

_SPEC_ID_RE = re.compile(r"^[0-9a-zA-Z][0-9a-zA-Z\-_]*$")
_FRONTMATTER_RE = re.compile(r"^---\r?\n.*?\r?\n---\r?\n", re.DOTALL)


def _resolve_specs_dir() -> Path:
    """Resolve the repo's ``specs/`` directory.

    Walks up from this module file until it finds a sibling ``specs/`` dir
    with the expected layout. Defensive: returns a Path even if not found —
    the endpoint then 404s on every request, which is the right behaviour
    if the deploy stripped the specs/ directory.
    """
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        candidate = parent / "specs"
        if candidate.is_dir():
            return candidate
    return here.parents[3] / "specs"


def _strip_yaml_frontmatter(text: str) -> str:
    """Drop a leading ``--- … ---`` YAML block, if present."""
    m = _FRONTMATTER_RE.match(text)
    if m:
        return text[m.end():].lstrip("\n")
    return text


def _serve_spec_markdown(spec_id: str) -> PlainTextResponse:
    """Locate, frontmatter-strip, and serve one spec file as markdown.

    ``spec_id`` may be the full filename stem (``"0121-how-it-works-..."``)
    or just the leading number (``"0121"``). Path traversal is impossible
    because the id is constrained to ``[0-9a-zA-Z\\-_]+`` and never joined
    with `/`.
    """
    spec_id = (spec_id or "").strip()
    if not _SPEC_ID_RE.match(spec_id):
        raise HTTPException(status_code=400, detail="invalid spec id")
    specs_dir = _resolve_specs_dir()
    if not specs_dir.is_dir():
        raise HTTPException(status_code=404, detail="specs directory not available")
    target: Path | None = None
    exact = specs_dir / f"{spec_id}.md"
    if exact.is_file():
        target = exact
    else:
        # Prefix-by-leading-digits, e.g. "0121" → "0121-…md".
        for f in sorted(specs_dir.glob(f"{spec_id}-*.md")):
            target = f
            break
    if target is None or not target.is_file():
        raise HTTPException(status_code=404, detail="spec not found")
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        raise HTTPException(status_code=500, detail="failed to read spec")
    return PlainTextResponse(
        _strip_yaml_frontmatter(text),
        media_type="text/markdown; charset=utf-8",
    )


def _looks_like_email(s: str) -> bool:
    return bool(_EMAIL_RE.match(s or ""))


def _require_admin(request: Request) -> str:
    """Verify the request scope marks the caller as admin. Returns the email."""
    user = request.scope.get("user") or {}
    email = user.get("email")
    if not email or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="admin only")
    return email


def _count_admins(client: Any) -> int:
    res = (
        client.table("approved_emails")
        .select("email")
        .eq("is_admin", True)
        .execute()
    )
    return len(res.data or [])


def _supabase_list_runs(client: Any) -> list[RunListRow]:
    """Build a list of RunListRow from the runs table.

    Joins in topic from session_files.brief.md via a second query; rounds
    column is left None in supabase mode for v1 (would need an events
    aggregate query per row).
    """
    res = (
        client.table("runs")
        .select(
            "id,slug,created_at,pushed_at,phase_reached,exit_code,duration_ms,"
            "total_cost_usd,state,metrics"
        )
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    runs_rows = res.data or []
    # Spec 0082 — drop hidden runs before doing any further work (saves the
    # brief-fetch round-trip for filtered-out rows too).
    if HIDDEN_RUN_IDS:
        runs_rows = [r for r in runs_rows if r.get("id") not in HIDDEN_RUN_IDS]
    if not runs_rows:
        return []

    run_ids = [r["id"] for r in runs_rows]
    briefs_res = (
        client.table("session_files")
        .select("run_id,content")
        .in_("run_id", run_ids)
        .eq("path", "brief.md")
        .execute()
    )
    briefs: dict[str, str] = {row["run_id"]: row["content"] for row in (briefs_res.data or [])}

    out: list[RunListRow] = []
    for r in runs_rows:
        phase_str = r.get("phase_reached") or "phase0"
        phase_int = phase_to_int(phase_str)
        topic = _extract_h1(briefs.get(r["id"], ""))
        started_at = r.get("created_at")
        started_ago = _seconds_since_iso(started_at)
        duration = r["duration_ms"] / 1000 if r.get("duration_ms") else None
        status = _status_from_columns(
            phase_reached=phase_str,
            exit_code=r.get("exit_code"),
            state=r.get("state") or {},
            # Spec 0181 — orchestrator's last upsert ts is the canonical
            # "last activity" proxy for Supabase-backed runs (cheaper
            # than a per-row events.MAX(ts) JOIN). Drives the abandoned
            # rule in derive_run_status.
            last_event_at=r.get("pushed_at"),
        )
        out.append(
            RunListRow(
                id=r["id"],
                display_id=display_id(r["id"]),
                status=status,  # type: ignore[arg-type]
                phase=phase_int,
                topic=topic,
                started_at_ago=started_ago,
                started_at=started_at or "",
                duration=duration,
                cost=float(r.get("total_cost_usd") or 0.0),
                rounds=None,
            )
        )
    return out


def _status_from_columns(
    *,
    phase_reached: str,
    exit_code: int | None,
    state: dict,
    last_event_at: str | None = None,
) -> str:
    """Map pushed-run columns onto the UI's status enum.

    Spec 0032's ``--push-while-running`` writes the row mid-flight, so
    Supabase-backed runs are NOT necessarily completed at read time. The
    ``last_event_at`` parameter (typically the row's ``pushed_at``)
    drives the spec-0181 staleness check inside ``derive_run_status``,
    distinguishing healthy in-flight runs from orchestrators that died
    before writing a terminal event.

    Spec 0136 — passes the raw ``exit_code`` through to
    ``derive_run_status`` so the unified truth table's silent-exit
    defence branch (``exit_code == 0`` + not done → ``deadlocked``)
    fires for Supabase-backed runs the same way it fires for the
    disk-backed path.
    """
    final_emitted = bool(state.get("final_emitted_to"))
    return derive_run_status(
        state_phase=phase_reached,
        final_emitted=final_emitted,
        hard_cap_hit=exit_code == 51,
        run_failed=False,  # truth table derives this from exit_code now
        run_completed_exit_code=exit_code,
        last_event_at=last_event_at,
    )


def _extract_h1(brief_text: str) -> str:
    """Match `aggregator._read_topic`: first H1, else first non-empty line."""
    if not brief_text:
        return ""
    for line in brief_text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    for line in brief_text.splitlines():
        s = line.strip()
        if s:
            return s[:200]
    return ""


def _seconds_since_iso(iso_ts: str | None) -> float | None:
    if not iso_ts:
        return None
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(dt.tzinfo) - dt).total_seconds()


def _require_run_exists(client: Any, run_id: str) -> None:
    if not _safe_run_id(run_id):
        raise HTTPException(status_code=404, detail="not found")
    # Spec 0082 — hidden runs 404 across all per-run endpoints (detail, SSE,
    # inputs, searches, files, attachments). One choke-point keeps the rule
    # in sync with the list view's filter.
    if run_id in HIDDEN_RUN_IDS:
        raise HTTPException(status_code=404, detail="not found")
    res = client.table("runs").select("id").eq("id", run_id).limit(1).execute()
    if not (res.data or []):
        raise HTTPException(status_code=404, detail="not found")


def _safe_run_id(run_id: str) -> bool:
    return bool(run_id) and run_id not in ("..", ".") and "/" not in run_id and "\\" not in run_id


def _safe_rel_path(path: str) -> bool:
    if not path or path.startswith("/") or ".." in path.split("/"):
        return False
    return True


def _safe_attachment_path(rel_path: str) -> bool:
    """Attachment paths must live under `attachments/` and not traverse out."""
    if not rel_path or rel_path.startswith("/") or "\\" in rel_path:
        return False
    parts = rel_path.split("/")
    if ".." in parts or "" in parts:
        return False
    return parts[0] == "attachments" and len(parts) >= 2


def _read_attachments_index(session: Path) -> dict[str, Any]:
    """Return the parsed attachments.json body or an empty bundle."""
    path = session / "attachments.json"
    if not path.is_file():
        return {"attachments": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"attachments": []}


# ─── Spec 0033 — input bundle helpers ─────────────────────────────────────────


_INPUT_KEY_RE = re.compile(r"^[a-zA-Z0-9_]+$")


def _normalize_input_key(turn_key: str) -> str | None:
    """Normalise a turn-key from camel or snake form.

    The wire format uses ``phase2Round3Claude`` for Consumption-tab keys;
    the on-disk filenames use ``phase2_round3_claude.json``. The Input
    endpoint accepts both. Also accepts the special key ``input`` for
    the Phase 0 shared bundle.

    Returns the canonical snake-case key or ``None`` if the input is
    invalid.
    """
    if not turn_key or not _INPUT_KEY_RE.match(turn_key):
        return None
    if turn_key == "input":
        return "input"
    # Camel → snake. ``phase2Round3Claude`` → ``phase2_round3_claude``.
    snake = re.sub(r"(?<!^)([A-Z])", r"_\1", turn_key).lower()
    return snake


def _list_input_bundle_keys_fs(session: Path) -> list[str]:
    """List input-bundle keys available on disk under ``session/inputs/``."""
    inputs_dir = session / "inputs"
    if not inputs_dir.is_dir():
        # Phase 0 synth still available if brief.md exists — surface that
        # so the UI can show the Input tab on the Phase 0 card.
        if (session / "brief.md").is_file():
            return ["input"]
        return []
    keys: list[str] = []
    for entry in inputs_dir.iterdir():
        if not entry.is_file() or not entry.name.endswith(".json"):
            continue
        keys.append(entry.stem)
    if "input" not in keys and (session / "brief.md").is_file():
        keys.append("input")
    keys.sort()
    return keys


def _read_input_bundle_fs(session: Path, turn_key: str) -> dict | None:
    """Resolve a single input bundle from disk; synthesise if needed.

    Spec 0085 — when the per-turn JSON is absent on disk (older runs
    that pre-date input auditing, or runs whose bundle was lost),
    synthesise a fallback bundle from the agent's current default
    prompts. Successful disk reads stamp ``system_source: 'recorded'``
    on the response; synthesised payloads stamp ``'agent-default'``
    (set by the builder). The frontend uses this to render the
    "agent default, not per-run" caveat.
    """
    from dual_research.ui.aggregator import (
        build_input_bundle_fallback,
    )

    key = _normalize_input_key(turn_key)
    if key is None:
        return None
    if key == "input":
        # Spec 0150 — synth fallback retired; pre-0142 runs were
        # backfilled with persisted ``inputs/input.json`` files.
        # Missing file => no bundle to surface.
        path = session / "inputs" / "input.json"
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        payload.setdefault("system_source", "recorded")
        return payload
    path = session / "inputs" / f"{key}.json"
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        payload.setdefault("system_source", "recorded")
        return payload
    # Spec 0085 — synthesise from the agent's current default prompts.
    return build_input_bundle_fallback(session, key)


def _list_input_bundle_keys_supabase(client: Any, run_id: str) -> list[str]:
    """List input-bundle keys present in the Supabase ``session_files`` table."""
    try:
        res = (
            client.table("session_files")
            .select("path")
            .eq("run_id", run_id)
            .like("path", "inputs/%.json")
            .execute()
        )
    except Exception:
        return []
    rows = res.data or []
    keys: list[str] = []
    for r in rows:
        p = r.get("path") or ""
        if not p.startswith("inputs/") or not p.endswith(".json"):
            continue
        keys.append(p[len("inputs/") : -len(".json")])
    # Phase 0 synth: surface `input` if brief.md is in session_files.
    if "input" not in keys:
        try:
            brief_res = (
                client.table("session_files")
                .select("path")
                .eq("run_id", run_id)
                .eq("path", "brief.md")
                .limit(1)
                .execute()
            )
            if brief_res.data:
                keys.append("input")
        except Exception:
            pass
    keys.sort()
    return keys


# ─── Spec 0036 — search audit helpers ────────────────────────────────────────


def _list_search_audit_keys_fs(session: Path) -> list[str]:
    """List search-audit keys available on disk under ``session/searches/``."""
    searches_dir = session / "searches"
    if not searches_dir.is_dir():
        return []
    keys: list[str] = []
    for entry in searches_dir.iterdir():
        if not entry.is_file() or not entry.name.endswith(".json"):
            continue
        keys.append(entry.stem)
    keys.sort()
    return keys


def _read_search_audit_fs(session: Path, turn_key: str) -> dict | None:
    """Resolve a single per-turn search-audit bundle from disk."""
    key = _normalize_input_key(turn_key)
    if key is None or key == "input":
        # No per-turn audit for the Phase 0 synthesised input bundle.
        return None
    path = session / "searches" / f"{key}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _list_search_audit_keys_supabase(client: Any, run_id: str) -> list[str]:
    """List search-audit keys in the Supabase ``session_files`` table."""
    try:
        res = (
            client.table("session_files")
            .select("path")
            .eq("run_id", run_id)
            .like("path", "searches/%.json")
            .execute()
        )
    except Exception:
        return []
    rows = res.data or []
    keys: list[str] = []
    for r in rows:
        p = r.get("path") or ""
        if not p.startswith("searches/") or not p.endswith(".json"):
            continue
        keys.append(p[len("searches/") : -len(".json")])
    keys.sort()
    return keys


def _read_search_audit_supabase(client: Any, run_id: str, turn_key: str) -> dict | None:
    """Spec 0079: positive results memoised in ``_SEARCH_AUDIT_CACHE`` keyed
    by ``(run_id, key)``. See `_read_input_bundle_supabase` for the rationale."""
    key = _normalize_input_key(turn_key)
    if key is None or key == "input":
        return None

    cache_key = (run_id, key)
    cached = _SEARCH_AUDIT_CACHE.get(cache_key)
    if cached is not MISSING:
        return cached

    table_path = f"searches/{key}.json"
    try:
        res = (
            client.table("session_files")
            .select("content")
            .eq("run_id", run_id)
            .eq("path", table_path)
            .limit(1)
            .execute()
        )
    except Exception:
        return None
    rows = (res.data if res else None) or []
    if not rows:
        return None
    try:
        payload = json.loads(rows[0]["content"])
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    _SEARCH_AUDIT_CACHE.set(cache_key, payload)
    return payload


def _summarize_audit_payload(payload: dict) -> dict:
    """Compute the per-key summary stats the UI's chip layer consumes."""
    events = payload.get("tool_events") or []
    queries = len(events)
    consulted = 0
    for ev in events:
        sources = ev.get("consulted_sources") or []
        consulted += len(sources)
    flags = payload.get("flags") or {}
    has_warning = bool(flags.get("cited_url_not_in_consulted_sources"))
    return {"queries": queries, "consulted": consulted, "has_warning": has_warning}


def _search_audit_summary_fs(session: Path, keys: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for key in keys:
        path = session / "searches" / f"{key}.json"
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        out[key] = _summarize_audit_payload(payload)
    return out


def _search_audit_summary_supabase(
    client: Any, run_id: str, keys: list[str]
) -> dict[str, dict]:
    if not keys:
        return {}
    try:
        res = (
            client.table("session_files")
            .select("path,content")
            .eq("run_id", run_id)
            .like("path", "searches/%.json")
            .execute()
        )
    except Exception:
        return {}
    rows = res.data or []
    key_set = set(keys)
    out: dict[str, dict] = {}
    for row in rows:
        p = row.get("path") or ""
        if not p.startswith("searches/") or not p.endswith(".json"):
            continue
        key = p[len("searches/") : -len(".json")]
        if key not in key_set:
            continue
        try:
            payload = json.loads(row.get("content") or "")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        out[key] = _summarize_audit_payload(payload)
    return out


def _read_input_bundle_supabase(client: Any, run_id: str, turn_key: str) -> dict | None:
    """Resolve a single input bundle from Supabase; synthesise if needed.

    Spec 0079: positive results are memoised in ``_INPUT_BUNDLE_CACHE`` keyed by
    the normalised ``(run_id, key)``. Bundles are append-only-immutable, so the
    cache never goes stale; restart-on-deploy is the only invalidation hook.
    Negative results (not-found) are not cached — live runs may have a bundle
    appear after the first lookup.

    Spec 0085: when the persisted bundle is absent, synthesise a fallback
    from the agent's current default prompts (mirroring the filesystem
    path in :func:`_read_input_bundle_fs`). The synthesised payload is
    not cached so live runs can still attach a real bundle and have it
    pick up on the next read.
    """
    from dual_research.ui.aggregator import _parse_snake_key, synthesize_bundle_payload

    key = _normalize_input_key(turn_key)
    if key is None:
        return None

    cache_key = (run_id, key)
    cached = _INPUT_BUNDLE_CACHE.get(cache_key)
    if cached is not MISSING:
        return cached

    table_path = f"inputs/{key}.json"
    try:
        res = (
            client.table("session_files")
            .select("content")
            .eq("run_id", run_id)
            .eq("path", table_path)
            .limit(1)
            .execute()
        )
    except Exception:
        res = None
    rows = (res.data if res else None) or []
    if rows:
        try:
            payload = json.loads(rows[0]["content"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        payload.setdefault("system_source", "recorded")
        _INPUT_BUNDLE_CACHE.set(cache_key, payload)
        return payload

    # Spec 0150 — Phase-0 synth fallback retired; pre-0142 runs were
    # backfilled with persisted ``inputs/input.json`` rows so the
    # ``key == "input"`` branch always finds the file above. The
    # non-Phase-0 fallback below stays — it serves keys whose per-turn
    # bundle was never recorded (pre-spec-0033 runs).
    if key == "input":
        return None

    # Spec 0085 — fetch the brief once for the non-Phase-0 fallback
    # path below.
    brief_text = ""
    try:
        brief_res = (
            client.table("session_files")
            .select("content")
            .eq("run_id", run_id)
            .eq("path", "brief.md")
            .limit(1)
            .execute()
        )
    except Exception:
        brief_res = None
    brief_rows = (brief_res.data if brief_res else None) or []
    if brief_rows:
        brief_text = brief_rows[0].get("content") or ""

    # Spec 0085 — non-Phase-0 fallback: parse the snake key and dispatch
    # to the appropriate builder. Mirrors aggregator.build_input_bundle_fallback
    # but reads the brief from Supabase, not the filesystem.
    parsed = _parse_snake_key(key)
    if parsed is None:
        return None
    phase, round_idx, ui_agent_label, is_repair = parsed
    payload = synthesize_bundle_payload(
        phase=phase,
        round_idx=round_idx,
        ui_agent_label=ui_agent_label,
        is_repair=is_repair,
        brief_text=brief_text,
    )
    # Not cached — see docstring rationale.
    return payload


async def _supabase_event_stream(
    client: Any,
    run_id: str,
    request: Request,
) -> AsyncIterator[dict]:
    """Polled SSE: emit a snapshot when max(events.seq) changes.

    Spec 0081 — shares the run-snapshot LRU with the GET endpoint, so
    concurrent viewers + the poll loop only pay one materialise per seq
    transition no matter how many simultaneous subscribers.
    """
    last_seq = -2  # force first emit even on empty events
    while True:
        if await request.is_disconnected():
            return
        current_seq = latest_event_seq(client, run_id)
        if current_seq != last_seq:
            payload = _materialize_snapshot_supabase(
                client, run_id, seq=current_seq
            )
            yield {
                "event": "snapshot",
                "data": json.dumps(payload),
            }
            last_seq = current_seq
        await asyncio.sleep(SUPABASE_STREAM_POLL_SECONDS)


def _materialize_snapshot_supabase(
    client: Any, run_id: str, *, seq: int | None = None
) -> dict:
    """Build a camelCase JSON-ready run snapshot, memoised by (run_id, seq).

    Spec 0081. Computes the latest_event_seq if the caller hasn't already
    (the SSE loop has, the GET endpoint hasn't); checks the LRU; on miss
    runs the full `SupabaseSessionData.materialize()` + `load_run_snapshot`
    pipeline. Returned dict is the camelCase wire shape, ready to wrap in
    a ``JSONResponse``.
    """
    if seq is None:
        seq = latest_event_seq(client, run_id)
    cache_key = (run_id, seq)
    cached = _RUN_SNAPSHOT_CACHE.get(cache_key)
    if cached is not MISSING:
        return cached
    with SupabaseSessionData(client, run_id).materialize() as tmp:
        run = load_run_snapshot(tmp)
    run.id = run_id
    run.display_id = display_id(run_id)
    payload = _to_camel(to_jsonable(run))
    _RUN_SNAPSHOT_CACHE.set(cache_key, payload)
    return payload


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _resolve_session(runs_dir: Path, run_id: str) -> Path:
    """Resolve a run id to its session directory, with path-traversal guards."""
    if not run_id or run_id in ("..", ".") or "/" in run_id or "\\" in run_id:
        raise HTTPException(status_code=404, detail="not found")
    session = (runs_dir / run_id).resolve()
    base = runs_dir.resolve()
    if not str(session).startswith(str(base) + os.sep) and session != base:
        raise HTTPException(status_code=404, detail="not found")
    if not session.is_dir():
        raise HTTPException(status_code=404, detail="not found")
    return session


_ALLOWED_FILE_EXT = {".md", ".json", ".jsonl", ".txt"}


def _read_scoped_file(session: Path, rel_path: str) -> str:
    """Read ``session/rel_path`` after verifying it stays inside ``session``.

    404s on traversal, non-allowed extensions, missing files, and binaries.

    Spec 0034: ``.md`` files are rewritten through ``assign_block_ids``
    on the way out so the rendered DOM carries the same block IDs the
    aggregator pre-resolved against. The added ``<!-- block-id: b-N -->``
    HTML comments are invisible to humans reading the rendered markdown
    and are stripped + lifted by the frontend's Markdown renderer.
    """
    target = (session / rel_path).resolve()
    base = session.resolve()
    if not str(target).startswith(str(base) + os.sep) and target != base:
        raise HTTPException(status_code=404, detail="not found")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="not found")
    if target.suffix not in _ALLOWED_FILE_EXT:
        raise HTTPException(status_code=404, detail="not found")
    try:
        body = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise HTTPException(status_code=404, detail="not found")
    if target.suffix == ".md":
        try:
            from dual_research.protocol.blocks import assign_block_ids
            body, _ = assign_block_ids(body)
        except Exception:
            # Defensive: never fail the read because of an ID-rewrite hiccup.
            pass
    return body


async def _run_event_stream(session: Path, request: Request) -> AsyncIterator[dict]:
    """Yield ``snapshot`` SSE frames whenever the transcript file changes."""
    # Initial frame: whatever is on disk right now.
    yield _snapshot_frame(session)

    if awatch is None:  # pragma: no cover — watchfiles is a declared dep
        return

    # awatch yields a set of (Change, path) tuples per batch.
    try:
        async for changes in awatch(session, stop_event=None):
            if await request.is_disconnected():
                break
            if any(p.endswith("transcript.jsonl") for _, p in changes):
                yield _snapshot_frame(session)
    except asyncio.CancelledError:
        # Client disconnected mid-await — normal termination.
        return


def _snapshot_frame(session: Path) -> dict:
    """Build one SSE frame containing a full ``Run`` snapshot."""
    run = load_run_snapshot(session)
    return {
        "event": "snapshot",
        "data": json.dumps(_to_camel(to_jsonable(run))),
    }


# ─── Spec 0060 — cross-run search helpers ─────────────────────────────────────

_MAX_SEARCH_RESULTS = 50


def _search_runs_fs(runs_dir: Path, query: str) -> list[dict[str, Any]]:
    """Substring search across all runs on disk. Returns camelCase dicts."""
    results: list[dict[str, Any]] = []
    if not runs_dir.exists():
        return results
    for entry in sorted(runs_dir.iterdir(), reverse=True):
        if not entry.is_dir():
            continue
        if not (entry / "state.json").exists() and not (entry / "brief.md").exists():
            continue
        run_id = entry.name
        did = display_id(run_id)
        try:
            _search_run_dir(entry, run_id, did, query, results)
        except Exception:
            continue
        if len(results) >= _MAX_SEARCH_RESULTS:
            break
    return results[:_MAX_SEARCH_RESULTS]


def _search_run_dir(
    session: Path,
    run_id: str,
    did: str,
    query: str,
    results: list[dict[str, Any]],
) -> None:
    """Search a single run directory for matches and append to results."""
    brief_path = session / "brief.md"
    brief_text = ""
    if brief_path.is_file():
        try:
            brief_text = brief_path.read_text(encoding="utf-8")
        except OSError:
            pass

    # Extract topic from H1.
    topic = ""
    for line in brief_text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            topic = s[2:].strip()
            break
    if not topic:
        for line in brief_text.splitlines():
            s = line.strip()
            if s:
                topic = s[:200]
                break

    # 1. Topic match.
    if topic and query in topic.lower():
        results.append({
            "runId": run_id,
            "displayId": did,
            "topic": topic,
            "matchType": "topic",
            "snippet": topic,
        })

    # 2. Brief body match (beyond H1).
    for line in brief_text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            continue
        if s and query in s.lower():
            results.append({
                "runId": run_id,
                "displayId": did,
                "topic": topic,
                "matchType": "brief",
                "snippet": s[:200],
            })
            break

    # 3. Final doc match (final.md).
    final_path = session / "final.md"
    if final_path.is_file():
        try:
            final_text = final_path.read_text(encoding="utf-8")
        except OSError:
            final_text = ""
        for line in final_text.splitlines():
            s = line.strip()
            if s and query in s.lower():
                results.append({
                    "runId": run_id,
                    "displayId": did,
                    "topic": topic,
                    "matchType": "final",
                    "snippet": s[:200],
                })
                break


def _search_runs_supabase(client: Any, query: str) -> list[dict[str, Any]]:
    """Substring search across all runs in Supabase."""
    results: list[dict[str, Any]] = []

    # Get all run IDs and their briefs.
    try:
        runs_res = (
            client.table("runs")
            .select("id,slug")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
    except Exception:
        return results
    run_rows = runs_res.data or []
    # Spec 0082 — search must not surface hidden runs.
    if HIDDEN_RUN_IDS:
        run_rows = [r for r in run_rows if r.get("id") not in HIDDEN_RUN_IDS]
    if not run_rows:
        return results

    run_ids = [r["id"] for r in run_rows]

    # Fetch briefs for topic search.
    try:
        briefs_res = (
            client.table("session_files")
            .select("run_id,content")
            .in_("run_id", run_ids)
            .eq("path", "brief.md")
            .execute()
        )
    except Exception:
        briefs_res = None
    briefs: dict[str, str] = {}
    if briefs_res and briefs_res.data:
        briefs = {row["run_id"]: row["content"] for row in briefs_res.data}

    for r in run_rows:
        rid = r["id"]
        did = display_id(rid)
        brief_text = briefs.get(rid, "")
        topic = _extract_h1(brief_text)

        # Topic match.
        if topic and query in topic.lower():
            results.append({
                "runId": rid,
                "displayId": did,
                "topic": topic,
                "matchType": "topic",
                "snippet": topic,
            })

        # Brief body match.
        for line in brief_text.splitlines():
            s = line.strip()
            if s.startswith("# "):
                continue
            if s and query in s.lower():
                results.append({
                    "runId": rid,
                    "displayId": did,
                    "topic": topic,
                    "matchType": "brief",
                    "snippet": s[:200],
                })
                break

        if len(results) >= _MAX_SEARCH_RESULTS:
            break

    return results[:_MAX_SEARCH_RESULTS]


# ─── snake_case → camelCase translation ──────────────────────────────────────


_SNAKE_RE = re.compile(r"_([a-zA-Z])")


# Spec 0148 — single-segment canonical-ID allowlist for ``_to_camel``. Sourced
# from the artifact registry at import time so future single-segment IDs
# (e.g. a hypothetical ``final_draft``) are picked up without code change.
# Dotted IDs (``user_prompt.message``, etc.) are already handled by the
# ``"." in k`` guard inherited from spec 0146; this allowlist closes the
# single-segment hole that the FE ``normalisePiecesRaw`` shim used to cover.
from dual_research.contract.artifacts import REGISTRY as _ARTIFACT_REGISTRY

_CANONICAL_SINGLE_SEGMENT_IDS: frozenset[str] = frozenset(
    artifact.id_template
    for artifact in _ARTIFACT_REGISTRY
    if "." not in artifact.id_template and "<" not in artifact.id_template
)


def _snake_to_camel(name: str) -> str:
    """``"phase_timings"`` → ``"phaseTimings"``. Single-trailing-underscore
    fields (``in_``) lose the trailing underscore."""
    if name.endswith("_") and not name.endswith("__"):
        name = name[:-1]
    return _SNAKE_RE.sub(lambda m: m.group(1).upper(), name)


def _to_camel(obj: Any) -> Any:
    """Recursively rewrite string dict keys snake_case → camelCase.

    Non-string keys (e.g. the ``int`` keys in ``phase_timings``) are coerced
    to ``str`` so the result is JSON-serializable directly. List order and
    primitive values are preserved.

    Spec 0146 — dotted keys are canonical artifact IDs (the Python registry
    is the source of truth) and pass through verbatim. Without this guard
    ``user_prompt.message`` arrives at JS as ``userPrompt.message`` and the
    Consumption-card per-piece lookups silently miss.

    Spec 0148 — extends the guard with an import-time-derived allowlist of
    single-segment canonical IDs (``user_prompt``, ``current_draft``,
    ``all_p2_turns``, …). Before this guard, those keys were camelCased
    on the wire and the frontend inverted them via ``normalisePiecesRaw``;
    that workaround is retired in this PR so the canonical-ID contract
    matches end-to-end. New single-segment additions to the registry are
    picked up automatically.
    """
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str):
                if "." in k or k in _CANONICAL_SINGLE_SEGMENT_IDS:
                    out[k] = _to_camel(v)
                else:
                    out[_snake_to_camel(k)] = _to_camel(v)
            else:
                out[str(k)] = _to_camel(v)
        return out
    if isinstance(obj, list):
        return [_to_camel(v) for v in obj]
    return obj


# ─── CLI entry point ──────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dual-research serve",
        description="Run the dual-research monitoring UI server.",
    )
    p.add_argument("--host", default="127.0.0.1", help="Bind host (default 127.0.0.1).")
    p.add_argument("--port", type=int, default=6173, help="Bind port (default 6173).")
    p.add_argument(
        "--runs-dir",
        metavar="PATH",
        help="Where to read session directories from. Default: <project>/runs/.",
    )
    p.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn auto-reload (dev only).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``dual-research serve``."""
    import uvicorn

    parser = _build_parser()
    args = parser.parse_args(argv)

    backend = os.environ.get("RUNS_BACKEND", "fs").strip().lower()

    if backend == "supabase":
        from dual_research.config import load_supabase_credentials
        from dual_research.persistence.remote import RemoteSession

        sb = load_supabase_credentials()
        remote = RemoteSession.from_credentials(sb.url, sb.service_role_key)
        client = remote._client  # internal handle is fine — same package
        print(
            f"dual-research UI server v{__version__}\n"
            f"  backend: supabase ({sb.url})\n"
            f"  auth: Supabase / Google OAuth\n"
            f"  listening on http://{args.host}:{args.port}\n",
            file=sys.stderr,
        )
        app = _make_supabase_app(
            client,
            supabase_url=sb.url,
            supabase_anon_key=sb.anon_key,
        )
    else:
        paths = resolve_paths(args.runs_dir)
        runs_dir = paths.runs_dir.resolve()
        print(
            f"dual-research UI server v{__version__}\n"
            f"  backend: fs (local, unauthenticated)\n"
            f"  runs-dir: {runs_dir}\n"
            f"  listening on http://{args.host}:{args.port}\n",
            file=sys.stderr,
        )
        app = _make_app(runs_dir)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


__all__ = ["main", "_make_app", "_make_supabase_app"]
