---
spec: "0167"
date: 2026-05-22
version: 1.28.0
pr: https://github.com/Lexiz/dual-research/pull/190
---

# Spec 0167 — Critique pane bar2 + bar1 + DS catch-up

v1.28.0 ships four locked critique-pane chrome changes (§2.3 / §2.4 / §2.5 / §2.6) and a DS catch-up. Two larger items from the spec — §2.1 class rename and §2.2 per-segment count plumbing — are deferred with documented reasoning.

## What landed

- **§2.3 Bar-1 `.crit-drift-pill` — unconditional render + muted-at-zero.** [src/dual_research/ui/static/run-detail.jsx](src/dual_research/ui/static/run-detail.jsx) drops the `runWideDrift > 0 &&` guard; the slot renders unconditionally carrying `data-count={runWideDrift}`. New CSS rule `.crit-drift-pill[data-count="0"]` mutes background, color, and opacity to 0.55 so the bar-1 right cluster doesn't reflow if drift appears mid-run.
- **§2.5 / §2.6 Kind-cluster order Q · D · I · C, "All" dropped.** [run-detail.jsx:7176](src/dual_research/ui/static/run-detail.jsx) `<TabGroup variant="kind-tabs">` reordered. The leading "All" `<Tab>` is gone — no active chip = "show all". Clicking an active kind chip now toggles `kindFilter` back to `'all'` (deselect).
- **§2.4 Phase-tab DS catch-up.** [design-system/assets/Design System v2.html](design-system/assets/Design System v2.html) §12 (state A) gets the missing `P0 Brief` tab. Live has rendered four phase tabs since spec 0136; DS reference was stuck on the spec-0098 three-tab set.
- **DS catch-up.** [design-system/SPEC.md](design-system/SPEC.md) §4.1 rewritten to document the four-tab phase set, the always-rendered drift slot with muted-at-zero variant, the locked kind-cluster order Q · D · I · C, the dropped "All" chip, and the `.fgroup` ↔ `.tab-group-solid` naming reality (live uses `.fgroup`; DS canonical uses `.tab-group-solid` — same lifted-tile contract).
- **DS canonical CSS.** [design-system/assets/styles/composed-components.css](design-system/assets/styles/composed-components.css) `.drift-chip` selector now also covers `.crit-drift-pill[data-count="0"]` via grouped selector, documenting the cross-name muted-at-zero contract.

## Notes on deferrals

- **§2.1 class rename `.fgroup` → `.tab-group-solid` — deferred.** The existing `.fgroup .ft.is-active` rule at [components.css:2275](src/dual_research/ui/static/components.css) already produces the spec's lifted-tile active state (`background: var(--md-surface); color: var(--md-on-surface); box-shadow: var(--md-elev-1)`) — visually identical to what the spec proposes for `.tab-group-solid .tab-solid[data-active="true"]`. Renaming would be pure code-organisation churn with zero user-visible delta. Tracked in CHANGELOG as deferral; if/when the DS canonical fully adopts `.tab-group-solid` consistently across all surfaces, a follow-up spec can do the live JSX rename.
- **§2.2 per-segment count plumbing — deferred.** The agent and status filter buttons in `.fgroup` currently don't show counts. Adding `(N)` for each option requires computing `agentCounts.{all,claude,gpt}` and `statusCounts.{all,open,resolved,drift}` against the active phase + plumbing them into JSX. Substantial enough to warrant its own spec — not blocking the other §2.3 / §2.4 / §2.5 / §2.6 items.

## Tests

- `uv run pytest tests/ -q` — **1532 passed in 19.46s**.
- `npm test` (vitest, happy-dom) — **9 passed (9)**.
- Live-push end-to-end: every branch-phase event landed on `origin/main` as its own commit.

## Deploy notes

- **Clean deploy on first attempt.** No Fly lease errors this round. The lease-table bug pattern has been intermittent — 6 deploys in a row hit it (0160–0166), then 0167 came through clean. Worth noting for the upstream report.
- Final cluster: 2 machines on v1.28.0. Sweep: `no stale blues`.
- `/api/health` → `{"ok":true,"version":"1.28.0","backend":"supabase"}` immediately on first hit.

## Open follow-ups

- §2.1 + §2.2 (above).
- The DS HTML §12 state B and state C blocks weren't updated this cycle — only state A. They still show three phase tabs (P2 / P4 / Σ) and the old kind-cluster order. Cleanup spec.
- Cross-pane chip rename inconsistency — live `.crit-drift-pill` vs DS `.drift-chip`. CSS rule covers both via grouped selector; eventual rename would unify.

## What's intentionally still rough

- Title attribute on `.crit-drift-pill` when `data-count="0"` says "No items with ledger drift" rather than "0 items with ledger drift". Subjective choice for the screen-reader / hover surface.
- Kind cluster's "click active to deselect" behaviour is wired in this spec but not visually telegraphed. A future cycle could add a subtle "active + hover" state that previews the deselect.
