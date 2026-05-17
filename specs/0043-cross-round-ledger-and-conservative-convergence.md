---
spec: 0043
title: Cross-round ledger + standing-items input + conservative convergence
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.41.0
created: 2026-05-17
pr: "https://github.com/Lexiz/dual-research/pull/44"
---

# Spec 0043 — Cross-round ledger + standing-items input + conservative convergence

## Context

Today the dual-research system relies on the agents to self-manage
closure across rounds:

- Each turn ends with self-reported counters (`OPEN_QUESTIONS: N`,
  `OPEN_ISSUES: N`, `BLOCKING_DISAGREEMENTS: N`).
- The agent decides which prior questions / disagreements / issues to
  keep in next round's `## Open questions for X`, `## Substantive
  disagreements I'm holding`, `## Issue ledger (delta + currently
  open)` sections. Items disappear from the section when the agent
  decides they're addressed; the system reads "absence" as "resolved."
- Convergence
  ([`protocol/convergence.py`](../src/dual_research/protocol/convergence.py))
  terminates a phase when both agents report matching `STATUS:
  AGREED` + `OPEN_QUESTIONS: 0` + `BLOCKING_DISAGREEMENTS: 0` +
  matching `FINAL_SURFACED_DISAGREEMENTS: N`. The check is bilateral
  (both agents must agree) and multi-factor, which is genuinely
  strong — but every signal in it is still agent-self-reported.

This is **high-trust, low-verification**. It works on the happy path
because agents are diligent and the bilateral check is hard to fake.
But it has structural gaps:

1. **Silent ghosting is possible.** An agent can stop emitting a
   question in round 3 without ever addressing it. The system marks
   it resolved by absence. The other agent might notice and
   complain — or might not. There's no programmatic ghost signal.
2. **Self-counters aren't audited.** `OPEN_QUESTIONS: 6` is what the
   agent claims. After [spec 0042's](./0042-critique-data-integrity.md)
   D4, the UI badges now read from parsed-item counts (with the
   self-counter logged as a debug sanity-check). But nothing in the
   *system* (parser, orchestrator, convergence) actually enforces
   that the two agree.
3. **Items aren't programmatically linked across rounds.** D-N / Q-N
   IDs are a convention agents maintain. If an agent renames `D-4` to
   `D-4'` in round 3, the system can't trace the same item across
   rounds. (Spec 0042 partly addresses this for claim → disagreement
   escalation by leveraging D-N IDs, but the linkage is implicit.)
4. **The LLM doesn't get structured prior-state.** Each round the
   orchestrator hands the agent the entire prior thread verbatim and
   asks the agent to re-derive "what's still open." The agent has to
   re-parse prose every round. Structured state would reduce
   cognitive load + improve compliance with the negotiation
   protocol.

[Spec 0042](./0042-critique-data-integrity.md) fixed the
*visualisation* side of these gaps — UI counts now read from parsed
items, taxonomy is honest, modal load paths work. But the spec
explicitly deferred the *system-side* tracking question (see Out of
Scope of 0042): "Spec 0042 reads parsed-item counts per turn; the
system still trusts agent-self-managed closure between rounds."

Spec 0043 closes the gap on the system side without imposing a new
output-compliance regime on the agents. Three changes that work
together:

1. The orchestrator builds an authoritative cross-round **ledger** —
   one entry per item with stable ID, kind, raiser, round-first-seen,
   round-last-seen, current status, status-transition history. The
   ledger is derived from the existing parsed sections; agents don't
   have to emit anything new.
2. The next-round prompt template gains a `## Standing items from
   prior rounds` section built from the ledger's open items. The agent
   reads this as structured input alongside the existing prior-turn
   dump — so the LLM gets to *use* the tagging instead of re-deriving
   it from prose each round.
3. Convergence cross-checks the system-computed ledger open-set
   against the agent self-counters. A phase terminates only when
   both signals agree the open-set is empty. If they disagree, the
   phase keeps running and the agent is told (in the next round's
   standing-items input) which items they ghosted.

Critically: **the agent's output protocol is unchanged**. Agents
still write the same `## Open questions for X`, `## Substantive
disagreements I'm holding`, `## Issue ledger (delta + currently
open)`, `## Answers to:`, `## Resolved or non-blocking differences`
sections they write today. The ledger is built by parsing what they
already emit. No new mandatory sections, no `addressed / maintained
/ withdrawn / escalated` per-item move emission, no ledger-update
syntax to memorise. The only change the agent sees is on the
*input* side: a structured "here's what's still in play" block at
the top of round-N's prompt.

Prior context:
- [Spec 0028](./0028-review-inline-comments.md) — established the
  Phase 4 section taxonomy.
- [Spec 0034](./0034-critique-navigation.md) — introduced
  `resolve_review_items` (anchor pre-resolution at parse time);
  established positional + verbatim-match question answer linkage in
  `ui/questions.py`.
- [Spec 0041](./0041-critique-classification-and-resilience.md) —
  split `kind="issue"` / `"comment"` / `"question"`; established
  Issue ledger "absent from latest round = resolved" semantics.
- [Spec 0042](./0042-critique-data-integrity.md) — extended parser
  coverage to Phase 1; added `kind="claim"` + `Run.claims`; aligned
  badge counts with parsed items. This spec builds directly on
  0042's wire-format additions.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **New `src/dual_research/ledger/` package with `LedgerEntry` + `LedgerState` dataclasses.** | One entry per stable item. Fields: `id`, `kind` (`question` / `disagreement` / `claim` / `issue` / `comment`), `raised_round`, `raised_by`, `raised_turn_key`, `current_status` (per-kind enum), `status_history` (`list[tuple[round, status, reason]]`), `body_snippet` (first ~120 chars), `last_addressed_round` (None if never), `ghosted_rounds` (count of rounds open with no addressing signal). `LedgerState` per (run, phase) — Phase 2 ledger + Phase 4 ledger are independent. |
| D2  | **Ledger built deterministically from existing parsed sections — no new agent output required.** | `build_phase_ledger(session_dir, phase)` walks the phase's turn files in chronological order, runs `extract_review_items` on each, and applies per-kind state transitions (D4) to maintain the ledger. Idempotent: same session dir → same ledger. Rebuilt on every `load_run_snapshot` (no persistence beyond a sidecar `<session>/ledger.json` for debugging — the canonical source is always disk). |
| D3  | **Cross-round item identity** | **Disagreements & issues**: stable IDs already exist in the protocol (`D-N`, `OAI-N`, `C-N`). The ledger uses them as the canonical key. **Questions**: today's `reconstruct_questions` already assigns `Q-c-r1-01` IDs deterministically per-turn and threads answer linkage via positional + verbatim-match. The ledger inherits that linkage and treats matched questions as the same entry. **Claims**: matched to later-round disagreements via D-N suffix (spec 0042 D6 surfaced this transition; D3 here makes it explicit in the ledger). **Comments**: per-turn IDs, terminal status, no cross-round linkage. |
| D4  | **Per-kind closure rules** | **Question**: `open` → `answered` iff the question's body appears in a later turn's `## Answers to {raiser}'s open questions` or `## Answers to {raiser}'s prior comments` section (positional + verbatim-match, existing logic). **Disagreement**: `open` → `resolved` iff D-N appears in `## Resolved or non-blocking differences`; `open` → `final-surfaced` iff appears in `## Final-surfaced disagreements`. **Claim**: `open` → `escalated` iff the D-N suffix appears in any later round's `## Substantive disagreements I'm holding` (claim hardens into a held disagreement); `open` → `withdrawn` iff the claim's body-prefix is absent from all later rounds AND no escalation. **Issue**: `open` → `fixed` iff absent from latest round's `## Issue ledger` by the same raiser (existing `reconstruct_issues` semantics). **Comment**: terminal `noted` only. |
| D5  | **Ghosted detection** | An item is `ghosted` for round N iff it was `open` at the start of round N AND received no addressing signal in round N (no presence in `## Answers to:`, no `## Resolved or non-blocking`, no `## Substantive disagreements I'm holding` reference). The `ghosted_rounds` counter on `LedgerEntry` accumulates these. UI surfaces a `⚠` annotation on ledger entries with `ghosted_rounds > 0`. Does NOT block convergence — ghosting is a *flag*, not a failure. |
| D6  | **`## Standing items from prior rounds` injected into round-N (N≥2) prompts.** | The orchestrator (`phase2.py` / `phase4.py`) builds this section from the ledger's open entries before composing the round's prompt. Format: ~200-500 tokens depending on accumulated state. Each entry: one line `- [{id}] {kind} raised by {agent} in r{N}: {body_snippet} — status: {status}` plus a one-line section header explaining how to use it. Agent instruction is soft ("you should address each of these items naturally in your reply; items left unaddressed will be flagged as ghosted to the user"). No new mandatory output section. |
| D7  | **Conservative convergence — both signals must agree.** | `protocol/convergence.py::can_terminate(phase)` gains a new check alongside the existing self-counter test: `ledger.open_count(phase) == 0`. Phase terminates only when BOTH conditions are true. If agent counters say 0 but ledger has open items, the convergence check returns `False` and the phase keeps running. Drift is logged + surfaced in the UI. Mirror check for `BLOCKING_DISAGREEMENTS` (held disagreements only) and `OPEN_ISSUES` (Phase 4). |
| D8  | **Drift signal — agent counter vs ledger count mismatch is logged + surfaced.** | When `stats.openQuestions != ledger.open_questions_for_turn(turnKey)`, the aggregator records a `LedgerDrift` event with `(turn_key, kind, agent_count, ledger_count)`. UI displays a small `⚠ drift` badge on the turn card with a tooltip showing the breakdown. (Spec 0042 D4 already logs this at the frontend at debug level; spec 0043 makes it a first-class event surfaced on `Run.drifts: list[LedgerDrift]`.) |
| D9  | **Kill-switch — `DR_LEDGER_MODE=legacy` falls back to self-counter-only convergence.** | Env-flag gate. When set, `can_terminate` returns the legacy result (self-counter check only); the standing-items prompt section is omitted; the ledger is still built (used by UI) but doesn't affect convergence. Default is `DR_LEDGER_MODE=enforce` (ledger active). Mitigates risk if real runs misbehave — we can roll back without a code revert. |
| D10 | **`Run.ledger` exposed on the wire as a typed array per phase.** | New `Run.phase_ledgers: dict[int, list[LedgerEntry]]` keyed by phase (2, 4). Each LedgerEntry serialises to the camelCased shape on the wire. UI's cross-round Critique pane reads `run.phaseLedgers[2]` / `[4]` as the canonical source for the per-round breakdown, replacing the ad-hoc cross-kind merging the Critique explorer does today. **Out of scope for this spec:** redesigning the Critique pane / Summary tab visually — that's spec 0046. Spec 0043 just adds the data shape. |
| D11 | **Backfill on existing runs is automatic.** | The aggregator rebuilds ledger state on every `load_run_snapshot` from the existing on-disk turn files. Hosted Supabase runs and local runs both get ledger data on next page-load. No migration script. The `<session>/ledger.json` sidecar is a debugging artefact — useful for inspection but never authoritative. |
| D12 | **`OPEN_QUESTIONS:` self-counter stays in the protocol prompts.** | We don't remove the self-counter — agents still emit it (it's part of the existing prompt template). The ledger becomes the *enforcement* source of truth, but the agent counter is preserved as a sanity signal. When the two disagree, drift is logged. Eventually if drift is rare, we could deprecate the counter — that's a future spec. |

## Proposed change

### 1. Ledger package — `src/dual_research/ledger/` (new)

```
src/dual_research/ledger/
├── __init__.py        — re-exports LedgerEntry, LedgerState, build_phase_ledger
├── models.py          — @dataclass LedgerEntry, LedgerState, LedgerDrift, status enums
├── build.py           — build_phase_ledger(session_dir, phase) → LedgerState
├── transitions.py     — per-kind closure detection (apply_question_transitions,
│                        apply_disagreement_transitions, apply_issue_transitions,
│                        apply_claim_transitions)
└── prompt.py          — build_standing_items_section(ledger, *, max_items, max_chars)
                         → str ready to inline into the prompt
```

`LedgerEntry`:

```python
@dataclass
class LedgerEntry:
    id: str                     # canonical cross-round ID (D-1, OAI-3, Q-c-r1-01, Cl-c-p1-04)
    kind: str                   # "question" | "disagreement" | "claim" | "issue" | "comment"
    raised_round: int           # 0 for Phase 1 plan-draft items
    raised_by: str              # "claude" | "gpt"
    raised_turn_key: str        # phase1_claude / phase2_round1_claude / etc.
    current_status: str         # see per-kind enums below
    status_history: list[LedgerStatusTransition]
    body_snippet: str           # first ~120 chars of body
    last_addressed_round: int | None
    ghosted_rounds: int = 0     # accumulates each round the item was open without addressing
```

`LedgerStatusTransition`:

```python
@dataclass
class LedgerStatusTransition:
    round: int
    status: str
    reason: str                 # e.g. "answered in phase2_round3_gpt's ## Answers to: section"
    turn_key: str               # which turn triggered the transition
```

Per-kind status enums:

```python
QUESTION_STATUSES   = ("open", "answered", "withdrawn")
DISAGREEMENT_STATUSES = ("open", "resolved", "final_surfaced")
CLAIM_STATUSES      = ("open", "escalated", "withdrawn")
ISSUE_STATUSES      = ("open", "fixed", "non_blocking")
COMMENT_STATUSES    = ("noted",)
```

### 2. Build function — `src/dual_research/ledger/build.py`

```python
def build_phase_ledger(session_dir: Path, phase: int) -> LedgerState:
    """Walk the phase's turn files in chronological order, derive a
    cross-round ledger from parsed sections.

    Phase 2: walks phase1/draft-<agent>.md (raised items only, no
    transitions because Phase 1 has one shot) + phase2/round-NN-<agent>.md
    for every round.

    Phase 4: walks phase4/round-NN-<agent>.md for every round, anchored
    against the current converged draft.

    For each turn file in order:
    1. Extract review items via existing extract_review_items.
    2. For each item with a stable cross-round ID (D-N for disagreements,
       OAI-N/C-N for issues, body-prefix-match for claims/questions),
       upsert into the ledger.
    3. Apply per-kind transitions based on the current turn's content:
       - Did this turn's ## Answers to: reference any open question?
         (mark answered)
       - Did this turn's ## Substantive disagreements I'm holding reference
         a prior claim's D-N? (mark claim escalated)
       - Did this turn's ## Resolved or non-blocking differences include
         this disagreement? (mark resolved)
       - Did this turn's ## Issue ledger drop a prior issue? (mark fixed)
    4. For every still-open item that received no addressing signal in
       this turn, increment ghosted_rounds.
    """
```

### 3. Standing items prompt section — `src/dual_research/ledger/prompt.py`

```python
def build_standing_items_section(
    ledger: LedgerState,
    *,
    perspective: str,           # "claude" or "openai" — items raised BY the other are highlighted
    max_items: int = 30,        # truncate at this many items
    max_chars: int = 3000,      # truncate at this many total chars
) -> str:
    """Compose the ## Standing items from prior rounds section.

    Empty ledger → returns "" (orchestrator omits the section).
    Otherwise:

        ## Standing items from prior rounds

        These items were raised in earlier rounds and remain open as
        of this point. Address each in your reply: answer it directly
        (for questions), resolve or concede the position (for
        disagreements/claims), incorporate the fix (for issues). Items
        you leave unaddressed will be flagged to the user as ghosted.

        ### Raised by openai (3 items)
        - [Q-g-r2-04] question raised in r2: <body snippet> — status: open
        - [D-5] disagreement raised in r2: <body snippet> — status: open
        - [Cl-g-r1-02] claim raised in r1: <body snippet> — status: open

        ### Raised by you (2 items)
        - [D-1] disagreement raised in r1: <body snippet> — status: open
        - [Q-c-r1-03] question raised in r1: <body snippet> — status: open

    Items are grouped by raiser so the agent reads "what's still on me"
    distinct from "what's still on the other side." Status is always
    `open` in this section (resolved items omitted). Body snippets are
    capped at ~120 chars and trail with `…` when truncated.
    """
```

### 4. Orchestrator wiring — `src/dual_research/orchestrator/phase2.py`

`negotiation_turn` (R≥2) call site already inlines prior turns. Add a
ledger build + standing-items injection:

```python
# Before composing the round-r prompt:
ledger = build_phase_ledger(session_dir, phase=2)
standing_items = build_standing_items_section(
    ledger, perspective=agent_be, max_items=30, max_chars=3000
)
# Pass standing_items into the prompt template; template inlines it
# below the prior-turns block.
claude_prompt = negotiation_turn_prompt(
    brief_content=brief_content,
    own_draft=claude_draft,
    other_draft=openai_draft,
    prior_turns=prior,
    standing_items=standing_items,    # new
    agent_name="claude",
    other_name="openai",
    round=r,
    soft_cap=soft_cap,
    hard_cap=hard_cap,
)
```

Mirror for `openai` half. Same change in `phase4.py` for review rounds.

When `DR_LEDGER_MODE=legacy`, the `standing_items` arg is `""` and the
prompt template omits the section.

### 5. Prompt template — `src/dual_research/protocol/prompts.py`

Extend `negotiation_turn_prompt` + `review_turn_prompt` signatures with
an optional `standing_items: str = ""` parameter. Inline the section
below the prior-turns dump, before the agent's instruction block:

```python
def negotiation_turn_prompt(..., standing_items: str = "", ...):
    ...
    prompt = f"""
        {system_header}

        {brief_section}

        {drafts_section}

        {prior_turns_section}

        {standing_items}

        {instruction_block}
    """
```

`standing_items` is empty-string by default so any existing callers /
tests continue to work without modification.

### 6. Convergence — `src/dual_research/protocol/convergence.py`

`can_terminate_phase2_round` + `can_terminate_phase4_round` gain a
ledger cross-check:

```python
def can_terminate_phase2_round(
    claude_parsed, openai_parsed, *, ledger: LedgerState | None = None
) -> tuple[bool, list[str]]:
    errs = []
    # Existing self-counter checks (status agreed, counters zero, etc.)
    ... # unchanged

    # Spec 0043 D7 — ledger cross-check.
    if ledger is not None and _LEDGER_MODE != "legacy":
        open_qs = ledger.open_count(kind="question")
        open_ds = ledger.open_count(kind="disagreement")
        open_cs = ledger.open_count(kind="claim")
        if open_qs > 0:
            errs.append(f"ledger reports {open_qs} questions still open (agents say 0)")
        if open_ds > 0:
            errs.append(f"ledger reports {open_ds} held disagreements (agents say 0)")
        if open_cs > 0:
            errs.append(f"ledger reports {open_cs} claims unresolved (agents say 0)")
    return (len(errs) == 0, errs)
```

Same shape for `can_terminate_phase4_round` against `kind="issue"`.

The orchestrator passes the freshly-built ledger to `can_terminate_*`
on each round-end check.

### 7. Aggregator + wire surface — `src/dual_research/ui/`

`models.py`:

```python
@dataclass
class Run:
    ...
    # Spec 0043 — per-phase ledger snapshots, derived from disk on every
    # load_run_snapshot. Empty until Phase 2/4 has at least one turn file.
    phase_ledgers: dict[int, list[LedgerEntry]] = field(default_factory=dict)
    # Per-turn drift events: when stats.openQuestions disagrees with the
    # ledger's count of items that became open in that turn.
    drifts: list[LedgerDrift] = field(default_factory=list)
```

`aggregator.py::load_run_snapshot`:

```python
# After existing reconstruct_questions / reconstruct_claims / etc.:
from dual_research.ledger.build import build_phase_ledger
run.phase_ledgers = {
    2: build_phase_ledger(session_dir, phase=2).entries,
    4: build_phase_ledger(session_dir, phase=4).entries,
}
run.drifts = _compute_drift_events(run)
```

`_compute_drift_events` walks each turn's `phase_stats` and compares
the self-counter against the per-turn ledger snapshot. Emits one
`LedgerDrift` per (turn, kind) mismatch.

### 8. UI — `src/dual_research/ui/static/run-detail.jsx`

- New `LedgerDriftBadge` component: renders a small `⚠ drift` chip on
  any turn card where `run.drifts` has an entry for that turn key.
  Tooltip shows `"agent: N · ledger: M"` per drifted kind.
- New `GhostedAnnotation` on critique cards: when `entry.ghostedRounds > 0`,
  render a `⚠ ghosted N rounds` annotation under the headline.
- Critique pane's per-phase content reads from `run.phaseLedgers[pid]`
  as the canonical source for cross-round display (replacing the
  ad-hoc cross-kind merging done today). Visual layout unchanged
  here — that's spec 0046.

### 9. Tests

- `tests/ledger/test_models.py` (new) — LedgerEntry default values,
  status enum validation.
- `tests/ledger/test_transitions.py` (new):
  - Question raised R1, answered R2 → ledger.status == "answered",
    last_addressed_round == 2.
  - Question raised R1, not addressed in R2, not addressed in R3 →
    ghosted_rounds == 2 at end of R3.
  - Disagreement raised R2, resolved R4 → status == "resolved",
    last_addressed_round == 4.
  - Claim raised P1, same D-N appears in R2's substantive
    disagreements → status == "escalated".
  - Claim raised P1, body-prefix never appears later → status ==
    "withdrawn" (after the run terminates).
  - Issue raised R1, dropped from R2's ledger by same raiser → status
    == "fixed".
- `tests/ledger/test_build.py` (new):
  - Full build on a synthetic 3-round Phase 2 fixture — assert
    expected ledger shape end-to-end.
  - Full build on partner-vetting fixture — assert specific item IDs
    have expected status transitions (regression guard).
- `tests/ledger/test_prompt.py` (new):
  - build_standing_items_section with empty ledger returns "".
  - Truncates correctly at max_items / max_chars.
  - Groups by raiser correctly.
- `tests/orchestrator/test_phase2_standing_items.py` (new):
  - R≥2 prompt includes "## Standing items from prior rounds"
    section when ledger has open items.
  - R1 prompt does NOT include the section (no prior rounds).
  - `DR_LEDGER_MODE=legacy` env var → section omitted in all rounds.
- `tests/protocol/test_convergence_ledger.py` (new):
  - Self-counter says 0 + ledger says 0 → can_terminate returns
    True.
  - Self-counter says 0 + ledger says 3 → can_terminate returns
    False with "ledger reports 3 questions still open".
  - `DR_LEDGER_MODE=legacy` → ledger check skipped, agent
    self-counter is sole signal.
- `tests/ui/test_aggregator_ledger.py` (new):
  - `Run.phase_ledgers` populated on partner-vetting fixture.
  - `Run.drifts` empty on a clean fixture; non-empty on a synthetic
    drift fixture.

### 10. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.40.0 → 0.41.0.
- `CHANGELOG.md`: `## [0.41.0]` heading; new `[Unreleased]` placeholder.
- `VERSION_NOTES` entry at the top of `how-it-works.jsx`:
  > **0.41.0 — Authoritative cross-round ledger.** The system now
  > maintains a programmatic ledger of every claim / question /
  > disagreement / issue across rounds, derived from existing parsed
  > sections (no new agent output required). The next round's prompt
  > includes a `## Standing items from prior rounds` block so the
  > LLM has structured prior-state as input. Convergence requires
  > both the agent self-counters AND the system ledger to agree the
  > open-set is empty — silent ghosting no longer terminates a
  > phase. Ghosted items surface in the critique pane with a `⚠`
  > annotation. Toggle off with `DR_LEDGER_MODE=legacy`.

### 11. Files touched

Backend:
- `src/dual_research/ledger/__init__.py` (new)
- `src/dual_research/ledger/models.py` (new)
- `src/dual_research/ledger/build.py` (new)
- `src/dual_research/ledger/transitions.py` (new)
- `src/dual_research/ledger/prompt.py` (new)
- `src/dual_research/protocol/prompts.py` — standing_items parameter on negotiation/review templates
- `src/dual_research/protocol/convergence.py` — ledger cross-check
- `src/dual_research/orchestrator/phase2.py` — build ledger + inject standing items
- `src/dual_research/orchestrator/phase4.py` — same
- `src/dual_research/ui/models.py` — Run.phase_ledgers, Run.drifts, LedgerDrift dataclass
- `src/dual_research/ui/aggregator.py` — wire ledger build into load_run_snapshot

Frontend:
- `src/dual_research/ui/static/run-detail.jsx` — LedgerDriftBadge, GhostedAnnotation, Critique pane reads from phaseLedgers
- `src/dual_research/ui/static/how-it-works.jsx` — VERSION_NOTES

Tests:
- `tests/ledger/__init__.py` (new)
- `tests/ledger/test_models.py` (new)
- `tests/ledger/test_transitions.py` (new)
- `tests/ledger/test_build.py` (new)
- `tests/ledger/test_prompt.py` (new)
- `tests/orchestrator/test_phase2_standing_items.py` (new)
- `tests/protocol/test_convergence_ledger.py` (new)
- `tests/ui/test_aggregator_ledger.py` (new)

## Out of scope

- **Forcing agents to emit explicit per-item moves** (`addressed /
  maintained / withdrawn / escalated` per standing item every round).
  This was an option we considered and rejected — it imposes output
  compliance burden on the agent and risks degrading substantive
  quality. The ledger derives closure from existing sections; agents
  keep writing what they write today.
- **Removing the `OPEN_QUESTIONS:` / `OPEN_ISSUES:` self-counters
  from the protocol prompts.** They stay as a sanity-signal. Once
  the ledger has burned in across many runs and drift is rare, a
  future spec can deprecate.
- **Visual redesign of the Critique pane / Summary tab.** Spec 0046.
  This spec adds the data shape (`Run.phase_ledgers`) the redesign
  will consume.
- **Per-turn-card UI for the standing-items section the LLM sees.**
  The standing-items block is part of the prompt input — users see
  it via the existing Input tab on the full-view modal (which renders
  the persisted input bundle). No separate display.
- **A "ledger replay" debug surface in the UI.** The
  `<session>/ledger.json` sidecar is a debugging artefact for
  developers; surfacing the full state history in the UI is a
  follow-up.
- **Phase 1 ledger.** Phase 1 has one draft per agent (no rounds);
  there are no transitions to track. Claims raised in Phase 1 enter
  the *Phase 2* ledger as soon as Phase 2 begins (initial status
  `open`, raised_round = 0 with a special turn_key `phase1_<agent>`).
- **Cost reconciliation against the ledger.** Spec 0039 covered cost;
  this spec doesn't touch billing.
- **Cross-phase ledger queries** (e.g. "which Phase 2 claim hardened
  into a Phase 4 issue?"). Phase 2 and Phase 4 ledgers are
  independent. If a future spec wants cross-phase tracing, it can
  add a join layer on top.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec adds ~15-20 new
      tests across ledger / orchestrator / protocol / aggregator.
- [ ] Manual: fresh test run on a small prompt (via `dual-research-run`
      skill) with `DR_LEDGER_MODE=enforce` (default). Verify R2+
      prompts contain `## Standing items from prior rounds`
      section. Inspect the persisted input bundle at
      `<session>/inputs/phase2_round2_<agent>.json`.
- [ ] Manual: same prompt but with `DR_LEDGER_MODE=legacy`. Verify
      R2+ prompts do NOT contain the standing-items section.
      Convergence matches pre-spec behaviour (self-counter only).
- [ ] Manual: deliberately drift on a synthetic test — patch an
      agent's `OPEN_QUESTIONS: 0` while a question is still parseable.
      Verify convergence does NOT terminate the phase; UI shows
      `⚠ drift` badge on the turn card.
- [ ] Manual: partner-vetting fixture loads on local UI. Critique
      pane shows phase ledgers with `last_addressed_round` populated
      for answered questions, `ghosted_rounds` counter on any
      unaddressed items. No regression vs spec 0042's display.
- [ ] Preview-verified against partner-vetting fixture at
      `localhost:6173`.
- [ ] Hosted run on `dual-research-alex.fly.dev` — verify the
      ledger surfaces for the existing partner-vetting run on next
      page-load (auto-backfill via D11).

## Risks

- **Prompt size growth.** Standing-items section adds ~200-500
  tokens per round (depending on ledger depth). On a 5-round Phase 2
  that's 1-2.5k extra prompt tokens cumulative. At Claude Sonnet 4.6
  / GPT-5.5 rates that's ~$0.01-0.05 per run. Worth it for the
  structured input the agent gets back. Mitigation: `max_items=30` +
  `max_chars=3000` truncation caps growth on pathological runs.
- **Conservative convergence may extend round count.** If agent
  counters say "done" but ledger reports open items, the phase keeps
  running. On a sloppy agent this could add 1-2 rounds. On the
  partner-vetting fixture I expect 0 extra rounds (the agents
  converged cleanly). Mitigation: `hard_cap` from `Round` still
  caps total rounds — ledger can't loop forever. Plus the
  `DR_LEDGER_MODE=legacy` kill-switch is a clean rollback path.
- **Agent compliance with the new input format.** Agents might
  ignore the standing-items section if the instruction is too soft,
  OR get confused if it's too prescriptive. Mitigation: the
  instruction text is the only knob; tune iteratively if real-run
  experience shows poor uptake. The section is informational, not
  required — the agent's output protocol is unchanged.
- **Closure detection false-positives.** A question's
  body-prefix-match against a later `## Answers to:` section could
  match a paraphrased answer that doesn't actually address the
  question. Existing `reconstruct_questions` handles this with a
  `match: positional | verbatim` confidence signal; the ledger
  inherits that and treats `positional` matches as `answered` but
  with the original confidence preserved in `status_history`.
- **Closure detection false-negatives.** An agent answers a question
  in prose without using the `## Answers to:` section header. The
  ledger marks it ghosted; the user sees the `⚠` annotation; the
  agent gets the standing item back in the next round's input.
  This is the "extends round count" risk above but it's also the
  *correct* behaviour — if the protocol's answer-channel isn't used,
  we shouldn't silently mark it answered.
- **Ledger build cost on every snapshot.** O(rounds × items × kinds)
  with per-item closure checks. On the partner-vetting fixture
  (~70 items across 5 rounds) the build runs in <100ms. Should not
  affect cold-load performance. If a future run produces hundreds
  of items, we can cache the ledger in `metrics.json` alongside
  cost data.
- **Drift events may spam the UI on existing runs.** Pre-spec
  transcripts have agent counters but no ledger to compare against;
  the first load builds the ledger from scratch and computes drift
  retroactively. Partner-vetting may show several drift events for
  rounds where the counter and the parsed-count differed historically.
  This is honest — the drift was always there, we just couldn't see
  it. The UI can show them with a "historical" tint to distinguish
  from live drift on a fresh run.

## Open questions

- Whether the standing-items section should include the body
  snippet inline OR just the ID + a "see prior turn" reference.
  v1 includes the snippet (~50 chars) for context. If real-run
  experience shows agents responding more reliably with just IDs
  + reference, v2 can trim. Trade-off is prompt tokens vs cognitive
  ease.
- Whether `claim → escalated` transitions should auto-create a
  corresponding disagreement ledger entry, or leave the disagreement
  as a separate parser-driven entry. v1 leaves them separate — the
  ledger has both the claim (status: escalated) and the disagreement
  (status: open) with the same D-N. UI can render them as linked
  history. A cleaner model might collapse them into one entry with
  a kind transition; defer until we see how the UI reads it.
- Whether to enforce that an agent's per-turn `## Answers to:`
  section references all open questions from the prior round (and
  fail-validate the turn if it doesn't). v1 doesn't enforce — the
  ledger's ghosted-rounds counter is the signal. Strict enforcement
  would be a follow-up spec if ghosting is common in real runs.
- Whether the kill-switch should be a per-run override (in the
  `dual-research run` CLI) instead of just an env flag. v1 is
  env-flag-only since the use case is "roll back if something
  breaks across all runs"; per-run override can land later.
