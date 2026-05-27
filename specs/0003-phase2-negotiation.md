---
spec: 0003
title: Phase 2 — plan negotiation with caps, repair, and drafter tiebreak
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.4.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/3"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0003 — Phase 2: plan negotiation

## Context

Spec 0002 ran Phase 0 (preflight) + Phase 1 (parallel research) and stopped. This spec implements Phase 2 — the turn-based plan-negotiation conversation where the two agents alternately propose, critique, and converge on a single plan + drafter. This is the most complex phase in the protocol; once it works, Phase 3 (drafting) and Phase 4 (review) follow the same general shape and are smaller specs.

End state of this spec: after `dual-research --prompt "..."` finishes Phase 1, the orchestrator runs Phase 2 turn pairs in a loop until both agents emit `STATUS: AGREED` with hash-matched `AGREED_PLAN` blocks and a chosen drafter — or the hard cap is hit. The session directory grows a `phase2/` subdirectory of `round-NN-{agent}.md` turn files. State (`drafter`, `agreed_plan`, `final_surfaced_disagreements`) lands in `state.json` on convergence.

Web search wiring is deferred to a follow-up spec — Phase 2 prompts already accommodate "(none)" for corroboration sections when search returns nothing.

## Proposed change

### New modules

```
src/dual_research/orchestrator/
  phase2.py          # the main negotiation loop
  repair.py          # malformed-turn repair flow
  _turns.py          # turn-file IO helpers (read, write, list, naming)
```

### Round-1 well-formedness

The original protocol exempts round 1 of Phase 2 from the strict well-formedness check (round 1 cannot agree; only STATUS, DRAFTER, OPEN_QUESTIONS are required). Add:

```python
# In protocol/convergence.py
def assert_well_formed_round1_turn(p: ParsedTurn, agent: str) -> None:
    """Round-1 minimal check: STATUS, DRAFTER, OPEN_QUESTIONS only."""
```

### Phase 2 loop

```
for round in 1..hard_cap:
    build prompts (round-1 vs round-2+ have different prompts)
    run both agents in parallel via asyncio.gather
    write turn files: phase2/round-NN-claude.md, phase2/round-NN-openai.md

    for each agent:
        parse turn
        validate well-formedness (round-1 leniency)
        on ProtocolParseError → invoke repair (budget = 1 per agent per phase;
            second consecutive failure across rounds → exit 52)

    emit Phase2RoundComplete with parsed states

    if is_plan_agreed:
        extract agreed_plan + canonical FSD items into state
        save state (drafter, agreed_plan, FSDs)
        break → advance to Phase 3

    elif all_substantive_gates_pass_except_drafter:
        invoke pick_drafter (domain-fit → plan-alignment → hash-of-brief)
        save state with selected drafter + agreed_plan
        emit DrafterTiebreakResolved
        break → advance to Phase 3

    if round == soft_cap:
        emit SoftCapHit, log warning, continue (autonomous mode)

    if round == hard_cap:
        emit HardCapHit, write deadlock artifacts, exit 51

run_session: catches the ProtocolParseError-after-repair case and exits 52;
the hard-cap path returns exit 51.
```

### Repair flow

When a parsed turn fails `assert_well_formed_*`, the orchestrator:

1. Increments the agent's `consecutive_failures` counter (across rounds, per phase).
2. If counter ≥ 2: raise `ProtocolParseError` up to `run_session` → exit 52 with state preserved.
3. Saves the malformed text to `phase2/round-NN-{agent}.malformed-N.md` (audit trail).
4. If the per-phase budget > 0: spends one budget unit and invokes the agent again with `repair_prompt(...)`. The repair call's output overwrites `round-NN-{agent}.md`. Emit `RepairInvoked`.
5. Re-parses and re-validates the repaired turn. If still malformed, leaves it (next round's check will hit `consecutive_failures = 2` and exit 52). If valid, resets `consecutive_failures` to 0.

The repair call is metered into the run's total cost like any other agent call.

### Caps

- **Soft cap** (default 6): logged warning, run continues. No prompting (autonomous-only).
- **Hard cap** (default 12): emit `HardCapHit`, write `final.md` placeholder containing both agents' last turns under "Reviewer disagreements (unresolved after N rounds)", set state to `done` with the deadlock-appendix indicator, return exit 51 from `run_session`.

### Prior-turn inlining

The negotiation_turn_prompt (rounds 2+) inlines every prior turn from the same phase. Reading them is a small helper in `_turns.py`:

```python
def list_phase2_turns(session: SessionDirectory, up_to_round: int) -> list[PriorTurn]:
    """Return PriorTurn(agent, round, content) for every round <= up_to_round,
    sorted by (round, agent)."""
```

### State updates on convergence

When `is_plan_agreed` returns true OR when the drafter tiebreak resolves:

```python
state.phase = "phase3"
state.drafter = agreed_drafter
state.agreed_plan = parsed_claude_turn.agreed_plan  # hash-verified by isPlanAgreed
state.final_surfaced_disagreements = extract_canonical_fsd_items(agreed_plan)
session.save_state(state)
```

### Event types added

```python
# events/types.py
class Phase2RoundComplete(Event):
    round: int
    agreed: bool
    claude_status: str | None
    openai_status: str | None
    claude_drafter: str | None
    openai_drafter: str | None
    claude_open_questions: int | None
    openai_open_questions: int | None
    claude_blocking: int | None
    openai_blocking: int | None
    claude_fsd: int | None
    openai_fsd: int | None

class RepairInvoked(Event):
    agent: str
    phase: int
    round: int
    errors: list[str]
    budget_remaining: int

class SoftCapHit(Event):
    phase: str  # "phase2" | "phase4"
    round: int
    cap: int

class HardCapHit(Event):
    phase: str
    round: int
    cap: int

class DrafterTiebreakResolved(Event):
    round: int
    selected_drafter: str
    reason: str  # "domain-fit" | "plan-alignment" | "hash-of-brief"
    claude_proposed: str | None
    openai_proposed: str | None

class Phase2Complete(Event):
    rounds: int
    converged: bool
    drafter: str | None
    fsd_count: int
    via_tiebreak: bool
```

### Exit codes

```python
EXIT_HARD_CAP = 51
EXIT_PROTOCOL_PARSE_FAILURE = 52
```

`run_session` returns these in its `RunResult.exit_code`; the CLI propagates as the process exit code.

### Files added or modified

- `src/dual_research/orchestrator/phase2.py` (new)
- `src/dual_research/orchestrator/repair.py` (new)
- `src/dual_research/orchestrator/_turns.py` (new)
- `src/dual_research/orchestrator/run.py` — invoke `run_phase2` after Phase 1; return appropriate exit codes
- `src/dual_research/orchestrator/__init__.py` — export new exit codes
- `src/dual_research/events/types.py` — five new event types
- `src/dual_research/events/__init__.py` — re-export them
- `src/dual_research/protocol/convergence.py` — `assert_well_formed_round1_turn`
- `src/dual_research/protocol/__init__.py` — re-export it
- `tests/orchestrator/test_phase2.py` (new) — stub-agent convergence, tiebreak, repair, hard-cap paths
- `tests/orchestrator/test_turns.py` (new) — turn-file helpers
- `CHANGELOG.md`, `pyproject.toml`, `__init__.py` — version 0.3.0 → 0.4.0

## Out of scope

- **Web search wiring** — deferred to a focused follow-up spec (spec 0005). Phase 2 prompts handle the "(none)" search case.
- **Phase 3 / Phase 4** — separate specs.
- **Resume from prior session.** Still deferred.
- **Live UI subscription to Phase 2 events.** The events are emitted; the consumer is the future UI in a later spec.

## Test plan

- [ ] Unit: `assert_well_formed_round1_turn` accepts the round-1 minimum; rejects missing STATUS / DRAFTER / OPEN_QUESTIONS
- [ ] Unit: `list_phase2_turns` returns turns in `(round, agent)` order across multiple rounds
- [ ] Unit (stub agents): Phase 2 converges when both agents emit AGREED with matching plans → state advanced to phase3, drafter set, FSDs extracted
- [ ] Unit (stub agents): drafter-tiebreak path — all substantive gates pass but drafters differ → `pick_drafter` invoked, `DrafterTiebreakResolved` emitted, state advanced
- [ ] Unit (stub agents): malformed turn → repair invoked once, budget decrements; second consecutive failure raises ProtocolParseError
- [ ] Unit (stub agents): repair-then-valid path resets `consecutive_failures`
- [ ] Unit (stub agents): hard cap → `HardCapHit` emitted, exit code 51, deadlock artifacts on disk
- [ ] E2E: real-API run on a synthetic brief with `--soft-cap 3 --hard-cap 6` (small caps to limit cost) using the test tier. Expected: either converges or hits soft/hard cap cleanly. Verify state.json, transcript, metrics.
- [ ] All 49 existing tests still pass

## Risks

- **E2E flakiness on real APIs.** Agents may emit slightly malformed output, triggering repair. That's the point of the repair flow; it should be exercised, not avoided. If we observe >50% repair rate on the synthetic brief, prompt adjustments are warranted (but ONLY plumbing, not substance — see spec 0001 / repo rules).
- **Cost.** With `soft-cap 3 hard-cap 6` and the test tier, expect $0.10–$0.80 per E2E. If it exceeds $1.50, abort and inspect the brief / prompts.
- **State drift on parse failures.** Mitigation: state.json is only written when a phase completes successfully; mid-phase failures leave `phase: "phase2"` and a partial transcript that's diagnosable.
- **Round-1 leniency miscalibration.** If agents produce malformed round-1 output, current code accepts it (only STATUS/DRAFTER/OPEN_QUESTIONS checked). Round 2 will then have insufficient context. Mitigation: well-formedness for round 1 is intentionally narrow; substantive content is enforced by prompt structure, not parser.
