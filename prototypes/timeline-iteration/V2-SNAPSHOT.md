# Canvas Timeline — V2 (locked 2026-05-23)

> Named checkpoint of the timeline workshop's `proposed.html` state. Companion
> to [`prototypes/critique-iteration/V2-SNAPSHOT.md`](../critique-iteration/V2-SNAPSHOT.md).
> Treat this as the source of truth when authoring a spec that promotes V2
> into the live dual-research app.

## The rule of thumb

**Everything that lives in `prototypes/timeline-iteration/proposed.html` right
now is exactly what needs to land on the live site.** No filtering, no
prioritisation — the whole canvas is the spec.

## What V2 is

Timeline V2 = the workshop-locked state from [`NOTES.md`](./NOTES.md) §1
(iters 1, 2, 3, 4, 4b, 5, 6, 7, 8, 9, 10, 11, 12, 13). **No patches** have
been applied on top — unlike the critique pane, the timeline canvas didn't
need additional fixes during this session. The state as captured in NOTES.md
is the state of record.

## Where Timeline V2 lives on disk

| File | Role |
|---|---|
| [`prototypes/timeline-iteration/mockup.html`](./mockup.html) | Workshop wrapper (Iteration / Live / DS tabs + theme + width toggle) |
| [`prototypes/timeline-iteration/proposed.html`](./proposed.html) | The iter-locked target state |
| [`prototypes/timeline-iteration/live.html`](./live.html) | Verbatim live-app dump of `.rdvc__pane` |
| [`prototypes/timeline-iteration/ds.html`](./ds.html) | Verbatim DS v2 §16 extract |
| [`prototypes/timeline-iteration/NOTES.md`](./NOTES.md) | Original 660-line drift overview + per-element spec |

## The two user-flagged differences vs. live (from the Critique-issue Notion page)

### T1 — Card height in the collapsed state

Iteration cards are visibly **shorter** than live cards. The iteration card
height is correct.

**Source of truth:** [NOTES.md](./NOTES.md) §2.4.1 (frame) + iter 5
(`.tl-phase__hd` padding 12px 16px, `.tl-phase__body` padding 8px 16px 12px,
`gap: 6px`). The live `.tl-thread` chrome carries extra padding/margin from
pre-iter-5 defaults.

**Implementation hint for the future spec:** when promoting iter 5 into
`src/dual_research/ui/static/components.css`, confirm the gap + padding
values land verbatim — earlier specs (0164) shipped the M3 chrome but the
height parity check was never browser-verified per the spec 0173 handoff.

### T2 — Click behaviour + cost precision

(a) On the iteration: clicking a card **unfolds it in place** to show the
turn body (full view mode button + the three action chips on the right). On
the live site: clicking immediately opens the full-view modal — the in-place
expansion is skipped.

(b) The total cost in the expanded action chip should be rounded to **2
decimals** (e.g. `$0.03`, not `$0.0312`).

**Source of truth:**
- For (a): the workshop wrapper triggers in-place unfold via the iframe DOM
  click handler. The live app's `.tl-thread` click currently routes to the
  modal-open action. The right fix on live is to bind the head click to
  toggle `data-expanded` on the card and only route the explicit "Full view"
  button to the modal.
- For (b): NOTES.md §2.7.2 + iter 10. Spec 0165 §2.5 shipped the
  `fmtCost2(n)` helper but the call-site may not have been wired everywhere
  the user expects.

## The full iter list (verbatim §1 from NOTES.md)

| Iter | Change | Element |
|---|---|---|
| 1 | `P{N}` → `Phase {N}` in the marker label | Phase header |
| 2 | Removed redundant `.tl-phase__pcode` (`PHASE 0` after the chevron) | Phase header |
| 3 | Added a `System` identity chip + human-readable Error chip for agentless cards | Turn cards (brief + render-error) |
| 4 | M3 timeline-card chrome — filled card, outline, hover elev-1, expanded elev-2 | Turn cards (both states) |
| 4b | Side-by-side dark/light rendering | Workshop wrapper only — does not ship |
| 5 | 16 px horizontal pane gutter + `surface-container-high` card + `outline-variant` border | Phase body + turn card chrome |
| 6 | Identity-chip background bumped to ~30% color-mix (Claude / GPT / System) | Turn card head |
| 7 | Softer System chip (idle @ 20%) + explicit dark Claude/GPT text in light mode | Turn card head |
| 8 | Provider-tinted header strips (sable/sage @ 8%) + 2 px provider left-stripe + radius `--md-shape-lg` (16dp) | Header strips + turn cards |
| 9 | Category bubbles in phase-header chips dimmed to 70% alpha | Phase-header chip cluster |
| 10 | Activity chip bumped to `surface-container-highest` + cost rounded to 2 decimals | Turn card head + expanded actions |
| 11 | Live-state sweep + dot pulse + "negotiating · round 4" phrase | Header strips |
| 12 | `box-shadow: var(--md-elev-2)` on `.as.in-header.is-live` | Header strips (live state only) |
| 13 | Narrow-view (≤1799 px) agent-strip equalisation — both capped at 320 px | Header strips (responsive) |

## Drift items (verbatim §3 from NOTES.md)

These are issues NOTES.md called out vs. the pre-iteration live state. Most
shipped via specs 0164/0165/0166/0173.

| ID | Issue | Status (per spec history) |
|---|---|---|
| 3.A | Light-mode `--md-on-{primary,secondary}-container` tokens missing | Was already correct in live — spec 0165 §2.1 became a no-op |
| 3.B | Identity-chip backgrounds too subtle | Shipped via spec 0165 §2.2 |
| 3.C | Activity chip invisible after iter-5 surface bump | Shipped via spec 0165 §2.3 |
| 3.D | Phase header pcode redundant | Shipped via spec 0164 §2.2 |
| 3.E | Cost precision drift | Shipped via spec 0165 §2.5 (2-decimal `fmtCost2`) |
| 3.F | `turn [object object]` rendering bug | Defensive guard via spec 0166 §2.4; upstream fix via spec 0173 §2.2 |
| 3.G | DS §16 reference doesn't reflect live | Cumulatively caught up across specs 0164 / 0165 / 0166 |

## What the future spec should promote into live

The full set: every iter (1 → 13) **plus** the two user-flagged behavioural
fixes (T1 height parity, T2 click-to-unfold + cost precision). Per the user's
rule of thumb, the spec target is **the whole iteration canvas**, not a
filtered subset.

The promotion target lives in:
- `src/dual_research/ui/static/components.css` — live timeline CSS
- `design-system/assets/styles/composed-components.css` — DS authoritative copy
- `src/dual_research/ui/static/run-detail.jsx` — TimelineCard component + click handler binding
