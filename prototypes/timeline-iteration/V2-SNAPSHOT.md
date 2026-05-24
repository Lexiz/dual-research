# Timeline pane V2 — canonical snapshot (2026-05-24)

> **Purpose.** Canonical reference for the V2 timeline-pane state that spec [0203](../../specs/0203-timeline-v2-live-promotion.md) promotes from workshop to live. Freezes (a) the user-flagged issues against the live app (T1, T2.a, T2.b), (b) the shipped-audit for the 13 iter-locked design changes from [NOTES.md](./NOTES.md) §1, (c) the shipped-audit for drift items 3.A–3.G, (d) what stays out of scope, (e) the file list the promotion commit touches.
>
> **Pixel target** is [`proposed.html`](./proposed.html) (workshop CSS stack iter-1→iter-13).
> **Diff target** is [`live.html`](./live.html) (verbatim live-app dump from 2026-05-22).
> **Source of issues** is the Notion page [Critique & Timeline](https://www.notion.so/36999f3e507f8083b551f2c8fcbe46d3) (2026-05-23), section "Timeline".

---

## 1. Background

The workshop at [`prototypes/timeline-iteration/`](./) ran 13 iterations on 2026-05-22 ([NOTES.md](./NOTES.md)). The iter stack landed across four shipped specs:

- [spec 0164](../../specs/0164-timeline-pane-card-chrome-and-phase-header.md) — M3 card chrome (iter 4/5/8), phase header simplification (iter 1/2), narrow-view strip equalisation (iter 13), pane gutter (iter 5).
- [spec 0165](../../specs/0165-timeline-pane-chip-polish-and-token-drift.md) — chip polish (iter 6/7/9/10), light-mode token drift fix (3.A), cost precision (iter 10 + 3.E).
- [spec 0166](../../specs/0166-timeline-pane-system-error-chips-and-live-state.md) — System + Error chip primitives (iter 3), live-state agent-strip wiring (iter 11/12), turn-render data-layer fix (3.F).
- [spec 0173](../../specs/0173-drain-deferrals-from-0166-0167-0168.md) — `.activity-dot` pulse-info wiring (iter 11 §2.2.3 dot pulse) + other deferred items.

The user audited the live app against the workshop state on 2026-05-23 ([Notion page](https://www.notion.so/36999f3e507f8083b551f2c8fcbe46d3), Timeline section) and reported the timeline pane "is actually implemented pretty well … except for two things." This snapshot collapses the Notion audit + the per-iter shipped-audit + drift-status into a single index spec 0203 can cite verbatim.

The Notion timeline section enumerates two issues — **T1** (collapsed card height) and **T2** (click behaviour + cost precision). T2 has two distinct sub-issues so the snapshot disambiguates: **T2.a** (click should unfold in-place, not open the modal) and **T2.b** (turn-card cost rounded to two decimals after the comma).

---

## 2. User-flagged discrepancies (T1, T2.a, T2.b)

Each row maps to the Notion issue, the relevant `NOTES.md` iter (or the workshop CSS rule when no NOTES iter discusses it directly), the live-app file + line that needs to change, and the workshop pixel target.

| T# | Title | Notion ref | NOTES.md / workshop ref | Live currently | Pixel target |
|---|---|---|---|---|---|
| T1 | Collapsed timeline card head is taller than the workshop target — live is `padding: 10px 12px` (~42 px head) where workshop is `padding: 6px 12px` (~34 px head) | "the actual height of the cards in their collapsed state … on the live site they're a little bit higher … the iteration one is correct" | `proposed.html` iter-5 `<style id="iter-5-m3-card">` lines 249–254 — `.tl-thread > .tl-card-head { padding: 6px 12px !important; gap: 6px; background: transparent; border: 0; }`. [NOTES.md §2.4.2](./NOTES.md) calls out the 36-ish-px target loosely; the canonical pixel-exact source is the workshop CSS. | [components.css:2709-2711](../../src/dual_research/ui/static/components.css#L2709) `.qthread.tl-thread > .tl-card-head { padding: 10px 12px; }` — spec 0164 §2.4 picked a more generous head padding before the workshop's iter-5 lock; this overshoots the canvas. | `padding: 6px 12px; gap: 6px;` on `.qthread.tl-thread > .tl-card-head` → collapsed head clientHeight ≈ 34 px (chips 22 px tall + 12 px total vertical padding). |
| T2.a | Click on a collapsed card unfolds in place AND opens the full-view modal — should ONLY unfold in place; an explicit "Open full view" button opens the modal | "on the iteration you can actually click on the card and it will unfold itself … on the live website … the moment you click on it, it immediately unfolds itself but it also opens the full view mode … both of these need to work exactly like it is on the iteration" | `proposed.html` `_inline-script.js` simulates the in-place toggle via the `is-open-expanded` class on `.tl-thread` — the workshop has no modal at all, so the head-click unfolds the body and that's it. | [run-detail.jsx:825](../../src/dual_research/ui/static/run-detail.jsx#L825) — single state variable `openId` drives BOTH the inline `.is-open-expanded` class ([line 1232](../../src/dual_research/ui/static/run-detail.jsx#L1232) via `isOpen={openId === item.id}` at [line 934](../../src/dual_research/ui/static/run-detail.jsx#L934)) AND the `<ArtifactModal />` mount ([line 949–955](../../src/dual_research/ui/static/run-detail.jsx#L949)). Card head click + "Open full view" button click both call the same `onToggle` callback, so clicking the head opens both. | Split state: `expandedId` (drives `.is-open-expanded` and `data-expanded`) + `openId` (drives `ArtifactModal`). Card head click → toggle `expandedId` only; "Open full view" button click → set `openId` only. The two behaviours are independent. |
| T2.b | Turn-card cost should round to two decimals; verify EVERY cost display inside the timeline pane (not just the one already wired) | "the total cost in the batch should be rounded to two decimals after the comma" | Workshop `proposed.html` has no live cost data — the canonical helper is [run-detail.jsx:2720](../../src/dual_research/ui/static/run-detail.jsx#L2720) `fmtCost2(n)` (2-decimal, `<$0.01` for sub-cent values), introduced by [spec 0165 §2.5](../../specs/0165-timeline-pane-chip-polish-and-token-drift.md). | [run-detail.jsx:1344](../../src/dual_research/ui/static/run-detail.jsx#L1344) — expanded turn-card action chip already uses `fmtCost2(cost)` ✓ — shipped by spec 0165 §2.5. **Gap:** [run-detail.jsx:185](../../src/dual_research/ui/static/run-detail.jsx#L185) — `TimelineAgentPill` passes `costFormatter={fmt.costShort}` ([shared.jsx:658](../../src/dual_research/ui/static/shared.jsx#L658) `(n) => $${n.toFixed(2)}`) which is 2-decimal but **lacks the `<$0.01` sub-cent fallback** that `fmtCost2` has. Sub-cent agent-strip costs render as `$0.00` instead of `<$0.01`. | Migrate `TimelineAgentPill` to use `fmtCost2` (or equivalently extend `fmt.costShort` with the `<$0.01` fallback and keep the existing call-site). All other timeline-pane cost displays (only the two above exist) end up using fmtCost2 semantics. |

**Note on T2.b scope.** Per the user's promotion brief on 2026-05-24, T2.b's "every cost display" scope is bounded to **the timeline pane** (`.rdvc__pane` rooted at `Timeline`) — `TimelineAgentPill` and the expanded turn-card action chip. Cost displays outside the timeline pane (Consumption tab `fmtCost1` call-sites at [run-detail.jsx:2990,3110,3189,3213,3226,3253,3261,3266](../../src/dual_research/ui/static/run-detail.jsx); run-detail header CostBadge / ReconciliationChip 4-decimal `fmt.cost` at [run-detail.jsx:516,564,576,584,602,611,659](../../src/dual_research/ui/static/run-detail.jsx)) stay as they are — [spec 0165 §2.5](../../specs/0165-timeline-pane-chip-polish-and-token-drift.md) explicitly preserves the run-detail footer 4-decimal precision as the audit value.

---

## 3. Iter-1→iter-13 shipped audit

Each iter from [NOTES.md §1](./NOTES.md) verified against current code on 2026-05-24. ✓ = fully shipped, audited file:line cited; ⚠ = partial / drift surfaced (none currently); ⊘ = workshop-only, does not ship.

| Iter | One-line change | Shipping spec | Verified at | Status |
|---|---|---|---|---|
| 1 | `P{N}` → `Phase {N}` marker label | [0164 §2.2](../../specs/0164-timeline-pane-card-chrome-and-phase-header.md) | [run-detail.jsx:918](../../src/dual_research/ui/static/run-detail.jsx#L918) `<span className="lbl">Phase {vp.pid}</span>` | ✓ |
| 2 | `.tl-phase__pcode` removed | 0164 §2.2 | [components.css:2604](../../src/dual_research/ui/static/components.css#L2604) comment "removed by spec 0164 §2.2"; [components.css:2581-2582](../../src/dual_research/ui/static/components.css#L2581) grid drops to 5 cols | ✓ |
| 3 | System chip + Error chip for agentless / failed cards | [0166 §2.3 + §2.4](../../specs/0166-timeline-pane-system-error-chips-and-live-state.md) | [run-detail.jsx:1255-1267](../../src/dual_research/ui/static/run-detail.jsx#L1255) `<SystemChip /> / <ErrorChip />` branches in TlTurnRow | ✓ |
| 4 | M3 timeline-card chrome (filled card, outline, hover elev-1, expanded elev-2) | [0164 §2.4](../../specs/0164-timeline-pane-card-chrome-and-phase-header.md) | [components.css:2659-2706](../../src/dual_research/ui/static/components.css#L2659) `.qthread.tl-thread` block + hover + `.is-open-expanded` | ✓ |
| 4b | Side-by-side dark/light workshop wrapper | — | [`mockup.html`](./mockup.html) only | ⊘ workshop-only |
| 5 | 16 px horizontal pane gutter + surface-container-high card + outline-variant border | 0164 §2.3 + §2.4 | [components.css:2585](../../src/dual_research/ui/static/components.css#L2585) `.tl-phase__hd { padding: 12px 16px }`; [components.css:2629](../../src/dual_research/ui/static/components.css#L2629) `.tl-phase__body { padding: 8px 16px 12px; gap: 6px }`; [components.css:2660-2661](../../src/dual_research/ui/static/components.css#L2660) card surface + outline | ✓ |
| 6 | Identity-chip background bumped to ~30% color-mix | [0165 §2.1](../../specs/0165-timeline-pane-chip-polish-and-token-drift.md) | [components.css:509-517](../../src/dual_research/ui/static/components.css#L509) `.tl-card-head .chip.tone-claude/gpt/neutral` color-mix rules | ✓ |
| 7 | Softer System chip (idle @ 20%) + explicit dark Claude/GPT text in light mode | 0165 §2.1 + §2.2 (3.A) | [components.css:515-517](../../src/dual_research/ui/static/components.css#L515) System chip 20%; [components.css:549-557](../../src/dual_research/ui/static/components.css#L549) `body.light .tl-card-head .chip.tone-{claude,gpt}` text-color overlay | ✓ |
| 8 | Provider-tinted header strips (sable/sage @ 8%) + 2 px provider left-stripe + `--md-shape-lg` (16 dp) | 0164 §2.4 + §2.2 | [components.css:483-490](../../src/dual_research/ui/static/components.css#L483) `.as.is-a.in-header` / `.as.is-b.in-header` 8% color-mix; [components.css:2687-2695](../../src/dual_research/ui/static/components.css#L2687) `:has()` provider stripes; [components.css:2662](../../src/dual_research/ui/static/components.css#L2662) `border-radius: var(--md-shape-lg)` | ✓ |
| 9 | Category bubbles in phase-header chips dimmed to 70% alpha | 0165 §2.3 | [components.css:536-539](../../src/dual_research/ui/static/components.css#L536) `.tl-phase__chips .chip.tone-X .cat-bubble` 70% color-mix | ✓ |
| 10 | Activity chip bumped to `surface-container-highest` + expanded-card cost rounded to 2 decimals | 0165 §2.4 + §2.5 | [components.css:519-525](../../src/dual_research/ui/static/components.css#L519) `.tl-card-head .chip.tone-neutral.mono` surface-container-highest; [run-detail.jsx:1344](../../src/dual_research/ui/static/run-detail.jsx#L1344) `fmtCost2(cost)` | ✓ |
| 11 | Live-state sweep on `.as.in-header.is-live::before` + activity-dot pulse + "negotiating · round 4"-style phrase | 0166 §3 + [0173 §2.1](../../specs/0173-drain-deferrals-from-0166-0167-0168.md) | [components.css:591-599](../../src/dual_research/ui/static/components.css#L591) `::before` sweep + GPT delay; [components.css:661-679](../../src/dual_research/ui/static/components.css#L661) `.activity-dot` pulse-info wiring; [run-detail.jsx:164-176](../../src/dual_research/ui/static/run-detail.jsx#L164) phrase derivation in `composeAgentActivity` | ✓ |
| 12 | `box-shadow: var(--md-elev-2)` on `.as.in-header.is-live` | 0166 §3 | [components.css:631-635](../../src/dual_research/ui/static/components.css#L631) `.as.in-header.is-live { box-shadow: var(--md-elev-2) }` | ✓ |
| 13 | Narrow-view (≤ 1799 px) agent-strip equalisation — both `.as.in-header` capped at 320 px | 0164 §2.5 | [components.css:561-587](../../src/dual_research/ui/static/components.css#L561) `@media (max-width: 1799px) .tl__head .as.in-header, .tl__tabs .as.in-header { width: 320px; max-width: 320px; flex: 0 0 320px; margin-left: auto }` | ✓ |

**Bottom line.** All 13 ship-eligible iters are shipped. No iter needs re-shipping in spec 0203. The promotion delta is exactly T1 + T2.a + T2.b (plus the cascading DS-mirror updates per [CLAUDE.md](../../CLAUDE.md#design-system) §Design system).

---

## 4. Drift items 3.A–3.G shipped audit

Each drift item from [NOTES.md §3](./NOTES.md) verified against current code on 2026-05-24.

| Drift | Title | Shipping spec | Verified at | Status |
|---|---|---|---|---|
| 3.A | Light-mode `--md-on-{primary,secondary}-container` tokens missing | [0165 §3.A](../../specs/0165-timeline-pane-chip-polish-and-token-drift.md) | [tokens.css:339-342](../../src/dual_research/ui/static/tokens.css#L339) `body.light { --md-on-primary-container: #3b2810; --md-on-secondary-container: #0a322d }` | ✓ |
| 3.B | Identity-chip background too subtle by default | 0165 §2.1 | [components.css:509-517](../../src/dual_research/ui/static/components.css#L509) — scoped `.tl-card-head` overrides at 30% / 20% color-mix | ✓ |
| 3.C | Activity chip = card surface (invisible after iter 5) | 0165 §2.4 | [components.css:519-525](../../src/dual_research/ui/static/components.css#L519) — `.tl-card-head .chip.tone-neutral.mono { background: var(--md-surface-container-highest) }` | ✓ |
| 3.D | Phase header pcode redundant with marker | 0164 §2.2 | [components.css:2604](../../src/dual_research/ui/static/components.css#L2604) — pcode removed, comment in place | ✓ |
| 3.E | Cost precision drift | 0165 §2.5 | [run-detail.jsx:2720](../../src/dual_research/ui/static/run-detail.jsx#L2720) `fmtCost2` helper + [run-detail.jsx:1344](../../src/dual_research/ui/static/run-detail.jsx#L1344) call-site. **Note:** T2.b extends this further into the TimelineAgentPill at [run-detail.jsx:185](../../src/dual_research/ui/static/run-detail.jsx#L185) — partial coverage from 0165 is the lever T2.b pulls. | ✓ (expanded-card chip) + extended by T2.b (agent strip) |
| 3.F | `turn [object object]` rendering bug | 0166 §2.3 + §2.4 | [run-detail.jsx:1255-1267](../../src/dual_research/ui/static/run-detail.jsx#L1255) defensive `activityLabelError` branch → `<SystemChip /> + <ErrorChip />` | ✓ |
| 3.G | `Design System v2.html` §16 doesn't reflect the live timeline | — | Not shipped in 0164/0165/0166/0173 — [`design-system/assets/Design System v2.html`](../../design-system/assets/Design%20System%20v2.html) §16 still renders the pre-marker / pre-chip-cluster anatomy. | ⚠ deferred — out of scope for spec 0203; tracked for a follow-up DS-catch-up spec. |

**Bottom line.** Six of seven drift items shipped cleanly. 3.G (DS §16 catch-up) is acknowledged unshipped and deferred per [§5](#5-deliberately-deferred-not-in-scope-for-spec-0203) — it doesn't block spec 0203 since the user-facing pixels read off `composed-components.css` + `components.css`, not the rendered HTML reference.

---

## 5. Deliberately deferred (NOT in scope for spec 0203)

Per the user's promotion brief on 2026-05-24:

- **Drift 3.G** — `Design System v2.html` §16 still renders pre-marker / pre-chip-cluster anatomy. Out of scope for the V2-promotion spec; tracked for a follow-up DS-catch-up spec (no number assigned yet; expect to draft post-merge of 0203 and the parallel critique-V2 promotion 0203 critique sibling).
- **Iter 4b** — workshop-only side-by-side wrapper; never ships.
- **Critique pane** — covered by the parallel spec authoring in [`prototypes/critique-iteration/`](../critique-iteration/) (sibling V2-SNAPSHOT.md drives the critique promotion).
- **Canvas skill regeneration logic** — separate spec (the next one in the series).
- **Σ Summary cluster / Resolved split** — critique-side concerns; not in this spec.
- **`fmtCost1` migration outside the timeline pane** — Consumption tab cost displays and run-detail header CostBadge / ReconciliationChip 4-decimal precision stay as they are; [spec 0165 §2.5](../../specs/0165-timeline-pane-chip-polish-and-token-drift.md) explicitly preserves the audit precision in those surfaces.

---

## 6. Promotion target files (all three updated in the same commit)

Per [`CLAUDE.md`](../../CLAUDE.md) §Design system: DS authoritative copy and live-app copy stay in sync — additions to one MUST land in the other in the same commit.

| File | Role | T1 | T2.a | T2.b |
|---|---|---|---|---|
| [`src/dual_research/ui/static/components.css`](../../src/dual_research/ui/static/components.css) | Live-app timeline CSS | shrink `.qthread.tl-thread > .tl-card-head` padding to `6px 12px`; add `gap: 6px` | no change (state lives in JSX) | no change (cost rendering is JSX) |
| [`design-system/assets/styles/composed-components.css`](../../design-system/assets/styles/composed-components.css) | DS authoritative copy | mirror the same `.tl-card-head` padding/gap | no change | no change |
| [`src/dual_research/ui/static/run-detail.jsx`](../../src/dual_research/ui/static/run-detail.jsx) | React components for the timeline pane | no change | split state at line 816 (introduce `expandedId` separate from `openId`); rewire `isOpen` derivation, `onToggle`, "Open full view" button onClick, and ArtifactModal mount condition; add `data-expanded` attribute on `<article>` mirroring `expandedId` | swap `costFormatter={fmt.costShort}` at [line 185](../../src/dual_research/ui/static/run-detail.jsx#L185) to `costFormatter={fmtCost2}` |

---

## 7. References

- [`prototypes/timeline-iteration/NOTES.md`](./NOTES.md) — full iter record (iters 1-13 + drift items 3.A-3.G)
- [`prototypes/timeline-iteration/proposed.html`](./proposed.html) — pixel target (workshop CSS stack)
- [`prototypes/timeline-iteration/live.html`](./live.html) — diff target (live-app dump 2026-05-22)
- Notion: [Critique & Timeline](https://www.notion.so/36999f3e507f8083b551f2c8fcbe46d3) (the T1/T2 source, Timeline section)
- [`design-system/SPEC.md`](../../design-system/SPEC.md) — DS sections cited by spec 0203 (§3 primitives, §4.4 Timeline pane, §9 badge governance)
- Prior shipping specs: [0164](../../specs/0164-timeline-pane-card-chrome-and-phase-header.md), [0165](../../specs/0165-timeline-pane-chip-polish-and-token-drift.md), [0166](../../specs/0166-timeline-pane-system-error-chips-and-live-state.md), [0173](../../specs/0173-drain-deferrals-from-0166-0167-0168.md)
- Parallel critique-V2 promotion: [`prototypes/critique-iteration/V2-SNAPSHOT.md`](../critique-iteration/V2-SNAPSHOT.md) (no file-level conflict expected — different selectors/components)
