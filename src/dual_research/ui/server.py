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
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator

import base64
import mimetypes

from fastapi import FastAPI, HTTPException, Request
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
from dual_research.ui.datasource import SupabaseSessionData, latest_event_seq
from dual_research.ui.labels import display_id, derive_run_status, phase_to_int
from dual_research.ui.models import RunListRow, to_jsonable

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

    # ─── API routes ───────────────────────────────────────────────────────────

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "version": __version__,
            "runsDir": str(runs_dir),
        }

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

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str) -> JSONResponse:
        session = _resolve_session(runs_dir, run_id)
        run = load_run_snapshot(session)
        return JSONResponse(_to_camel(to_jsonable(run)))

    @app.get("/api/runs/{run_id}/stream")
    async def stream_run(run_id: str, request: Request) -> EventSourceResponse:
        session = _resolve_session(runs_dir, run_id)
        return EventSourceResponse(_run_event_stream(session, request))

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
        return JSONResponse(payload)

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

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "version": __version__, "backend": "supabase"}

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

    @app.get("/api/runs")
    async def list_runs() -> JSONResponse:
        rows = _supabase_list_runs(client)
        return JSONResponse([_to_camel(dataclasses.asdict(r)) for r in rows])

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str) -> JSONResponse:
        _require_run_exists(client, run_id)
        with SupabaseSessionData(client, run_id).materialize() as tmp:
            run = load_run_snapshot(tmp)
        # The tmpdir name was synthetic; restore the real run id everywhere.
        run.id = run_id
        run.display_id = display_id(run_id)
        return JSONResponse(_to_camel(to_jsonable(run)))

    @app.get("/api/runs/{run_id}/stream")
    async def stream_run(run_id: str, request: Request) -> EventSourceResponse:
        _require_run_exists(client, run_id)
        return EventSourceResponse(_supabase_event_stream(client, run_id, request))

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
        return PlainTextResponse(rows[0]["content"], media_type="text/plain; charset=utf-8")

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
        return JSONResponse(payload)

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
            "id,slug,created_at,phase_reached,exit_code,duration_ms,"
            "total_cost_usd,state,metrics"
        )
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    runs_rows = res.data or []
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


def _status_from_columns(*, phase_reached: str, exit_code: int | None, state: dict) -> str:
    """Map pushed-run columns onto the UI's status enum.

    Pushed runs are by definition completed (push happens post-run), so we
    only really see done / errored / deadlocked here.
    """
    final_emitted = bool(state.get("final_emitted_to"))
    run_failed = exit_code not in (None, 0, 51)
    hard_cap_hit = exit_code == 51
    return derive_run_status(
        state_phase=phase_reached,
        final_emitted=final_emitted,
        hard_cap_hit=hard_cap_hit,
        run_failed=run_failed,
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
    """Resolve a single input bundle from disk; synthesise Phase 0 if needed."""
    from dual_research.ui.aggregator import build_phase0_input_bundle

    key = _normalize_input_key(turn_key)
    if key is None:
        return None
    if key == "input":
        # Try a persisted bundle first; fall back to synthesis from brief.md.
        path = session / "inputs" / "input.json"
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
        return build_phase0_input_bundle(session)
    path = session / "inputs" / f"{key}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


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


def _read_input_bundle_supabase(client: Any, run_id: str, turn_key: str) -> dict | None:
    """Resolve a single input bundle from Supabase; synthesise Phase 0 if needed."""
    from dual_research.protocol.prompts import preflight_input_bundle

    key = _normalize_input_key(turn_key)
    if key is None:
        return None
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
            return json.loads(rows[0]["content"])
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    if key == "input":
        # Fall back to synthesis from brief.md (live in session_files).
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
            return None
        brief_rows = brief_res.data or []
        if not brief_rows:
            return None
        brief_text = brief_rows[0].get("content") or ""
        pieces = preflight_input_bundle(brief=brief_text, agent_name="<agent>")
        return {
            "agent": "shared",
            "phase": "phase0",
            "label": "phase0-input",
            "pieces": pieces,
            "emitted_at": "",
        }
    return None


async def _supabase_event_stream(
    client: Any,
    run_id: str,
    request: Request,
) -> AsyncIterator[dict]:
    """Polled SSE: emit a snapshot when max(events.seq) changes."""
    last_seq = -2  # force first emit even on empty events
    while True:
        if await request.is_disconnected():
            return
        current_seq = latest_event_seq(client, run_id)
        if current_seq != last_seq:
            with SupabaseSessionData(client, run_id).materialize() as tmp:
                run = load_run_snapshot(tmp)
            run.id = run_id
            run.display_id = display_id(run_id)
            yield {
                "event": "snapshot",
                "data": json.dumps(_to_camel(to_jsonable(run))),
            }
            last_seq = current_seq
        await asyncio.sleep(SUPABASE_STREAM_POLL_SECONDS)


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
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        raise HTTPException(status_code=404, detail="not found")


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


# ─── snake_case → camelCase translation ──────────────────────────────────────


_SNAKE_RE = re.compile(r"_([a-zA-Z])")


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
    """
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if isinstance(k, str):
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
