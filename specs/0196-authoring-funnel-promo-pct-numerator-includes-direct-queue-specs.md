---
kind: dev
spec: "0196"
slug: authoring-funnel-promo-pct-numerator-includes-direct-queue-specs
title: "Fix: authoring funnel `promo_pct` numerator counts all queued specs, blows past 100% when most specs skip the draft step"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 7
depends_on: []
complexity: S
created: 2026-05-23
queued_at: "2026-05-23T12:01:06Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: deferred-from-0183
promoted_from_draft: ""
---

# Spec 0196 — Fix: authoring funnel `promo_pct` numerator counts all queued specs, blows past 100% when most specs skip the draft step

> **Type:** bug  |  **Severity:** P2  |  **Affects:** spec dashboard Metrics tab → §2.4.7 authoring funnel sub-line (`X% reached queue`).
> **Bump:** PATCH — one-line change to the numerator of `promo_pct` plus a fixture-value update in the regression test.
> **Evidence:** Spec 0183 handoff `## Deferred during implementation` first (and only) bullet — [handoffs/2026-05-23-spec-0183-authoring-funnel-drafts-count-includes-current-backlog.md:34](handoffs/2026-05-23-spec-0183-authoring-funnel-drafts-count-includes-current-backlog.md:34). Live render observed: `Last 30 days · 0 drafts in backlog + 8 promoted · 538% reached queue · 84% of queued shipped` — the 538% is mathematically impossible if "reached queue" is a conversion rate.

---

## 1. Reproduction

**Environment:** any dashboard render against a repo whose `specs/` directory contains queued/merged specs that did **not** come through the draft funnel (i.e. specs authored via `/spec-queue` directly from a conversation, so `promoted_from_draft` is empty in their frontmatter).

**Steps:**

1. Author N specs in the last 30 days, all via `/spec-queue` (no draft step). They land with `promoted_from_draft: ""`.
2. Author M specs in the same window via `/spec-draft` + `/spec-promote`. They land with `promoted_from_draft: "<id>"` populated.
3. Run `uv run python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out /tmp/dash` (or load the live dashboard) and navigate to the Metrics tab.
4. Locate the authoring funnel SVG and read the sub-line text.

**Expected:** The "`Z% reached queue`" clause is a conversion rate over the draft funnel — i.e. `promoted_recent / (current_drafts + promoted_recent)`. It is bounded in `[0, 100]` by construction and reads "of the drafts that existed in this window, what fraction graduated into queued specs". With N=8 direct-queue specs, M=0 promoted, and 0 current drafts, the funnel has no draft inputs and the sub-line should fall through to the empty-state prose at [scripts/spec_lifecycle/render_dashboard.py:1330](scripts/spec_lifecycle/render_dashboard.py:1330) (`Last 30 days · {queued_recent} queued · {deployed_recent} shipped`). With M>0 promoted and zero backlog, it should read `100% reached queue` (every draft that existed converted).

**Actual:** The clause uses `queued_recent` (every spec with status `queued` in the window, including direct-queue specs) as the numerator and `current_drafts + promoted_recent` as the denominator — a mongrel ratio of two unrelated populations. Live render: `Last 30 days · 0 drafts in backlog + 8 promoted · 538% reached queue · 84% of queued shipped` (538% = 43 queued_recent ÷ 8 promoted_recent, give or take). Once the numerator exceeds the denominator the metric becomes nonsense, and it does so whenever the repo's queueing pattern is direct-from-conversation (which is the dominant pattern in this repo).

## 2. Root cause hypothesis

[scripts/spec_lifecycle/render_dashboard.py:1324](scripts/spec_lifecycle/render_dashboard.py:1324) — `promo_pct = int(round((queued_recent / drafts_count) * 100)) if drafts_count else 0`. The numerator should describe the same population as the denominator: `current_drafts + promoted_recent` is "drafts that existed in the window", so the numerator must be "drafts that graduated", which is `promoted_recent` (specs whose `promoted_from_draft` frontmatter is set and whose `queued_at` is within the window — see [scripts/spec_lifecycle/render_dashboard.py:1238-1245](scripts/spec_lifecycle/render_dashboard.py:1238)).

Why the wrong numerator slipped through: spec 0183 §3.3 literally said "the denominator was implicitly `promoted_recent`; now it's `current_drafts + promoted_recent`" without revisiting the numerator. The pre-0183 code had `queued_recent / promoted_recent` — the same shape, just with a smaller-yet-still-wrong denominator that hid the unbounded behavior on smaller fixtures (and made the bug invisible until the live repo accumulated 8 promotions against 43 queued). Spec 0183 inherited the numerator without re-deriving it from the metric's prose definition.

The fix is one symbol change. `queued_recent` → `promoted_recent`. Everything else — the denominator, the prose, the empty-state guard, the rendered HTML — already lines up with the corrected semantics.

## 3. Fix

### 3.1 — `promo_pct` numerator switches to `promoted_recent`

[scripts/spec_lifecycle/render_dashboard.py:1324](scripts/spec_lifecycle/render_dashboard.py:1324). Current line:

```python
promo_pct = int(round((queued_recent / drafts_count) * 100)) if drafts_count else 0
```

New line:

```python
promo_pct = int(round((promoted_recent / drafts_count) * 100)) if drafts_count else 0
```

`promoted_recent` and `drafts_count` are already in scope from [scripts/spec_lifecycle/render_dashboard.py:1238](scripts/spec_lifecycle/render_dashboard.py:1238) and [scripts/spec_lifecycle/render_dashboard.py:1271](scripts/spec_lifecycle/render_dashboard.py:1271) respectively. No new variables, no new helpers, no signature changes.

### 3.2 — Update the spec-0183 comment to match the corrected semantics

[scripts/spec_lifecycle/render_dashboard.py:1321-1323](scripts/spec_lifecycle/render_dashboard.py:1321) — the three-line comment above the `promo_pct =` line was written for the old (wrong) numerator. Rewrite it to one or two lines reflecting the corrected metric: "% of drafts that existed in this window which graduated into queued specs (`promoted_recent / (current_drafts + promoted_recent)`). Direct-queue specs are excluded — they never entered the draft funnel."

### 3.3 — `ship_pct` is unaffected

[scripts/spec_lifecycle/render_dashboard.py:1325](scripts/spec_lifecycle/render_dashboard.py:1325) — `ship_pct = int(round((deployed_recent / queued_recent) * 100)) if queued_recent else 0`. This metric correctly describes "% of queued specs that shipped" — both terms are queue-level, not draft-level. No change.

### 3.4 — Sub-line prose stays the same

[scripts/spec_lifecycle/render_dashboard.py:1326-1331](scripts/spec_lifecycle/render_dashboard.py:1326) — the prose `f"Last 30 days · {current_drafts} drafts in backlog + {promoted_recent} promoted · {promo_pct}% reached queue · {ship_pct}% of queued shipped"` reads correctly once `promo_pct` is bounded. No edit. The empty-state fall-through at [scripts/spec_lifecycle/render_dashboard.py:1330](scripts/spec_lifecycle/render_dashboard.py:1330) is unchanged.

## 4. Regression-prevention test

Update one existing assertion in [tests/spec_lifecycle/test_render_dashboard_spec_0183.py:83-100](tests/spec_lifecycle/test_render_dashboard_spec_0183.py:83) and add one new test in the same file.

- [ ] Update `test_authoring_funnel_promo_pct_uses_new_denominator` at [tests/spec_lifecycle/test_render_dashboard_spec_0183.py:83](tests/spec_lifecycle/test_render_dashboard_spec_0183.py:83) — the fixture has 2 current drafts + 2 recent promotions = 4 total in window. The old assertion expected `50% reached queue` (which was `queued_recent=2 / drafts_count=4`, coincidentally matching `promoted_recent / drafts_count` because all promoted specs were also queued). After the fix the math becomes `promoted_recent=2 / drafts_count=4 = 50%` — the same number for this fixture. Add a second, sharper fixture: 0 current drafts + 1 promoted spec + 3 direct-queue specs (status `queued`, `promoted_from_draft: ""`); assert `100% reached queue` (because 1 promoted ÷ 1 total-draft = 100%) — pre-fix this fixture produced `400% reached queue` (4 queued ÷ 1 total-draft).
- [ ] New test: `test_authoring_funnel_promo_pct_excludes_direct_queue_specs` — constructs `specs` with 5 direct-queue specs (status `queued`, `promoted_from_draft` empty, `queued_at` in window) AND 1 promoted spec AND `drafts` with 1 current draft. Assert the rendered sub-line contains `50% reached queue` (1 promoted ÷ (1 backlog + 1 promoted) = 50%). The 5 direct-queue specs must NOT pull the numerator up. Fails before the fix (would render `300% reached queue` = 6 queued ÷ 2 total-draft); passes after.

## 5. Blast radius

- **Files touched.** [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py) — one line of code, two lines of comment. [tests/spec_lifecycle/test_render_dashboard_spec_0183.py](tests/spec_lifecycle/test_render_dashboard_spec_0183.py) — one test updated, one test added. Total ~10 LOC delta.
- **Callers of the modified expression.** None — `promo_pct` is a local variable inside `_render_authoring_funnel`. Used in two adjacent f-strings ([scripts/spec_lifecycle/render_dashboard.py:1327-1329](scripts/spec_lifecycle/render_dashboard.py:1327)) and nowhere else.
- **`queued_recent` is still in scope.** It's used by `ship_pct` on the next line — no dead-code cleanup needed.
- **No DS change.** The funnel SVG geometry is unchanged. No CSS, no token, no `composed-components.css` / `components.css` edits.
- **No wire-format change.** `/api/data` payload unaffected; funnel is server-rendered.
- **No schema change.** No `SpecRow` / `DraftRow` field additions.
- **Other tests in the file.** `test_authoring_funnel_drafts_bucket_counts_current_backlog`, `test_authoring_funnel_drafts_bucket_sums_backlog_and_promotions`, `test_authoring_funnel_no_double_counting`, `test_authoring_funnel_empty_state_when_no_activity` — none of these read `promo_pct` from the rendered HTML, so they're unaffected.

## 6. Out of scope

- A dashboard breakdown of "direct-queue vs promoted" spec authoring — a useful metric, but a different chart. The funnel is the draft-pipeline view; a separate "spec sourcing" chart belongs in its own spec.
- Re-naming `queued_recent` to `queued_total_recent` to disambiguate from the now-narrower `promoted_recent` numerator. The variable name is fine in context; renames bloat the diff.
- Backfilling `promoted_from_draft` on historical specs that arguably came from a conversation that took place before the spec workflow existed. The frontmatter is the source of truth as-is.
- Reconsidering the 30-day window. Same window for both halves; no change.

## 7. Risks

- **Lower headline number on the live dashboard.** After the fix, the repo's funnel sub-line will read something like `100% reached queue` (typical for the current state where backlog is small) or `0% reached queue` if all drafts are unpromoted. Either is mathematically correct — the metric is now bounded. Risk is purely cosmetic: a viewer accustomed to the inflated number may briefly think "did something break?" Mitigation: handoff prose calls out the change explicitly so the next dashboard check isn't confusing.
- **Empty-state visibility for direct-queue-heavy repos.** A repo that authors specs exclusively via `/spec-queue` (no drafts ever) will see `0% reached queue` with `0 drafts in backlog + 0 promoted` — which falls through to the empty-state prose at [scripts/spec_lifecycle/render_dashboard.py:1330](scripts/spec_lifecycle/render_dashboard.py:1330) (`Last 30 days · {queued_recent} queued · {deployed_recent} shipped`). This is the correct rendering for "no draft activity" and was already the design after spec 0183. No new risk; just confirming the fall-through still triggers.
- **Test fixture coupling.** The updated `test_authoring_funnel_promo_pct_uses_new_denominator` keeps its `50% reached queue` assertion because the old and new math happen to coincide on its fixture. The added second test (`test_authoring_funnel_promo_pct_excludes_direct_queue_specs`) is the one that actually catches the regression. Make sure both land in the same commit so the locking semantics are explicit.
