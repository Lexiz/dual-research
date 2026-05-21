---
spec: 0141
title: Critique aggregation invariants and resolved-view integrity
label: bug
version-bump: PATCH
status: ready
target-version: 1.9.2
created: 2026-05-21
pr: ""
---

# Spec 0141 — Critique aggregation invariants and resolved-view integrity

> Ship bucket: **Orchestrator item-state pipeline integrity — invariant enforcement on
> the raise → transition cycle + UI aggregation that respects it.**
> Depends on: **0140** (Phase 4 deadlock + extractor fix). 0140 lands first; some of
> the empty-turn evidence in the anchor run traces partly to the Phase 4 extractor
> bug 0140 owns, and 0141's verification step assumes the Phase 4 path is already
> well-behaved before measuring orchestrator-wide empty-turn rate.
> Complexity: **M** — two narrow orchestrator fixes (one guard at the AddressBlock
> handler, one minimum-engagement check on parser output), plus an explicit
> verification clause for the resolved-view symptom that should self-resolve once
> the two upstream fixes land. No UI rework, no protocol churn.
> Targeted version bump: **PATCH (1.9.1 → 1.9.2)** — all three findings are
> behaviour bugs against existing invariants; no new surface, no contract change.

---

## 1. Context

Three bugs surfaced in the Notion backlog against anchor run
`20260521-010637-dvs-backend-language-choice` cluster around the same pipeline:
the orchestrator's item-state machine (`apply_turn` → ledger transitions →
`ItemRaised` / `ItemTransitioned` events → UI aggregation in
`ui/items.py`). Each is a different symptom of the same class of leak —
the pipeline does not enforce the invariants its consumers assume.

### B02 — Disagreement raise/close invariant violated (`9 raised, 10 closed`)

The Notion screenshot shows a run-summary count where disagreements closed >
disagreements raised. An item cannot close more times than it was raised, so
the aggregator must be either over-counting closes, under-counting raises, or
counting the same item closed twice.

A direct query on the anchor run's event stream confirms the third
hypothesis. Querying `events` for `kind=in.(item_raised,item_transitioned)` on
`run_id=20260521-010637-dvs-backend-language-choice` yields **15 raises** with
`item_kind="disagreement"` but **16 transitions from a non-terminal to a
terminal state** for D-prefixed item ids (one excess close).

The smoking gun is item `D-plan-g-01`, which carries four transitions in seq
order:

| seq | round | actor  | from → to              |
|-----|-------|--------|------------------------|
| 109 | 2.1   | claude | open → addressed       |
| 121 | 2.2   | openai | addressed → **resolved** |
| 137 | 2.3   | claude | **resolved → addressed** |
| 144 | 2.3   | openai | addressed → **resolved** |

The same item closes twice (seq 121 and seq 144). The `ui/items.py`
`_apply_transition` aggregator increments `closed` on every non-terminal →
terminal transition with no de-duplication, so D-plan-g-01 is counted as two
closes against one raise. Scaled across the run that's the +1 excess.

Quoted payload at seq 137 (the resolved → addressed re-open the orchestrator
should not have allowed):

```json
{"id": "D-plan-g-01", "via": null, "actor": "claude",
 "phase": 2, "round": 3, "reason": "",
 "to_state": "addressed", "from_state": "resolved",
 "evidence_records": []}
```

The Notion screenshot's 9/10 numbers are a particular slice (per-agent or
per-phase) of the same defect; the underlying invariant violation is
unambiguously present in the raw event stream.

The orchestrator's `AddressBlock` handler in
[`deep_research.py:345-401`](src/dual_research/orchestrator/deep_research.py)
has no guard for "the item is already terminal" — it only short-circuits
when `from_state == to_state == addressed` (line 366). A late-arriving
ADDRESS for a `resolved` item drops the item back to `addressed`, which a
subsequent RESOLVE then closes again. This is the protocol-layer leak that
spec 0141 plugs.

### B06 — Empty turns with zero critique movement

The Notion writeup observes that many turns in Phase 0, Phase 2, and Phase 4
record no item raises, no addresses, no resolutions, no withdrawals — "the
models ping-pong without producing anything new." Two hypotheses are
called out: either the model genuinely produced nothing actionable
(prompt-side fix), or the patch extractor dropped the operations between
parse and ledger (capture-path fix).

The anchor run's event stream shows turns where `turn_started` and
`turn_ended` are the only events between turn boundaries — no
`item_raised`, no `item_transitioned`. Concrete example, Phase 4 round 6
(claude):

```
seq 249  turn_started   {"agent":"claude","label":"phase4-r6-claude"}
seq 250  turn_inputs    {…}
seq 251  turn_searches  {…}
seq 252  turn_ended     {"agent":"claude","label":"phase4-r6-claude",
                         "finish_reason":"max_tokens",
                         "output_tokens":8750,
                         "duration_ms":185844}
```

The `finish_reason: max_tokens` is dispositive: the model was actively
producing output but hit the per-turn output ceiling before emitting any
parseable RAISE / ADDRESS / RESOLVE block. The parser ran on the truncated
turn body and found no blocks. The orchestrator accepted the empty turn,
advanced the round counter, and moved on. No alarm, no retry, no signal
that this turn carried zero engagement.

A run-wide tally of empty turns on the anchor run (no item events between
turn_started and turn_ended) shows roughly half of Phase 4's GPT turns and
the tail half of Phase 4's Claude turns are empty — consistent with B10's
"deadlock with very little resolution movement" observation.

The Phase 4 path is owned by spec 0140 (deadlock fix); however the
extractor's silent acceptance of zero-block turns is a generic
orchestrator concern that applies in Phase 0 and Phase 2 too, and that's
0141's piece.

### B10 — Resolved view contradicts the Phase 4 timeline

The Critique panel's "Resolved" group renders items grouped by *resolution
round*, attributing each resolved item to the round in which the
`closed`-state transition was first counted. With the B02 leak in play,
items that closed twice carry the earlier (Phase 1 or early-Phase-2)
attribution while the timeline shows the same item being addressed again
and re-resolved in Phase 2 or Phase 4. The "Resolved" group thus reads as
if almost everything closed early when the timeline shows ongoing
churn — exactly the symptom in B10.

With B02 fixed (resolved → addressed transitions blocked at the
orchestrator) and B06 fixed (empty turns surface as a first-class event the
UI can flag), the resolved-view's source of contradictory data is
removed. B10 is therefore tagged as a **derived symptom** — 0141 verifies
that it self-resolves once the two upstream fixes land, with an explicit
contingency clause if it doesn't (see §5.3).

The relevant resolved-view rendering paths are
[`run-detail.jsx:6080-6118`](src/dual_research/ui/static/run-detail.jsx)
(bucket-by-status logic; `_isResolvedStatus` allow-list) and
[`run-detail.jsx:6538-6580`](src/dual_research/ui/static/run-detail.jsx)
(`CritiquePhaseContent` `Resolved` group render). No JSX changes are
proposed in this spec; the source of the wrong attribution is upstream.

---

## 2. Goals

1. **Enforce the lifecycle invariant `terminal states are absorbing`** in the
   orchestrator's `apply_turn`. Once an item enters `resolved`,
   `acknowledged`, `withdrawn`, or `capped`, no subsequent ADDRESS /
   RESOLVE / WITHDRAW / ACKNOWLEDGE block from either agent may transition
   it out. Such blocks are silently dropped at the orchestrator with a
   `ProtocolViolation` event for the audit trail (mirroring
   `CloseoutViolation`'s precedent).

2. **Surface empty turns as a first-class signal.** After parsing a turn
   that produced **zero ledger-affecting blocks** (no RAISE / ADDRESS /
   RESOLVE / WITHDRAW / ACKNOWLEDGE), emit a new
   `EmptyTurnDetected` event recording the agent, phase, round,
   `finish_reason`, and parser block count. The event is informational;
   it does not abort the turn. The UI can later surface a turn-card
   warning chip from this signal; that JSX work is not in this spec.

3. **Verify B10 self-resolves** by replaying the anchor run after the two
   fixes land, then checking that the Critique panel's Resolved group's
   round attribution matches the `item_transitioned` event sequence's
   final close round for every item. If a discrepancy remains, escalate
   to a follow-up spec — see §5.3.

4. **No false-positive churn on legit empty turns.** Phase 1
   (parallel-draft) and Phase 3 (single-agent drafting) emit by design
   no item events. The `EmptyTurnDetected` guard must be scoped to the
   negotiation / review phases (Phase 0, 2, 4) where item movement is
   expected per round.

---

## 3. Non-goals

- **No change to the Phase 4 deadlock detection or extractor itself.**
  Spec 0140 owns that path. 0141's empty-turn detection is downstream
  of whatever 0140 ships and intentionally does not duplicate its
  Phase 4 retry semantics. The two specs land in order (0140 first).
- **No resolved-view JSX rework.** The `CritiquePhaseContent` Resolved
  group at [`run-detail.jsx:6576`](src/dual_research/ui/static/run-detail.jsx)
  stays. The fix is at the data layer (orchestrator) — once the upstream
  events are clean, the existing UI produces the right view.
- **No UI surface for `ProtocolViolation` or `EmptyTurnDetected` events
  in this spec.** A follow-up may render a small warning chip on
  affected turn cards once the events accumulate enough signal across
  real runs.
- **No retry-on-empty-turn semantics.** An empty turn still ends the
  turn and advances the round counter. Re-prompting is policy work for
  a follow-up that can lean on the new signal.
- **No legacy-protocol coverage.** Pre-spec-0114 transcripts have no
  `item_raised` / `item_transitioned` stream; the legacy shim is
  unaffected.

---

## 4. Current-state audit

### 4.1 — Item lifecycle invariant gap (Goal 1)

| Element                                 | File                                                                | Lines     | Current state |
|-----------------------------------------|---------------------------------------------------------------------|-----------|---------------|
| `AddressBlock` handler                  | [`deep_research.py`](src/dual_research/orchestrator/deep_research.py) | 345–401   | Short-circuits only on `from_state == to_state == addressed` (line 366). Will accept `resolved → addressed`, `withdrawn → addressed`, `acknowledged → addressed`, `capped → addressed` — there is no `is_terminal(ent.current_state)` guard at the top of the branch. The smoking-gun re-open at seq 137 (D-plan-g-01) flows through here. |
| `ResolveBlock` handler                  | [`deep_research.py`](src/dual_research/orchestrator/deep_research.py) | 406–430   | Guarded by `ent.current_state != State.ADDRESSED` (line 410). Correct in isolation, but only because AddressBlock leaks an item back to `addressed`; once that leak is plugged, this guard becomes the actual gate. |
| `WithdrawBlock` handler                 | [`deep_research.py`](src/dual_research/orchestrator/deep_research.py) | 431–455   | Guarded by `is_terminal(ent.current_state)` (line 435). Already correct — model for the AddressBlock fix. |
| `AcknowledgeBlock` handler              | [`deep_research.py`](src/dual_research/orchestrator/deep_research.py) | 456–492   | Guarded by `is_terminal(ent.current_state)` (line 460). Already correct — model for the AddressBlock fix. |
| `closeout.items_blocking_convergence`   | [`closeout.py`](src/dual_research/orchestrator/closeout.py)          | 96–98     | Reads `is_terminal(it.current_state)`. Authoritative definition of "terminal" for convergence; same definition the new guard must use. |
| `is_terminal` predicate                 | [`contract/lifecycle.py`](src/dual_research/contract/lifecycle.py)   | —         | Canonical predicate over the `State` enum (`{RESOLVED, ACKNOWLEDGED, WITHDRAWN, CAPPED}`). |
| UI close-counter                        | [`ui/items.py`](src/dual_research/ui/items.py)                       | 188–208   | `_apply_transition` increments `closed += 1` on every non-terminal → terminal transition without de-duplication. The aggregator trusts the orchestrator to never let an item close twice; today that trust is misplaced. |

The fix lives at the orchestrator: a single `if is_terminal(ent.current_state): continue` clause at the top of the `AddressBlock` branch (after the `ent is None` and `ent.raiser == agent` guards) plugs the leak at its source. The UI aggregator stays as-is — once the orchestrator stops emitting illegal transitions, the aggregator's count is correct.

### 4.2 — Empty-turn detection (Goal 2)

| Element                          | File                                                                | Lines     | Current state |
|----------------------------------|---------------------------------------------------------------------|-----------|---------------|
| `parse_turn_v2`                  | [`protocol/parse.py`](src/dual_research/protocol/parse.py)           | 1198–1338 | Always returns a `ParsedTurnV2`. `parsed.blocks` is a list of `OperationBlock` (RaiseBlock / AddressBlock / ResolveBlock / WithdrawBlock / AcknowledgeBlock). An empty list is a valid return — the validator does not reject it. |
| `apply_turn`                     | [`deep_research.py`](src/dual_research/orchestrator/deep_research.py) | 285–494   | Iterates `parsed.blocks`, emitting `ItemRaised` / `ItemTransitioned` per block. When the list is empty, the loop is a no-op and the function returns `([], [], [])` — silently. No event records "this turn carried zero engagement". |
| `turn_ended` payload             | (event-bus emission, callsite TBD)                                  | —         | Carries `finish_reason`, `output_tokens`, `duration_ms`, `prompt_pieces`. Sufficient for the empty-turn detector to attribute cause (max-tokens vs. genuine empty body). |
| `CloseoutViolation` precedent    | [`events/types.py`](src/dual_research/events/types.py)               | 421–462   | Existing pattern for "orchestrator dropped a block and is recording it for the audit trail". `ProtocolViolation` (B02) and `EmptyTurnDetected` (B06) follow the same shape. |
| `is_closeout_round` plumbing     | [`closeout.py`](src/dual_research/orchestrator/closeout.py)          | 182–252   | Demonstrates how to scope a parser-side check to a subset of rounds. `EmptyTurnDetected` uses the same shape (phase-scoped: 0, 2, 4 only). |

Phase 1 and Phase 3 do not emit item events by design (`ui/aggregator.py:1840-1845` only projects `phase_summary_0/2/4`). The empty-turn detector is therefore gated on `phase in {0, 2, 4}`.

### 4.3 — Resolved-view rendering (Goal 3 verification target)

| Element                                    | File                                                                | Lines       | Current state |
|--------------------------------------------|---------------------------------------------------------------------|-------------|---------------|
| `_isResolvedStatus` allow-list             | [`run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx)       | 6083–6085   | Recognises `resolved`, `answered`, and any `resolved-*` prefix. Bucketing is deterministic given the input item.status. |
| Bucket loop (`pushItem`)                   | [`run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx)       | 6086–6118   | Drops each item into `resolvedItems` / `openNewItems` / `openCarriedItems` / `driftItems` based strictly on `item.status`. No round-attribution math here. |
| `CritiquePhaseContent` Resolved render     | [`run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx)       | 6538–6580   | `renderGroup('Resolved', resolvedItems, …)` (line 6576). The displayed "resolved in r{N}" chip reads from item-level `closedRound` which the upstream item-projection sets from the **first** terminal transition (B02 leak: a re-closed item carries the earlier round). |
| `item.closedRound` projection              | [`ui/items.py`](src/dual_research/ui/items.py) (and aggregator)      | 200–208 + projection paths in `aggregator.py` | Currently sourced from the first non-terminal → terminal transition. Once B02 is fixed, this projection's value matches the final transition automatically (an item can only close once). |

No JSX change is proposed; §5.3 verifies via replay.

### 4.4 — Anchor-run data points

| Datum                                                                      | Value                                                       |
|----------------------------------------------------------------------------|-------------------------------------------------------------|
| Run                                                                        | `20260521-010637-dvs-backend-language-choice`               |
| `item_raised` events (item_kind=disagreement)                              | 15                                                          |
| `item_transitioned` events to a terminal state (D-prefixed ids)            | 16                                                          |
| Re-opened items (`resolved → addressed` transitions on disagreements)      | 1 (D-plan-g-01 at seq 137)                                  |
| `turn_ended` events with no preceding `item_raised`/`item_transitioned`    | ≥ 6 in Phase 4 alone (rounds 6/7/8 both agents)             |
| Example empty-turn `finish_reason`                                         | `max_tokens` at seq 252 (phase4-r6-claude, 8750 output toks) |
| Phase 4 final state                                                        | Deadlock at round 8 (matches B10's "very little resolution") |

---

## 5. Proposed change

### 5.1 — Terminal-state guard on `AddressBlock` (B02 fix)

**Change** ([`deep_research.py:345-369`](src/dual_research/orchestrator/deep_research.py)). Add an `is_terminal` short-circuit at the top of the AddressBlock branch, matching the existing pattern on WithdrawBlock (line 435) and AcknowledgeBlock (line 460):

```diff
             elif isinstance(blk, AddressBlock):
                 ent = self.state.find(blk.item_id)
                 if ent is None:
                     # Address of an unknown item is silently dropped;
                     # the validator already flagged it as malformed.
                     continue
                 if ent.raiser == agent:
                     # An agent cannot ADDRESS their own item; ignore.
                     continue
+                if is_terminal(ent.current_state):
+                    # Spec 0141 — terminal states are absorbing. Once an
+                    # item is resolved / acknowledged / withdrawn /
+                    # capped, a late-arriving ADDRESS must not re-open
+                    # it. Without this guard, the smoking-gun pattern
+                    # observed on anchor run
+                    # 20260521-010637-dvs-backend-language-choice is:
+                    #   r2.2  openai: addressed → RESOLVED
+                    #   r2.3  claude: ADDRESS the (resolved) item →
+                    #         leaks back to ADDRESSED
+                    #   r2.3  openai: addressed → RESOLVED (second close)
+                    # The same item closes twice, producing the
+                    # `closed > raised` invariant violation
+                    # in the run-summary aggregator (B02).
+                    violations.append(ProtocolViolation(
+                        phase=self.phase,
+                        round=round,
+                        agent=agent,
+                        violation_code="terminal_state_re_address",
+                        item_id=ent.id,
+                        from_state=ent.current_state.value,
+                        dropped_block=blk.raw_text[:1000],
+                    ))
+                    continue
                 # Anti-hallucination validation when evidence is required.
                 if ent.evidence_required:
                     …
```

**New event type** ([`events/types.py`](src/dual_research/events/types.py), append after the existing `CloseoutViolation` definition). Same dataclass shape as `CloseoutViolation` plus `item_id` and `from_state`:

```python
@dataclass(frozen=True)
class ProtocolViolation(Event):
    """Spec 0141 — orchestrator dropped a block that would have violated
    the item-state invariant.

    Today this fires for exactly one case: an ADDRESS block targeting
    an item already in a terminal state (resolved / acknowledged /
    withdrawn / capped). Future invariants can use the same event with
    a different `violation_code`.
    """
    kind: str = "protocol_violation"
    phase: int
    round: int
    agent: str
    violation_code: str
    item_id: str
    from_state: str
    dropped_block: str
```

Wire `ProtocolViolation` into the return tuple of `apply_turn` so the orchestrator's caller can publish it on the event bus alongside `CloseoutViolation`s ([`deep_research.py:296`](src/dual_research/orchestrator/deep_research.py) signature update).

### 5.2 — Empty-turn detector (B06 fix)

**New event type** ([`events/types.py`](src/dual_research/events/types.py)):

```python
@dataclass(frozen=True)
class EmptyTurnDetected(Event):
    """Spec 0141 — a negotiate / review turn produced zero
    ledger-affecting blocks (no RAISE / ADDRESS / RESOLVE / WITHDRAW /
    ACKNOWLEDGE) at parse time.

    Fires only in phases that expect item movement (0, 2, 4). Phases 1
    and 3 are by-design item-silent and do not generate this event.

    Informational only — does not abort the turn or advance any retry
    counter. Consumers (the UI surface, post-run analytics) decide what
    to do with it.
    """
    kind: str = "empty_turn_detected"
    phase: int
    round: int
    agent: str
    parser_block_count: int  # always 0 by definition; carried for future
    finish_reason: str | None  # from the turn_ended payload
    output_tokens: int
```

**Detection site** ([`deep_research.py:apply_turn`](src/dual_research/orchestrator/deep_research.py), at the bottom of the method, immediately before the return). Phase-scoped to 0 / 2 / 4:

```python
# Spec 0141 — empty-turn signal. After processing every block in the
# parsed turn, if zero ledger-affecting blocks were observed AND the
# phase expects item movement, emit `EmptyTurnDetected`. Phase 1
# (parallel drafts) and Phase 3 (single-agent drafting) skip this
# check by design — those phases emit no item events.
if self.phase in (0, 2, 4):
    ledger_block_count = sum(
        1 for blk in parsed.blocks
        if isinstance(blk, (RaiseBlock, AddressBlock, ResolveBlock,
                            WithdrawBlock, AcknowledgeBlock))
    )
    if ledger_block_count == 0:
        empty_turn_events.append(EmptyTurnDetected(
            phase=self.phase,
            round=round,
            agent=agent,
            parser_block_count=0,
            finish_reason=getattr(parsed, "_finish_reason", None),
            output_tokens=getattr(parsed, "_output_tokens", 0),
        ))
```

`finish_reason` and `output_tokens` are not currently fields on `ParsedTurnV2`. The orchestrator already has the upstream `turn_ended` payload at the callsite (it builds the event); the cleanest plumbing is to thread `finish_reason` and `output_tokens` into `apply_turn`'s signature as keyword arguments rather than stashing them on `ParsedTurnV2`. Trade-off captured in §10.

The orchestrator's caller (the round driver in `phase0.py` / `phase2.py` / `phase4.py`) publishes any `EmptyTurnDetected` events to the event bus and writes them to the transcript, same path as `CloseoutViolation`.

**Why this is not a retry trigger.** The B06 writeup proposed two fixes — prompt-side (nudge harder) or capture-side (fix the extractor). Empirically the anchor run shows the capture side is already faithful (parser output matches turn body); the empty turns are real, driven by `max_tokens` on long Phase 4 review turns plus model "I have nothing new" outputs. The right intervention is a signal, not a retry; the prompt-side fix is a separate effort that can lean on this signal once it's accumulated across multiple runs.

### 5.3 — B10 verification (resolved-view consistency)

After §5.1 and §5.2 land, run the following verification protocol:

1. **Replay the anchor run** end-to-end against the patched orchestrator using `ledger.replay.replay_items_from_disk` against the on-disk session directory (`runs/20260521-010637-dvs-backend-language-choice/`). Replay reconstructs the `item_raised` / `item_transitioned` stream from the turn bodies under the new orchestrator rules.

2. **Diff the replay's terminal-transition count against the raise count** per item kind. Expected: `terminal_transitions[kind] == raises[kind]` for every kind in `{question, disagreement, issue, comment}`. The pre-fix value is `disagreement: 15 raised / 16 closed`; the post-fix value must read `15 / 15`.

3. **Render the run-detail page** against the replayed event stream and visually confirm:
   - The Critique panel's `Resolved` group attributes each disagreement to its **single** closing round (no item appears in the Phase 1 resolved bucket that the timeline shows being addressed in Phase 4).
   - The Phase 4 timeline's per-round closed-count chips sum to the same total the Resolved group displays for items closed in Phase 4.
   - No item appears in two resolution-round buckets.

4. **If a discrepancy remains** after §5.1 and §5.2 land, treat as a third bug independent of the orchestrator-layer fixes: a follow-up spec audits the `item.closedRound` projection in `ui/aggregator.py` (the `closed_turn_key` / `closedBy` plumbing at lines 1661 and 6657) and adjusts the projection to read from the **last** terminal transition rather than the first. This contingency is captured at line 6657 of run-detail.jsx (the resolution-round derivation already references `closedRound`), but B02's fix removes the root cause; the projection adjustment is only required if B10's symptom persists after replay.

### 5.4 — Cache bust

No client-side change in this spec; no `?v=` bump required. (If the implementer adds a UI surface for `ProtocolViolation` / `EmptyTurnDetected` in a follow-up, that spec will own the cache-bust.)

---

## 6. Out of scope (additions to §3)

- **Phase 4 extractor / deadlock semantics** — owned by spec 0140. 0141 lands second and does not touch the Phase 4 deadlock detector, the Phase 4 review-prompt body, or the editor's removal-tracking. The empty-turn detector in §5.2 fires on Phase 4 turns where they are empty for orchestrator-wide reasons (parser found zero blocks), but it does not duplicate 0140's Phase-4-specific retry semantics.
- **UI surfacing of `ProtocolViolation` / `EmptyTurnDetected`** — no warning chip, no badge, no audit-log surface in this spec. The events land on the bus and in the transcript; a follow-up may surface them. Avoiding the UI scope keeps this a pure data-integrity patch.
- **Resolved-view visual rework** — the `CritiquePhaseContent` Resolved group's layout, sort, grouping, copy is unchanged. §5.3 confirms the symptom self-resolves; if it doesn't, a follow-up tunes the `item.closedRound` projection.
- **Retry-on-empty-turn / nudge-harder prompts** — not in this spec. The fix is a signal, not a behaviour change. Prompt tightening is its own effort and benefits from real `EmptyTurnDetected` data first.
- **Legacy-protocol (pre-0114) coverage** — the invariant fix only applies to runs with v2 item events.
- **Schema migration** — `ProtocolViolation` and `EmptyTurnDetected` are append-only event types; no existing event payload changes shape. No DB migration required.

---

## 7. Test plan

### Unit tests

- [ ] **`apply_turn` blocks `addressed → addressed` no-op** (existing behaviour, regression-pin). The line-366 short-circuit on `from_state == to_state == addressed` stays — no duplicate transition emitted.
- [ ] **`apply_turn` blocks `resolved → addressed`** (new). Construct a ledger with an item in `State.RESOLVED`. Feed an `AddressBlock` for it (from the other agent). Assert:
  - `transition_events` is empty.
  - `violations` contains exactly one `ProtocolViolation` with `violation_code == "terminal_state_re_address"` and `from_state == "resolved"`.
  - The ledger entry's `current_state` is unchanged (still `RESOLVED`).
- [ ] **`apply_turn` blocks `acknowledged → addressed`, `withdrawn → addressed`, `capped → addressed`** (new — same shape, parameterised over the four terminal states).
- [ ] **`apply_turn` allows `open → addressed` and `addressed → resolved`** (existing happy path).
- [ ] **`EmptyTurnDetected` fires in Phase 0/2/4 only** (new). Parameterised: feed a `ParsedTurnV2` with zero ledger-affecting blocks. For `phase in (0, 2, 4)` assert exactly one `EmptyTurnDetected`; for `phase in (1, 3, 5)` (any non-negotiate phase) assert no event.
- [ ] **`EmptyTurnDetected` carries `finish_reason` and `output_tokens`** (new). Verify the field plumbing from the call site.
- [ ] **`EmptyTurnDetected` does not fire when the turn produces any ledger-affecting block** (new). Single-block parse → no event.
- [ ] **`ui/items.py` aggregator counts closes correctly under the post-fix event stream** (regression-pin). Replay an anchor-run-shaped event stream with the duplicate-close removed; assert `disagreements.closed == disagreements.raised` per phase.

### Integration tests

- [ ] **Anchor-run replay invariant**. Replay `20260521-010637-dvs-backend-language-choice` against the patched orchestrator (via `ledger.replay.replay_items_from_disk`). Assert:
  - Per-kind `terminal_transitions == raises` for all four kinds.
  - At least one `ProtocolViolation` event is recorded (the D-plan-g-01 re-open at seq 137 must now be flagged).
  - At least one `EmptyTurnDetected` event is recorded for the Phase 4 r6 claude turn.
- [ ] **Anchor-run rendered Resolved view consistency** (manual). Render the run-detail page against the replayed event stream and inspect the Critique panel's Resolved group. Each disagreement appears in exactly one round bucket; the round it appears in matches the seq of its single terminal transition.

### Regression tests

- [ ] Existing convergence and closeout tests pass unchanged (`should_urge_closeout`, `check_convergence`, `parse_with_closeout` behaviour with `is_closeout_round=True`).
- [ ] No-op address (`addressed → addressed`) still short-circuits silently — no `ProtocolViolation` emitted, no duplicate transition event.

---

## 8. Risks

- **False positives on legit "I'm done" turns.** A Phase 2 agent who has nothing to address (counterpart's items are already addressed, all own items are ratified) may emit a turn body that contains only `STATUS: AGREED` and the agreed-plan section, with zero ledger-affecting blocks. That turn is **correctly** zero-block — it should not be flagged as broken. *Mitigation:* `EmptyTurnDetected` is informational, not an error. The follow-up UI surface should distinguish "zero blocks + AGREED" (healthy) from "zero blocks + non-AGREED + max_tokens" (suspicious). 0141 emits the raw signal and lets the consumer decide.
- **`ProtocolViolation` accumulation hiding real bugs.** If a follow-up violation code is added (`terminal_state_re_resolve`, `addressing_own_item`, etc.) the event stream may carry several per turn. *Mitigation:* the `violation_code` field discriminates; per-code tallies are simple to derive in the aggregator.
- **Replay-vs-live divergence.** The §5.3 verification uses replay, but the production orchestrator path is live. The two should agree post-fix (replay reads the same turn bodies through the same parser and applies the same orchestrator rules), but historically the replay path has lagged spec changes. *Mitigation:* `ledger/replay.py` already imports from `orchestrator.deep_research` for transition logic; the §5.1 / §5.2 fixes flow through automatically. Add a smoke assert in the unit-test layer: same parser input + same orchestrator state → identical event sequence regardless of live vs replay path.
- **`finish_reason` not always set.** Some provider responses lack a `finish_reason`. *Mitigation:* the field is `str | None` on `EmptyTurnDetected`; consumers handle `None` (treat as "unknown — investigate").
- **Phase 4 empty turns that should have been retried.** The fix surfaces a signal but does not retry. A user reading the new event stream will see legitimate "the model gave up" turns and may ask "why didn't we retry?" *Mitigation:* §6 calls this out as out-of-scope; spec 0140 owns Phase 4 retry policy.

**Rollback.** Both changes are purely additive at the orchestrator (one new branch in `AddressBlock`, one new emit at the bottom of `apply_turn`, two new event types). A rollback is a clean revert of the orchestrator hunk and the event-type definitions; no DB migration, no client cache state to clear, no schema dependency. The new event types are append-only in the event bus and ignored by any consumer that doesn't know about them.

---

## 9. Open questions

- **§5.2 `finish_reason` / `output_tokens` plumbing.** Cleanest path is to add the two as keyword arguments to `apply_turn`. Alternative is to stash them on `ParsedTurnV2` (intrusive — `ParsedTurnV2` is parser output, not turn-execution state). Recommend the keyword-argument route; confirm at implementation.
- **§5.1 violation surface — `ProtocolViolation` vs reuse `CloseoutViolation`.** The two have the same shape modulo the new `item_id` and `from_state` fields. Reusing `CloseoutViolation` with new `violation_code` values would avoid a new event class but blurs the audit trail (closeout is a phase-end protocol; this is a generic invariant violation). Recommend the new type. Confirm at implementation.
- **§5.3 B10 contingency timing.** If the replay shows the symptom persists, do we ship 0141 as-is (B02 + B06 fixed, B10 deferred) or hold 0141 until the projection fix is bundled? Recommend ship — B02 / B06 are independent wins and the contingency is well-scoped.
