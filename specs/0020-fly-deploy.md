---
spec: 0020
title: Fly.io deployment of the UI server with Supabase-backed aggregator
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.19.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/20"
---

# Spec 0020 — Fly.io deployment + Supabase-backed UI

## Context

Spec 0019 shipped the Supabase schema and `dual-research --push` CLI. A
completed session-dir can now be mirrored into Postgres via three
tables (`runs`, `events`, `session_files`). What's still missing: a
**public URL** where those pushed runs are visible.

This spec deploys the existing `dual-research serve` UI server to
Fly.io and teaches it to read from Supabase instead of the local
filesystem. The orchestrator stays local; nothing on the user's laptop
changes. The hosted server is a thin read-only window onto whatever's
been pushed.

Auth is **not** in this spec — that's 0021. As a stopgap during the
0020 → 0021 interregnum, the hosted instance gates every route with
HTTP Basic auth tied to a `UI_BASIC_AUTH_PASSWORD` Fly secret. When
0021's Google OAuth lands, the env var and the middleware are removed
in the same PR. Local invocations of `dual-research serve` are
unaffected (no password → no gate).

## Design decisions

Every decision below was a "just decide" per the user's feedback —
none are hard to reverse, none lock anything in for future specs.
Listed here so you can scan and push back if any feel wrong:

| # | Decision | One-liner |
|---|---|---|
| D1 | **Materialize a temp directory per request** to bridge Supabase → aggregator | Aggregator stays untouched (~600 lines of tested logic). Per-request cost is single-digit milliseconds. |
| D2 | **Server-side polled SSE** for live updates | Server polls the `events` table every 5s, emits a `snapshot` SSE frame on `max(seq)` change. Frontend unchanged. |
| D3 | **`RUNS_BACKEND=fs\|supabase`** toggle, defaults to `fs` | Local mode is the default; Fly sets `RUNS_BACKEND=supabase`. One env var, one branch in the server factory. |
| D4 | **Single Docker image**, single process | FastAPI + uvicorn, multi-stage Python 3.14 build. No worker, no nginx, no compose. |
| D5 | **Fly app `dual-research-alex`** in region `iad` (US East) | Closest to most consumers; shared-cpu-1x@256 MB is plenty for one user. Free tier covers it. |
| D6 | **Auto-stop after 5 min idle** (Fly default) | Cold-start is ~2s. Fine for a "share this URL" use case. |
| D7 | **HTTP Basic auth as a stopgap** until 0021 | One Fly secret, one ~15-line middleware. Removed when OAuth lands. Local mode never gated. |
| D8 | **Static assets** served by FastAPI's `StaticFiles` mount, no CDN | Already wired today. ~50 KB of JSX served once per session — caching is browser-default. |
| D9 | **Logs** stream to stdout → Fly's log collector | uvicorn already writes there. Nothing new. |
| D10 | **App created out-of-band by the user**, `fly deploy` from the spec | First `fly apps create` is interactive (asks for region, billing card if not on file). One-time. After that, `fly deploy` is non-interactive. |

If any of these warrant a re-think, the spec body still applies —
deviations are confined to small bits below.

## Proposed change

### Aggregator-side: a Supabase data source (`src/dual_research/ui/datasource.py`, new)

```python
class SupabaseSessionData:
    def __init__(self, client: Client, run_id: str): ...
    def materialize(self, dest: Path) -> Path:
        """Hydrate a tmp directory with this run's files + a synthetic
        transcript.jsonl, return the path. Caller owns cleanup."""
```

The materializer queries `session_files` (paginated for safety) and
writes every row to `dest/<path>`. It also queries `events` (ordered by
`seq`) and reconstructs `transcript.jsonl` line by line — each row's
`payload` JSONB is dumped, then `ts` and `event` (kind) are reinjected
to match what the aggregator expects. End result: a tmpdir that looks
exactly like a real session-dir.

`load_run_snapshot(path)` and `summarize_run(path)` need no changes.

### Server-side: a backend toggle (`src/dual_research/ui/server.py`)

`_make_app` reads `RUNS_BACKEND` from the environment. When `supabase`,
it constructs a `RemoteSession` (reusing the spec-0019 client) and
wires the route handlers to:

- `GET /api/runs` — query `runs` ORDER BY `created_at DESC` LIMIT 100;
  map rows to `RunListRow` shape directly (no aggregator pass — much
  faster for the list view).
- `GET /api/runs/{id}` — materialize tmpdir → `load_run_snapshot`.
- `GET /api/runs/{id}/files/{path}` — `SELECT content FROM session_files
  WHERE run_id = $1 AND path = $2`. Direct.
- `GET /api/runs/{id}/stream` — start a 5s poll loop on
  `SELECT max(seq) FROM events WHERE run_id = $1`. Emit a new snapshot
  (via materialize+aggregate) when `max(seq)` increases. Close on
  client disconnect.
- `GET /api/health` — same as today.

When `RUNS_BACKEND=fs` (or unset), every code path matches today's
behaviour. The toggle is one if/else at the top of `_make_app`.

### HTTP Basic auth middleware (stopgap)

`src/dual_research/ui/auth.py` (new), ~20 lines:

```python
class BasicAuthMiddleware:
    def __init__(self, app: ASGIApp, expected_password: str): ...
    async def __call__(self, scope, receive, send):
        # 401 with WWW-Authenticate: Basic on missing/wrong creds.
        # Otherwise pass through.
```

`_make_app` attaches the middleware only when `UI_BASIC_AUTH_PASSWORD`
is set. Username is `dual-research`. The browser caches credentials
per origin, so users enter them once per session. Spec 0021 removes
this entire file in the same PR that wires Google OAuth.

### Docker + Fly

**`Dockerfile`** at project root, multi-stage:

```dockerfile
FROM python:3.14-slim AS base
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY src/ ./src/
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uv", "run", "dual-research", "serve", "--host", "0.0.0.0", "--port", "8080"]
```

**`.dockerignore`** excludes `.venv/`, `runs/`, `__pycache__/`,
`tests/`, `.git/`, the `handoffs/` directory, and `*.md` (except
README.md / CHANGELOG.md / CONTRIBUTING.md if we ever serve them).

**`fly.toml`** at project root, declares:

- `app = "dual-research-alex"`
- `primary_region = "iad"`
- `[http_service] internal_port = 8080`
- `auto_stop_machines = "stop"`, `auto_start_machines = true`, `min_machines_running = 0`
- `force_https = true`
- `[[vm]]` `size = "shared-cpu-1x"`, `memory = "256mb"`

Health check: Fly's default HTTP probe against `/api/health`.

### Secrets / env vars on Fly

Set via `fly secrets set` (one-time):

- `RUNS_BACKEND=supabase`
- `SUPABASE_URL=…`
- `SUPABASE_SERVICE_ROLE_KEY=…`
- `UI_BASIC_AUTH_PASSWORD=…` (we generate a random 24-char string and the user saves it)

`SUPABASE_ANON_KEY` is **not** set on Fly — the server uses the
service-role key. The anon key matters for spec 0021 when the browser
talks to Supabase directly for auth.

### Version + CHANGELOG

`pyproject.toml` 0.18.0 → 0.19.0. `__init__.py` ditto.
`CHANGELOG.md` gets a `## [0.19.0]` entry.

## Out of scope

- **Real auth** (Google OAuth + email allowlist) — spec 0021. Until
  then, HTTP Basic is the gate.
- **Admin route** (`approved_emails` CRUD) — spec 0022.
- **Kickoff-from-UI** — spec 0023.
- **Custom domain.** Ship at `dual-research-alex.fly.dev`. The user
  can point a custom domain at it later via `fly certs add` — one
  command, no spec needed.
- **Auto-push on `RunCompleted`.** Considered in spec 0019,
  deferred — still deferred. The user pushes manually after a run.
- **Live SSE through Supabase Realtime.** The 5-second poll is fine
  for sharing finished runs (the only hosted use case until 0023).
  Switching to Realtime is a contained refactor in `server.py`.
- **CDN / static asset optimisation.** ~50 KB of JSX over Fly's
  default Anycast TLS is fine.
- **Backup of pushed Supabase data.** Free tier includes daily
  backups; we accept that.
- **Reads from the `events` table via PostgREST count/aggregate
  endpoints.** We do a one-shot `max(seq)` poll; if Supabase ever
  charges per row scanned, we'd revisit.

## Test plan

### Unit

`tests/ui/test_datasource_supabase.py` (new) — uses the same fake
supabase client pattern from spec 0019:

- [ ] Materializing a known set of `session_files` rows produces the
      expected directory tree.
- [ ] Reconstructed `transcript.jsonl` round-trips: events written by
      the fake client are recoverable as a JSONL file the aggregator
      can replay.
- [ ] `summarize_run` against a materialized tmpdir produces the same
      `RunListRow` as it would against the original session-dir.

`tests/ui/test_server_supabase_mode.py` (new) — FastAPI's TestClient
against `_make_app(...)`:

- [ ] `GET /api/runs` returns rows from the `runs` table, sorted
      newest first.
- [ ] `GET /api/runs/{id}` returns the same Run shape as fs-mode does
      against the same data on disk.
- [ ] `GET /api/runs/{id}/files/missing.md` returns 404.
- [ ] Path-traversal attempts on `/files/{path}` return 404.

`tests/ui/test_basic_auth.py` (new):

- [ ] Without `UI_BASIC_AUTH_PASSWORD`, all routes return 200/404 as
      usual.
- [ ] With it set, missing/wrong creds return 401 with
      `WWW-Authenticate: Basic`.
- [ ] Correct creds pass through.

### Manual smoke (post-deploy)

- [ ] `fly deploy` succeeds; `fly status` shows a running machine.
- [ ] `https://dual-research-alex.fly.dev/api/health` returns 401
      (auth gate working).
- [ ] With basic-auth creds, `/api/health` returns ok + version 0.19.0.
- [ ] The all-runs list shows the run pushed in spec 0019.
- [ ] Opening the run-detail page renders the same Run shape the
      local UI shows.
- [ ] `/api/runs/.../files/final.md` returns the markdown body.

Total expected: ~12 new tests. 238 existing → ~250.

## Risks

- **Cold start.** Fly auto-stops the machine after 5 min idle. First
  request after idle takes ~2 s while the machine wakes. Acceptable
  for our use case (sharing finished runs); we'd revisit if the URL
  becomes load-bearing.
- **Supabase free-tier limits.** 500 MB database, 2 GB egress / month,
  50K monthly active users (irrelevant — we have one). Pushed runs
  are tiny (≤ 5 MB per run). Poll-driven egress is ~1 KB per 5s — at
  most ~70 MB / month if a user keeps the page open all day every day.
  Well inside limits.
- **Basic-auth weakness.** HTTP Basic over HTTPS is fine for "keep
  randos out" but is not real auth. Removed when 0021 lands. Don't
  share the URL widely until then.
- **Aggregator-on-tmpdir performance.** A single run snapshot
  materializes ~30 files. At ~50 KB per render request, this is
  invisible. If a future run has hundreds of files (it won't), we'd
  add per-run caching keyed on `events.max(seq)`.
- **Fly auth handshake on deploy.** `fly deploy` requires the user's
  Fly token. The user is already logged in (`flyctl auth login`
  succeeded in the pre-work). If the token expires before deploy, a
  `flyctl auth login` re-run is the fix.
- **`fly apps create` failure modes.** Requires a billing card on
  file even though we sit inside the free allowance. If the user
  hasn't added one yet, the CLI prompts for it. One-time friction.

## Open questions

- **Custom domain** — when does the user want their own domain?
  Out of scope for 0020 either way (one `fly certs add` away).
- **Realtime vs polling timing** — 5 s is a guess. Could be tuned
  down to 2 s if egress allows; the per-poll cost is one `SELECT
  max(seq)` per open detail-page client. Revisit if it ever matters.
