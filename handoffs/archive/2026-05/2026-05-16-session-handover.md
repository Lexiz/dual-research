# Session handover — 2026-05-16

A snapshot of the project at the end of a long session that shipped the
hosted-deployment track (spec 0019 → 0024). Read this first; it tells
you what's live, what's open, and what to ask the user about before
starting the next bit of work.

---

## 1 · Where the project is

**Local tool:** `~/dual-research`, on `main`, **v0.22.0 expected after
the open PR merges**. The HEAD of `main` at the moment this handover is
written is one commit behind v0.22.1: the `spec/0024-header-pass-2-theme-toggle`
branch has the v0.22.1 changes plus this handover bundled into a single
PR (see §5).

**Hosted UI:** **https://dual-research-alex.fly.dev/** — live, gated by
Google OAuth + email allowlist. The single Fly machine in `iad`
auto-stops when idle (~5 min) and warms in ~2 s on first hit.

**Sign-in:** user's Google account `alex.lisitzky@gmail.com`, seeded as
admin in the `approved_emails` table.

**Tests:** 277 pytest cases green. `uv run pytest tests/ -q`.

---

## 2 · What shipped in this session (spec 0019 → 0024)

| Spec | Title | What landed |
|---|---|---|
| 0019 | Supabase schema + `--push` CLI | New Postgres tables (runs / events / session_files) + `dual-research --push runs/<dir>` to bulk-upload a completed session-dir. |
| 0020 | Fly deploy of the UI server | Dockerfile, fly.toml, `RUNS_BACKEND=fs|supabase` toggle, supabase-backed aggregator path (materialize tmpdir + reuse existing aggregator). HTTP Basic auth as a stopgap. |
| 0021 | Google OAuth + email allowlist | Supabase Auth wired to Google. `SupabaseAuthMiddleware` validates Bearer tokens + checks `approved_emails`. Frontend SDK bootstrap, `/api/config`, landing+sign-in screens, `authedFetch`. Basic auth removed. |
| 0022 | Admin allowlist UI + profile menu + landing redesign | `#/settings` (admin-only allowlist CRUD with self-delete + last-admin protection). Avatar dropdown in the chrome bar (Design / Settings / Sign out). Landing page with two-agent SVG + Google brand button. |
| 0023 | Compact header (pass 1) + How-it-works page + release notes | Run-detail header 4 rows → 2 rows. New `#/how-it-works` static page with hand-rolled SVGs explaining the protocol end-to-end, plus a `VERSION_NOTES` array (release notes). CONTRIBUTING.md asks future user-visible specs to append. |
| 0024 | Header (pass 2) + compact theme toggle | Drops TOPIC tag and in-header back arrow; chrome bar's "All runs" tab swaps to a back arrow when on a detail view. Status badge composes with the errors count when present. Cost+tokens single badge. Theme toggle: single pill, sun + moon icons. |

The hosted-deployment kickoff (`handoffs/hosted-deployment-kickoff.md`,
spec 0018) is fully delivered. The "spec roadmap" in §3 of that doc is
complete except for **0023 (kickoff-from-UI)** — see §3 below, which
remains the unbuilt feature.

---

## 3 · What's still open

### The "bigger feature" the user wants to do next

End of this session the user said:

> "Now we come to the actual new feature. I would like several things.
> Let's first implement this, and then we'll do the bigger feature."

They never described that feature. **Ask them what it is** before
making assumptions. Plausible candidates given the trajectory:

- Kickoff-from-UI: a "New run" form on the hosted UI that enqueues a
  job and runs the orchestrator. The original kickoff doc earmarks
  this as the post-hosted spec (originally numbered 0023 there — now
  whatever the next available number is, so **0025+**).
- A different feature entirely. Don't assume.

### Carryovers from the integration track (still deferred)

Originally from `handoffs/integration-state.md`, intentionally not
fixed in 0019–0024:

| # | Issue | File |
|---|---|---|
| I6 | Old fixture runs show as `running` forever; no liveness probe | `ui/labels.py` |
| I8 | `currentTurn.body` keeps full final-doc in every SSE snapshot post-completion | `ui/aggregator.py` |
| I9 | "connected" pill on the All-runs view (no SSE there) | `ui/static/app.jsx` |
| I10 | `final.md` metadata header reports wrong duration | `orchestrator/finalize.py` |
| I11 | `ErrorCard` may crash on errored runs | `ui/static/run-detail.jsx::ErrorCard` |

None block any feature; pick up between feature specs whenever
convenient. Bundle into a single PATCH spec ("Live-run polish") to
keep noise down.

### Known papercut introduced or not yet fixed in this session

- **`rounds` column on the supabase-mode all-runs list is blank.**
  Computing it cheaply needs either an events count-aggregate query or
  a denormalized column. Cosmetic. Noted in spec 0019.
- **`pyiceberg` has no Python 3.14 wheel** as of writing, so the Fly
  Dockerfile uses `python:3.14` (full) instead of `-slim`. Adds
  ~150 MB; revisit when pyiceberg ships a 3.14 wheel.
- **Polling rate for hosted live updates is 5 s** (`SUPABASE_STREAM_POLL_SECONDS`).
  Tune if a real live-run viewing scenario matters.

---

## 4 · How everything is wired (orientation map)

### Backend

- `src/dual_research/cli.py` — orchestrator CLI plus `--push`.
- `src/dual_research/persistence/remote.py` — `RemoteSession.push_session_dir()`.
- `src/dual_research/ui/server.py` — FastAPI. Two app factories:
  - `_make_app(runs_dir)` — fs mode, ungated.
  - `_make_supabase_app(client, ...)` — supabase mode, gated by
    `SupabaseAuthMiddleware`. Exposes `/api/me`, `/api/config`,
    `/api/approved-emails*`, run endpoints, and a polled SSE stream.
- `src/dual_research/ui/auth.py` — `SupabaseAuthMiddleware`. Plumbs
  `scope["user"] = {email, is_admin, token}`. Cached 60 s per token.
- `src/dual_research/ui/datasource.py` — `SupabaseSessionData.materialize()`
  rebuilds an aggregator-shaped tmp dir from supabase tables.
- `src/dual_research/config.py` — `load_credentials()` (Anthropic/OpenAI/Notion)
  and `load_supabase_credentials()` (URL + anon + service-role).

### Frontend (`src/dual_research/ui/static/`)

Loaded in this order from `index.html`:

- `shared.jsx` — tokens, primitives, `Icon` map, `fmt` helpers, agent
  glyphs.
- `auth.jsx` — Supabase JS SDK bootstrap, `useSupabaseClient`,
  `useSession`, `useMe`, `authedFetch`, `LandingScreen`,
  `NotApprovedScreen`.
- `live-data.jsx` — `useLiveRun` (polls /api/runs/:id every 5 s),
  `useRunList` (polls /api/runs every 3 s), `useFileBody`. All
  via `authedFetch`.
- `router.jsx` — hash routes: `/`, `/runs/:id`, `/language`,
  `/settings`, `/how-it-works`.
- `run-detail.jsx` — `RunDetailHeader` (2 rows, post-spec-0024),
  `Timeline`, `DisagreementExplorer`, `RunErrorsView`, `Footer`,
  `RunDetail`.
- `run-list.jsx` — all-runs table.
- `errors.jsx` — global errors view.
- `design-language.jsx` — token reference (`#/language`).
- `settings.jsx` — admin allowlist CRUD (`#/settings`).
- `how-it-works.jsx` — protocol explanation + `VERSION_NOTES` array.
- `app.jsx` — top-level `App`, `ChromeBar`, `AvatarMenu`,
  `ThemeToggle`, `HowItWorksLink`, route render.

### Schema

- `supabase/migrations/0001_initial.sql` — runs / events / session_files.
- `supabase/migrations/0002_approved_emails.sql` — allowlist + seed.

Both applied manually via Supabase Dashboard → SQL Editor.

### Infra

- `Dockerfile` — `python:3.14` (full, due to pyiceberg), uv-managed.
- `fly.toml` — `dual-research-alex`, region `iad`, shared-cpu-1x@256mb,
  auto-stop, health check on `/api/health`.

### Tests

- `tests/persistence/test_remote.py` — push fake client.
- `tests/ui/test_datasource_supabase.py` — materialize.
- `tests/ui/test_server_supabase_mode.py` — supabase-mode endpoints.
- `tests/ui/test_supabase_auth.py` — middleware.
- `tests/ui/test_admin_endpoints.py` — /api/me + /api/approved-emails.
- `tests/ui/supabase_fake.py` — fake supabase client (read + upsert +
  delete + .auth.get_user).

---

## 5 · Git state at end of session

`main` at `e4b4d41` (spec 0023 merged).

Local branch `spec/0024-header-pass-2-theme-toggle` has spec 0024's
implementation + this handover bundled — opened as **one** PR rather
than two (deliberate user request to avoid two-merge churn). The
handover lives in this directory so the kickoff prompt below can
reference it.

Once that PR merges, `main` jumps to v0.22.1 with everything in this
handover applied. The hosted URL is already running v0.22.1 (deploys
went out before the PR landed — same divergence pattern as spec 0022;
not a problem in practice but worth knowing).

---

## 6 · Engineering workflow

Unchanged. `CONTRIBUTING.md` is authoritative:

```
spec → branch → implement → PR → admin squash-merge → next spec
```

One spec ↔ one branch ↔ one PR. The next spec number is **0025**.

Two house-keeping touches from this session:

1. **Step 5** of the workflow now asks specs that change user-visible
   behaviour to append a new entry to `VERSION_NOTES` in
   `how-it-works.jsx`. Internal-plumbing-only specs can skip.
2. **Feedback memory updated** at
   `~/.claude/projects/-Users-alexlisitzky/memory/feedback_low_reversal_just_decide.md`:
   for low-reversal-cost UI / design decisions, just pick and proceed;
   only escalate for high-reversal calls.

---

## 7 · Common operations cheat-sheet

```bash
# Run tests
uv run pytest tests/ -q

# Run a local research run
uv run dual-research --prompt "..."

# Push a completed run to Supabase (idempotent)
uv run dual-research --push runs/<session-dir>

# Local UI server (fs mode, ungated)
uv run dual-research serve

# Deploy hosted (remote builder, ~3-5 min)
cd ~/dual-research && flyctl deploy --remote-only --yes

# Live URL
open https://dual-research-alex.fly.dev/

# Fly secrets (already set, listed for reference)
#   SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
#   RUNS_BACKEND=supabase

# Local env vars in ~/.zshrc
#   ANTHROPIC_API_KEY, OPENAI_API_KEY, NOTION_TOKEN,
#   SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
```

---

## 8 · Pointers to the original briefings

- `handoffs/hosted-deployment-kickoff.md` — the spec-0018 doc that
  framed this whole track.
- `handoffs/integration-state.md` — the local-tool snapshot at the
  moment hosted work began.
- `handoffs/backend-state.md` — the original v0.9.0 backend handoff.
- `specs/0019-db-schema-and-push.md` through `specs/0024-header-pass-2-theme-toggle.md`
  — six specs in this session.

---

*Generated 2026-05-16 at the end of the session that shipped the
hosted-deployment track. Companion to `handoffs/hosted-deployment-kickoff.md`.*
