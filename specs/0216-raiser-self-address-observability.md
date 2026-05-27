---
kind: dev
spec: "0216"
slug: raiser-self-address-observability
title: "Make raiser self-ADDRESS visible via ProtocolViolation"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-25
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: "004"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0216 — Make raiser self-ADDRESS visible via ProtocolViolation

> **Type:** bug  |  **Severity:** P2 (observability gap; behaviour itself is correct)  |  **Affects:** all 3 interaction phases (0, 2, 4) — anywhere `apply_turn` parses ADDRESS blocks
> **Bump:** PATCH — bug fix
> **Evidence:** local run `runs/20260521-010637-dvs-backend-language-choice/phase2/round-04-claude.md` — Claude (raiser of `D-plan-c-05`) re-ADDRESSed its own item inside the "Addressing items raised against me" section; the orchestrator dropped the block silently, the dashboard showed nothing, and the misuse was only spotted by manually reading the raw turn file. `runs/` is gitignored; cited for human reference.

This is **Spec 3 of 3** in a sequenced bug-fix batch from the phase-4 / phase-2 investigation. Sibling fixes: spec 0214 (hash-gate deadlock) and spec 0215 (in-round partner blindness).

---

## 1. Reproduction

**Environment:** dual-research orchestrator at HEAD on 2026-05-25; Deep Research protocol, any interaction phase (0/2/4). Models: prod-tier `claude` + `openai`.

**Steps:**

1. Fire any DR run that reaches a round where one agent has items in `addressed` state.
2. Manually craft (or coax via prompt drift) a turn from that agent containing an `ADDRESS` block whose `item_id` matches an item the same agent originally raised.
3. Run the turn through the orchestrator's `apply_turn` path.

**Expected:** The orchestrator drops the misuse (correct — raisers cannot ADDRESS their own items; only the other agent's items can be addressed) AND emits a `ProtocolViolation` event with code `raiser_self_address`, so the misuse appears in the run ledger and on the dashboard, and downstream feedback (future closeout / drift detection / surfaced-in-prompt-next-round) can pick it up.

**Actual:** The drop happens silently at [`src/dual_research/orchestrator/deep_research.py:379-381`](src/dual_research/orchestrator/deep_research.py:379) via a bare `continue`. No `ProtocolViolation` emitted, no dashboard signal, no transcript entry. The agent wastes the turn slot and gets no feedback that the block was discarded.

**Smoking-gun reference:** local `runs/20260521-010637-dvs-backend-language-choice/phase2/round-04-claude.md` — Claude raised `D-plan-c-05` in an earlier round, OpenAI ADDRESSed it (state → `addressed`), and Claude's round-4 turn put an ADDRESS block targeting `D-plan-c-05` inside its "Addressing items raised against me" section. The validator swallowed the block; the run continued; the only signal was a human reading the raw file.

## 2. Root cause hypothesis

Two collaborating gaps:

**Gap A — silent drop, no event** ([`src/dual_research/orchestrator/deep_research.py:378-381`](src/dual_research/orchestrator/deep_research.py:378)):

```python
if ent.raiser == agent:
    # An agent cannot ADDRESS their own item; ignore.
    continue
```

Compare against the immediately-following branch ([`deep_research.py:382-400`](src/dual_research/orchestrator/deep_research.py:382)) which handles terminal-state re-address: that one appends a `ProtocolViolation(violation_code="terminal_state_re_address", ...)` before `continue`-ing. The raiser-self-address peer branch is structurally identical but skips the event emission — the bug is the missing append, not the drop semantics.

**Gap B — prompt doesn't enumerate the prohibition.** The phase-0/2/4 Ratifying-section instructions at [`prompts.py:1631-1633`](src/dual_research/protocol/prompts.py:1631), [`prompts.py:1849-1851`](src/dual_research/protocol/prompts.py:1849), and [`prompts.py:2117-2119`](src/dual_research/protocol/prompts.py:2117) list the valid raiser actions for items in `addressed` state (RESOLVE / ACKNOWLEDGE / WITHDRAW / counter-argument) but never explicitly state "do not use ADDRESS for your own items." Drift in the wild is predictable: an agent looking at a partner's ADDRESS-then-RESOLVE pattern mirrors the structure into its own Ratifying section.

`src/dual_research/protocol/errors.py` does NOT enumerate violation codes (read the file — it only defines `Status` enum and `ProtocolParseError`). Codes are inline string literals at the `ProtocolViolation` construction sites. So "register the new code" is just "use a new string"; no schema/enum edit.

## 3. Fix

Three additive edits — none change existing behaviour, only add observability and prompt clarity.

### Code changes (verified file:line refs at HEAD on 2026-05-25)

**1. `src/dual_research/orchestrator/deep_research.py:378-381` — emit a violation before dropping.**

Replace:

```python
if ent.raiser == agent:
    # An agent cannot ADDRESS their own item; ignore.
    continue
```

With:

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

The drop semantics are unchanged — same `continue`, same downstream state. This is purely additive event emission so the misuse surfaces in the ledger and on the dashboard. Field order mirrors the peer `terminal_state_re_address` emission a few lines below at [`deep_research.py:390-399`](src/dual_research/orchestrator/deep_research.py:390); reuse the same `dropped_block=blk.raw_text[:1000]` cap.

**2. `src/dual_research/protocol/errors.py` — NO change required.**

The file does not enumerate violation codes (verified by inspection: only `Status` enum and `ProtocolParseError` class). Codes are inline strings at the `ProtocolViolation(violation_code=...)` call sites and the documenting comment on `ProtocolViolation` in `events/types.py:519`. Optionally extend that doc-comment to mention the new code alongside `terminal_state_re_address`; the edit is documentation-only and won't affect any consumer.

**3. `src/dual_research/protocol/prompts.py` — clarify the Ratifying-section instructions across phases 0/2/4.**

Three sites need the same clarifying line appended to the parenthesised instructions:

- **Phase 0 (input-negotiation), [`prompts.py:1631-1633`](src/dual_research/protocol/prompts.py:1631):**

  Before:
  ```
  (For every one of your raised items currently in `addressed` state,
   emit RESOLVE, ACKNOWLEDGE, WITHDRAW, or a counter-argument that flips
   it back to open. Silent skipping is rejected.)
  ```
  After:
  ```
  (For every one of your raised items currently in `addressed` state,
   emit RESOLVE, ACKNOWLEDGE, WITHDRAW, or a counter-argument that flips
   it back to open. Silent skipping is rejected. Do NOT use ADDRESS here;
   ADDRESS is reserved for the other agent's items in the "Addressing
   items raised against me" section above.)
  ```

- **Phase 2 (plan-negotiation), [`prompts.py:1849-1851`](src/dual_research/protocol/prompts.py:1849):**

  Before:
  ```
  (For every item you raised that's in `addressed` state: RESOLVE,
   ACKNOWLEDGE, WITHDRAW, or counter-argument. No silent skips.)
  ```
  After:
  ```
  (For every item you raised that's in `addressed` state: RESOLVE,
   ACKNOWLEDGE, WITHDRAW, or counter-argument. No silent skips. Do NOT
   use ADDRESS here; ADDRESS is reserved for the other agent's items in
   the "Addressing items raised against me" section above.)
  ```

- **Phase 4 (cross-review), [`prompts.py:2117-2119`](src/dual_research/protocol/prompts.py:2117):**

  Before:
  ```
  (RESOLVE / ACKNOWLEDGE / WITHDRAW / counter-argument for every one of
   your items in `addressed` state.)
  ```
  After:
  ```
  (RESOLVE / ACKNOWLEDGE / WITHDRAW / counter-argument for every one of
   your items in `addressed` state. Do NOT use ADDRESS here; ADDRESS is
   reserved for the other agent's items in the "Addressing items raised
   against me" section above.)
  ```

The three "first round" placeholder Ratifying sections at lines 1560, 1774, 2028 (each reading `(none — first round)`) are unchanged.

## 4. User stories & acceptance criteria

Not a UI bug — skipped per the bug template's "REQUIRED for UI bug fixes" gate. The §5 regression-prevention tests are the load-bearing acceptance criteria.

The dashboard will surface the new violation code through its existing `ProtocolViolation` rendering path (the dashboard already renders `terminal_state_re_address` and other codes generically by string); no dashboard schema change required. Verify by inspecting one post-fix run's dashboard view that the new code appears as a violation chip.

## 5. Regression-prevention test

**New test file: `tests/orchestrator/test_spec_0216_raiser_self_address.py`:**

- [ ] `test_raiser_self_address_emits_protocol_violation_with_item_id_and_from_state` — fixture: agent X raised item I (state `open`); X's next turn parses to a turn containing an ADDRESS block targeting I. Call `apply_turn`. Assert: exactly one `ProtocolViolation(violation_code="raiser_self_address", item_id=I.id, from_state="open", agent=X, dropped_block=<non-empty>)` in the returned violations list, AND `I.current_state == open` (drop preserved — state unchanged). Locks in observability + preserves correct drop behaviour.
- [ ] `test_raiser_self_address_emits_violation_when_own_item_is_addressed_state` — same as above but I is in `addressed` state (the smoking-gun scenario). Assert the violation fires with `from_state="addressed"` and the item remains in `addressed` state (no re-ADDRESS, no state regression).
- [ ] **Replay fixture test: `test_replay_round04_claude_self_address_emits_violation`** — copy `round-04-claude.md` from the local failing run into `tests/fixtures/raiser_self_address_replay/` and commit it. Parse with `parse_turn_v2`; build a `DeepResearchState` stub where Claude is the raiser of `D-plan-c-05` and the item is in `addressed` state; call `apply_turn`. Assert: a `ProtocolViolation(violation_code="raiser_self_address", item_id="D-plan-c-05", agent="claude", from_state="addressed")` is emitted. Locks in that the actual failing scenario surfaces a violation post-fix.
- [ ] **Negative: `test_other_agent_address_does_not_emit_raiser_self_address`** — agent Y (not the raiser of I) emits an ADDRESS block targeting I. Assert: no `raiser_self_address` violation; state transitions normally to `addressed`. Locks in we didn't broaden the gate.
- [ ] **Negative: `test_raiser_counter_argument_or_resolve_does_not_emit_violation`** — agent X raises item I, OpenAI ADDRESSes it (state `addressed`), X emits RESOLVE/ACKNOWLEDGE/WITHDRAW for I in the Ratifying section. Assert: no `raiser_self_address` violation; state transitions cleanly. Locks in counter-arguments and proper raiser-side ratifications keep working.

**Existing tests:**

- [ ] Run `uv run pytest tests/orchestrator/ tests/protocol/ -q` to verify no existing test asserts on the *absence* of any violation in the raiser-self-address path. Update any such assertion if found; the violation count for affected fixtures changes from 0 to 1 for the new code.

## 6. Blast radius

- The bare `continue` at `deep_research.py:379-381` has no other callers — it's an internal control-flow branch inside the ADDRESS handler. Verified by file inspection.
- `ProtocolViolation` event schema ([`events/types.py:499-525`](src/dual_research/events/types.py:499)) already supports the fields we populate. Adding a new code string doesn't require schema migration.
- Dashboard renders `ProtocolViolation` events generically by `violation_code`; the new code surfaces with no renderer change. (The renderer may apply a default styling if the code is unknown — confirm by inspecting one post-fix run's dashboard view.)
- The three prompt edits are purely additive text inside parenthesised instruction blocks. No structural-marker change. Agents that already follow the protocol correctly are unaffected.
- `src/dual_research/protocol/errors.py` does NOT need to change (no enum exists). Optional doc-comment update on `ProtocolViolation` in `events/types.py:519` is documentation-only.
- Specs 0214 (hash gate) and 0215 (in-round partner blindness) — independent. Either ships first without conflict; this spec touches only the ADDRESS-handling branch and prompt parenthetical text.

## 7. Out of scope

- Surfacing the new violation in the next-round prompt as feedback to the offending agent — separate concern. Once observability exists, a follow-up spec can decide whether to echo the violation back into the prompt to actively coach against the misuse. Not gated on this spec.
- Bug #1 (phase-4 hash-gate deadlock) — spec 0214.
- Bug #2 (in-round partner blindness in `_drive_interaction_phase`) — spec 0215.
- Broader prompt rework for the Ratifying section — only the minimal clarifying line is added; no structural reshuffle.
- CHANGELOG / version bump — handled by the standard `/dev-next` flow (`pyproject.toml`, `src/dual_research/__init__.py`, PATCH bump, `### Fixed` entry linking back to this spec).
- Dashboard renderer special-casing for the new code (custom icon, colour) — generic rendering is sufficient; revisit if the misuse pattern proves frequent in production runs.

## 8. Risks

- **Risk:** Some existing test asserts on the *absence* of any `ProtocolViolation` in a path that happens to include a raiser-self-address misuse (i.e. depends on the silent drop as load-bearing behaviour).
  **Mitigation:** Run the full orchestrator + protocol test suite early in implementation; update violation-count assertions on any affected fixture. Low likelihood — the protocol's invariant is "violations are flagged, not hidden"; current absence is the bug.

- **Risk:** Agents over-correct after the prompt clarification and stop emitting *legitimate* counter-arguments in the Ratifying section (confusing "ADDRESS-block-shaped counter-argument" with "ADDRESS block").
  **Mitigation:** The clarifying sentence only forbids the ADDRESS marker name; counter-arguments are not ADDRESS blocks (they're free-form prose under the raiser's section). The existing instruction text already names "counter-argument" as a valid raiser action — adding the negative ADDRESS rule doesn't remove anything. PATCH bump means short rollout window; monitor the first few post-deploy runs to confirm raiser counter-arguments still appear.

- **Risk:** Dashboard renders the new code without a label/colour and looks broken.
  **Mitigation:** The dashboard already handles unknown violation codes (`terminal_state_re_address` predates this spec and renders fine). Verify by inspecting one post-fix run's dashboard view. If a label is desired, follow up with a renderer tweak — not gating.

- **Risk:** The replay fixture commits an agent-emitted turn body verbatim, which is large and changes shape if we re-render the run.
  **Mitigation:** Fixtures are immutable once committed; the failing run on disk is the canonical evidence. The fixture file is a static snapshot for replay testing, not a live run artifact. Trim the file if needed (keep only the ADDRESS block + minimal surrounding sections that `parse_turn_v2` needs).

## 9. CHANGELOG language

For the version's `### Fixed` section:

> ### Fixed
> - **Silent raiser self-ADDRESS drop now emits `ProtocolViolation` (spec 0216):** when an agent ADDRESSes an item it itself raised (protocol-forbidden — only the other agent's items can be addressed), the orchestrator was silently dropping the block at `deep_research.py:379-381` with no event emitted, leaving the misuse invisible to the dashboard and transcript. Now emits `ProtocolViolation(violation_code="raiser_self_address", item_id=…, from_state=…)` while preserving the existing drop semantics. The Ratifying-section instructions for all three interaction phases (0/2/4) gained an explicit "do not use ADDRESS here" clarification.

## Pointers

- The silent drop: [`src/dual_research/orchestrator/deep_research.py:378-381`](src/dual_research/orchestrator/deep_research.py:378).
- Peer violation pattern to mirror: [`deep_research.py:382-400`](src/dual_research/orchestrator/deep_research.py:382) (`terminal_state_re_address`).
- The three Ratifying-section sites: [`prompts.py:1631`](src/dual_research/protocol/prompts.py:1631) (phase 0), [`prompts.py:1849`](src/dual_research/protocol/prompts.py:1849) (phase 2), [`prompts.py:2117`](src/dual_research/protocol/prompts.py:2117) (phase 4).
- Failing run: local `runs/20260521-010637-dvs-backend-language-choice/phase2/round-04-claude.md` (untracked; `runs/` is gitignored).
- Sibling specs in this batch: spec 0214 (hash-gate deadlock), spec 0215 (in-round partner blindness).
