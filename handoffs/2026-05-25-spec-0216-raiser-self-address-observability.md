---
spec: "0216"
date: 2026-05-25
version: 1.44.21
pr: https://github.com/Lexiz/dual-research/pull/252
kind: deploy
---

# Spec 0216 — Make raiser self-ADDRESS visible via ProtocolViolation

Shipped as v1.44.21. The orchestrator no longer silently drops the
`raiser == agent` case in the ADDRESS handler. When an agent emits an
ADDRESS block targeting an item it itself raised (protocol-forbidden —
only the *other* agent's items can be addressed), the misuse now surfaces
as a `ProtocolViolation(violation_code="raiser_self_address", item_id=…,
from_state=…)` before the existing `continue`. Drop semantics are
unchanged.

This is **Spec 3 of 3** in the sequenced bug-fix batch from the phase-4 /
phase-2 investigation. Sibling fixes shipped earlier today:
- spec 0214 — Drop phase-4 agent-emitted hash gate (v1.44.19).
- spec 0215 — Fix in-round partner blindness in list_turns (v1.44.20).

## What landed

**Code (4 edits, all narrow):**

- `src/dual_research/orchestrator/deep_research.py` — the `raiser ==
  agent` branch at ~line 379 gained the `violations.append(
  ProtocolViolation(...))` call mirroring the peer
  `terminal_state_re_address` branch immediately below. Field shape
  matches the peer (phase, round, agent, violation_code, item_id,
  from_state, dropped_block); `dropped_block` is capped at 1000 chars
  exactly like the peer.
- `src/dual_research/protocol/prompts.py` — the Ratifying-section
  parentheticals at all three interaction phases (0/2/4) gained an
  explicit `"Do NOT use ADDRESS here; ADDRESS is reserved for the other
  agent's items in the 'Addressing items raised against me' section
  above."` line appended to the existing instructions. Purely additive
  text inside the parenthesised instruction blocks — no
  structural-marker change, no removed instructions.
- `src/dual_research/events/types.py` — the `ProtocolViolation`
  doc-comment was widened from "this fires for exactly one case" to a
  bulleted enumeration of both codes in use today
  (`terminal_state_re_address` + the new `raiser_self_address`).
  Documentation only; no consumer behaviour change.

**Tests (5 new + 1 widened):**

- New file `tests/orchestrator/test_spec_0216_raiser_self_address.py`
  covers:
  - `test_raiser_self_address_emits_protocol_violation_with_item_id_and_from_state`
    — `open` source state.
  - `test_raiser_self_address_emits_violation_when_own_item_is_addressed_state`
    — `addressed` source state (the smoking-gun scenario).
  - `test_replay_round04_claude_self_address_emits_violation` — replay
    test against the actual failing turn from
    `runs/20260521-010637-dvs-backend-language-choice/phase2/round-04-claude.md`,
    copied verbatim into `tests/fixtures/raiser_self_address_replay/`.
    Locks in that the real failing scenario now surfaces a violation.
  - `test_other_agent_address_does_not_emit_raiser_self_address` —
    negative; non-raiser address still transitions cleanly.
  - `test_raiser_resolve_or_withdraw_does_not_emit_violation` —
    negative; legitimate raiser-side ratifications still work.
- `tests/ledger/test_replay_spec_0141.py` — the anchor-run replay
  assertion was widened. Pre-fix the test asserted *every*
  `ProtocolViolation` carried code `terminal_state_re_address`. Post-fix
  it accepts both codes against a `known_codes` set and pins the B02
  smoking-gun assertion that at least one `terminal_state_re_address`
  is present.

Full suite: **1955 passed**.

## Deploy

`.github/workflows/deploy.yml` run
[26402531137](https://github.com/Lexiz/dual-research/actions/runs/26402531137)
succeeded on `main` commit `6ec363021d72be12607e081d9e71c3c6b5391ebe`.
Smoke: `https://dual-research-alex.fly.dev/` returns HTTP 200.

## Observability post-deploy

Future DR runs that exhibit a raiser self-ADDRESS will produce a
`protocol_violation` event with `violation_code: raiser_self_address`.
The dashboard's existing renderer for `ProtocolViolation` events handles
unknown `violation_code` strings generically (the
`terminal_state_re_address` code already routes through that path), so
the new code will surface as a violation chip without renderer change.
Spec 0216 §4 / §6 / §8 anticipate this — no follow-up to the renderer
is gated on this spec.

## Not done — explicitly punted

The spec was scoped narrowly to **observability only**. The following are
out-of-scope per the spec body and are not deferrals — they were never
in scope and would land as separate specs if they're wanted:

- Surfacing the new violation as feedback inside the offending agent's
  next-round prompt (so the prompt actively coaches against re-emitting).
- Broader Ratifying-section prompt rework (only the minimal "do not use
  ADDRESS here" line was added).
- Dashboard renderer special-casing for the new code (custom icon /
  colour).
