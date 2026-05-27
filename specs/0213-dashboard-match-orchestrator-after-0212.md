---
kind: dev
spec: "0213"
slug: dashboard-match-orchestrator-after-0212
title: "Refactor: collapse 11-stage timeline to 7 honest spans + decimal sub-spec treatment"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
depends_on: ["0211", "0212"]
complexity: M
created: 2026-05-25
queued_at: "2026-05-25T00:00:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

<!-- DEV SPEC RULE: this body contains NO open questions, unresolved items,
TBD markers, or "we'll figure it out later" prose. Every decision is either
answered here or explicitly deferred via §5 Out of scope with a named
follow-up target. -->

# Spec 0213 — Refactor: collapse 11-stage timeline to 7 honest spans + decimal sub-spec treatment

> **Type:** refactoring  |  **Complexity:** M  |  **Depends on:** 0211, 0212
> **Bump:** PATCH — dashboard renderer restructure, no orchestrator behavior change
> **Evidence:** spec 0211 moved deploys to GH Actions; spec 0212 introduced the buffered-events doctrine where post-merge events flush atomically at step 23; spec 0211.3 and spec 0212.1 added decimal sub-spec IDs the dashboard doesn't render distinctly. The live timeline at [render_dashboard.py:3468](scripts/spec_lifecycle/render_dashboard.py:3468) still encodes the pre-0211 single-event-per-row model, so three rows visually never tick and "Branch" dishonestly absorbs the whole implementation phase. The metrics chart at [render_dashboard.py:784](scripts/spec_lifecycle/render_dashboard.py:784) already groups to 7 buckets, but its labels and event pairs disagree with what the timeline should show — the dashboard contradicts itself today.
>
> This is the last process/dashboard spec — after it, back to product work.

---

## 1. Current state

### 1.1 Timeline rows are decoupled from /dev-next's actual emission cadence

The canonical stage list lives in two mirrored places:

- **Python definition** at [stages.py:25-37](scripts/spec_lifecycle/stages.py:25) — the `STAGES` tuple of `StageDef(name, event)` entries. The Python renderer at [render_dashboard.py:578](scripts/spec_lifecycle/render_dashboard.py:578) calls `compute_stages(...)` from this list and emits one DOM node per stage via [render_dashboard.py:553 `_render_stage_node`](scripts/spec_lifecycle/render_dashboard.py:553).
- **JS mirror** at [render_dashboard.py:3468-3480](scripts/spec_lifecycle/render_dashboard.py:3468) — the `STAGE_DEFS` array used by the in-browser `computeStages` ([render_dashboard.py:3560](scripts/spec_lifecycle/render_dashboard.py:3560)) so the timeline survives the 5s `/api/data` refresh without server roundtrip. The comment at [render_dashboard.py:3463](scripts/spec_lifecycle/render_dashboard.py:3463) explicitly mandates `STAGE_DEFS` mirror `STAGES` — they must move in lockstep.

Both definitions encode 11 rows: `Pre-flight, Read handoff, Read spec, Reconcile, Branch, Implement, Test, PR, Merge, Deploy, Handoff`. Each row has a single `event` step that marks it `done`.

After specs 0211 and 0212 this model is broken in three ways:

1. **Three rows never visually tick.** /dev-next buffers `handoff_read`, `spec_read`, `planning_started`, `reconcile_complete` during the read-and-plan phase and pushes them in one batch at step 13 (the branch push). The three rows `Read handoff`, `Read spec`, `Reconcile` all light up in the same `/api/data` refresh window — the user sees them appear together rather than as a progression.
2. **"Branch" duration is dishonest.** The single-event-per-stage model computes duration as `prev_stage_event_ts → this_stage_event_ts` (see [stages.py:265-274](scripts/spec_lifecycle/stages.py:265)). For the `Branch` row that's `reconcile_complete → branched` — fine, except the next row `Implement` uses `branched → implement_complete`, which means the `Implement` row gets the right duration but the `Branch` row absorbs only the seconds between reconcile and branch creation. Worse, on legacy specs where `reconcile_complete` is missing, the fallback chain at [stages.py:236-241](scripts/spec_lifecycle/stages.py:236) anchors the Branch row's duration further back, and Branch ends up *appearing* to absorb 30m–1h+ in real runs. The duration is a heuristic over a model that no longer fits.
3. **Deploy + Handoff necessarily tick together.** Per spec 0212's buffer-events doctrine, the post-merge events `deploy_started`, `deployed`, `deploy_health_check_ok`, `handoff_written` are buffered local-only until step 23 flushes them atomically to `main`. The dashboard regenerates from a single push, so two timeline rows light up in the same refresh. **This is correct, not a bug** — but the dashboard's row structure implies they're separable stages.

### 1.2 The dashboard already disagrees with itself

The metrics-chart bucketing at [render_dashboard.py:784-793](scripts/spec_lifecycle/render_dashboard.py:784) already groups events into 7 buckets:
`Pre-flight, Read & plan, Reconcile, Implement, Tests, PR + merge, Deploy`.

The timeline at [render_dashboard.py:3468](scripts/spec_lifecycle/render_dashboard.py:3468) renders 11 rows. The two views describe the same /dev-next cycle but disagree on its shape. Neither matches the target 7-row model this spec ships — even `_STAGE_GROUPS` has no `Handoff` bucket and splits `Read & plan` and `Reconcile` separately.

### 1.3 Decimal sub-specs are parsed but rendered identically to parents

`SpecRow.number` at [render_dashboard.py:74-86](scripts/spec_lifecycle/render_dashboard.py:74) correctly extracts decimal child IDs (`"0211.3"`, `"0212.1"`) from filenames via the `SPEC_ID_RE` regex. Sort keys at [render_dashboard.py:88-94](scripts/spec_lifecycle/render_dashboard.py:88) order them after their parents. The JS mirror at [render_dashboard.py:3522-3536](scripts/spec_lifecycle/render_dashboard.py:3522) does the same client-side. But nowhere in the timeline or History list does the renderer treat them visually distinct from parent specs — `_link_spec(s.number, s.number)` at [render_dashboard.py:1746](scripts/spec_lifecycle/render_dashboard.py:1746) just emits the ID as text; the in-flight hero shows the spec ID flat.

### 1.4 What does NOT need fixing

- **The History list does not render per-stage durations.** [`_render_all_specs`](scripts/spec_lifecycle/render_dashboard.py:1722) is a 6-column grid: Spec, Title, Type, Status, Lifetime, Cycle. It uses `_spec_lifetime_seconds` (created → deployed) and `s.cycle_seconds` (started_at → deployed_at — see [render_dashboard.py:113-122](scripts/spec_lifecycle/render_dashboard.py:113)), neither of which depends on stage rows. The original spec brief asked "if History shows per-stage durations, update them" — verified against current code: it does not, so this is a no-op slice of B.
- **`Avg cycle (last 10)`** at [render_dashboard.py:1957](scripts/spec_lifecycle/render_dashboard.py:1957) is computed from `cycle_seconds` (frontmatter `started_at` → `deployed_at`). Independent of the 11-stage model; no change needed.
- **Per-stage note text** at [stages.py:115-169 `_note_for`](scripts/spec_lifecycle/stages.py:115) is keyed by the **end** event of each stage (`handoff_read`, `reconcile_complete`, etc.). When rows collapse, some keys become dead. This spec consolidates the keys so each new row has one note from the end_event.

## 2. Target state

### 2.1 Seven honest spans, one `(start_event, end_event)` pair each

Replace the 11-row single-event model with a 7-row span model:

| # | Row name      | start_event          | end_event            |
|---|---------------|----------------------|----------------------|
| 1 | Pre-flight    | `cycle_started`      | `preflight_ok`       |
| 2 | Read & plan   | `handoff_read`       | `reconcile_complete` |
| 3 | Implement     | `branched`           | `implement_complete` |
| 4 | Test          | `tests_started`      | `tests_green`        |
| 5 | Ship          | `pr_opened`          | `merged`             |
| 6 | Deploy        | `merged`             | `deployed`           |
| 7 | Handoff       | `deployed`           | `handoff_written`    |

A row's bar duration is `end_ts − start_ts`. The row is `done` when the `end_event` has landed, `curr` when neither event has landed and the prior row is done (or it's row 1 with the cycle anchor present), `queued` when later rows haven't reached it.

### 2.2 Span model — algorithm

Update `StageDef` at [stages.py:17-22](scripts/spec_lifecycle/stages.py:17) to add a `start_event: str` field (rename the existing `event` to `end_event` consistently across the file; or keep `event` as the end_event for backward-compat clarity — pick one in the implementation step and stay consistent). Failure-event semantics carry forward unchanged.

Update `compute_stages` at [stages.py:183-287](scripts/spec_lifecycle/stages.py:183) so:

- A stage's `duration_seconds` is `by_step[end_event].ts − by_step[start_event].ts` when both are present.
- If `start_event` is missing on a legacy/in-progress spec (events emitted before this spec landed), fall back to **the prior row's `end_event` timestamp** as the start anchor — preserves the old "cumulative chain" semantics so historical spec pages still show non-zero durations. Document this fallback in a comment.
- The `curr` heuristic stays: lowest-index stage where `end_event` isn't in `by_step` and the prior stage's `end_event` is (or `i == 0`).
- The cycle anchor used for the *first* stage's start is `cycle_started → queued → in_progress` (the existing chain at [stages.py:236-241](scripts/spec_lifecycle/stages.py:236)) — this is now identical to row 1's `start_event` so no extra logic is needed for row 1 in the new world.

Update the JS mirror at [render_dashboard.py:3560-3612 `computeStages`](scripts/spec_lifecycle/render_dashboard.py:3560) to use the same span model. The renderer at `_render_stage_node` ([render_dashboard.py:553-573](scripts/spec_lifecycle/render_dashboard.py:553)) keeps its structure — `tl__step--done/--curr/--queued/--fail` classes still drive CSS; only the duration source changes.

### 2.3 Metrics chart bucketing — align with the new timeline

Update `_STAGE_GROUPS` at [render_dashboard.py:784-793](render_dashboard.py:784) so its 7 buckets match the 7 timeline rows 1:1. The new labels and pairs:

| Label       | chart-token   | pairs                                          |
|-------------|---------------|------------------------------------------------|
| Pre-flight  | chart-grey    | `cycle_started→preflight_ok`                   |
| Read & plan | chart-mint    | `handoff_read→reconcile_complete`              |
| Implement   | chart-blue    | `branched→implement_complete`                  |
| Test        | chart-green   | `tests_started→tests_green`                    |
| Ship        | chart-purple  | `pr_opened→merged`                             |
| Deploy      | chart-peach   | `merged→deployed`                              |
| Handoff     | chart-yellow  | `deployed→handoff_written`                     |

Keep `chart-*` tokens distinct per bucket to preserve the stacked-bar palette. Add a unit-test assertion that `STAGES` (Python) and `_STAGE_GROUPS` produce the same 7 labels in the same order with the same `(start, end)` pairs — anything that drifts is a bug.

### 2.4 Decimal sub-spec visual treatment — both timeline and History list

Two pieces of UI affordance, applied consistently:

- **Indent.** When `SpecRow.number` parses to `(parent, child)` with `child > 0`, the row gets an `ItemCard--sub-spec` (or equivalent existing modifier — pick one that aligns with `design-system/SPEC.md`) class that contributes ~16px of left-padding. Same class on both the in-flight hero spec ID and the History list row.
- **Chip.** Prepend a small `↳ {parent_id}` chip next to the spec ID — e.g. `↳ 0211`. The chip uses an existing chip primitive from `design-system/SPEC.md` (tone `neutral`, `no-dot`) — no new tokens, no new components.

No tree widgets, no collapse/expand, no hover sub-states — only indent + chip. The chip and indent appear in:

- `_render_hero_inflight` ([render_dashboard.py:576](scripts/spec_lifecycle/render_dashboard.py:576)) where the spec ID is rendered as a chip on the hero.
- `_render_all_specs` ([render_dashboard.py:1722-1762](scripts/spec_lifecycle/render_dashboard.py:1722)) — the `qrow__id` cell.
- The JS-side equivalents in the bootstrap (the rows the 5s refresh repaints client-side) so first-paint and post-refresh agree.

Cite `design-system/SPEC.md` chip + sub-row composition rules in the implementation. If the DS has no `↳`-pattern chip variant, add the variant in this same commit (it's a tone-neutral chip with a glyph prefix — a small extension, not a new component).

### 2.5 Note keys consolidate

In [stages.py:115-169 `_note_for`](scripts/spec_lifecycle/stages.py:115):

- `handoff_read` and `spec_read` notes merge into a single `reconcile_complete` note (the `Read & plan` row's end_event) — combine the path + verdict + counts into one line: e.g. `handoff: <path> · spec: <path> · <mech> mechanical · <sem> semantic · <verdict>`.
- `branched` note merges into the `implement_complete` note — prepend the branch name: `<branch> · <lines> lines / <files> files / <commits> commits`.
- `pr_opened` and `merged` notes both stay relevant; for the `Ship` row use the `merged` note (which currently says `admin squash + delete branch`) and append the PR URL: `PR <url> · admin squash + delete branch`.
- `deploy_started`, `deployed`, `deploy_health_check_ok` notes consolidate behind the `deployed` end_event note (which already says `fly deploy · vN.N.N live`). Keep that wording; it's still accurate post-0211.
- `handoff_written` note unchanged.

## 3. Stepwise migration

Each step is independently shippable to the branch (not to main) and revertable.

- **Step 1 — Update `stages.py` to span model.** Edit the `StageDef` dataclass to include `start_event`, rewrite `STAGES` to the 7-row table from §2.1, rewrite `compute_stages` to compute durations as `end_ts − start_ts` with the legacy fallback in §2.2, consolidate `_note_for` per §2.5. Add unit tests for the new compute_stages behavior on three fixtures: a fully-shipped spec, an in-flight spec stopped mid-`Read & plan`, and a legacy spec missing `start_event`s. Verifies the algorithm independently of the renderer.
- **Step 2 — Update `_STAGE_GROUPS` in `render_dashboard.py`.** Rewrite the table at lines 784-793 to the new 7-row alignment from §2.3. Add a test that asserts `STAGES` and `_STAGE_GROUPS` produce the same 7 labels with the same `(start, end)` pairs. Verifies metrics and timeline stay in lockstep.
- **Step 3 — Update the JS mirror `STAGE_DEFS` + `computeStages`.** Edit `STAGE_DEFS` at lines 3468-3480 to encode `[name, start_event, end_event]` per row. Edit `computeStages` at lines 3560-3612 to use the span model matching §2.2. Add a source-pattern test (per spec 0206) asserting the new JS shape — positive regex on the post-fix `[name, start_event, end_event]` form, antipodal regex on the pre-fix `[name, completedStep]` form. Verifies the 5s client-side refresh agrees with first-paint.
- **Step 4 — Decimal sub-spec indent + chip in both views.** Add the `ItemCard--sub-spec` (or equivalent) class in `_render_stage_node`, `_render_hero_inflight`, `_render_all_specs`, plus the JS-side repaints. Cite `design-system/SPEC.md` for the chip + sub-row pattern. Add a source-pattern test rendering a fixture with a decimal child spec, asserting the indent class + `↳ 0211` chip appear in both the in-flight hero output and the History list row. Verifies the visual affordance lands consistently.
- **Step 5 — Documentation in renderer + stages.** Add a short comment at the top of `stages.py` and near `STAGE_DEFS` in `render_dashboard.py` explicitly documenting: "Under spec 0212 buffer-events doctrine, `Deploy` and `Handoff` rows tick at the same `/api/data` refresh — both events flush atomically at /dev-next step 23. This is correct behavior; do not try to interleave them." So a future reader doesn't reopen the wound.

## 4. Behavior preservation

- [ ] Existing dashboard render tests at `tests/test_render_dashboard*.py` still pass — no orchestrator behavior changes, no event-emission changes, no frontmatter schema changes.
- [ ] Existing `tests/test_stages*.py` (compute_stages behavior on shipped specs) passes after being updated to assert the new 7-row output. The semantic contract — a stage transitions `queued → curr → done` once its end_event lands — is preserved; only the row count and duration arithmetic change.
- [ ] The JS bootstrap's first-paint and 5s repaint produce identical timeline HTML for any spec — source-pattern test on the post-fix STAGE_DEFS shape (positive regex on `'Read & plan', 'handoff_read', 'reconcile_complete'`; antipodal regex on `'Read handoff', 'handoff_read'` and on `'Read spec', 'spec_read'` to prove the old 11-row defs are gone).
- [ ] `Avg cycle (last 10)` value on the metrics tab is unchanged for the historical specs (independent of stage rows — uses `cycle_seconds`).
- [ ] Legacy in-flight specs missing the new `start_event` (anything currently buffered or already-completed before this lands) still render non-zero durations via the prior-row-fallback in §2.2 — assert with a fixture in the compute_stages tests.

### Required tests (UI doctrine per spec 0206)

- Source-pattern test on `STAGE_DEFS` (JS) — positive regex on the 7-row `[name, start_event, end_event]` form; antipodal-absence regex on `'Read handoff'`, `'Read spec'`, `'Branch'`, `'PR'`, `'Merge'` as standalone row names.
- Source-pattern test on `STAGES` (Python) — positive regex on the same 7 `(name, start_event, end_event)` tuples.
- Render test on a fixture with a decimal-child spec asserting the indent class + `↳ {parent_id}` chip appear in **both** `_render_hero_inflight` output and `_render_all_specs` output. Run the JS-bootstrap source-pattern test to confirm the equivalent client-side repaint emits the same shape.
- Consistency assertion: `STAGES` (Python) and `_STAGE_GROUPS` (Python) produce the same 7 labels in the same order with the same `(start, end)` pairs. This is the gate that keeps the metrics chart and the live timeline aligned forever; drift becomes a test failure.
- Existing dashboard render tests pass unchanged after Step 1+2+3 land together (they're a single PR by design).

### Runtime verification (per CLAUDE.md UI doctrine)

This spec touches dashboard HTML rendered to `https://lexiz.github.io/dual-research/`. Per `design-system/SPEC.md §13`, runtime rendering is verified via Claude Preview MCP screenshots in the PR description. Capture: (1) the in-flight hero with the 7-row timeline, (2) the same hero rendered for a decimal-child spec showing indent + chip, (3) the History list with a decimal child indented under its parent, (4) the Metrics-tab stacked bar with the 7 new buckets.

## 5. Out of scope

**Explicit: this spec ships no new feature.** It restructures the dashboard renderer to reflect the orchestrator's actual cadence — behavior change is zero. Any feature work that depends on this refactor lives in a follow-up spec.

Out of scope explicitly:

- **Changing what events /dev-next emits.** The orchestrator's event vocabulary at `scripts/spec_lifecycle/*` and the /dev-next skill is untouched. This spec adapts the *renderer* to the events that already exist.
- **Real-time GH Actions deploy-progress streaming.** Under spec 0212's buffer-events doctrine, `deploy_started`, `deployed`, `deploy_health_check_ok`, `handoff_written` flush atomically at step 23 — Deploy + Handoff row clocks tick at the same instant on the live dashboard. **This is correct behavior, not a bug.** Documented in Step 5 of §3. Any future "stream the GHA run live" work is a separate spec with depends_on this one.
- **Tree widgets, collapse/expand, or hover sub-states for decimal sub-specs.** Indent + chip only.
- **History list per-spec stage-duration breakdown.** Verified against [render_dashboard.py:1722](scripts/spec_lifecycle/render_dashboard.py:1722): the History list does not show per-stage durations today, only Lifetime + Cycle aggregates. No B.1 work needed.
- **`Avg cycle (last 10)`** calc changes. Independent of stage rows (uses `cycle_seconds` from frontmatter). Untouched.
- **SKILL.md edits.** No /dev-next, /spec-queue, /dev-queue-run SKILL.md changes — those skills don't reference the 11-row timeline by name. (Re-verified by `grep -r "Read handoff\|Read spec\|Reconcile\|Branch\|Implement\|PR\|Merge\|Deploy\|Handoff" .claude/skills/` before commit; prune only if dead references show up.)
- **Design-system primitive extension beyond the `↳`-chip variant.** If the DS already has a tone-neutral chip with a glyph prefix, use it. If not, add the variant inline; do not refactor the broader chip system.

## 6. Risks

- **Renderer/orchestrator decoupling drift.** /dev-next's event vocabulary is the contract. If /dev-next renames an event later and only the spec body — not `STAGES` — gets updated, the dashboard silently breaks. Mitigation: the §2.3 consistency assertion test makes `STAGES`/`_STAGE_GROUPS` divergence a CI failure. Renames to /dev-next events will trip CI in this spec's tests.
- **Legacy in-flight specs.** Any spec currently mid-cycle when this ships has buffered events emitted by the pre-0213 orchestrator code paths (which are unchanged — only the renderer changes). The §2.2 fallback handles the case where `start_event` is missing on a stage: use the prior row's `end_event` as the start anchor. Test fixture proves this is non-zero.
- **JS mirror drift.** `STAGE_DEFS` and `STAGES` must stay aligned — the JS comment at [render_dashboard.py:3463](scripts/spec_lifecycle/render_dashboard.py:3463) mandates this. Mitigation: the source-pattern tests in §4 cover both definitions; if either changes shape, both tests fire.
- **Decimal sub-spec rendering misses a surface.** The dashboard has at least three places that render a spec ID: in-flight hero, History list row, per-spec page header. The first two get the indent + chip per §2.4. The per-spec page header at [render_dashboard.py:2279](scripts/spec_lifecycle/render_dashboard.py:2279) (`render_spec_page`) is a single-page view — out of scope for the indent affordance (no siblings to indent against), but the chip is still useful as a visual cue. **Decision: also apply the chip (not the indent) to `render_spec_page`'s H1 so the spec's own page shows it's a sub-spec.** Render-test asserts this on the decimal-child fixture.
- **Visual regression in the History list grid.** The current 6-column grid is `70px 1fr 110px 100px 90px 90px`. Adding a chip + indent inside the Spec cell must not push the grid out of alignment. Mitigation: the chip + indent live inside the existing first cell; grid template is unchanged. Visual verification via Claude Preview MCP screenshot in §4.
- **Doctrine misread.** A future reader sees Deploy + Handoff tick simultaneously and assumes the renderer is broken. Mitigation: Step 5 of §3 lands an explicit comment in both `stages.py` and near `STAGE_DEFS` in `render_dashboard.py` calling out the spec 0212 buffer-events doctrine and the intentional simultaneity.
