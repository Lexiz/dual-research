---
kind: dev
spec: "0248"
slug: all-runs-card-refinements-provider-metrics
title: All Runs card refinements — chrome cleanup, avatar menu restore, inline archive tray, note-width fix, rich provider metric bands
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: L
created: 2026-05-28
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "Direct continuation of the 0246 card layout, reviewed end-to-end in a static prototype; ready to implement now."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. -->

# Spec 0248 — All Runs card refinements + rich provider metric bands

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** —
> **Bump:** MINOR — adds per-agent metric payloads, a restored avatar menu, and a new inline-archive interaction; no existing contract removed.
> **Evidence:** Follow-up to [spec 0246](specs/0246-all-runs-card-layout-rewrite.md) (card layout) and [spec 0245](specs/0245-archive-runs.md) (archive). All five changes were built and approved in the static review prototype at `prototypes/all-runs-iteration/index.html`. Spec 0246 explicitly deferred "richer plan-turns/critiques chips" — see [aggregator.py:341](src/dual_research/ui/aggregator.py:341) — which §2.5 below now delivers.

---

## 1. Context

The 0246 card rewrite shipped the All Runs landing page but left five rough edges that surfaced in real use. (1) A redundant "dual-research" wordmark strip ([run-list.jsx:339](src/dual_research/ui/static/run-list.jsx:339)) sits between the chrome and the stats, wasting vertical space. (2) The chrome rewrite replaced the Google-login avatar + dropdown menu with a bare initial ([run-list.jsx:333](src/dual_research/ui/static/run-list.jsx:333)); the working `AvatarMenu`/`AvatarDisc`/`MenuItem` source still lives in [app.jsx:398](src/dual_research/ui/static/app.jsx:398) but is no longer mounted, so users lost Sign out, Design language, Replay tour, and Settings. (3) The hover archive affordance is a floating icon button ([run-list.jsx:547](src/dual_research/ui/static/run-list.jsx:547), [components.css:5866](src/dual_research/ui/static/components.css:5866)) whose confirm step is a full-screen `Modal` ([run-list.jsx:566](src/dual_research/ui/static/run-list.jsx:566)) — disproportionate for a reversible soft-delete. (4) The terminal-state note spans the full card width because the grid places it in a `"note note"` row ([components.css:5697](src/dual_research/ui/static/components.css:5697)), visually detaching it from the phase strip it annotates. (5) The per-agent rows ([run-list.jsx:469](src/dual_research/ui/static/run-list.jsx:469)) show only name + cost + a searches chip, despite the card now having spare vertical space.

The per-agent metric data needed for (5) is partially free and partially not. `metrics.json` already carries per-agent `input_tokens`/`output_tokens`/`cache_*`/`searches`/`cost_usd` ([metrics.py:81](src/dual_research/persistence/metrics.py:81)), so total tokens + searches are cheap. The raised/solved tallies for Questions/Disagreements/Issues are NOT — they require `reconstruct_questions`/`reconstruct` (disagreements)/`reconstruct_issues`/`reconstruct_comments` ([questions.py:318](src/dual_research/ui/questions.py:318), [disagreements.py:549](src/dual_research/ui/disagreements.py:549), [issues.py:151](src/dual_research/ui/issues.py:151), [comments.py:43](src/dual_research/ui/comments.py:43)) which parse every Phase 2/4 round file. `summarize_run` is deliberately cheap (no transcript replay — [aggregator.py:417](src/dual_research/ui/aggregator.py:417)) and the `/api/runs` list is polled every 3 s ([live-data.jsx:191](src/dual_research/ui/static/live-data.jsx:191)). The chosen approach (decided in the queueing conversation) is to **persist the per-agent critique tallies at run-write time** so the list endpoint stays cheap — never compute-on-read in the hot list path.

## 2. Proposed change

Five sub-changes. (1)(2)(3)(4) are UI-only (`run-list.jsx`, `app.jsx`, CSS). (5) is full-stack (Python data model + write-time persistence + aggregator + CSS + JSX). Per CLAUDE.md, every new CSS class lands in **both** [components.css](src/dual_research/ui/static/components.css) and [design-system/assets/styles/composed-components.css](design-system/assets/styles/composed-components.css) in the same commit.

### 2.1 — Remove the wordmark strip, tighten top spacing

Delete the `ProjectStrip` render from `AllRunsPage` ([run-list.jsx:267](src/dual_research/ui/static/run-list.jsx:267)) and the `ProjectStrip` component ([run-list.jsx:339](src/dual_research/ui/static/run-list.jsx:339)); drop the `.ar-project*` rules ([components.css:5578](src/dual_research/ui/static/components.css:5578)). Reduce `.ar-page` top padding so the stats panel sits closer under the sticky chrome (prototype used `padding-top: 18px`). DS: spacing per [SPEC.md §2.7](design-system/SPEC.md); layout constants [§2.14](design-system/SPEC.md).

### 2.2 — Restore the Google avatar image + dropdown menu

Lift `AvatarMenu` + `AvatarDisc` + `MenuItem` ([app.jsx:398-522](src/dual_research/ui/static/app.jsx:398)) into the chrome and mount it in `AllRunsChrome` in place of the bare `.ar-avatar` span ([run-list.jsx:333](src/dual_research/ui/static/run-list.jsx:333)). `AvatarDisc` renders `me.avatarUrl` (Google `user_metadata.avatar_url`, exposed by `useMe`) with a deterministic-hue initials fallback on missing/`onError`. The menu retains: identity header (full name, email, `admin` badge), Design language, Replay tour (dispatches `dr-replay-tour`), Settings (admin only), Sign out (`client.auth.signOut()`). The menu needs the supabase auth `client` + `session`; thread them from the auth layer ([auth.jsx](src/dual_research/ui/static/auth.jsx) — same source `app.jsx` already used). Close on outside-click + Escape. DS: icons [SPEC.md §2.12](design-system/SPEC.md); admin badge follows badge governance [§9](design-system/SPEC.md); focus ring [§2.13](design-system/SPEC.md); menu surface [§2.2](design-system/SPEC.md)/[§2.9](design-system/SPEC.md).

### 2.3 — Inline archive tray (replaces floating icon + full-screen modal)

Remove `.rc-archive-btn` floating button ([run-list.jsx:547-560](src/dual_research/ui/static/run-list.jsx:547), [components.css:5866](src/dual_research/ui/static/components.css:5866)) and the `ConfirmArchiveDialog`/`ConfirmUnarchiveDialog` `Modal` usage ([run-list.jsx:566-596](src/dual_research/ui/static/run-list.jsx:566)). Add a `.rc-tray` row at the card bottom that expands on `:hover` (max-height + opacity transition) for admins on the active view. The tray has two in-place states: **prompt** ("Would you like to archive this run?" + Archive button) → **confirm** ("Archive run <id>? You can restore it later." + Cancel / Yes, archive). Confirm fires the existing `POST /api/runs/{id}/archive` ([server.py:760](src/dual_research/ui/server.py:760)) via the existing `handleArchiveConfirm` ([run-list.jsx:193](src/dual_research/ui/static/run-list.jsx:193)); the tray stays open while confirming (`.is-confirming`) so a pointer leave mid-confirm doesn't collapse it. Archived view gets the analogous restore tray (`DELETE …/archive`). The full-screen `Modal` ([SPEC.md §4.6](design-system/SPEC.md)) is no longer used for this flow. The tray is a **new composed component** — add it to DS [§4](design-system/SPEC.md) and both CSS files.

### 2.4 — Constrain the note to phase-strip width

Change the `.run-card` grid so the agents column spans the phases+note rows and the note occupies only the left (phase-strip) column ([components.css:5694-5702](src/dual_research/ui/static/components.css:5694)):

```
grid-template-areas:
  "head   head"
  "phases agents"
  "note   agents"
  "tray   tray";
```

This makes `.rc-note` width equal the `.rc-phases` width (verified in prototype: both 595 px, right edge aligned), and the taller provider bands (§2.5) consume the reclaimed vertical space rather than leaving the left-column gap. Add `align-items: start` on the card; `.rc-phases { align-self: start }`, `.rc-note { align-self: end }`.

### 2.5 — Rich single-row provider metric bands

Replace `AgentRow` ([run-list.jsx:469](src/dual_research/ui/static/run-list.jsx:469)) with a `ProviderCard` rendering a single-row band: brand logo (from `BRAND_SVGS` — [shared.jsx:41](src/dual_research/ui/static/shared.jsx:41), reuse `BrandMark` [shared.jsx:51](src/dual_research/ui/static/shared.jsx:51)) in a brand-tinted square with a sable/sage spine; provider name with **total tokens** beneath it; **cost** vertically centered with a divider; then inline metric groups — **Questions / Disagreements / Issues** each as a `raised`/`solved` badge pair, plus a **Searches** count. Badges follow governance [SPEC.md §9](design-system/SPEC.md): `raised` → neutral, `solved` → ok, `searches` → info (fixed mappings [§9.3](design-system/SPEC.md)). Agent colors `--p-sable` (Claude) / `--p-sage` (GPT) per [§2.1](design-system/SPEC.md). The provider band is a **new composed component** — add to DS [§4](design-system/SPEC.md) and both CSS files.

Backend (the not-free part):

- **Data model** — extend `AgentBreakdown` ([models.py:~795](src/dual_research/ui/models.py)) with `tokens: int = 0` and a `critique: dict[str, tuple[int, int]] = {}` (keys `questions`/`disagreements`/`issues`, value `(raised, solved)`) and `searches: int = 0`. All defaulted so the supabase builder and old callers stay valid (same pattern the 0246 fields used).
- **Write-time tally persistence** — add a per-agent critique tally to `metrics.json`. A pure helper (reusing the `reconstruct_*` parsers) computes, per agent: tokens (sum of `input/output/cache_*` from `totals_by_agent`), searches, and `(raised, solved)` per category — `raised` = items whose `raised_by` == that agent; `solved` = those in a terminal/resolved state. Persist under a new `metrics.json` key (e.g. `critique_by_agent`) written wherever `metrics.save()` is already called ([run.py:515](src/dual_research/orchestrator/run.py:515), [run.py:558](src/dual_research/orchestrator/run.py:558), [run.py:629](src/dual_research/orchestrator/run.py:629)) and at finalize ([finalize.py](src/dual_research/orchestrator/finalize.py)). Place the helper to avoid an orchestrator→ui import cycle (e.g. a thin module the orchestrator may import, or compute in the aggregator and have the orchestrator call it). Running runs reflect the last write — acceptable.
- **Aggregator** — `derive_agent_breakdowns` ([aggregator.py:336](src/dual_research/ui/aggregator.py:336)) reads the persisted tokens + `critique_by_agent` from `metrics.json` and populates the new fields. `summarize_run` stays cheap — **no `reconstruct_*` call in the list path.**
- **Wire** — the snake→camel layer ([server.py](src/dual_research/ui/server.py), `_to_camel`) carries the new fields automatically; verify camelCase keys (`critique`, `tokens`, `searches`) reach the client.

Old runs (no `critique_by_agent` in `metrics.json`) render `0`/`—` for tallies — documented in §7.

## 3. User stories & acceptance criteria

### 3.1 — User stories

> As an `admin`, I want to archive a run without a full-screen modal, so that a reversible soft-delete feels lightweight and I stay in context.
> As an `admin`, I want my Google avatar and account menu back, so that I can sign out and reach Settings/Design language from the runs page.
> As a `viewer`, I want each run card to show per-provider tokens and how many questions/disagreements/issues each agent raised and solved, so that I can judge each agent's contribution at a glance.
> As a `viewer`, I want the error/terminal note aligned under the phase strip, so that it reads as an annotation of the phases rather than a full-width banner.

### 3.2 — Acceptance scenarios (BDD)

> **Scenario 1:** Inline archive confirm stays in-card
> GIVEN an admin on the active All Runs view hovering a non-archived run card
> WHEN they click "Archive" in the revealed tray and then "Yes, archive"
> THEN no full-screen modal appears, the `.rc-tray` confirm state renders inside the card, and `POST /api/runs/{id}/archive` fires.

> **Scenario 2:** Avatar menu restored
> GIVEN an authenticated admin on the All Runs page
> WHEN they click the avatar in the chrome
> THEN a dropdown shows their name/email, an `admin` badge, and Design language / Replay tour / Settings / Sign out items.

> **Scenario 3:** Provider band shows metrics
> GIVEN a run whose `metrics.json` carries `critique_by_agent`
> WHEN the run card renders
> THEN each provider band shows the brand logo, total tokens, cost, and `raised`/`solved` badge pairs for Questions/Disagreements/Issues plus a Searches count.

> **Scenario 4:** Note aligns to phase strip
> GIVEN a terminal-state run card
> WHEN it renders
> THEN the `.rc-note` left/right edges match the `.rc-phases` strip (left column only), not the full card width.

## 4. Data / Schema deltas

- `AgentBreakdown` gains `tokens: int`, `searches: int`, `critique: dict[str, tuple[int,int]]` (all defaulted).
- `metrics.json` gains a `critique_by_agent` object: `{ "claude": {"tokens": N, "searches": N, "questions": [r,s], "disagreements": [r,s], "issues": [r,s]}, "openai": {…} }`. Additive; older files without it degrade gracefully (zeros). No migration required — `metrics.json` is per-run and rewritten on the next run-write.
- Supabase `metrics` JSONB inherits the same shape when present; absent → zeros (same degradation the 0246 fields already accept — [server.py:1147](src/dual_research/ui/server.py:1147)).

## 5. Out of scope

- No change to the archive **backend** endpoints (`POST`/`DELETE /api/runs/{id}/archive`) or admin gating — reused as-is.
- No backfill/re-materialization of historical `metrics.json` — old runs show zero tallies; not worth a one-off migration.
- No change to the run-detail page's critique panes; this spec only touches the All Runs list card and chrome.
- No new badge **kinds** — reuse the nine canonical kinds ([SPEC.md §9.2](design-system/SPEC.md)).
- Dark-mode-specific tuning beyond what the existing tokens already give (the prototype rendered both via `body.light`).

## 6. Test plan

UI anatomy via source-pattern tests per [SPEC.md §13](design-system/SPEC.md) / spec 0206 doctrine, at `tests/test_spec_0248_all_runs.py` using `tests/_ui_pattern_helpers.py`:

- [ ] Positive: `run-list.jsx` renders a `ProviderCard`/`.rc-prov` with brand logo, `.rc-prov__tok`, `.rc-prov__cost`, and `.rc-rs--raised`/`.rc-rs--solved`/`.rc-rs--count` badges; antipodal: the old `AgentRow`/`.rc-agent__chips`-only shape is absent.
- [ ] Positive: `.run-card` grid template places `note` in the left column and `agents` spanning phases+note rows; antipodal: the pre-fix `"note note"` full-width row is absent in both CSS files.
- [ ] Positive: chrome mounts the avatar menu (`AvatarMenu`/`AvatarDisc`); antipodal: the bare `.ar-avatar` initial-only span is gone; `ProjectStrip` is removed.
- [ ] Positive: `.rc-tray` inline archive markup with prompt + confirm states present; antipodal: `.rc-archive-btn` floating button and `ConfirmArchiveDialog` `Modal` usage are absent.
- [ ] Python: a unit test feeds a fixture session dir to the new tally helper and asserts per-agent `(raised, solved)` for questions/disagreements/issues + tokens + searches; and asserts `derive_agent_breakdowns` reads `critique_by_agent` from `metrics.json` and that `summarize_run` issues no `reconstruct_*` call (cheap-path guard).
- [ ] Both CSS files (`components.css` + `composed-components.css`) contain the new `.rc-prov*` / `.rc-tray*` classes (sync check).
- [ ] Runtime: Claude Preview MCP screenshot in the PR (8-capture ItemCard parity grid not required — this card is not an ItemCard — but include light+dark card captures showing all five changes).

## 7. Risks

- **List-endpoint cost regression** — mitigated by design: tallies are persisted at write-time; `summarize_run` must not call `reconstruct_*`. The cheap-path guard test enforces it. If a future change reintroduces on-read parsing, the test fails.
- **Orchestrator→ui import cycle** when reusing `reconstruct_*` at write time — mitigated by placing the tally helper to avoid the cycle (named in §2.5); revert is a single import move.
- **Old runs show zero tallies** — acceptable and documented (§5); new runs populate immediately. No data loss.
- **Avatar menu regressions** — the source is lifted verbatim from `app.jsx`, which is the currently-working implementation; risk is wiring the supabase `client`/`session` into the chrome. If it can't be threaded cleanly, fall back to reading the client from the existing auth module the chrome already has access to.
- **Brand-logo licensing** — marks are trademarks (already noted in [design-language.jsx:486](src/dual_research/ui/static/design-language.jsx:486)); fine for this internal tool, unchanged from current usage.
