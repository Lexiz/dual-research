---
kind: dev
spec: "0178"
slug: input-section-default-open-on-outer-expand
title: "Fix: three-section Input panel reveals empty body — drop inner per-piece default-collapse so one click on outer chevron shows content"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 8
depends_on: []
complexity: S
created: 2026-05-22
queued_at: "2026-05-22T22:00:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: bug-spec-batch-2205-claude
promoted_from_draft: ""
---

# Spec 0178 — Fix: three-section Input panel reveals empty body on first chevron click

> **Type:** bug  |  **Severity:** P1  |  **Affects:** every full-view modal that uses the Agent Input three-section panel — `InputBriefModal`, `PreflightResponseModal`, `NegotiateLeftPane` Input sub-tab, `DocumentModal`. Live since spec 0145 §5.4 (three-section grouping) layered the outer collapse on top of spec 0085's per-piece collapse without re-evaluating the inner default state. Spec 0151 §3.2 touched the adjacent empty-piece path but did not address this perception gap.
> **Bump:** PATCH — bug fix only; no schema, no API, no new component.
> **Evidence:** Notion bug-batch page "Specs 2205 (Claude)" Bug 3 (`https://www.notion.so/Specs-2205-Claude-36899f3e507f802a90f6df0566d9704b`). Anchor run for manual repro: `20260521-010637-dvs-backend-language-choice`. Symptom: user clicks the "System prompt" or "Derived inputs" chevron in any full-view input panel; the outer section opens but only a per-piece header row appears with no body — a second click on the inner chevron is required to see the actual prompt text.

---

## 1. Reproduction

**Environment.** Live app `https://dual-research-alex.fly.dev`, any run with a recorded input bundle (anchor run `20260521-010637-dvs-backend-language-choice` works). Viewport 1440 × 900 or wider. No browser flags. The bug is renderer-side and reproduces in every full-view modal.

**Steps.**

1. Navigate to the anchor run's detail page on the live app.
2. Open any full-view modal that exposes the three-section Agent Input panel — pick any:
   - Phase 0 brief card → opens `InputBriefModal`.
   - Phase 0 per-agent preflight card → opens `PreflightResponseModal`.
   - Phase 2 or Phase 4 per-agent turn card → opens the split-pane modal, click `NegotiateLeftPane`'s **Input** sub-tab.
   - Plan / draft document card → opens `DocumentModal`.
3. The panel renders three section headers: **System prompt** (closed), **User prompt** (open), **Derived inputs** (closed).
4. Click the chevron next to **System prompt**.

**Expected:** One click → the System Prompt section reveals its `system.task.input` (and any other `system.*`) piece bodies inline, fully visible as Markdown.

**Actual:** One click → the outer section expands → only the per-piece header row(s) (chevron + `system.task.input` label + char count) appear; the body content is hidden behind a second collapsed chevron. The user perceives this as "I clicked and got nothing." A second click on the inner per-piece chevron is required to see the prompt text.

Same failure repeats for **Derived inputs** whenever the turn carries `prior_turns.*` pieces (i.e., every Phase 2 and Phase 4 turn — those carry the prior-turn transcripts as derived state). **User prompt** is the one section that renders correctly on first open, because its outer group is `defaultOpen={true}` and `user_prompt.*` keys are not flagged by the inner-collapse heuristic. The Notion report lists all three section names; only System Prompt and Derived Inputs are reproducibly empty-on-first-click.

## 2. Root cause hypothesis

The panel has **two nested CollapsibleSection layers**, with the **inner** layer defaulting closed for `system.*` and `prior_turns.*` keys. The user clicks the outer chevron expecting one act of disclosure; the inner state hides the body anyway.

- **Outer per-section collapse.** [src/dual_research/ui/static/run-detail.jsx:6096](src/dual_research/ui/static/run-detail.jsx:6096) — `InputSectionGroup` wraps each of System / User / Derived. The three `defaultOpen` values are set at [src/dual_research/ui/static/run-detail.jsx:6027-6046](src/dual_research/ui/static/run-detail.jsx:6027) — `system: false`, `user_prompt: true`, `derived: false`.
- **Inner per-piece collapse.** [src/dual_research/ui/static/run-detail.jsx:6134](src/dual_research/ui/static/run-detail.jsx:6134) — `InputSection` wraps every piece (one system prompt, one prior-turn transcript, etc.) in its **own** `CollapsibleSection` ([src/dual_research/ui/static/shared.jsx:1599](src/dual_research/ui/static/shared.jsx:1599)). The inner `defaultOpen` is `!defaultCollapsed` at [src/dual_research/ui/static/run-detail.jsx:6149](src/dual_research/ui/static/run-detail.jsx:6149).
- **The heuristic that drives the inner closed-state.** [src/dual_research/ui/static/run-detail.jsx:5902-5905](src/dual_research/ui/static/run-detail.jsx:5902) — `isDefaultCollapsed(key)` returns true for `key.startsWith('system.')` and `key.startsWith('prior_turns.')`. The call site that pipes this into the inner CollapsibleSection: [src/dual_research/ui/static/run-detail.jsx:6068](src/dual_research/ui/static/run-detail.jsx:6068) — `defaultCollapsed={isDefaultCollapsed(key)}`.

Net effect: when the user opens the **outer** System Prompt or Derived Inputs section, the inner CollapsibleSection rows are still closed, so opening the outer reveals only header rows with hidden bodies.

The `isDefaultCollapsed` heuristic was introduced in spec 0085 when the panel had only one level of collapse (per-piece). Spec 0145 §5.4 layered the outer three-section grouping on top, and spec 0151 §3.1 extracted the shared renderer for split-pane reuse — but neither follow-up re-evaluated whether the inner collapse should still default closed now that the outer group already gates bulk system text. Spec 0151 §3.2's narrower fix (dropping the empty-piece filter, adding the `(empty)` placeholder at [src/dual_research/ui/static/run-detail.jsx:6188](src/dual_research/ui/static/run-detail.jsx:6188)) addressed empty-string rendering but not the double-collapse perception gap — its handoff test plan checked "verify the piece renders with `(empty)` placeholder" but never asserted a populated piece becomes visible in one click.

**Modes A and B from the Notion report explicitly ruled out by reading the renderer:**

- **Mode A** (wire data missing → renderer shows `(empty)`): if `bundle.pieces` is empty, `PromptPiecesThreeSectionView` short-circuits to `<InputEmptyState>` at [src/dual_research/ui/static/run-detail.jsx:6014-6016](src/dual_research/ui/static/run-detail.jsx:6014). The user would see a global "bundle empty" placeholder, not an empty section body.
- **Mode A'** (key-mismatch): the renderer iterates `Object.keys(pieces)` at [src/dual_research/ui/static/run-detail.jsx:6012](src/dual_research/ui/static/run-detail.jsx:6012); keys come from the wire response itself. Spec 0150 retired the legacy-key read-shim and backfilled all historical bundles to canonical keys, so a client-side key mismatch is not structurally possible.
- **Mode B** (server returns empty strings): the per-piece `(empty)` placeholder at [src/dual_research/ui/static/run-detail.jsx:6188](src/dual_research/ui/static/run-detail.jsx:6188) would render as literal "(empty)" text — the user would see *something*, not whitespace.

The user's symptom ("nothing below the section header" — actually a header row with no body) is consistent only with Mode C — outer expanded, inner closed, only header rows visible.

## 3. Fix

Flatten the inner-default-collapsed behaviour. The outer `InputSectionGroup` keeps its current three defaults (System closed, User open, Derived closed) and remains the only "user must opt in to see this section" gate. Once a user has clicked the outer chevron, they want to see content — don't make them click again.

The per-piece inner CollapsibleSection chevron stays present (users who want to fold a single long piece can still do so), but its default state becomes **open** for every key.

**DS citation.** The change targets the `CollapsibleSection` primitive's `defaultOpen` prop — `design-system/SPEC.md` §3 (Primitives, line 325) governs `<CollapsibleSection>` rendering. `design-system/SPEC.md` §4.5 (Agent input panel, line 444) depicts the canonical three-tier hierarchy with `▶/▼` glyphs at the **outer**-section level only; the inner per-piece chevron is not codified as default-collapsed in the DS. This spec aligns implementation with the depicted one-click reveal. No DS file changes are required; no new primitive is introduced; no token table is touched.

**Concrete edits**, all in [src/dual_research/ui/static/run-detail.jsx](src/dual_research/ui/static/run-detail.jsx):

1. **Delete the `isDefaultCollapsed` helper** at lines 5897-5905 (the function definition + its preceding 5-line comment about the system/prior_turns heuristic). It has exactly one caller and that caller is also being changed; no other reference exists in the codebase (confirmed by grep across `src/`, `tests/`, `design-system/`, `scripts/`).
2. **Drop the prop at the `InputSection` call site.** [run-detail.jsx:6068](src/dual_research/ui/static/run-detail.jsx:6068) — remove `defaultCollapsed={isDefaultCollapsed(key)}` from the `<InputSection>` invocation. The line `isAgentDefault={isSystemPiece(key) && systemSource === 'agent-default'}` and `attachmentTitles={attachmentTitles}` are unchanged.
3. **Drop the parameter from `InputSection`'s signature** at [run-detail.jsx:6134](src/dual_research/ui/static/run-detail.jsx:6134) — remove `defaultCollapsed` from the destructured props (signature becomes `function InputSection({ piece, text, isAgentDefault, attachmentTitles })`).
4. **Set the inner CollapsibleSection to `defaultOpen={true}`** at [run-detail.jsx:6149](src/dual_research/ui/static/run-detail.jsx:6149) — replace `defaultOpen={!defaultCollapsed}` with `defaultOpen={true}`.

No CSS changes (CollapsibleSection's `.cs-*` chrome is untouched). No backend changes. No schema or API changes. No new exports. Net diff ~ 12 lines removed, 1 line changed.

## 4. Regression-prevention test

Source-level pytest, matching the existing pattern at [tests/test_ui_jsx_syntax.py](tests/test_ui_jsx_syntax.py) (the codebase's convention for run-detail.jsx invariants — vitest is wired only for the dashboard-bootstrap artefact at [tests/js/](tests/js/), and introducing a happy-dom mount of `run-detail.jsx` would be a multi-spec lift outside this bug's scope).

New file `tests/test_input_section_default_open.py`:

```python
"""Spec 0178 — InputSection rows must default open after outer group expands.

The two-level collapse pattern (outer section + inner per-piece) led to a
"clicked but got nothing" UX bug because system.* and prior_turns.* pieces
were default-collapsed at the inner level. This test locks in: the inner
CollapsibleSection inside InputSection has no per-key collapse heuristic.
"""
import re
from pathlib import Path

JSX = Path(__file__).parent.parent / "src" / "dual_research" / "ui" / "static" / "run-detail.jsx"


def test_no_is_default_collapsed_helper():
    text = JSX.read_text()
    assert "isDefaultCollapsed" not in text, (
        "isDefaultCollapsed reintroduces the two-click reveal regression "
        "(spec 0178). Inner per-piece CollapsibleSection rows must default "
        "open once the user has expanded the outer InputSectionGroup."
    )


def test_input_section_inner_default_open_unconditional():
    text = JSX.read_text()
    m = re.search(
        r"function\s+InputSection\b.*?<CollapsibleSection\s+([^>]*)>",
        text, re.DOTALL,
    )
    assert m is not None, (
        "InputSection / its inner CollapsibleSection not found — "
        "if the component was renamed or restructured, update this test."
    )
    props = m.group(1)
    assert re.search(r"defaultOpen=\{true\}", props), (
        f"InputSection inner CollapsibleSection must use defaultOpen={{true}}; "
        f"found: {props.strip()!r}. The inner collapse must not be gated by a "
        f"per-key heuristic — that produced the spec-0178 two-click bug."
    )
```

**Before-fix behaviour.** Both tests fail — the JSX file currently contains `isDefaultCollapsed` (helper at line 5902, call site at line 6068) and `defaultOpen={!defaultCollapsed}` at line 6149.

**After-fix behaviour.** Both tests pass — `isDefaultCollapsed` is deleted, the inner `<CollapsibleSection>` carries `defaultOpen={true}`.

- [ ] Test: `tests/test_input_section_default_open.py::test_no_is_default_collapsed_helper` — asserts the heuristic helper is gone from `run-detail.jsx` (locks against accidental reintroduction in future per-piece-collapse experiments).
- [ ] Test: `tests/test_input_section_default_open.py::test_input_section_inner_default_open_unconditional` — asserts the inner CollapsibleSection inside `InputSection` declares `defaultOpen={true}` with no per-key condition (locks the actual render-time invariant; survives later renames as long as `InputSection` is still the function name and `<CollapsibleSection>` is still the inner primitive).

## 5. Blast radius

- **Files touched:** 1 source file (`src/dual_research/ui/static/run-detail.jsx`) + 1 new test file (`tests/test_input_section_default_open.py`). Net source diff ~13 LOC (12 removed, 1 changed). The test file is new and ~30 LOC.
- **Consumers of the affected renderer.** `PromptPiecesThreeSectionView` (the function `InputSection` is rendered inside) has exactly two callers in `src/`:
  - `InputTabContent` ([src/dual_research/ui/static/run-detail.jsx:6083](src/dual_research/ui/static/run-detail.jsx:6083)) — used by `InputBriefModal` ([src/dual_research/ui/static/run-detail.jsx:6647](src/dual_research/ui/static/run-detail.jsx:6647)), `PreflightResponseModal` ([src/dual_research/ui/static/run-detail.jsx:6684](src/dual_research/ui/static/run-detail.jsx:6684)), and `DocumentModal` ([src/dual_research/ui/static/run-detail.jsx:4745](src/dual_research/ui/static/run-detail.jsx:4745)).
  - `AgentInputPane` ([src/dual_research/ui/static/run-detail.jsx:5885](src/dual_research/ui/static/run-detail.jsx:5885)) — used by the split-pane left rail.
- All four consumer modals pick up the fix uniformly. There is no per-modal divergence in the shared renderer; the same `<InputSection>` function services every consumer.
- **Outer collapse defaults unchanged.** System closed / User open / Derived closed remain at [src/dual_research/ui/static/run-detail.jsx:6027-6046](src/dual_research/ui/static/run-detail.jsx:6027). The user's mental model of "click to peek at System / Derived" is preserved; only the second click is eliminated.
- **`CollapsibleSection` primitive untouched.** [src/dual_research/ui/static/shared.jsx:1599](src/dual_research/ui/static/shared.jsx:1599) is not modified. Every other consumer of `CollapsibleSection` (How-It-Works, timeline phase groups, critique sections) keeps its existing behaviour.
- **No backend / API / schema / event-stream changes.** No CSS changes. No DS primitive changes. No CHANGELOG fan-out beyond the one PATCH entry under `### Fixed` per CLAUDE.md's versioning rule.

## 6. Out of scope

- **Bug 1** from the Notion batch (split-pane Agent Input dual-card → single column with Claude/GPT toggle) — already queued as spec 0171.
- **Bug 2** (critique-card ID chip + literal `**` markdown title) — already queued as spec 0172.
- **Bug 4** (broader critique-card design-system parity beyond the 0151 rework) — to be queued separately after this spec lands.
- **Bug 5** (Consumption tab V2 unfolded-card anatomy) — to be queued separately.
- **Bug 6** (All-Runs `running` for runs that died days ago) — to be queued separately.
- **Spec 0173 §2.11** (per-item-card collapse affordance in the critique pane) — different surface and different intent: that spec *adds* a click-to-expand affordance to critique cards; this spec *removes* a click-to-expand requirement from input pieces. The two specs touch disjoint regions of `run-detail.jsx` (critique item-cards at ~1500-1800 vs. input panel at ~5900-6200) and have no overlap.
- **The original spec 0085 intent of saving vertical space when system prompts are long.** No longer applies, because the outer `InputSectionGroup` already keeps the System section closed by default. A user opening the outer chevron has explicitly asked for the content; honour that. Long-system-prompt mitigation, if it ever becomes a real complaint, is a separate UX spec.
- **Replacing the per-piece chevron affordance with a different primitive** (e.g., `<details>` or inline-only render). The per-piece chevron stays — users who want to fold a single long piece keep that affordance, just not as the default.
- **Documenting the inner-collapse-default rule in `design-system/SPEC.md`.** The DS today describes the outer three-section structure (§4.5) and the generic `CollapsibleSection` primitive (§3, line 325); neither codifies inner per-piece default state. Adding a "default open inside outer-gated sections" rule to SPEC.md is a small, separate DS-only edit that can ride with this spec OR follow as a one-line clarifier — implementer's call, but if added, the wording is roughly: *"§4.5 — When an outer `InputSectionGroup` is closed by default (System / Derived), the inner per-piece `<CollapsibleSection>` rows it contains MUST default open. The user's act of expanding the outer section is the disclosure intent; nested per-piece collapse defaults are reserved for user-initiated folding only."*

## 7. Risks

- **Long system prompts dump immediately when the user opens the outer section.** Mitigated by the fact that the outer System section is still `defaultOpen=false` — the user has to explicitly opt in. The per-piece chevron remains so they can fold a single piece manually if they want. This matches every other section pattern in the app (e.g., How-It-Works sections, timeline phases).
- **Stale prose referencing the inner-default-collapse heuristic.** Inline comments in `run-detail.jsx` near the deleted `isDefaultCollapsed` block, and the spec 0085 / 0145 / 0151 historical notes already in CHANGELOG, may reference "default-collapsed system pieces." Grep `src/`, `design-system/`, `specs/` and `CHANGELOG.md` for `default.?collapsed` / `isDefaultCollapsed` before merging; update or scrub any prose that explicitly promised inner-collapse-by-default.
- **Concurrent merge with spec 0173 (queue pos 2) or other queued UI specs.** Spec 0173 touches the critique pane item-cards (lines ~1500-1800 of `run-detail.jsx`); this spec touches the input panel (lines ~5900-6200). The two regions are disjoint, so no textual conflict is expected even if 0173 lands first. If 0173 reshuffles line numbers, the `file:line` citations above may drift — the citations are anchored to current `main` and the implementer should reconcile against whatever `main` looks like at branch-cut time.
- **Manual verification gap.** The regression test is source-level — it locks the JSX prop value but cannot prove the rendered output is correct. The Notion bug-batch page's verification protocol (one click → real text visible across all four full-view modals, with attached screenshots in the PR description) is mandatory before flipping this spec to `merged`. The handoff PR MUST include screenshots for each of the four modals — see CLAUDE.md's standing rule that UI specs which cite design-system references must include rendered-output evidence.
