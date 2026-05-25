---
kind: draft
draft_id: "004"
slug: raiser-self-address-observability
title: Make raiser self-ADDRESS visible via ProtocolViolation
type: bug
status: draft
created: 2026-05-25
source_session: ""
---

# Draft 004 — Make raiser self-ADDRESS visible via ProtocolViolation

## Context

The protocol forbids an agent from ADDRESS-ing an item they themselves
raised — only the *other* agent's items can be addressed. The orchestrator
already enforces this at
[deep_research.py:379-381](src/dual_research/orchestrator/deep_research.py:379)
by silently `continue`-ing past the offending block. The drop is correct
behavior, but it's invisible: no `ProtocolViolation` is emitted, the dashboard
shows nothing, and the agent gets no feedback that it just wasted a turn.

The smoking gun is
`runs/20260521-010637-dvs-backend-language-choice/phase2/round-04-claude.md`,
where Claude (raiser of `D-plan-c-05`) re-ADDRESSed its own item inside the
"Addressing items raised against me" section. The validator swallowed the
block, the run continued, and we only noticed by reading the raw round file.
The bug is two-fold: (1) missing observability on the orchestrator side, and
(2) the prompt's Ratifying section enumerates the valid raiser actions
(RESOLVE / ACKNOWLEDGE / WITHDRAW / counter-argument) without explicitly
saying "do not use ADDRESS for your own items."

## Sketch / proposed direction

- **Emit a violation instead of silent drop.** Replace the bare `continue`
  at [deep_research.py:379-381](src/dual_research/orchestrator/deep_research.py:379)
  with:
  ```python
  if ent.raiser == agent:
      violations.append(ProtocolViolation(
          phase=self.phase,
          round=round,
          agent=agent,
          violation_code="raiser_self_address",
          item_id=ent.id,
          from_state=ent.current_state.value,
          dropped_block=blk.raw_text[:1000],
      ))
      continue
  ```
  The drop itself is preserved — this is purely additive event emission so
  the misuse shows up in the run ledger and on the dashboard.

- **Register the new violation code.** If `src/dual_research/protocol/errors.py`
  enumerates codes (see the existing `terminal_state_re_address` peer code
  referenced near [deep_research.py:395](src/dual_research/orchestrator/deep_research.py:395)),
  add `raiser_self_address` alongside it.

- **Teach the prompt the right pattern.** In each Ratifying section of
  `src/dual_research/protocol/prompts.py` (phase 0, phase 2, phase 4 review
  prompts; the structure at [prompts.py:2117-2119](src/dual_research/protocol/prompts.py:2117)
  is one of three to update consistently), add an explicit line stating
  that the raiser of an item in `addressed` state uses
  RESOLVE / ACKNOWLEDGE / WITHDRAW / counter-argument **in this section**,
  never ADDRESS. ADDRESS is reserved for the other agent's items, in the
  "Addressing items raised against me" section.

- **Tests** under a new
  `tests/orchestrator/test_spec_NNNN_raiser_self_address.py`:
  - Construct a turn where agent X raised item I and then emits an ADDRESS
    block targeting I; `apply_turn` returns a
    `ProtocolViolation(code="raiser_self_address")` and the item's state is
    unchanged (drop preserved).
  - Replay `round-04-claude.md` from the run fixture and assert the same
    violation surfaces.
  - Negative: agent Y (not the raiser) ADDRESS-ing item I emits no
    `raiser_self_address` violation and the ledger transitions normally.
  - Negative: a counter-argument from the raiser inside the Ratifying
    section parses cleanly with no violation.

- **PATCH bump.** Bug fix only, no public-API change. Bump
  `pyproject.toml` and `src/dual_research/__init__.py`; update
  `CHANGELOG.md`.

## Files touched

- `src/dual_research/orchestrator/deep_research.py` — additive violation emission
- `src/dual_research/protocol/errors.py` — new code (if codes enumerated)
- `src/dual_research/protocol/prompts.py` — Ratifying-section clarification across phases 0/2/4
- `tests/orchestrator/test_spec_NNNN_raiser_self_address.py` — new
- `CHANGELOG.md`
- `pyproject.toml` + `src/dual_research/__init__.py` (PATCH bump)
