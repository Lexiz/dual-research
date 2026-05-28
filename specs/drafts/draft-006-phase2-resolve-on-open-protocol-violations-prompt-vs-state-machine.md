---
kind: draft
draft_id: "006"
slug: phase2-resolve-on-open-protocol-violations-prompt-vs-state-machine
title: "Phase 2 agents repeatedly emit RESOLVE on items still in 'open' state — prompt/agent mismatch with the 0228 state machine"
status: draft
created: 2026-05-28
source_session: deferred-from-0241-diagnostic-rerun-pair
parent_spec: null
disposition: defer
disposition_reason: "Real but non-blocking — 0228's state-machine guard handles it correctly (emits ProtocolViolation, run continues). Cowork flagged it as a separate prompt/agent issue to park while we focus on the H3 process-death class. Promote only if it becomes a convergence-blocker or if the rate increases."
---

# Draft 006 — Phase 2 agents emit RESOLVE on items still in `open` state

> **Source:** Pattern observed in the post-0241 diagnostic re-run pair: [`runs/20260527-200213-backend-language-choice/`](runs/20260527-200213-backend-language-choice/) (5 PVs in phase 2 r2 claude), [`runs/20260528-061323-backend-language-choice/`](runs/20260528-061323-backend-language-choice/) (8 PVs in phase 2 r2 across both agents). Same `reason: "RESOLVE attempted on item in 'open'; expected 'addressed'"` and `reason: "RESOLVE issued by claude but item was raised by openai"`. Cowork sign-off `cowork/briefs/2026-05-28-h3-caffeinate-first-then-0242.md`: "real but not the killer — orchestrator handled them correctly; separate prompt/agent issue to park."

## Context

The 0228 state machine requires items to transition `open → addressed → resolved` (or other valid paths). Agents in phase 2 round 2 are emitting RESOLVE markers on items that are still in `open` state — skipping the `addressed` step — and on items that were raised by the OTHER agent (where the convention is the raiser does the resolve).

The orchestrator's behaviour is correct: 0228 catches these as `ProtocolViolation(state_machine_invalid_op)` and the run continues. The items remain in their pre-violation state. No crash, no convergence corruption.

**But**: the agents keep doing it. Either (a) the agent prompt is ambiguous about when RESOLVE is allowed, (b) the agent's understanding of "addressed" vs "open" drifts during long phase-2 turns, or (c) the state-machine contract changed at some point and the prompt didn't catch up.

## Why this is a draft, not a spec

Three remediation paths, none obviously right yet:

1. **Tighten the agent prompt.** Add an explicit "you may ONLY RESOLVE items currently in `addressed` state that YOU raised" preamble. Cheap; might not stick across the agent's whole context window.
2. **Allow RESOLVE-from-open as a legal transition.** Treat the agent's emission as authoritative; let RESOLVE skip the `addressed` step when the agent has both addressed AND resolved the item in the same turn. Changes the contract (0228 surface), needs careful test coverage.
3. **Bidirectional resolution.** Allow either agent to RESOLVE an item regardless of original raiser, if the resolution body addresses the item substantively. Convention change.

Decision is gated on data we don't yet have: how often does this fire on a successfully-completing run? Today every observed phase-2 run died before convergence, so we can't tell if the violations are a correlated symptom of stress or a true persistent agent-prompt gap.

## Trigger to promote

- A live re-run completes successfully AND the post-fix PV rate on RESOLVE-on-open is still meaningful (>2 per run).
- OR an agent prompt change is needed for an unrelated reason (e.g. a CLAUDE.md update on contract semantics) — bundle this fix in.
- OR a future convergence-rule spec needs the state-machine surface clarified — bundle this as a dependency.

## Out of scope for this draft

- Fixing the state machine surface in 0228. Out of scope until we know whether the prompt is the right lever.
- Changing the orchestrator's PV handling. The current behaviour (emit, log, continue) is correct.

## Pointers

- 0228 state-machine contract: [`src/dual_research/contract/verifier.py`](src/dual_research/contract/verifier.py) `_check_i4_4` and the `state_machine_invalid_op` ProtocolViolation kind.
- Agent prompts for phase 2: [`src/dual_research/protocol/prompts.py`](src/dual_research/protocol/prompts.py) — search for `RESOLVE` and the phase-2 round protocol section.
- Evidence runs: 200213, 061323 transcripts (both in `runs/` corpus, not yet promoted to fixtures).
