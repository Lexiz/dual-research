---
spec: 0107
title: Timeline phase/turn card treatment + RunDetailHeader children M3 token migration
label: refactoring
version-bump: PATCH
status: proposed
target-version: 0.76.4
created: 2026-05-19
pr: ""
---

# Spec 0107 — Timeline cards + RunDetailHeader children

> Ship bucket: **Cleanup / post-arc correction**
> Depends on: 0099 (timeline rework), 0094 (cards/badges CSS), 0106 (hotfix surface tiers)
> Complexity: **S**
> Targeted version bump: **PATCH** (refactoring — no new feature surface)
> Drive mode: **by hand** (not autonomous wrapper). Verifier hardening is a
> separate spec; until it lands, the wrapper's verify step false-passes.

## 1. Goal

After v0.76.3 the page has visible M3 surface tiering at the *pane*
level (chrome / sub-header / agent-bar / timeline-pane / critique).
What still looks unfinished is **inside** those panes:

- The timeline pane's phase + turn rows look like a flat text list,
  not the M3 card stack the design system specifies. `.tl-phase`
  and `.tl-turn` have no card surface, no elevation, no dashed
  divider — they sit transparent on the body surface.
- The `RunDetailHeader` children (`Topic`, `CostBadge`,
  `ReconcileChip`, `StatusErrorsBadge`, `PhaseDotsRow`) are still
  inline-styled with v1 tokens (`var(--bg-2)`, `var(--fg-1)`,
  `var(--border-1)`). They look slightly off against the new
  `.run-detail__head` surface (cream M3 surface holding v1
  cream chips with v1 grey borders).

After this spec lands, the timeline reads as a card stack and the
cost/status chips read as M3 chips.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — add card surface
  treatment to `.tl-phase` and `.tl-turn` (background, outline-
  hair border, padding), plus the single dashed top border on
  `.tl-turn--open` per spec 0099 Issue 11 (which 0099 specified
  but never wired). Approximately 15–20 new lines.
- `src/dual_research/ui/static/run-detail.jsx` — swap v1 token
  references in five sub-header child components:
  - `Topic` (line 374): `var(--fg-0)` → `var(--md-on-surface)`.
  - `CostBadge` (line 574): `var(--bg-2)` → `var(--md-surface-
    container-high)`, `var(--border-1)` → `var(--md-outline-
    hair)`, `var(--fg-1)` → `var(--md-on-surface-variant)`,
    `var(--fg-2)` → `var(--md-on-surface-muted)`, `var(--fg-3)`
    → `var(--md-on-surface-faint)`.
  - `ReconcileChip` (line 439): same v1-token-to-M3-token sweep
    inside its inline styles.
  - `StatusErrorsBadge` (line 604): same sweep; the COLORS.* refs
    stay (those are semantic palette anchors).
  - `PhaseDotsRow` (line 257): same sweep.
  - No structural changes — just token swaps. Component contracts
    and call sites untouched.
- `pyproject.toml` — bump `version = "0.76.3"` → `"0.76.4"`.
- `src/dual_research/__init__.py` — bump `__version__` similarly.
- `uv.lock` — refresh dual-research version line.
- `CHANGELOG.md` — new `[0.76.4]` entry.

Notably **not** touched: any inline v1 token outside the five
sub-header child components (the run-detail page still has ~280
inline v1 references that drain in follow-ups), the run-list page,
modals, error cards, consumption sub-cards.

## 3. Material 3 anatomy

- `#surfaces` — `.tl-phase` and `.tl-turn` read
  `--md-surface-container-low` (matches `.crit2__body` and the
  timeline body surface). Provides the "card on body" elevation
  illusion without an actual shadow (M3 prefers tonal elevation
  for low tiers).
- `#elevation` — no shadow at tier 1; the outline-hair border
  is the separator, same as `.tl-phase__hd` already uses.
- `#shape` — both elements get `border-radius:
  var(--md-shape-md)` (12 dp) for the card look.

Exact CSS class anchors introduced/wired:

```
.tl-phase                         → #surfaces (card surface + radius)
.tl-turn                          → #surfaces (card surface + radius)
.tl-turn--open                    → #surfaces (dashed top divider — spec 0099 Issue 11)
```

## 4. Notion issues addressed

- Issue 11 (spec 0099 deferred) — single dashed top border on
  expanded turn card.

## 5. Acceptance criteria

> All criteria are DOM-level. Hand-verified in the dev preview at
> http://127.0.0.1:6173/#/runs/20260516-035048-partner-vetting-
> arch-critique before push.

- [ ] `document.querySelector('.tl-phase')` has computed
      `backgroundColor` matching `--md-surface-container-low` (NOT
      `rgba(0,0,0,0)`).
- [ ] `document.querySelector('.tl-turn')` likewise has a
      non-transparent background and `borderRadius` ≈ 12 px.
- [ ] `document.querySelector('.tl-turn--open')` (when a turn
      is expanded) has a dashed top border using
      `--md-outline-hair` color.
- [ ] `getComputedStyle(document.querySelector('header[data-tour-
      anchor="run-detail-header"] .mono')).backgroundColor` (the
      CostBadge) matches `--md-surface-container-high`, not
      `--bg-2`.
- [ ] No `var(--bg-2)`, `var(--bg-3)`, `var(--fg-1)`, `var(--fg-2)`,
      `var(--fg-3)`, `var(--border-1)` substrings remain in the
      `Topic`, `CostBadge`, `ReconcileChip`, `StatusErrorsBadge`,
      `PhaseDotsRow` function bodies of `run-detail.jsx`.
- [ ] `uv run pytest tests/ -q` → 924 passed.
- [ ] Visual regression: `/api/health` on prod reports `0.76.4`
      after fly deploy; the chrome, sub-header, agent-bar, timeline
      pane SURFACES (tiers) are pixel-identical to v0.76.3 — only
      the children inside change.

## 6. Visual verification matrix

Two viewports × two themes = four hand-shot Playwright captures on
the canonical fixture:

- `2200×1300 dark` — full run-detail; phase rows + turn rows must
  read as cards stacked on the timeline body surface
- `2200×1300 light` — same; cards must be visible against the cream
  body surface (no cream-on-cream collapse)
- `1400×900 dark`
- `1400×900 light`

Side-by-side with v0.76.3 (HEAD~1) — the panes are identical, only
the cards-inside change.

## 7. Anti-pattern checks

- [ ] No emoji in component labels.
- [ ] No new inline `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)`
      tokens introduced in the touched functions.
- [ ] Reduced-motion contract preserved (no new animations).
- [ ] The `data-tour-anchor="run-detail-header"` attribute survives.

## 8. Handover read

> *First task on running this spec: read
> `handoffs/2026-05-19-spec-0105-*.md` end-to-end. Verify v0.76.3
> is live (`curl https://dual-research-alex.fly.dev/api/health`).
> Verify the five named child components still match the line
> numbers in § 2 before editing.*

## 9. Spec rewrite mandate

> *If a child component listed in § 2 has been further refactored
> since this spec was drafted, edit § 2 to match before
> implementing.*

## 10. Backend touched?

**no.** Static frontend only.

## 11. CSS class anchor list

```
.tl-phase                         → #surfaces (new card surface)
.tl-turn                          → #surfaces (new card surface)
.tl-turn--open                    → #surfaces (dashed top divider)
```
