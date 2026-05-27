---
spec: 0114
title: Deep Research protocol — canonical methodology, lifecycle, and prompts
label: new-feature
version-bump: MAJOR
status: proposed
target-version: 1.0.0
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0114 — Deep Research protocol (backend, end-to-end)

## Context

The current protocol has accumulated chaotic tracking semantics. Five overlapping ledger kinds (question, disagreement, claim, issue, comment) with different ID schemes (`D-N`, `Q-g-r1-NN`, `Cl-c-p1-NN`, `OAI-P4-NN`, `C-N`, `[I-g-r1-NN]`) and a regex-based claim→disagreement escalation pipeline make the run-to-UI traceability fragile. Status counters are open-snapshots only — `raised this round` vs `resolved this round` are not first-class in events or state, only reconstructed post-hoc by the UI aggregator. Per-item evidence is not linked to specific items. Repair budget is consumed on cosmetic regex misses. The hard-cap behavior has accreted multiple escape valves (canonical-FSD synthesis, stuck-AGREED promotion, force-verbatim-copy) that paper over a missing convergence semantics rather than fixing it.

This spec replaces the entire negotiation protocol with a clean canonical model named **Deep Research**. The methodology is universal and domain-invariant; the brief carries all per-run variability. Every tracked item has a stable orchestrator-assigned ID, a 6-state lifecycle with mutual handshake, rationale required at every state transition, optional per-item evidence with anti-hallucination validation, and full cross-phase provenance flowing into a final-document appendix. A single contract module (`src/dual_research/contract/`) is the source of truth that the prompts, parser, validator, orchestrator, persistence, and downstream UI (spec 0115) all read from.

A backward-compat shim is included so the existing UI keeps rendering during the transition. The UI overhaul and the `validate-run` CLI are scoped to spec 0115 — this spec is the backend protocol foundation.

## Goals

1. **Single source of truth**: one contract module names every category, lifecycle state, marker, status name. Prompts, parser, validator, orchestrator import from it. No duplicated string literals.
2. **Provenance end-to-end**: every tracked item carries `id`, `kind`, `raised_round`, `raised_by`, `current_status`, `status_history` (with rationale at every transition) from raise-time, through every round, through phase boundaries, into the final document.
3. **Convergence honesty**: a phase converges only when both agents emit `AGREED` in the same round, every item is in a terminal state, and the phase artifact hash-matches across both sides. No silent divergence; no escape-valve gymnastics.
4. **Closeout safety**: when agents try to converge but items remain non-terminal, an explicit closeout urge fires; agents get a bounded number of closeout rounds to ratify; remaining non-terminal items auto-cap with a distinct terminal state (`capped`) carrying system-generated rationale.
5. **Evidence integrity**: every item raised with `evidence_required: true` must be addressed with a structured evidence record whose `evidence_event_id` matches a real tool-call event in the same turn, whose URL is in the consulted source set, and whose content excerpt appears in the consulted page content.
6. **Drop the menagerie**: a single, deterministic convergence rule and a single closeout mechanism replace `canonical-FSD synthesis`, `stuck-AGREED promotion`, `force-verbatim-copy repair`, the multi-tier `repair` flow, and the regex-based `claim → disagreement` escalation. Each was a workaround for a missing invariant; the new model gives the invariant.

## Non-goals (in this spec)

- UI rendering changes — scoped to spec 0115
- `validate-run` post-hoc CLI — scoped to spec 0115
- Migration of historical run artifacts to the new schema — old runs stay readable in their legacy shape; the UI's legacy renderer keeps working on them
- Multi-mode support beyond Deep Research — this spec establishes Deep Research as the only mode for now; multi-mode dispatch is future work
- Removing the backward-compat shim — that's scoped to spec 0115 as part of the UI cutover

## Vocabulary & naming

**Mode name**: "Deep Research" (collective name for this methodology — package will live at `src/dual_research/contract/` and the orchestrator will dispatch through `deep_research` mode entry points; the repo name `dual_research` is retained for backward compatibility).

**Phase names** (descriptive, used in user-facing surfaces and in the contract module):

| code phase | descriptive name | shape |
|---|---|---|
| phase 0 | input | multi-round, interaction |
| phase 1 | research-plan | one-shot parallel, production |
| phase 2 | negotiate-plan | multi-round, interaction |
| phase 3 | draft | one-shot single agent, production |
| phase 4 | review-draft | multi-round, interaction |
| finalize | finalize | orchestrator-only, no LLM call |

The legacy `phase0/` … `phase4/` filesystem layout is retained. Descriptive names are aliases used in prompts and the contract module.

**Phase tokens used in stable IDs**: `input`, `plan`, `review`. (Phases 1 and 3 don't raise items, so they have no token.)

## Categories

Four canonical categories. Same vocabulary used across every phase that allows raising; categories differ only in which phase(s) they are allowed in.

| kind | first-letter token (in IDs) | raisable in | resolvable in | typical raiser intent |
|---|---|---|---|---|
| `question` | `Q` | input, plan, review | same phase or later via closeout | "I don't know; the other agent does or should research it" |
| `disagreement` | `D` | input, plan, review | same phase or later via closeout | "I hold position X; the other agent holds Y; we differ on substance" |
| `issue` | `I` | review only | review | "the drafted document is defective in a specific way" |
| `comment` | `C` | review only | review | "the drafted document could be improved in a specific non-defect way" |

The `claim` kind is **removed**. Items previously in the `## Claims I expect the other agent might dispute` section are gone — the new prompts do not ask for them. Inline `[V]` / `[U]` source tagging on material factual claims in body prose **remains exactly as today** — those are inline annotations, not tracked items.

Brief-issues (the phase 0 `BRIEF_ISSUES` count today) is **removed as a counter**. The same content is now first-class `question` and `disagreement` items raised in phase 0 about the brief, with stable IDs.

## Item lifecycle

Every tracked item, regardless of category, lives in one of six states.

**States**:

| state | terminal? | who can set it | meaning |
|---|---|---|---|
| `open` | no | raiser at first appearance | item exists; addressee has not responded |
| `addressed` | no | addressee in response turn | response provided; raiser has not ratified |
| `resolved` | yes | raiser only | raiser explicitly ratified the response |
| `acknowledged` | yes | both parties (mutual handshake) | both agreed the item cannot be resolved within this run |
| `withdrawn` | yes | raiser only | raiser explicitly retracted |
| `capped` | yes | orchestrator only | hard cap reached without terminal handshake; orchestrator force-closed |

**Transitions** (and who triggers each):

```
                         (raiser)
                       ┌──────────► resolved
                       │
                       │  (mutual:
                       │   both emit
   (raiser)  (addressee)│   ACKNOWLEDGE
   open ───────► addressed in consecutive
       ▲         │     │   turns)
       │         │     └──────────► acknowledged
       │         │
       │   (raiser counter-argues)
       └─────────┘
                       (raiser)
                       ┌──────────► withdrawn
                       │
                       │ (orchestrator, only
                       │  at hard cap or
                       │  ghost-cap)
                       └──────────► capped
```

**Rationale required at every state transition**. The `LedgerStatusTransition.reason` field (already in `src/dual_research/ledger/models.py`) is made mandatory at the prompt level: every RESOLVE / ACKNOWLEDGE / WITHDRAW / counter-argument operation block must include a non-empty `reason:` field. The validator rejects operations without rationale.

**`acknowledged` is mutual**. A single ACKNOWLEDGE block by either party is a *proposal*. The item flips to terminal `acknowledged` only when both parties have emitted ACKNOWLEDGE for the same item ID in consecutive turns. Until then, the item stays in its current state (`open` or `addressed`). No intermediate `acknowledged_pending` state is needed — the state machine handles the mutuality in the orchestrator's post-round update step.

**`capped` is orchestrator-only**. Agents cannot emit `STATUS: capped` for an item; only the orchestrator sets this state, and it does so under two conditions: (a) hard cap reached for the phase with non-terminal items remaining; (b) ghost-cap (the agent failed to ratify items across the closeout budget — see closeout section below). Each `capped` transition records which of the two paths fired via a `via:` field on the transition: `via: hard_cap` or `via: ghost_cap`.

## Stable IDs

Format: **`<kind>-<phase>-<raiser>-<seq>`**

| component | values |
|---|---|
| `kind` | `Q` (question), `D` (disagreement), `I` (issue), `C` (comment) |
| `phase` | `input`, `plan`, `review` |
| `raiser` | `c` (claude), `g` (gpt) |
| `seq` | zero-padded 2-digit, monotonic per (kind, phase, raiser) namespace |

Examples: `Q-input-c-01`, `D-plan-g-04`, `I-review-c-12`, `C-review-g-03`.

**Rules**:

- IDs are **assigned by the orchestrator at parse time**, not by the agent. The agent emits `### RAISE` blocks with `kind` and `body` only; the parser stamps the next available sequence in the (kind, phase, raiser) namespace.
- IDs are **immutable** once assigned. An item that flips to `withdrawn` or `acknowledged` retains its ID forever.
- Sequence is **monotonic per phase, not per round**. If an agent raises 3 items in round 1 and 2 more in round 3, the sequences are 01..05, not 01..03 + 01..02.
- IDs are **globally unique within a run** by construction.
- All legacy ID schemes (`D-N`, `Q-g-r1-NN`, `Cl-c-p1-NN`, `OAI-P4-NN`, `[I-g-r1-NN]`) are removed from prompts. Legacy run artifacts on disk are not migrated.

## Evidence model

**Per-item flag**: every RAISE block sets `evidence_required: true | false`. The raiser declares whether resolving this specific item requires external evidence (web search results — not citations of the brief or attached documents, which are reference, not evidence).

**Category-level guidance in prompts** (not enforced — agent picks the flag per-item):

| category | typical evidence requirement |
|---|---|
| question | usually true (an answer often needs a source) |
| disagreement | usually true when resolution turns on a factual claim |
| issue | usually false (defects are observable from the draft) |
| comment | usually false (suggestions don't need external sources) |

**Evidence record structure**. When addressing an item with `evidence_required: true`, the addressing turn must emit one or more linked evidence records:

```
### EVIDENCE for D-plan-g-04
- url: <full URL>
- title: <page title>
- search_query: <the query the agent used>
- fetched_at: <ISO-8601 UTC timestamp>
- evidence_event_id: <tool_call_id from the provider; must match a ToolEvent in this turn's TurnSearchAudit>
- content_excerpt: |
    <≥ 200 chars and ≤ 2000 chars of the actual page body the agent consulted;
     must appear as a substring in the consulted content after light normalization>
```

**Cardinality**:

- One item → many evidence records (a disagreement may be backed by multiple sources).
- One evidence record → exactly one item ID (no shared records across items; emit twice if the same source backs two items).

**Anti-hallucination validation** (runs at parse time, rejects the turn if any check fails):

1. `evidence_event_id` MUST correspond to a real `ToolEvent.event_id` in the same turn's `TurnSearchAudit` payload (already captured per Spec 0036 in `src/dual_research/audit/schema.py`). A turn that references a fabricated event_id is rejected with flag `evidence_event_id_fabricated`.
2. The `url` MUST appear in the `consulted_sources` of the referenced `ToolEvent`. Otherwise: flag `evidence_url_not_consulted`.
3. The `content_excerpt` MUST appear as a substring of the consulted content (after light normalization — whitespace collapse, smart quote folding, line-ending normalization). Otherwise: flag `evidence_content_not_in_source`.

A failed evidence validation makes the entire ADDRESS operation invalid — the item is not transitioned to `addressed`, and the orchestrator emits a `closeout_urged` event for it in the next round. Today's `cited_url_not_in_consulted_sources` flag (audit/validate.py:115) becomes a hard rejection, not a soft warning.

## Per-turn output contract

One canonical turn structure for every interaction-phase round (input, negotiate-plan, review-draft). Phase artifact section appears only when emitting `AGREED`. Counter sub-fields vary slightly by phase (issues/comments counters only appear in review-draft).

### Sections in order

```
## Stance

(2–4 sentence prose summary of my position this round. The UI uses this
as the timeline-card TL;DR.)

## Addressing items raised against me

(One ADDRESS block per currently-open item where I am the addressee.
 Each block contains the response body, optional linked evidence records,
 and a proposes_status field.)

## Ratifying my own items

(One operation block per currently-addressed item that I raised. Each is
 one of RESOLVE, ACKNOWLEDGE, WITHDRAW, or a counter-argument that flips
 the item back to open with rationale. No silent skipping; the validator
 rejects turns missing required ratifications.)

## New items I'm raising

(Zero or more RAISE blocks. Each declares kind, body, anchor, and
 evidence_required flag. The orchestrator assigns the stable ID at
 parse time.)

## Phase artifact          ← only when emitting STATUS: AGREED

(The hash-matched canonical block: AGREED_INTERPRETATION for phase 0,
 AGREED_PLAN for phase 2, AGREED_DRAFT_ACCEPTANCE for phase 4.
 Absent in non-AGREED turns.)

## Status

(Machine-readable footer — STATUS line + action arrays + per-kind
 running counts. The orchestrator parses this for convergence checks
 and drift detection.)
```

### The 5 operation block types

**RAISE** (in `## New items I'm raising`):

```
### RAISE
kind: question | disagreement | issue | comment
body: |
  <the question / argument / defect / comment text>
anchor_type: quote | after | none
anchor_text: <verbatim ≤25-word span from prior content, or section heading, or "">
evidence_required: true | false
```

The orchestrator stamps the ID at parse time.

**ADDRESS** (in `## Addressing items raised against me`):

```
### ADDRESS <item-id>
response: |
  <my answer / counter-argument / acknowledgment that the item is valid + fix description>
evidence:
  - url: ...
    title: ...
    search_query: ...
    fetched_at: ...
    evidence_event_id: ...
    content_excerpt: |
      ...
  - (additional evidence records if multiple sources)
proposes_status: addressed | acknowledged_proposed
```

`proposes_status: addressed` (default) — "here's my response; awaiting your ratification".
`proposes_status: acknowledged_proposed` — "I see no path to resolution; I propose we acknowledge this is irreconcilable; over to you to ratify with your own ACKNOWLEDGE block or counter-argue".

Evidence block is required when the item's `evidence_required: true`; otherwise optional.

**RESOLVE** (in `## Ratifying my own items`):

```
### RESOLVE <item-id>
reason: |
  <why I accept this resolution — what specifically about the response or
   evidence moved me from my prior position>
```

Required: non-empty `reason` referencing the response substance.

**ACKNOWLEDGE** (in `## Ratifying my own items` or `## Addressing items raised against me`):

```
### ACKNOWLEDGE <item-id>
reason: |
  <why this item cannot be resolved within the current run — interpretive
   gap, lack of data, scope mismatch, etc.>
```

The state machine in the orchestrator transitions the item to terminal `acknowledged` only when both parties have emitted ACKNOWLEDGE blocks for the same item ID in consecutive turns. A single ACKNOWLEDGE leaves the item in its current state with a `acknowledge_proposed_by: <agent>` flag on the entry.

**WITHDRAW** (in `## Ratifying my own items`):

```
### WITHDRAW <item-id>
reason: |
  <why I'm retracting — superseded by another item, immaterial after
   reflection, mistaken raise, etc.>
```

Required: non-trivial reason. Withdrawals with empty reason are rejected.

### Anchor format

For RAISE blocks, the anchor optionally ties the item to a specific span in prior content:

- `anchor_type: quote` + `anchor_text: <verbatim span>` — anchors to existing content the item is critiquing.
- `anchor_type: after` + `anchor_text: <section heading>` — anchors to a missing-content slot the item proposes should be filled.
- `anchor_type: none` — un-anchored (general item, not tied to a specific span).

The anchor text is also embedded as a blockquote line directly under the RAISE block, preserving the existing UI side-by-side viewer convention:

```
### RAISE
kind: question
...
> quote: <verbatim ≤25-word span>
```

This dual representation (structured field + blockquote line) is intentional — the blockquote serves the existing markdown rendering path; the structured field is what the parser uses.

### Status footer

```
## Status
STATUS: IN_PROGRESS | AGREED

# Action arrays this turn (orchestrator-assigned IDs)
RAISED_THIS_TURN: [Q-plan-c-04, D-plan-c-05]
ADDRESSED_THIS_TURN: [Q-plan-g-02, D-plan-g-04]
RESOLVED_THIS_TURN: [D-plan-c-01]
ACKNOWLEDGED_THIS_TURN: [Q-plan-c-03]
WITHDRAWN_THIS_TURN: []

# Per-kind running counts from my perspective on items I raised
OPEN_QUESTIONS: 2
OPEN_DISAGREEMENTS: 1
OPEN_ISSUES: 0          ← present only in review-draft phase
OPEN_COMMENTS: 0        ← present only in review-draft phase
ADDRESSED_QUESTIONS: 1
ADDRESSED_DISAGREEMENTS: 0
ADDRESSED_ISSUES: 0     ← review-draft only
ADDRESSED_COMMENTS: 0   ← review-draft only
```

- `STATUS` is the phase-level intent for this turn. Only two values universal across all interaction phases.
- Action arrays carry stable IDs. Since IDs encode `kind+phase+raiser`, all per-kind and per-raiser breakdowns are derivable by the orchestrator. The agent does not break these down.
- Per-kind running counts are self-reported by the agent for **items they raised**. The orchestrator's ledger independently computes the same counts; mismatch fires a `LedgerDrift` event (spec 0043's existing mechanism). Drift signals are a debugging surface, not a hard reject.
- In phase 0 and phase 2 (only Q and D allowed), `OPEN_ISSUES` and `OPEN_COMMENTS` are not emitted; the parser tolerates either absence or zero values.

## Phase artifacts

Each interaction phase has a hash-matched artifact block. Both agents emit byte-identical text when reaching `STATUS: AGREED`. The orchestrator computes a normalized SHA-256 hash of each side's block; convergence requires the hashes to match.

### Phase 0 — `AGREED_INTERPRETATION`

```
### AGREED_INTERPRETATION

#### Scope
- In scope:
  - <bullet>
  - <bullet>
- Out of scope:
  - <bullet>
  - <bullet>

#### Approach
<one paragraph: how the research will be conducted, what stance the
 agents are taking, what weightings apply, what posture they have
 toward the source materials>

#### Carry-forward items
- [Q-input-c-04] open: <body> — to be researched in phase 1
- [D-input-g-02] acknowledged: <body> — flagged as briefing limitation
(or "(none)" if nothing carries forward)
```

The carry-forward section is the structured statement of what phase 0 produced as constraints on phase 1: questions still open (research them), disagreements still acknowledged (note them as briefing limitations).

### Phase 2 — `AGREED_PLAN`

```
### AGREED_PLAN

#### Sections
1. Title: <section title>
   Key claims:
   - <key claim>
   - <key claim>
2. Title: <section title>
   Key claims:
   - <key claim>
   …

#### Carry-forward items (from phase 2)
- [D-plan-g-04] acknowledged: <body> — to appear in surfaced-disagreements section of final
- [Q-plan-c-07] acknowledged: <body> — to appear in open-questions section of final
(or "(none)")

#### Drafter
DRAFTER: claude | openai
```

The `DRAFTER` line is part of the hashed artifact — drafter selection is not a side parameter; it is part of what the agents agreed to.

### Phase 4 — `AGREED_DRAFT_ACCEPTANCE`

```
### AGREED_DRAFT_ACCEPTANCE

draft_version: v7
draft_hash: <SHA-256 of the draft file content, lowercase hex>
endorsement: |
  <one sentence on why this draft satisfies the brief>
```

Phase 4's "artifact" is the draft file itself, which lives on disk. The acceptance block records which version both agents are agreeing to and includes the file's content hash so the orchestrator can verify they're agreeing to the same bytes.

Cross-check at phase 4 convergence: both agents emit identical `draft_version` + `draft_hash`, AND the drafter did NOT emit a `## Revised draft` section in this round (the draft pointer is stable for this round, both agents reviewed the same file).

## Convergence rules

A phase converges when **all three** conditions are met **in the same round**:

1. Both agents emit `STATUS: AGREED` in their respective turns of this round.
2. The orchestrator's ledger has **zero non-terminal items** at end-of-round (no `open` items, no `addressed` items from either raiser; only `resolved` / `acknowledged` / `withdrawn` / `capped` items remain).
3. The phase artifact hash-matches across both agents (`AGREED_INTERPRETATION` block / `AGREED_PLAN` block + drafter line / `AGREED_DRAFT_ACCEPTANCE` block + stable draft pointer).

If any of the three fails, the phase does not converge and the closeout mechanism may fire (see below). No partial convergence, no escape valves, no canonical-FSD synthesis, no stuck-AGREED promotion.

**Drafter selection** (phase 2 only): chosen by the agents in their `AGREED_PLAN` blocks. Both must declare the same drafter for convergence to fire. At hard cap with non-matching drafter declarations, the orchestrator picks the agent with the higher `DOMAIN_FIT_OTHER` value from the most recent round (the agent whose fit was rated higher by the other side). If still tied (same fit-other rating), default to `claude`. This replaces the multi-tier tiebreak chain.

## Closeout mechanism (replaces "repair")

The closeout mechanism replaces the multi-tier `repair` flow with a simpler design: nudge when convergence is attempted but blocked by non-terminal items, with a bounded budget.

### Trigger

The closeout mechanism fires when **both agents emit `STATUS: AGREED` in the same round** but condition 2 of convergence fails — there are still non-terminal items. The agents tried to converge but left loops open.

### Mechanism

1. The orchestrator emits a `closeout_urged` event listing the non-terminal item IDs grouped by raiser.
2. The next round is a **closeout round**. Each agent's prompt receives a `closeout_request` section listing items they need to act on (items they raised that are non-terminal, items addressed at them that are still open).
3. The closeout round prompt restricts the agent to closing operations only: RESOLVE, ACKNOWLEDGE, WITHDRAW, or counter-argument for already-open items they raised. **No RAISE blocks are permitted in a closeout round.** Any RAISE block in a closeout turn is silently dropped by the parser and recorded as a `closeout_violation` event.
4. After both closeout-round turns are written, the orchestrator re-checks convergence (the three conditions).
5. If convergence passes → phase converges with `via_closeout: true` flag on the phase-complete event.
6. If convergence still fails → check budget.

### Closeout budget

Each agent has **a closeout budget of 2 per phase**. Each failed closeout round (the agent did not bring all their non-terminal items to terminal state) decrements the budget by 1. When an agent's budget reaches 0 and a subsequent closeout round still leaves non-terminal items raised by that agent:

- Those non-terminal items auto-flip to `capped` with `via: ghost_cap` on the transition record and an orchestrator-generated rationale: *"Agent <name> exhausted closeout budget (2 closeout rounds) without bringing this item to a terminal state; auto-capped at round N."*
- The phase converges via this auto-cap path (`via_ghost_cap: true` on the phase-complete event).

### Hard cap

Independent of the closeout mechanism, each phase has a hard cap on rounds:

| phase | soft cap | hard cap |
|---|---|---|
| input | 2 | 4 |
| negotiate-plan | 4 | 8 |
| review-draft | 4 | 8 |

When the hard cap is hit before convergence, all non-terminal items auto-flip to `capped` with `via: hard_cap` on the transition record and an orchestrator-generated rationale. The phase converges with `via_hard_cap: true` flag.

The soft cap is a signal-only event (`soft_cap_hit`) for UI / logging; no behavior change. The hard cap is the actual ceiling.

## Cross-phase carryover

Items are **frozen at phase boundaries**. Once a phase converges (whether organically, via closeout, ghost-cap, or hard-cap), every item in that phase is in a terminal state. From the next phase onward, those items are read-only history:

- They cannot be re-raised, re-opened, re-ratified, withdrawn, or modified.
- They appear in the ledger as historical record, fully queryable by ID.
- They contribute to the final-document appendix.

Phase 0 items do NOT carry forward as live entities into phase 2; they are summarized in the `AGREED_INTERPRETATION` block (which is part of phase 2's input). Phase 2 items do not carry forward as live entities into phase 4; they are embedded in the draft (which is phase 4's input). Phase 4 items are terminal at phase end.

The final document's appendix is assembled by the finalize step from all terminal-not-resolved items across all phases. Items with `current_status` in `{acknowledged, capped}` are surfaced; items with `current_status == withdrawn` are surfaced only when the withdrawal `reason` is non-trivial (heuristic: reason text length > 40 characters AND does not match patterns like "duplicate of", "superseded by"). Resolved items do not appear in the appendix (they are part of the substance of the document body).

Appendix structure produced in the final document:

```
## Appendix — Unresolved items

### Briefing limitations (phase 0)
- [Q-input-c-01] acknowledged: <body>
  - Raised by: Claude in round 1
  - Acknowledged in round 3
  - Reason: <terminal-reason text>
- [D-input-g-02] capped (hard cap): <body>
  - Raised by: GPT in round 2
  - Capped in round 4
  - Reason: <orchestrator-generated text>

### Surfaced disagreements (negotiate-plan phase)
…

### Unanswered research questions (negotiate-plan phase)
…

### Known issues in this draft (review-draft phase)
…

### Pending comments (review-draft phase)
…
```

Each row carries the item ID, terminal state, body, raiser, raised-round, terminal-round, and terminal-reason. The final-document appendix is a complete trace of every loose end in the run.

## Central contract module

A new package `src/dual_research/contract/` defines all the constants, enums, regexes, and validators that the rest of the system imports from. Nothing else duplicates these literals.

### Files

```
src/dual_research/contract/
  __init__.py            — public surface
  categories.py          — Category enum, raisable_in / resolvable_in maps
  lifecycle.py           — State enum, transition table, terminal predicate
  ids.py                 — ID format spec, parse/format functions
  markers.py             — section heading + counter marker patterns (compiled regexes)
  operations.py          — operation block schemas (RAISE/ADDRESS/RESOLVE/ACKNOWLEDGE/WITHDRAW)
  evidence.py            — evidence record schema + anti-hallucination rules
  artifacts.py           — phase artifact templates (interpretation/plan/draft-acceptance)
  validator.py           — turn-level validator (validate_turn(text, phase, round, agent))
  caps.py                — soft/hard cap defaults per phase
  status.py              — STATUS enum + counter field names per phase
```

### `categories.py`

```python
from enum import StrEnum
from typing import FrozenSet

class Category(StrEnum):
    QUESTION = "question"
    DISAGREEMENT = "disagreement"
    ISSUE = "issue"
    COMMENT = "comment"

ID_TOKEN = {
    Category.QUESTION: "Q",
    Category.DISAGREEMENT: "D",
    Category.ISSUE: "I",
    Category.COMMENT: "C",
}

# Phase names as used in IDs and prompts
PHASE_TOKEN = {
    0: "input",
    2: "plan",
    4: "review",
}

# Per-phase allow-set: which categories can be raised in which phase
RAISABLE_IN: dict[int, FrozenSet[Category]] = {
    0: frozenset({Category.QUESTION, Category.DISAGREEMENT}),
    2: frozenset({Category.QUESTION, Category.DISAGREEMENT}),
    4: frozenset({Category.QUESTION, Category.DISAGREEMENT,
                  Category.ISSUE, Category.COMMENT}),
}
```

### `lifecycle.py`

```python
from enum import StrEnum

class State(StrEnum):
    OPEN = "open"
    ADDRESSED = "addressed"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    WITHDRAWN = "withdrawn"
    CAPPED = "capped"

TERMINAL_STATES = frozenset({State.RESOLVED, State.ACKNOWLEDGED,
                              State.WITHDRAWN, State.CAPPED})

# Valid transitions: from → set of allowed to-states (plus who can trigger)
TRANSITIONS = {
    State.OPEN: {
        State.ADDRESSED:    {"actor": "addressee"},
        State.WITHDRAWN:    {"actor": "raiser"},
    },
    State.ADDRESSED: {
        State.RESOLVED:     {"actor": "raiser"},
        State.OPEN:         {"actor": "raiser"},  # counter-argument
        State.WITHDRAWN:    {"actor": "raiser"},
        State.ACKNOWLEDGED: {"actor": "mutual",
                             "requires": "ack-from-both-in-consecutive-turns"},
    },
    # capped is orchestrator-only; not in agent transition table
}

CAPPED_VIA = {
    "hard_cap": "Hard cap reached for the phase",
    "ghost_cap": "Closeout budget exhausted; non-terminal items auto-capped",
}
```

### `ids.py`

```python
import re
from contract.categories import Category, ID_TOKEN, PHASE_TOKEN

ID_PATTERN = re.compile(r"^([QDIC])-(input|plan|review)-([cg])-(\d{2})$")

def format_id(kind: Category, phase_token: str, raiser: str, seq: int) -> str:
    return f"{ID_TOKEN[kind]}-{phase_token}-{raiser}-{seq:02d}"

def parse_id(item_id: str) -> tuple[Category, str, str, int]:
    m = ID_PATTERN.match(item_id)
    if not m:
        raise ValueError(f"malformed item ID: {item_id}")
    kind_token, phase_token, raiser, seq = m.groups()
    kind = next(k for k, tok in ID_TOKEN.items() if tok == kind_token)
    return kind, phase_token, raiser, int(seq)
```

### `markers.py`

All regexes for section headings, counter markers, and operation block recognizers are compiled here. The parser (`src/dual_research/protocol/parse.py`) imports from this module; no regex literals live in `parse.py`.

Tolerance patterns (existing `_LEAD = r"^[\s>*\-`#]*"` style) are preserved. The `EVIDENCE_CHECKED_SECTION_RE` brittleness from the bug we found (header glued to body with no newline) is fixed in this module by using a more tolerant boundary: `(?=\b|[A-Z])` after the heading text instead of plain `\b`.

### `validator.py`

The top-level entry point is:

```python
def validate_turn(
    text: str,
    *,
    phase: int,
    round: int,
    agent: str,
    is_closeout_round: bool = False,
) -> ValidationResult: ...
```

Returns a `ValidationResult` with `valid: bool` and `errors: list[ValidationError]`. Errors include:

- Missing required sections (`## Stance`, `## Status`, `## Phase artifact` when AGREED, etc.)
- Malformed operation blocks (missing fields, malformed item IDs in references)
- Operations on items in invalid states (e.g. RESOLVE on an `open` item — must be `addressed` first)
- Counter drift between self-reported and ledger-computed values
- Missing rationale on transitions
- Evidence validation failures (event_id fabricated, URL not in consulted sources, content excerpt not in source)
- Closeout violations (RAISE in a closeout round, unrequired operations)
- Raising disallowed categories for the phase (e.g. raising an `issue` in phase 0)

Each error has a `severity` of `error` (rejects the turn) or `warning` (logged but not rejecting). The parser drives turn rejection / repair via the error severities.

## Parser updates

`src/dual_research/protocol/parse.py` is rewritten around the contract module. Key changes:

1. **All regex literals move to `contract/markers.py`**. The parser file becomes a thin coordinator that calls into typed extraction functions.
2. **Operation blocks (`### RAISE` / `### ADDRESS` / `### RESOLVE` / `### ACKNOWLEDGE` / `### WITHDRAW`) are parsed into typed dataclasses** (`RaiseBlock`, `AddressBlock`, etc.). The parser walks the markdown's `### ` headings and dispatches to per-type extractors. Field parsing is YAML-style (`key: value` or `key: |` with following indented block).
3. **The `EVIDENCE_CHECKED_SECTION_RE` regex is fixed** to tolerate headers glued to body text (the bug from the run we audited — `## Evidence checked this roundThe ...` is now matched).
4. **Item ID assignment is added**. After parsing a turn's RAISE blocks, the parser queries the ledger for the next available sequence per (kind, phase, raiser) namespace and stamps the IDs in place. The IDs become canonical from this point.
5. **Anti-hallucination evidence validation** is implemented as a parse-time check that requires the turn's `TurnSearchAudit` (already collected per Spec 0036). The parser refuses to mark an item as `addressed` if any of the three evidence checks fail.

The legacy `OPEN_QUESTIONS_RE` / `OPEN_ISSUES_RE` / `BLOCKING_DISAGREEMENTS_RE` / `FINAL_SURFACED_DISAGREEMENTS_RE` / `DRAFTER_RE` / `STRONGEST_REMAINING_OBJECTION_RE` regexes are retained inside the contract module's markers file because they appear in the legacy event payloads that the backward-compat shim still emits. They are deprecated and will be removed in spec 0115.

## New prompts (full text)

All prompt construction lives in `src/dual_research/protocol/prompts.py`. The existing function names are replaced; the function bodies emit the new prompts.

### Common preamble — `_COMMON_PREAMBLE`

Included in every prompt. Establishes role, methodology, tone.

```
You are participating in a Deep Research run with another large language
model from a different family. Your shared goal is to critically improve
the input — research it, surface disagreements, resolve them with
evidence, and converge on a single document that is better than what
either of you could produce alone.

Two failure modes — equally bad:

- Sycophancy: agreeing because disagreement is awkward, or because the
  conversation has gone on long enough. Your job is not to be pleasant;
  it is to be useful. Do not flip to AGREED to end the loop. If you
  cannot articulate why you accept the other side's argument, do not
  accept it.

- Adversarialism: manufacturing or re-litigating differences that do
  not materially change the final document. Concede when the other
  side's evidence is stronger. The goal is the best document, not the
  longest debate. If you raise a disagreement, you must be able to
  state in one sentence how resolving it one way versus the other would
  change the final document; if you can't, drop it.

Before every turn, write — privately, in your reasoning — your strongest
objection to your own current position if you were arguing the opposite.
If you cannot articulate one, that is itself a signal you may be
acquiescing.

## Source tagging

Every material factual claim in your body prose must carry one of:

- [V] — Verified this run. Backed by a source you retrieved this run
  via web search or another tool. The URL must be one the tool returned.
- [U] — Unverified this run. From your training weights or by reasoning;
  you did not retrieve a source this run.

Being honest about [U] is more valuable than over-claiming [V]. Tagging
accurately is the goal — tagging every claim is not.

## Tracked items

You and the other agent track items across rounds. There are four
canonical categories:

- question — something you need to know that you believe the other
  agent can answer or research.
- disagreement — a substantive position where you and the other agent
  differ on what is true or what should be done.
- issue — (review phase only) a defect in the drafted document.
- comment — (review phase only) a non-defect suggestion on the drafted
  document.

Each item has a stable ID (e.g. Q-plan-c-04, D-input-g-02). The
orchestrator assigns the ID when you raise the item; you do not pick
the sequence number. Once assigned, the ID is permanent — across
rounds, across phases, across resolution.

Every item lives in one of these states:

- open — you raised it; the other agent has not responded.
- addressed — the other agent responded; you have not ratified.
- resolved — you (the raiser) accepted the response. Terminal.
- acknowledged — both of you agreed the item cannot be resolved within
  this run. Terminal. Reached by both emitting an ACKNOWLEDGE block for
  the same item in consecutive turns.
- withdrawn — you retracted it. Terminal.
- capped — the orchestrator force-closed it (you ran out of rounds or
  ran out of closeout budget). Terminal.

Every state transition you trigger must carry a non-empty reason. The
reason is required, not optional. The system rejects turns with empty
rationales.

## Evidence

When you raise an item, you declare evidence_required: true | false.
When you address an item with evidence_required: true, your response
must include one or more structured EVIDENCE records, each tied to a
real tool call you made this turn (its event_id), with the source URL,
the search query you used, and a ≥200-character excerpt of the actual
page content you consulted. The system validates each evidence record
against the turn's tool-call audit; fabricated evidence makes your
ADDRESS operation invalid.

## Output protocol

Your turn must follow the structured output protocol exactly. See the
phase-specific instructions below for the section template and the
operation block formats. Failure to follow the protocol causes the
turn to be rejected.
```

### Phase 0 round 1 — `preflight_prompt`

```python
def preflight_prompt(*, brief_content: str, agent_name: str, other_name: str) -> str:
    return COMMON_PREAMBLE + f"""
# Phase 0 (input): brief critique — round 1

You are agent "{agent_name}". The other agent is "{other_name}". You are
both reading the brief for the first time. Your job this round:

1. Read the brief carefully.
2. State your interpretation of what the brief is asking for — scope,
   approach, key questions. (Do not start the actual research yet; this
   phase is about agreeing on the task, not doing it.)
3. Raise any questions you have about the brief that need clarification
   (kind: question, raised in phase 0).
4. Raise any disagreements you have with how the brief is framed,
   what's in/out of scope, missing inputs, or framing flaws (kind:
   disagreement, raised in phase 0).

You will see {other_name}'s first-round critique starting in round 2,
at which point the negotiation begins — you address each other's items,
ratify your own that get addressed, and converge on a shared
AGREED_INTERPRETATION block.

## Inputs

{{brief_content}}

## Output

Produce a turn with the canonical section structure (see preamble).
Section breakdown for THIS round:

## Stance
(2–4 sentences: your reading of the task and the posture you're taking.)

## Addressing items raised against me
(none — first round)

## Ratifying my own items
(none — first round)

## New items I'm raising
(RAISE blocks for each question and disagreement you have about the
 brief. Be specific, anchor with > quote: when possible.)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: [list of IDs the orchestrator will assign]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: <int>
OPEN_DISAGREEMENTS: <int>
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0

(No phase artifact block at round 1 — phase 0 cannot converge in round 1.)
"""
```

### Phase 0 round N (N≥2) — `input_negotiation_prompt`

```python
def input_negotiation_prompt(
    *,
    brief_content: str,
    prior_turns: Iterable[PriorTurn],
    standing_items: str,
    agent_name: str,
    other_name: str,
    round: int,
    soft_cap: int,
    hard_cap: int,
    is_closeout_round: bool = False,
    closeout_request: str = "",
) -> str:
    return COMMON_PREAMBLE + f"""
# Phase 0 (input): brief critique — round {round}

You are agent "{agent_name}". This is round {round} of phase 0
(soft cap {soft_cap}, hard cap {hard_cap}). Phase 0 converges when both
of you emit STATUS: AGREED in the same round, all items are terminal,
and your AGREED_INTERPRETATION blocks hash-match.

## Inputs

{{brief_content}}

{{prior_turns_section}}

{{standing_items_section — items raised across rounds that are not yet terminal}}

{{closeout_request_section — only when this is a closeout round}}

## Output

Produce a turn with the canonical section structure.

## Stance
(2–4 sentences summarizing your position this round.)

## Addressing items raised against me
(ADDRESS block per currently-open item from {other_name} pointed at you.
 Each addresses with response body + evidence if required +
 proposes_status. ACKNOWLEDGE blocks here when you see no path
 to resolution.)

## Ratifying my own items
(For every one of your raised items currently in `addressed` state,
 emit RESOLVE, ACKNOWLEDGE, WITHDRAW, or a counter-argument that flips
 it back to open. Silent skipping is rejected.)

## New items I'm raising
(RAISE blocks for genuinely new questions or disagreements. Do not
 re-raise items that are already in the ledger.)

## Phase artifact         ← only when emitting STATUS: AGREED

### AGREED_INTERPRETATION

#### Scope
- In scope:
  - <bullet>
- Out of scope:
  - <bullet>

#### Approach
<paragraph>

#### Carry-forward items
- [<id>] <terminal-state>: <body> — <one-line rationale for carrying forward>
(or "(none)")

## Status
STATUS: IN_PROGRESS | AGREED
RAISED_THIS_TURN: [...]
ADDRESSED_THIS_TURN: [...]
RESOLVED_THIS_TURN: [...]
ACKNOWLEDGED_THIS_TURN: [...]
WITHDRAWN_THIS_TURN: [...]
OPEN_QUESTIONS: <int>
OPEN_DISAGREEMENTS: <int>
ADDRESSED_QUESTIONS: <int>
ADDRESSED_DISAGREEMENTS: <int>

## Closeout constraints (if this is a closeout round)
{closeout_request_message}
You may emit only RESOLVE, ACKNOWLEDGE, WITHDRAW, or counter-argument
operations on the listed items. RAISE blocks are not permitted in a
closeout round and will be silently dropped.
"""
```

### Phase 1 — `research_plan_prompt`

```python
def research_plan_prompt(
    *,
    brief_content: str,
    agreed_interpretation: str,
    agent_name: str,
) -> str:
    return COMMON_PREAMBLE + f"""
# Phase 1 (research-plan): produce your research plan and initial thesis

You are agent "{agent_name}". You have completed phase 0 jointly with
the other agent and you both agreed on the AGREED_INTERPRETATION block
below. Your job in this phase is single-shot and parallel — the other
agent is producing their own plan + thesis at the same time, and you
will not see theirs until phase 2.

This is a PRODUCTION phase. You do not raise tracked items in this
phase. You do not address items. You do not emit the operation blocks
(RAISE / ADDRESS / RESOLVE / ACKNOWLEDGE / WITHDRAW). Phase 1's only
output is the plan + thesis as prose.

You will, however, continue to use inline [V] and [U] tags on material
factual claims in your body prose.

## Inputs

{{brief_content}}

{{agreed_interpretation_block}}

## Output

Produce a single markdown document with these sections (headings
verbatim):

## 1. Summary
3–5 sentences capturing your core findings and bottom-line thesis.

## 2. My thesis
1–3 sentences stating the judgment you currently believe is most
correct. If the brief is purely descriptive, state which findings you
are most confident in and which you are least confident in.

## 3. Detailed findings
The substance — organized according to the agreed scope and approach.
This is where the bulk of your phase 1 work goes. Cite sources inline.

## 4. Sources
Numbered list with URLs.

Do not include "Claims I expect the other agent might dispute" or
"Open questions" sections — those are NOT part of the new phase 1
output. Disagreements and questions are raised in phase 2, not here.
Phase 1 is your independent draft; the negotiation comes next.
"""
```

### Phase 2 round 1 — `plan_negotiation_round1_prompt`

```python
def plan_negotiation_round1_prompt(
    *,
    brief_content: str,
    agreed_interpretation: str,
    own_plan: str,
    other_plan: str,
    agent_name: str,
    other_name: str,
) -> str:
    return COMMON_PREAMBLE + f"""
# Phase 2 (negotiate-plan): plan negotiation — round 1

You are agent "{agent_name}". The other agent is "{other_name}". You
have both produced your phase 1 plans + theses independently. Now you
read each other's work and begin the negotiation.

Round 1 is for raising items, not converging. STATUS: AGREED is not
allowed in round 1; it will be rejected.

Your job this round:

1. Read {other_name}'s phase 1 plan carefully.
2. Compare it to your own.
3. Raise questions where you need clarification about {other_name}'s
   claims, methodology, or scope (kind: question).
4. Raise disagreements where you and {other_name} take materially
   different positions on substance or framing (kind: disagreement).
5. Each raised item must have an anchor (> quote: or > after:) where
   appropriate.
6. Flag evidence_required: true on items whose resolution turns on
   factual claims that need an external source.

## Inputs

{{brief_content}}

{{agreed_interpretation_block}}

{{own_plan}}

{{other_plan}}

## Output

Produce a turn with the canonical section structure.

## Stance
(2–4 sentences: where you and {other_name} agree, where you differ,
 what you think the biggest open questions are.)

## Addressing items raised against me
(none — first round)

## Ratifying my own items
(none — first round)

## New items I'm raising
(RAISE blocks. Do not flood; raise the items that materially affect
 the final document, not every wording quibble. If you cannot state
 how resolving an item would change the final document, drop it.)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: [...]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: <int>
OPEN_DISAGREEMENTS: <int>
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
"""
```

### Phase 2 round N (N≥2) — `plan_negotiation_round_n_prompt`

```python
def plan_negotiation_round_n_prompt(
    *,
    brief_content: str,
    agreed_interpretation: str,
    own_plan: str,
    other_plan: str,
    prior_turns: Iterable[PriorTurn],
    standing_items: str,
    agent_name: str,
    other_name: str,
    round: int,
    soft_cap: int,
    hard_cap: int,
    is_closeout_round: bool = False,
    closeout_request: str = "",
) -> str:
    return COMMON_PREAMBLE + f"""
# Phase 2 (negotiate-plan): plan negotiation — round {round}

You are agent "{agent_name}". This is round {round} of phase 2
(soft cap {soft_cap}, hard cap {hard_cap}). Phase 2 converges when
both of you emit STATUS: AGREED in the same round, all items are
terminal, your AGREED_PLAN blocks hash-match, and you both name the
same DRAFTER.

## Inputs

{{brief_content}}

{{agreed_interpretation_block}}

{{own_plan}}

{{other_plan}}

{{prior_turns_section}}

{{standing_items_section}}

{{closeout_request_section}}

## Output

Produce a turn with the canonical section structure.

## Stance

## Addressing items raised against me
(ADDRESS blocks for every {other_name} item pointed at you in `open`
 state. Include evidence records when evidence_required: true. If you
 see no path to resolution, ACKNOWLEDGE in this section.)

## Ratifying my own items
(For every item you raised that's in `addressed` state: RESOLVE,
 ACKNOWLEDGE, WITHDRAW, or counter-argument. No silent skips.)

## New items I'm raising
(Only genuinely new items.)

## Phase artifact         ← only when emitting STATUS: AGREED

### AGREED_PLAN

#### Sections
1. Title: <section title>
   Key claims:
   - <claim>
   - <claim>
2. …

#### Carry-forward items (from phase 2)
- [<id>] <terminal-state>: <body> — <where this appears in the final document>

#### Drafter
DRAFTER: claude | openai

## Status
STATUS: IN_PROGRESS | AGREED
RAISED_THIS_TURN: [...]
ADDRESSED_THIS_TURN: [...]
RESOLVED_THIS_TURN: [...]
ACKNOWLEDGED_THIS_TURN: [...]
WITHDRAWN_THIS_TURN: [...]
OPEN_QUESTIONS: <int>
OPEN_DISAGREEMENTS: <int>
ADDRESSED_QUESTIONS: <int>
ADDRESSED_DISAGREEMENTS: <int>
"""
```

### Phase 3 — `drafting_prompt`

```python
def drafting_prompt(
    *,
    brief_content: str,
    agreed_interpretation: str,
    own_plan: str,
    other_plan: str,
    agreed_plan: str,
    carry_forward_items: list[LedgerEntry],
    prior_phase2_turns: Iterable[PriorTurn],
    agent_name: str,
    other_name: str,
) -> str:
    return COMMON_PREAMBLE + f"""
# Phase 3 (draft): produce the unified document

You are agent "{agent_name}", chosen as the drafter at the conclusion of
phase 2. Your job is single-shot: produce the unified document
following the AGREED_PLAN exactly in section order and topic.

This is a PRODUCTION phase. You do not raise tracked items here. You
do not emit operation blocks. The other agent does not run this phase.

The carry-forward items from phase 2 (terminal-not-resolved questions
and disagreements that need to appear in the final document) must each
be rendered in the appropriate section of your output:

- terminal `acknowledged` disagreements → "## Disagreements left open"
  section, one subsection per item (`### <id>: <short title>`) with
  both positions and the agreed treatment in the final document.
- terminal `acknowledged` questions → "## Open questions" section,
  enumerated.
- terminal `capped` items → same sections as `acknowledged`, marked as
  such with the orchestrator-generated rationale.

## Inputs

{{brief_content}}

{{agreed_interpretation_block}}

{{own_plan}}

{{other_plan}}

{{agreed_plan_block — hash-verified, verbatim from phase 2}}

{{carry_forward_items_list — with IDs, terminal states, rationales}}

{{prior_phase2_turns}}

## Output

Produce a single markdown document following the agreed plan section
order. Required structure:

## 1. Summary
3–5 sentences.

## 2. Findings
The merged substance — follow the agreed plan section by section.

## 3. Disagreements left open
One subsection per carry-forward disagreement (### <id>: <title>),
containing the canonical treatment from the agreed plan's
carry-forward items list.

## 4. Open questions
Numbered list of carry-forward questions with their IDs.

## 5. Sources
Merged numbered list with URLs. Reconcile duplicate citations across
the two phase 1 plans.

## 6. Confidence ledger
| Claim | Tag | Signal | Source notes |

Material claims for the ledger are those tied to FSD entries, those
flagged in phase 2 evidence reports, and any other claim that
materially affects the final recommendation. Non-material claims are
omitted.

Favour positions with stronger evidence regardless of which agent
held them. Preserve uncertainty honestly — do not smooth it away to
make the document sound more settled than it is.
"""
```

### Phase 4 round 1 — `review_round1_prompt`

```python
def review_round1_prompt(
    *,
    brief_content: str,
    draft_content: str,
    drafter_name: str,
    agent_name: str,
    other_name: str,
) -> str:
    role = "DRAFTER" if agent_name == drafter_name else "REVIEWER"
    return COMMON_PREAMBLE + f"""
# Phase 4 (review-draft): cross-review — round 1

You are agent "{agent_name}", acting as {role} in this phase. The draft
is by {drafter_name}. You are both reading the draft for the first time
in the review phase.

Round 1 is for raising items, not converging. STATUS: AGREED is not
allowed in round 1 and will be rejected.

Allowed categories in this phase: question, disagreement, issue,
comment. Raise items you genuinely consider material:

- question — clarification needs about the draft.
- disagreement — substantive points where you disagree with the draft's
  framing or position.
- issue — defects in the draft (incorrect claim, missing required
  section, broken reasoning, etc.).
- comment — non-defect suggestions (could be clearer, could be
  reorganized, etc.).

## Inputs

{{brief_content}}

{{draft_content}}

## Output

Produce a turn with the canonical section structure.

## Stance
(2–4 sentences: your overall reaction to the draft. The UI uses this
 as the timeline-card TL;DR.)

## Addressing items raised against me
(none — first round of this phase)

## Ratifying my own items
(none — first round)

## New items I'm raising
(RAISE blocks. Anchor with > quote: or > after: when applicable.
 evidence_required flag per item.)

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: [...]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: <int>
OPEN_DISAGREEMENTS: <int>
OPEN_ISSUES: <int>
OPEN_COMMENTS: <int>
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
ADDRESSED_ISSUES: 0
ADDRESSED_COMMENTS: 0
"""
```

### Phase 4 round N (N≥2) — `review_round_n_prompt`

```python
def review_round_n_prompt(
    *,
    brief_content: str,
    draft_content: str,
    drafter_name: str,
    prior_turns: Iterable[PriorTurn],
    standing_items: str,
    agent_name: str,
    other_name: str,
    round: int,
    soft_cap: int,
    hard_cap: int,
    draft_version: int,
    is_closeout_round: bool = False,
    closeout_request: str = "",
) -> str:
    role = "DRAFTER" if agent_name == drafter_name else "REVIEWER"
    return COMMON_PREAMBLE + f"""
# Phase 4 (review-draft): cross-review — round {round}

You are agent "{agent_name}", acting as {role}. The draft is by
{drafter_name}, currently at version v{draft_version}. This is round
{round} (soft cap {soft_cap}, hard cap {hard_cap}).

Phase 4 converges when both of you emit STATUS: AGREED in the same
round, all items are terminal, your AGREED_DRAFT_ACCEPTANCE blocks
match (same draft_version, same draft_hash), and the drafter has not
revised the draft in this round.

If you are the DRAFTER and the other agent's prior turn raised
substantive items, you may revise the draft in this turn by emitting
a "## Revised draft" section with the full revised content. The
orchestrator detects this and advances the draft version pointer. The
REVIEWER never modifies the draft.

If you are the REVIEWER, write "(reviewer — no draft edits)" in the
revision-note slot below.

## Inputs

{{brief_content}}

{{draft_content (v{draft_version})}}

{{prior_turns_section}}

{{standing_items_section}}

{{closeout_request_section}}

## Output

Produce a turn with the canonical section structure.

## Stance

## Addressing items raised against me
(ADDRESS blocks for every {other_name} item in `open` state pointed at
 you. Include evidence records when evidence_required: true. ACKNOWLEDGE
 in this section if you see no path.)

## Ratifying my own items
(RESOLVE / ACKNOWLEDGE / WITHDRAW / counter-argument for every one of
 your items in `addressed` state.)

## New items I'm raising
(Only genuinely new items.)

## Revised draft         ← drafter only, if any revisions
(Full revised draft content. Reviewer writes "(reviewer — no draft edits)".)

## Phase artifact         ← only when emitting STATUS: AGREED

### AGREED_DRAFT_ACCEPTANCE

draft_version: v<N>
draft_hash: <SHA-256 hex>
endorsement: |
  <one sentence on why this draft satisfies the brief>

## Status
STATUS: IN_PROGRESS | AGREED
RAISED_THIS_TURN: [...]
ADDRESSED_THIS_TURN: [...]
RESOLVED_THIS_TURN: [...]
ACKNOWLEDGED_THIS_TURN: [...]
WITHDRAWN_THIS_TURN: [...]
OPEN_QUESTIONS: <int>
OPEN_DISAGREEMENTS: <int>
OPEN_ISSUES: <int>
OPEN_COMMENTS: <int>
ADDRESSED_QUESTIONS: <int>
ADDRESSED_DISAGREEMENTS: <int>
ADDRESSED_ISSUES: <int>
ADDRESSED_COMMENTS: <int>
"""
```

### Closeout prompt augmentation

The closeout request is rendered as a section inserted into the appropriate phase prompt (input_negotiation, plan_negotiation_round_n, or review_round_n) when the prior round attempted convergence but left non-terminal items:

```python
def closeout_request_section(items: list[LedgerEntry], agent_name: str) -> str:
    return f"""
## Closeout request

You and the other agent both emitted STATUS: AGREED in the previous
round, but the system detected non-terminal items still in the ledger.
The phase cannot converge while items are non-terminal. This is a
**closeout round** — you have a constrained job:

Items that need ratification from you ({agent_name}):

{items_listing — each item with id, kind, body excerpt, current_state, who_addressed_it}

Your operations this round must be only:
- RESOLVE — if you accept the response or position
- ACKNOWLEDGE — if you and the other agent should agree this is
  irreconcilable (the orchestrator will transition the item to terminal
  acknowledged only when the other agent's ACKNOWLEDGE for the same
  item lands in their next turn)
- WITHDRAW — if you no longer hold the item
- counter-argument — if the response did not move you and you want to
  flip the item back to open with rationale

You may NOT raise new items in this round. RAISE blocks will be
silently dropped and recorded as a closeout violation.

You have **{remaining_budget}** closeout rounds remaining in your
budget. If you exhaust your budget without bringing your items to
terminal state, the orchestrator will auto-cap the remaining items
(state: capped, via: ghost_cap) and the phase will converge with the
items recorded as orchestrator-forced.
"""
```

## Orchestrator changes

`src/dual_research/orchestrator/` is updated:

1. **`phase0.py` becomes multi-round**. New shape mirrors `phase2.py`'s round loop. Maintains the `Phase0Outcome` dataclass shape but adds `via_hard_cap` / `via_closeout` / `via_ghost_cap` flags. Emits the new event payload (see Event schema section) AND the legacy `Phase0Complete` payload via the backward-compat shim. The phase 0 → phase 1 contract becomes: pass the `AGREED_INTERPRETATION` block into `research_plan_prompt`.

2. **`phase1.py`** is unchanged in shape (still one-shot parallel) but receives the agreed interpretation as input alongside the brief. The prompt no longer asks for "Claims I expect" or "Open questions" sections.

3. **`phase2.py` simplifies**. Drops:
   - `canonical-FSD synthesis` escape (`splice_canonical_into_agreed_plan`, `extract_canonical_fsd_items` for synthesis-only paths)
   - `stuck-AGREED promotion` (`STUCK_AGREED_K` logic)
   - `force-verbatim-copy` repair turn for hash drift
   - `tiebreak` chain for drafter selection (`all_substantive_gates_pass_except_drafter` chain)
   - Legacy `parse_with_repair` flow
   
   Adds:
   - `parse_with_closeout` (new mechanism, see closeout section)
   - Simple drafter tiebreak (higher `DOMAIN_FIT_OTHER`, default claude on tie)
   - Auto-cap on hard cap and ghost-cap with explicit `via:` tagging
   
   Convergence rule becomes the three-condition cross-check: both AGREED + all items terminal + plan hash + drafter match.

4. **`phase3.py`** receives the new structured input: `agreed_interpretation` + `agreed_plan` + parsed `carry_forward_items` (list of LedgerEntry). Output is the unified document; orchestrator continues to write it to `phase3/draft-v1.md`. No agent-side raising in this phase.

5. **`phase4.py` simplifies similarly to phase2.py**. Drops `stuck-AGREED` promotion, `parse_with_repair` legacy flow. Adds the closeout mechanism and the new convergence rule (both AGREED + all items terminal + `AGREED_DRAFT_ACCEPTANCE` match + drafter didn't revise this round).

6. **`repair.py` is replaced by `closeout.py`**. The function signatures change. `parse_with_repair` becomes `parse_with_closeout(text, *, phase, round, validator, tracker, …)`. The closeout tracker records per-agent budget per phase. Malformed sibling files keep their `.malformed-1.md` naming convention (it's still useful for human debugging).

7. **`finalize.py`** is updated to construct the final document's appendix from all terminal-not-resolved items across all phases. The aggregation queries the ledger (built fresh from the on-disk turn files via `build_phase_ledger` for each of phases 0/2/4) and renders the appendix section per the structure in the cross-phase carryover section above.

## Event schema + persistence

New event types added to `src/dual_research/events/types.py`:

```python
@dataclass(frozen=True)
class ItemRaised:
    event_type: ClassVar[str] = "item_raised"
    id: str              # e.g. Q-plan-c-04
    kind: str            # "question" | "disagreement" | "issue" | "comment"
    phase: int           # 0, 2, 4
    round: int
    raiser: str          # "claude" | "openai"
    body: str            # full raise body
    anchor_type: str     # "quote" | "after" | "none"
    anchor_text: str
    evidence_required: bool

@dataclass(frozen=True)
class ItemTransitioned:
    event_type: ClassVar[str] = "item_transitioned"
    id: str
    from_state: str      # "open" | "addressed" | …
    to_state: str
    actor: str           # "claude" | "openai" | "orchestrator"
    phase: int
    round: int
    reason: str
    evidence_records: list[dict] = field(default_factory=list)  # populated on ADDRESS transitions
    via: str | None = None  # "hard_cap" | "ghost_cap" — only when actor=="orchestrator"

@dataclass(frozen=True)
class CloseoutUrged:
    event_type: ClassVar[str] = "closeout_urged"
    phase: int
    round: int
    affected_items: list[str]  # IDs
    affected_raiser_budgets: dict[str, int]  # raiser → remaining budget

@dataclass(frozen=True)
class PhaseConverged:
    event_type: ClassVar[str] = "phase_converged"
    phase: int
    final_round: int
    via_closeout: bool = False
    via_ghost_cap: bool = False
    via_hard_cap: bool = False
```

These events form the canonical persistence of the lifecycle. The ledger can be reconstructed from the event stream alone — no need to re-parse markdown for state derivation.

### Backward-compat shim

The orchestrator continues to emit the legacy events (`Phase0Complete`, `Phase2RoundComplete`, `Phase4RoundComplete` with their existing payloads) alongside the new events. The legacy payloads are populated by computing the legacy fields from the ledger at the end of each round:

- `claude_brief_issues` / `openai_brief_issues` ← count of `open` + `addressed` items raised by that agent in phase 0
- `claude_open_questions` / `openai_open_questions` ← count of `open` + `addressed` questions raised by that agent in phase 2
- `claude_blocking` / `openai_blocking` ← count of `open` disagreements raised by that agent in phase 2
- `claude_fsd` / `openai_fsd` ← count of `acknowledged` disagreements raised by that agent in phase 2 (the new model's analogue to FSD)
- `claude_open_issues` / `openai_open_issues` ← count of `open` + `addressed` items in phase 4 (mirrors today's conflated count for compatibility)

The shim lives in `src/dual_research/events/legacy_shim.py` and is invoked at every phase boundary. It is removed in spec 0115 as part of the UI cutover.

### State persistence

`src/dual_research/persistence/state.py` `SessionState` is extended:

```python
@dataclass
class SessionState:
    # ... existing fields ...
    phase: str
    drafter: str | None
    agreed_plan: str | None
    final_surfaced_disagreements: list[dict]  # retained for legacy reads
    draft_round: int
    final_emitted_to: str | None
    
    # NEW
    agreed_interpretation: str | None = None  # phase 0 agreed block
    carry_forward_phase0: list[dict] = field(default_factory=list)
    carry_forward_phase2: list[dict] = field(default_factory=list)
    carry_forward_phase4: list[dict] = field(default_factory=list)
    closeout_budgets: dict[str, dict[str, int]] = field(default_factory=dict)
    # e.g. {"phase2": {"claude": 2, "openai": 2}, "phase4": {"claude": 2, "openai": 2}}
```

The carry-forward lists are written at phase boundaries from the parsed agreed-artifact's carry-forward section. The finalize step reads them to assemble the appendix.

## Migration plan

1. Land Spec 0114 in a feature branch.
2. Add `src/dual_research/contract/` with all submodules. New code; nothing else imports yet.
3. Add new event types to `events/types.py` alongside the existing ones. The new events are emitted from new code paths only.
4. Implement `parse_with_closeout` in `orchestrator/closeout.py` alongside the existing `parse_with_repair`. Both coexist temporarily.
5. Implement the new prompts in `protocol/prompts.py` as new functions (`preflight_prompt_v2` → eventually renamed to canonical). Old prompts remain available for legacy code paths during the transition.
6. Implement the new parser in `protocol/parse.py` — the new typed extraction functions for operation blocks. Legacy regexes retained for the shim's legacy event population.
7. Wire phase orchestrators (`phase0.py` … `phase4.py`) to use the new prompts and the new parser. The legacy shim emits the legacy events alongside.
8. Run the existing test suite + new contract-validator tests. Goal: existing UI continues to render correctly for new runs, new runs use the new protocol internally.
9. Land the spec; merge to main.
10. Spec 0115 (UI + validator + shim removal) follows.

## Test plan

- [ ] Unit tests for `contract/lifecycle.py` — every allowed transition fires, every disallowed transition rejects.
- [ ] Unit tests for `contract/ids.py` — format/parse roundtrip on a corpus of IDs; reject malformed.
- [ ] Unit tests for `contract/validator.py` — feed valid and invalid turn texts; check error severities.
- [ ] Unit tests for the parser (`protocol/parse.py`) — each operation block type parses correctly; malformed blocks are detected; the `EVIDENCE_CHECKED_SECTION_RE` brittleness fix is validated against the bug pattern from run `20260519-132908-backend-language-choice/phase4/round-03-claude.md`.
- [ ] Integration test: replay the audited run's brief through the new orchestrator end-to-end (with mocked LLM responses that emit the new format). Verify the final document's appendix contains every terminal-not-resolved item with full provenance.
- [ ] Integration test: closeout mechanism fires correctly when agents emit AGREED with non-terminal items; closeout budget decrements; ghost-cap fires at budget exhaustion.
- [ ] Integration test: hard-cap behavior — agents never reach AGREED; cap fires; all non-terminal items auto-cap with `via: hard_cap`.
- [ ] Integration test: evidence anti-hallucination — agent emits an evidence block with a fabricated event_id; turn is rejected; closeout urge fires next round.
- [ ] Backward-compat shim test: run an end-to-end test with the new protocol; verify the legacy `Phase2RoundComplete` etc. payloads are populated with sensible values derived from the ledger; verify the existing UI renders them.
- [ ] Manual end-to-end run: fire a full Deep Research run on a small brief via the `dual-research-run` skill; verify the run completes; inspect the transcript for new event types; inspect `final.md` for the appendix structure.

## Risks

- **Risk**: Agents fail to follow the new prompt structure reliably, producing malformed turns at higher rates than the legacy prompts.
  - **Mitigation**: The closeout mechanism converts most malformed-output scenarios into "the item didn't transition; you need to try again in the closeout round." The structured operation blocks are simpler than the legacy free-form sections, which should improve reliability rather than worsen it. We monitor the `closeout_violation` event rate on the first few production runs and tune the prompts if needed.

- **Risk**: The backward-compat shim's computed legacy field values disagree with what the legacy UI expects, causing rendering bugs on the existing UI before spec 0115 lands.
  - **Mitigation**: A specific test in the shim's unit tests confirms that for a fixed-input run, the legacy payload fields are byte-identical to what the legacy parser would have produced. Any drift is caught at CI time.

- **Risk**: The new convergence rule rejects runs that the legacy system would have converged via escape valves (canonical-FSD synthesis or stuck-AGREED), increasing the hard-cap rate.
  - **Mitigation**: The closeout mechanism is the new "escape" — it allows agents who have substantively agreed to clean up their item state explicitly rather than the orchestrator papering over it. The auto-cap path (`via: hard_cap` and `via: ghost_cap`) is the final safety net for runs that genuinely can't converge. The audit of historical runs suggested most escape-valve uses were workarounds for the missing `acknowledged` state, which the new model provides.

- **Risk**: Anti-hallucination evidence validation rejects legitimate evidence due to normalization edge cases (whitespace, encoding, etc.).
  - **Mitigation**: The content_excerpt match uses light normalization (whitespace collapse, smart-quote folding, line-ending normalization). The error severity for `evidence_content_not_in_source` may be set to `warning` initially (logged but not rejecting) for the first few production runs, then upgraded to `error` once we've confirmed false-positive rates are low.

- **Risk**: The spec is large; bugs sneak in despite the test plan.
  - **Mitigation**: The compat shim means a failure of the new model degrades gracefully — the legacy UI continues to render legacy events, even if the new events are malformed. We can ship spec 0114 and observe a few real runs before spec 0115 cuts over.

## Open questions

- **OQ-1**: Should ID sequences reset per round, per phase, or per run? Spec says per (kind, phase, raiser). Confirm this is the right scope — the alternative (per run) would mean phase 4 issue IDs start at 01 even though phase 2 raised many disagreements; the chosen scope keeps the IDs more readable.
- **OQ-2**: The closeout budget is set to 2 per phase per agent. This is a guess; tune after observing real runs. The number is configurable in `contract/caps.py`.
- **OQ-3**: Should the `via_canonical_fsd_synthesis` escape be retained as a one-shot "the agents already agree but the canonical section is missing" auto-fix, or fully removed in favor of the closeout mechanism? Spec currently says fully removed for simplicity; if we observe a class of runs that get stuck on a canonical-section formatting issue, we can re-introduce.
- **OQ-4**: The `endorsement` text in `AGREED_DRAFT_ACCEPTANCE` is a one-sentence prose field. Should it be more structured (multi-field, like the phase 2 5-line agreement check), or kept loose? Spec keeps it loose; agents have enough structure elsewhere.
