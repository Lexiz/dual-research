# ItemCard reference screenshots

Reference baseline for the `design-system/SPEC.md` §4.1 ItemCard parity-verification rule (spec 0179). Each ItemCard-touching spec MUST embed a side-by-side image grid in its PR description comparing the four kinds × two states against these four references — see [spec 0205.1](../../../specs/0205.1-itemcard-parity-grid-refresh-and-retroactive-attachment.md) for the rule's enforcement history.

When the live-app ItemCard anatomy shifts (head structure, body stacking, chip glyphs, source-row shape), update the four PNGs **and** bump the row for the affected files below. The "last anatomy-shifting spec" column is the load-bearing one: future spec authors read it to decide whether the references still describe the current rendering or whether their own spec needs to refresh them first.

## Current baseline

| File | Captured | App version | Canonical run | Last anatomy-shifting spec |
|---|---|---|---|---|
| [`07-question-card-duplicate.png`](07-question-card-duplicate.png) | 2026-05-24 | 1.44.2 | `20260521-010637-dvs-backend-language-choice` (P4) | [spec 0205](../../../specs/0205-fix-p4-critique-card-five-visual-regressions.md) (Bug 1 SourceRow + Bug 3 link-variant glyph) |
| [`08-disagreement-card.png`](08-disagreement-card.png) | 2026-05-24 | 1.44.2 | `20260521-010637-dvs-backend-language-choice` (P4) | [spec 0205](../../../specs/0205-fix-p4-critique-card-five-visual-regressions.md) (Bug 1 SourceRow + Bug 3 link-variant glyph) |
| [`09-issue-card.png`](09-issue-card.png) | 2026-05-24 | 1.44.2 | `20260521-010637-dvs-backend-language-choice` (P4) | [spec 0205](../../../specs/0205-fix-p4-critique-card-five-visual-regressions.md) (Bug 1 SourceRow + Bug 2 lifecycle-leads body + Bug 3 link-variant glyph) |
| [`10-comments-card.png`](10-comments-card.png) | 2026-05-24 | 1.44.2 | `20260521-010637-dvs-backend-language-choice` (P4) | [spec 0205](../../../specs/0205-fix-p4-critique-card-five-visual-regressions.md) (Bug 1 SourceRow + Bug 2 lifecycle-leads body + Bug 3 link-variant glyph) |

App version read from `/api/health` at capture time. Capture mechanism: Playwright + system Chrome at 2400×1400 viewport, `device_scale_factor=2`, light theme, full-page screenshot cropped to each card's bounding box. The capture script lives at `/tmp/capture_itemcards.py` in the spec-0205.1 cycle's working tree — re-run from a fresh worktree against the current `dual-research-alex.fly.dev` build whenever this table needs refreshing.

## How to refresh

When a new spec changes ItemCard anatomy (head, body stacking, source-row shape, lifecycle structure, kind chip palette, or any `.item-card__*` CSS chrome), the same spec MUST:

1. Update the four PNGs above against the new anatomy. Use a canonical run with at least one item of each kind (Q / D / Issue / Comment).
2. Bump the relevant row(s) in the table above — `Captured` date, `App version`, and `Last anatomy-shifting spec` link.
3. Embed the standard 4-kinds × 2-states parity grid in the PR description (the rule at `design-system/SPEC.md` §4.1).

The four PNG filenames stay stable across refreshes so that older PR descriptions that embed the references by path still resolve to current images.

## Documented departures from the references

This footnote is mirrored in `design-system/SPEC.md` §4.1. When the live-app ItemCard anatomy intentionally departs from the rendering captured here, name the departure in BOTH places:

- **Lifecycle leads Issue + Comment expanded bodies** (spec 0205 Bug 2). Pre-0205 references showed a standalone `<Markdown text={item.body}/>` block above `ItemCardLifecycleSection`. Post-0205 the standalone block is gone — the lifecycle section's raise-row already carries `item.body` as its quote. The four PNGs above were re-captured post-0205 and now reflect lifecycle-first stacking; no departure to track.
- **Expanded `SourceRow` renders excerpt as `<blockquote>` with brand-toned left border, not `<pre>`** (spec 0205 Bug 1). URL · FETCHED · SEARCH QUERY render as `(t-overline label) · value` grid rows instead of inline spans. The four PNGs above reflect the new shape — no departure to track.
- **`mdi:link-variant` glyph on head Sources chip AND `.item-card__sources-hd` segment header** (spec 0205 Bug 3). One canonical sources glyph across both surfaces. The four PNGs above show the new glyph — no departure to track.
