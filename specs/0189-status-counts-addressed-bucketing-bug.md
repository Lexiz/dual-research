---
kind: dev
spec: "0189"
slug: status-counts-addressed-bucketing-bug
title: "Fix: statusCounts.open misses items in `addressed` state — All ≠ Open + Resolved + Drift"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 10
depends_on: ["0173"]
complexity: S
created: 2026-05-23
queued_at: "2026-05-23T00:00:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: deferred-from-0173
promoted_from_draft: ""
---

# Spec 0189 — Fix: statusCounts.open misses items in `addressed` state

> **Type:** bug  |  **Severity:** P2  |  **Affects:** v1.32.0+ (post-spec 0173) — critique-pane bar-2 status segments
> **Bump:** PATCH — bug fix in the §2.4 status-count derivation
> **Evidence:** Spec 0173 handoff `## Deferred during implementation` third bullet — [handoffs/2026-05-23-spec-0173-drain-deferrals-from-0166-0167-0168.md:45](handoffs/2026-05-23-spec-0173-drain-deferrals-from-0166-0167-0168.md:45): *"The `addressed` status (a transitional state between `open` and `resolved` per `stateTone` mapping at run-detail.jsx:~1693) doesn't match either predicate and so falls outside any bucket. If an item lingers in `addressed`, it shows in neither `Open (N)` nor `Resolved (N)` counts and `All` ≠ sum of the others."*

---

## 1. Reproduction

**Environment:** Live app https://dual-research-alex.fly.dev, post-v1.32.0 deploy. Critique pane, bar-2 status segments. Any run where at least one item is currently in the `addressed` transitional state (between raise and resolution / withdrawal — typically the actor has responded but the raiser has not yet conceded or pushed back).

**Steps:**
1. Open any run-detail page on the live app.
2. Navigate to the critique pane (default view for runs that have items).
3. Find a phase where at least one item is in `addressed` state. The `stateTone` mapping at [src/dual_research/ui/static/run-detail.jsx:1693](src/dual_research/ui/static/run-detail.jsx) (post-0173 the equivalent code lives in `ItemCard` around line 1788) confirms `addressed` is a valid `currentState` value distinct from `open` and `resolved`.
4. Read the bar-2 status segments: `All (N) · Open (X) · Resolved (Y) · Drift (Z)`.

**Expected:** `N == X + Y + Z` (with `addressed` items counted under either Open or Resolved per the design contract — spec 0173 §2.4 only listed three buckets, so `addressed` must collapse into one of them).

**Actual:** `N > X + Y + Z`. The bar-2 `Open` count predicate at [src/dual_research/ui/static/run-detail.jsx:7234](src/dual_research/ui/static/run-detail.jsx) is `_isOpenStatus(it.status) && !isDrift(it)` where `_isOpenStatus` at [src/dual_research/ui/static/run-detail.jsx:7135](src/dual_research/ui/static/run-detail.jsx) is `(s) => s === 'open' || s === 'open-new'`. The bar-2 `Resolved` count predicate at [src/dual_research/ui/static/run-detail.jsx:7235](src/dual_research/ui/static/run-detail.jsx) is `_commentIds.has(it.id) || _isResolvedStatus(it.status)` where `_isResolvedStatus` at [src/dual_research/ui/static/run-detail.jsx:7136–7138](src/dual_research/ui/static/run-detail.jsx) is `s === 'resolved' || s === 'answered' || (typeof s === 'string' && s.startsWith('resolved-'))`. Items with `status === 'addressed'` match neither — they get the All count but fall out of every per-state count, producing an arithmetic mismatch the user can see by glance.

## 2. Root cause hypothesis

The bug is structural: when spec 0173 §2.4 introduced the bar-2 segment counts ([src/dual_research/ui/static/run-detail.jsx:7232–7237](src/dual_research/ui/static/run-detail.jsx)), it reused the existing `_isOpenStatus` and `_isResolvedStatus` predicates that `pushItem` had been using since pre-0173 for filtering. Those predicates were defined narrowly: `_isOpenStatus` matches only `'open' | 'open-new'`, `_isResolvedStatus` matches only `'resolved' | 'answered' | 'resolved-*'`. The `addressed` value — which is a real status value emitted by the item-state machine, used as `currentState` for items that are mid-arc — is not covered by either predicate. The pre-0173 `pushItem` code path falls through to the "Unknown status" warning branch at [src/dual_research/ui/static/run-detail.jsx:7156–7160](src/dual_research/ui/static/run-detail.jsx) and buckets `addressed` items into `openCarriedItems` (the "this is open, just carried over from an earlier round" pile) by default. That fallback is correct for `pushItem`'s purposes but the new `statusCounts.open` predicate at line 7234 doesn't have an analogous "unknown status counts as open" fallback. Both lines 7234 and 7235 use strict-match predicates and so `addressed` falls between the cracks.

Two places need to agree: `pushItem`'s bucketing logic (`addressed` → open) and the `statusCounts.open` count predicate (`addressed` → should also count toward open).

## 3. Fix

The narrowest fix: route `addressed` into the `Open` bucket consistently. Two equivalent ways to express it; pick option A.

**Option A (recommended):** Widen `_isOpenStatus` to include `'addressed'`. One-line change at [src/dual_research/ui/static/run-detail.jsx:7135](src/dual_research/ui/static/run-detail.jsx):

```jsx
// Before
const _isOpenStatus = (s) => s === 'open' || s === 'open-new';

// After
const _isOpenStatus = (s) => s === 'open' || s === 'open-new' || s === 'addressed';
```

This update flows automatically through:
- `statusCounts.open` at [src/dual_research/ui/static/run-detail.jsx:7234](src/dual_research/ui/static/run-detail.jsx) — `addressed` items now count.
- `pushItem` at [src/dual_research/ui/static/run-detail.jsx:7146](src/dual_research/ui/static/run-detail.jsx) (status-filter early-return) and [src/dual_research/ui/static/run-detail.jsx:7157](src/dual_research/ui/static/run-detail.jsx) (open-bucket assignment) — `addressed` items now match the explicit Open branch instead of falling through to the warning + default bucket. Net behavior change in `pushItem`: an `addressed` item that previously triggered the `console.warn('[critique] unknown item.status:', it.status, it)` warning no longer triggers it. The bucketing outcome is the same (it lands in `openCarriedItems`).

**Option B (more conservative):** Add `addressed` only to the `statusCounts.open` predicate, leaving `_isOpenStatus` unchanged. Inline the union at line 7234:

```jsx
open: allPhaseItems.filter(it => !_commentIds.has(it.id) && (_isOpenStatus(it.status) || it.status === 'addressed') && !isDrift(it)).length,
```

This avoids touching `pushItem`'s warning path but duplicates the status-set definition. Option A is cleaner — `_isOpenStatus` is the canonical "what counts as open?" predicate, and `addressed` belongs in that set.

**Why route `addressed` to Open, not Resolved.** The handoff explicitly recommended this: *"route `addressed` into `Open` (consistent with the legacy bucketing in `pushItem`)."* And the design contract: `addressed` means "the actor has responded but the item is not yet closed" — by definition, still open from the raiser's POV. Resolution requires the raiser to accept (`resolved`), withdraw (`withdrawn`), or be capped (`capped`). The `stateTone` mapping at the current [src/dual_research/ui/static/run-detail.jsx:1788+](src/dual_research/ui/static/run-detail.jsx) `ItemCard` declaration tones `addressed` as `info` — same tone as `open` — corroborating that `addressed` reads as a not-yet-closed state.

## 4. Regression-prevention test

A test that fails before the fix and passes after. Lives under [tests/spec0189/](tests/spec0189/) (mirroring the convention from `tests/spec0173/`).

- [ ] **Test:** `test_status_counts_addressed_routes_to_open` — structural test using a regex pattern over [src/dual_research/ui/static/run-detail.jsx](src/dual_research/ui/static/run-detail.jsx). Asserts: `_isOpenStatus` definition string contains `'addressed'`. Fails before the fix (predicate omits `addressed`), passes after.

The simpler structural form is preferred over a JSX/jsdom runtime test because the existing `tests/spec0173/test_item_round_shape.py` already establishes the pattern of using regex over `run-detail.jsx` to catch the kind of bucket-mismatch bug this spec is fixing.

A secondary, optional test:

- [ ] **Test:** `test_status_counts_arithmetic_invariant` — build a minimal `allPhaseItems` fixture (small JS object array in a `.txt` testdata file) including one item per status value (`open`, `open-new`, `addressed`, `resolved`, `answered`, `resolved-aligned`, `withdrawn`, `capped`) and exercise the predicates via Python translation of the JS logic (or just structural assertions). Assert: `len(allPhaseItems) == open_count + resolved_count + drift_count + neither_count` where `neither_count` must be 0 after the fix. This is heavier than the structural test and is welcome but not required.

## 5. Blast radius

Two call sites consume `_isOpenStatus`:

1. **`pushItem`** at [src/dual_research/ui/static/run-detail.jsx:7146, 7157](src/dual_research/ui/static/run-detail.jsx). Behavior change: items with `status === 'addressed'` now match the explicit open-branch in both the filter-early-return (line 7146) and the bucketing if-chain (line 7157). Previously they fell through to the `openCarriedItems.push(item)` default at line 7161 *via* the warning branch. Bucketing outcome is identical — `addressed` items still land in `openCarriedItems` (since their `_itemRound` is typically less than `latestRound`, the `openNewItems` branch at line 7159 is not taken). The visible difference is one fewer console warning per `addressed` item. Net: a small win.

2. **`statusCounts.open`** at [src/dual_research/ui/static/run-detail.jsx:7234](src/dual_research/ui/static/run-detail.jsx). Behavior change: the Open chip now reports the count the user expects.

No other consumers. The widened predicate does not leak outside the file (no exports, no shared module). The `stateTone` mapping at [src/dual_research/ui/static/run-detail.jsx:1788+](src/dual_research/ui/static/run-detail.jsx) inside `ItemCard` independently maps `addressed` to `info` tone — that mapping is read-only relative to this fix and stays as-is.

## 6. Out of scope

- **The `statusCounts.resolved` predicate.** It uses `_isResolvedStatus`, which already covers the only resolved states (`resolved`, `answered`, `resolved-*`). It does not over-count, does not under-count, and `addressed` is correctly excluded from it (it would be wrong to call `addressed` resolved). Leave alone.
- **A fifth `Addressed (N)` count chip.** The handoff floated this as an alternative ("either route `addressed` into `Open` … or add a fifth count chip"). The spec body listed only `Open / Resolved / Drift` so a fifth chip would over-step. Out of scope.
- **Other potentially-uncovered status values.** A grep through the codebase for `it.status === ...` reveals only the values matched by the existing predicates plus `addressed`. If a future spec introduces additional statuses (`hibernated`, `escalated`, etc.), they'll need their own bucketing decision and may regress this invariant. That's a future-spec concern.
- **`pushItem`'s console.warn** at [src/dual_research/ui/static/run-detail.jsx:7156–7160](src/dual_research/ui/static/run-detail.jsx). This fix incidentally silences it for `addressed` items. The warning stays in place for other unknown statuses — out of scope to refactor or remove.
- **The `_itemRound` and `latestRound` interaction** at line 7158–7161 that decides between `openNewItems` and `openCarriedItems`. Unchanged. Addressed items still land in `openCarriedItems` per the round comparison.
- **Bar-1 run-wide counts** at [src/dual_research/ui/static/run-detail.jsx:6986–6987](src/dual_research/ui/static/run-detail.jsx). Those use a different predicate (`it.status === 'open'` for `runWideOpen` and `it.status !== 'open'` for `runWideResolved`) — `addressed` items count under `runWideResolved` there because they don't match `=== 'open'`. That's a separate inconsistency, but the handoff did not flag it and the spec body did not list it in §2.4 — separate spec.

## 7. Risks

- **Behavioral side-effect from widening `_isOpenStatus`.** `pushItem`'s status-filter early-return at line 7146 includes `!_isOpenStatus(it.status)` as a reject clause for `statusFilter === 'open'`. Widening the predicate means an `addressed` item that the user filtered to via the Open tab is no longer rejected here — but it also wasn't being shown before (it would fall through to the bucketing chain and land in `openCarriedItems`, which the Open filter displays). Net visible: same — `addressed` items show up in the Open tab both before and after the fix, just via a cleaner code path.
- **The fix changes `pushItem`'s console.warn output.** A monitoring or screenshot tool that scrapes `console.warn` lines as a regression signal would see one fewer warning per addressed item. Unlikely to exist; not load-bearing. Mitigation: the test plan's structural test fails if the predicate isn't widened, so we have a positive signal that the fix landed.
- **Future status additions.** A new spec adding `hibernated` or another transitional state would re-introduce this bug. Mitigation: out of scope here; document the invariant ("`statusCounts.open + statusCounts.resolved + statusCounts.drift == statusCounts.all`") in the code comment above `statusCounts`.
- **Race with spec 0188.** Spec 0188 touches `ItemCardIssueBody` and `ItemCardCommentBody` (lines ~1699–1767) — well above the lines this spec touches (~7135 and ~7234). No conflict expected.
