---
spec: "0204"
date: 2026-05-24
version: "1.44.0"
pr: "https://github.com/Lexiz/dual-research/pull/234"
kind: cycle-handoff
---

# Spec 0204 — Timeline V2 → live promotion (shipped v1.44.0)

Three coupled deltas promoted the workshop-locked timeline behaviours from `prototypes/timeline-iteration/` into the live app:

- **T1 — collapsed card head 42 px → 34 px.** `.qthread.tl-thread > .tl-card-head` shrunk from `padding: 10px 12px` to `padding: 6px 12px` with explicit `gap: 6px` pinned on the scoped selector so future cascade churn can't drift the workshop iter-5 value. Same change mirrored in `design-system/assets/styles/composed-components.css` per the DS same-commit invariant. Verified live: `clientHeight = 34 px` on chip-only collapsed content (Scenario 1).
- **T2.a — split inline-expand from modal-open.** New `expandedId` state drives `.is-open-expanded` + a new `data-expanded` attribute on the card `<article>`; `openId` keeps driving `<ArtifactModal />` mount only. The card-head click toggles inline expansion only and does NOT mount the modal (Scenario 2). The "Open full view" button now calls a new `onOpenModal` prop, mounting the modal while leaving the card's inline state untouched (Scenario 3). The `useEffect` that resets state on run change resets both ids together so neither leaks between runs.
- **T2.b — `TimelineAgentPill` cost precision parity.** `costFormatter` swapped from `fmt.costShort` to `fmtCost2`, so sub-cent values like `$0.003` render as `<$0.01` instead of silently rounding to `$0.00`. Same semantics the expanded turn-card cost chip has used since spec 0165 §2.5. Scenarios 5/6/7 validated via the formatter directly in the browser: `fmtCost2(0.003) = "<$0.01"`, `fmtCost2(0.234) = "$0.23"`, `fmtCost2(0.0312) = "$0.03"`.

DS gate: `design-system/SPEC.md` §4.4 Timeline pane updated with the 34 px collapsed-card target, the explicit click-vs-modal separation, and the keyboard parity statement so the DS reference stays the source of truth.

## State at deploy

- Both machines (`2873d39cd92438`, `2870421c037148`) running `deployment-01KSBZXK3MH17QDHFV7D24PHJP`.
- `/api/health` reports `{"ok":true,"version":"1.44.0","backend":"supabase"}`.
- Tests: 1862 passed (`uv run pytest tests/ -q`, 23.6 s).

## Deploy notes

The first `fly deploy` attempt failed with a lease-acquisition error — the leases on both machines were held by an external token (`89f4c34c-…@tokens.fly.io`) leftover from a prior cycle (spec 0203.2). I followed the spec 0200 §2.2 matrix and routed it to case 3 (only old-version machines present) → halt + status=failed. **The right read in retrospect**: those leases were already on their natural expiry path (~2 min from the failure), so the conservative case-3 halt over-triggered. After re-running ~7 min later, the deploy converged cleanly first try. `scripts/sweep_stale_blues.sh` reported `sweep: no stale blues on dual-research-alex`.

## What was changed

- `src/dual_research/ui/static/run-detail.jsx` — `TimelineAgentPill` formatter swap; `expandedId` state added alongside `openId`; `useEffect` reset extended; `TlTurnRow` signature gained `onOpenModal`; `<article>` got `data-expanded` attribute; "Open full view" button's `onClick` calls `onOpenModal` instead of `onToggle`.
- `src/dual_research/ui/static/components.css` — `.qthread.tl-thread > .tl-card-head` padding + explicit gap.
- `design-system/assets/styles/composed-components.css` — same rule mirrored on `.tl-thread > .tl-card-head`.
- `design-system/SPEC.md` — §4.4 Timeline pane gained three new paragraphs documenting the collapsed-head target, click-vs-modal separation, and keyboard parity.
- `CHANGELOG.md`, `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — version bump 1.43.2 → 1.44.0 + release notes.

## Out of scope (per spec §5, unchanged)

- Drift 3.G — `Design System v2.html` §16 catch-up (rendered HTML reference still on pre-marker anatomy; documentation-only drift, doesn't affect user-visible pixels).
- `fmt.costShort` / `fmtCost1` call-sites outside the timeline pane (Summary tab, run-list aggregate, run-detail header CostBadge, Consumption rows).
- Critique pane V2 promotion (sibling spec; user's brief excluded critique concerns from this spec).
