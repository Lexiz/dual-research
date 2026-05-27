---
kind: dev
spec: "0223"
slug: phase4-turn-cards-render-issues-comments-deltas
title: "Fix: Phase 4 turn cards drop Issues + Comments per-round Δ chips (Q→D→I→C contract violated)"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-26
queued_at: ""
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

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §7 Out of scope with a
named follow-up target. -->

# Spec 0223 — Fix: Phase 4 turn cards drop Issues + Comments per-round Δ chips (Q→D→I→C contract violated)

> **Type:** bug  |  **Severity:** P2  |  **Affects:** every run-detail Timeline view at `https://dual-research-alex.fly.dev/#/runs/<id>` once Phase 4 (Cross-review) has started — visible across all browsers, both themes, at every viewport. Confirmed on deployed v1.45.1.
> **Bump:** PATCH — bug fix; no API surface change, no DS primitive change.
> **Evidence:** User screenshot of the Phase 4 (Cross-review) section on the deployed app — phase header chip cluster correctly carries all four canonical category chips (Q `1 +1/−0` · D `0 +2/−2` · I `18 +22/−4` · C `5 +5/−0`) per [TlPhaseHeadChips at run-detail.jsx:1027-1076](src/dual_research/ui/static/run-detail.jsx:1027), but every per-turn row in the same phase (Claude turn 1, GPT turn 1, …, Claude turn 3, GPT turn 3) shows only two per-round Δ chips on the right — visibly the Q (info / blue) and D (warn / amber) tones; no err-tone (I) chip and no idle-tone (C) chip is rendered in the per-turn `.tl-card-head__right` cluster. The deployed JS at `https://dual-research-alex.fly.dev/run-detail.jsx?v=0221a` was confirmed byte-identical to HEAD on the relevant render block, so this is a runtime / data-shape gap, not a source regression.

---

## 1. Reproduction

**Environment:** Deployed app at `https://dual-research-alex.fly.dev/` v1.45.1 (also reproduces on local `uv run dual-research-ui-dev` against any local fixture run that completed Phase 4 with ≥ 1 cross-review round). All browsers, both themes, every viewport width.

**Steps:**
1. Open any run that reached Phase 4 cross-review — example: `https://dual-research-alex.fly.dev/#/runs/20260521-010637-dvs-backend-language-choice`.
2. Scroll to the Phase 4 (Cross-review) section in the Timeline.
3. Compare the phase-header chip cluster (rendered by [`TlPhaseHeadChips`](src/dual_research/ui/static/run-detail.jsx:1027)) against the per-turn `.tl-card-head__right` cluster on each Claude / GPT turn row (rendered inside [`TlTurnRow`](src/dual_research/ui/static/run-detail.jsx:1155) at [run-detail.jsx:1288-1320](src/dual_research/ui/static/run-detail.jsx:1288)).

**Expected:** Each per-turn card carries **four** per-category Δ chips on the right cluster, in fixed Q → D → I → C order, in identical styling to the phase-header chips above them — per [design-system/SPEC.md §9.2](design-system/SPEC.md) row "Category counter (dense)" (rendered on `timeline turn cards; phase headers`) and [§9.4](design-system/SPEC.md) rule 8 (`Zero-activity chips render dim (opacity 0.55) but stay present so category columns align across rounds`). Per-turn card right cluster shape:

```
[+Q | −Q] [+D | −D] [+I | −I] [+C | −C] [status] [chev]
```

Each chip carries the per-round `raised` (green `+N`) and `closed` (red `−N`) delta — slim-Δ presentation per [design-system/SPEC.md §9.2](design-system/SPEC.md) ("Category counter (dense)" — value · +raised · −closed). Q+D totals across all per-turn rows in a phase must sum to the corresponding phase-header chip's add/sub values; the same parity must hold for I + C once the fix lands.

**Actual:** Per-turn cards render only **two** Δ chips on the right cluster: Q (info tone) and D (warn tone). The I (err) and C (idle) chips are absent from the DOM. The phase header is unaffected — it correctly renders all four. The Q→D→I→C category-column-alignment contract from [SPEC §9.4](design-system/SPEC.md) rule 8 is silently violated: a downward column scan across the phase reveals two chip columns where four should be.

## 2. Root cause hypothesis

The JSX render site at [run-detail.jsx:1209-1211](src/dual_research/ui/static/run-detail.jsx:1209) *intends* to render all four categories for Phase 4 per-turn rows:

```js
const chipCategories = (phase === 4)
  ? ['questions', 'disagreements', 'issues', 'comments']
  : ['questions', 'disagreements'];
```

The map block downstream at [run-detail.jsx:1298-1320](src/dual_research/ui/static/run-detail.jsx:1298) iterates `chipCategories` with a `{ standing:0, raised:0, closed:0, capped:0 }` fallback for missing keys on `item.stats.categories`, and a `dim` modifier when `(raised + closed) === 0` — so even when I + C have zero activity, four chips should appear (two dim, two saturated as appropriate). The DS primitive `<Chip>` at [shared.jsx:1620+](src/dual_research/ui/static/shared.jsx) does not early-return on `dim` — `dim` only sets a CSS class that drops opacity to 0.55. Verified the deployed asset at `https://dual-research-alex.fly.dev/run-detail.jsx?v=0221a` is byte-identical to HEAD on these lines.

Yet only two chips render. The two non-mutually-exclusive runtime gaps that can produce this output, ranked by likelihood:

1. **Most likely — `phase` identity mismatch.** `item.phase` on Phase 4 cross-review turn rows is not the integer `4`. Possible non-`=== 4` values: the string `"4"`, the string `"phase4"`, `null` (cross-review turn rows historically had a wonky phase field — see the spec-0166 §2.4 defensive turn-render carve-out at [run-detail.jsx:1268-1280](src/dual_research/ui/static/run-detail.jsx:1268) and the spec-0119 (3/9) timeline turn-card migration that introduced this conditional). Strict equality at line 1209 then falls through to the two-category default. Phase 0 + Phase 2 (which DO render two chips correctly) presumably carry integer `0` / `2` — they pass the implicit "is this a known phase" check downstream because the else-branch is `['questions','disagreements']`, which happens to be what they need; the bug is silent there.

2. **Secondary — `item.stats.categories` shape gap.** The Python aggregator's [`TurnCategoryStats`](src/dual_research/ui/models.py:363) dataclass has all four fields (`questions` / `disagreements` / `issues` / `comments` — each a `CategoryCounters`) and the aggregator's `_apply_raise` / `_apply_transition` at [items.py:118-156](src/dual_research/ui/items.py:118) / [items.py:232-316](src/dual_research/ui/items.py:232) populates them via the `_KIND_TO_FIELD` dispatch at [items.py:63-68](src/dual_research/ui/items.py:63) for all four item kinds. So the in-memory model is complete. The JSON projection to the frontend (most likely `dataclasses.asdict` or an explicit serializer in [aggregator.py](src/dual_research/ui/aggregator.py) — implementer to grep for the `categories` projection in the turn-stats payload) may emit only the keys that have non-zero values, dropping zero-valued `issues` / `comments` keys. The JSX fallback at line 1299 already covers a missing key — so this gap alone would NOT prevent rendering as long as hypothesis 1 is fixed. Both gaps may be present; both should be checked.

3. **Less likely — CSS hides err / idle chips on `.tl-card-head__right`.** Quick grep on [components.css](src/dual_research/ui/static/components.css) for any rule that scopes `.tone-err` or `.tone-idle` inside `.tl-card-head` returns zero hits. The chip media queries at [components.css:1104+](src/dual_research/ui/static/components.css:1104) only target the critique pane filter row, not timeline cards. Rule out via DOM inspection during implementation, but do not refactor CSS speculatively if the JSX fix resolves the symptom.

**The implementer's first 15 minutes** should be a DOM inspection on the run cited above (`20260521-010637-dvs-backend-language-choice`) — open devtools, evaluate `JSON.stringify(window.__RUN__?.timeline?.find(it => it.phase === 4 && it.round === 1 && it.agent === 'claude') ?? document.querySelector('.tl-phase[data-phase="4"] .tl-thread .tl-card-head'))` or read the equivalent `bundle.json` for a local fixture run — to confirm the actual `item.phase` value emitted for cross-review turn rows. The fix follows mechanically from what's observed:

- **If `item.phase` is `"phase4"` / `"4"` / `null` for cross-review rows:** fix at the data source so `item.phase === 4` (integer) is the project-wide contract across `run.timeline`. Locate the cross-review turn-row assembly by grepping `aggregator.py` for the phase 4 timeline branch (likely near [aggregator.py:718](src/dual_research/ui/aggregator.py:718) `elif phase == 4:`). This is the canonical fix — Phase 0 + Phase 2 rows already pass `=== 4`-style numeric checks, so making Phase 4 conform restores invariant parity.
- **If `item.phase` is `4` (integer) and the JSX conditional is firing correctly:** the secondary gap (hypothesis 2) is the actual culprit — the JSON projection drops zero-valued I/C keys before they reach `categories[cat]`. Even then, the existing `|| { standing:0, raised:0, closed:0, capped:0 }` fallback should cover it; if it does not, follow the chain to find the dropping serializer and stop it from dropping.

Whichever combination is found, the user-visible acceptance is: four chips per Phase 4 turn card, in Q→D→I→C order, with the same `dim` / `+raised` / `−closed` / `⊘ capped` semantics as Q + D today.

## 3. Fix

Single coherent change, expected ≤ 30 LOC across source + test:

1. **Identify the actual `item.phase` value emitted on cross-review turn rows** via DOM inspection on a deployed run with Phase 4 data (see §2). One of the two fix paths below applies.

2. **Path A — phase-identity normalisation at the data source (preferred when applicable).** Fix the aggregator so cross-review turn rows in `run.timeline` carry `phase: 4` (integer) — the same shape Phase 0 / Phase 2 rows already use. Locate the cross-review turn-row assembly in [aggregator.py](src/dual_research/ui/aggregator.py) (grep entry points: `elif phase == 4:` near [aggregator.py:718](src/dual_research/ui/aggregator.py:718), and the `"phase4"` string at [aggregator.py:1402](src/dual_research/ui/aggregator.py:1402) which may be coercing the int into a string in a turn-row dict). Normalise the assignment so the timeline-item `phase` field is always the int. This is the structurally-correct fix: the rest of `run.timeline` (including the phase header chip cluster, which works correctly today) assumes integer phase identity.

3. **Path B — fix the JSX conditional defensively (fallback if Path A is non-trivial).** If the `phase` field is intentionally non-integer for cross-review rows for some upstream reason, normalise at the consumer at [run-detail.jsx:1209](src/dual_research/ui/static/run-detail.jsx:1209):

   ```js
   const phaseNum = Number(item.phase);
   const chipCategories = (phaseNum === 4)
     ? ['questions', 'disagreements', 'issues', 'comments']
     : ['questions', 'disagreements'];
   ```

   This handles `4`, `"4"`, and `4.0`; it does NOT handle `"phase4"` or `null` — if the data emits those, Path A is mandatory because Path B's defensive coercion would mask the data-layer regression and silently keep Phase 4 acting like a non-int phase elsewhere in the file. **Path A is strongly preferred** unless the implementer discovers a load-bearing reason the data layer cannot emit integer `4`.

4. **Verify hypothesis 2 once Path A or B is in.** Reload, DOM-inspect a Phase 4 turn row, confirm four `.chip` elements in `.tl-card-head__right` (excluding the trailing status chip and chevron). If only two render after Path A/B lands, the JSON projection IS dropping zero-valued I/C keys for turn-stats — find the serializer in [aggregator.py](src/dual_research/ui/aggregator.py) / [models.py](src/dual_research/ui/models.py) that projects `TurnCategoryStats` and make sure all four keys are always emitted (even at zero). The JSX fallback at line 1299 covers a missing key, so this only matters if Path A/B isn't enough on its own.

5. **No CSS change expected.** The existing `<Chip tone="err">` and `<Chip tone="idle">` configurations already power the Phase 4 header I / C chips at [TlPhaseHeadChips at run-detail.jsx:1053-1073](src/dual_research/ui/static/run-detail.jsx:1053). Per-turn cards use the same primitive; once the data path delivers, no CSS work is needed. If CSS changes turn out to be required, land them in both [`src/dual_research/ui/static/components.css`](src/dual_research/ui/static/components.css) AND [`design-system/assets/styles/composed-components.css`](design-system/assets/styles/composed-components.css) in the same commit per the CLAUDE.md dual-write invariant.

**Files touched (expected):**

- [`src/dual_research/ui/aggregator.py`](src/dual_research/ui/aggregator.py) — Path A: normalise cross-review turn-row `phase` to integer `4`. ~1–5 LOC.
- [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) — Path B (only if Path A blocked): defensive `Number()` coercion at line 1209. ~1 LOC.
- [`src/dual_research/ui/models.py`](src/dual_research/ui/models.py) and/or [`aggregator.py`](src/dual_research/ui/aggregator.py) — only if hypothesis 2 is also active: ensure JSON projection of `TurnCategoryStats` emits all four `categories` keys.
- [`tests/test_spec_0223_phase4_turn_chips.py`](tests/test_spec_0223_phase4_turn_chips.py) — new, source-pattern test pair plus an aggregator-level integer-phase assertion.
- [`CHANGELOG.md`](CHANGELOG.md), [`pyproject.toml`](pyproject.toml), [`src/dual_research/__init__.py`](src/dual_research/__init__.py) — patch version bump per project convention; CHANGELOG entry under `### Fixed` linking back to this spec.

## 4. User stories & acceptance criteria

UI bug. Both subsections REQUIRED per template §4.

### 4.1 — User stories

> As a `researcher`, I want each Phase 4 (Cross-review) turn card to show how many Issues and Comments were raised and resolved in that round — alongside the Questions and Disagreements counters that are already there — so that I can scan a single column of cards to see how each agent's review round contributed to convergence without scrolling up to the phase header for the totals.

> As a `viewer` reviewing a finished run for retrospective, I want the per-turn chip cluster on Phase 4 cards to have the same Q → D → I → C anatomy as the phase header above it, so that the visual relationship "phase totals = sum of per-turn deltas" is self-evident and the four-category column alignment from `design-system/SPEC.md` §9.4 rule 8 actually holds on this surface.

### 4.2 — Acceptance scenarios (BDD)

> **Scenario 1:** Phase 4 turn card carries four category Δ chips in fixed order
> GIVEN a run that reached Phase 4 cross-review with ≥ 1 review round on each agent (e.g. `https://dual-research-alex.fly.dev/#/runs/20260521-010637-dvs-backend-language-choice`)
> WHEN the user scrolls to the Phase 4 section and inspects any per-turn card's `.tl-card-head__right` cluster
> THEN the cluster contains exactly four `<Chip>` elements before the trailing status chip and chevron, in DOM order: `tone-info` (Q), `tone-warn` (D), `tone-err` (I), `tone-idle` (C) — matching the canonical Q → D → I → C order from [SPEC.md §9.3](design-system/SPEC.md) and §9.4 rule 3.

> **Scenario 2:** Phase 4 turn card category-Δ values sum to the phase-header chip totals
> GIVEN the same Phase 4 view as scenario 1, with the phase-header chips showing Q `+a/−b` · D `+c/−d` · I `+e/−f` · C `+g/−h`
> WHEN the user mentally (or a test programmatically) sums the per-round `add` / `sub` values across all per-turn cards in the phase for one category (e.g. Issues)
> THEN the per-turn sum equals the phase-header chip's `add` / `sub` for that category — the per-turn cluster is the round-by-round breakdown of the header's roll-up.

> **Scenario 3:** Phase 0 and Phase 2 per-turn cards still render only two category chips (no regression)
> GIVEN a run with completed Phase 0 (briefing dialog) and Phase 2 (clarification dialog) rounds
> WHEN the user inspects any Phase 0 or Phase 2 per-turn card's `.tl-card-head__right` cluster
> THEN the cluster contains exactly two `<Chip>` elements before the trailing status chip and chevron, in DOM order: `tone-info` (Q) and `tone-warn` (D) — Phase 0 and Phase 2 do not raise Issues or Comments, so adding empty I / C chips there would be wrong.

> **Scenario 4:** Zero-activity Phase 4 categories render dim, not absent
> GIVEN a Phase 4 turn row where one agent raised no Issues and no Comments in that round (e.g. Claude turn 1 with all zeros for I and C)
> WHEN the user inspects that card's `.tl-card-head__right` cluster
> THEN the I and C chips are still present in the DOM, carrying the `dim` modifier (opacity 0.55 per [SPEC.md §9.4](design-system/SPEC.md) rule 8) and `+0 / −0` values — they are dim, not omitted, so the four-column scan still aligns.

## 5. Regression-prevention test

- [ ] **Source-pattern test (new):** [`tests/test_spec_0223_phase4_turn_chips.py`](tests/test_spec_0223_phase4_turn_chips.py) — pure stdlib via [`tests/_ui_pattern_helpers.py`](tests/_ui_pattern_helpers.py), per [design-system/SPEC.md §13](design-system/SPEC.md) UI test doctrine. Three checks:
  1. **Positive — four-category list literal present on the Phase 4 branch.** `assert_jsx_contains` on [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) for a regex matching the four-category list `['questions', 'disagreements', 'issues', 'comments']` inside a `chipCategories` ternary whose condition references `phase` / `phaseNum` and `=== 4`. Whitespace-flexible.
  2. **Antipodal — two-category list NOT used as Phase 4 branch.** `assert_jsx_lacks` for any `chipCategories` assignment that pairs `phase === 4` (or `phaseNum === 4`) with the two-category list. Locks against a future revert.
  3. **Positive — render-site downstream still maps `chipCategories` to per-chip `<Chip>` with `add` / `sub` from `raised` / `closed`.** Anchors the spec-0133 §5.9 slim-Δ presentation so a future "let's just show standing" regression flags here.

- [ ] **Aggregator unit test (new — only fires when Path A from §3 is taken):** if the fix touches [`aggregator.py`](src/dual_research/ui/aggregator.py) to normalise cross-review turn-row `phase`, add an assertion in [`tests/`](tests/) (reuse the closest existing Phase 4 aggregator-fixture test if one exists; otherwise add a small one) that asserts `isinstance(timeline_item['phase'], int) and timeline_item['phase'] == 4` for every cross-review turn row in a fixture run's projected timeline. The same test should also assert the projected `categories` dict on those rows always contains all four keys (`questions`, `disagreements`, `issues`, `comments`) — covers hypothesis 2 from §2.

- [ ] **No-regression on Phase 0 + Phase 2:** the source-pattern test from check 1 also `assert_jsx_contains` for the two-category list literal remaining as the else-branch of the same ternary. If a future refactor accidentally drops the two-category branch, this fails — Phase 0 + Phase 2 must keep their two-chip cluster.

- [ ] **Runtime verification (not a Python test — goes in the PR description per [design-system/SPEC.md §13.3](design-system/SPEC.md) and CLAUDE.md UI test doctrine):** Claude Preview MCP screenshot of the Phase 4 section of the cited run, showing each per-turn card with four Q / D / I / C chips, plus a screenshot of an unaffected Phase 0 turn card to demonstrate no regression. Sum at least one category's per-turn deltas in the screenshot caption and confirm it matches the phase-header chip.

## 6. Blast radius

**Consumers of the Phase 4 per-turn chip render block:**

- The single render site at [run-detail.jsx:1298-1320](src/dual_research/ui/static/run-detail.jsx:1298) (`TlTurnRow` component). One DOM site per Phase 4 turn row in the Timeline pane. No other surface consumes `chipCategories` from `TlTurnRow`.

**Consumers of `item.phase` if Path A is taken (data-layer normalisation):**

- [`TlPhaseHeadChips`](src/dual_research/ui/static/run-detail.jsx:1027) already uses `phaseId === 4` for the header chip cluster — works today, so the data already carries the right value at the *phase* level. Path A would extend that correctness to per-turn rows, which currently diverge.
- The defensive turn-render at [run-detail.jsx:1268-1280](src/dual_research/ui/static/run-detail.jsx:1268) (spec 0166 §2.4) — this branch handles non-numeric `item.round`, not `item.phase`; unaffected.
- The provider-stripe `:has()` selectors at [components.css:2696-2713](src/dual_research/ui/static/components.css:2696) — read off the identity chip's `tone-claude` / `tone-gpt`, not off `item.phase`; unaffected.
- Any other JSX that does `phase === N` arithmetic — grep `src/dual_research/ui/static/*.jsx` for `phase ===` before merging; the fix should consolidate the contract that `item.phase` is always an int across `run.timeline`.

**Consumers of the JSON projection of `TurnCategoryStats` (if hypothesis 2 is also addressed):**

- Same single render site at [run-detail.jsx:1298-1320](src/dual_research/ui/static/run-detail.jsx:1298). The phase-header chip cluster reads `phaseStats.phaseSummary_N`, a sibling projection ([run-detail.jsx:1028](src/dual_research/ui/static/run-detail.jsx:1028)), not the per-turn projection — so a per-turn projection fix does not touch the header.

**Why this doesn't break adjacent callers:** the fix either normalises a data-layer field that was already inconsistent with the rest of the codebase (Path A — restores invariant parity) OR adds a defensive `Number()` coercion at the JSX site (Path B — strictly additive at the consumer). Both keep Phase 0 + Phase 2 rendering unchanged (else-branch unchanged). The DS primitive `<Chip>` is not modified.

## 7. Out of scope

- **Narrow-viewport overflow of the Phase 4 header chip cluster** (the user-flagged separate concern that the introduction of the `⚠ ledger drift` chip pushes the row past the available width at certain viewports). Do NOT touch [`TlPhaseHeadChips`](src/dual_research/ui/static/run-detail.jsx:1027), the `⚠ ledger drift` chip, or any `@media` rules under `.tl-phase__chips`. **Deferred to a follow-up dev spec to be drafted post-merge** — once this fix lands, per-turn rows also get four chips, which may make the right-cluster overflow worse on those rows too; the follow-up spec should consider both surfaces together.
- **Anything else on the Phase 4 surface beyond the per-turn category Δ chips** — no expanded-card body changes, no critique-pane chip changes, no header layout work, no badge governance vocabulary changes ([SPEC.md §9.5](design-system/SPEC.md) stays as-is).
- **Refactoring the `phase`-identity contract across the wider codebase.** This spec fixes the cross-review turn-row data shape (Path A) OR adds a single defensive coercion at the consumer (Path B). A broader audit of "every place that does `phase === N`" is out of scope; a single grep-pass during implementation to confirm no immediate collateral is required, but not a refactor.
- **Adding a Playwright / DOM-rendering test.** Per [`design-system/SPEC.md` §13](design-system/SPEC.md) and CLAUDE.md UI test doctrine, this codebase locks UI anatomy via source-pattern tests, not DOM harnesses. Runtime verification lives in the PR description via Claude Preview MCP screenshots. (The §13 trigger that would revisit this remains: a categorical class of bugs not catchable by source patterns.)

## 8. Risks

- **Picking Path B when Path A is the right answer.** If `item.phase` is `"phase4"` / `null` / something else non-int for cross-review rows AND other consumers in the file silently rely on that wrongness, Path B (consumer-side coercion) masks the underlying contract drift and leaves a hidden trap for future work. Mitigation: implementer must DOM-inspect first, prefer Path A, and only fall back to Path B with an explicit `// spec-0223: …` justification noting why Path A was infeasible.
- **Per-turn chip cluster gets visually crowded at narrow viewports** once four chips render instead of two. Mitigation: per §7 this is explicitly deferred to a follow-up spec; this fix prioritises restoring the DS §9.4 rule 8 invariant. If overflow becomes acute on the runtime-verification screenshot, the implementer may add a one-line PR-description note flagging it for the follow-up — but does not widen scope.
- **Cached browser stylesheets / JSX assets.** Existing cache-busting URL parameters on static assets (`?v=…`) handle this on deploy; no spec-level action required.
- **Hypothesis 2 turns out to be the dominant cause.** If the JSON projection IS dropping zero-valued `issues` / `comments` keys for turn-stats AND the JSX fallback fails to cover it for a reason not visible from the file read in §2, the fix must also touch the serializer. Mitigation: §5 check 2 (the aggregator unit test) asserts the projected `categories` dict carries all four keys, so the gap surfaces in tests if it is present.
