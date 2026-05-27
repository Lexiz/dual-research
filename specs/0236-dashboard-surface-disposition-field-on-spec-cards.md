---
kind: dev
spec: "0236"
slug: dashboard-surface-disposition-field-on-spec-cards
title: "Spec dashboard renders the `disposition` field on each spec card so backfilled-as-`archive` carve-outs are visually distinguishable from `disposition: ship` queue heads"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: deferred
depends_on: ["0229.1"]
complexity: S
created: 2026-05-27
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: "deferred-from-0229.1"
promoted_from_draft: ""
disposition: defer
disposition_reason: "Dashboard surfacing is a UX improvement on top of the operational lever (the queue-head filter); the lever is what determines `/dev-next` behaviour, and shipping the surface without a queue-head consumer would invert the dependency order."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0236 — Dashboard surfaces `disposition` on each spec card

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** 0229.1 (the disposition field this surfaces)
> **Bump:** MINOR — observable new UI element on every spec card; no schema or backend change.
> **Evidence:** Spec 0229.1 §7 R3 named the surfacing gap; the handoff at [`handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:34`](handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:34) repeats it: *"The renderer at [`scripts/spec_lifecycle/render_dashboard.py`](scripts/spec_lifecycle/render_dashboard.py) doesn't currently read or render the field. Surfacing it (as a column, a filter, or a per-card chip) is a separate UI spec."*

---

## 1. Context

The spec dashboard at `https://lexiz.github.io/dual-research/` shows one card per spec under several lifecycle buckets (Queue, In-flight, Recently-merged, Archive). Spec frontmatter is the data source — `kind`, `type`, `status`, `target_version`, `complexity`, etc. are surfaced as chips, labels, or counts.

Spec 0229.1 introduced `disposition: {ship, defer, archive}` and `disposition_reason: <one sentence>` on every spec. The renderer at [`scripts/spec_lifecycle/render_dashboard.py`](scripts/spec_lifecycle/render_dashboard.py) does not currently read either field, so 235 backfilled-as-`archive` specs visually look identical to the few specs with `disposition: ship` that have shipped under the convention. For an operator scanning the queue, this means the queue-head filter (when spec 0237 or equivalent lands the `/dev-next` change to filter on `disposition: ship`) won't be visible in the dashboard — they'll have to grep frontmatter to see which specs `/dev-next` will actually pick.

The dashboard's existing chip system already supports per-card metadata pills — for example, the `complexity: S/M/L` chip renders at [`scripts/spec_lifecycle/render_dashboard.py`](scripts/spec_lifecycle/render_dashboard.py) and follows a consistent pattern. The disposition chip slots in naturally.

## 2. Proposed change

### 2.1 — Render a `disposition` chip on every spec card

In [`scripts/spec_lifecycle/render_dashboard.py`](scripts/spec_lifecycle/render_dashboard.py), the function that renders each spec card consults the frontmatter dict. Add a one-line chip render for `fm.get("disposition")`:

- `disposition: ship` → green chip labelled `ship`, indicating queue-head eligibility.
- `disposition: defer` → amber chip labelled `defer`, indicating recorded-but-not-actionable.
- `disposition: archive` → muted chip labelled `archive`, indicating informational-only.
- field missing → no chip (renderer treats absence as legacy / pre-backfill).

The chip uses the existing chip CSS class vocabulary in [`design-system/SPEC.md`](design-system/SPEC.md) (per CLAUDE.md DS gate: "tokens only for color"). Concretely the three states map to:

- `ship` → `--p-success` family (the same family used for the merged-status chip).
- `defer` → `--p-warning` family (or the existing amber chip if one exists).
- `archive` → `--p-neutral-muted` family.

Hover on the chip shows `disposition_reason` verbatim (truncated to 120 chars in the tooltip if longer; the full text stays in the spec file).

### 2.2 — Filter bar adds a `disposition` facet

The dashboard already has a filter bar (type, status, complexity). Add a `disposition` facet with three checkboxes — `ship`, `defer`, `archive` — defaulting to all checked. Operators who want to see only the actionable queue can uncheck `defer` and `archive` and see the `/dev-next`-eligible cohort.

The filter logic lives client-side in the dashboard's JS; the renderer just emits the field as a `data-disposition="<value>"` attribute on each card element. The filter UI uses the same pattern as the existing type/status filters.

### 2.3 — Backwards compatibility

Specs without a `disposition` field — historical merged or archived specs that aren't covered by spec 0229.1's backfill (e.g. anything under `specs/archive/`) — render with no chip and pass the filter (the absence-of-field is treated as "show by default"). This avoids hiding the historical record from operator view.

The renderer at [`scripts/spec_lifecycle/render_dashboard.py:1539`](scripts/spec_lifecycle/render_dashboard.py:1539) already documents the exclusion logic for `_templates/` and similar non-spec files; the new chip logic respects the same exclusion list.

## 3. User stories & acceptance criteria

### 3.1 — User stories

> As a **dev** running `/dev-queue-run`, I want to see at a glance which queued specs will actually be picked by `/dev-next`, so that I can predict the next ~5 cycles without reading frontmatter files.

> As an **admin** triaging carve-outs, I want to filter the dashboard to `disposition: ship` only, so that I see exactly the actionable queue head without `archive`-class noise.

### 3.2 — Acceptance scenarios (BDD)

> **Scenario 1:** `disposition chip renders on every queued card`
> GIVEN the dashboard renders the queue bucket with a spec carrying `disposition: ship` in frontmatter
> WHEN I view the card for that spec
> THEN a chip with text `ship` and class `chip-success` is present in the card DOM

> **Scenario 2:** `filter bar hides defer-class specs`
> GIVEN the queue contains specs of all three disposition values
> WHEN I uncheck the `defer` and `archive` boxes in the disposition filter
> THEN only cards with `data-disposition="ship"` remain visible; the dashboard shows the queue-head-actionable cohort only

## 4. Data / Schema deltas

No schema change. Spec frontmatter already carries `disposition` post-spec-0229.1. The renderer just reads two fields it previously ignored.

## 5. Out of scope

- **Changing the queue-head filter semantics in `/dev-next`.** This spec is a visualisation. The actual filter on `disposition: ship` is a separate change to the out-of-repo `/dev-next` SKILL.md (the parallel deferred item from the 0229.1 handoff).
- **Persisting filter state across page loads.** Filter selections reset on reload. A persistent-filter feature is a future dashboard polish spec.
- **Surfacing `disposition_reason` in the main card body.** The tooltip on hover is the right surface for the reason text; embedding it inline would clutter cards that today are dense with chips already.
- **Backfilling `disposition` on archived specs under `specs/archive/`.** Spec 0229.1 §5 explicitly deferred archived specs; this spec inherits that scope.

## 6. Test plan

- [ ] **Unit — chip render maps `disposition: ship` to the success-class chip.** New test in [`tests/spec_lifecycle/test_dashboard_disposition_chip.py`](tests/spec_lifecycle/test_dashboard_disposition_chip.py) (new file) renders the dashboard HTML for a synthetic spec with `disposition: ship` and asserts the output contains `<span class="chip-success">ship</span>` (or whatever the exact CSS class is once §2.1's DS lookup resolves).
- [ ] **Unit — chip render maps `disposition: archive` to the neutral-muted chip.** Same synthetic-spec pattern, asserts the muted chip class.
- [ ] **Unit — chip absent when `disposition` key is missing.** A synthetic spec lacking the field renders no chip; assert the chip element type is not present in the card output.
- [ ] **Source-pattern test — renderer reads `disposition` field.** Positive regex against `scripts/spec_lifecycle/render_dashboard.py`: `fm\.get\("disposition"\)`; antipodal-absence regex: no path where the disposition chip is unconditionally wrapped in `if False:` or guarded out.
- [ ] **Filter bar emits `data-disposition` attribute.** Render a card with `disposition: defer` and assert the output card HTML contains `data-disposition="defer"`.
- [ ] **In-repo invariant — every existing in-repo spec's frontmatter has `disposition` post-spec-0229.1.** Walks `specs/*.md` (excluding archive + templates), asserts each has the key. (This duplicates spec 0229.1's invariant; intentional belt-and-braces.)

## 7. Risks

- **R1 — DS chip class for `defer` / `amber` doesn't currently exist in [`design-system/SPEC.md`](design-system/SPEC.md).** *Mitigation:* check the DS spec first; if no amber-family chip exists, ship a new one in the same commit (chip class added in both `design-system/assets/styles/composed-components.css` AND `src/dual_research/ui/static/components.css` per the CLAUDE.md two-files-one-commit rule).
- **R2 — Dashboard tests rely on snapshot HTML and could fail noisily on the new chip output.** *Mitigation:* the snapshot tests in [`tests/spec_lifecycle/`](tests/spec_lifecycle/) update naturally — the new chip is additive, not a restructure. Any failing snapshot is regenerated with the chip output and reviewed.
- **R3 — Filter UI adds DOM complexity to an already-dense filter bar.** *Mitigation:* the new disposition filter follows the existing complexity / type / status pattern exactly. No new UX paradigm introduced. If the bar becomes visually crowded, that's a follow-up polish spec, not a blocker for shipping the data.
