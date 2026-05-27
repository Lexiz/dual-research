---
spec: 0115
title: Deep Research UI — timeline, critique cards with sources, appendix, validate-run CLI
label: new-feature
version-bump: MAJOR
status: proposed
target-version: 1.1.0
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0115 — Deep Research UI + validator

## Context

Spec 0114 introduces the Deep Research protocol — a new contract for how the two agents interact, track items, handshake on resolutions, surface acknowledged divergences, and converge on the final document. Spec 0114 ships the backend with a backward-compat shim that emits legacy event payloads alongside the new ones, so the existing UI continues to render runs without immediate breakage.

This spec catches the UI up to the new protocol and removes the shim. It also adds a post-hoc `validate-run` CLI that loads a finished run, builds the ledger from the new event stream, and reports contract violations.

The most visible new concept the UI must accommodate is **sources** — every resolved or acknowledged item that was raised with `evidence_required: true` has one or more structured evidence records (URL, title, search query, fetched-at, full content excerpt). These need to be rendered inline on the critique cards (disagreement / question / issue / comment cards) so the reader can see what backed each resolution — title and full content, not just URL. The display must scale to multiple sources per card and remain readable: collapsed-by-default per source with one-click expand to see the full content excerpt.

## Goals

1. Render timeline cards with the new badge model: provider · activity · raised/addressed/resolved/acknowledged/withdrawn/capped counts per category, status right-aligned. Layout matches the canonical spec we established in audit conversation.
2. Render critique cards (one per tracked item) with linked sources displayed inline; multiple sources per card; per-source collapsible content excerpt panel.
3. Render the final-document appendix structure (unresolved items grouped by category and phase, with full provenance).
4. Ship `dual-research validate-run <session-dir>` — a CLI tool that re-reads the run's event stream, rebuilds the ledger via the contract module, runs the contract validator, and prints a report of any violations.
5. Remove the backward-compat shim from spec 0114 once UI is reading the new event stream. The legacy `Phase0Complete` / `Phase2RoundComplete` / `Phase4RoundComplete` payloads stop carrying the legacy fields (or are dropped entirely).

## Non-goals

- Changes to the backend protocol — that's spec 0114's territory.
- Migration of legacy run artifacts to the new event schema — old runs continue to render via a "legacy mode" code path in the UI for backward compatibility on previously-completed runs.
- New visual design tokens or layout changes beyond what's needed to support the new data model. The M3 chrome from specs 0099-0110 stays.
- Additional categories or lifecycle states — the contract is locked in spec 0114.

## UI changes

### 1. Timeline cards — new badge model

Each timeline card represents one agent's turn (or input/draft for one-shot phases). The badge row layout:

**Left cluster** (aligned to card content edge, in order):
- Provider badge: `Claude` or `GPT`
- Activity / round badge: `preflight`, `draft plan`, `turn 1`, `turn 2`, … (single canonical label per round; no duplicated `R1` chip)
- **Per-category summary chips** (see below)
- Closeout / cap modifier chips (when applicable): `⟳ closeout`, `via hard cap`, `via ghost cap`

**Right cluster** (right-aligned to card edge):
- Status badge: `Done`, `In progress`, `Capped`

Per-card chip layout, by card type:

| card type | per-category chips |
|---|---|
| phase 0 input card | `AgentInput` (single chip, no provider, no counters) |
| phase 0 round (per agent) | provider · `turn N` · one chip each for **Questions** and **Disagreements** |
| phase 1 plan (per agent) | provider · `draft plan` · status (no per-category chips — phase 1 raises nothing) |
| phase 2 round (per agent) | provider · `turn N` · one chip each for **Questions** and **Disagreements** |
| phase 3 draft | drafter-provider · `draft` · status (no per-category chips — phase 3 raises nothing) |
| phase 4 round (per agent) | provider · `turn N` · one chip each for **Questions**, **Disagreements**, **Issues**, **Comments** |

#### Per-category summary chip — uniform across the timeline

For every interaction-phase round, the card shows **one chip per category allowed in that phase**, in a fixed left-to-right order: Questions → Disagreements → (Issues → Comments only in phase 4). The chip is always present, even when zero, so the columns align visually across rounds and the reader can read down a column to see how a category evolved.

Each chip carries three numbers, in this order:

- **standing** — total non-terminal items of this category that this agent raised, *as of the end of this round*. (Sum of `open` + `addressed` items.)
- **raised** — items of this category this agent raised *during this round*.
- **closed** — items of this category this agent raised that transitioned to a terminal state (`resolved` / `acknowledged` / `withdrawn` / `capped`) *during this round*. A counter-argument (`addressed` → `open`) does NOT count as closed.

**Canonical chip text**: full category word (plural), then the three numbers in a clear inline summary. Examples:

- `Questions  4 standing · 2 raised · 1 closed`
- `Disagreements  0 standing · 0 raised · 0 closed`
- `Issues  3 standing · 0 raised · 2 closed`
- `Comments  1 standing · 1 raised · 0 closed`

**Reading the chip**: "Questions — 4 are still in flight; this round added 2 and closed 1." Numbers update monotonically along the column (standing of round N = standing of N−1 + raised − closed) so the timeline tells a coherent story by category.

**Forbidden**: never use bare letter abbreviations like `Q`, `D`, `I`, `C`, `T`, or compound shorthand like `QCR1`. Always the full word (plural). Never merge categories into a single chip — every allowed category gets its own chip even when all three numbers are zero.

**Visual style**: the standing number is the primary value (largest type weight); raised / closed are secondary, separated by middle-dot. When `raised + closed == 0` the chip dims slightly to indicate "no activity this round" while still showing the standing total — this preserves the column alignment without drawing the eye.

#### Per-card detail popover

Clicking a per-category chip opens a popover listing the item IDs that contributed to each of the three numbers (standing / raised / closed), with one-line snippets and click-through to the critique card for that item. The popover groups the three lists under sub-headings; closed items are further broken down by terminal state (resolved / acknowledged / withdrawn / capped) since that distinction matters for the reader.

#### Phase-level summary on the phase header

The header row above each phase's set of turn cards (e.g. "Phase 2 — Negotiate plan") shows the same per-category summary, but aggregated across both agents and showing the *phase-end* state (after the phase converged):

- `Questions  0 standing · 7 raised · 7 closed`
- `Disagreements  2 standing · 5 raised · 3 closed` (2 standing here ≡ items carried forward, since the phase has converged)

This gives a one-glance summary of the phase outcome.

**Card body** — the existing `## Stance` prose section is rendered as the card's TL;DR text. The body content is the full markdown of the turn, rendered with the existing side-by-side viewer for items with `> quote:` / `> after:` anchors. The operation blocks (`### RAISE` / `### ADDRESS` / etc.) are rendered as collapsible mini-cards inline.

### 2. Critique pane — cards with linked sources

The Critique pane (existing UI surface, currently rendering questions / issues / disagreements / comments cards) is updated to consume the new event stream's `ItemRaised` + `ItemTransitioned` events.

Each tracked item across the run gets one critique card. Card structure:

```
┌─────────────────────────────────────────────────────────────┐
│ [Q-plan-c-04]   [question]   [resolved]   raised by Claude  │
│                                                              │
│ Body of the raised item — the question text itself.         │
│ Anchored to GPT's plan via `> quote: …`                     │
│                                                              │
│ ─ Timeline ─                                                 │
│  • Round 1 — raised by Claude (evidence_required: true)     │
│  • Round 2 — addressed by GPT                               │
│  • Round 3 — resolved by Claude                             │
│    Reason: "GPT's evidence from [source] addresses my       │
│    concern; I no longer believe the brief is ambiguous."    │
│                                                              │
│ ─ Sources (2) ─                                              │
│  [▶] OpenTelemetry Go SDK Status — example.com/otel-go     │
│  [▶] Go OTel Logs API Release Notes — example.com/otel-rel │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

The card sections:

- **Header chip row**: ID, kind, current status, raiser.
- **Body**: the raised item's content with its anchor rendered as a blockquote link to the underlying source content. Click expands the linked content in the side-by-side viewer.
- **Timeline**: chronological list of state transitions, each with round number, actor, and rationale. This is the provenance trail.
- **Sources**: the new section. Renders one collapsed row per evidence record, with title and URL visible by default; expand to see full content excerpt.

#### Sources section in detail — the new widget

Each evidence record produces one row. The row has two states:

**Collapsed (default)** — shows the source title (clickable to follow URL in new tab), the URL hostname, and a chevron indicator:

```
[▶] OpenTelemetry Go SDK Status — example.com
```

**Expanded** — clicking the chevron reveals the full evidence record below the row:

```
[▼] OpenTelemetry Go SDK Status
    URL: https://example.com/otel-go-status (opens in new tab)
    Fetched: 2026-05-19 13:45 UTC
    Search query: "OpenTelemetry Go logs stable 2026"

    Content excerpt:
    ┌─────────────────────────────────────────────────────────┐
    │ The OpenTelemetry Go SDK marks logs as beta as of April │
    │ 2026. The log package version `v0.18.0` confirms        │
    │ non-stable status. [...]                                │
    │                                                          │
    │ (full 200–2000 char excerpt; scrollable if it overflows │
    │  the card's content area)                                │
    └─────────────────────────────────────────────────────────┘
```

**Design constraints**:

- Multiple sources per card supported — the section renders as many rows as there are evidence records. The card scrolls if total height exceeds the viewport.
- Each source is independently collapsible. One click per source; no "expand all" needed for v1 (can be added later if requested).
- Default state is collapsed — opening a card doesn't immediately expand all sources, which would visually overwhelm with multi-source items.
- The content excerpt is rendered inside a `<pre>` block with `white-space: pre-wrap` so line breaks and indentation in the original page content are preserved.
- Long excerpts (>800 chars) get a `max-height: 200px; overflow-y: auto` on the content-excerpt block so the card height stays bounded; user can scroll within the excerpt.
- Source row is keyboard-accessible — Enter/Space toggles expansion.
- The header chip row's `[resolved]` status badge color-codes the card border:
  - `resolved` → green left border
  - `acknowledged` → amber left border
  - `withdrawn` → grey left border
  - `capped` → red left border
  - `open` / `addressed` → blue left border (in-flight)

**Hallucinated evidence** — when an evidence record was flagged by the contract validator (event_id fabricated / URL not in consulted set / content excerpt not in source), the source row renders with a red warning chip `⚠ unverified` to the right of the title. Clicking the chip explains which validation check failed. The row still renders the agent's reported content, but the warning makes it visually obvious that the source cannot be trusted.

#### Filtering and grouping

The Critique pane gets filter chips at the top. Each chip carries its own per-category count so the numbers on the chip match the timeline summary chips exactly. Same vocabulary, full words (plural), never abbreviated.

- **By category** (counts = total items of that category across the run, scoped to the active phase / raiser / status filters):
  - `Questions (12)` · `Disagreements (5)` · `Issues (4)` · `Comments (2)` · `All (23)`
- **By status**: `Open` · `Addressed` · `Resolved` · `Acknowledged` · `Withdrawn` · `Capped` · `All`
- **By raiser**: `Claude` · `GPT` · `Either`
- **By phase**: `Phase 0 (input)` · `Phase 2 (negotiate plan)` · `Phase 4 (review draft)` · `All`

Cards group under section headers based on the active grouping (default: by category, then by phase). The section header repeats the per-category summary chip from the timeline (standing · raised-across-phase · closed-across-phase) so the reader can cross-reference back to the timeline without re-counting.

**Uniformity invariant**: a viewer can pick any per-category summary chip on a timeline turn card, click it, and arrive at a filtered critique view whose count chip displays the same standing number. The same canonical (kind, phase, raiser) namespace drives both surfaces — there is no separate vocabulary anywhere in the UI.

### 3. Final-document appendix rendering

When the user opens the final document in the UI, the new "Unresolved items" appendix section is rendered as a structured card group rather than raw markdown. Each unresolved item gets a compact card with the same header chip row and timeline + sources sub-sections as the full critique card, but rendered more densely (shorter timeline, sources collapsed by default).

The appendix layout in the rendered document:

```
## Appendix — Unresolved items

### Briefing limitations (phase 0)
  ▸ [Q-input-c-01] acknowledged — body
  ▸ [D-input-g-02] capped (hard_cap) — body
  
### Surfaced disagreements (negotiate-plan phase)
  ▸ [D-plan-g-04] acknowledged — body
  
### Unanswered research questions (negotiate-plan phase)
  ▸ [Q-plan-c-07] capped (ghost_cap) — body
  
### Known issues in this draft (review-draft phase)
  ▸ [I-review-g-03] acknowledged — body
  
### Pending comments (review-draft phase)
  ▸ [C-review-c-05] capped (hard_cap) — body
```

Each card is collapsed by default; expanding shows the full timeline and sources. Same widget as the Critique pane's full card, just in a denser stack.

The underlying `final.md` markdown file (written by `finalize.py`) carries the same content in plain markdown so it works in any markdown viewer. The UI rendering is just a richer view of the same content.

### 4. Closeout indicator in the UI

When a round was a closeout round (the prior round attempted convergence but left non-terminal items), the timeline card for that round renders a small `⟳ closeout` chip immediately after the round chip, before the per-category summary chips. Hovering shows the list of items the closeout was requested for.

Phase complete events that came via the closeout / ghost-cap / hard-cap paths render a corresponding flag on the phase header in the timeline:

- `via_closeout: true` → small `via closeout` chip
- `via_ghost_cap: true` → small `via ghost cap` chip
- `via_hard_cap: true` → small `via hard cap` chip

These are not alarming colors — they're informational, helping the reader understand how the phase ended.

#### Cap modifiers on per-category chips

When an agent's items in a category were ghost-capped or hard-capped in a round, the closed-count includes those transitions and the chip gets an extra suffix `· ⊘ N` showing how many of the closed count came via orchestrator-forced cap rather than agent action. Example:

- `Questions  0 standing · 0 raised · 4 closed · ⊘ 2`

reads as: "Of the 4 questions closed this round, 2 were orchestrator-capped (the other 2 were resolved / acknowledged / withdrawn normally)." The cap suffix is omitted when the cap count is zero.

### 5. Components touched

Estimated component changes (file-level only; full diff scoped during implementation):

- `src/dual_research/ui/static/live-data.jsx` — `buildLiveTimeline()` rewritten to consume new event types. Attach the full new-style stats (raised/addressed/resolved/acknowledged/withdrawn/capped per category) to every interaction-phase card.
- `src/dual_research/ui/static/run-detail.jsx` — `TlTurnRow` rewritten to render the new badge model (left cluster + right-aligned status, no duplicated round chip, full counter palette).
- `src/dual_research/ui/static/run-detail.jsx` — `CritiquePane` and `CritiqueCard` updated to render the new card structure (header chips, body, timeline, sources).
- `src/dual_research/ui/static/run-detail.jsx` — new `SourceRow` component with collapse/expand mechanics and full content excerpt rendering.
- `src/dual_research/ui/aggregator.py` — `PhaseStats` and `TurnStats` dataclasses updated to carry the new per-category, per-lifecycle-state counters. Stats are computed from the new event stream.
- `src/dual_research/ui/models.py` — `Question`, `Issue`, `Comment`, `Disagreement` dataclasses unified or replaced by a single `Item` dataclass with `kind` field that mirrors the ledger's `LedgerEntry`. `EvidenceRecord` dataclass added.
- `src/dual_research/ui/questions.py`, `issues.py`, `comments.py` — removed (functionality moves to the unified `Item` model fed directly from the event stream).
- `src/dual_research/ui/aggregator.py` — appendix-building functions added that walk the ledger for terminal-not-resolved items per category per phase.
- CSS — new styles for the sources section + collapsible source rows. Reuses the existing design tokens (`m3-elevation`, `qref-*`, etc.).

## `validate-run` CLI

A new CLI subcommand that audits a finished run against the contract.

### Invocation

```
dual-research validate-run <session-dir>
dual-research validate-run runs/20260519-132908-backend-language-choice
```

### What it does

1. Loads the session at `<session-dir>` — reads `transcript.jsonl`, `state.json`, `metrics.json`, and the per-phase turn files.
2. Rebuilds the ledger from the event stream using `build_phase_ledger` per phase.
3. Walks every turn file and runs the contract `validate_turn` validator against each. Collects validation errors.
4. Checks cross-phase invariants:
   - All terminal items have non-empty `reason` in their final transition.
   - All `capped` items have a `via:` field.
   - All `evidence_required: true` items that ended in `resolved` have at least one evidence record.
   - All evidence records pass the anti-hallucination cross-check (event_id matches a real ToolEvent; URL in consulted set; content excerpt in source).
   - Phase artifact hashes match where claimed.
   - `LedgerDrift` events match between self-reported counters and ledger-computed counters.
   - Final document's appendix structure is well-formed.
5. Prints a structured report.

### Report format

```
Deep Research Run Audit — runs/20260519-132908-backend-language-choice

Status: 12 warnings, 3 errors

== Phase 0 (input) ==
✓ converged via closeout in round 3
✓ AGREED_INTERPRETATION hash-match verified
✓ 0 contract violations

== Phase 1 (research-plan) ==
✓ both plans produced

== Phase 2 (negotiate-plan) ==
✗ ERROR: phase2-r5-claude turn: ADDRESS for D-plan-g-04 missing
         evidence record; item flagged evidence_required: true
✓ converged in round 9 (via_canonical_promotion=false; matches new model)
⚠ WARNING: 3 LedgerDrift events on phase2-r6 — claude self-reported
           OPEN_DISAGREEMENTS=1, ledger computed 2

== Phase 3 (draft) ==
✓ draft produced

== Phase 4 (review-draft) ==
✓ converged via_stuck_agreed=true in round 8 — this is the legacy
  flag; new model would have used ghost_cap, but this run was pre-cutover
…

== Cross-phase ==
✗ ERROR: I-review-c-03 ended in `acknowledged` but only one ACKNOWLEDGE
         block was found (need consecutive turns from both agents)
✗ ERROR: 1 evidence record has unverified content excerpt (Q-plan-c-04,
         source 1 of 2): "OpenTelemetry Go SDK Status" — excerpt text
         does not appear in consulted page content

== Final document ==
✓ appendix structure well-formed
✓ all unresolved items have full provenance
```

### Exit code

- `0` — no errors, may have warnings
- `1` — at least one error
- `2` — invalid session directory (not a valid run)

### Implementation

`src/dual_research/cli.py` gets a new subcommand `validate-run` that calls into `src/dual_research/contract/validator.py` (already imported by the orchestrator). The validator's per-turn check is reused; new functions in `contract/validator.py` perform the cross-phase invariants.

### Use cases

- **Regression detection**: run on every recent run after deploying a protocol change; surface any violations.
- **Debugging**: when a run ends with weird convergence behavior, run this to inspect what the contract says about it.
- **Production sanity**: schedule a daily cron that runs `validate-run` on the latest run and surfaces errors to a dashboard.

## Backward-compat shim removal

Spec 0114 ships a backward-compat shim in `src/dual_research/events/legacy_shim.py` that emits the legacy `Phase0Complete` / `Phase2RoundComplete` / `Phase4RoundComplete` event payloads alongside the new events. Once the new UI consumes the new events directly, the shim becomes dead weight.

Removal steps in this spec:

1. Delete `src/dual_research/events/legacy_shim.py`.
2. Remove the shim invocations from the orchestrator's phase-boundary code paths.
3. Drop the legacy fields from the event payload dataclasses (e.g. `Phase2RoundComplete.claude_open_questions` etc.). The events keep their event-type strings but become empty marker events, since all data now lives in `ItemRaised` / `ItemTransitioned` / `PhaseConverged` events.
4. Update any internal consumers of the legacy events to consume from the new event stream.
5. Run the existing test suite; expect any test that asserted against the legacy fields to fail. Update those tests to assert against the new event stream.

After shim removal, the legacy UI rendering code path (which today reads `claude_open_questions` etc. and renders the legacy badges) is also removed in this spec. The UI is unified around the new event stream.

## Test plan

- [ ] Unit tests for the new `SourceRow` component (React): collapse/expand toggle, keyboard accessibility, multiple sources, long excerpt scroll, hallucinated-evidence warning chip.
- [ ] Unit tests for the new `CritiqueCard` component: header chips render for each lifecycle state, timeline section renders one row per transition with correct actor + reason, sources section renders the right count.
- [ ] Unit tests for the appendix rendering (final document view): each unresolved category renders its section header; items in each section show ID + state + body; expansion shows timeline.
- [ ] Unit tests for the new `validate-run` CLI: feed a fixture session that violates each contract rule individually; verify the right error fires.
- [ ] Integration test: end-to-end with the new protocol (spec 0114 backend + spec 0115 UI). Verify timeline cards render correctly per-round per-agent; verify critique cards show the right sources count for items with evidence; verify the final-doc appendix matches what the markdown file says.
- [ ] Manual run-through: fire `dual-research-run` on a small brief, watch the live UI populate with new-style timeline cards. Open a few critique cards, expand sources, verify content is readable.
- [ ] Manual: open a *legacy* run (one completed before spec 0114 landed) in the UI. Verify it still renders correctly via the legacy code path that this spec keeps in place for back-compat on historical runs.

## Risks

- **Risk**: The new event stream is larger than the legacy stream (one event per state transition, evidence records embedded). Transcript files grow significantly, potentially impacting load times.
  - **Mitigation**: Measure transcript size on a few production runs. If size becomes a problem, consider compression on disk (gzipped jsonl) or breaking the transcript into per-phase files.

- **Risk**: The source-display UI is the most visible new component. Edge cases (very long URLs, very long titles, non-Latin character sets in content excerpts, missing fields) need to be handled gracefully.
  - **Mitigation**: Property-based testing on the `SourceRow` component with adversarial inputs. Visual QA in dark mode + light mode + responsive widths.

- **Risk**: Hallucinated-evidence warning chips become a regular sight on production runs, suggesting agents lie about sources more than expected.
  - **Mitigation**: Track the rate. If high, tune the prompt to emphasize evidence integrity more (low-cost) or consider adding a turn-level rejection that demands re-emission (higher-cost).

- **Risk**: The legacy rendering path for old runs accumulates bit-rot since it's no longer the primary path.
  - **Mitigation**: Add a CI snapshot test that loads a fixture legacy run and verifies the legacy UI rendering still works. If it ever breaks, we'll see it before users do.

- **Risk**: The `validate-run` CLI is useful as a debugging tool but becomes a maintenance burden if its rules drift from the contract module.
  - **Mitigation**: The CLI is implemented as a thin wrapper around `contract/validator.py` — there's exactly one source of truth for the contract rules. The CLI doesn't duplicate them.

## Open questions

- **OQ-1**: Should `validate-run` also have a `--fix` mode that auto-rewrites the run's state.json / transcript to bring it into compliance where possible (e.g. backfilling missing rationale fields with a placeholder)? Spec currently says no — fix mode adds substantial complexity and risks data corruption.
- **OQ-2**: Should the sources display expand-all be a per-card option (one button to expand all sources on this card)? Could be added if multi-source cards become common and users find per-source clicking tedious.
- **OQ-3**: Hallucinated-evidence cards — should the UI hide them entirely from the critique pane until manually shown, or just warn? Spec currently says warn (still visible). Hiding feels like silencing a debugging signal.
- **OQ-4**: The appendix in `final.md` is currently rendered as plain markdown for compatibility with any reader. The UI's "richer" rendering reads the same markdown and parses it back into structured cards. Should we instead write the appendix to a separate structured file (e.g. `appendix.json`) and have `final.md` just reference it? Spec currently keeps it as plain markdown — works in any tool.
