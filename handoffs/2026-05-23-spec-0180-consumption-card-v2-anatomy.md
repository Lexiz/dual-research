---
spec: "0180"
date: 2026-05-23
version: "1.36.3"
pr: "https://github.com/Lexiz/dual-research/pull/210"
---

# Spec 0180 — Consumption card V2 anatomy — handoff

## What landed

V1 → V2 anatomy on every Consumption tab card. Per Notion bug-batch Issues 12 + 13.

- **Two stacked bars** at the top of every card, both visible in collapsed state: `Total input` (`ccx-bar-row--total-input`) and `Total output` (`ccx-bar-row--total-output`). Both share a single denominator (per-card-pair scale) so the input-vs-output visual comparison is meaningful. The combined `is-total` `Total tokens` bar from spec 0118 is gone.
- **Header gains `.hd-totals` slot** — total tokens · total cost right-aligned at the bar-fill column's right edge, between the provider name and the bracketed `(% of context)`. `.ccx-header` is now a 4-column grid (`hd-id · 1fr filler with hd-totals right-aligned · stats · chev`).
- **Output totals block added** (`.ccx-totals.ccx-totals--output`) — parallel to the existing input totals. Carries `output tokens · output cost · cache savings · total output`.
- **Cache-savings line relocated** from input totals to output totals (Issue 13 — V1 / spec 0148 D12 placed it on the input side, the V2 placement is the output side as a cost-savings annotation). The line is moved, not removed; rendering logic + copy + per-card data path are unchanged.
- **Collapsed mono cache-reuse line dropped** (the spec 0051 retained-from-collapsed `mono` text under the bar). The output totals block carries the canonical surface now.
- **Output header bar removed** from the unfolded body. The always-visible total-output bar replaces it; the IIFE's `outputHeader` element is gone. Per-output sub-rows (`Reasoning` · `Response` · `Tool calls`) still render in the unfolded body when split data exists.
- **Inline grid styling lifted** from per-render-site `style={{...}}` blobs onto the `.ccx-bar-row` class. Grid template is now `minmax(140px, 28%) 1fr minmax(110px, max-content)` — same as the inline overrides but applied once.
- **DS-side parity**: modifier classes land in both `src/dual_research/ui/static/components.css` and `design-system/assets/styles/composed-components.css` (CLAUDE.md two-place rule). `design-system/SPEC.md` §4.3 rewritten to codify the V2 anatomy. `design-system/assets/Design System v2.html` Consumption section re-rendered to match.
- **Regression test added** at `tests/test_consumption_card_v2.py` — 6 invariants: no combined `is-total` bar, both `--total-*` modifiers present, `--output` totals modifier present, cache-savings positioned in output totals, no inline grid template on `.ccx-bar-row` JSX elements.

## Resolved data question

Spec §3.6 flagged: "does the wire format split web-search cost into input-side vs output-side?" Read of `usage` shape on the anchor run confirms **no** — `usage.searches` / `usage.searchCost` is a single combined number. The implementation surfaces the web-search line **only in the input totals block** (the existing location); it is NOT duplicated on the output side. Rationale: the line is already visible in input totals; duplication on output would add visual noise without accounting precision. If a future spec lands separate `output_search_*` fields on the wire, surfacing them in the output totals block is a one-line change.

## Verify

Live: <https://dual-research-alex.fly.dev/#/runs/20260521-010637-dvs-backend-language-choice> → Consumption tab.

- Every collapsed card shows two stacked bars (`Total input` + `Total output`) plus the header total tokens · total cost cluster.
- Expand any card with cache reuse — the `cache savings · ×N reuse on Xkt` line appears in the output totals block at the bottom, not in the input totals.
- The reuse-stripe overlay applies only to the input bar.

## Deploy notes

- `fly deploy` clean, both machines (`18530d9c0d9178`, `e823e05c570958`) green; old blue machines (`185516dc3e3d08`, `8e2541f763d748`) destroyed.
- `scripts/sweep_stale_blues.sh`: `sweep: no stale blues on dual-research-alex`.
- Smoke: `https://dual-research-alex.fly.dev/run-detail.jsx` carries all three new selector hooks (`ccx-bar-row--total-input`, `ccx-bar-row--total-output`, `ccx-totals--output`).

## Tests

`uv run pytest tests/ -q` — 1649 passed in 19.68s. Includes the 6 new `test_consumption_card_v2.py` assertions.
