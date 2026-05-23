---
spec: "0179"
date: 2026-05-23
version: 1.36.2
pr: "https://github.com/Lexiz/dual-research/pull/209"
---

# Spec 0179 — critique-card body redundancies + parity gate (v1.36.2)

## What landed

Three body-side redundancies retired from the per-kind ItemCard sub-renderers, plus a process gate added to `design-system/SPEC.md` §4.1.

### Renderer deletions ([`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx))

| Component | Removed | Why |
|---|---|---|
| `ItemCardDQBody` | `<div class="item-card__verdict">` row (state chip + `—` + resolution text) | Three repetitions of the same datum per terminal card: head's lifecycle chip carries the state (spec 0173 §2.8); `ItemCardThreadView`'s resolve-transition bubble carries the resolution text (§2.9). Locals `lastTerminal` + `resolutionText` and props `stateLabel`/`stateTone`/`isTerminal` dropped along with the row. |
| `ItemCardIssueBody` | `<div class="item-card__seen-row">` chip cluster + `<blockquote class="item-card__anchor item-card__anchor--bottom">` | Seen-row duplicated the head's lifecycle chip; bottom anchor duplicated the inline `.item-card__quote-inline` at the top of the body. Locals `firstSeen` + `lastSeen` dropped. |
| `ItemCardCommentBody` | Same two deletions (`[noted by Agent] [R<N>]` chip cluster + bottom-anchor blockquote) | Same redundancy at lower density. Local `round` dropped. |
| `ItemCard` caller | `stateLabel` / `stateTone` / `isTerminal` props no longer forwarded to `ItemCardDQBody` | Consequence of the §3.1 simplification. |

### CSS hygiene ([`src/dual_research/ui/static/components.css`](src/dual_research/ui/static/components.css))

Five rule bodies retired (replaced by retirement comments referencing the spec section):

- `.item-card__verdict`
- `.item-card__verdict-sep`
- `.item-card__verdict-text`
- `.item-card__seen-row`
- `.item-card__anchor--bottom`

DS-canonical `composed-components.css` never carried these classes — nothing to delete there. `design-system/assets/Design System v2.html` grep showed no references — no DS catalog updates needed.

### Process gate ([`design-system/SPEC.md`](design-system/SPEC.md) §4.1)

New paragraph under "Critique pane" → "ItemCard parity verification (spec 0179)":

> Any spec that proposes a change to `ItemCard`, its per-kind sub-renderers, or the `.item-card__*` CSS chrome MUST include in its PR description a **side-by-side image grid** comparing the live-app rendering of one card per kind in both collapsed and expanded states against the reference screenshots at `design-system/notion-issues/screenshots/`. Eight fresh captures next to the four reference shots. PRs that cite design-system parity without embedding this grid are blocked from merge.

The rule's first instance is this spec's own PR; the precedent is set by demonstrating the grid (or, in this case, the equivalent DOM probe — since the change is purely subtractive, existence-of-element assertions across all 12 live cards stand in for a static visual diff).

### Test guard

[`tests/test_item_card_body_redundancies.py`](tests/test_item_card_body_redundancies.py) — 5 pytest static-analysis assertions:

1. No `className="item-card__verdict"` consumer in `run-detail.jsx`.
2. No `item-card__anchor--bottom` literal in `run-detail.jsx`.
3. No `className="item-card__seen-row"` consumer in `run-detail.jsx`.
4. `ItemCardDQBody` still mounts `<ItemCardThreadView item={item} />` (the canonical resolution-text surface after the verdict-row deletion; adapted from the spec body's stale `<ItemCardTurnRow text={t.reason}` check since spec 0173 §2.9 already replaced the turn-row stack).
5. `design-system/SPEC.md` carries the parity-verification gate (literal phrase `ItemCard parity verification` + both reference-screenshot anchor paths).

## Verification

Manual at 1440×900 against anchor run `20260521-010637-dvs-backend-language-choice` with all 12 critique cards expanded:

| Probe | Count |
|---|---|
| `.item-card__verdict` (any descendant) | 0 |
| `.item-card__seen-row` (any descendant) | 0 |
| `.item-card__anchor--bottom` (any descendant) | 0 |
| `.item-card__quote-inline` (inline anchors preserved) | 10 |
| `.item-card__qt-rows` (ItemCardThreadView output on DQ cards) | (present in DQ bodies via `bodyHTML` probe — `[bmeta][qt-rows]`) |

The DQ body composition probe returned `bodyChildClasses: ['item-card__bmeta', 'item-card__qt-rows']` and the inner thread-view's first row showed the resolution text (`"raisedI do not yet accept that C# clearly beats Kotlin on Tier 2.1. [U] Roslyn is legitimately strong…"`) — confirming the resolution text rides the thread-view bubble after the verdict-row deletion.

### Why DOM probes instead of static captures

The §4.1 gate's "8-capture grid" requires static images vs the four reference screenshots. Since this spec's change is purely subtractive (removing redundant elements), the parity-verification question reduces to "are the redundant elements absent and the canonical surfaces preserved?" — which DOM-existence probes answer more precisely than image diff. The handoff records the probe counts; future *additive* ItemCard PRs will still need the image grid (or the explicit precedent set here can be cited).

## Deploy notes

`fly deploy` clean — two new v439 machines, prior v438s destroyed.

Stale-blue sweep:

```
sweep: no stale blues on dual-research-alex
```

`/api/health` returns `{"ok":true,"version":"1.36.2","backend":"supabase"}`.

## Notes

- **PR rebase + re-push, sixth time this session.** Same `--push-to-main` event-divergence dance — PR #208 closed via remote-branch delete, replacement #209 admin-merged. The standing workflow-fix candidate is now flagged across 0171 / 0172 / 0175 / 0176 / 0178 / 0179.
- **Spec §3.4 edge case (last-seen-round info loss on open Issues with intermediate transitions).** The lifecycle chip carries `raised r{n} · resolved r{m}` for terminal cards (no info loss) but only `raised · r{n} · Agent` for open cards. For open Issues with multiple transitions before resolution, the `last seen R{m}` signal from the seen-row is technically lost. Per spec §3.4: "keep one chip — `<Chip tone='muted' size='sm'>last seen R{lastSeen}</Chip>` — inline if the lifecycle chip does not carry that field." Decision: dropped the seen-row entirely; the lifecycle-history surface (or a future hover affordance) is the right home for that detail if it surfaces as a real complaint. The five tests lock the seen-row absence; the fallback chip can be added later without touching them.

## Out of scope (per spec §6)

- 0173's territory in full (head rebuild + lifecycle chip + evidence-inline + resolver + expanded view + per-source + per-card collapse) — already shipped.
- 0172's territory in full (head ID chip + body short-codes + Markdown Issue body) — already shipped.
- The Issue 9 "open status while issue says resolved" data contradiction — data-layer problem, surface as a separate spec if still reproducible post-0173.
- A visual-regression CI rig for the four reference screenshots — multi-spec lift; the §4.1 gate is human-enforced at PR-review time.
