---
kind: dev
spec: "0183"
slug: authoring-funnel-drafts-count-includes-current-backlog
title: "Fix: authoring funnel DRAFTS bucket only counts promoted drafts, omits current backlog under `specs/drafts/`"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 6
depends_on: []
complexity: S
created: 2026-05-22
queued_at: "2026-05-22T21:50:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: deferred-from-0177
promoted_from_draft: ""
---

# Spec 0183 — Fix: authoring funnel DRAFTS bucket only counts promoted drafts, omits current backlog under `specs/drafts/`

> **Type:** bug  |  **Severity:** P2  |  **Affects:** spec dashboard Metrics tab → §2.4.7 authoring funnel — the leftmost (DRAFTS) bucket.
> **Bump:** PATCH — single signature change to plumb `drafts` from `render_index` into `_render_metrics` → `_render_authoring_funnel`.
> **Evidence:** Spec 0177 handoff `## Deferred during implementation` second bullet — [handoffs/2026-05-22-spec-0177-dashboard-redesign-v3-horizontal-hero-and-metrics.md:41](handoffs/2026-05-22-spec-0177-dashboard-redesign-v3-horizontal-hero-and-metrics.md:41). The spec said "current draft count + drafts promoted in last 30 days"; the implementation only delivered the second half.

---

## 1. Reproduction

**Environment:** any dashboard render against a repo whose `specs/drafts/` directory contains one or more drafts that have *not* been promoted (i.e. files like `specs/drafts/draft-001-foo.md` exist and have `kind: draft` frontmatter, but no `specs/NNNN-foo.md` has `promoted_from_draft: 001`).

**Steps:**

1. Add `N` draft files under `specs/drafts/` with `kind: draft` frontmatter. None of them get promoted in the last 30 days.
2. Run `uv run python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out /tmp/dash` (or load the live dashboard) and navigate to the Metrics tab.
3. Locate the authoring funnel SVG (last block on the Metrics tab). Read the DRAFTS bucket count (large number, e.g. `0`).

**Expected:** The DRAFTS bucket count is the **number of current unpromoted drafts plus drafts that became queued specs in the last 30 days** — i.e. the full "drafts that ever existed in this 30d window" picture as the spec 0177 §2.4.7 description called for ("current draft count + drafts promoted in last 30 days"). With N current drafts and zero recent promotions, the bucket reads `N`.

**Actual:** The DRAFTS bucket reads only the count of recent promotions. Unpromoted backlog drafts are invisible. With N current drafts and zero recent promotions the bucket reads `0`, falsely implying no authoring activity even though there are N parked ideas waiting.

## 2. Root cause hypothesis

[scripts/spec_lifecycle/render_dashboard.py:1221-1257](scripts/spec_lifecycle/render_dashboard.py:1221) — `_render_authoring_funnel(specs, now)` only receives `specs` (the list of `SpecRow` objects from `specs/*.md`). It has no handle on the `DraftRow` list. Its `drafts_count` is computed at [scripts/spec_lifecycle/render_dashboard.py:1257](scripts/spec_lifecycle/render_dashboard.py:1257) as `drafts_count = promoted_recent` — exactly the count of specs whose `promoted_from_draft` frontmatter is set and whose `queued_at` is within the last 30 days. The "current drafts under `specs/drafts/`" half of the bucket is simply missing from the function.

The plumbing gap is one level up. [scripts/spec_lifecycle/render_dashboard.py:2014](scripts/spec_lifecycle/render_dashboard.py:2014) — the call site — passes only `specs`:

```python
parts.append(_wrap_region("metrics", _render_metrics(specs, now)))
```

And [scripts/spec_lifecycle/render_dashboard.py:675](scripts/spec_lifecycle/render_dashboard.py:675) — `_render_metrics(specs, now)` — never receives `drafts`. But `drafts` *is* available in the calling scope: `render_index` accepts both lists at [scripts/spec_lifecycle/render_dashboard.py:1918-1921](scripts/spec_lifecycle/render_dashboard.py:1918) and `collect()` populates them both at [scripts/spec_lifecycle/render_dashboard.py:128-156](scripts/spec_lifecycle/render_dashboard.py:128). The data is there; the parameter just isn't threaded through.

## 3. Fix

Thread `drafts: list[DraftRow]` through two function signatures and use it in `_render_authoring_funnel`. No DS change, no new helpers, no schema change.

### 3.1 — `_render_metrics` gains a `drafts` parameter

[scripts/spec_lifecycle/render_dashboard.py:675](scripts/spec_lifecycle/render_dashboard.py:675). New signature:

```python
def _render_metrics(
    specs: list[SpecRow],
    drafts: list[DraftRow],
    now: dt.datetime,
) -> str:
```

Pass `drafts` through to `_render_authoring_funnel` at the call site inside `_render_metrics` body (search for `funnel_html = _render_authoring_funnel(` around line 826).

### 3.2 — `_render_authoring_funnel` reads current backlog from `drafts`

[scripts/spec_lifecycle/render_dashboard.py:1221](scripts/spec_lifecycle/render_dashboard.py:1221). New signature:

```python
def _render_authoring_funnel(
    specs: list[SpecRow],
    drafts: list[DraftRow],
    now: dt.datetime,
) -> str:
```

Replace [scripts/spec_lifecycle/render_dashboard.py:1257](scripts/spec_lifecycle/render_dashboard.py:1257) — `drafts_count = promoted_recent` — with:

```python
current_drafts = len(drafts)
drafts_count = current_drafts + promoted_recent
```

`current_drafts` counts every file the collector accepted under `specs/drafts/` (see [scripts/spec_lifecycle/render_dashboard.py:144-154](scripts/spec_lifecycle/render_dashboard.py:144) — the collector already filters out `README.md` and entries without frontmatter, so `len(drafts)` is the right number). The promoted-in-last-30d half (`promoted_recent`) keeps its existing meaning — counting drafts that *graduated* into queued specs within the window — and the two halves sum to a complete picture: backlog + throughput.

Update the funnel sub-line at [scripts/spec_lifecycle/render_dashboard.py:1309-1311](scripts/spec_lifecycle/render_dashboard.py:1309) (the `funnel_sub` string) so the prose matches the new count semantics. Current text reads `f"Last 30 days · {drafts_count} drafts promoted · {promo_pct}% reached queue · …"` — after the fix `drafts_count` no longer means "drafts promoted", so rephrase to something like `f"Last 30 days · {current_drafts} drafts in backlog + {promoted_recent} promoted · {promo_pct}% reached queue · …"`. Keep the same overall structure so the chart-card height doesn't shift.

### 3.3 — `promo_pct` recomputation

`promo_pct = int(round((queued_recent / drafts_count) * 100)) if drafts_count else 0` at [scripts/spec_lifecycle/render_dashboard.py:1307](scripts/spec_lifecycle/render_dashboard.py:1307). The denominator was implicitly `promoted_recent`; now it's `current_drafts + promoted_recent`. This is semantically correct — the conversion rate "% of drafts that reached queue" should compare queued to all drafts that *existed* in the window, not just to drafts that already converted. The new ratio reads lower for repos with high backlog (which is exactly what we want — large backlog means low conversion). Document the new semantics in a one-line code comment above the `promo_pct =` line.

### 3.4 — Empty-state branch

The empty-state guard at [scripts/spec_lifecycle/render_dashboard.py:1264](scripts/spec_lifecycle/render_dashboard.py:1264) — `if not any(c for _l, c, _t in stages_data)` — still works correctly with the new `drafts_count`. The guard fires only when *every* bucket is zero, which now requires zero current drafts AND zero promotions AND zero in-flight AND zero deployed in the last 30 days — still the right semantics for "no activity".

## 4. Regression-prevention test

New test in [tests/spec_lifecycle/test_render_dashboard_spec_0177.py](tests/spec_lifecycle/test_render_dashboard_spec_0177.py) (which already covers the funnel under spec 0177) or a sibling file.

- [ ] Test: `test_authoring_funnel_drafts_bucket_counts_current_backlog` — constructs `specs` with zero promoted-from-draft entries and `drafts` with three `DraftRow` instances; calls `_render_authoring_funnel(specs, drafts, now)`; asserts the rendered SVG contains `>3<` as the DRAFTS bucket count (the count text element from [scripts/spec_lifecycle/render_dashboard.py:1290-1292](scripts/spec_lifecycle/render_dashboard.py:1290)). Fails before the fix (would render `>0<`); passes after.
- [ ] Test: `test_authoring_funnel_drafts_bucket_sums_backlog_and_promotions` — constructs `specs` with two promoted-from-draft entries (`queued_at` inside the 30d window) AND `drafts` with three current draft files; asserts the rendered DRAFTS count is `5` (3 + 2). Locks the sum semantics so a future refactor that picks only one half regresses.

A bonus test for `promo_pct` recomputation:

- [ ] Test: `test_authoring_funnel_promo_pct_uses_new_denominator` — same fixture as above; asserts the rendered `funnel_sub` text reflects `queued_recent / (current_drafts + promoted_recent)` as a percentage, not the old `queued_recent / promoted_recent`.

## 5. Blast radius

- **Files touched.** [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py) — three functions (`render_index` body's call to `_render_metrics`, `_render_metrics` signature, `_render_authoring_funnel` signature + body). Total ~5 LOC delta excluding the test file.
- **Callers of `_render_metrics`.** Only the one call site at [scripts/spec_lifecycle/render_dashboard.py:2014](scripts/spec_lifecycle/render_dashboard.py:2014) inside `render_index`. No external callers (verified via grep — `_render_metrics` is private, prefix `_`).
- **Callers of `_render_authoring_funnel`.** Only `_render_metrics` itself. Verified via grep of the entire repo.
- **`DraftRow` shape.** The function only needs `len(drafts)`. No new field on `DraftRow`. The collector already populates it at [scripts/spec_lifecycle/render_dashboard.py:144-154](scripts/spec_lifecycle/render_dashboard.py:144).
- **No DS change.** No new CSS classes, no token changes, no `composed-components.css` / `components.css` edits.
- **No wire-format change.** `/api/data` payload is unchanged — the funnel is rendered server-side as static SVG, the bootstrap client just swaps the region in place.
- **Tests touched.** Any existing test that calls `_render_metrics(specs, now)` directly will fail to compile. Search [tests/spec_lifecycle/](tests/spec_lifecycle/) for `_render_metrics(` — the implementer updates each call site to pass `drafts=[]` (since the existing tests don't exercise the funnel branch).

## 6. Out of scope

- Reconciling "current drafts" with "drafts that were promoted" to avoid double-counting a draft that has both a file under `specs/drafts/` AND a `promoted_from_draft` reference. Per the spec workflow at [CLAUDE.md](CLAUDE.md) "Spec workflow" section, `/spec-promote` **deletes** the draft file when it lands the new dev spec — so a promoted draft has no file under `specs/drafts/` anymore. The two halves are disjoint by construction. No de-duplication needed.
- A separate "drafts opened this week" metric. Single-bucket fix only.
- A history view of drafts created over time. The funnel is a snapshot; trend lines are a different chart.

## 7. Risks

- **Stale draft files.** A draft file that was never promoted *and* never deleted (e.g. abandoned ideas) inflates the backlog count indefinitely. The risk is small in practice — drafts are short-lived (per the spec workflow they exist for days, not weeks) — but operationally the bucket can drift upward over months. Mitigation: out of scope for this fix; if it becomes painful, follow-up spec adds a per-draft `created_at` filter to `current_drafts` (count only drafts created in the last 30 days).
- **Test-fixture coverage.** Any test that constructs `_render_metrics` with a tiny `specs` list now also has to construct a `drafts` list (even if empty). Mitigation: pass `drafts=[]` explicitly at every existing test call site; new tests get a `DraftRow` factory.
- **Funnel sub-line readability.** The prose at [scripts/spec_lifecycle/render_dashboard.py:1309-1311](scripts/spec_lifecycle/render_dashboard.py:1309) gets one more clause. If the rendered card runs out of horizontal room on narrow viewports, the line wraps. The existing card uses a `chart-card__sub` style that already handles wrapping per [design-system/SPEC.md §2.1](design-system/SPEC.md) — no new CSS.
