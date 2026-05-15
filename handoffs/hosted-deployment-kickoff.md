# Hosted deployment kickoff

Briefing for the next Claude Code session, which will start the
hosted-deployment track. Read this AFTER `handoffs/backend-state.md`
(v0.9.0, accurate) and `handoffs/integration-state.md` (v0.16.1+
snapshot of the local-tool state at the moment hosted work begins).

---

## 1 · Where we are at

- **Local tool at v0.16.2 on `main`.** Orchestrator + observability UI both work; integration verified end-to-end with two live test-tier runs; 223 tests green.
- **No hosted deployment.** Everything is `127.0.0.1:6173` against the local filesystem `runs/`.
- **The product goal has expanded.** The user now wants the UI publicly accessible at a real URL, gated by Google OAuth + admin-managed email allowlist, with data stored in a real database. Orchestrator stays local for now (run from the user's laptop) and pushes session data to the hosted DB. Later: a kickoff-from-UI feature so approved users can launch runs from the web (out of scope until 0023).

---

## 2 · Architectural decisions (locked in)

These were debated in the integration-session chat that produced spec 0018. The next session should not re-litigate them without a strong reason.

| Decision | Choice | Why |
|---|---|---|
| Hosting | **Fly.io** | The current backend (FastAPI + uvicorn + `watchfiles` + SSE) ports as-is; preserves architecture. Future "kickoff-from-UI" needs long-running compute (10–15 min per run) which Vercel serverless functions cannot do (60 s cap). |
| Database + auth | **Supabase** | Postgres + Google OAuth + email allowlist in one product; reduces the auth-spec from "build the flow" to "configure providers + write the allowlist check." Free tier covers a personal tool. |
| Orchestrator location | **Local laptop, push to hosted DB** | No need to ship API keys to the host; user's existing local workflow stays unchanged; cheapest path to a public UI. |
| UI codebase | **Keep current React+Babel-via-CDN bundle** initially | Already verified working; rewriting to Next.js is its own multi-day project. Port only if a concrete need (auth-aware routing, SSR perf) emerges. |
| Live updates on hosted UI | **Polling (3–5 s) initially**; consider Supabase realtime later | Simplest first-cut. The local instance already has true live-via-SSE; the hosted instance is for *sharing* finished or near-finished runs, where polling is fine. |
| Domain | Fly subdomain (`dual-research-<handle>.fly.dev`) initially; user owns a custom domain to point at it later | Free TLS either way. |

### Why Fly.io and not Vercel (short version)

User has a Vercel account and asked whether to use it. Two technical reasons dominated:

1. **The current backend is incompatible with Vercel serverless.** No persistent filesystem, no `watchfiles.awatch`, no long-lived SSE through 10–60-second function timeouts. Would require a full backend redesign before the hosted UI works at all.
2. **The future kickoff-from-UI goal is incompatible too.** A run is 8–15 min; Vercel functions cap at 60 s. Would need an external worker. Fly runs a normal Python process, so it just works.

If the user changes their mind and wants Vercel later, the path is: rewrite the API as Next.js routes + Vercel Postgres + an external Fly worker for long-running runs. That's bigger than just deploying as-is to Fly.

---

## 3 · Spec roadmap

| Spec | Title | Scope |
|---|---|---|
| 0019 | **DB schema + push CLI** | Design Supabase Postgres schema (runs, events, files, agents, errors, disagreements, phase_stats). Add `dual-research push <session-dir>` CLI subcommand that uploads a completed session-dir to Supabase via the Supabase Python client. Mirrors disk data; does NOT change orchestrator behaviour. Markdown bodies live in TEXT columns initially (small enough; can move to Supabase Storage if files get large). |
| 0020 | **Fly.io deployment** | Dockerize the `dual-research serve` UI server. New `fly.toml`. Adapt aggregator to read from Supabase instead of `runs/` (toggle via env var so local-FS mode still works). Polling for the live-runs list. Public URL on a Fly subdomain. |
| 0021 | **Google OAuth + email allowlist** | Wire Supabase auth on the FastAPI side; auth middleware that gates every `/api/*` and `/static/*` route. New `approved_emails` table seeded with the user's email as the first admin. Sign-in page (minimal — just a "Sign in with Google" button) when unauthenticated. |
| 0022 | **Admin route for the allowlist** | `#/admin` route, visible only to admins. CRUD on `approved_emails`. Bootstrap rule: at least one row marked `admin = true`. |
| 0023 (later) | **Kickoff-from-UI** | A "New run" form on the hosted UI that enqueues a job; a Fly worker (or the same machine) runs the orchestrator with the user's saved API keys. Bigger spec; out of scope until 0019–0022 land. |

Total estimated: 0019 ≈ 90 min, 0020 ≈ 120 min, 0021 ≈ 90 min, 0022 ≈ 45 min. Roughly two sessions of 2 hours each is the right unit, not one all-in.

---

## 4 · Pre-work the user must do before spec 0019 starts

These can't be done by the agent; they create accounts in third-party services.

- [ ] **Supabase account.** Create at https://supabase.com. Create a new project (region close to the user). Free tier is fine.
- [ ] **Capture Supabase credentials.** From Project Settings → API:
  - `SUPABASE_URL` (e.g. `https://abcdefg.supabase.co`)
  - `SUPABASE_ANON_KEY` (public, used by the browser if it ever calls Supabase directly)
  - `SUPABASE_SERVICE_ROLE_KEY` (private, used by the orchestrator's push CLI and the hosted server)
- [ ] **Add those to `~/.zshrc`** alongside `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`.
- [ ] **Fly.io account.** Create at https://fly.io. Install the CLI: `brew install flyctl`. Run `fly auth login`. The free tier covers one app + a small volume; this project sits well inside it.
- [ ] **Google Cloud OAuth client** — needed in spec 0021, not 0019. Skip for now; the next-next session walks you through this with Supabase's docs.

---

## 5 · Open design questions for spec 0019

The next session should answer these in the spec body before writing code.

1. **Bulk push or streaming?** Simplest first cut: bulk push at run end. `dual-research push <session-dir>` reads the completed session-dir and uploads everything in one transaction. Live-during-run streaming is a follow-up (and only matters once kickoff-from-UI exists). Recommend: **bulk for 0019**.
2. **Schema shape.** Two reasonable options:
   - **Normalized** (one table per event type — runs, turns, errors, etc.). More schema design upfront; cleaner queries.
   - **Event-log** (one `events` table with a JSONB payload, one `runs` table for top-level metadata). Less schema; defers shape decisions; queries are slightly clumsier.
   - Recommend: **event-log for 0019, normalize later if specific queries get painful.** Mirrors the on-disk `transcript.jsonl` model directly.
3. **Markdown bodies storage.** Two options:
   - **TEXT columns in a `session_files` table** with `path` + `content`. Simple; works for everything we have today.
   - **Supabase Storage** (object bucket). More moving pieces; only justified if files get large (>1 MB each, which they're not).
   - Recommend: **TEXT columns for 0019.** Move to Storage if/when a real `final.md` blows past a megabyte.
4. **Run-level row ID.** Use the session-dir name (`20260515-163105-live-integration-test`) as the natural key, or generate a UUID? Recommend: **session-dir name** — it's already globally unique, already exposed in the URL hash, already in `Run.id`.
5. **Idempotency.** What if `dual-research push <session-dir>` is run twice? Upsert by run id, replace files? Recommend: **upsert, replace files; safe to re-run**.
6. **Schema migrations.** Supabase has SQL editor; for now, hand-write the initial migration into `supabase/migrations/0001_initial.sql` and run it via the dashboard. Defer migration-tooling-as-code (`alembic`, `dbmate`, etc.) until we have more than one migration.

---

## 6 · Open carryovers from the integration track (orthogonal — pick up any time)

These were intentionally deferred from spec 0016/0017. None block the hosted-deployment track.

| # | Issue | File |
|---|---|---|
| I6 | Old fixture runs show as `running` forever; no liveness probe | `ui/labels.py` |
| I8 | `currentTurn.body` keeps full final-doc in every SSE snapshot post-completion | `ui/aggregator.py` |
| I9 | "connected" pill on All-runs view (no SSE there) | `ui/static/app.jsx` |
| I10 | `final.md` metadata header reports wrong duration | `orchestrator/finalize.py` |
| I11 | `ErrorCard` crashes on errored runs (pre-existing) | `ui/static/run-detail.jsx::ErrorCard` (line ~827) |

Cleanest packaging: one PATCH spec ("Live-run polish") bundling I6+I8+I9+I10+I11 → v0.17.x. ~30 min, no API spend, fully testable against existing fixtures. Pick up between hosted-deployment specs whenever convenient.

---

## 7 · Engineering workflow (unchanged)

Same `spec → branch → implement → PR → admin squash-merge` as
`CONTRIBUTING.md`. Next spec number after 0018 is **0019**.

---

## 8 · Paste this into the next Claude Code session

Open Claude Code in `~/dual-research`, then paste the block below verbatim:

```
We just shipped spec 0018 — a documentation-only kickoff for a new
multi-session track that takes dual-research from a local tool to a
publicly accessible, Google-auth-gated, DB-backed hosted UI.

Read these three documents before doing anything else:

1. `handoffs/hosted-deployment-kickoff.md` — the primary briefing for
   this track. Sections 2 (locked architectural decisions), 3 (spec
   roadmap), 4 (user pre-work), and 5 (open design questions for spec
   0019) are load-bearing.

2. `handoffs/integration-state.md` — snapshot of the local-tool state
   at the moment hosted work begins. Confirms v0.16.2 is the baseline.

3. `handoffs/backend-state.md` — original backend handoff at v0.9.0;
   the orchestrator hasn't changed materially since.

Then start spec 0019 — DB schema + `dual-research push` CLI.

Before writing the spec:

a. Confirm the user has completed the pre-work in
   handoffs/hosted-deployment-kickoff.md §4 (Supabase project +
   credentials in ~/.zshrc, Fly.io CLI installed). If anything's
   missing, surface that first and stop.

b. Choose answers to the open design questions in
   handoffs/hosted-deployment-kickoff.md §5. The recommendations there
   are sensible defaults; only deviate with a stated reason in the spec
   body.

c. Write specs/0019-db-schema-and-push.md following CONTRIBUTING.md
   (label: new-feature; MINOR bump to 0.18.0). Then branch, implement,
   open a PR, admin-squash-merge.

Concrete deliverables for spec 0019:

- `supabase/migrations/0001_initial.sql` — full schema (runs, events,
  session_files, plus any small lookup tables).
- New module `src/dual_research/persistence/remote.py` (or similar) — a
  client that talks to Supabase via the supabase-py SDK or via plain
  asyncpg/psycopg, your call. State the choice in the spec.
- New CLI subcommand `dual-research push <session-dir>` — bulk uploads
  a completed session-dir to the configured Supabase project.
  Idempotent (upsert by run id).
- Env-var wiring for SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in
  config.py.
- Tests with a Supabase test project OR a docker-compose Postgres so
  CI doesn't depend on a live Supabase. Pick whichever is cheaper to
  set up; document in the spec.

Required env vars on the user's machine: ANTHROPIC_API_KEY,
OPENAI_API_KEY (existing), plus SUPABASE_URL and
SUPABASE_SERVICE_ROLE_KEY (new — confirmed in §4 pre-work above).

Engineering posture: same as ever — single-author repo, linear `main`
via squash-merges of `spec/NNNN-<slug>` branches, every change starts
with a spec. CONTRIBUTING.md is the source of truth.

Start by reading the three handoff docs.
```

---

*Generated 2026-05-15. Spec 0018. Companion to `handoffs/integration-state.md`.*
