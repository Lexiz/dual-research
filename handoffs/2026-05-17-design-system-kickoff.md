# Handover — Design system implementation kickoff

**Date:** 2026-05-17
**Branch:** `main` (clean)
**Hosted:** [`dual-research-alex.fly.dev/api/health`](https://dual-research-alex.fly.dev/api/health) → `{"version":"0.47.0","backend":"supabase"}`
**Specs shipped today:** 0046 (early AM), 0047, 0048, 0049 + 0.46.1 hotfix
**Last commit:** `18f7a6a Spec 0049 — flip front-matter to merged + PR link`
**Tests:** 725 green (was 657 at start of day)
**Working tree:** clean

---

## Bottom line for the new session

You are starting a **design-system implementation** session. The
prior thread arc closed the audit-gap items from
[`handoffs/2026-05-17-gaps-and-next-three-specs.md`](2026-05-17-gaps-and-next-three-specs.md)
*except* three deferred items (F7, F10, Notion-as-MCP — see "Open
items" below). The codebase is in a stable, well-tested state and
ready for the substantial UI refactor that Claude Design's
deliverables will drive.

The **expected input** for this session is a pair of documents
returned by Claude Design (likely on the user's Desktop or in
their inbox/Notion/etc.):

1. **`DESIGN-SYSTEM-V1.md`** — fully implementable design system for
   dual-research *as it exists today*, including a "Changes from
   current state" section documenting every component/pattern/
   visualization that drifted.
2. **`DUAL-RESEARCH-V2.md`** — independent product proposal for the
   next version (surface-by-surface), assuming V1 as baseline.

V1 is the implementation target. Implementing V2 is a separate,
larger spec arc.

Pre-work the user did to produce these deliverables is documented in
the design-brief artifacts (see "Design brief context" below).

---

## What shipped today (chronological)

Five PRs merged to `main` between 09:25 UTC and 17:02 UTC.

| PR  | Spec      | Version       | Merged at    | Title                                                                            |
|-----|-----------|---------------|--------------|----------------------------------------------------------------------------------|
| #47 | 0046      | 0.43 → 0.44.0 | 10:25 UTC    | Critique + Summary + Consumption rework + design unification                     |
| #48 | 0047      | 0.44 → 0.45.0 | 12:37 UTC    | Run-detail resilience + Phase 4 repair-turn visibility                           |
| #49 | 0048      | 0.45 → 0.46.0 | 14:54 UTC    | Always-on cost verification + pricing_version snapshot                           |
| #50 | (hotfix)  | 0.46 → 0.46.1 | ~15:35 UTC   | reconcile-costs CLI: graceful missing-runs/ + exit-code semantics                |
| #51 | 0049      | 0.46.1 → 0.47.0 | 17:00 UTC | Reconcile-costs reads run-cost data from Supabase; daily cron re-enabled         |

### Spec 0046 — Critique + Summary + Consumption rework + design unification ([PR #47](https://github.com/Lexiz/dual-research/pull/47))

Shipped earlier in the day before the audit-gap arc. 10 design decisions:

1. Critique pane header restructured: three primary buttons left, count cluster right.
2. Per-phase context-aware filter chips (Phase 2 → `[All|Questions|Disagreements|Claims]`, Phase 4 → `[All|Issues|Comments|Disagreements]`).
3. Human-readable card headlines (`Issue C-1 · open · …` instead of `**C-1** — open — …`).
4. `GhostedAnnotation` wired into every critique card (spec 0043 defined the component; 0046 wired it).
5. Summary tab redesigned: per-kind, per-model tables; empty kinds dropped.
6. Consumption tab: single-row card with inline expand (no width jump).
7. Consumption tab: dropped "not used in this turn: …" footer.
8. Consumption tab: web-search cluster cleaned up (no more "of which web search" wording).
9. **Uniform `PaneButton` component** across Critique pane, Summary, Consumption tab, and Conversation/Consumption pair. Single design language for all toggle/tab/filter buttons.
10. No backend changes — pure JSX/CSS refactor over existing wire data.

**Why this matters for the new session:** the `PaneButton` component
established in 0046 is the *de facto* design-token anchor in the
current codebase. Claude Design's V1 will likely subsume or replace
it; expect this to be the load-bearing refactor seam.

### Spec 0047 — Run-detail resilience + Phase 4 repair-turn visibility ([PR #48](https://github.com/Lexiz/dual-research/pull/48))

Audit gaps F1 + F2 + F5. Three defensive bugfixes bundled because the testing motion is identical.

- **F1 — Drafter-null run-detail crash.** Five historical local runs (`drafter=null + status=completed`) rendered a blank page with `Cannot read properties of null (reading 'name')`. `ArtifactHeader`'s `kind === 'doc'` and `kind === 'doc-live'` branches now guard `meta` defensively (matches the pattern already in `DocumentModal`); `buildLiveTimeline` skips the `doc-final` push entirely when `run.drafter` is null.
- **F2 — Post-finalize NoneType.** The `confidence_tag` crash from partner-vetting (2026-05-16) was already fixed by spec 0036's guards on `main` by the time we got there; this PR's contribution is the **DEADLOCKED + None Phase 2** regression test (`tests/orchestrator/test_emit_final_resume.py`) that the original spec-0036 only covered for APPROVED. Sweep of `finalize.py` confirmed no remaining unguarded `phase{N}_outcome.<attr>` accesses on `Foo | None` parameters.
- **F5 — Phase 4 sibling-key collapse.** Per-turn key on the wire gains a `_repair` suffix for sibling labels (`phase4-r1-claude-repair`, `phase2-r4-gpt-hashdrift-repair`). The aggregator's `_on_turn_ended` was overwriting the original turn's cost with the repair turn's cost; now each LLM call gets its own Consumption-tab card. Consumption-tab regex extended to capture the `Repair` suffix; repair rows sort adjacent to their parent with a `repair` chip + muted background. Timeline `StatsChips` gains a `+repair` discoverability hint. Agent-level rollups unchanged (still sum every event → matches the bill).

6 new tests; 665 total green at that point.

### Spec 0048 — Always-on cost verification + pricing_version snapshot ([PR #49](https://github.com/Lexiz/dual-research/pull/49))

Audit gaps C1 + F8. The big spec of the day — full cost-verification system end-to-end.

- **F8 — `PRICING_VERSION` snapshot.** Human-bumped date constant in [`pricing.py`](../src/dual_research/agents/pricing.py) (initial value `2026-05-17`); `Metrics.to_json()` records it; `recompute-costs` stamps the rewritten `metrics.json` with the live value + surfaces the before/after transition on the CLI diff line. Snapshot regression test in `tests/agents/test_pricing_version.py::test_version_tracks_table` ties the `PRICING` dict's SHA-256 to the version string so a rate edit can't ship without bumping the date.
- **C1 — Cost reconciliation harness.** New [`src/dual_research/audit/reconcile.py`](../src/dual_research/audit/reconcile.py) (~450 LOC) + new `dual-research reconcile-costs` CLI subcommand. Pulls daily provider totals from the **OpenAI Organization Costs API** (verified end-to-end with real key) and the **Anthropic Admin Cost Report API** (built blind, tested against canned docs-shape fixture — no admin key available in the user's Console UI; see "Anthropic admin-key status" below). Joins to local `metrics.json` totals per UTC date, computes per-(provider, model) deltas, writes a `ReconcileReport` to `reconcile/<date>.json`.
  - **Five-state `verification_status` enum:** `verified` / `drift` / `partial` / `unverified` / `awaiting_provider_data`.
  - **CLI modes:** `--day` · `--from/--to` · `--all` · `--run RUN_ID` · `--since-yesterday`.
  - **Each provider's admin key is independently optional** via env vars (`OPENAI_ADMIN_KEY`, `ANTHROPIC_ADMIN_KEY`, plus `OPENAI_PROJECT_ID` / `ANTHROPIC_WORKSPACE_ID` for scoping). Missing key ⇒ provider skipped, never crashes.
  - **Hosted-mode persistence:** new Supabase `reconcile_results` table (migration `supabase/migrations/0004_reconcile_results.sql`); `--push` upserts each snapshot. Server endpoint `GET /api/reconcile/<date>` reads from local file (dev) or Supabase (hosted).
  - **Run-detail UI verification chip** in the header (`run-detail.jsx::ReconcileChip`) renders all 5 states with tooltips listing what was checked / skipped.
  - **Consumption-tab per-row "provider-billed" annotation** under the costs cluster: `Provider-billed: $X · Δ $Y (Z%)`, warn-tinted if the delta exceeds tolerance.
  - **GitHub Actions daily cron** at 02:00 UTC (`.github/workflows/reconcile-costs.yml`).

44 new tests; 718 total green at that point.

**Real-world data the system surfaced:** partner-vetting day (2026-05-16) showed **OpenAI billed $14.37 vs local $15.08** — a +$0.71 drift, driven by gpt-5.5 local accounting being 78% off provider billing on the day. This drift is real and shipped on `main`; investigating it is a separate future spec.

### 0.46.1 hotfix — reconcile-costs CLI exit-code semantics ([PR #50](https://github.com/Lexiz/dual-research/pull/50))

The first GitHub Actions cron run (via `workflow_dispatch` after the secrets landed) revealed two related issues:

1. **CLI exited 2 when `runs/` was missing** — CI runners check out a clean repo with no local `runs/` directory (gitignored). The underlying `gather_local_totals` already returns `{}` for missing dirs; only the CLI's early-exit was overzealous. Now warns + proceeds with empty local totals.
2. **Exit-code semantics were too strict** — `ReconcileReport.within_tolerance` only returned `True` for `verified`, so `unverified` / `partial` / `awaiting_provider_data` (legitimate operational states) all exited 1 and would alert needlessly. Updated to: **only `drift` returns exit 1**; the other four states are operational, not failures.
3. **Daily cron schedule disabled** as a stopgap — CI runners couldn't see local `runs/` so the cron would always report spurious drift. `workflow_dispatch` was kept. (Re-enabled in spec 0049 below.)

1 new regression test; 719 total green at that point.

### Spec 0049 — Reconcile-costs reads run-cost data from Supabase ([PR #51](https://github.com/Lexiz/dual-research/pull/51))

The architectural follow-up to 0.46.1 — closes the gap that disabled the cron in the first place.

- **New `gather_supabase_totals(client, *, start_date, end_date) -> LocalTotals`** in [`audit/reconcile.py`](../src/dual_research/audit/reconcile.py). Queries the hosted `runs` table for runs whose `created_at` (indexed) falls in the date range, then enforces the canonical `metrics.started_at` window in Python. Same `LocalTotals` return shape as `gather_local_totals` so `compare_day` is source-agnostic.
- **Per-run aggregation extracted to shared `_ingest_run_metrics`** so both gather paths feed the same code — any per-call shape drift surfaces in both at once instead of silently diverging.
- **New `reconcile-costs --source {local,supabase}` flag** (default `local`, backward compatible). `reconcile_day` / `reconcile_range` gain optional `local_totals` kwarg so the CLI can gather once across a range and pass through.
- **GitHub Actions daily cron re-enabled** at 02:00 UTC with `--source supabase --push`. CI runner's empty `runs/` directory is no longer a problem.
- **Real smoke** on prod Supabase + OpenAI: 2026-05-16 reproduces the spec-0048 +$0.71 drift via the Supabase path — confirms source parity.

6 new tests; **725 total green** (current).

---

## Open items at session end

Cross-referencing the original audit doc
([`handoffs/2026-05-17-gaps-and-next-three-specs.md`](2026-05-17-gaps-and-next-three-specs.md)),
**three items remain unaddressed**. The user's initial assessment
identified only "Notion as MCP"; F7 and F10 were also originally
slated for spec 0049 but we used the 0049 slot for the
Supabase-source reconciliation work instead.

| ID    | Item                                                          | Surface                          | Effort     | Why deferred                                                                                       |
|-------|---------------------------------------------------------------|----------------------------------|------------|----------------------------------------------------------------------------------------------------|
| F7    | `[V]` / `[U]` citation tag inline rendering                   | Markdown component + Web Search tab | ~half day  | Original 0049 slot was used for Supabase-source reconciliation instead; F7 still unstarted.        |
| F10   | Server-side re-fetch of cited URLs (snippet population)       | New audit module + endpoint + UI | ~2–3 days  | Same as F7. Plus this item has substantial network/ToS/extractor surface.                          |
| —     | Notion-as-MCP (expose dual-research data via MCP server)      | New surface                      | ?          | Explicitly excluded from the 0047/0048/0049 plan in the audit doc; from a broader thread arc.      |

These are NOT blockers for design-system implementation — they're orthogonal product gaps. Worth scoping in their own specs when the design system is settled.

**Real cost drift discovered + still open on production data:** the 2026-05-16 reconciliation shows local accounting is +$0.71 over OpenAI billing, driven mostly by gpt-5.5 (local $2.92 vs billed $13.73 — local is under-reporting), partially offset by openai-web-search (local $1.55 vs billed $0.49 — local is over-reporting). The verification system surfaces this correctly. Investigating/fixing the accounting is a separate spec.

---

## Design brief context (input for this session)

Prior to this thread arc, the user packaged a comprehensive design
brief and sent it to Claude Design as **suggestive input** — Claude
Design is the design authority. Reference details from the
[earlier session's `SESSION-REFERENCE.md`](#) (handle
`dr-design-brief-20260517-1550-b6e20c`):

- **Brief delivered as:** a 122 MB zip on the user's Desktop, unzipped into a folder named `dual-research-design-brief/` (note: as of this handover the folder is no longer at that exact path in my view — user has likely moved/renamed; ask them where it lives now).
- **Inputs Claude Design received** (file names worth knowing for the new session):
  - `INPUT-current-design-and-suggestions.md` — descriptive notes on current tokens/components + suggestions. Input to V1.
  - `INPUT-improvement-notes.md` — surface-by-surface friction/opportunity notes. Input to V2.
  - `INPUT-codebase-and-spec-archaeology.md` — codebase audit + spec-by-spec history of how the design got here.
  - `assets/` — `theme.css`, brand SVGs (Claude/OpenAI), icon set, font notes, protocol-overview.svg.
  - `reference/` — source files: `index.html`, `design-language.jsx`, `shared.jsx`.
  - `screenshots/` — 223 screenshots across all surfaces × states × modals × tabs × themes × viewports (dark/light, desktop/mobile/tablet, hosted auth, logged-in chrome, etc.).
- **Expected deliverables back from Claude Design:**
  1. `DESIGN-SYSTEM-V1.md` — implementable design system for the *current* app, including a "Changes from current state" section documenting every component/pattern/visualization that was changed from the current build, with before/after/why.
  2. `DUAL-RESEARCH-V2.md` — independent product proposal for the next version (surface-by-surface), assuming V1 as baseline.

V1 is the implementation target for this new session. V2 is reference / future-planning.

**Stack the new design lands on:** Python orchestrator + React (UMD + Babel-standalone, no build step) + Supabase + Fly.io. No build tooling for the frontend — every JSX file is loaded directly via `<script type="text/babel">` in `index.html`. Token-level changes (CSS custom properties) live in `theme.css`; component-level changes live in `shared.jsx` and the per-surface JSX files (`run-detail.jsx`, `runs-list.jsx`, `how-it-works.jsx`).

UI voice (per the brief): read-only, calm, dense, terminal-adjacent. Sable (#d4a574) = Claude, Sage (#7cc4b8) = GPT.

---

## State of the codebase

### Where things live

| Surface                          | Primary file                                                                                                   |
|----------------------------------|----------------------------------------------------------------------------------------------------------------|
| Run-detail page (largest surface)| [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) (~6500 LOC)        |
| Runs list                        | [`src/dual_research/ui/static/runs-list.jsx`](../src/dual_research/ui/static/runs-list.jsx)                     |
| "How it works" / changelog       | [`src/dual_research/ui/static/how-it-works.jsx`](../src/dual_research/ui/static/how-it-works.jsx)               |
| Shared components + helpers      | [`src/dual_research/ui/static/shared.jsx`](../src/dual_research/ui/static/shared.jsx)                            |
| Live data builders               | [`src/dual_research/ui/static/live-data.jsx`](../src/dual_research/ui/static/live-data.jsx)                      |
| Tokens / theme                   | [`src/dual_research/ui/static/theme.css`](../src/dual_research/ui/static/theme.css)                              |
| Server                           | [`src/dual_research/ui/server.py`](../src/dual_research/ui/server.py)                                            |
| Aggregator (transcript → UI)     | [`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py)                                    |

### Components introduced in the day's specs (likely to be re-styled by V1)

- `PaneButton` (spec 0046 D9) — shared toggle/tab/filter button. Used by Critique pane, Summary, Consumption, Conversation/Consumption pair.
- `CardHeadline` (spec 0046 D3) — shared critique-card headline (`{Kind} {Public ID} · {status} · {body}`).
- `GhostedAnnotation` (spec 0043, wired in spec 0046 D4) — `⚠ ghosted Nr` chip on critique cards.
- `RepairChip` (spec 0047) — `repair` chip on Consumption-tab repair-sibling rows + `+repair` on timeline turns.
- `ReconcileChip` (spec 0048 D13) — verification chip in run-detail header with 5 visual states.
- `ProviderBilledLine` (spec 0048 D14) — bottom-line in `ConsumptionCard` for `Provider-billed: $X · Δ $Y (Z%)`.

### Operational facts

- **Tests:** 725 green via `uv run pytest tests/ -q`.
- **Local dev:** `uv run dual-research serve --host 127.0.0.1 --port 6173` (see `.claude/launch.json` config `dual-research-ui`).
- **Hosted deploy:** `fly deploy` (manual). `/api/health` reports current version + backend mode.
- **Daily reconcile cron:** `.github/workflows/reconcile-costs.yml`, runs 02:00 UTC, can fire manually via `workflow_dispatch` from the Actions tab.

### Environment variables the new session may need

In `~/.zshrc` (already set):
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` — model calls (orchestrator).
- `OPENAI_ADMIN_KEY` — cost reconciliation, OpenAI side.
- `OPENAI_PROJECT_ID=proj_0W823hZF68Md05LXB3iCXRx7` — scope OpenAI cost query to dual-search project.
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` — hosted-mode persistence.
- `SUPABASE_ACCESS_TOKEN` — Supabase CLI for migrations (added 17:00 UTC for spec 0049's migration apply).

**Not set, won't change without user action:**
- `ANTHROPIC_ADMIN_KEY` — admin keys aren't currently mintable in the user's Anthropic Console (the Service Accounts UI only issues workspace-scoped `sk-ant-api03-` keys which 401 on `/v1/organizations/*`). Cron + chip report `partial · ⚠ Anthropic` until this is resolved out-of-band.
- `ANTHROPIC_WORKSPACE_ID` — meaningless without `ANTHROPIC_ADMIN_KEY`.

In **GitHub repo secrets** (same names, set at 15:35–16:28 UTC):
- `OPENAI_ADMIN_KEY`, `OPENAI_PROJECT_ID`
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

In **Fly secrets** (already deployed):
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

---

## Anthropic admin-key status (context for any work that touches reconciliation)

The Anthropic Console UI was updated some time before 2026-05-17 and the `Settings → Admin Keys` page is no longer present in the user's organization. The replacement appears to be **Service Accounts** under Organization Settings, but in the current UI a service-account-issued key carries the `sk-ant-api03-` prefix (workspace-scoped) and returns `401 invalid x-api-key` on every `/v1/organizations/*` endpoint regardless of which workspace role the SA has. The user attempted to assign a workspace role to a service account and got a `"Service account role couldn't be updated"` toast.

Resolution path (deferred to user when bandwidth allows):
- Email Anthropic support asking how to mint a key that can call `/v1/organizations/cost_report` in the current Console UI.
- When such a key is available: `export ANTHROPIC_ADMIN_KEY=...` in `~/.zshrc`, restart the server, and the Anthropic side of reconciliation activates automatically. Also add it to GitHub repo secrets so the daily cron picks it up.

The reconcile module's Anthropic adapter is built blind against the public docs' response shape; tests use a canonical canned fixture. First real-key call will be the moment of truth for shape parity.

---

## Recommended kickoff approach for this session

1. **Get the deliverables.** Ask the user where `DESIGN-SYSTEM-V1.md` and `DUAL-RESEARCH-V2.md` are now (the original brief directory at `/Users/alexlisitzky/Desktop/dual-research-design-brief/` is no longer at that path).
2. **Read V1 cover-to-cover** before touching code. Pay special attention to the "Changes from current state" section — that's the diff.
3. **Spin up the dev server first thing** (`uv run dual-research serve --host 127.0.0.1 --port 6173`, or use Claude Preview's `dual-research-ui` config from `.claude/launch.json`). Open the partner-vetting run (`runs/20260516-035048-partner-vetting-arch-critique/`) as the canonical fixture — it has every kind of artifact (negotiate, drafting, review, web search, citations, repair turns, reconcile chip).
4. **Decide on a spec-arc shape** with the user. V1 will likely be too big for one spec; expect 3–5 specs covering tokens first, then shared components, then per-surface adoption. Use the prior pattern from specs 0042–0046 (small, focused, testable, one PR each).
5. **Plan for component-level seams.** The `PaneButton` (spec 0046) is the most recent shared-component anchor; V1 will likely subsume it. Other recent components (`ReconcileChip`, `RepairChip`, `GhostedAnnotation`, `CardHeadline`) will all need to be re-styled in V1's tokens. Worth listing every component introduced after the design brief was packaged so V1's "Changes from current state" can be cross-referenced.
6. **Watch the verification chip** — the run-detail header now shows a `drift` chip with the +$0.71 finding. If V1 restyles the chip, make sure it preserves all 5 visual states (`verified` / `drift` / `partial` / `unverified` / `awaiting`).
7. **Keep tests green at every spec boundary** (currently 725). Component re-styling shouldn't change behavior; structural test-failures in JS surfaces are rare in this codebase (no JSX-level tests), but Python-side wire-format guards catch a lot.

---

## Workflow conventions to follow

Per [`CONTRIBUTING.md`](../CONTRIBUTING.md):

```
spec → branch → implement → tests + preview-verify → version-bump →
CHANGELOG + VERSION_NOTES → PR (admin squash-merge) → fly deploy → STOP
```

Per-spec:

1. Copy [`specs/TEMPLATE.md`](../specs/TEMPLATE.md) → `specs/NNNN-<slug>.md`. Front-matter: `status: in-progress`, `target-version`, `created`, `pr: ""`.
2. Branch: `spec/NNNN-<slug>`.
3. Implement; run `uv run pytest tests/ -q` (expect 725 green baseline).
4. Preview-verify via `.claude/launch.json`'s `dual-research-ui` config.
5. Version bump in `pyproject.toml` + `src/dual_research/__init__.py`.
6. CHANGELOG: move `[Unreleased]` to versioned heading.
7. `VERSION_NOTES` at top of `how-it-works.jsx` if user-visible.
8. Spec front-matter `status: merged` + `pr:` populated before final push.
9. `gh pr create --label "spec/<label>" --title "Spec NNNN — <title>" ...`
10. `gh pr merge <PR#> --admin --squash --delete-branch`
11. `fly deploy` + `curl https://dual-research-alex.fly.dev/api/health` — verify new version.
12. **STOP.** Pause before the next spec per memory entry `feedback_pause_between_specs.md`.

---

## Hard constraints (memory-derived)

- **STOP after each spec deploys + `/api/health` reports the new version.** Don't auto-start the next one. The user authorizes one spec at a time.
- **DO NOT delete `runs/20260516-035048-partner-vetting-arch-critique/`** — canonical fixture across all specs and the only run with real reconcile data on file.
- **Permissions are pre-configured globally** for `git`/`gh`/`uv`/`fly`/`pytest`/`supabase` inside `/Users/alexlisitzky/dual-research`.
- **Memory entries** apply: `feedback_pause_between_specs.md`, `feedback_low_reversal_just_decide.md`, `feedback_no_handoff_unless_asked.md`, `feedback_secrets_pragmatic.md`.

---

## Quick sanity checklist when each design-system spec deploys

- [ ] `uv run pytest tests/ -q` green (725 baseline).
- [ ] Preview-verified on `localhost:6173` against partner-vetting + at least one other run.
- [ ] `pyproject.toml` + `__init__.py` version match each other and `/api/health`.
- [ ] CHANGELOG entry under the right heading (Added / Changed / Fixed).
- [ ] VERSION_NOTES entry at the top of `how-it-works.jsx` if user-visible.
- [ ] Spec front-matter `status: merged` + `pr:` populated.
- [ ] PR merged via `--admin --squash --delete-branch`.
- [ ] `fly deploy` clean exit; `curl /api/health` reports new version.
- [ ] Local `main` synced.
- [ ] Verification chip still works in all 5 states (if anywhere near it).

---

## How to begin

Paste this verbatim to the new session:

> I have a previous Claude Code session — its full handover is at `/Users/alexlisitzky/dual-research/handoffs/2026-05-17-design-system-kickoff.md`. Read it cover-to-cover before doing anything else. After that, I'll point you at the Claude Design deliverables (`DESIGN-SYSTEM-V1.md` + `DUAL-RESEARCH-V2.md`) and we'll plan the spec arc together.
