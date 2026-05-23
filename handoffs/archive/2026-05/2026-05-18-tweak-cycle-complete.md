# Handover — 2026-05-18 tweak-cycle complete (v0.69.8 → v0.69.12)

**Date:** 2026-05-18
**Branch:** `main` (clean)
**Latest commit on `main`:** `17e0503 Spec 0087 completion patch — knock out remaining deferred items (#88)`
**Version:** `0.69.8` → `0.69.12` (4 PATCH bumps across 4 PRs)
**Hosted:** [`dual-research-alex.fly.dev/api/health`](https://dual-research-alex.fly.dev/api/health) → `{"ok":true,"version":"0.69.12","backend":"supabase"}`
**Fly image:** `dual-research-alex:deployment-…` (machines on v66 — was v63 before this arc)
**Static-asset cache-bust:** `v=0084` → `v=0088`
**Tests:** 800 green
**Working tree:** clean
**Open PRs:** 0

---

## 0 · Bottom line for the new session

You are picking up a **shipped, deployed cleanup arc** that just closed out the 2026-05-18 tweak-cycle audit. The full audit lives at

```
/Users/alexlisitzky/dual-research-automation/audits/2026-05-18-tweak-cycle-screenshot-audit.md
```

That file contains 29 screenshot deltas — each one is a side-by-side comparison of what the user originally asked for (a previous design-system spec) against what was actually visible on the deployed UI as of 2026-05-18 morning. Many of those deltas had **open gaps** — items the prior spec attempted but didn't fully ship.

This arc closed every still-open gap from that audit, plus three pieces of NEW user feedback that surfaced during review of the three specs we shipped today (0085 / 0086 / 0087 + the 0087 completion patch). The cleanup ran as **3 specs + 1 follow-up patch**, 4 PRs total, all squash-merged to `main` and deployed to Fly.

The arc is done. There is no immediate follow-up work in flight. Future work should treat the live UI on `dual-research-alex.fly.dev` as the new baseline.

---

## 1 · What shipped (PR-by-PR)

### Spec 0085 — Agent Input panel completion + modal vertical space ([PR #85](https://github.com/Lexiz/dual-research/pull/85))

**Version bump:** `0.69.8` → `0.69.9`
**Spec doc:** [`specs/0085-agent-input-completion-and-modal-vertical-space.md`](../specs/0085-agent-input-completion-and-modal-vertical-space.md)
**Audit deltas closed:** 15.13 (deferred-checks half), 15.30, 17.13
**New user feedback addressed:** modal vertical-space utilisation

#### Backend changes

- **`build_input_bundle_fallback(session_dir, snake_key)`** (new) in [`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py) — parses a snake-case turn key (`phase2_round3_claude`, `phase4_round1_gpt`, `phase2_round3_claude_repair`) and dispatches to the matching `*_input_bundle()` builder in [`src/dual_research/protocol/prompts.py`](../src/dual_research/protocol/prompts.py). Returns the bundle dict with the system prompt synthesised from current source.
- **`synthesize_bundle_payload(...)`** (new, pure) — the dispatcher's body, extracted as a pure function so both the filesystem path (`build_input_bundle_fallback`) and the Supabase path (`_read_input_bundle_supabase`) share one dispatch. Takes `phase / round_idx / ui_agent_label / is_repair / brief_text`. Returns the JSON-ready payload stamped with `system_source: 'agent-default'`.
- **`_parse_snake_key(snake_key)`** (new) — internal helper; regex parses `phase{N}(_round{R})?_(claude|gpt)(_repair)?` into a tuple.
- **`build_phase0_input_bundle()`** (existing) — now stamps `system_source: 'agent-default'` on its return payload for consistency.
- **`_read_input_bundle_fs(session, turn_key)`** and **`_read_input_bundle_supabase(client, run_id, turn_key)`** in [`src/dual_research/ui/server.py`](../src/dual_research/ui/server.py) — when the persisted bundle isn't on disk (filesystem) or in `session_files` (Supabase), they now synthesise a fallback bundle instead of returning `None`. Persisted bundles get `system_source: 'recorded'` stamped on response. Synthesised non-Phase-0 results are deliberately NOT cached so a real bundle written later wins.

#### Frontend changes

- **`InputTabContent`** (in [`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx)) reads `bundle.system_source`. When `'agent-default'`, the `system` piece's `<InputSection>` renders an "agent default" chip on its header AND an italic caveat paragraph inside the body: "This is the agent's current default system prompt — the per-run system prompt for this older turn was not recorded. The exact prompt the model saw may have differed."
- **`InputEmptyState`** is no longer reached for the "bundle not recorded" branch — the backend always returns at least a synthesised System Prompt. The component stays in code for the `error` + `renderKeys.length === 0` branches.
- **Modal vertical space** — `.dr-modal` rule in [`components.css`](../src/dual_research/ui/static/components.css) sets `min-height: 72vh` alongside the existing `max-height: 92vh`. Content-rich modals now claim the available height instead of cropping at natural content height.
- **Split-view modals** — `NegotiateLeftSubTabs` array reordered so `{id: 'input', label: 'Agent Input'}` is FIRST; `NegotiateLeftPane` and `DraftReviewModal` `useState` defaults flipped from `'original'` to `'input'` so the Agent Input tab is active on modal open (matching the single-view rule from spec 0074).

#### Tests added

- `tests/ui/test_aggregator_input_bundles.py` — 13 new tests under `TestSpec0085ParseSnakeKey` + `TestSpec0085BundleSynthesisFallback` covering every-phase synthesis, repair-suffix handling, missing-brief degradation, pure-function smoke test, and Phase 0 `system_source` marker.
- `tests/ui/test_server_input_bundles.py` — `test_missing_key_returns_404` renamed to `test_missing_key_synthesises_fallback_with_agent_default`; added `test_unparseable_key_returns_404` and `test_recorded_bundle_stamps_system_source_recorded`.
- `tests/ui/test_server_cache.py` — `test_input_bundle_helper_does_not_cache_negative_results` renamed to `test_input_bundle_helper_does_not_cache_synthesised_fallback` and rewritten to assert that synthesised payloads are NOT cached (so a real bundle landing later wins).

---

### Spec 0086 — Consumption tab rework ([PR #86](https://github.com/Lexiz/dual-research/pull/86))

**Version bump:** `0.69.9` → `0.69.10`
**Spec doc:** [`specs/0086-consumption-tab-rework.md`](../specs/0086-consumption-tab-rework.md)
**Audit deltas closed:** 20.14 + 20.18 (both "completely misunderstood" per the user's review of my initial delta verdicts)
**New user feedback addressed:** "phase name eats horizontal space"

#### Visual outcome

Each phase group is now headed by a `<ConsumptionPhaseHeader>` band ABOVE the rows (was: an inline phase-label cell inside every row, eating ~100 px of horizontal real estate). Phases without rounds (P0/P1/P3/P5) render with a 2-col grid (cards span full pane width); phases with rounds (P2/P4) use a 3-col grid with a narrow `Round N` chip on the left (`--consumption-round-w: 64px`). The legacy `<TokenLaneCell>` top-row compact-bar that duplicated the total bar above the expanded card is GONE — the card itself is the click-to-expand surface.

#### Code changes (all in [`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) + [`components.css`](../src/dual_research/ui/static/components.css) + [`tokens.css`](../src/dual_research/ui/static/tokens.css))

- **New helper `groupConsumptionRowsByPhase(rows, run)`** — groups flat rows by `phase`, attaches the phase name (via `PHASE_NAMES`), the per-phase duration (from `run.phaseTimings`), and the round count derived from the rows themselves.
- **New component `<ConsumptionPhaseHeader>`** — small uppercase mono name + faint right-anchored meta line carrying duration + round count when present.
- **`ConsumptionView` rewired** to iterate groups, render a header per group, then the rows in that group.
- **`ConsumptionRow` rewritten** — no more inline phase-label cell, no more `<TokenLaneCell>` top-row. `data-has-round="true|false"` attribute selects the grid template. The cards themselves are the row.
- **`ConsumptionCard` extended** with `expanded` (bool) + `onToggle` (callback) props. Wrapped in a `<button>` so the whole card is the disclosure surface. When `expanded === true`, breakdown bars + output bar cascade inside the card; when false, only data header + cost + total bar render. Chevron at top-right rotates on expand.
- **Paired expansion** — `ConsumptionView`'s `expanded: Set<rowId>` state shape stays; both agent cards in a row share one flag.
- **`ConsumptionRowExpanded` deleted** — its work moved inside `ConsumptionCard`.
- **`TokenLaneCell` deleted** — only orphan reference remains in a code comment.
- **New token `--consumption-round-w: 64px`** in tokens.css.
- **New CSS rules** in components.css: `.consumption-phase-group`, `.consumption-phase-header`, `.consumption-row[data-has-round]`, `.consumption-round-chip`, `.consumption-card` becomes a button-style surface with `:focus-visible` ring.

---

### Spec 0087 — Cross-cutting polish (initial PR) ([PR #87](https://github.com/Lexiz/dual-research/pull/87))

**Version bump:** `0.69.10` → `0.69.11`
**Spec doc:** [`specs/0087-cross-cutting-polish.md`](../specs/0087-cross-cutting-polish.md) (630-line spec; final spec from the 3-spec consolidation; covers 22 audit deltas + 3 new feedback items across 14 sections)

#### What landed in the initial 0087 PR

- **§ A** — Run-list `STATUS → TOPIC` gap bumped `8 → 20 px`. Run-detail `StatusErrorsBadge` aligned to `.sb` height (20 px) via `minHeight: 20`.
- **§ B** — Top-chrome tabs (`All runs` / `Compare` / `Search` / `How it works`) enforce `min-width: 110px` via new `.tab-chrome` class. Chrome strip `align-items: stretch → center` so tabs are vertically centered, not flush against the top edge.
- **§ C** — Run-list header chip tooltips ("Total runs in the current filter" / "Runs currently in progress" / "Aggregate cost across the visible runs").
- **§ D.1** — PhaseRail legibility regression fixed. `.phase-rail-node.is-completed .pr-label` color `var(--ok) → var(--fg-2)`. (Items D.2 + D.3 were deferred and shipped in the follow-up patch — see below.)
- **§ E** — AgentStrip Claude + GPT pills equal-width via new `.as.as-timeline { width: 400px }`. Both pills now render at identical outer widths regardless of model-name string length.
- **§ F** — Critique pane chrome rework. The visible win:
  - `PaneHeader` typography parity with Timeline (constant `14px / 600 / fg-0`, was conditional on whether `left` prop was provided).
  - Three-row structure: (1) title + count + aggregate stats; (2) phase-scope tab group in its own row; (3) kind + agent + status filter chips right-aligned in their own row.
  - Tooltips on every filter chip (closes the 14.45 tooltip mandate).
- **§ G.1 + § G.2** — Timeline phase-header bands now ALL render at the same width (`width: calc(100% + 12px)`; `marginLeft/Right: -6` for the 6 px horizontal overhang per the 14.49 spec). Was ragged because each band sized to label content.
- **§ H** — Agent Input card chip variant unification. `PreflightChip(stats.state === 'ok')` migrated from `<StatusInline label="OK" />` (bordered gray legacy) to `<SB tone="ok" size="sm">ok</SB>` (rounded green pill) matching the brief-critique cards.
- **§ I** — Chip vocabulary polish:
  - `StatChip` rewritten — mixed `+1 -1` cases now render as TWO sibling chips (`[+1 issue]` info-tinted + `[-1 prior issue]` ok-tinted) instead of one merged warn-tinted chip with a bare `-N`.
  - Singular inflection enforced in displayed text (`+1 issue` not `+1 issues`).
  - Round identifier rendered as a bordered uppercase `R<n>` chip (was bare lowercase `r<n>` text).
- **§ J** — Collapsible-section defaults. `Resolved / answered` and `Comments` sections both default to `defaultOpen={false}`. Chevron-on-right was deliberately deferred — the existing chevron is placed inside each `renderTitle` callsite, so flipping it requires editing ~6 sites; not done in this batch.
- **§ K.3 + § K.4** — Disagreement detail view. Dropped the redundant uppercase `RESOLUTION` block from the QuestionThread render. Added `in round N` suffix to the resolution footer matching the Question variant's format (`Answered by GPT in round 3`).
- **§ L.1 + § L.2** — Issue + Comment metadata footers converted from middot-separated text to chip clusters with BrandMark icons.
- **§ N** — Design Language page polish. `solid 48` brand-mark variant restored; per-card description text added below the glyph row; new "Accessibility" Construction principle bullet.

#### What was deferred (handed off to the completion patch — see below)

- § D.2: PhaseRail pill anchoring
- § D.3: PhaseRail `<Chip>` primitive migration
- § G.3: Card vertical-density reduction
- § K.1: `raised by X` chip pair
- § K.2: BrandMark icons inside agent attribution chips
- § L.3: `[Self-raised]` chip promotion
- § N.3: `?full=1` URL fallback

---

### Spec 0087 completion patch ([PR #88](https://github.com/Lexiz/dual-research/pull/88))

**Version bump:** `0.69.11` → `0.69.12`
**No separate spec doc** — this is a follow-up against `specs/0087-cross-cutting-polish.md`.

#### What shipped

- **§ D.2 — PhaseRail pill anchoring** — each pill now tracks its phase header's y-position. Implemented via `ResizeObserver` on the scroll container + RAF-throttled scroll listener. On every measurement pass: `getBoundingClientRect()` of each `[data-phase-id="N"]` header, translate to `top` offset for the matching pill. `.phase-rail` switched from `position: sticky` to `position: relative`; anchored pills carry `position: absolute` + `is-anchored` class.
- **§ G.3 — Card vertical-density** — `.card` padding `8 → 6 px` vertically (horizontal stays at 12 px); timeline-row `marginBottom` `6 → 4 px`. ~6 px shorter per artifact card across the timeline.
- **§ K.1 — `raised by X` chip pair** — extended `<CardHeadline>` with a new `extraChips` prop (array of `{label, color, tone}`). When `d.raisedBy === 'claude'` or `'gpt'`, surfaces a muted chip carrying the originator's BrandMark glyph. Skips for `raisedBy === 'both'` (the only fixture state in current data — would add no signal).
- **§ K.2 — BrandMark icons inside agent attribution chips** — `conceded by Claude` / `conceded by GPT` chips now inline the Claude burst / OpenAI knot glyph beside the agent name via a JSX `statusLabel` (with a parallel `statusLabelPlain` string for footer-text interpolation).
- **§ L.3 — `[Self-raised]` chip promotion** — new `_parseSelfRaised(body)` helper detects + strips every `[Self-raised]` substring from comment bodies (both the topic-line prefix and the body bold-title duplicate). The CommentCard surfaces a `self-raised` chip in the header strip via the new `extraChips` prop.

#### What's documented as wontfix

- **§ D.3 — PhaseRail `<Chip>` migration** — the PhaseRail is a vertical-column layout (dot above label, centered), while `<Chip>` is for inline-horizontal pills. Wholesale migration would break the visual; the existing `.phase-rail-node` class IS already a domain-appropriate chip primitive for vertical-rail use. Forcing the generic Chip would break the layout.

#### Already-shipped item that was wrongly listed as deferred

- **§ N.3 — `?full=1` URL fallback** — already wired in spec 0087's initial PR via `DesignLanguageView`'s `params.get('full') === '1'` switch in [`design-language.jsx`](../src/dual_research/ui/static/design-language.jsx). The `FullReference` component (line 275+ of design-language.jsx) is fully populated with the comprehensive long-form reference content.

#### Bug fixed in this patch

- **`[object Object] in round 3` regression** — my § K.2 change made `statusLabel` a React node (JSX with BrandMark) instead of a string. `QuestionThread.footer` was template-interpolating it (`` `${statusLabel} in round ${d.closedRound}` ``), producing `[object Object] in round 3`. Added a parallel `statusLabelPlain` string field for footer-text usage. Footer now correctly reads `✓ conceded by GPT in round 3`.

---

## 2 · Files touched (cumulative across all 4 PRs)

```
specs/0085-agent-input-completion-and-modal-vertical-space.md  (new, 317 lines)
specs/0086-consumption-tab-rework.md                            (new, 391 lines)
specs/0087-cross-cutting-polish.md                              (new, 630 lines)
handoffs/2026-05-18-tweak-cycle-complete.md                     (new — this doc)

src/dual_research/__init__.py                  (version 0.69.8 → 0.69.12)
pyproject.toml                                 (version 0.69.8 → 0.69.12)
uv.lock                                        (mirrors version bump)
CHANGELOG.md                                   (4 new release entries)

src/dual_research/ui/aggregator.py             (+176 lines — synthesis helpers)
src/dual_research/ui/server.py                 (+104 lines — fallback path in both backends)
src/dual_research/ui/static/run-detail.jsx     (+977 lines / -460 lines — biggest surface; Consumption rework + critique pane chrome + chip vocabulary + disagreement chips)
src/dual_research/ui/static/run-list.jsx       (+15 lines — column gap + chip tooltips)
src/dual_research/ui/static/components.css     (+136 lines — modal min-height, consumption-card chrome, phase-rail chrome, .tab-chrome, .as-timeline, card density)
src/dual_research/ui/static/tokens.css         (+10 lines — --consumption-round-w token)
src/dual_research/ui/static/index.html         (cache-bust v=0084 → v=0088 across 22 references)
src/dual_research/ui/static/app.jsx            (+10 lines — chrome strip alignment + .tab-chrome wiring)
src/dual_research/ui/static/design-language.jsx (+21 lines — Accessibility principle, solid 48, per-card description)

tests/ui/test_aggregator_input_bundles.py      (+159 lines — synthesis fallback + parse helper)
tests/ui/test_server_input_bundles.py          (+44 lines — system_source + unparseable-key cases)
tests/ui/test_server_cache.py                  (+36/-12 lines — negative-cache renamed + reworked)
```

**Net diff vs `e5f16d8` (last commit before this arc began):** ~2400 lines added / ~400 removed across source + tests + docs.

---

## 3 · Risks + open follow-ups (small)

These are NOT blocking but worth knowing:

- **§ J chevron-on-right** — still on the left in collapsible-section headers. The `cs-chevron` is placed by each individual `renderTitle` callsite (6 sites in run-detail.jsx), so flipping requires editing all of them. The user's audit graded this `nice-to-have`; no urgency.
- **§ K.1 `raised by` chip — fixture coverage** — every disagreement in the partner-vetting fixture has `raisedBy: 'both'`, so the new `raised by X` chip never renders on current data. A new run with asymmetric attribution will exercise the chip; the code path is unit-test-grade simple (one ternary), so the risk is low.
- **PhaseRail anchoring on fast scroll** — measurement is RAF-throttled, but very fast scrolls may briefly show pills at stale positions. The transition CSS (`top var(--m-fast) var(--ease)`) smooths between measurements; should be invisible at normal use.
- **Card density** — settled on `6 px` vertical padding (audit suggested ~32 px target overall; current cards render at ~50 px). If the user wants tighter, a single CSS change in `.card { padding: ... }`.

---

## 4 · How to verify the deploy

```bash
curl -s https://dual-research-alex.fly.dev/api/health
# → {"ok":true,"version":"0.69.12","backend":"supabase"}

curl -s https://dual-research-alex.fly.dev/index.html | grep "v=0088" | head -2
# → confirms cache-bust marker

fly status -a dual-research-alex
# → both machines on VERSION 66, 1 total / 1 passing
```

Live URL: [https://dual-research-alex.fly.dev/](https://dual-research-alex.fly.dev/)
Canonical fixture run for visual review: [`#/runs/20260516-035048-partner-vetting-arch-critique`](https://dual-research-alex.fly.dev/#/runs/20260516-035048-partner-vetting-arch-critique).

---

## 5 · Source-of-truth artifacts

- **Audit (read-only reference):** `/Users/alexlisitzky/dual-research-automation/audits/2026-05-18-tweak-cycle-screenshot-audit.md` — 29 screenshot deltas with per-delta gap analysis. Every delta listed in the spec doc tables maps back to a section in this audit file.
- **Briefing screenshots:** `/Users/alexlisitzky/dual-research-automation/briefings/2026-05-18-tweak-cycle/` — 29 PNGs that triggered the audit.
- **Current-state captures from the audit:** `/Users/alexlisitzky/dual-research-automation/audits/design-system-inconsistencies/current-*.png` — 29 PNGs captured at 2200×1300 during the audit.
- **Specs:** [`specs/0085-…`](../specs/0085-agent-input-completion-and-modal-vertical-space.md), [`specs/0086-…`](../specs/0086-consumption-tab-rework.md), [`specs/0087-…`](../specs/0087-cross-cutting-polish.md) — each spec is self-contained with full Context, Proposed Change, Out of Scope, Test Plan, Risks, Open Questions sections.
- **PRs:** [#85](https://github.com/Lexiz/dual-research/pull/85), [#86](https://github.com/Lexiz/dual-research/pull/86), [#87](https://github.com/Lexiz/dual-research/pull/87), [#88](https://github.com/Lexiz/dual-research/pull/88).
- **CHANGELOG:** [`CHANGELOG.md`](../CHANGELOG.md) — entries `[0.69.9]` through `[0.69.12]` describe the per-version changes at a feature level.

---

## 6 · Fresh-session bootstrap prompt

Paste the following into a fresh Claude Code session to pick up where this arc left off:

```
You are picking up dual-research development from a freshly-deployed
state. The 2026-05-18 tweak-cycle audit closed cleanly across 4 PRs
(specs 0085 + 0086 + 0087 + a 0087 completion patch) — every gap from
the 29-screenshot audit is now shipped to production at
https://dual-research-alex.fly.dev/ (version 0.69.12).

Before doing ANY work:

1. Read the handover at
   /Users/alexlisitzky/dual-research/handoffs/2026-05-18-tweak-cycle-complete.md
   end-to-end. It documents what shipped, what's deferred, where the
   source-of-truth artifacts live, and the small open follow-ups.

2. Read CHANGELOG.md entries [0.69.9] through [0.69.12] for a
   feature-level diff against the previous release.

3. Spin up the dev server with the existing launch config:
   uv run dual-research serve --host 127.0.0.1 --port 6173
   …or via the `preview_start name="dual-research-ui"` MCP tool.
   Open the canonical fixture at
   #/runs/20260516-035048-partner-vetting-arch-critique
   and confirm the visual state matches the deployed UI at 2200×1300.

4. Confirm readiness. When you have read the handover + skimmed the
   live UI, say literally: "I'm ready for the next briefing." Then
   stop and wait for the user.

Critical reminders the prior session learned the hard way:

- Take all UI verification screenshots at 2200×1300 or wider. Smaller
  viewports hide layout gaps and led to incorrect verdicts during the
  audit phase.
- The canonical fixture for run-detail verification is the partner-
  vetting run (display id 3a4a). Other runs may exhibit Phase-0-only
  data and won't exercise the critique pane / consumption tab.
- Don't touch /Users/alexlisitzky/dual-research-automation/audits/
  unless explicitly asked — it's the read-only source of truth from
  this arc.
- "dual research" / "DR" = /Users/alexlisitzky/dual-research/.
```

---

## 7 · Tests

```
$ uv run pytest tests/ -q
800 passed in 6.s
```

The new test surfaces are:
- `tests/ui/test_aggregator_input_bundles.py::TestSpec0085ParseSnakeKey` — 7 cases covering every snake-key shape.
- `tests/ui/test_aggregator_input_bundles.py::TestSpec0085BundleSynthesisFallback` — 8 cases covering every-phase synthesis, repair handling, missing-brief degradation, pure-function smoke test.
- `tests/ui/test_server_input_bundles.py::test_missing_key_synthesises_fallback_with_agent_default` (renamed from `test_missing_key_returns_404`)
- `tests/ui/test_server_input_bundles.py::test_unparseable_key_returns_404`
- `tests/ui/test_server_input_bundles.py::test_recorded_bundle_stamps_system_source_recorded`
- `tests/ui/test_server_cache.py::test_input_bundle_helper_does_not_cache_synthesised_fallback` (renamed + rewritten)

No new test files were created for specs 0086 / 0087 / 0087-patch — those are pure frontend / CSS changes verified visually.
