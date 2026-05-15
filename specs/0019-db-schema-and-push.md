---
spec: 0019
title: Supabase schema + `--push` CLI for hosted-deployment track
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.18.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/19"
---

# Spec 0019 — Supabase schema + `--push` CLI

## Context

Spec 0018 (the [hosted-deployment kickoff](../handoffs/hosted-deployment-kickoff.md))
established a multi-session track that takes `dual-research` from a
local tool to a publicly accessible, Google-auth-gated, DB-backed UI.
The architectural decisions are locked in there — Fly.io for hosting,
Supabase for Postgres + Google OAuth + email allowlist, and an
orchestrator that **stays local** and pushes session data to the hosted
DB rather than running on the host. The reasoning (Vercel's serverless
timeouts can't host 8–15-minute runs; sending API keys to a host adds
risk for no benefit) is in the kickoff doc §2.

This spec is the **first** of that track. It mirrors a completed
session-dir into Supabase Postgres so the hosted UI server (spec 0020)
can read runs from the DB instead of `runs/`. It does **not** change
orchestrator behaviour — `dual-research --prompt …` still writes the
same files to the same `runs/` directory. The push is an explicit
follow-up step (`dual-research --push runs/<session-dir>`) the user
runs after a completed run.

Pre-work in the kickoff doc §4 is done: the user has a Supabase project
(`https://qpdsxspdwqukircrfqkm.supabase.co`), credentials live in
`~/.zshrc`, and `flyctl` is installed and authenticated. Three new env
vars are now expected:

- `SUPABASE_URL` — project URL (no path).
- `SUPABASE_ANON_KEY` — public/browser key. Holds the new-format
  `sb_publishable_…` string; spec 0020+ will use it browser-side. Not
  used in 0019 — declared now so we wire all three at once.
- `SUPABASE_SERVICE_ROLE_KEY` — secret key (new format `sb_secret_…`).
  Used by the push CLI; bypasses RLS.

## Design decisions

The kickoff doc §5 listed six open design questions with recommended
answers. This spec adopts all six recommendations; rationale per row:

| # | Decision | Why |
|---|---|---|
| Q1 | **Bulk push at run end**, no live streaming | Simplest first cut. Live-during-run streaming only matters once we have kickoff-from-UI (spec 0023+). Until then, the orchestrator writes to disk and the user pushes when a run is "done enough to share". |
| Q2 | **Event-log schema** (one `events` table with JSONB payload + a `runs` table for top-level metadata) — *not* normalised per event type | Mirrors `transcript.jsonl` directly. No schema-design upfront; we can normalise later if a specific query gets painful. |
| Q3 | **TEXT columns** for markdown bodies (in `session_files`) — not Supabase Storage | Largest `final.md` we've seen is ~30 KB. Postgres TOAST handles multi-MB TEXT cells transparently. Move to Storage if a real run pushes past 1 MB per file. |
| Q4 | **Session-dir name as the run primary key** (e.g. `20260515-163105-live-integration-test`) — not a UUID | Already globally unique by construction (timestamp prefix). Already exposed in `Run.id` and the URL hash. Foreign keys are TEXT not UUID, slightly heavier indexes — fine at this scale. |
| Q5 | **Upsert by run id, replace files on re-push** | `dual-research --push` should be safe to re-run after a partial failure. The semantics are "the disk truth wins; replace what's in the DB for this run." |
| Q6 | **Hand-written SQL migration**, applied via Supabase Dashboard SQL editor | Migration tooling-as-code (alembic, dbmate) is overkill for one migration. Revisit when we have >1. |

Two further choices not in the kickoff:

- **Client library: `supabase-py>=2.9`** (PostgREST over HTTPS), not
  raw `asyncpg`/`psycopg`. Reasoning: (a) the existing env vars are
  REST-API-style (URL + service-role key), not a Postgres DSN; using
  the SDK avoids requiring a 4th env var (`SUPABASE_DB_URL`); (b) push
  isn't performance-critical (≤ few hundred rows per run); (c) recent
  `supabase-py` versions accept the new `sb_secret_*` key format. If
  perf becomes a problem in spec 0020+, swap to `psycopg` behind the
  same `RemoteSession` interface — the API surface outside
  `persistence/remote.py` doesn't change.
- **CLI shape: `--push <session-dir>` as a new mutually-exclusive
  mode**, alongside `--prompt` / `--brief` / `--notion` / `--resume`
  — *not* an argparse subcommand (`dual-research push <dir>`).
  Reasoning: subcommand restructuring would break the existing
  top-level invocation (`dual-research --prompt "…"`) and is bigger
  than this spec needs. `--push <dir>` mirrors `--resume <dir>`
  exactly. The kickoff doc proposed the subcommand form; this is a
  stated deviation per kickoff §0.

## Proposed change

### Schema — `supabase/migrations/0001_initial.sql`

Three tables. Foreign keys cascade so deleting a run cleans up its
events and files. JSONB everywhere it makes sense — readable in the
Supabase Table Editor, queryable with `->` / `->>`.

```sql
-- runs: one row per session directory.
CREATE TABLE runs (
    id              TEXT PRIMARY KEY,         -- session-dir name
    slug            TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL,     -- from session-dir name prefix
    pushed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_tier      TEXT,                     -- 'prod' | 'test'
    claude_model    TEXT,
    openai_model    TEXT,
    phase_reached   TEXT,                     -- 'phase0'..'phase4' | 'final'
    exit_code       INT,
    duration_ms     BIGINT,
    total_cost_usd  NUMERIC(10, 4),
    confidence      TEXT,                     -- 'HIGH' | 'MODERATE' | 'LOW' | NULL
    state           JSONB,                    -- full state.json
    metrics         JSONB                     -- full metrics.json
);

CREATE INDEX runs_created_at_idx ON runs (created_at DESC);

-- events: append-only mirror of transcript.jsonl, one row per JSONL line.
CREATE TABLE events (
    run_id      TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    seq         INT NOT NULL,                 -- 0-based line index in JSONL
    ts          TIMESTAMPTZ NOT NULL,         -- from JSONL `ts` field
    kind        TEXT NOT NULL,                -- from JSONL `event` field
    payload     JSONB NOT NULL,               -- everything else from the JSONL line
    PRIMARY KEY (run_id, seq)
);

CREATE INDEX events_run_kind_idx ON events (run_id, kind);

-- session_files: every .md/.json/etc. file under the session dir.
CREATE TABLE session_files (
    run_id      TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    path        TEXT NOT NULL,                -- e.g. 'phase2/round-01-claude.md'
    content     TEXT NOT NULL,
    size_bytes  INT NOT NULL,
    PRIMARY KEY (run_id, path)
);
```

No Row Level Security policies — service-role bypasses RLS anyway, and
spec 0021 will add the auth layer. The hosted UI (spec 0020) will read
via the service-role too until 0021.

### Python — `src/dual_research/persistence/remote.py` (new)

A thin push client. Public API:

```python
class RemoteSession:
    def __init__(self, url: str, service_role_key: str): ...
    def push_session_dir(self, session_dir: Path) -> PushSummary: ...
```

Reads, in order:
1. The session-dir name (PK).
2. `state.json` → `runs.state` JSONB, `runs.phase_reached`, `runs.drafter`.
3. `metrics.json` → `runs.metrics` JSONB, `runs.total_cost_usd`,
   `runs.duration_ms` (computed from `started_at` / `ended_at`).
4. `final.md` first line metadata header → `runs.confidence`,
   `runs.exit_code` (if present), `runs.claude_model` /
   `runs.openai_model` / `runs.model_tier` (the header has all three).
5. `transcript.jsonl` → batched insert into `events` (one chunk per
   ~500 lines to stay under PostgREST request-size limits).
6. Every file under the session-dir matching `*.md`, `*.json`,
   `*.jsonl` (transcript already covered as events; included here too
   as a verbatim backup) → batched upsert into `session_files`.

Idempotency: every write is `upsert(on_conflict=primary_key)`. Re-push
replaces the row's contents.

`PushSummary` dataclass returns `runs: 1, events_inserted: N,
files_inserted: M, duration_ms: …` so the CLI prints a useful summary.

### Config — `src/dual_research/config.py`

Add a second credentials dataclass + loader:

```python
@dataclass(frozen=True)
class SupabaseCredentials:
    url: str
    anon_key: str
    service_role_key: str

def load_supabase_credentials() -> SupabaseCredentials:
    url = os.environ.get("SUPABASE_URL", "").strip()
    anon = os.environ.get("SUPABASE_ANON_KEY", "").strip()
    service = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    missing = [n for n, v in [
        ("SUPABASE_URL", url),
        ("SUPABASE_ANON_KEY", anon),
        ("SUPABASE_SERVICE_ROLE_KEY", service),
    ] if not v]
    if missing:
        raise MissingCredentialError(
            "Missing Supabase environment variable(s): " + ", ".join(missing)
        )
    return SupabaseCredentials(url=url, anon_key=anon, service_role_key=service)
```

Existing `load_credentials()` is untouched — Anthropic/OpenAI/Notion
loading is orthogonal to the Supabase load. `--push` calls the new
loader; orchestrator runs call the existing one.

### CLI — `src/dual_research/cli.py`

Add `--push <session-dir>` to the existing mutually-exclusive input
group:

```
src.add_argument("--push", metavar="DIR",
                 help="Push a completed session-dir to Supabase.")
```

`_dispatch(args)` recognises `args.push`, calls
`load_supabase_credentials()`, instantiates `RemoteSession`, calls
`push_session_dir(Path(args.push))`, prints the summary, returns exit
code 0. Errors (missing env, malformed session-dir, network failure)
exit non-zero with a one-line message — same pattern as
`MissingCredentialError` today.

The push path explicitly does NOT load
`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` — those are needed for
orchestrator runs, not for a metadata push.

### Dependency — `pyproject.toml`

```
"supabase>=2.9",
```

added to `dependencies`. The SDK's transitive deps (`gotrue`,
`postgrest`, `realtime`, `storage3`) come with it. No optional extras.

### Version + CHANGELOG

`pyproject.toml` 0.17.0 → 0.18.0. `__init__.py` ditto.
`CHANGELOG.md` gets a new `## [0.18.0]` entry under "Added".

## Out of scope

- **Hosted UI server reading from Supabase** — spec 0020. The
  aggregator in `ui/aggregator.py` still reads `runs/` from disk after
  this spec. Spec 0020 will add a `RUNS_BACKEND=fs|supabase` toggle.
- **Live streaming during a run.** No SSE-to-Supabase bridge.
  `dual-research --push` is a manual, post-run command. Streaming
  becomes interesting after spec 0023 (kickoff-from-UI).
- **Auth, RLS, the `approved_emails` table.** All deferred to spec
  0021. The DB is wide-open behind the service-role key for now.
- **Schema migration tooling.** Hand-write `0001_initial.sql`; apply
  via Supabase Dashboard. Migration tooling (`dbmate`, `alembic`,
  `supabase migration up`) is overkill for one migration; revisit
  when we have a second.
- **`runs` cleanup / retention.** Pushing the same run twice replaces
  its rows; deleting a run from disk doesn't delete it from Supabase.
  Hosted-side cleanup is a future concern.
- **Brief media** (Notion-fetched images, attachments). Current
  orchestrator doesn't emit any binary artifacts; if it ever does,
  Supabase Storage is the right home — but not in this spec.
- **Push from the orchestrator at run end** (auto-push on
  `RunCompleted`). Considered, deferred — the manual command is fine
  for one user and keeps run/push concerns separate.

## Test plan

Two layers:

### Unit (always run, no Supabase needed)

`tests/persistence/test_remote.py` — exercises `RemoteSession` against
a **fake supabase client** (in-memory dict-of-dicts). Verifies:

- [ ] A synthetic session-dir with `state.json` + `metrics.json` +
      `brief.md` + a small `transcript.jsonl` + two phase round files
      produces the expected `runs` / `events` / `session_files` rows.
- [ ] Re-pushing the same session-dir doesn't grow row counts (upsert
      replaces).
- [ ] A session-dir missing `state.json` raises a clear error before
      any DB writes.
- [ ] An empty `transcript.jsonl` results in zero `events` rows
      (still inserts a `runs` row).
- [ ] `events` rows have monotonically increasing `seq` matching JSONL
      line order.
- [ ] `session_files` includes `.md`, `.json`, `.jsonl` files but not
      hidden `.tmp*` files (atomic-write detritus).
- [ ] `runs.duration_ms` is computed from
      `metrics.ended_at - metrics.started_at` when both are set, and
      NULL when either is missing.

`tests/config/test_supabase_credentials.py` — env-var loader rejects
missing vars with the expected error message and accepts a clean set.

### Integration (gated)

`tests/persistence/test_remote_integration.py` —
`@pytest.mark.integration`, skipped by default. Requires
`SUPABASE_TEST_URL` + `SUPABASE_TEST_SERVICE_ROLE_KEY` env vars (a
*separate* Supabase project from production; created locally when
running these). Verifies:

- [ ] End-to-end push against a real Supabase project: rows land,
      bodies round-trip, indexes are present.
- [ ] Re-push on the same project doesn't duplicate.

Not added to CI (no live Supabase secrets in CI yet). Documented in
the spec body and in the test docstring how to run them locally.

### Live verification (manual)

- [ ] Apply `supabase/migrations/0001_initial.sql` via the Supabase
      Dashboard SQL editor.
- [ ] Run `dual-research --push runs/20260515-163105-live-integration-test`
      against the real project. Confirm 1 run row, ≥1 events row, ≥6
      session_files rows in the Supabase Table Editor.
- [ ] Re-run the same push. Confirm row counts unchanged.

Total: ~10 new unit tests. 223 existing → ~233.

## Risks

- **`supabase-py` and the new `sb_secret_*` key format.** Recent
  versions of the SDK accept arbitrary-string keys (it just passes
  them through as `apikey` and `Authorization: Bearer`). If `2.9+` is
  not actually new-format-compatible, fallback path is two lines:
  swap the SDK out for direct HTTPS calls to `${URL}/rest/v1/<table>`
  with `apikey` + `Authorization: Bearer` headers. We'd find out at
  the very first unit-test pass against the fake (which doesn't care)
  *and* the first integration test (which would error 401). Cheap to
  detect, cheap to fix.
- **Request-size limits on PostgREST.** Supabase's default
  request-body cap is 1 MB. A run with a huge transcript could exceed
  this. Mitigation: batched inserts (chunk size 500 events / 50
  files); we don't push the entire transcript in one request. The
  largest session we've observed has ~300 transcript lines; well
  under one chunk.
- **`runs.created_at` parsing.** The session-dir name embeds a UTC
  timestamp (`20260515-163105-…`); we parse it back into a TIMESTAMPTZ.
  A malformed dir name would cause the push to fail at parse time
  before any DB writes — explicit error, no partial state.
- **TEXT vs Storage for markdown.** If a real `final.md` blows past
  ~1 MB, the row gets large but Postgres TOAST handles it; we'd
  notice from slow `session_files` selects. Migration path is in the
  decision table above; nothing in this spec is structurally locked
  to TEXT.
- **Idempotency edge: partial pushes.** If the network drops between
  the `runs` upsert and the `events` batch, the run row exists but
  events are partial. A re-push completes the work. We do *not*
  delete prior events on re-push (we replace by `(run_id, seq)`
  primary key on conflict); if the new push has fewer events than the
  prior (e.g. user truncated the transcript), stale rows linger.
  Acceptable for spec 0019; can add an explicit `DELETE … WHERE run_id
  = …` pre-batch in a follow-up if this matters.

## Open questions

None outstanding for this spec. Spec 0020 will need to decide:
realtime subscription vs polling on the hosted aggregator; the answer
is "polling, 3–5 s" per kickoff §2, but the implementation will
reopen the trade-off.
