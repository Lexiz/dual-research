---
spec: 0010
title: UI HTTP server with SSE
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.11.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/10"
---

# Spec 0010 — UI HTTP server with SSE

## Context

Spec 0009 added an internal aggregator that turns a session directory into a UI-shaped `Run` object. This spec exposes it over HTTP so the frontend (spec 0011) can fetch list rows, get the full snapshot for a run, and live-tail in-flight runs over Server-Sent Events.

The server is read-only and assumes the orchestrator (the existing `dual-research` CLI) is writing to `runs/<id>/` in a separate process. The integration point is the on-disk transcript file: when `transcript.jsonl` grows, the server reloads the snapshot and pushes a new SSE frame. No in-process pub/sub between orchestrator and server is required.

## Proposed change

### New module `src/dual_research/ui/server.py`

A FastAPI application plus a CLI entry point. Endpoints:

| Method | Path | Returns |
|---|---|---|
| `GET` | `/api/runs` | List of `RunListRow` (JSON) by scanning `runs-dir` |
| `GET` | `/api/runs/{run_id}` | Full `Run` snapshot (JSON) |
| `GET` | `/api/runs/{run_id}/stream` | SSE; emits one `snapshot` event per transcript-file change |
| `GET` | `/api/runs/{run_id}/files/{path:path}` | Raw markdown body as `text/plain; charset=utf-8` |
| `GET` | `/api/health` | `{"ok": true, "version": "...", "runs_dir": "..."}` |
| `GET` | `/` and `/static/*` | Static UI bundle (placeholder until spec 0011) |

Field translation: at the JSON boundary, Python snake_case → UI camelCase. Done via a small `_to_camel` recursive helper applied to `dataclasses.asdict` output. `TokenUsage.in_` becomes `in`. No camelCase leakage in the Python layer.

### CLI dispatch

`dual-research serve [--port 6173] [--host 127.0.0.1] [--runs-dir PATH]` — added to `src/dual_research/cli.py` as a one-line short-circuit on the first positional argument: when `argv[0] == "serve"`, hand off to `dual_research.ui.server.main`. Existing CLI flags are untouched.

### SSE protocol

The stream emits exactly one event type, `snapshot`, carrying the full JSON-serialized `Run`. The simplest contract for the UI — apply the snapshot, re-render, repeat. No per-field deltas; the JSON payload for a typical run is ~5–30 KB which is well under SSE practical limits.

Implementation:

```python
@app.get("/api/runs/{run_id}/stream")
async def stream(run_id: str):
    session = _resolve(run_id)
    async def events():
        # Initial snapshot
        yield _frame(load_run_snapshot(session))
        # Tail the transcript file
        transcript = session / "transcript.jsonl"
        async for _change_batch in awatch(session, recursive=False):
            if any(c[1].endswith("transcript.jsonl") for c in _change_batch):
                yield _frame(load_run_snapshot(session))
    return EventSourceResponse(events())
```

`watchfiles.awatch` polls the directory; on each batch it filters for `transcript.jsonl` changes and reloads. If `transcript.jsonl` doesn't exist yet, the initial snapshot is empty-ish and the watcher fires once the orchestrator creates the file.

### File endpoint security

`/api/runs/{run_id}/files/{path:path}` is path-scoped to the session dir:

```python
target = (runs_dir / run_id / path).resolve()
base   = (runs_dir / run_id).resolve()
if not str(target).startswith(str(base) + os.sep): 404
if not target.is_file(): 404
```

Only `.md`, `.json`, `.jsonl`, and `.txt` extensions are served. Anything else returns 404 (defensive; prevents accidental binary disclosure).

### New dependencies in `pyproject.toml`

- `fastapi>=0.115` — HTTP framework
- `uvicorn[standard]>=0.32` — ASGI server (the `[standard]` extra brings `watchfiles` + `httptools` for free)
- `sse-starlette>=2.1` — SSE response helper that handles client disconnect cleanly
- `watchfiles>=0.24` — async file watcher (already a transitive of uvicorn[standard], pinned for clarity)

### Tests under `tests/ui/test_server.py`

`httpx.AsyncClient` against the FastAPI app (no real network):

- `test_health_ok` — `/api/health` returns `{ok: true, version, runs_dir}`.
- `test_runs_list_empty_when_dir_missing` — empty list, 200.
- `test_runs_list_returns_rows` — write two fixture session dirs into `tmp_path`, assert order + count + `display_id` shape.
- `test_run_snapshot_404_when_absent` — non-existent id → 404.
- `test_run_snapshot_returns_camelcase` — verify `phaseTimings`, `agents.claude.tokens.in`, `startedAtAgo` are present.
- `test_file_endpoint_serves_markdown` — write `brief.md`; fetch returns body + `text/plain` content-type.
- `test_file_endpoint_rejects_path_traversal` — `..%2Fetc%2Fpasswd` → 404.
- `test_file_endpoint_rejects_non_text_ext` — `secret.pdf` → 404 even when present.
- `test_sse_emits_initial_snapshot` — connect, assert at least one `event: snapshot` frame.
- `test_sse_emits_followup_on_transcript_growth` — connect, append a line to `transcript.jsonl`, assert a second snapshot frame arrives (with a short timeout).

The SSE tests run inside the existing pytest-asyncio loop. Total: ~12 new tests; suite target ~190 green.

### CHANGELOG + version bump

`0.10.0 → 0.11.0`. New CHANGELOG entry documents the endpoint table.

## Out of scope

- **UI bundle wiring.** Spec 0011 populates `src/dual_research/ui/static/` with the JSX/CSS from `~/Trimble/handoff/` and adds the JS client.
- **Authentication.** Single-user local app on `127.0.0.1`. If the server ever moves off localhost we add auth in a future spec.
- **Compression.** SSE frames are uncompressed. A 30 KB snapshot on localhost is fine; gzip is a follow-up.
- **Live token streaming.** Backend doesn't emit per-token deltas; turn bodies become visible when their round file lands on disk (already handled by the aggregator).
- **Polling fallback.** All modern browsers support SSE; we don't ship a long-poll alternative.
- **Run-list SSE.** The "All runs" view polls `/api/runs` every 3 seconds (spec 0011); the server doesn't currently broadcast a global feed.

## Test plan

- [ ] 12 new tests under `tests/ui/test_server.py` pass
- [ ] All previous tests (179) still pass
- [ ] `uv run dual-research serve --port 6173` boots and responds to `curl http://127.0.0.1:6173/api/health`
- [ ] `curl http://127.0.0.1:6173/api/runs` returns a non-empty list when the local `runs/` dir has fixtures
- [ ] `curl http://127.0.0.1:6173/api/runs/<id>/files/brief.md` returns the markdown body
- [ ] Connecting to `/api/runs/<id>/stream` returns at least an initial snapshot

## Risks

- **`watchfiles` polling on macOS.** Native FS events on macOS are slightly less reliable than on Linux. `watchfiles` falls back to polling (50–200ms) when needed; latency is acceptable for a monitor UI. If it ever proves too slow we can also re-read on a 1s heartbeat.
- **SSE keepalive across proxies.** `EventSourceResponse` sends a keepalive comment every 15s by default. No risk on localhost; if anyone ever proxies this through nginx, document the buffering caveat then.
- **Large transcript file reads.** `load_run_snapshot` re-reads the full transcript on each emit. Worst case ~500 lines × ~200 bytes = 100 KB per re-read; sub-millisecond. If we ever exceed this we add a cached aggregator state per run_id keyed by file mtime.
- **Path traversal.** The file endpoint uses `Path.resolve()` + `startswith` of the realpath. Tested explicitly; no symlink escape since session dirs are created flat by the orchestrator.

## Open questions

None — the user is happy to ship the simplest working version and iterate.
