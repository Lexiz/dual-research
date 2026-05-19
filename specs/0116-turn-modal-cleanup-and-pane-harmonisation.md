---
spec: 0116
title: Turn / Cross-review modal cleanup + Timeline-Critique pane visual harmonisation
label: bug
version-bump: NONE
status: proposed
target-version: "next-release (1.1.x)"
created: 2026-05-20
pr: ""
---

# Spec 0116 — Turn modal cleanup + Timeline-Critique pane harmonisation

> Ship bucket: **Composed**
> Depends on: **0085, 0098, 0101, 0111, hotfix sourcerow-duplicate (#125)**
> Complexity: **S–M** (5 sub-changes, all frontend, no backend, no migrations).
> Targeted version bump: **NONE** — CHANGELOG entry under `[Unreleased]`; version + cache-bust roll into the next release per current project state.

## 1. Context

Source: [Notion · Known issues v2](https://www.notion.so/Known-issues-v2-36599f3e507f80a8ad5fdb26b143a695) — final two outstanding issues (8 + 10) plus two screenshot-driven typographic / spacing harmonisation requests filed during spec-0116 drafting.

This is the FOURTH and FINAL spec of the Known issues v2 series. After this ships, the entire Notion backlog from 2026-05-19 is closed:

- 0111 (merged) — Critique cards: bucket / scroll / badges / height (Notion 1, 2, 4, 5).
- 0112 (merged) — Agent strip text overflow (Notion 3).
- 0113 (merged) — Full-view modal vertical fill + accordion cap (Notion 6, 7, 9).
- **0116 (this spec)** — Turn / cross-review modal cleanup + pane harmonisation (Notion 8, 10 + two screenshot-driven items).

Spec numbers 0114, 0115, 0117, 0118 are reserved for the deep-research-protocol / artifact-naming / consumption-and-cost-tracking work shipped or in flight in parallel.

### Notion Issue 8 — Turn modal (Phase 2 negotiate)

User report: the Phase 2 turn modal has noise at the top — a five-cell phase stepper (Preflight · Parallel draft · Negotiate plus · Converged draft · Cross review) that "we can remove… that's just noise." Inside, the Agent Input · Original view shows two columns both labelled "Research brief," which is confusing — on Claude's turn 1 the user expects: LEFT = ChatGPT's research plan (the actual input fed to Claude), RIGHT = Claude's questions about it.

### Notion Issue 10 — Cross-review modal (Phase 4)

Same modal component (`NegotiateReviewModal` handles both Phase 2 and Phase 4), same noise, same confusing default. Plus a substantive data-correctness question: *"Is Phase 4 cross-review actually being fed the Research brief instead of the Converged Draft?"*

### Data-correctness investigation

Orchestrator code, definitively:

- **Phase 2 turn N** (`src/dual_research/orchestrator/phase2.py:172` + `protocol/prompts.py:266`): prompt = `Brief + own Phase 1 draft + other's Phase 1 draft + ALL prior Phase 2 turns`. Brief inlined; bulk of payload is the negotiation history.
- **Phase 4 turn N** (`src/dual_research/orchestrator/phase4.py:169-170` + `protocol/prompts.py:616-617`): prompt = `Brief + Current draft + ALL prior Phase 4 review turns`. The **brief is appended as reference**; the **primary artifact under review is the Converged Draft**:
  ```python
  + _inline_section("Brief", brief_content)
  + _inline_section("Current draft", draft_content)
  ```

**Conclusion: no workflow bug.** The orchestrator is correct. The user's data-correctness concern was caused entirely by a misleading UI default (the modal lands on a tab that flattens the composite prompt into two agent-by-agent columns, both starting with "Research brief"). This spec fixes the UI default; no backend change is needed.

### Screenshot-driven items

- **Phase header size**. Left: `.tl-phase__name { font-size: 13px }`. Right: `.crit-group__title { font: var(--md-title-m-size) ≈ 16px }`. Critique section header is heavier; user wants them equal — increase the left.
- **Card row spacing**. Left: `.tl-phase__body { gap: 8px }` and `.qthread.tl-thread { margin: 0 }` → 8 px effective. Right: `.crit-group__body { gap: 8px }` PLUS inline `style={{ marginBottom: 8 }}` on each `<article className="qthread">` (`shared.jsx:1117`) → 16 px effective. Drop the inline margin; both panes match at 8 px.

## 2. Proposed change

Five sub-changes:

### 2.1 — Remove the PhaseRail callsite (Notion 8 + 10)

Delete the `<PhaseRail run={run} />` JSX line from `NegotiateReviewModal` at `run-detail.jsx:4218`. Component definition at `~:712-732` preserved for any future caller.

### 2.2 — Default left-pane sub-tab to 'original' (Notion 8 + 10)

Change `React.useState('input')` to `React.useState('original')` in `NegotiateLeftPane` at `run-detail.jsx:4307`. The 'input' sub-tab remains one click away; we're only moving the default. `leftPaneTabsFor` already orders the 'original' chips so the first one is the most relevant artifact per phase (Phase 4 → Current draft; Phase 2 round ≥ 2 → Other's prior turn; Phase 2 round 1 → Other's draft).

### 2.3 — Document the data-correctness finding (Notion 10)

CHANGELOG entry names `phase4.py:169-170` + `prompts.py:616-617` so a reader can verify. No code change.

### 2.4 — Phase-header text size harmonisation

Bump `.tl-phase__name` (`components.css:2034`) from `font: var(--md-w-medium) 13px/1 var(--md-font-plain)` to `font: var(--md-w-medium) var(--md-title-m-size)/1.5 var(--md-font-plain)`. Matches `.crit-group__title`.

### 2.5 — Critique card-row spacing harmonisation

Remove the inline `style={{ marginBottom: 8 }}` from `<article className="qthread">` at `shared.jsx:1117`. Parent `gap: 8px` becomes the single source of card spacing.

**Audit.** Three `<QuestionThread>` callsites:

1. `renderItem` in `CritiquePhaseContent` — inside `.crit-group__body { gap: 8 }`. ✓
2. Summary "Highest-leverage" callsite — single card, no spacing concern. ✓
3. `DisagreementExplorer` — plain `<div>` without `gap`. Relies on the inline margin. **Compensating change**: switch its wrapper to `display: flex; flex-direction: column; gap: 8` and adjust the "Resolved" `GroupHeader`'s `marginTop` from 20 → 12 (12 + 8 gap = 20 total).

## 3. Files touched

- `src/dual_research/ui/static/run-detail.jsx`:
  - ~`:4218` — delete `<PhaseRail run={run} />`. § 2.1
  - ~`:4307` — `useState('input')` → `useState('original')`. § 2.2
  - ~`:7257-7272` — `DisagreementExplorer` wrapper → flex column + gap; `marginTop` 20 → 12. § 2.5
- `src/dual_research/ui/static/shared.jsx`:
  - ~`:1117` — remove `style={{ marginBottom: 8 }}` on `.qthread` article. § 2.5
- `src/dual_research/ui/static/components.css`:
  - `.tl-phase__name` (~`:2034`) — bump to `var(--md-title-m-size)/1.5`. § 2.4
- `CHANGELOG.md` — entry under `[Unreleased]`.

No backend. No new tokens. No new classes. No migrations. No version-or-cache-bust in this PR (per current project convention; rolls into the next release commit).

## 4. Acceptance criteria

- [ ] **§2.1** — `document.querySelectorAll('.phase-rail').length === 0` on any Phase 2 or Phase 4 turn modal.
- [ ] **§2.2** — Active left-pane sub-tab is "Original" on every Phase 2 / Phase 4 turn modal. First doc chip per phase: P4 → "Current draft" active; P2 r ≥ 2 → "Other's prior turn"; P2 r1 → "Other's draft".
- [ ] **§2.3** — CHANGELOG names `phase4.py:169-170` + `prompts.py:616-617`.
- [ ] **§2.4** — Computed `font-size` on `.tl-phase__name` equals computed `font-size` on `.crit-group__title`.
- [ ] **§2.5** — No `.qthread` element carries inline `margin-bottom`. Measured spacing between consecutive `.qthread` siblings is 8 px in both `.crit-group__body` and `.tl-phase__body`.
- [ ] `uv run pytest tests/ -q` → green.
- [ ] No modification to `pyproject.toml`, `src/dual_research/__init__.py`, or `index.html` cache-bust.

## 5. Out of scope

- The 'input' sub-tab itself (still works, still one click away).
- The `PhaseRail` component definition (preserved).
- Notion issues 1-7, 9 — shipped in 0111 / 0112 / 0113.
- Version bump + cache-bust — handled by next release commit per current project pattern.
- Backend.

## 6. Backend touched?

**no.** Pure frontend.
