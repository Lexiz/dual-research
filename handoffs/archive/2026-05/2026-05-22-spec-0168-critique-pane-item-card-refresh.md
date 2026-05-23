---
spec: "0168"
date: 2026-05-22
version: 1.29.0
pr: https://github.com/Lexiz/dual-research/pull/191
---

# Spec 0168 — Critique pane item-card refresh (§2.1 only this cycle)

v1.29.0 ships **§2.1 only** of the L-complexity spec 0168 — the M3 card chrome catch-up for `.item-card`. The other seven sections (head rebuild, ID rendering rationale, lifecycle chip, evidence-needed inline, resolver identity, expanded view scaffolding, source attribution, per-card collapse) are explicitly deferred. The deferred work is internal to card layout and behaviour, not a blocker on §2.1's user-visible win.

## What landed (§2.1 only)

- **Item-card frame M3 chrome** ([src/dual_research/ui/static/components.css](src/dual_research/ui/static/components.css)) — `.item-card` adopts the spec-0164 `.tl-thread` chrome wholesale:
  - `background: var(--md-surface-container-high)` (was: `--md-surface-container`)
  - `border: 1px solid var(--md-outline-variant)` (was: `--md-outline-hair`)
  - `border-radius: var(--md-shape-lg)` (16 dp, was: `--md-shape-sm`/8 dp)
  - `overflow: hidden`, standard-easing transition on background/box-shadow/border-color
  - Hover lifts to `--md-elev-1` + `--md-surface-container-highest` + `--md-outline`
  - `padding: 12px 14px` retained (head/body etc. own theirs)
  - `margin: 0` (status-group body now uses `gap: 6px`)
- **Provider stripe** via `[data-raised-by]` attribute. The live JSX already carries this attribute (`data-raised-by="claude"|"gpt"|"system"`); no JSX change required. 2 px sable for Claude, sage for GPT, idle grey for System. Mirrors the timeline turn card's `:has()` stripe from spec 0164.
- **Status-group body gap.** `.crit2 .crit-group__body { display: flex; flex-direction: column; gap: 6px; }` replaces per-card margin.
- **DS canonical CSS unifies `.crit-card` and `.item-card`.** [design-system/assets/styles/composed-components.css](design-system/assets/styles/composed-components.css) groups the two selectors so both render with the identical chrome. Long-standing naming drift documented but not renamed.

## Deferred (§2.2 – §2.9)

| § | Title | Why deferred |
|---|---|---|
| 2.2 | Card head rebuild (drop low-value chips, reorganise) | Substantial JSX change — needs targeted iteration |
| 2.3 | ID rendering rationale (drop from card head) | Coupled to §2.2 |
| 2.4 | Round / state lifecycle chip with provenance | Needs data plumbing + chip-grouping work |
| 2.5 | Evidence-needed banner inline (vs. body row) | Small CSS, but coupled to head rebuild |
| 2.6 | Resolver identity on resolved state | Data plumbing for resolver-agent |
| 2.7 | Expanded view lifecycle scaffolding | Significant restructure of the expanded card layout |
| 2.8 | Source attribution (per-source provider + round) | Data plumbing + per-source render |
| 2.9 | Per-card collapse (`data-expanded="false"` default) | New behaviour, default state change, accessibility wiring |

Recommend authoring two follow-up specs that bundle the deferred sections by coupling:
- One spec for §2.2 + §2.3 + §2.5 (head rebuild + cleanup)
- One spec for §2.7 + §2.8 + §2.9 (expanded view + sources + collapse)

§2.4 + §2.6 (lifecycle chip + resolver identity) could ride with either group depending on which lands first.

## Tests

- `uv run pytest tests/ -q` — **1532 passed in 19.37s**.
- `npm test` — **9 passed (9)**.

## Deploy notes

- **Two consecutive lease-error attempts** before the third `fly deploy` converged. Same Fly bluegreen pattern as previous deploys (8 of the last 9 cycles).
- Final cluster: 2 machines on v1.29.0. Sweep: `no stale blues`.
- `/api/health` → `{"ok":true,"version":"1.29.0","backend":"supabase"}`.

## What's intentionally still rough

- The 16 dp radius + new chrome lands on every existing critique card without a hover-snapshot test. Visual smoke (deferred to manual) is the contract.
- The `.crit-card` (DS canonical) and `.item-card` (live impl) name unification was done via grouped selector, not by renaming the live JSX. A future cleanup could pick a single canonical name and migrate both DS and live.
