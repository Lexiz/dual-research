---
kind: dev
spec: "0219"
slug: phase4-section-delta-contract-v2
title: "Fix: §3.2 section-delta drafter contract — reviewer/validator collision, heading-mismatch corruption, REPLACE_SECTION budget overrun, mid-phase resume waste"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: ["0218"]
complexity: L
created: 2026-05-26
queued_at: "2026-05-26T17:00:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: "088616eb-610e-4309-ba52-6e26ede558f5"
promoted_from_draft: ""
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §7 Out of scope with a
named follow-up target. -->

# Spec 0219 — Fix: §3.2 section-delta drafter contract — reviewer/validator collision, heading-mismatch corruption, REPLACE_SECTION budget overrun, mid-phase resume waste

> **Type:** bug  |  **Severity:** P0  |  **Affects:** every prod-tier dual-research run whose phase-3 draft enters phase-4 review under the spec-0218 §3.2 section-delta contract. Bug 1 kills the run with exit 52. Bug 2 silently corrupts the published draft (`draft-v2.md` doubled in size from duplicated sections). Together they make spec 0218 a net regression for any non-trivial brief.
> **Bump:** PATCH — bug fix (no contract-additive surface for downstream consumers; reviewer prompt and parser are internal to the orchestrator).
> **Evidence:** run [`runs/20260526-000758-backend-language-choice/`](runs/20260526-000758-backend-language-choice/) — `transcript.jsonl` carries **6** `revised_draft_delta_violation` events, **3** `repair_invoked`, **3** `empty_turn_detected`, terminal `run_failed` at `2026-05-26T07:03Z` with exit 52 after the repair budget exhausted. `phase4/round-02-claude.malformed-1.md` is the smoking gun for bug 2 (drafter emits eight `### REPLACE_SECTION` ops, only two of which match a real draft heading; the other six promote to APPEND and balloon `draft-v2.md` to ~90KB of duplicated content). Prior-session diagnostic transcript at `~/.claude/projects/-Users-alexlisitzky-ClaudeCode-dual-research-workspace-dual-research/088616eb-610e-4309-ba52-6e26ede558f5.jsonl` (240 messages).

---

## 1. Reproduction

**Environment:** dual-research prod tier (`dual-research-alex.fly.dev`), v1.44.24 (spec 0218 merged). Phase-4 review on any brief whose phase-3 draft uses a numbered-section hierarchy that differs from the brief's criteria hierarchy (the smoking-gun brief is `backend-language-choice` — draft headings are `## 1. Summary, ## 2. Findings, ## 3. Disagreements Left Open, ## 4. Open Questions, ## 5. Sources, ## 6. Confidence Ledger` while the brief's criteria are numbered `2.1, 2.2, 2.3, ...`).

**Steps:**

1. Run a prod-tier session with `backend-language-choice` (or equivalent — any brief where draft headings ≠ brief criteria headings).
2. In phase 4 round 2, observe the reviewer (openai) emit a `## Revised draft` block containing the literal string `"(reviewer — no draft edits)"` per the prompt template at [src/dual_research/protocol/prompts.py:2231-2236](src/dual_research/protocol/prompts.py:2231).
3. Observe the drafter (claude) emit `## Revised draft` with `### REPLACE_SECTION 2.1 — Executive Summary…`, `### REPLACE_SECTION 2.2 — Tier 1: Hard Requirements…`, etc. — eight ops, six of which target headings the current draft does NOT contain.
4. Tail the transcript: 6 × `revised_draft_delta_violation` events, 3 × `repair_invoked`, terminal `run_failed` exit 52 after the repair budget exhausts. The on-disk `draft-v2.md` is 90KB with all six mismatched REPLACE_SECTION ops appended verbatim alongside the original sections.

**Expected:**

- Reviewer never trips the §3.2 validator. The validator's "non-empty body inside `## Revised draft`" rule applies to the drafter only.
- Drafter never emits a REPLACE_SECTION targeting a heading absent from the current draft. Heading-mismatch is a hard parse failure, never silently promoted to APPEND.
- Drafter response stays inside the 16K output cap on at least 95% of turns (no `finish_reason="max_tokens"`).
- A resume of a phase-4 run that completed N rounds picks up at round N+1, not round 1.

**Actual:**

- Reviewer trips the validator every round (`revised_draft_body_missing_delta_op` from [src/dual_research/protocol/parse.py:510-512](src/dual_research/protocol/parse.py:510)) because the prompt template tells it to write prose inside `## Revised draft`.
- Drafter's mismatched REPLACE_SECTION ops promote to APPEND at [src/dual_research/protocol/parse.py:615-627](src/dual_research/protocol/parse.py:615) (`sections.append((op.heading, "\n" + op.body + "\n"))` at line 627), with the violation merely logged via `transcript.write("revised_draft_delta_violation", …)` at [src/dual_research/orchestrator/dr_run.py:1404-1410](src/dual_research/orchestrator/dr_run.py:1404). Draft duplicated.
- Drafter phase-4 round 2 (claude): **16,758 output tokens, `finish_reason="max_tokens"`**. Spec 0218 §3.4 raised the cap to 16K under the assumption that REPLACE_SECTION ops would be small; in practice the drafter emits full section bodies and overshoots anyway.
- Each resume restarts phase 4 at round 1 because the round counter from the loop at `dr_run.py` (phase-4 driver) is never persisted; only `state.draft_round` (a version pointer that increments per applied revision) is saved at [src/dual_research/orchestrator/dr_run.py:1402-1403](src/dual_research/orchestrator/dr_run.py:1402). ~$1.40 per resume per agent on prod-tier models.

## 2. Root cause hypothesis

Four coupled defects, all rooted in §3.2 of spec 0218.

### 2.1 Bug 1 (P0) — Reviewer template contradicts the §3.2 validator

The reviewer's output template at [src/dual_research/protocol/prompts.py:2231-2236](src/dual_research/protocol/prompts.py:2231) renders a `## Revised draft` section with the placeholder body `(reviewer — no draft edits)`. The §3.2 validator `_assert_v2_well_formed_turn` at [src/dual_research/orchestrator/repair.py:215-238](src/dual_research/orchestrator/repair.py:215) rejects ANY non-empty body inside `## Revised draft` that does not parse as a delta op — see the role-blind check at [repair.py:232](src/dual_research/orchestrator/repair.py:232) (`if parsed.revised_draft is not None and parsed.revised_draft.strip():`). The reviewer's placeholder is non-empty and not a delta op → instant violation → repair → next attempt same prompt → 2 consecutive failures → `parse_v2_with_repair` raises at [repair.py:281-283](src/dual_research/orchestrator/repair.py:281) → orchestrator exits 52 (`EXIT_PROTOCOL_PARSE_FAILURE` at [src/dual_research/orchestrator/run.py:161](src/dual_research/orchestrator/run.py:161)).

### 2.2 Bug 2 (P0) — Heading-mismatch silently promoted to APPEND, corrupting the draft

`apply_revised_draft_deltas` at [src/dual_research/protocol/parse.py:615-627](src/dual_research/protocol/parse.py:615) handles unmatched REPLACE_SECTION headings by **appending** the body instead of failing. The agent uses brief-criteria headings (`2.1 Executive Summary`, `2.2 Tier 1: Hard Requirements`, …) because the brief is the most recent thing in its context that uses a numbered hierarchy — but the current draft headings are `1. Summary, 2. Findings, 3. Disagreements Left Open, …`. Each mismatch produces a duplicated section in the output. Evidence: [`runs/20260526-000758-backend-language-choice/phase4/round-02-claude.malformed-1.md:147,153,179,257,458,486,500,530`](runs/20260526-000758-backend-language-choice/phase4/round-02-claude.malformed-1.md:147) emits eight REPLACE_SECTION ops — only `1. Summary` and `5. Sources` match draft-v1; the other six promote to APPEND. Resulting `draft-v2.md` is 90KB with duplicated content side-by-side.

### 2.3 Bug 3 (P1) — REPLACE_SECTION ops emit full section bodies, busting the 16K cap

Spec 0218 §3.4 raised `_TURN_MAX_OUTPUT_TOKENS` from 8K to 16K on the premise that "section deltas are smaller than full-draft re-emits." In practice, a single REPLACE_SECTION whose body is a full rewrite of a 2K-token section is 2K output tokens. Six of them is 12K, plus stance + addressing + status overhead → 16-17K → hits the cap. Measured in the smoking-gun run: phase-4 round 2 claude turn = **16,758 output tokens with `finish_reason="max_tokens"`**; repair turn = 15,286 tokens; round 3 = 15,524 tokens spent re-rewriting around bug-2 damage. The §3.2 contract has no per-op size discipline.

### 2.4 Bug 4 (P2) — Phase-4 round counter not checkpointed mid-phase

`state.draft_round` defined at [src/dual_research/persistence/state.py:17](src/dual_research/persistence/state.py:17) and saved via `save_state` at [state.py:82](src/dual_research/persistence/state.py:82) is a **version pointer** that bumps when the drafter emits an accepted revision — NOT the loop's round counter. The phase-4 round loop variable in [dr_run.py](src/dual_research/orchestrator/dr_run.py) is purely local. Mid-phase saves exist at [dr_run.py:750,1126,1162,1341,1403,1514](src/dual_research/orchestrator/dr_run.py:1402) but none persist the loop position. Resumes re-enter phase 4 at round 1 even when prior attempts completed R1+R2+R3 — wasted ~$1.40/resume on prod-tier models. Likely a 2nd-order symptom (becomes much rarer once bugs 1-2 stop forcing resumes) but worth fixing for correctness.

## 3. Fix

Five concrete edits. Order is independent except where noted.

### 3.1 Reviewer template: drop `## Revised draft` entirely

In [src/dual_research/protocol/prompts.py](src/dual_research/protocol/prompts.py): remove the `## Revised draft` section + its `(reviewer — no draft edits)` placeholder from the reviewer's output template at lines 2231-2236 (and from the analogous phase-2 reviewer template if symmetric — check both). The reviewer continues to emit `## Stance`, addressing items, `## New items I'm raising`, `## Status`; the absence of `## Revised draft` is the reviewer's signal that no draft change is being proposed.

### 3.2 §3.2 validator: gate on `is_drafter`

In `_assert_v2_well_formed_turn` at [src/dual_research/orchestrator/repair.py:215-238](src/dual_research/orchestrator/repair.py:215): the check at line 232 (`if parsed.revised_draft is not None and parsed.revised_draft.strip():`) only fires when the turn is the drafter's. Plumb the role flag through (the existing `agent` string is available; add a small signature change to pass `is_drafter: bool` or look up role from the orchestrator's `_drive_interaction_phase` site at [dr_run.py:329](src/dual_research/orchestrator/dr_run.py:329)). Reviewer turns with a missing or empty `## Revised draft` are valid.

### 3.3 Drafter prompt: inject literal current-draft headings

At the drafter's prompt-rendering site in `dr_run.py` (the call path that builds the per-turn user prompt — find it via grep for the drafter-prompt assembly that feeds `_drive_interaction_phase`), insert a new section immediately before the §3.2 delta-op instructions:

```
The current draft's literal section headings (use ONLY these — verbatim):
- ## 1. Summary
- ## 2. Findings
- ## 3. Disagreements Left Open
- ## 4. Open Questions
- ## 5. Sources
- ## 6. Confidence Ledger
```

Render the list programmatically by parsing `## ` lines from `state.current_draft_path` (or whatever holds the on-disk current draft). Each delta op MUST target a heading from this list — taken verbatim, no paraphrase, no renumbering, no substring drift.

### 3.4 Parser: hard-fail on REPLACE_SECTION heading mismatch

In `apply_revised_draft_deltas` at [src/dual_research/protocol/parse.py:615-627](src/dual_research/protocol/parse.py:615): replace the silent-APPEND fallback at line 627 with a hard parse failure (`raise ProtocolParseError("replace_section_unknown_heading", …)`) that flows through the existing repair plumbing. The error message must include the unmatched heading AND the list of valid headings from the current draft. (The repair budget is shared with all other §3.2 violations — one mismatch consumes one repair attempt.)

### 3.5 New op: `EDIT_SECTION <heading>` with `ANCHOR:` / `REPLACE_WITH:` pairs (default surgical op)

Add a fourth delta-op kind to the regex at [src/dual_research/protocol/parse.py:473](src/dual_research/protocol/parse.py:473):

```
### EDIT_SECTION <heading>
ANCHOR: <verbatim substring from the current section, 1-3 lines>
REPLACE_WITH: <new content>
```

Multiple `ANCHOR:` / `REPLACE_WITH:` pairs are allowed within one `EDIT_SECTION` block (apply in document order). `ANCHOR` must match the named section exactly once — `0` matches or `>1` matches raise `edit_section_anchor_ambiguous` (or `…_not_found`) and feed the repair flow. Cost target: a 5-line typo fix becomes ~100 output tokens instead of ~2000 with REPLACE_SECTION.

Doctrine update inline in the drafter prompt (3.3 above): "Default to `EDIT_SECTION`. Use `REPLACE_SECTION` only when rewriting > 50% of a section; include a `reason:` line under the heading explaining why a surgical edit was not enough. `REPLACE_DRAFT_FULL` remains the escape hatch for structural rewrites."

Add a `reason:` field requirement on REPLACE_SECTION (validator-enforced, same parser site).

### 3.6 Checkpoint the phase-4 round counter

Add `phase4_round: int = 0` to `RunState` at [src/dual_research/persistence/state.py:17](src/dual_research/persistence/state.py:17). At the top of the phase-4 round loop in `dr_run.py` (find via grep for `phase4_round` or the loop body that drives `_drive_interaction_phase` per round), set `ctx.state.phase4_round = r` and `save_state(ctx.state)` immediately after both agents complete that round. On resume, the loop seeds from `ctx.state.phase4_round + 1`. Reset to 0 on `phase_entered phase4`.

## 4. User stories & acceptance criteria

Non-UI bug spec. The §5 regression-prevention tests are the load-bearing gate.

## 5. Regression-prevention test

New file `tests/test_spec_0219_section_delta_contract_v2.py` (pure stdlib; pattern after `tests/test_spec_0218_*` if present). Six tests, one per bug + one replay:

- [ ] **`test_reviewer_revised_draft_omitted_passes_validator`** — Bug 1 lock-in. Synthesise a reviewer turn with `## Stance, … ## Status` and NO `## Revised draft` section. Assert `_assert_v2_well_formed_turn(parsed, is_drafter=False)` returns clean. Pre-fix: validator raises. Post-fix: passes.
- [ ] **`test_reviewer_revised_draft_prose_passes_validator`** — Defence-in-depth. A reviewer turn that still has a `## Revised draft` body (in case some prompt path leaks one) must NOT trip the drafter-only gate. Assert validator passes.
- [ ] **`test_drafter_revised_draft_empty_still_fails`** — Bug 1 negative case. A drafter turn whose `## Revised draft` is empty / prose-only must still fail (`revised_draft_body_missing_delta_op`). Confirms the gate doesn't accidentally pass drafter violations.
- [ ] **`test_replace_section_unknown_heading_hard_fails`** — Bug 2 lock-in. Apply `### REPLACE_SECTION 2.1 — Executive Summary` to a draft whose headings are `## 1. Summary, ## 2. Findings`. Pre-fix: silently appends, no exception. Post-fix: raises `replace_section_unknown_heading` with a message listing the valid headings.
- [ ] **`test_edit_section_anchor_roundtrip`** — Bug 3 lock-in for the new op. Parse, apply, and re-serialise an `EDIT_SECTION` block with two `ANCHOR:`/`REPLACE_WITH:` pairs against a known section. Assert the resulting draft has the edits applied verbatim and the rest of the section bytewise-equal.
- [ ] **`test_phase4_round_checkpoint_survives_resume`** — Bug 4 lock-in. Build a `RunState` with `phase4_round=3`, save, reload, assert `phase4_round==3`. Plus an integration-style test that simulates one phase-4 driver iteration writing `phase4_round=r` and a fresh process picking up at `r+1`.
- [ ] **`test_replay_malformed_turn_from_smoking_gun_run`** — End-to-end. Copy `runs/20260526-000758-backend-language-choice/phase4/round-02-claude.malformed-1.md` to `tests/fixtures/spec_0219/round-02-claude.malformed-1.md` as the test fixture. Run `parse_v2_with_repair` against it with a stub current draft whose headings are draft-v1's. Pre-fix: produces a 90KB-style duplicated draft via APPEND promotion. Post-fix: raises `replace_section_unknown_heading` cleanly on the first mismatched op (`### REPLACE_SECTION 2.1 — Executive Summary…` at line 153 of the fixture).

## 6. Blast radius

- **§3.2 callers:** `_drive_interaction_phase` at [src/dual_research/orchestrator/dr_run.py:329](src/dual_research/orchestrator/dr_run.py:329) (validator gating change); `_on_revised_draft` at [src/dual_research/orchestrator/dr_run.py:1370-1415](src/dual_research/orchestrator/dr_run.py:1370) (heading-mismatch now raises instead of logging — the existing `revised_draft_delta_violation` transcript event becomes a parse-failure event; verify nothing downstream depends on it being a non-fatal log).
- **Reviewer-template consumers:** anything that lifted phase-2 or phase-4 reviewer prompt fragments — grep for `Revised draft` callers in [src/dual_research/protocol/prompts.py](src/dual_research/protocol/prompts.py).
- **Parser regex:** [src/dual_research/protocol/parse.py:473](src/dual_research/protocol/parse.py:473) is the central regex; adding `EDIT_SECTION` to the alternation must not break the existing three op-kinds.
- **State migration:** adding `phase4_round` to `RunState` at [src/dual_research/persistence/state.py:17](src/dual_research/persistence/state.py:17) needs a backwards-compatible default (`= 0`) — existing on-disk states deserialise without the field and get 0, which is exactly "start at round 1" behaviour.
- **Dashboard / metrics:** per-turn category-delta aggregates are downstream of the parser; once Bug 2 stops corrupting drafts, those aggregates self-correct (no code change required in the UI items module).
- **UI:** no live-app surface touched. Skipping DS check.

## 7. Out of scope

- **Bumping `_TURN_MAX_OUTPUT_TOKENS` above 16K.** Ruled out in the prior session — same disease, later symptom. Bugs 2-3 attack the root cause (smaller per-op payloads); raising the cap is a band-aid. Re-open as a separate spec only if EDIT_SECTION + REPLACE_SECTION-with-reason still busts 16K on > 5% of phase-4 turns after this spec ships.
- **Multi-turn drafter (one section per turn).** Doubles latency, complicates state, EDIT_SECTION solves the budget problem more cheaply. Deferred to a follow-up spec only if EDIT_SECTION proves insufficient.
- **Tool-use file-handle transport for the draft.** Tool-input JSON counts as output tokens — same problem (already ruled out in spec 0218 §3.2 rationale). Not revisiting.
- **The `empty_turn_detected` events (3 in the smoking-gun run).** Likely a 2nd-order symptom of bugs 1-2 corrupting the conversation state; re-evaluate post-merge. If still present, file a separate spec.
- **Phase-2 reviewer template symmetry.** If phase-2 has the same `## Revised draft` placeholder, fix it in §3.1 here. If it diverges materially from phase-4, file a separate spec for phase-2 specifically.
- **Anchor matcher fuzziness (whitespace-tolerant ANCHOR matching for EDIT_SECTION).** Start strict (byte-exact). Loosen only if real-world failures justify it.

## 8. Risks

- **EDIT_SECTION ambiguity ergonomics.** Strict single-match ANCHOR may trip when an agent picks a too-common anchor string. Mitigation: error message must show the section and instruct the agent to include 1-3 lines of surrounding context. Repair budget absorbs the retry.
- **State-file backwards compatibility.** The `phase4_round` default-0 strategy assumes pydantic / dataclass tolerates absent fields with defaults on load. Verify the load path at [state.py](src/dual_research/persistence/state.py) — if it strict-rejects unknown fields after the addition (new-field migration direction) the test in §5 catches it; if it strict-rejects old states missing the new field (old-state direction) we add an explicit `extra="ignore"` or default handling.
- **Reviewer prompt change cascades.** Removing `## Revised draft` from the reviewer template changes the expected response shape — confirm via grep that no downstream parser branch is keyed on the section's *presence* for reviewer turns. Spec 0218's parser tolerates absence (`parsed.revised_draft is None`).
- **Heading-injection prompt may itself bust the input budget on draft drafts with many sections.** Mitigation: cap at 20 headings (truncate with `… (+N more)`) — but the smoking-gun draft has 6, so this is theoretical.
- **Hard-fail on heading mismatch reduces tolerance** — a single typo now consumes a repair attempt instead of silently mangling the draft. Net positive (loud failure > silent corruption), but watch for repair-budget exhaustion in the first few prod runs post-deploy.
