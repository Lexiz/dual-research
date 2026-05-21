---
spec: 0139
title: Canonical prompt-pieces, per-attachment token tracking, and full-view alignment
label: refactoring
version-bump: MINOR
status: proposed
target-version: 1.10.0
created: 2026-05-21
pr: ""
---

# Spec 0139 — Canonical prompt-pieces, per-attachment token tracking, and full-view alignment

## Context

Specs 0114 (Deep Research protocol), 0117 (artifact registry + display names), and 0118 (Consumption tab + per-piece token tracking) established a single canonical vocabulary for the inputs and outputs of every phase. The diagram `diagrams/deep-research-pipeline.light.svg` is the human-readable contract for that vocabulary: every phase, every round, every named piece a model sees on input or persists on output.

In practice three drifts have accumulated between the diagram, the registry, and what the UI actually shows:

1. **The `user_prompt` composite is collapsed in the emitter.** [`prompt_pieces.py`](../src/dual_research/protocol/prompt_pieces.py) emits a single `user_prompt` key per phase, even though the registry already templates `user_prompt.message` and `user_prompt.attachment.<id>` ([artifacts.py:167-170](../src/dual_research/contract/artifacts.py:167)). Attachments therefore get no individual token share in Consumption and no individual row in any full-view modal.
2. **Two registry entries are dead.** `system.preamble` ([artifacts.py:151](../src/dual_research/contract/artifacts.py:151)) and `system.task.closeout` ([artifacts.py:163](../src/dual_research/contract/artifacts.py:163)) are defined but never emitted as pieces. The diagram does not mention either; the UI cannot render either; the Consumption tab never receives either.
3. **`run-detail.jsx` carries a legacy piece vocabulary parallel to the registry.** `INPUT_PIECE_ORDER = ['system', 'brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp']` ([run-detail.jsx:5085](../src/dual_research/ui/static/run-detail.jsx:5085)) drives every full-view input panel and every per-phase grouping. These short keys are not the canonical IDs the aggregator emits — they're a pre-0117 mapping that the input-bundle layer translates into. The result is that the Consumption tab (canonical IDs) and the full-view modals (legacy keys) are speaking two languages about the same pieces.

The user-visible consequence is that the **briefing full view** currently shows the original chat message under "User prompt" + a system block under "System prompt", but does not surface attachments under that User-prompt section, does not surface a methodology preamble (if one exists), and does not align its labels with the Consumption tab's piece names. The **side-by-side modals** (NegotiateReviewModal / DraftReviewModal) read input bundles via the legacy vocabulary, so the left "contested input" pane and the input sub-pane are not labelled by canonical artifact ID.

This spec lands the three corrections together because they share one root cause — divergence from the registry — and because the Consumption tab and the full-view modals can only stay in sync if they're driven from the same canonical piece dict.

**Outputs are explicitly out of scope** for per-piece token decomposition. Output artifacts keep their canonical IDs for provenance and timeline labelling, but `output_tokens` stays atomic per turn (provider-reported, not estimated per output piece). This is a deliberate scope cut to keep the spec focused on the input side, which is where the cost-visualization gap lives today.

## Proposed change

### 1. Decompose `user_prompt` into composite pieces in the emitter

In [`src/dual_research/protocol/prompt_pieces.py`](../src/dual_research/protocol/prompt_pieces.py), every `pieces_for_*()` function changes its `user_prompt` parameter from a single string to a composite. Two options for the signature; pick the one with fewer call-site changes:

- **(a)** Replace the `user_prompt: str` parameter with `user_prompt_message: str, attachments: Iterable[Attachment]` where `Attachment` is `(id: str, title: str, content: str)`.
- **(b)** Keep `user_prompt: str` as a back-compat aggregate but add `attachments: Iterable[Attachment] | None = None`, and when supplied, emit per-attachment keys in addition to (or instead of) the aggregate.

Recommended: **(a)**, with a one-time migration of every `pieces_for_*()` call site in `orchestrator/dr_run.py` ([dr_run.py:573, 716, 721, 892, 1103, 1252](../src/dual_research/orchestrator/dr_run.py)).

Emitted keys per phase become:

| Phase | Keys emitted (when present) |
|---|---|
| P0 | `system.task.input`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `prior_turns.phase0`, `ledger.standing_items`, `closeout.request` |
| P1 | `system.task.research_plan`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `phase0.agreement.interpretation` |
| P2 | `system.task.plan_negotiation`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `phase0.agreement.interpretation`, `phase1.claude`, `phase1.openai`, `prior_turns.phase2`, `ledger.standing_items`, `closeout.request` |
| P3 | `system.task.drafting`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `phase0.agreement.interpretation`, `phase1.claude`, `phase1.openai`, `phase2.agreement.plan`, `all_p2_turns`, `carry_forward.phase2` |
| P4 | `system.task.review`, `user_prompt.message`, `user_prompt.attachment.<id>` × N, `current_draft`, `prior_turns.phase4`, `ledger.standing_items`, `closeout.request` |

The aggregate `user_prompt` key is **dropped** from the emitted dict. The Consumption tab's "Per-phase grouping" table in spec 0118 already groups by prefix (`user_prompt.*`) so per-section totals continue to roll up correctly. A small renderer adjustment in the Consumption tab presents the composite under a single "User prompt" group label by default, expandable to the per-attachment breakdown.

### 2. Investigate `system.preamble` and `system.task.closeout`; either wire up or delete

Both are registered with display names but never produced by any `pieces_for_*()` function. Resolve before implementing the rest of the spec:

- Read [`src/dual_research/protocol/prompts.py`](../src/dual_research/protocol/prompts.py) and `protocol/blocks.py`. Confirm whether a methodology preamble is in fact prepended to every system prompt at assembly time. If yes, plumb a `system_preamble: str` argument through every `pieces_for_*()` function and emit `system.preamble`; the full-view's System-prompt section then gets a dedicated subsection. If no, delete the `ArtifactDef` line in `contract/artifacts.py` and document the removal here.
- For `system.task.closeout`: confirm that the closeout instructions live entirely inside the `closeout.request` piece (the round-conditional input the orchestrator injects when convergence is blocked). If the closeout instructions are not also part of `system.task.input`/`system.task.review`/etc., add the emission. If they are subsumed by `closeout.request`, delete the `system.task.closeout` registry entry.

The investigation is small and bounded: read those two files, decide, and either add 1-2 emitter lines or remove 1-2 registry lines. Land the decision in this spec's commit, do not defer.

### 3. Replace the legacy UI piece vocabulary with canonical artifact IDs

In [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx), the legacy keys `'system', 'brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp'` are removed from:

- `INPUT_PIECE_LABEL` ([line 5071-5080](../src/dual_research/ui/static/run-detail.jsx:5071)) — replaced by a `displayNameOf(canonicalId, attachmentTitles)` helper that ports the Python `artifacts.display_name()` logic to JS.
- `INPUT_PIECE_ORDER` ([line 5085](../src/dual_research/ui/static/run-detail.jsx:5085)) — replaced by a canonical-ID order list defined per phase, matching the diagram's arrival-order numbering.
- `INPUT_PIECE_DEFAULT_COLLAPSED` ([line 5089](../src/dual_research/ui/static/run-detail.jsx:5089)) — keys retargeted to canonical IDs.
- Every reader (`InputTabContent`, `AgentInputDualPane`, the Consumption tab's piece-bar renderer) reads pieces by canonical ID. The aggregator stops translating canonical → legacy at the input-bundle boundary; canonical IDs flow end-to-end.

A small JS module `src/dual_research/ui/static/artifact-display.js` (new file) holds:
- The registry template list, mirrored from `contract/artifacts.py`. The Python side and the JS side stay in sync via a CI test that loads both and asserts equivalence (see Test Plan).
- `displayNameOf(id, attachmentTitles)` — the JS port of `display_name()`.
- `phaseOrderFor(phaseNum)` — returns the canonical-ID order for a phase's input pieces (matches the diagram's arrival order).

### 4. Full-view single-view modals: drive sections from canonical pieces

`InputBriefModal` and `PreflightResponseModal` ([run-detail.jsx:5636, 5682](../src/dual_research/ui/static/run-detail.jsx:5636)) restructure to:

- **System prompt section** — one row per `system.*` piece in the emitted dict for this turn (typically `system.task.<phase>`, plus `system.preamble` if wired up after the §2 investigation, plus `system.task.closeout` if it survives §2). Each row labelled by `displayNameOf()`, body collapsed by default.
- **User prompt section** — one row for `user_prompt.message`, then one row per `user_prompt.attachment.<id>` in attachment order. Each attachment row shows the title (from `attachments.json`), the piece's estimated tokens, and the rendered content (markdown for text attachments; thumbnail for images; download link for binary).
- **Derived inputs section** — one row per remaining piece (`prior_turns.phase{N}`, `ledger.standing_items`, `closeout.request`, prior agreements/plans/drafts when the phase has them). Always collapsed by default; this is where the "what other context was fed to the agent" lives.

The existing `Sources` and `Files` tabs on `InputBriefModal` ([line 5659-5667](../src/dual_research/ui/static/run-detail.jsx:5659)) are removed — that information is now native to the User-prompt section. The `Content` tab stays (it shows `brief.md` standalone, which remains useful even when the full Input view is also accessible) but is renamed `User prompt` to match the section label.

### 5. Full-view side-by-side modals: canonical labels on both panes

`NegotiateReviewModal` and `DraftReviewModal` ([run-detail.jsx:3982, 4414](../src/dual_research/ui/static/run-detail.jsx:3982)) update so that:

- **Left pane** ("Original" sub-tab) — the document currently shown is labelled by its canonical artifact ID rather than by a path or a phase-specific phrase. The mapping is per phase × round, already implemented in `leftPaneTabsFor()` ([line 4928-4960](../src/dual_research/ui/static/run-detail.jsx:4928)); this change is label-only:

  | Card | Left-pane document → canonical artifact ID |
  |---|---|
  | P0 round 1 | `user_prompt.message` (briefing chat message) |
  | P0 round N≥2 | `phase0.<other_agent>.r<N-1>` (other agent's prior preflight turn) |
  | P1 plan | `user_prompt.message` (briefing) |
  | P2 round 1 | `phase1.<other_agent>` (other agent's research plan) |
  | P2 round N≥2 | `phase2.<other_agent>.r<N-1>` |
  | P3 draft | `phase2.agreement.plan` (the agreed plan being executed) |
  | P4 round 1 | `current_draft` (= `phase3.draft.v1` at this point) |
  | P4 round N≥2 | `phase4.<other_agent>.r<N-1>` |

- **Input sub-tab** — replaces `AgentInputDualPane`'s legacy-keyed layout with the same canonical-piece layout used by the single-view modals (System / User prompt / Derived). Still dual-pane (Claude vs GPT) for phases where both agents share the same input set.
- **Right pane (Q/D/I/C critique)** — unchanged in layout. Confirm the items are read from `run.phaseReviewItems[phase{N}Round{R}{Agent}]` ([line 4996](../src/dual_research/ui/static/run-detail.jsx:4996)) and that the critique pane's filter chips line up with the categories the phase emits per the diagram (P0/P2 = Q/D; P4 = Q/D/I/C; P1/P3 = none).

### 6. Per-attachment persistence and aggregator support

`prompt_pieces` is one half of the path; the aggregator needs to receive and forward the per-attachment keys.

- [`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py): confirm that the `promptPieces` payload in the `TurnEnded` event is propagated as a dict-of-canonical-IDs unchanged. If it currently normalises keys, that normalisation is removed.
- [`src/dual_research/ui/models.py`](../src/dual_research/ui/models.py): if there is a typed schema for the piece dict, widen it to `dict[str, int]` keyed by canonical IDs (the registry's `is_known()` predicate is the validator).
- Persistence: per-turn `inputs/<turnKey>.json` keys change to canonical IDs in the same migration. **Backfill is out of scope** — historical runs render with whatever keys they recorded; the UI reads either vocabulary during a transition window via the legacy-key shim, which is deleted in the next minor release.

### 7. Diagram update

`diagrams/deep-research-pipeline.{light,dark}.svg` adds the User-prompt composite to the persistent-input strip more explicitly, replacing the indicative "Attachment 1 / Attachment 2 / Attachment 3 / … per attached source" with a single row labelled `user_prompt.message` plus N rows labelled `user_prompt.attachment.<id>`. The bundled UI copies under `src/dual_research/ui/static/diagrams/` are regenerated.

## Out of scope

- **Output-piece token decomposition.** Per-turn `output_tokens` stays one number, attributed to the turn as a whole. Outputs keep their canonical IDs for provenance and timeline labelling.
- **`pieces_for_finalize()`.** Finalize is programmatic; no model call; no token attribution. The full-view for the final document remains a single-pane content view of `final.document` with no Input tab.
- **Historical run backfill** of `inputs/<turnKey>.json` to canonical keys.
- **Search audit (Web Search) tab restructure.** Untouched.
- **Right-pane (Q/D/I/C) restructure.** Untouched beyond label-confirmation.
- **Cost-per-attachment rendering in the Consumption tab beyond expandable rows.** No new charts or breakdowns; the per-attachment data is exposed, but the existing per-phase bar chart aggregates `user_prompt.*` into one segment as it does today.

## Test plan

- [ ] Unit: `pieces_for_*()` emit `user_prompt.message` + zero-or-more `user_prompt.attachment.<id>` for every phase that takes a user prompt; no aggregate `user_prompt` key remains in any return value.
- [ ] Unit: per phase, asserting the full set of canonical keys against the diagram's arrival-order list, gated by the round/blocked conditionals (`prior_turns.*` from R2+; `closeout.request` only when blocked; etc.).
- [ ] Unit: `is_known()` returns True for every key any `pieces_for_*()` can emit; CI fails on the first orphan key.
- [ ] Unit (cross-language): `artifact-display.js`'s template list parses from a JSON dump emitted by `contract/artifacts.py` at build time; Python and JS template lists must compare equal.
- [ ] Unit: `displayNameOf('user_prompt.attachment.foo', {foo: 'My document'})` returns `Attachment · My document`; falls through to the literal ID when no matching template, as `display_name()` does today.
- [ ] Integration: run a smoke session with a brief + 2 attachments; assert that every `pieces_for_*()` emits two `user_prompt.attachment.<id>` keys, the inputs/<turnKey>.json files persist them, and the aggregator forwards them in `TurnEnded` payloads.
- [ ] Manual: open the briefing card's full view on a multi-attachment run. Verify (i) System prompt and User prompt sections are present, (ii) the User prompt section lists the chat message followed by one row per attachment with its title, (iii) no Sources/Files tabs remain.
- [ ] Manual: open a P0/P2/P4 round modal. Verify the left pane shows the document labelled by its canonical artifact ID; the Input sub-tab matches the canonical-piece layout; the right pane shows the expected Q/D (and Q/D/I/C for P4) cards.
- [ ] Manual: open the Consumption tab. Verify the User-prompt group has an expand affordance that reveals per-attachment rows; collapsed view sums to the same total as today's `user_prompt` segment.
- [ ] Visual regression: snapshot the InputBriefModal and one card from each phase × round combination before/after the refactor; the only intended deltas are (a) attachments now in-section, (b) labels via `displayNameOf()` rather than legacy short keys.

## Risks

- **Cross-language template drift.** Python `REGISTRY` and JS `REGISTRY` can fall out of sync. Mitigation: a CI test that dumps `REGISTRY` to JSON at build time and asserts the JS file matches; failing CI is the only path to a green merge.
- **Persistence format change.** `inputs/<turnKey>.json` keys change. Mitigation: read-path shim that accepts both legacy short keys and canonical IDs during the 1.10.0 release; shim removal in 1.11.0 covered by a separate small spec.
- **Aggregator key normalisation regressions.** If the aggregator previously normalised piece keys, removing that normalisation can corrupt per-phase totals. Mitigation: a regression test that loads a recorded fixture run and asserts piece totals per phase pre/post-refactor.
- **`system.preamble` investigation finds an actual preamble.** Wiring it through every emitter is small but touches every phase's call site. Mitigation: the investigation lands first in the spec's implementation order so the rest of the work absorbs the signature change in one pass.
- **Visual regressions in the side-by-side modals' left-pane labels.** Labels like "Other's prior turn" → `phase0.<agent>.r<N-1>` shown via display name will read differently. Mitigation: confirm the display-name resolution renders human-friendly strings before merge; the snapshot test catches structural breakage.

## Open questions

- Do we want `user_prompt.attachment.<id>` rows in the Consumption tab to render their title (from `attachments.json`) or the raw `<id>`? Default in this spec: title via `displayNameOf()` with `attachmentTitles` map; raw ID as fallback when the title resolver returns null.
- Should the legacy-key shim sunset deadline be encoded as a `# REMOVE AFTER 1.11.0` comment in `run-detail.jsx`, or tracked solely as a follow-up spec? Default: both — comment for in-file visibility, spec for ownership.
- For P3's left-pane label, the table above proposes `phase2.agreement.plan` as the "document being executed". An alternative is `phase0.agreement.interpretation` (the brief the plan implements). Pick one in implementation; both are reasonable, the diagram's section-by-section ordering for P3 suggests the plan is the more proximate cause of the draft.
