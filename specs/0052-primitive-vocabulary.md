---
spec: 0052
title: Primitive vocabulary — Button, StatusBadge, Chip, RunIDChip, ThemeToggle, Card, AgentStrip + today's-component migration
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.49.0
created: 2026-05-17
pr: ""
---

# Spec 0052 — Primitive vocabulary

## Context

Second spec of the Claude Design migration arc — Ship 2, item 1 (the
plan we settled on in the [handoff](../handoffs/2026-05-17-design-system-kickoff.md)
called this SPEC-0051, but a parallel session shipped a Consumption
rework as 0051, so the design-system arc shifts up one slot).

Spec 0050 landed the foundation: tokens, base, focus ring,
reduced-motion contract, MDI icons, emoji removal. This spec
introduces the **primitive vocabulary** that surface-level specs
(Tab system, Run list, Run detail header, Timeline + critique) will
consume in SPEC-0053..0057.

Three primitives replace five legacy ones (CMP-04). Card collapses
to one component with three variants (CMP-05). AgentStrip shrinks
its min-width (CMP-07). ThemeToggle restored to segmented sun/moon
(CMP-02). Five components introduced in today's specs
(0046–0048) — `ReconcileChip`, `RepairChip`, `GhostedAnnotation`,
`CardHeadline`, and `ProviderBilledLine` — are migrated onto the new
primitives in the same PR, since the migration *is* the call-site
sweep.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **New `src/dual_research/ui/static/components.css`** — copied from the brief, only the sections we ship in this spec: `.btn`, `.sb` (StatusBadge), `.chip`, `.rid` (RunIDChip), `.card` (+ `.card-expandable` / `.card-live`), `.as` + `.ai` (AgentStrip + AgentIcon), `.tt` (ThemeToggle). | Mirrors the brief's source layout. Other component classes (Tab, Modal, QuestionThread, etc.) arrive in their respective specs. |
| D2  | **`index.html`** — new `<link rel="stylesheet" href="components.css">` between `base.css` and `theme.css` (load order: tokens → base → components → legacy). | Components ride on tokens + base; legacy `theme.css` cascade-overrides as it drains. |
| D3  | **New React primitives in `shared.jsx`**: `Button`, `StatusBadge`, `Chip`, `RunIDChip`, `Card`, `CardExpandable`, `CardLive`, `AgentStrip`, `ThemeToggle`. Each is a thin wrapper applying the corresponding `.foo` class + variant props. Exposed on `window` for cross-file consumption. | One component per CSS class. Props mirror brief's React API in [`scripts/primitives.jsx`](../../Downloads/Dual-research%20dashboard/scripts/primitives.jsx). |
| D4  | **Legacy `Pill` and existing `StatusBadge`** in `shared.jsx` stay alive **unchanged** (no auto-forwarding shims). | Auto-forwarding would change visuals on every legacy call site at once (different chrome, different padding). Safer to leave both APIs alive and migrate call sites surface-by-surface in SPEC-0055..0057. |
| D5  | **ThemeToggle restored to segmented sun/moon** (CMP-02) — replaces the current single-button cycle. `.tt` container + two `.tt-cell` buttons + `.tt-thumb` slider. `data-theme="light"`/`"dark"` controls thumb position. 180 ms ease-out transition. | Original product pattern (per brief §6). The current single-icon toggle has no "current state" affordance. |
| D6  | **AgentStrip min-width 480 → 320** (CMP-07). Just a token swap in the new `.as` class. | Header no longer dominated by strip after the chrome restructure (SPEC-0056). |
| D7  | **`ReconcileChip` migrated to `<Chip tone={…} pill lg icon={…}>`** (not `StatusBadge` as initially drafted) with the existing 5-state palette mapping to `tone-ok` / `tone-warn` / `tone-info` / `tone-muted` / `tone-info`. Chip's `icon` prop renders the per-state Mdi; Chip's `pill` + `lg` modifiers preserve the pill shape; inner body composition stays bespoke. All 5 states preserved. | StatusBadge always renders a dot before the label and is bound to a simple "dot + label" anatomy; ReconcileChip needs icon-replaces-dot + multi-element composed body. Chip's tone classes + icon prop + composed children is the right primitive fit. |
| D8  | **`RepairChip` migrated to `<Chip tone-warn>`** with `repair` label. The `compact` prop (used on Consumption-tab tight-row contexts) preserved via inline-style override on Chip's `style` pass-through. | Pure CSS-class swap; behavior unchanged. |
| D9  | **`GhostedAnnotation` AND `GhostedRoundsBadge` migrated to `<Chip tone-warn icon="alert">`** with `ghosted Nr` label. The two were near-duplicate components (one used inline as critique-pane annotation, one used inside `CardHeadline`); both now render identically via the single primitive. | Two-for-one migration. |
| D10 | **`CardHeadline` NOT migrated in this spec.** Its two inline-styled internal badges (kind+ID, status) use dynamic `accentColor` / `statusColor` props which don't fit Chip's static-tone system cleanly. Defer to **SPEC-0057** (timeline + critique surface rework) where `Card.expandable` is the proper wrapper. | The original D10 mis-stated the migration target — brief §8.9 doesn't describe Card.expandable as a headline-row pattern. CardHeadline reads new tokens via cascade in the meantime. |
| D11 | **`ProviderBilledLine` NOT touched in this spec.** It lives in the Consumption-card body, which is the active workspace of the parallel spec 0051. | Coordination — avoid merge conflicts. ProviderBilledLine migration deferred to a later spec after 0051 lands. |
| D12 | **No surface restructure.** Run list, run detail header, timeline, modals — all unchanged. Only primitive call sites change. | This is "primitive vocabulary", not "surface rework." Surfaces start landing in SPEC-0055. |
| D13 | **`Chip` primitive gains a `style` pass-through prop** beyond what the brief's [`primitives.jsx`](../../Downloads/Dual-research%20dashboard/scripts/primitives.jsx) defines. `RepairChip`'s `compact` mode and `GhostedAnnotation`'s `marginLeft` need it; cleaner than adding modifiers for each one-off. | Minor extension to the brief's API; documented inline. |
| D14 | **`SB` (new StatusBadge) is the brief-aligned name** in `shared.jsx` — the legacy `StatusBadge` keeps its original name + behaviour. Sweep happens when surface specs adopt SB; until then both coexist. | Avoids shadowing the legacy export. |

## Files touched

- [`src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) — **new**, copied from brief (relevant sections only).
- [`src/dual_research/ui/static/index.html`](../src/dual_research/ui/static/index.html) — new `<link rel="stylesheet" href="components.css">`.
- [`src/dual_research/ui/static/shared.jsx`](../src/dual_research/ui/static/shared.jsx) — new primitive components (`Button`, `StatusBadge`, `Chip`, `RunIDChip`, `Card`, `CardExpandable`, `CardLive`, `AgentStrip`, `ThemeToggle`); existing `Pill` and `StatusBadge` rewritten as deprecated shims forwarding to new versions; `window` exports updated.
- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) — migrate `ReconcileChip` (D7), `RepairChip` (D8), `GhostedAnnotation` (D9), `CardHeadline` (D10) onto new primitives. Other inline-styled chips in this file stay as-is until their owning surface spec lands.
- [`src/dual_research/ui/static/app.jsx`](../src/dual_research/ui/static/app.jsx) — `ThemeToggle` call site swaps from the single-button widget to the new segmented `<ThemeToggle>` primitive.
- `pyproject.toml` + `src/dual_research/__init__.py` + `CHANGELOG.md` + `how-it-works.jsx` VERSION_NOTES — 0.48.1 → 0.49.0.

## Out of scope

- **Tab system + table header** (CMP-01 / CMP-08 / CMP-11) → SPEC-0053.
- **QuestionThread + QuestionRef** (CMP-03 / CMP-09 / CMP-10) → SPEC-0054.
- **All surface restructures** (run-list sort, run-detail header rework, sticky PhaseRail, three-axis critique filter, modal RoundScrubber, etc.) → SPEC-0055..0058.
- **All other primitives from the brief** (`MetricRow`, `MetricStack`, `MetaBar`, `ChipCluster`, `CapBar`, `PhaseDots`, `ConnectionPill`, `Form fields`, `FullPageMessage`, `Markdown`) — not in this spec. Sweep as needed in later specs.
- **`ProviderBilledLine`** — defer to coordinate with spec 0051's Consumption rework (per D11).
- **Sweep `Pill` / legacy `StatusBadge` call sites** across `run-list.jsx`, `errors.jsx`, `auth.jsx`, `settings.jsx` — shims keep them working; full sweep happens in each surface's own spec.
- **Re-styling components introduced after spec 0048** other than the five named today's-components — there aren't any others.

## Test plan

- [ ] `uv run pytest tests/ -q` — 725 baseline green (no Python changes; pure JSX/CSS).
- [ ] Manual preview-verify on `localhost:6173`:
  - [ ] **ReconcileChip preserves all 5 visual states** on partner-vetting (`3a4a`) — the `drift` state with the +$0.71 finding must still render correctly. Other 4 states verified via tooltip / forced state.
  - [ ] **RepairChip** still renders on the `r4 GPT` turn-card row in partner-vetting.
  - [ ] **GhostedAnnotation** chips visible on each ghosted Question card.
  - [ ] **CardHeadline** renders correctly across critique cards.
  - [ ] **AgentStrip** renders at new 320 min-width without breaking the header layout in both themes.
  - [ ] **ThemeToggle** segmented control swaps theme smoothly; thumb animates; both cells aria-labeled.
  - [ ] **Existing surfaces** using legacy `Pill` / `StatusBadge` shims still render (run list, errors view, settings).
- [ ] No console errors; no broken `var(--token)` references.
- [ ] Hosted smoke after deploy: `curl /api/health` reports `0.49.0`.

## Risks

- **Merge conflict with parallel spec 0051.** That spec is touching `run-detail.jsx` in the Consumption-card region. Mitigation: D11 carves `ProviderBilledLine` out. Other migrations (ReconcileChip in header, RepairChip on turn cards, GhostedAnnotation + CardHeadline in critique pane) are in disjoint regions. If 0051 lands first, this spec rebases cleanly; if this lands first, 0051 rebases.
- **ReconcileChip 5-state preservation.** Same risk as spec 0050 — the production data still shows the +$0.71 drift on partner-vetting. The state palette is the load-bearing object; rewiring it onto `StatusBadge` while preserving the per-state body composition is the highest-risk surface in this spec. Mitigation: snapshot the rendered chip per state via preview tools before/after; tests for each state's body content.
- **`Pill` / legacy `StatusBadge` shim fidelity.** Their existing call sites use various props (size, color, icon). The shims must accept the legacy prop shape and emit the new primitive. If a prop drops on the floor, callsites render off-spec. Mitigation: grep every `<Pill>` and `<StatusBadge>` usage, list expected props, verify the shim covers them.
- **AgentStrip min-width drop may break run-detail header layout** if a downstream component relied on the 480 min. Mitigation: preview-verify run-detail header in both themes at standard + narrow viewport before merge.
- **ThemeToggle segmented swap is user-visible.** Existing users have muscle memory for the single-button toggle. Per CMP-02 the brief calls this a "restore" — the segmented version was the original. Brief decision; ship it. Note in VERSION_NOTES.

## Open questions

- The brief lists `Pill` as deprecated but our codebase uses it widely. Sweep in this spec or shim and defer? **Default this spec:** shim and defer (D4). Sweep happens with each surface's own rework.
- Brief's `StatusBadge` has a `live` modifier that pulses the dot. The current StatusBadge implementation doesn't have this. Add to the new primitive in this spec or wait until a surface needs it? **Default:** add to the new primitive (it's a single CSS class); call sites adopt as needed.
