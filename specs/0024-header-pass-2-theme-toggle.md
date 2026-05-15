---
spec: 0024
title: Run-detail header pass 2 + compact theme toggle
label: refactoring
version-bump: PATCH
status: merged
target-version: 0.22.1
created: 2026-05-16
pr: "https://github.com/Lexiz/dual-research/pull/24"
---

# Spec 0024 — Header pass 2 + compact theme toggle

## Context

Spec 0023 dropped the run-detail header from four rows to two, but
there's still meaningful waste. The chrome bar already has an "All
runs" tab, so the in-detail "← All runs" chip is redundant — a back
arrow is enough. The brand/id/copy pill is decoration: every run is
dual-research, the gradient icon is meaningless, and the 4-char hash
chip has no shown affordance for what clicking it does. Phase progress
plus its "PHASE N Label" label competes with the headline status badge
for the same row.

The theme toggle is two pills today (light + dark side by side); a
single compact icon-toggle pill carries the same affordance in half
the horizontal space.

This spec is purely visual — no backend changes.

## Design decisions

| # | Decision | One-liner |
|---|---|---|
| D1 | **Drop the back chip; replace with an icon-only ← arrow button** | Tab "All runs" in the chrome already serves as the textual back affordance; the chip duplicates it. |
| D2 | **Drop the "dual-research" brand text and gradient icon** | Every run is dual-research; the brand mark adds noise. |
| D3 | **Drop the "70e3" copy-id chip** | The full run id is already on the all-runs row; copy-to-clipboard isn't a primary workflow. |
| D4 | **Add a "TOPIC" caps-label tag in front of the topic text** | Makes the role of the long sentence explicit. Small mono badge. |
| D5 | **Drop the phase-strip "PHASE N Label" text** | The status badge already communicates the headline state; the phase number is in the meta row implicitly via outcome text. |
| D6 | **Drop the phase-strip outcome text ("converged in 12m 49s")** | Meta row already shows "12m 49s elapsed". |
| D7 | **Composite status+errors badge**: `[● completed]` (zero errors) or `[● completed │ ⚠ 3 errors]` (errors present, right half clickable to navigate to the errors view) | One pill, fewer chips. Click on the errors half toggles the errors view. |
| D8 | **Cost+tokens badge**: combine `$0.4228` and total-tokens count into a single pill `$0.4228 · 392Kt` | Two facts about scale in one chip. |
| D9 | **Phase progress dots move to the far right, on a second visual row immediately under the status badge** | Right-aligned, no label. Provides at-a-glance progress without the verbose `PHASE N Label` text. |
| D10 | **Theme toggle: single pill with two icons inside** (sun + moon), active icon highlighted, clicking the inactive icon flips theme | Halves the horizontal space the toggle eats. |
| D11 | **Layout: two visual rows total.** Row 1: back-arrow + TOPIC label + topic text + (push right) cost badge + status+errors badge. Row 2: meta line on left, phase dots on right (under the status badge). | Recovers another half-card of vertical space relative to spec 0023. |

## Proposed change

### `src/dual_research/ui/static/run-detail.jsx`

Rewrite `RunDetailHeader`:

```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ [←] TOPIC  Compare SQLite vs Postgres for a single-tenant API…    [$0.4228 · 392Kt]  [● completed │ ⚠ 3 errors] │
│       started 16:31 · drafter GPT · 12m 49s elapsed                                         •─•─•─•─•─●  │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

- `BackArrow` — small icon-only chip (24×24), uses `Icon.Arrow`
  rotated 180°. `BackChip` and `BrandIdPill` deleted.
- `TopicLabel` — caps mono tag `TOPIC` next to the topic line.
- `Topic` keeps the single-line clamp; gets a slightly larger
  treatment so it reads as the visual centre.
- `CostBadge` — new component. Pill containing `fmt.cost(total)` + ` · ` +
  total token count (claude.tokens.in + claude.tokens.out +
  gpt.tokens.in + gpt.tokens.out, k-suffixed via `fmt.tokens`).
- `StatusErrorsBadge` — new composite. Outer pill, two segments:
  left = status (existing StatusBadge-style content), right = errors
  (only when count > 0; clickable to toggle errors view). When the
  errors view is showing, the right segment becomes a "back to
  timeline" affordance.
- `PhaseDots` — extracted from current `PhaseProgressGroup`, no label.
  Placed in row 2 right-aligned.

The existing `PhaseProgressGroup` deleted; its inner dots loop reused
in the new `PhaseDots`. `RunIdChip` (orphan since spec 0023) finally
removed.

### `src/dual_research/ui/static/app.jsx`

Replace `ThemeSegmentedToggle` with a new `ThemeToggle`:

- One pill, fixed width ~58 px.
- Two stacked icon buttons inside (sun, moon), side by side.
- The active one has accent bg + `--fg-0` colour; the inactive is
  muted (`--fg-3`).
- Click on either icon switches; clicking the active one is a no-op.

`ThemeSeg` helper deleted; `Icon.Sun` and `Icon.Moon` inlined in the
new component (or added to the icon map — preferring the latter for
consistency).

### `src/dual_research/ui/static/shared.jsx`

- Add `Icon.Sun` and `Icon.Moon` to the `Icon` map (replacing the
  inline SVGs from `ThemeSegmentedToggle`).
- Add a `fmt.tokensTotal` helper that takes an agents-shaped object
  and returns `{ in + out }` summed across agents (or just call
  `fmt.tokens` inline — keeping changes contained).

### Version + CHANGELOG + VERSION_NOTES

`pyproject.toml` 0.22.0 → 0.22.1. `__init__.py` ditto.
CHANGELOG: `## [0.22.1]` entry.
`VERSION_NOTES` array in `how-it-works.jsx`: new entry at the top.

## Out of scope

- Run-list compaction. Visible row density on `#/` is fine for now.
- Mobile layout. Desktop-first.
- Animation between theme states. Instant flip.
- Repositioning the chrome-bar `All runs` tab. Stays put.
- Custom labelling of the run by the user. Topic comes from
  `brief.md`'s first H1 (or first non-empty line). Editing it is a
  future-feature concern.

## Test plan

- `pytest tests/` stays green (277).
- Manual: open a completed run, verify two-row header, status+errors
  composite pill, errors half clicks through to the errors view, cost
  badge shows cost + tokens, phase dots on row 2 right.
- Manual: toggle theme — single pill flips between light and dark
  icons; selected icon highlighted.

## Risks

- **Topic visual hierarchy collision.** A very long topic with a
  short tokens count + many errors could squeeze the right-side
  badges visually. Mitigated by topic single-line clamp + ellipsis;
  the badges are flex-shrink-none so they keep their natural width.
- **Mid-flight run "Phase N Label" deletion regresses live runs.**
  The status badge already says `running`; round and phase info is in
  the meta row when in-flight. If real users find the loss confusing
  for live runs we add a small phase chip back next to the status
  pill — not in this spec.
- **Theme toggle motion-affordance.** Single-pill icon toggles can
  feel less obvious than the segmented look. The active icon's
  highlighted background should make the click target clear; tooltip
  on the inactive icon ("Switch to light") helps if needed.
