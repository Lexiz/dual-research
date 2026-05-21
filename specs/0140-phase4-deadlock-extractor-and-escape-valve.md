---
spec: 0140
title: Phase 4 deadlock — draft extractor body retention + escape-valve breadth for terminal-ledger AGREED
label: bug
version-bump: PATCH
status: ready
target-version: 1.9.1
created: 2026-05-21
pr: ""
---

# Spec 0140 — Phase 4 deadlock: draft extractor + escape-valve breadth

> Ship bucket: **Phase 4 convergence loop fix.**
> Depends on: **0137** (substantive-convergence escape valve — this spec widens its precondition), **0036** (the original sibling-section tolerance in `extract_revised_draft_inclusive` — we extend its allowlist), **0114** (Deep Research protocol — defines the `## Stance / ## Addressing… / …` sentinel set this spec teaches the extractor to recognise).
> Complexity: **S** — one extractor swap in `dr_run.py`, one allowlist extension in `protocol/parse.py`, one widened precondition in `_drive_interaction_phase`. No new event types, no protocol changes.
> Targeted version bump: **PATCH (1.9.0 → 1.9.1)** — bug fix only. No prompt rewrites, no protocol surface changes, no UI consumer changes.

---

## 1. Context

On anchor run `20260521-010637-dvs-backend-language-choice`, Phase 4 burned the full 8-round hard cap and exited with `via_hard_cap=true`, leaving the final draft on disk as a 76-byte stub despite ~$10 of LLM spend. Three causally-linked bugs produced this:

**B12 → B13 → B07.** The draft extractor (`extract_revised_draft` at
[src/dual_research/protocol/parse.py:293-305](src/dual_research/protocol/parse.py))
truncates at the first `##` heading that follows `## Revised draft`.
On `round-07-claude.md` line 39 the drafter opened `## Revised draft`,
then on line 47 wrote `## 1. Executive Summary` (a draft-body
sub-section). The extractor captured only the 7-line preamble. The
on-disk artifact `phase4/draft-v7.md` is exactly **76 bytes** — the
brief title and nothing else. The full 312-line draft sat unused in
`round-07-claude.md`.

That stub draft is what the **next** Phase 4 round handed to the
reviewer agents — see
[src/dual_research/orchestrator/dr_run.py:1198-1199](src/dual_research/orchestrator/dr_run.py)
where `_build` for phase 4 reads `current_draft_path(...).read_text()`
on every round. GPT, asked to review a one-line stub, could not
honestly emit `AGREED` (there was nothing substantive to ratify) and
stayed at `IN_PROGRESS` for the entire phase. Claude, working from
its own internal copy of the full draft, did go AGREED — but the
mixed state never triggered any closeout or escape path.

Spec 0137's escape valve at
[src/dual_research/orchestrator/dr_run.py:339-361](src/dual_research/orchestrator/dr_run.py)
requires `rr.claude_status == "AGREED" and rr.openai_status ==
"AGREED"` simultaneously. The mixed `AGREED / IN_PROGRESS` shape
falls through. So does the closeout-urge predicate
([orchestrator/closeout.py:101-115](src/dual_research/orchestrator/closeout.py)),
which also requires both agents at AGREED. With no closeout and no
escape, the loop ran to `caps_for(4).hard == 8`
([contract/caps.py:32](src/dual_research/contract/caps.py)) and exited
via the hard-cap branch.

### Evidence (anchor run)

Real rows fetched from `events` for run `20260521-010637-dvs-backend-language-choice`:

| seq | ts (UTC) | kind | payload excerpt |
|---:|---|---|---|
| 176 | `01:37:53.939` | `phase_entered` | `{"phase":"phase4"}` |
| 270 | `02:06:45.545` | `phase_converged` | `{"phase":4, "final_round":8, "via_hard_cap":true, "via_artifact_promotion":false, "via_closeout":false, "via_ghost_cap":false}` |
| 271 | `02:06:45.546` | `phase_exited` | `{"phase":"phase4", "duration_ms":1731599}` |
| 272 | `02:06:45.547` | `phase4_complete` | `{"rounds":8, "approved":false, "revisions":7, "final_draft_round":8}` |

Supporting signals:

- The **only** `artifact_canonically_promoted` event in the whole run fired in phase 2 (seq=165, 01:33:10) — phase 4 never reached the escape branch.
- **Zero** `closeout_urged` events in phase 4 (the only one in the run, seq=64, was phase 0). The closeout precondition never matched because openai never went AGREED.
- Rounds 5 and 6 emitted **zero** `item_raised` / `item_transitioned` events between them (seqs 248→252 and 255→259 are pure turn churn) — confirming the ledger went motionless mid-phase.

On-disk artifacts (`runs/20260521-010637-dvs-backend-language-choice/phase4/`):

```
draft-v2.md     76 bytes   draft-v6.md     76 bytes
draft-v3.md     76 bytes   draft-v7.md     76 bytes
draft-v4.md     76 bytes   draft-v8.md    265 bytes
draft-v5.md     76 bytes
round-07-claude.md     29 502 bytes (312 lines)
```

`grep "^## " round-07-claude.md` shows the protocol-sentinel headings (`## Stance`, `## Addressing items raised against me`, `## Ratifying my own items`, `## New items I'm raising`, `## Revised draft`) followed by **draft-body** `##` sub-sections (`## 1. Executive Summary`, `## 2. Version Baseline`, … `## 4. Ranked Candidates`). The extractor stopped at the first body sub-section.

---

## 2. Current-state audit

### 2.1 — Phase 4 draft extraction path

| Element | File | Lines | Current state |
|---|---|---|---|
| `extract_revised_draft` (strict) | [parse.py:293-305](src/dual_research/protocol/parse.py) | 293–305 | Calls `extract_fenced_section(turn_text, "Revised draft")`, which terminates the body at the **first** `^##\s+\S` heading outside a fenced code block. No allowlist, no sibling tolerance. |
| `extract_revised_draft_inclusive` | [parse.py:356-397](src/dual_research/protocol/parse.py) | 356–397 | Sibling-tolerant variant: walks forward absorbing `##` headings unless they hit the `_PROTOCOL_TOP_HEADINGS` allowlist. **Allowlist is the v1 protocol set** (Summary / Status block / Disagreement carryover audit / Evidence checked this round / Substantive disagreements / Resolved or non-blocking / Final-surfaced / Comments on the current draft / AGREED_PLAN / Issue ledger). |
| `_PROTOCOL_TOP_HEADINGS` allowlist | [parse.py:315-326](src/dual_research/protocol/parse.py) | 315–326 | **Missing the Spec 0114 v2 sentinels**: `Stance`, `Addressing items raised against me`, `Ratifying my own items`, `New items I'm raising`, `Phase artifact`, `Status`, `Closeout constraints`. |
| Phase 4 drafter-revision call site | [dr_run.py:264-272](src/dual_research/orchestrator/dr_run.py) | 264–272 | Calls **`extract_revised_draft(result.text)`** (the strict one). The inclusive variant is never invoked in the Deep Research path. |
| Legacy `phase4.py` call sites | [phase4.py:117](src/dual_research/orchestrator/phase4.py), [phase4.py:334](src/dual_research/orchestrator/phase4.py) | — | Use `extract_revised_draft_inclusive`. The legacy path is the only consumer of the inclusive variant today; it is itself shadowed by `run_dr_phase4` for production runs. |
| Drafter prompt | [protocol/prompts.py:721](src/dual_research/protocol/prompts.py), [protocol/prompts.py:2085](src/dual_research/protocol/prompts.py) | 721, 2050–2085 | Instructs the drafter to emit `## Revised draft` with the full updated draft. Does not pin sub-heading depth; agents drift to `## N. Section`. |

### 2.2 — Phase 4 escape valve precondition (Spec 0137)

| Element | File | Lines | Current state |
|---|---|---|---|
| Spec 0137 escape branch | [dr_run.py:339-361](src/dual_research/orchestrator/dr_run.py) | 339–361 | Fires iff `rr.claude_status == "AGREED" AND rr.openai_status == "AGREED" AND not items_blocking_convergence(...)`. Both-AGREED is required. |
| `items_blocking_convergence` | [closeout.py:96-98](src/dual_research/orchestrator/closeout.py) | 96–98 | Returns the non-terminal-state ledger entries. Used by both the escape valve and the closeout-urge predicate. |
| Closeout-urge predicate | [closeout.py:101-115](src/dual_research/orchestrator/closeout.py) | 101–115 | Also requires `claude_status == openai_status == "AGREED"`. The mixed `AGREED / IN_PROGRESS` shape falls through this gate too — no fallback path. |
| Hard-cap branch | [dr_run.py:377-396](src/dual_research/orchestrator/dr_run.py) | 377–396 | The only path that catches "ran the round budget without convergence". Fires `HardCapHit` + auto-caps remaining items. This is what the anchor run hit. |
| `caps_for(4)` | [contract/caps.py:32](src/dual_research/contract/caps.py) | 32 | `PhaseCaps(soft=4, hard=8, closeout_budget=2)` — 8 rounds is the full burn. |

### 2.3 — Phase 4 wrapper

| Element | File | Lines | Current state |
|---|---|---|---|
| `run_dr_phase4` | [dr_run.py:1166-1333](src/dual_research/orchestrator/dr_run.py) | 1166–1333 | Sets up `_on_revised_draft` (the callback that writes `draft-v{N+1}.md` from the extractor output) and `_build` (re-reads `current_draft_path(...)` on every round). Delegates the loop to `_drive_interaction_phase`. |
| `_on_revised_draft` | [dr_run.py:1183-1195](src/dual_research/orchestrator/dr_run.py) | 1183–1195 | Receives `revised_text` from the extractor and writes it directly with `write_atomic`. A stub body is written verbatim — no length / content sanity check. |
| `current_draft_path` read | [dr_run.py:1198-1199](src/dual_research/orchestrator/dr_run.py) | 1198–1199 | `current_path.read_text(...)` happens at the top of every `_build`. The stub becomes the per-round draft input from the round **after** the truncated revision. |

---

## 3. Proposed change

Three surgical edits, no new event types.

### 3.1 — Switch the Phase 4 drafter-revision call to the inclusive extractor

In [src/dual_research/orchestrator/dr_run.py](src/dual_research/orchestrator/dr_run.py):

```python
# Line 85 — imports
from dual_research.protocol import (
    ...
-   extract_revised_draft,
+   extract_revised_draft_inclusive,
    ...
)

# Lines 264-266 — call site inside _drive_interaction_phase
if on_revised_draft is not None and agent_name == ctx.state.drafter:
-   revised = extract_revised_draft(result.text)
+   revised = extract_revised_draft_inclusive(result.text)
    if revised:
        await on_revised_draft(...)
```

The strict variant has no remaining caller in the Deep Research path
after this change. Legacy `phase4.py` already uses the inclusive
variant, so the two paths converge on one extractor.

### 3.2 — Extend `_PROTOCOL_TOP_HEADINGS` with the Spec 0114 sentinels

In [src/dual_research/protocol/parse.py:315-326](src/dual_research/protocol/parse.py):

```python
 _PROTOCOL_TOP_HEADINGS: frozenset[str] = frozenset({
     # ── v1 protocol headings (legacy phase2.py) ──
     "summary",
     "status block",
     "disagreement carryover audit",
     "evidence checked this round",
     "substantive disagreements i'm holding",
     "resolved or non-blocking differences",
     "final-surfaced disagreements",
     "comments on the current draft",
     "agreed_plan",
     "issue ledger (delta + currently open)",
+    # ── Spec 0114 v2 protocol headings (Deep Research) ──
+    "stance",
+    "addressing items raised against me",
+    "ratifying my own items",
+    "new items i'm raising",
+    "phase artifact",
+    "status",
+    "closeout constraints",
 })
```

These exactly mirror the sentinels already defined as parser regexes in
[contract/markers.py:25-50](src/dual_research/contract/markers.py)
(`SECTION_STANCE_RE`, `SECTION_ADDRESSING_RE`, `SECTION_RATIFYING_RE`,
`SECTION_NEW_ITEMS_RE`, `SECTION_PHASE_ARTIFACT_RE`,
`SECTION_STATUS_RE`, `SECTION_CLOSEOUT_CONSTRAINTS_RE`). After this
change, the inclusive extractor terminates the draft body at the next
**protocol** sentinel and absorbs every other `##` sub-heading
(including `## 1. Executive Summary` and friends) into the body.

`## Revised draft` itself is deliberately omitted from the allowlist —
the extractor's start anchor matches it directly via
`_REVISED_DRAFT_HEADING_RE`, and including it in the terminator set
would cause a same-section re-match.

### 3.3 — Widen the escape-valve precondition for terminal-ledger deadlocks

In [src/dual_research/orchestrator/dr_run.py:339-361](src/dual_research/orchestrator/dr_run.py),
extend Spec 0137's branch to also fire when **one** agent is AGREED
and the ledger is terminal:

```python
# ── Spec 0137 (widened by 0140) — substantive-convergence escape ──
# Original 0137 form: both AGREED + terminal ledger but hash drift.
# 0140 widening: one agent AGREED + terminal ledger for the full
# round budget is also a deadlock shape — the other agent is
# blocked on something the protocol cannot surface (typically a
# stub draft from a prior-round extractor truncation).
both_agreed = (
    rr.claude_status == "AGREED" and rr.openai_status == "AGREED"
)
one_agreed = (
    (rr.claude_status == "AGREED") ^ (rr.openai_status == "AGREED")
)
terminal_ledger = not items_blocking_convergence(phase.state.item_views())

if terminal_ledger and (
    both_agreed
    or (one_agreed and round_no >= caps.soft)
):
    converged = True
    via_artifact_promotion = True
    await event_bus.publish(
        ArtifactCanonicallyPromoted(phase=phase_label, round=round_no)
    )
    ctx.transcript.write(
        "artifact_canonically_promoted",
        phase=phase_label,
        round=round_no,
        trigger=("both_agreed" if both_agreed else "one_agreed_terminal"),
    )
    print(
        f"\n[{phase_label}] AGREED (artifact promotion, "
        f"{'both' if both_agreed else 'one'}-agent path). "
        f"Round {round_no}, ledger terminal.",
        flush=True,
    )
    break
```

Key design points:

- The widening is gated on `round_no >= caps.soft` (4 for phase 4) so it does not pre-empt early-round genuine work. With the extractor fix landing in the same release, the dominant deadlock shape becomes "one agent stuck on protocol semantics in late rounds with a terminal ledger" — exactly what the soft-cap gate catches.
- The `trigger` field on the transcript line lets us distinguish the two paths in replay without adding a new event type. The published event remains `ArtifactCanonicallyPromoted` — the UI consumer is unchanged.
- We deliberately do **not** add the third candidate trigger ("both `IN_PROGRESS` + zero ledger movement for K rounds"). It is harder to define safely (movement bookkeeping crosses round boundaries) and the extractor fix removes its real-world driver on the anchor run. If it resurfaces, a follow-up spec can layer it on the same branch.

---

## 4. Out of scope

- **No prompt rewrite.** The drafter is currently instructed to use `## Revised draft` with arbitrary body markup. We do not change the prompt to mandate `###` sub-headings; the extractor fix removes the need.
- **No `PhaseConverged` flag changes.** The existing `via_artifact_promotion` flag from Spec 0137 already covers the widened branch. The UI's "converged via artifact promotion" badge applies as-is.
- **No new event type.** `ArtifactCanonicallyPromoted` is re-used; the `trigger` discriminator lives in the transcript line only.
- **No closeout-predicate widening.** `should_urge_closeout` keeps its both-AGREED rule. Closeout's purpose (urge agents to resolve remaining items) doesn't fit the "one agent is silently stuck on protocol semantics" case the widening targets.
- **No retroactive salvage.** B12's path-3 suggestion ("pull lines 47–312 from `round-07-claude.md` and write a clean `final.md`") is not part of this spec. The anchor run is documented; a one-shot salvage script is a separate concern.
- **No `_strip_horizontal_rules` rework.** The HR-only edge case is unchanged.

---

## 5. Test plan

- [ ] **Unit test** in `tests/protocol/test_parse_revised_draft.py`: a turn with `## Revised draft` followed by `## 1. Executive Summary`, `## 2. Version Baseline`, `## 3. Tier 1 Pass/Fail`, `## 4. Ranked Candidates`, then `## Phase artifact`. Assert `extract_revised_draft_inclusive(...)` returns the body from `## 1. Executive Summary` through the line before `## Phase artifact`, including all four numbered sub-sections.
- [ ] **Unit test**: same turn but the body sub-section is named `## Status` (a protocol sentinel). Assert the extractor terminates at `## Status` — i.e. the allowlist still bites for legitimate sibling protocol sections.
- [ ] **Unit test**: `extract_revised_draft` (strict) is no longer imported by `dr_run.py`. Grep test: `assert "extract_revised_draft(" not in dr_run.py` (only the `_inclusive` form).
- [ ] **Unit test** in `tests/orchestrator/test_dr_run.py`: drive `_drive_interaction_phase` for phase 4 with claude AGREED, openai IN_PROGRESS, all ledger items terminal, at round 5 (>= `caps_for(4).soft`). Assert `result.via_artifact_promotion is True`, `result.via_hard_cap is False`, `result.final_round == 5`. Assert an `ArtifactCanonicallyPromoted` event was published with `phase="phase4"`.
- [ ] **Unit test**: same one-agent-AGREED scenario but at round 3 (< soft cap). Assert the escape valve does **not** fire; the loop continues.
- [ ] **Unit test**: regression on Spec 0137's both-AGREED + terminal-ledger + hash-drift path. Same expected outcome as 0137's test (`via_artifact_promotion=True`); confirm the widening did not break the original branch.
- [ ] **Unit test**: organic convergence (`rr.converged is True`) still wins the branch race — `via_artifact_promotion` stays `False` for the natural-agreement case.
- [ ] **Replay test**: re-parse `runs/20260521-010637-dvs-backend-language-choice/phase4/round-07-claude.md` with the post-fix `extract_revised_draft_inclusive`. Assert the returned body is >= 25 000 characters (full draft body, not the 76-byte preamble) and contains the literal `## 4. Ranked Candidates`.
- [ ] **Replay test**: replay the anchor run's phase 4 ledger shape through `_drive_interaction_phase` with a fake agent harness that emits the recorded statuses round-by-round. Assert the loop terminates at the first round where claude went AGREED with a terminal ledger (round 5 or 6 per the event stream), not at round 8 via hard cap.
- [ ] **Manual smoke**: fire a fresh `/dual-research-run` on a brief whose Phase 3 draft is short enough to trigger drafter `##` sub-section usage in Phase 4. Confirm `phase4/draft-vN.md` files contain full bodies, not stubs, and Phase 4 converges via either organic agreement or the widened escape valve (not hard cap).

---

## 6. Risks

- **False-positive convergence on the widened branch.** One agent at AGREED with a terminal ledger could mask a genuine disagreement the other agent has not yet been able to articulate (e.g. blocked on its own search). Mitigation: the `round_no >= caps.soft` gate ensures the agents have had at least 4 full rounds to surface items into the ledger before the branch arms. The AGREED agent has also implicitly endorsed the artifact; the IN_PROGRESS agent's drift on the artifact body is exactly what 0137 already accepts to drift in the both-AGREED case. The rollback is one boolean flag — flip the `one_agreed` condition off, no schema change.
- **Telemetry interpretation.** Existing `via_artifact_promotion=True` runs in the UI are pure both-AGREED hash-drift cases. After this spec lands, that flag also covers one-agent-AGREED-late-round cases. The transcript-side `trigger` field disambiguates without breaking the event schema; if the UI needs a finer split later, it can read the transcript.
- **Interaction with closeout.** The widened branch sits **before** the `if rr.closeout_event is not None:` block at [dr_run.py:363](src/dual_research/orchestrator/dr_run.py), so it takes precedence over a closeout urge. Since closeout never fires with mixed statuses (its predicate requires both AGREED), there is no real precedence conflict — but worth flagging in case the closeout predicate is widened separately later.
- **Extractor allowlist drift.** If Spec 0114 grows another sentinel section, the `_PROTOCOL_TOP_HEADINGS` set must be updated alongside `contract/markers.py`. Mitigation: add a comment cross-referencing markers.py and a test that asserts the two are kept in sync. Both files already live under the protocol/contract boundary.

---

## 7. Open questions

- None. The fix surfaces, the precondition widening shape, and the gating round all derive directly from the anchor run's event stream and on-disk artifacts.
