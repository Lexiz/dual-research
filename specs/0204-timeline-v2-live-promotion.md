---
kind: dev
spec: "0204"
slug: timeline-v2-live-promotion
title: Timeline pane V2 — promote workshop lock to live (T1 card height, T2.a click/modal split, T2.b cost precision parity)
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: ["0164", "0165", "0166", "0173"]
complexity: M
created: 2026-05-24
queued_at: "2026-05-24T00:29:09Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0204 — Timeline pane V2 → live promotion (T1 card height, T2.a click/modal split, T2.b cost precision parity)

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** 0164, 0165, 0166, 0173
> **Bump:** MINOR — promotes a user-visible behaviour set (cards unfold in place; explicit "Open full view" opens the modal; consistent 2-decimal cost rendering across the timeline pane) plus a small pixel-target correction on collapsed card height.
> **Evidence:** [`prototypes/timeline-iteration/V2-SNAPSHOT.md`](../prototypes/timeline-iteration/V2-SNAPSHOT.md) (canonical reference); Notion page [Critique & Timeline](https://www.notion.so/36999f3e507f8083b551f2c8fcbe46d3) (2026-05-23) Timeline section; [NOTES.md](../prototypes/timeline-iteration/NOTES.md) (workshop iter record); [`proposed.html`](../prototypes/timeline-iteration/proposed.html) (pixel target).

---

## 1. Context

The timeline pane in the live app drifts from the V2 design captured in the 2026-05-22 workshop on three counts that the user flagged in the [Critique & Timeline](https://www.notion.so/36999f3e507f8083b551f2c8fcbe46d3) Notion page (2026-05-23). Otherwise the V2 lock is shipped — [V2-SNAPSHOT.md §3](../prototypes/timeline-iteration/V2-SNAPSHOT.md#3-iter-1iter-13-shipped-audit) verifies every workshop iter (iter 1-13) and drift item (3.A-3.F) against current code on 2026-05-24 and finds them all in place via the four prior shipping specs ([0164](0164-timeline-pane-card-chrome-and-phase-header.md), [0165](0165-timeline-pane-chip-polish-and-token-drift.md), [0166](0166-timeline-pane-system-error-chips-and-live-state.md), [0173](0173-drain-deferrals-from-0166-0167-0168.md)). The only outstanding drift item, 3.G (DS §16 catch-up), is deferred per [§5](#5-out-of-scope).

The promotion delta in this spec is exactly the three user-flagged items — T1, T2.a, T2.b — each scoped to the timeline pane and verified against current code in the source-traceability table below.

### Source-artifact traceability

| Source item | Source quote/ref | Spec section |
|---|---|---|
| T1 — collapsed card head too tall | [V2-SNAPSHOT §2 T1](../prototypes/timeline-iteration/V2-SNAPSHOT.md#2-user-flagged-discrepancies-t1-t2a-t2b) — "live is `padding: 10px 12px` (~42 px head) where workshop is `padding: 6px 12px` (~34 px head)" + Notion Timeline §1 "the actual height of the cards in their collapsed state … on the live site they're a little bit higher … the iteration one is correct" | §2.1 |
| T2.a — head click also opens modal | [V2-SNAPSHOT §2 T2.a](../prototypes/timeline-iteration/V2-SNAPSHOT.md#2-user-flagged-discrepancies-t1-t2a-t2b) — single `openId` state drives both `.is-open-expanded` and `<ArtifactModal />` + Notion Timeline §2 "the moment you click on it, it immediately unfolds itself but it also opens the full view mode" | §2.2 |
| T2.b — cost not 2dp everywhere in timeline pane | [V2-SNAPSHOT §2 T2.b](../prototypes/timeline-iteration/V2-SNAPSHOT.md#2-user-flagged-discrepancies-t1-t2a-t2b) — `TimelineAgentPill` uses `fmt.costShort` which lacks the `<$0.01` sub-cent fallback `fmtCost2` has + Notion Timeline §2 "the total cost in the batch should be rounded to two decimals after the comma" | §2.3 |
| Iters 1-13 (shipped) | [V2-SNAPSHOT §3](../prototypes/timeline-iteration/V2-SNAPSHOT.md#3-iter-1iter-13-shipped-audit) — every iter ✓ verified against current code | §5 (verified-shipped, not re-shipped here — and iter 4b is workshop-only) |
| Drift 3.A-3.F (shipped) | [V2-SNAPSHOT §4](../prototypes/timeline-iteration/V2-SNAPSHOT.md#4-drift-items-3a3g-shipped-audit) — six of seven drift items ✓ verified | §5 (verified-shipped, not re-shipped here) |
| Drift 3.G (unshipped) | [V2-SNAPSHOT §4](../prototypes/timeline-iteration/V2-SNAPSHOT.md#4-drift-items-3a3g-shipped-audit) — DS §16 still renders pre-marker / pre-chip-cluster anatomy | §5 (deferred to follow-up DS-catch-up spec) |
| Notion Timeline §1 (T1) | Notion [Critique & Timeline](https://www.notion.so/36999f3e507f8083b551f2c8fcbe46d3) Timeline section, item 1 | §2.1 |
| Notion Timeline §2 click (T2.a) | Notion Timeline section, item 2 first half | §2.2 |
| Notion Timeline §2 cost (T2.b) | Notion Timeline section, item 2 last sentence | §2.3 |

---

## 2. Proposed change

Three coupled deltas. All three files in the same commit per [CLAUDE.md §Design system](../CLAUDE.md#design-system) (DS authoritative copy + live-app copy stay in sync).

### 2.1 T1 — collapsed card head 42 px → 34 px

**Current.** [components.css:2709-2711](../src/dual_research/ui/static/components.css#L2709):
```css
.qthread.tl-thread > .tl-card-head {
  padding: 10px 12px;
}
```
With 22 px chip content, head clientHeight ≈ 42 px.

**Target.** Workshop iter-5 [`proposed.html`](../prototypes/timeline-iteration/proposed.html) lines 249-254:
```css
.tl-thread > .tl-card-head {
  padding: 6px 12px;
  gap: 6px;
  background: transparent;
  border: 0;
}
```
With the same 22 px chip content, head clientHeight ≈ 34 px (chips 22 px + 12 px total vertical padding). The `gap: 6px` is also part of the iter-5 lock — `.qthread.tl-thread > .tl-card-head` currently inherits the default `.tl-card-head` gap from [components.css:1007-1018](../src/dual_research/ui/static/components.css#L1007); audit the cascade and set `gap: 6px` explicitly on the scoped selector so the workshop value isn't accidentally overridden. `background: transparent` and `border: 0` are already inherited correctly from the card-level chrome — no need to repeat them (the workshop's `!important` resets are workshop-only).

**Action.** Shrink padding on `.qthread.tl-thread > .tl-card-head` from `10px 12px` to `6px 12px` and explicitly set `gap: 6px`. Mirror in the DS authoritative copy at `design-system/assets/styles/composed-components.css` in the same commit (add the rule if it doesn't already mirror — current state per [V2-SNAPSHOT §6](../prototypes/timeline-iteration/V2-SNAPSHOT.md#6-promotion-target-files-all-three-updated-in-the-same-commit)).

The expanded-card head padding (when `.is-open-expanded` is set on `.qthread.tl-thread`) at [components.css:2704-2707](../src/dual_research/ui/static/components.css#L2704) stays as-is — the workshop's iter-5 expanded state keeps the same `padding: 6px 12px` head padding (the lift comes from the body, not the head padding bump), so the same shrunk value applies in both states.

### 2.2 T2.a — split inline-expand from modal-open

**Current.** [run-detail.jsx:816](../src/dual_research/ui/static/run-detail.jsx#L816):
```jsx
const [openId, setOpenId] = React.useState(null);
…
const openItem = items.find((i) => i.id === openId) || null;
```
[Line 934](../src/dual_research/ui/static/run-detail.jsx#L934) drives the inline expansion: `isOpen={openId === item.id}`. [Lines 949-955](../src/dual_research/ui/static/run-detail.jsx#L949) drive the modal: `{tab === 'conversation' && openItem && <ArtifactModal item={openItem} … />}`. [Line 935](../src/dual_research/ui/static/run-detail.jsx#L935) `onToggle={() => setOpenId(openId === item.id ? null : item.id)}` is the single callback that the card-head click ([line 1233](../src/dual_research/ui/static/run-detail.jsx#L1233)) and the "Open full view" button ([line 1333](../src/dual_research/ui/static/run-detail.jsx#L1333)) both call — so clicking the head opens both the inline body AND the modal simultaneously.

**Target.** Two independent state variables:

```jsx
// Inline expansion — drives `.is-open-expanded` class + `data-expanded` attribute.
const [expandedId, setExpandedId] = React.useState(null);
const toggleExpanded = (id) => setExpandedId(expandedId === id ? null : id);

// Modal — drives <ArtifactModal /> mount.
const [openId, setOpenId] = React.useState(null);
const openItem = items.find((i) => i.id === openId) || null;
```

Rewire the TlTurnRow call site at [run-detail.jsx:930-936](../src/dual_research/ui/static/run-detail.jsx#L930) so:

- `isOpen={expandedId === item.id}` (was: `openId === item.id`)
- `onToggle={() => toggleExpanded(item.id)}` (was: `setOpenId(…)`)
- New prop `onOpenModal={() => setOpenId(item.id)}` passed down for the "Open full view" button to consume.

Inside `TlTurnRow` ([run-detail.jsx:1230-1349](../src/dual_research/ui/static/run-detail.jsx#L1230)):

- The article's `onClick={onToggle}` and `onKeyDown` Enter/Space handler stay calling `onToggle` (inline expand only).
- Add `data-expanded={isOpen ? 'true' : 'false'}` on the `<article>` so BDD assertions can observe the inline state without parsing the className.
- Change the "Open full view" button at [line 1333](../src/dual_research/ui/static/run-detail.jsx#L1333) from `onClick={(e) => { e.stopPropagation(); onToggle(); }}` to `onClick={(e) => { e.stopPropagation(); onOpenModal(); }}`. The button no longer toggles the inline state; it only opens the modal. Clicking the button while the card is collapsed leaves the inline state collapsed (the modal is the focused surface).

The `ArtifactModal` mount condition at [line 949](../src/dual_research/ui/static/run-detail.jsx#L949) stays as-is (`tab === 'conversation' && openItem && …`) — `openItem` now derives from the renamed `openId` whose only writer is the "Open full view" button.

**Effect on existing keyboard / focus behaviour.** Enter/Space on the card head continues to toggle inline expansion (no modal). To open the modal via keyboard, Tab into the expanded card's "Open full view" button and press Enter. This matches the workshop's interaction model — the modal is an opt-in "focused reading" affordance, not a side-effect of card inspection.

**No CSS change required.** The existing `.qthread.tl-thread.is-open-expanded` rule at [components.css:2699](../src/dual_research/ui/static/components.css#L2699) keys off the class name set by the existing `isOpen` ternary; that ternary now reads from `expandedId` instead of `openId` but the class-set logic is unchanged.

### 2.3 T2.b — TimelineAgentPill cost uses `fmtCost2` semantics

**Current.** [run-detail.jsx:185](../src/dual_research/ui/static/run-detail.jsx#L185) inside `TimelineAgentPill`:
```jsx
costFormatter={fmt.costShort}
```
[shared.jsx:658](../src/dual_research/ui/static/shared.jsx#L658): `costShort: (n) => $${n.toFixed(2)}`. 2-decimal but no `<$0.01` sub-cent fallback — values like `$0.0034` render as `$0.00`.

**Target.** Use `fmtCost2` from [run-detail.jsx:2720](../src/dual_research/ui/static/run-detail.jsx#L2720), which already implements both the 2-decimal formatting AND the `<$0.01` sub-cent guard. Swap the prop:
```jsx
costFormatter={fmtCost2}
```

The expanded turn-card action chip at [run-detail.jsx:1344](../src/dual_research/ui/static/run-detail.jsx#L1344) already uses `fmtCost2` ✓ (shipped by [spec 0165 §2.5](0165-timeline-pane-chip-polish-and-token-drift.md)). No other cost displays exist inside the timeline pane (confirmed by grep audit captured in [V2-SNAPSHOT §2 T2.b note](../prototypes/timeline-iteration/V2-SNAPSHOT.md#2-user-flagged-discrepancies-t1-t2a-t2b)). With this one swap, every cost display rooted in `.rdvc__pane Timeline` renders via `fmtCost2`.

`fmt.costShort` remains in the codebase for the Summary tab [run-detail.jsx:8210,8619-8620](../src/dual_research/ui/static/run-detail.jsx) and the run-list aggregate [run-list.jsx:208](../src/dual_research/ui/static/run-list.jsx); those surfaces are outside the timeline pane and intentionally untouched per [§5](#5-out-of-scope).

---

## 3. User stories & acceptance criteria

### 3.1 — User stories

> As a **researcher**, I want a timeline card I click on to unfold in place so I can scan the body inline without losing context, so that I can read multiple cards in a single phase without each click yanking me into a full-screen modal.

> As a **researcher**, I want a clearly-labelled "Open full view" button inside the expanded card so I can explicitly choose to enter the focused side-by-side / document modal when I want to read a turn in full, so that the modal is a deliberate opt-in instead of a noisy side-effect of card inspection.

> As a **researcher**, I want sub-cent agent costs (`$0.0034`) to render as `<$0.01` instead of being silently rounded to `$0.00` in the timeline header agent strip, so that I can tell the difference between "this agent hasn't spent anything yet" (`$0.00`) and "this agent has spent a small but non-zero amount" (`<$0.01`).

> As a **viewer**, I want collapsed timeline turn cards to render at the workshop-locked compact height so that I can scan more turns at once without the pane padding overwhelming the content.

### 3.2 — Acceptance scenarios (BDD)

> **Scenario 1: T1 collapsed card head height matches workshop iter-5 lock.**
> GIVEN the run-detail view is rendered for a run with at least one P2 turn card AND no card has been clicked
> WHEN the page settles and the first collapsed `.qthread.tl-thread` card is measured
> THEN its `.tl-card-head` clientHeight equals 34 ± 1 px (chips 22 px + `padding: 6px 12px` → 34 px nominal)

> **Scenario 2: T2.a head click unfolds in place AND does NOT open the modal.**
> GIVEN a collapsed `.qthread.tl-thread` card with `data-expanded="false"` AND no `<ArtifactModal />` mounted
> WHEN the user clicks anywhere inside the card's `<header class="tl-card-head">` (and not on a nested chip's own click handler)
> THEN the article gains `data-expanded="true"` AND class `is-open-expanded` AND the `.tl-thread__body` is visible AND no `<ArtifactModal />` is mounted in the DOM

> **Scenario 3: T2.a "Open full view" button opens the modal AND does NOT toggle the inline state.**
> GIVEN an expanded `.qthread.tl-thread` card with `data-expanded="true"` AND no `<ArtifactModal />` mounted
> WHEN the user clicks the `.tl-thread__actions button` labelled "Open full view"
> THEN `<ArtifactModal />` is mounted AND the article's `data-expanded` attribute is still `"true"` (button click is independent of inline expansion state)

> **Scenario 4: T2.a clicking "Open full view" on a collapsed card opens the modal WITHOUT inline-expanding the card.**
> GIVEN a collapsed `.qthread.tl-thread` card with `data-expanded="false"` AND its expanded-card actions block visible via test setup (e.g. the test pre-expands then collapses to verify the independence)
> WHEN the user dispatches a click on the `.tl-thread__actions button.md-btn--tonal` "Open full view" directly
> THEN `<ArtifactModal />` mounts AND `data-expanded` remains `"false"`

> **Scenario 5: T2.b TimelineAgentPill renders sub-cent cost as `<$0.01`.**
> GIVEN a run whose Claude agent has `run.agents.claude.cost === 0.003` (USD) AND the timeline pane is on the Conversation tab
> WHEN `TimelineAgentPill` inside `.tl__head` renders
> THEN the cost slot inside `.as.is-a.in-header` displays `<$0.01` (NOT `$0.00`)

> **Scenario 6: T2.b TimelineAgentPill renders ≥ 1 cent cost as `$X.XX`.**
> GIVEN a run whose GPT agent has `run.agents.gpt.cost === 0.234` (USD)
> WHEN `TimelineAgentPill` inside `.tl__tabs` renders
> THEN the cost slot inside `.as.is-b.in-header` displays `$0.23` (2-decimal precision, matching `fmtCost2`)

> **Scenario 7: Expanded-card cost chip unchanged from spec 0165 baseline.**
> GIVEN an expanded turn card whose `cost === 0.0312` (USD)
> WHEN the expanded `.tl-thread__actions` row renders
> THEN the cost chip displays `$0.03` (the existing `fmtCost2` behaviour — sanity-check that T2.b doesn't regress what 0165 §2.5 shipped)

---

## 4. Data / Schema deltas

None. All three deltas are presentation-layer (CSS + JSX) and do not change the run-data schema, the dashboard event sidecar, the spec-frontmatter contract, or any persisted state.

---

## 5. Out of scope

- **Drift 3.G — `Design System v2.html` §16 catch-up.** The rendered HTML reference still shows the pre-marker / pre-chip-cluster anatomy ([V2-SNAPSHOT §4](../prototypes/timeline-iteration/V2-SNAPSHOT.md#4-drift-items-3a3g-shipped-audit)). Out of scope for the V2-promotion spec — deferred to a follow-up DS-catch-up spec drafted post-merge (no number assigned yet). Rationale: the user-facing pixels read off `composed-components.css` + `components.css`, not the rendered HTML reference; 3.G is documentation drift, not user-visible drift.
- **`fmtCost1` call-sites outside the timeline pane.** Consumption tab cost rows ([run-detail.jsx:2990,3110,3189,3213,3226,3253,3261,3266](../src/dual_research/ui/static/run-detail.jsx)) and run-detail header `CostBadge` / `ReconciliationChip` 4-decimal `fmt.cost` ([run-detail.jsx:516,564,576,584,602,611,659](../src/dual_research/ui/static/run-detail.jsx)) stay as they are. [Spec 0165 §2.5](0165-timeline-pane-chip-polish-and-token-drift.md) explicitly preserves the audit precision in those surfaces.
- **`fmt.costShort` call-sites outside the timeline pane.** Summary tab ([run-detail.jsx:8210,8619-8620](../src/dual_research/ui/static/run-detail.jsx)) and run-list aggregate ([run-list.jsx:208](../src/dual_research/ui/static/run-list.jsx)) keep `fmt.costShort` — different surfaces, different rendering budgets.
- **Critique pane V2 promotion.** Covered by the parallel sibling spec authoring at [`prototypes/critique-iteration/V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md). The user's promotion brief explicitly excludes critique-side concerns (Σ Summary, Resolved split, item-card chrome) from this spec.
- **Canvas skill regeneration logic.** Separate downstream spec.
- **Iter 4b workshop wrapper.** Workshop-only side-by-side dark/light renderer; never ships ([NOTES.md §2.8](../prototypes/timeline-iteration/NOTES.md)).
- **Re-shipping iters 1-13 or drift 3.A-3.F.** All verified ✓ shipped against current code per [V2-SNAPSHOT §3](../prototypes/timeline-iteration/V2-SNAPSHOT.md#3-iter-1iter-13-shipped-audit) and [§4](../prototypes/timeline-iteration/V2-SNAPSHOT.md#4-drift-items-3a3g-shipped-audit). The §1 traceability table routes those rows here so the source-artifact audit is explicit. Specifically: iter 1 (0164 §2.2 ✓), iter 2 (0164 §2.2 ✓), iter 3 (0166 §2.3+§2.4 ✓), iter 4 + iter 5 (0164 §2.3+§2.4 ✓), iter 4b (workshop-only, never ships), iter 6 (0165 §2.1 ✓), iter 7 (0165 §2.1+§2.2 ✓), iter 8 (0164 §2.4+§2.2 ✓), iter 9 (0165 §2.3 ✓), iter 10 (0165 §2.4+§2.5 ✓), iter 11 (0166 §3 + 0173 §2.1 ✓), iter 12 (0166 §3 ✓), iter 13 (0164 §2.5 ✓); drift 3.A (0165 §3.A ✓), 3.B (0165 §2.1 ✓), 3.C (0165 §2.4 ✓), 3.D (0164 §2.2 ✓), 3.E (0165 §2.5 ✓; T2.b extends to the agent strip), 3.F (0166 §2.3+§2.4 ✓).

---

## 6. Test plan

- [ ] **Same-commit invariant.** `git diff --name-only HEAD~1..HEAD` on the implementing branch lists both `src/dual_research/ui/static/components.css` AND `design-system/assets/styles/composed-components.css` (T1 lands in both files); also lists `src/dual_research/ui/static/run-detail.jsx` (T2.a + T2.b). Per [CLAUDE.md §Design system](../CLAUDE.md#design-system) the DS/live mirror is a same-commit invariant.
- [ ] **T1 BDD scenario 1** passes: collapsed `.qthread.tl-thread > .tl-card-head` measured clientHeight equals 34 ± 1 px on the live app `https://dual-research-alex.fly.dev/#/runs/<a P2-bearing run>` AND on `localhost:6173/#/runs/<same>`.
- [ ] **T2.a BDD scenarios 2, 3, 4** pass as Playwright tests OR as a manual verification (using `preview_click` + `preview_snapshot` on a P2 card): head click sets `data-expanded="true"` and does NOT mount `<ArtifactModal />`; "Open full view" button click mounts `<ArtifactModal />` independently of `data-expanded`.
- [ ] **T2.b BDD scenarios 5, 6, 7** pass: feed a synthetic `run.agents.claude.cost = 0.003` payload through the dev server and confirm the agent-strip cost slot renders `<$0.01`; feed `0.234` and confirm `$0.23`; expanded action chip with `cost = 0.0312` still renders `$0.03`.
- [ ] **No console errors / no React warnings** in browser devtools after the change is deployed; specifically no "unused-prop" warning from the new `onOpenModal` prop introduced by T2.a.
- [ ] **Modal keyboard path.** Tabbing into an expanded card, focusing the "Open full view" button, and pressing Enter still opens the modal (regression check for T2.a's button rewiring).
- [ ] **Inline-expand keyboard path.** Tabbing onto a collapsed `.qthread.tl-thread` article (which has `tabIndex={0}` and `role="button"`) and pressing Enter still toggles inline expansion via `data-expanded`, with no modal mount (regression check that the keyboard handler keeps calling `onToggle`, not `onOpenModal`).
- [ ] **CHANGELOG entry** under the new `## [X.Y.Z]` heading directly under `## [Unreleased]` lists the three deltas (T1 / T2.a / T2.b) with a one-liner each and links back to this spec.
- [ ] **DS gate.** [`design-system/SPEC.md`](../design-system/SPEC.md) §4.4 Timeline pane gets a one-line note documenting the 34 px collapsed card-head target AND the explicit click-vs-modal separation, so the DS reference stays the source of truth.

---

## 7. Risks

- **T2.a regression — modal users.** Users habituated to the current "card click opens everything" flow may briefly experience the new behaviour as "the modal stopped working." Mitigation: the "Open full view" button is already labelled — discoverability is high. The expanded card's body content matches what the modal would show for most turns, so the modal stops being mandatory rather than disappearing. If post-deploy feedback flags this, a follow-up spec can add a "double-click head to open modal" affordance — does NOT need to be designed in now.
- **T2.a state-split off-by-one.** Splitting one state into two is a class of bug that typically surfaces as "modal opens but inline doesn't" or vice-versa on edge cases (rapid clicks, route changes, tab switches). Mitigation: BDD scenarios 2-4 cover the three independent paths; the `useEffect` at [run-detail.jsx:820-822](../src/dual_research/ui/static/run-detail.jsx#L820) that resets `openId` on run/tab change must also reset `expandedId` — the spec implementer must extend that effect (cited explicitly here so the implementer doesn't miss it).
- **T1 over-shrink in unusual content.** If a turn's identity chip stack overflows the 22 px nominal height (e.g. a card with both a violation chip and a long activity label), the 6 px vertical padding may visually cramp. Mitigation: `.tl-card-head` uses `display: flex; align-items: center` so taller content auto-expands the head; the 34 px is the *minimum* height for chip-only content, not a fixed cap.
- **T2.b `fmtCost2` import wiring.** `fmtCost2` is defined at [run-detail.jsx:2720](../src/dual_research/ui/static/run-detail.jsx#L2720) and `TimelineAgentPill` is defined at [line 152](../src/dual_research/ui/static/run-detail.jsx#L152) — both in the same file, so no import wiring needed. Mitigation: the spec implementer must NOT lift `fmtCost2` into `shared.jsx` as a "cleanup" — that's out of scope and risks circular dep with the run-list / dashboard surfaces.
- **DS/live drift.** Standard same-commit hazard. Mitigation: §6's first test-plan checkbox.
- **Race with parallel critique-V2 spec (resolved at queue time).** Critique V2 landed as 0203 just before this push and this timeline spec was originally committed as 0203 too (the `/spec-queue` push fast-forwarded over critique's commit instead of triggering the retry loop). Renumbered to 0204 in a follow-up commit on `main`. `/dev-next` picks 0203 (critique) first, then 0204 (timeline). No file-level conflict expected between the two specs — different selectors / components.
