---
kind: dev
spec: "0171"
slug: agent-input-single-column-with-agent-toggle
title: "Fix: Agent Input sub-tab renders two narrow cards causing horizontal scroll in split-pane modals"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 2
depends_on: []
complexity: S
created: 2026-05-22
queued_at: "2026-05-22T20:00:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: notion-specs-2205-claude-bug-1
promoted_from_draft: ""
---

# Spec 0171 — Fix: Agent Input sub-tab renders two narrow cards causing horizontal scroll in split-pane modals

> **Type:** bug  |  **Severity:** P1  |  **Affects:** v1.29.0 (current main), all viewports 1500–1799 px (default MacBook 14″/16″ and typical half-screen 27″ widths).
> **Bump:** PATCH — bug fix
> **Evidence:** Product-owner regression report on Notion page `Specs 2205 (AL)` Issue 1 → restated in `Specs 2205 (Claude)` Bug 1. Spec 0151 §3.1 attempted the fix and explicitly preserved the dual-card outer frame; the structural problem ("two columns inside an already-narrow column") survived. Reproduces deterministically on the deployed v1.29.0 app.

---

## 1. Reproduction

**Environment:** dual-research UI at HEAD = `a920172` (deployed v1.29.0). Viewport 1440×900 (default MacBook-class). Any run with at least one Phase 2 or Phase 4 per-agent turn.

**Steps:**

1. Open the dual-research app and navigate to any run-detail page.
2. Click any Phase 2 or Phase 4 per-agent turn card to open its full-view modal (the kind that mounts `NegotiateLeftPane`).
3. Click the **Agent Input** sub-tab inside the left pane (`sub === 'input'` branch at [`src/dual_research/ui/static/run-detail.jsx:5139`](src/dual_research/ui/static/run-detail.jsx)).

**Expected:** A single-column view rendering exactly the three-section canonical Agent Input panel — `System prompt` / `User prompt` / `Derived inputs` — identical anatomy to the single-pane modals `DocumentModal`, `PreflightResponseModal`, and `InputBriefModal`. All three already call `InputTabContent` → `PromptPiecesThreeSectionView frame="single"` at one column. No horizontal scrollbar at any viewport ≥ 1280 px.

**Actual:** Two per-agent cards (Claude on the left, GPT on the right) are stacked horizontally inside the already-narrow split-modal left pane. The cards are too narrow for their canonical three-section body; the modal grows a horizontal scrollbar at 1500–1799 px (MacBook 14″/16″ and typical half-screen 27″). The user has flagged this twice — pre- and post- spec 0151.

## 2. Root cause hypothesis

Two-pane consumer mounted inside a one-pane consumer surface, plus a too-aggressive media-query breakpoint:

- [`src/dual_research/ui/static/run-detail.jsx:5800`](src/dual_research/ui/static/run-detail.jsx) — `function AgentInputDualPane` renders two `<AgentInputPane>` columns side-by-side via a `<div className="agent-input">` wrapper.
- [`src/dual_research/ui/static/components.css:1193`](src/dual_research/ui/static/components.css) — `.agent-input { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }` declares the two-column layout, with [`components.css:1212`](src/dual_research/ui/static/components.css) collapsing to a single column **only** below 1499 px. On 1500–1799 px viewports the grid stays at `1fr 1fr` inside the already-narrow split-modal left pane.
- Spec 0151 §3.1 (already merged, [PR #173](https://github.com/Lexiz/dual-research/pull/173)) explicitly migrated the per-card body to share the canonical `PromptPiecesThreeSectionView` with `InputTabContent`, but kept the dual-card outer frame at [`run-detail.jsx:5813–5818`](src/dual_research/ui/static/run-detail.jsx). The body migration solved the inner rendering parity; the structural decision ("two columns inside a column") was not revisited.

`AgentInputDualPane` is mounted once at [`run-detail.jsx:5139`](src/dual_research/ui/static/run-detail.jsx): `{sub === 'input' && <AgentInputDualPane item={item} run={run} />}`. No other surface consumes it. `AgentInputPane` has no external consumers either (only used as the dual-pane's per-column wrapper).

## 3. Fix

Single-column rewrite of the consumer, deletion of the now-unused dual-pane primitive and its CSS:

1. **Add a single-column wrapper component** `AgentInputSingleColumn` adjacent to `NegotiateLeftPane` in [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx). It renders:
   - A two-option segmented selector at the top of the pane labelled `Claude · GPT`. Uses the existing `.fgroup` segmented-control markup (per [`design-system/SPEC.md` §3.13](design-system/SPEC.md), table-row "Tab" → "M3 secondary as solid segmented pill (used for theme + density + agent + status filters)"). Default option = `item.agent` when truthy, else `claude`. Local state via `React.useState`; no persistence required (per-modal lifetime is fine).
   - A single `<PromptPiecesThreeSectionView frame="single" turnKey={selectedTurnKey} />` underneath. `selectedTurnKey` resolves against the existing paired-turn lookup at [`run-detail.jsx:5802–5811`](src/dual_research/ui/static/run-detail.jsx): if the chosen agent matches `item.agent`, use `item.turnKey`; otherwise look up the paired turn via `buildTimeline(run)`.

2. **Swap the consumer call** at [`run-detail.jsx:5139`](src/dual_research/ui/static/run-detail.jsx): replace `<AgentInputDualPane item={item} run={run} />` with `<AgentInputSingleColumn item={item} run={run} />`.

3. **Delete the now-unused primitives** at [`run-detail.jsx:5800–5841`](src/dual_research/ui/static/run-detail.jsx): `function AgentInputDualPane` and `function AgentInputPane`. Confirm via repo-wide grep that no other site imports either symbol before deletion.

4. **Delete the two-column CSS block** in both stylesheets in one commit (per CLAUDE.md project rule that the DS-canonical and live copies must stay in sync):
   - [`src/dual_research/ui/static/components.css:1189–1212`](src/dual_research/ui/static/components.css) — the `.agent-input`, `.agent-input__pane`, `.agent-input__pane--a`, `.agent-input__pane--b`, `.agent-input__head`, `.agent-input__body` rules and the 1499 px media query.
   - The mirror rules in [`design-system/assets/styles/composed-components.css`](design-system/assets/styles/composed-components.css) if present (verify via grep before deleting).

5. **Keep `PromptPiecesThreeSectionView`, `InputTabContent`, and the single-pane consumers (`DocumentModal`, `PreflightResponseModal`, `InputBriefModal`) untouched.** This spec is purely the structural fix at one consumer site.

### 3.1 Design-system citations

- **Segmented selector primitive:** [`design-system/SPEC.md` §3.13](design-system/SPEC.md) (Tab → solid segmented pill variant). The same `.fgroup` markup spec 0167 §2.1 kept after weighing the rename (line 344: "the existing `.fgroup` markup already provides the spec's visual contract").
- **Three-section panel primitive:** [`design-system/SPEC.md` §3.18](design-system/SPEC.md) `CollapsibleSection` — already used by `InputTabContent` consumers via `PromptPiecesThreeSectionView`. No new DS work.
- **Modal scroll surface:** the outer `.dr-modal-body` is the single scroll surface inside the modal (per the spec 0110/0113 comment at [`components.css:1280–1283`](src/dual_research/ui/static/components.css)); nested per-accordion scrollbars are explicitly forbidden. This spec must not introduce a new inner scroll container.

## 4. Regression-prevention test

A test that fails before this fix and passes after:

- [ ] **Vitest DOM test** in `tests/ui/static/` — mount `NegotiateLeftPane` with `sub='input'` against a Phase 2 turn fixture at viewport 1440×900. Assert:
  - Exactly one element matching `.cs-title` text "System prompt" (proves the three-section panel rendered, and only once — no dual-pane duplication).
  - Exactly one segmented selector with options "Claude" and "GPT" exists at the top of the pane.
  - `modalScroller.scrollWidth <= modalScroller.clientWidth` (proves no horizontal overflow).

- [ ] **Screenshot capture** of the Agent Input sub-tab on a Phase 2 turn modal at 1440 px, embedded in the spec handoff in a before/after pair against the live pre-fix capture, demonstrating pixel parity with `InputTabContent` consumers (`DocumentModal` etc.).

## 5. Blast radius

- `AgentInputDualPane` consumers: **one** site, [`run-detail.jsx:5139`](src/dual_research/ui/static/run-detail.jsx). Repo-grep confirms zero other usages.
- `AgentInputPane` consumers: zero outside `AgentInputDualPane` itself.
- `.agent-input*` CSS consumers: only the `AgentInputDualPane` JSX (verified via grep over `src/dual_research/ui/static/`).
- `PromptPiecesThreeSectionView` consumers: `InputTabContent` (single-pane modals) — **unchanged** by this spec; same `frame="single"` prop value already flowing through.
- Net diff: ~30 lines added (new `AgentInputSingleColumn`), ~45 lines removed (the two deleted functions + CSS block). Single consumer call-site swap.

## 6. Out of scope

- Bug 2 (Critique cards render literal `**` markdown and re-show the cryptic compound ID) — separate spec.
- Bug 3 (Expanding section chevrons reveals empty body across full-view modals) — separate spec.
- Bug 4 (Critique cards still diverge from the design system despite the 0151 rework) — separate spec.
- Bug 5 (Consumption tab's unfolded card does not match Design System V2) — separate spec.
- Bug 6 (All-Runs table reports `running` for runs that died days ago) — separate spec.
- Any styling refinement of `PromptPiecesThreeSectionView` itself (badge density, header typography, chevron motion) — out of scope here.
- Mobile / sub-1280 px responsive behaviour of the new segmented selector — desktop-only fix; sub-1280 px responsive audit is a separate initiative.
- Re-introducing a dual-agent side-by-side primitive for any other surface — if a future surface genuinely needs side-by-side agents, that primitive lands in its own spec with proper responsive rules. Not this one.

## 7. Risks

- **Default-agent guess wrong.** If the segmented selector defaults to a different agent than the user expected, they land on the "wrong" agent on first open. **Mitigation:** default = `item.agent` when present (the most common case — a turn modal is opened against a specific agent's turn). Falls back to `claude` only when no agent context exists.
- **Stale paired-turn lookup.** `buildTimeline(run)` is already memoised at [`run-detail.jsx:5801`](src/dual_research/ui/static/run-detail.jsx). The new component reuses the same memo; risk is low.
- **Some user actually wanted the dual view.** Mitigation: the canonical full-view single-pane modals (`DocumentModal` etc.) already use the single-column three-section panel exclusively; this spec brings the split-pane consumer onto the same anatomy. The product-owner directive on the Notion bug page is explicit ("should not be reintroduced inside a split-pane modal whose left pane is already narrow").
- **CSS regression on an undiscovered consumer.** Mitigated by repo-grep prior to deletion, plus the vitest assertion confirming the three-section panel renders correctly post-deletion.
