---
spec: "0164"
date: 2026-05-22
version: 1.25.0
pr: https://github.com/Lexiz/dual-research/pull/187
---

# Spec 0164 — Timeline pane M3 card chrome + phase header simplification + narrow-view strip equalisation

v1.25.0 ships six coupled visual gaps in the run-detail timeline pane, all in one MINOR release. No schema change, no data migration. Every existing run renders with the new chrome on first load.

## What landed

- **§2.1 Phase marker — full-word label.** `src/dual_research/ui/static/run-detail.jsx` line ~909 now renders `<span class="lbl">Phase {vp.pid}</span>` unconditionally. The previous fallback chain (`vp.pDef?.short || \`P${vp.pid}\``) is preserved everywhere else that needs the short form — the `<PhaseRail />` cell at line 784 (5-cell horizontal strip, space-constrained `.ph` slot) and the `<PhaseProgressStrip />` tooltip at line 756 (`title={\`${p.short} ${p.label} · ${stateLabel}\`}`) still pull `PHASES.short` from `src/dual_research/ui/static/live-data.jsx`.
- **§2.2 `.tl-phase__pcode` removed.** JSX element gone (was line ~914). CSS rule gone from both `src/dual_research/ui/static/components.css` and `design-system/assets/styles/composed-components.css`. `.tl-phase__hd` grid drops from 6 cols to 5: `marker · chevron · name · meta · chips` (template `auto 20px auto 1fr auto`).
- **§2.3 16 px pane gutter.** `.tl-phase__hd` padding `12px 16px`; `.tl-phase__body` `8px 16px 12px` with `gap: 6px`. Cards now inset from the pane edges instead of running flush.
- **§2.4 M3 turn card chrome.** `.qthread.tl-thread` rewritten (both CSS files): `--md-surface-container-high` background, `--md-outline-variant` border, `--md-shape-lg` (16 dp) radius, `overflow: hidden`, `padding: 0`, `gap: 0`. Standard-easing transition on background/box-shadow/border-color. Hover lifts to `--md-elev-1` + container-highest background + `--md-outline` border. `.is-open-expanded` drops to container-low + `--md-elev-2`; the inner `> .tl-card-head` keeps container-high with a hairline bottom border so the still-visible row reads above the expanded body. Head/body/actions own their padding (10/12 px on head, 10/12/0 on body, 8/12/10 on actions). The legacy `.qthread.is-open` / `.is-resolved` / `.is-drift` status side-borders are explicitly cleared on `.tl-thread` so the new provider stripe shows through — status info reads off the right-cluster status chip.
- **§2.4 Provider stripe via `:has()`.** 2 px left border, native CSS `:has()` against `.tl-card-head > .chip.tone-{claude,gpt,neutral:not(.mono)}`. Sable for Claude, sage for GPT, idle grey for System cards. The `:not(.mono)` qualifier on the neutral selector distinguishes the identity chip from the mono activity chip that may also carry `.tone-neutral`. Chrome 105+, Safari 15.4+, Firefox 121+.
- **§2.5 Header AgentStrip 8 % tonal tint.** `.as.is-a.in-header` and `.as.is-b.in-header` carry `color-mix(in srgb, var(--p-{sable,sage}) 8%, var(--md-surface-container))`. The existing `::before` gradient sweep (spec 0138 §5.1) for live-state still paints over this base. 2 px left-border and brand-mark icon unchanged.
- **§2.6 Narrow-view strip equalisation (≤ 1799 px).** `@media (max-width: 1799px)` block caps both `.tl__head .as.in-header` and `.tl__tabs .as.in-header` to 320 px with right-align preserved (their existing `margin-left: auto` lines up the right edges). `.as-activity` falls back to `text-overflow: ellipsis`. `!important` required because the unconditional `min-width: 600px` + `flex: 0 0 auto` on the base `.as.in-header` win on specificity otherwise.
- **DS catch-up.** `design-system/SPEC.md` §3 Primitives gained a new "Timeline card (`.tl-thread`)" row documenting the four states + per-provider stripe. §4.4 Timeline pane rewritten to codify the 5-col phase header, 16 px pane gutter, M3 turn card chrome with provider stripe, header AgentStrip 8 % tint, and narrow-view strip equalisation. `design-system/assets/Design System v2.html` §16 anatomy re-rendered: new 5-col phase header example with marker + chevron + name + meta; four `.tl-thread` variants (Claude / GPT / System / expanded-Claude); two in-header AgentStrip examples showing the 8 % sable + sage tints.

## Tests

- `uv run pytest tests/ -q` — **1532 passed in 20.09s**. No new tests added (spec is visual/CSS — manual visual smoke is the contract, per §7 of the spec). No existing test failed under the new chrome.
- `npm test` (vitest, happy-dom) — **9 passed (9)**. Dashboard-bootstrap and staleness-chip suites from spec 0163 still pass.
- Live-push end-to-end: every branch-phase event for this spec (`branched`, `implementing_started`, `implement_complete`, `tests_started`, `tests_green`, `pr_opened`, `merged`) landed on `origin/main` as its own commit within seconds of emission — the spec-0163 mechanism worked smoothly this entire cycle.

## Deploy notes

- `fly deploy` for v1.25.0 ran into the now-familiar Fly bluegreen lease-table bug — error: `failed to get lease on VM 781245db96d748: machine ID … lease currently held by … expires at 2026-05-22T17:54:01Z`. First attempt aborted partway through; **second attempt succeeded after the lease expired**, landing version 299 then version 301 across 4 machines (2/2 new tier each). Cluster eventually converged to 2 machines at v1.25.0 (image `01KS8D2T2SSJC3HC40X9DEAFKM` / fly version 299).
- Post-deploy sweep: `sweep: no stale blues on dual-research-alex` (final state — Fly self-destroyed the extras after the new green machines passed health checks).
- `/api/health` → `{"ok":true,"version":"1.25.0","backend":"supabase"}` confirmed live.
- **Transient propagation note:** for the first ~60s after deploy, `/api/health` continued to return `1.24.0` from a cached LB route. A fresh request after the cluster settled returned `1.25.0`.

## Open follow-ups

- **Fly bluegreen lease-table flakes.** Now four deploys in a row (handoffs 0160 / 0161 / 0163 / 0164) have surfaced lease errors during the rolling phase. The spec 0162 post-deploy sweep handles the *follow-up* hygiene (`safe_to_destroy` cleanup) but cannot prevent the lease-acquire failure mid-roll. Worth thinking about a pre-deploy lease-clearing step or filing upstream with Fly.
- Spec 0165 will pick up identity-chip backgrounds + activity-chip surface bump + light-mode chip text drift + cost precision + category-bubble alpha dim. The new `.tl-thread` chrome from this spec is its dependency — the M3 card primitive is now in place.
- Spec 0166 will add the System + Error chip primitives, agentless-card composition, live-state agent-strip wiring (`.is-live` class + dot pulse + elev-2 lift), and the `[object Object]` data-layer fix. Depends on this spec for the M3 primitive + the §2.5 in-header tint.

## What's intentionally still rough

- The `.tl-phase__hd` `:focus-visible` outline + state-layer hover overlay from the pre-existing implementation are kept as-is. Spec 0164 didn't call them out and changing them would balloon the diff.
- The expanded card body's text uses `--md-font-brand` italic per the legacy `.tl-thread__body` rule. Kept as-is.
- PhaseRail's `.ph` slot still reads `P0` / `P1` / etc. via `PHASES.short`. Out of scope for this spec (the marker, not the rail, was the user-visible problem).
