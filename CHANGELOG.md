# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Version bumps map to the `label` field on each merged spec:

- `breaking` → MAJOR
- `new-feature` → MINOR
- `bug` / `refactoring` / `test` → PATCH

## [Unreleased]

(Nothing yet.)

## [0.22.1] — 2026-05-16

### Changed

- **Run-detail header pass 2 + compact theme toggle** ([spec 0024](specs/0024-header-pass-2-theme-toggle.md)) — strip the redundant back-chip text (icon-only back arrow now), the dual-research brand pill, the gradient icon, and the copy-id chip. Topic gets a "TOPIC" caps tag. Cost merges with total tokens into one badge (`$0.4228 · 392Kt`). Status badge composes with the errors count when present (`completed | ⚠ 3 errors`, right half clickable to open the errors view). Phase progress dots move to row 2, right-aligned under the status. "PHASE N Label" and "converged in …" text removed (duplicated meta row). Header is now ~2 rows × ~28px, recovering another half-card of timeline space relative to spec 0023. The chrome bar's segmented light/dark toggle becomes a single compact pill with two icon buttons inside; same affordance, ~half the horizontal space. 277 tests still green.

## [0.22.0] — 2026-05-16

### Added

- **Compact run-detail header, "How it works" page, and release notes** ([spec 0023](specs/0023-header-howitworks-notes.md)) — three bundled UX changes. The run-detail header drops from four vertical rows to two: one primary row with back chip, merged dual-research/run-id pill, single-line topic, phase progress dots, phase label, cost, status, and a compact errors badge; one subtle mono meta row with started/drafter/elapsed/outcome (and in-flight round when applicable). Recovers about one timeline-card height. New "How it works" link in the chrome bar (right of the connection pill) opens a static page at `#/how-it-works` that walks through the protocol end-to-end: brief ingestion, the five phases with parallelism hints, hand-rolled inline SVGs of the phase flow and a single negotiation round, an FAQ covering "who goes first" (no-one — both agents fire via `asyncio.gather`), "fresh chats or one long chat" (fresh per turn; CACHE_BREAKPOINT is prefix caching, not a session), the tiebreak cascade, soft/hard cap behaviour, repair semantics. Release notes embedded as a `VERSION_NOTES` array seeded with v0.18 → v0.22 entries; CONTRIBUTING.md asks future user-visible specs to append a new entry there. New `Icon.Help` glyph. Static-only frontend work; no backend changes.

## [0.21.0] — 2026-05-15

### Added

- **Admin allowlist UI + profile menu + landing-page redesign** ([spec 0022](specs/0022-admin-and-polish.md)) — wraps up the hosted-deployment track with three user-facing upgrades. New admin route at `#/settings` (table of allowlist rows, inline add with optional admin checkbox, per-row remove) backed by four new endpoints: `GET /api/me` (email, isAdmin, avatarUrl, fullName from Google), `GET/POST /api/approved-emails`, `DELETE /api/approved-emails/{email}` — all admin-gated, with server-side protection against self-delete and removing the last admin (409 with a human-readable message). The chrome bar gains an **avatar dropdown** at the top-right: Google profile picture (deterministic-hue initials fallback when missing) opens a menu with Design language, Settings (admin only), and Sign out — the standalone Design link is gone. Landing page redesigned with a centered layout: a two-agent SVG visual (letter-mark "C" and "G" discs in the existing agent accent colours, dotted line + travelling dot between them), the wordmark, a tagline, and a properly-styled Google sign-in button. SupabaseAuthMiddleware now plumbs `is_admin` through the scope so admin handlers don't need a second DB lookup. 13 new unit tests; total 277.

## [0.20.0] — 2026-05-15

### Added

- **Google OAuth + email allowlist via Supabase Auth** ([spec 0021](specs/0021-google-oauth.md)) — the hosted UI now authenticates users via Google OAuth (mediated by Supabase Auth) and gates every `/api/*` request through an `approved_emails` allowlist. The HTTP Basic auth stopgap from spec 0020 is removed. New `supabase/migrations/0002_approved_emails.sql` defines the allowlist table and seeds the project owner as the first admin. New `SupabaseAuthMiddleware` validates Bearer tokens via `client.auth.get_user(token)` and checks the email against the allowlist, with a 60s in-memory cache keyed on token hash. `/api/health` and a new `/api/config` (returns `supabaseUrl` + `supabaseAnonKey` for the browser bootstrap) bypass the gate. Frontend gains `auth.jsx` (Supabase JS SDK bootstrap, `useSession` hook, sign-in screen, not-approved screen, top-level `authedFetch`). `live-data.jsx` switches from EventSource to `setInterval` polling (EventSource can't send `Authorization` headers; the kickoff doc preferred polling for hosted anyway) and uses `authedFetch` for every API call. Local `dual-research serve` (RUNS_BACKEND=fs) is never auth-gated. 10 new unit tests; 7 basic-auth tests removed. Total: 264.

## [0.19.0] — 2026-05-15

### Added

- **Fly.io deployment of the UI server with Supabase-backed aggregator** ([spec 0020](specs/0020-fly-deploy.md)) — the `dual-research serve` UI server can now run on Fly.io against the Supabase tables that spec 0019 introduced, so pushed runs are visible at a public URL. New `RUNS_BACKEND=fs|supabase` env var picks the backend at server boot — defaults to `fs` so local invocations are unchanged. In supabase mode, `/api/runs` queries the `runs` table directly (with a second query for `brief.md` topics) and the `/api/runs/{id}` + `/stream` paths materialize a tmp directory from `session_files` + `events` on each request, then hand it to the existing aggregator unchanged. New `Dockerfile` (python:3.14-slim, uv-managed deps) + `.dockerignore` + `fly.toml` (region `iad`, shared-cpu-1x@256mb, auto-stop after idle, health-check on `/api/health`). New `BasicAuthMiddleware` gates every route when `UI_BASIC_AUTH_PASSWORD` is set (Fly secret); `/api/health` always bypasses the gate so Fly's prober can see the machine. This middleware is a stopgap and gets removed in spec 0021 when Google OAuth lands. 22 new tests (datasource, supabase-mode server endpoints, basic-auth); total 260.

## [0.18.0] — 2026-05-15

### Added

- **Supabase schema + `--push` CLI** ([spec 0019](specs/0019-db-schema-and-push.md)) — first code change of the hosted-deployment track. New `supabase/migrations/0001_initial.sql` defines three tables: `runs` (one row per session-dir; metadata + JSONB `state` and `metrics`), `events` (append-only mirror of `transcript.jsonl`, one row per line, `payload JSONB`), and `session_files` (every `.md`/`.json`/`.jsonl` artifact under the session-dir, stored as TEXT). Foreign keys cascade so deleting a run cleans up its events and files. New module `src/dual_research/persistence/remote.py` defines `RemoteSession.push_session_dir(path)` — bulk-upserts a completed session-dir to Supabase via `supabase-py` (PostgREST over HTTPS); idempotent on re-push (every write keyed by primary key). New `--push <session-dir>` CLI mode (mutually exclusive with `--prompt`/`--brief`/`--notion`/`--resume`) wraps it; mirrors `--resume`'s shape. New `SupabaseCredentials` + `load_supabase_credentials()` in `config.py` read `SUPABASE_URL` + `SUPABASE_ANON_KEY` + `SUPABASE_SERVICE_ROLE_KEY` from the environment. Orchestrator behaviour unchanged — push is an explicit follow-up step the user runs after a completed run. 15 new unit tests against a fake in-memory supabase client (no live-Supabase dependency in CI). Total: 238 tests.

## [0.17.0] — 2026-05-15

### Added

- **Hosted deployment kickoff handoff package** ([spec 0018](specs/0018-hosted-deployment-kickoff.md)) — new document `handoffs/hosted-deployment-kickoff.md` bootstrapping a multi-session track that takes dual-research from a local tool to a publicly accessible, Google-auth-gated, DB-backed hosted UI. Locks in architectural decisions (Fly.io for hosting, Supabase for Postgres + Google OAuth + email allowlist, orchestrator stays local and pushes session data via a new CLI subcommand), spells out why Fly was chosen over Vercel (incompatibility between Vercel's serverless model and the current `watchfiles` + SSE backend; future kickoff-from-UI's 8–15-minute compute), enumerates the spec roadmap (0019 DB schema + push CLI, 0020 Fly deploy, 0021 Google OAuth + allowlist, 0022 admin route, 0023 later kickoff-from-UI), lists pre-work the user must do (Supabase project + credentials, Fly CLI install), surfaces open design questions for spec 0019, and ships a paste-ready prompt for a fresh Claude Code session to start the new track. Documentation only; backend and UI unchanged at v0.16.2 behaviour. 223 tests still green.

## [0.16.2] — 2026-05-15

### Fixed

- **Deadlocked phase-2 last round** ([spec 0017](specs/0017-deadlock-last-round.md)) — when a run deadlocked at the Phase 2 hard cap, the timeline rendered N-1 of N turn-card pairs. The Phase 2 in-progress branch computed `completedThrough = cur - 1`, expecting the live branch below to cover the `cur` round — but the live branch only fired for `status === 'running'`. For `deadlocked` / `errored`, the `cur` round was on disk and complete but neither branch picked it up. The divider's "N rounds" text (which spec 0016 fixed to read from `phaseStats.phase2`) was therefore one ahead of the rendered card count. Surfaced by a live-verify run that hard-capped on the web-components-catalogue prompt (5 of 5 rounds, $0.47). One-line fix in `buildLiveTimeline`: `completedThrough = st === 'running' ? cur - 1 : cur`. Symmetric Phase 4 case is unreachable today (outer guard already excludes deadlocked/errored from the Phase 4 in-progress branch) and is left out of scope.

## [0.16.1] — 2026-05-15

### Fixed

- **Live data fidelity** ([spec 0016](specs/0016-live-data-fidelity.md)) — five interpretation-layer bugs surfaced by the first concurrent backend + UI run (test-tier SQLite-vs-Postgres prompt, APPROVED in Phase 4 round 3, $0.4228).
  - **Round enumeration** — `live-data.jsx` no longer reads `run.round.current` for past phases. Phase 2 turn-card count and the "N rounds" divider extra-text now derive from `phaseStats.phase2` keys, so a Phase 2 that ran 4 rounds renders as 4 rounds once the run advances to Phase 4. Symmetric fix for Phase 4 enumeration once the run completes.
  - **Disagreement parser coverage** — `ui/disagreements.py::_D_LINE_RE` now also recognises `### D-N`, `#### D-N`, and `N.`/`N)` numbered-list anchors (Claude and OpenAI's actual mid-negotiation formats), in addition to the original `- D-N` list-marker form. A new bare-tail regex captures `<label> — <state>` without the `status:` keyword (OpenAI's form). `_read_round_file` now also pulls entries from `## Final-surfaced disagreements` and `## Resolved or non-blocking differences` so terminal-state entries don't vanish once Claude migrates them out of the "Substantive" section. Per-id records merged across sections keep the longest-information label. The live-integration run that previously rendered 0 disagreements now reconstructs all 6.
  - **Negotiation prompt** — `protocol/prompts.py::negotiation_turn_prompt` now includes a verbatim example of the open-form and terminal-form anchor lines, so agents emit a format the parser recognises (belt-and-braces with the parser broadening above).
  - **Terminal-status pills** — `run-detail.jsx::StatsChips` renders a status pill for every protocol state (`NEGOTIATING`, `REVIEWING`, `DISAGREED`, plus the existing `AGREED` / `APPROVED` / `NOT_APPROVED`). A non-terminal round no longer shows as a bare `4 questions · r1` with no agreement signal.
  - **Phase 0 chip math** — `live-data.jsx::attachItemStats` reports `max(claude.briefIssues, gpt.briefIssues)` instead of the sum. The two agents critique the same brief; their issue lists overlap; the sum was meaningless.
  - **Silent-failure footer** — when the parser finds zero disagreements but at least one round file contains a literal `D-<digit>` anchor, the aggregator sets a new `Run.disagreements_parse_suspected_miss` flag, and the Disagreement Explorer renders a one-line muted footer ("⚠ couldn't reconstruct disagreements from this run — open the round files directly"). Genuine no-disagreement runs are unaffected.
- 9 new tests; total 223.

## [0.16.0] — 2026-05-15

### Added

- **Integration kickoff handoff package** ([spec 0015](specs/0015-integration-kickoff-handoff.md)) — two new documents under `handoffs/`. `handoffs/frontend-state.md` is a comprehensive snapshot of what was built in specs 0009–0014 (modules, endpoints, Run wire shape, chip data flow, disagreement reconstruction, error taxonomy, known limitations). `handoffs/integration-kickoff.md` is a paste-ready prompt for a fresh Claude Code session whose goal is wiring the live data path end-to-end (concurrent `dual-research --prompt ...` + UI server, watching SSE deltas land in the browser). No code changes; backend and UI unchanged at v0.15.0 behaviour. 214 tests still green.

## [0.15.0] — 2026-05-15

### Added

- **Clearer card stats** ([spec 0014](specs/0014-clearer-card-stats.md)) — Phase 1 plan-draft timeline cards now carry chips too, derived from structured sections inside the draft body. `turn_stats.py` extracts `open_questions` and `blocking` (anticipated disagreements) by counting items in the draft's `Open questions` and `Claims I expect the other agent might dispute` sections. Both Claude-style `## H2` and OpenAI-style `N. **Heading**` numbered-section formats are tolerated. Chip labels switched from cryptic two-letter codes (`OQ`, `BD`, `OI`) to plain English (`N questions`, `N disagreements`, `N issues`) so they read naturally and align with the right-pane Disagreement explorer's vocabulary. 4 new tests; total 215.

## [0.14.0] — 2026-05-15

### Added

- **Run-id pill and timeline card stats** ([spec 0013](specs/0013-run-id-pill-and-card-stats.md)) — run-id cell in the All-runs list becomes a compact mono pill (just the 4-char `displayId`) with the full session-dir name, started time, and slug in the hover tooltip; the column shrinks 110px → 80px. Timeline cards now carry protocol-derived stats inline: Phase 0 input shows `OK` / `needs input · N`; Phase 1 plan drafts show `OQ N · BD M`; Phase 2 turns show `OQ N · BD M` plus a status pill when `AGREED`; Phase 4 turns show `OI N` plus `APPROVED` / `NOT_APPROVED`. Stats are produced by a new `dual_research.ui.turn_stats` module that re-uses `protocol.parse.parse_turn` against the per-phase round files and attaches them to `Run.phase_stats`. Aggregator + JS `buildLiveTimeline` thread the data through to `ArtifactHeader`.

## [0.13.0] — 2026-05-15

### Added

- **UI polish and navigation** ([spec 0012](specs/0012-ui-polish-and-navigation.md)) — eight UX fixes informed by live review of v0.12.0. Mono font swap from Geist Mono to JetBrains Mono for readability; run-id column in the All-runs view becomes a two-line stacked cell with the 4-char display id as the primary label and the time + slug suffix below (full slug stays in the row tooltip); long topics clamp to the first sentence via a new `formatTopic()` helper; placeholder agent glyphs replaced with the official Claude (Anthropic) and OpenAI brand marks from simple-icons.org; run-detail top bar redesigned into two stacked rows with a `← All runs` back chip and a clickable display-id chip that copies the full slug to clipboard; the top tab strip becomes single-item (`All runs`) with the Run-detail tab removed; Design language is demoted from a tab to a small palette-icon button in the top-right cluster; the top-right cluster reshapes into three sibling controls of equal weight — connection state pill, segmented sun/moon theme toggle, and the design-language button. UI-only change (no Python, no backend).

## [0.12.0] — 2026-05-15

### Added

- **UI bundle integration** ([spec 0011](specs/0011-ui-bundle-integration.md)) — the Claude Design React prototype is now wired to the live aggregator and lives under `src/dual_research/ui/static/`. `dual-research serve` boots the FastAPI server + UI bundle on `http://127.0.0.1:6173/` by default; the page reads real runs from disk and live-tails in-flight ones via SSE. Replaces the prototype's mock `data.jsx` with `live-data.jsx` (React hooks that fetch + stream the API), adds `router.jsx` (URL hash routing — `#/`, `#/runs/<id>`, `#/language`), and rewires `app.jsx` to use them. Per-turn markdown bodies are fetched lazily via `/api/runs/{id}/files/...`. Brand glyphs stay as placeholders. No build step (React + Babel + marked from CDN).

## [0.11.0] — 2026-05-15

### Added

- **UI HTTP server with SSE** ([spec 0010](specs/0010-ui-server.md)) — new `dual_research.ui.server` module (FastAPI + uvicorn) exposed via a `dual-research serve` CLI subcommand. Endpoints: `GET /api/runs` (list rows), `GET /api/runs/{id}` (full `Run` snapshot), `GET /api/runs/{id}/stream` (SSE — emits a full snapshot on every `transcript.jsonl` change), `GET /api/runs/{id}/files/{path:path}` (path-scoped markdown file serve), `GET /api/health`. JSON payloads are camelCase at the wire (snake_case stays in Python). Defaults to `127.0.0.1:6173`. New deps: `fastapi`, `uvicorn[standard]`, `sse-starlette`, `watchfiles`. Static UI bundle directory exists at `src/dual_research/ui/static/` as a placeholder — spec 0011 fills it.

## [0.10.0] — 2026-05-15

### Added

- **UI run aggregator** ([spec 0009](specs/0009-ui-run-aggregator.md)) — new internal package `src/dual_research/ui/` that reads a session directory and produces a single nested `Run` object matching the Claude Design UI shape (`agents.{claude,gpt}`, `disagreements[]` with per-round progression, `errors[]`, `phase_timings`, `round`). Pure read-side, zero backend changes; foundation for the upcoming HTTP server (spec 0010) and UI bundle (spec 0011). Handles backend↔UI agent label translation (`openai` → `gpt`), reconstructs Phase 2/4 disagreements with their stable D-N IDs from `## Substantive disagreements I'm holding` sections, and maps the four error-shaped backend events (`repair_invoked`, `soft_cap_hit`, `hard_cap_hit`, `run_failed`) to the UI's error taxonomy. Internal use only; no CLI surface yet. New tests under `tests/ui/`.

## [0.9.0] — 2026-05-15

### Added

- **Frontend handoff package** ([spec 0008](specs/0008-frontend-handoff.md)) — top-level `handoffs/` directory with two documents. `handoffs/backend-state.md` is a comprehensive snapshot of the backend at v0.9.0 (project state, repo layout, architecture, event bus contract with every event type, session-dir layout, CLI surface, engineering workflow, verified behaviour, known limitations, integration guidance for the UI). `handoffs/frontend-kickoff.md` is a paste-ready prompt the user pastes into a fresh Claude Code session to start frontend work — it instructs the new agent to read the backend handoff and the Claude Design output bundle at `~/Trimble/handoff/`, then ask clarifying questions before writing code. No code changes; backend behaviour unchanged. 104 tests still green.

## [0.8.0] — 2026-05-15

### Added

- **Rate-limit-aware retry + resume from prior session** ([spec 0007](specs/0007-resume-and-backoff.md)) — `agents/base.py` exports a `with_rate_limit_retry` helper that catches HTTP 429 from either SDK, honours the `Retry-After` header (clamped to [5s, 300s]), and falls back to exponential backoff with jitter. Both `ClaudeAgent` and `GptAgent` now wrap their SDK call in this helper (default 3 attempts). The CLI gains `--resume SESSION_DIR` (mutually exclusive with `--prompt`/`--brief`/`--notion`) which loads `state.json` from the session, validates it, and re-enters the orchestrator at the persisted phase — already-completed phases are skipped, partial phases pick up at the next round via the existing turn-file logic. `--extend-caps N` bumps both soft and hard caps by N on a resume so a previously hard-capped session can be given more rounds. Live verified: resume of a `state.phase=done` session correctly skips all phases (exit 0, $0 cost). 11 new pytest cases. Total suite: 104 green.

## [0.7.0] — 2026-05-15

### Added

- **Anthropic prompt caching** ([spec 0006](specs/0006-prompt-caching.md)) — every phase prompt (except `repair_prompt`) now includes a `CACHE_BREAKPOINT` sentinel at the boundary between the stable prefix and the dynamic per-call suffix. `ClaudeAgent` detects the marker, splits the content into two text blocks, attaches `cache_control: {"type": "ephemeral", "ttl": "1h"}` to the prefix, and adds the `extended-cache-ttl-2025-04-11` beta header for 1-hour cache lifetime. `GptAgent` strips the marker (OpenAI Responses API caches prefixes automatically). `DUAL_RESEARCH_NO_CACHE=1` disables caching on both providers. Cost ticker now shows `cache:r/w` when nonzero. Verified live: single-call A/B showed **76.6% savings** on the second identical call (5,550 tokens cache-written then cache-read at $0.10/M vs $1/M input). 12 new pytest cases; total: 93 green.

### Fixed

- **Cross-round cache invalidation in Phase 2 / Phase 4 prompts.** The round-specific header (`# Phase 2 round {round}...`) used to sit BEFORE the cache breakpoint inside `negotiation_turn_prompt` / `review_turn_prompt`, which changed the cached prefix hash on every round → no cross-round cache hits, only within-round. Restructured both builders so the round number is referenced AFTER the breakpoint. Verified by full Phase 0→4 E2E on test tier: agents converged to APPROVED in Phase 4 round 3, 23 model calls, $0.79 total, cache reads visible across rounds.

### Known limitations

- **Anthropic 30K-tokens/min rate limit still bites prod-tier multi-round Phase 2 around round 6.** Caching halved per-call input cost but cache _writes_ (the dynamic suffix that grows each round) still count against the per-minute input quota. Spec 0007 will add rate-limit-aware backoff + resume-from-prior-session so partial runs are recoverable. Test-tier runs are unaffected.

## [0.6.0] — 2026-05-15

### Added

- **Web search wiring on both providers** ([spec 0005](specs/0005-web-search.md)) — `ClaudeAgent` now passes the `web_search_20250305` server-side tool on `messages.stream(...)` (max 10 uses per call). `GptAgent` switched from Chat Completions to the Responses API and passes `{"type": "web_search"}` as a tool. Both stream identically to the prior shape. `DUAL_RESEARCH_NO_WEB_SEARCH=1` disables search on both providers (useful for offline tests). `AgentResult.extras` now records `searches: int` so the metadata header / transcript can surface how many searches each agent ran. Verified live: smoke test on a time-sensitive query ("current latest Python version") produced `3.14.5 — May 10, 2026` with real citations from both Claude (1 search) and GPT-5-mini (3 searches, $0.02 total). Prod-tier Phase 1 produced research with [V] tags and 2026-dated source URLs confirming both agents truly searched. 11 new pytest cases for the env-var flag; total suite: 81 green.

### Known limitations

- **Prod-tier rate limit (Anthropic).** The prod-tier full-convergence E2E surfaced an Anthropic Sonnet 4.6 rate limit of 30K input tokens per minute on the current account tier. Phase 2 round 2 includes the brief + both Phase 1 drafts + round-1 turns inlined (>100K input tokens), exceeding the per-minute budget and causing exit 2. **Mitigation paths** for a follow-up spec: (a) prompt caching on the brief / Phase 1 drafts / prior turns — the largely-static prefix should hit cache_read pricing and not count against per-minute input-token allowance; (b) Anthropic tier upgrade (sales contact). Test-tier runs (Haiku 4.5 + GPT-5-mini) are unaffected.

## [0.5.0] — 2026-05-15

### Added

- **Phases 3 + 4 + final document emission** ([spec 0004](specs/0004-phases-3-4-final.md)) — Phase 3 single-shot drafting by the agreed drafter (hash-verified `agreed_plan_block` + extracted canonical FSDs injected directly into the prompt). Phase 4 turn-based review loop with revised-draft detection (drafter embeds a `## Revised draft` section; orchestrator extracts and writes `draft-vN.md`, bumping `state.draft_round`). Repair flow reused from spec 0003. Soft cap = continue (autonomous); hard cap exits 51 with deadlock appendix in `final.md`. Metadata header rendering (Keep-a-Changelog–style provenance + cost + token totals + confidence tag HIGH/MODERATE/LOW). `final.md` lands in the session directory; `--out PATH` copies it elsewhere. Test-tier E2E demonstrated the Phase 2 hard-cap path cleanly (synthetic brief, test models couldn't hash-match an AGREED_PLAN block within 5 rounds, exit 51 + `phase2-deadlock.md` written). Phase 3 + 4 convergence path is unit-tested with stub agents; a prod-tier E2E to demonstrate the live convergence path is on the spec-0005 verification list. 12 new pytest cases; total: 70 green.

## [0.4.0] — 2026-05-15

### Added

- **Phase 2 — plan negotiation with caps, repair, and drafter tiebreak** ([spec 0003](specs/0003-phase2-negotiation.md)) — turn-based negotiation loop with parallel agent calls per round, written to `phase2/round-NN-{agent}.md`. Convergence detection via `is_plan_agreed` (hash-matched AGREED_PLAN). Drafter tiebreak invocation when substantive gates pass but DRAFTER differs (domain-fit → plan-alignment → hash-of-brief chain). Repair-turn flow with budget=1 per agent per phase + consecutive-failure tracking; second consecutive failure exits 52. Round-1 lenient validation (`assert_well_formed_round1_turn`). Soft cap = logged warning + continue (autonomous mode). Hard cap = `phase2-deadlock.md` emitted, exit 51. Five new event types (`Phase2RoundComplete`, `RepairInvoked`, `SoftCapHit`, `HardCapHit`, `DrafterTiebreakResolved`, `Phase2Complete`). Verified E2E on synthetic brief (4 rounds, genuine convergence after soft-cap warning, $0.29 total, drafter=openai via matching recommendations). 9 new pytest cases; total suite: 58 green.

## [0.3.0] — 2026-05-15

### Added

- **Orchestrator scaffold + Phase 0/1 end-to-end** ([spec 0002](specs/0002-orchestrator-phase01.md)) — session directory layout (`runs/<id>/` with `state.json` + `transcript.jsonl` + `metrics.json` + phase subdirs), atomic state writes, append-only transcript, per-agent cost rollup. Async event bus (`EventBus` with publish/subscribe and failure-isolated delivery). Orchestrator wired to run Phase 0 (preflight, parallel) and Phase 1 (research, parallel) with live cost ticker on stdout. CLI now runs Phases 0 + 1 by default (use `--ingest-only` to stop after brief ingest). Verified end-to-end on a synthetic brief (test tier, $0.03, 68s, two 12K-char Phase 1 drafts produced).

## [0.2.0] — 2026-05-15

### Added

- **Engineering workflow** ([spec 0001](specs/0001-engineering-workflow.md)) — spec-first development, branch-and-PR-per-spec, admin-squash-merge, semver version bumps tied to spec labels (`new-feature`/`bug`/`refactoring`/`test`/`breaking`), CHANGELOG, PR template, and GitHub labels. The first spec is also the spec for the system itself.

## [0.1.0] — 2026-05-15

Initial baseline. Pre-existing commits on `main`, collapsed into a single release entry. No retro specs.

### Added

- Project skeleton: uv-managed Python package, argparse CLI with mutually-exclusive `--prompt`/`--brief`/`--notion` input sources, model tier registry (prod: `claude-sonnet-4-6` 1M + `gpt-5.5`; test: `claude-haiku-4-5` + `gpt-5-mini`), credential loader, `.gitignore`. ([514fac3](https://github.com/Lexiz/dual-research/commit/514fac3))
- Input ingest layer: three modes including recursive Notion-tree fetch via REST API with depth + page caps, markdown block rendering, retry on 429/5xx, distinct 401/404 handling. ([bbfa103](https://github.com/Lexiz/dual-research/commit/bbfa103))
- Per-SDK agent runners: `ClaudeAgent` and `GptAgent` with async streaming, per-call token + USD cost capture, parallel-safe via `asyncio.gather`. Pricing table in `agents/pricing.py`. ([6b050c0](https://github.com/Lexiz/dual-research/commit/6b050c0))
- Protocol module ported from the original `lib/protocol.mjs`: byte-for-byte preservation of the epistemic-duty preamble, V/U source tagging, freshness rule, anti-sycophancy procedures, FSD canonical-section discipline, convergence gates, and repair-prompt structure. Adapted plumbing only (file paths → inlined content, MCP references → SDK-native phrasing). 36 pytest cases covering parsers, well-formedness assertions, convergence, hash tolerance, and tiebreak chain. Fixes two latent regex/parser bugs that existed in the original. ([4ff2af1](https://github.com/Lexiz/dual-research/commit/4ff2af1))
