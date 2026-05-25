---
kind: dev
spec: "0217"
slug: ledger-status-block-authoritative-for-closures
title: "Fix: phase-2/4 ledger reconstructors must honor STATUS.RESOLVED_THIS_TURN / WITHDRAWN_THIS_TURN"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: M
created: 2026-05-25
queued_at: "2026-05-25T00:00:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §7 Out of scope with a
named follow-up target. -->

# Spec 0217 — Fix: phase-2/4 ledger reconstructors must honor STATUS.RESOLVED_THIS_TURN / WITHDRAWN_THIS_TURN

> **Type:** bug  |  **Severity:** P1  |  **Affects:** phase-2 and phase-4 ledger reconstruction — orchestrator convergence gate (`is_plan_agreed` via `ledger_open_count`)
> **Bump:** PATCH — bug fix
> **Evidence:** session `20260525-135006-backend-language-choice`, log at `/tmp/dr-run-backend-language-choice.log`. Phase 2 burned three extra "administrative closeout" rounds because five D-items the agents had resolved were never recognized as closed by the ledger. Wall-clock cost: ~2h vs the 20–30 min the skill advertises for prod tier.

---

## 1. Reproduction

**Environment:** dual-research prod tier, phase-2 convergence loop. Same code path reused for phase-4 review convergence. Reproducible against any session where the agents emit `STATUS.RESOLVED_THIS_TURN: [...]` but close items under the `## Ratifying my own items` / `### RESOLVE D-N` block shape instead of the legacy `## Resolved or non-blocking differences` section.

**Steps:**

1. Run a phase-2 negotiation that surfaces ≥ 1 disagreement (any non-trivial prod-tier run).
2. Observe the round where an agent emits a STATUS block with `RESOLVED_THIS_TURN: [D-plan-c-01, D-plan-c-05]` (and similar in subsequent rounds — see log lines 1459, 1655, 1846) and ratifies via `## Ratifying my own items` rather than `## Resolved or non-blocking differences`.
3. Observe orchestrator runs the next round even though both sides have signaled all D-items closed.

**Expected:** The ledger sees `RESOLVED_THIS_TURN: [D-plan-c-01, D-plan-c-05]` in round R and records those D-items as resolved at round R. `is_plan_agreed(..., ledger_open_count=0)` returns True in round R+1 (or R, depending on the next emit) and phase 2 converges.

**Actual:** The reconstructor in [src/dual_research/ui/disagreements.py](src/dual_research/ui/disagreements.py) only recognizes closures from (a) the `## Resolved or non-blocking differences` section header (regex at [src/dual_research/ledger/build.py:52](src/dual_research/ledger/build.py:52)) or (b) per-item tail `D-N: label — status: resolved` (regex at [src/dual_research/ui/disagreements.py:71](src/dual_research/ui/disagreements.py:71)). It never consults the STATUS block. So `_ingest_disagreements` ([src/dual_research/ledger/build.py:189](src/dual_research/ledger/build.py:189)) inherits a `Disagreement.status="open"`, the ledger's open-count stays > 0, and `is_plan_agreed` rejects AGREED for three further administrative-closeout rounds.

The agent at log line 1472 self-diagnosed this as a "closeout-detection race" — that diagnosis is wrong. The orchestrator ordering at [src/dual_research/orchestrator/phase2.py:278-362](src/dual_research/orchestrator/phase2.py:278) is correct: write turns → parse → rebuild ledger from disk → call `is_plan_agreed(..., ledger_open_count=…)`. The STATUS check is evaluated AFTER the ledger sees the turn that contains the closures. The bug is a protocol/schema mismatch in the reconstructors, not an ordering bug in the orchestrator.

## 2. Root cause hypothesis

The protocol already promises `STATUS.RESOLVED_THIS_TURN: [...]` and `STATUS.WITHDRAWN_THIS_TURN: [...]` as the canonical machine-readable ledger-op channel. The parsing infrastructure already exists:

- Regexes for both tokens land at [src/dual_research/contract/markers.py:124-133](src/dual_research/contract/markers.py:124).
- Per-turn extraction lives at [src/dual_research/protocol/parse.py:1357-1359](src/dual_research/protocol/parse.py:1357) (`_parse_action_array(text, RESOLVED_THIS_TURN_RE)` and `…WITHDRAWN_THIS_TURN_RE`).
- The prompt template documents the contract (see [src/dual_research/protocol/prompts.py:1418-2045](src/dual_research/protocol/prompts.py:1418) for the per-phase STATUS-block schema embedded in the agent prompts).
- The session log itself emits the lists exactly as documented — e.g. `/tmp/dr-run-backend-language-choice.log:550` (`[D-input-c-01, …]`), `:1261`, `:1459`, `:1655`, `:1846`.

But the per-kind reconstructors that feed the ledger never call any of it. [src/dual_research/ui/disagreements.py](src/dual_research/ui/disagreements.py) computes `Disagreement.status` strictly from section-tail scanning of `## Substantive disagreements I'm holding` / `## Resolved or non-blocking differences` / `## Final-surfaced disagreements` plus the open-form / resolved-form / bare-tail regexes at lines 50–90. [src/dual_research/ui/questions.py](src/dual_research/ui/questions.py) similarly relies on positional / verbatim-text matching of answer blocks under `## Answers to {other}'s open questions`. Neither inspects the STATUS block.

Section-tail scanning was an earlier UI-prose convention that the orchestrator accidentally treated as the source of truth. When agents adopted the `## Ratifying my own items` / `### RESOLVE D-N` block shape (a third, undocumented UI-prose variant that the reconstructors also don't parse — see log lines 1497–1517), the resulting closures became silently invisible to the ledger. The agents kept emitting STATUS lists that were technically correct and structurally machine-readable; the ledger just wasn't listening on the right channel.

The structurally correct fix is to make STATUS the authoritative channel and demote section-tail scanning to a legacy fallback — which is what the protocol contract already says it is.

## 3. Fix

Make `STATUS.RESOLVED_THIS_TURN` / `STATUS.WITHDRAWN_THIS_TURN` the authoritative source of ledger-op closures. Apply in the per-kind reconstructors (not in `_ingest_*`) so the upstream `Disagreement` / `Question` models already carry the correct closure info before the ledger reads them.

### 3.1 — Per-turn STATUS pass in `reconstruct` (disagreements)

In [src/dual_research/ui/disagreements.py](src/dual_research/ui/disagreements.py), during the per-round walk, parse the turn's STATUS block via the existing `RESOLVED_THIS_TURN_RE` / `WITHDRAWN_THIS_TURN_RE` regexes from [src/dual_research/contract/markers.py:124-133](src/dual_research/contract/markers.py:124) (or the higher-level `_parse_action_array` helpers already used at [src/dual_research/protocol/parse.py:1357](src/dual_research/protocol/parse.py:1357)). For every `D-N` ID listed in `RESOLVED_THIS_TURN` or `WITHDRAWN_THIS_TURN`, mark the matching Disagreement entry as `resolved` at the round / turn-key of that turn — **regardless of which body section the body uses**, regardless of whether a section-tail closure exists.

### 3.2 — Per-turn STATUS pass in `reconstruct_questions`

Mirror the same in [src/dual_research/ui/questions.py](src/dual_research/ui/questions.py): every `Q-N` ID listed in `RESOLVED_THIS_TURN` / `WITHDRAWN_THIS_TURN` flips the Question's `status` to `answered` at the round / turn-key of that turn, independent of whether the body has a matching answer block. (The positional / verbatim-text linkage stays as a quality signal but no longer gates closure.)

### 3.3 — Section-tail scanning stays as a legacy fallback

Do NOT remove the section-tail / `## Resolved or non-blocking differences` scanning paths. They keep the reconstructor compatible with legacy turn files that pre-date this fix and with any future turns where an agent forgets to populate the STATUS block. On conflict (STATUS says resolved, body section still shows the item as open, or vice versa), **STATUS wins** — it is the documented canonical channel.

### 3.4 — Do NOT parse `### RESOLVE <id>` blocks

Explicitly do NOT introduce a third parsing grammar for the `## Ratifying my own items` / `### RESOLVE D-N` block shape the agents drifted into. STATUS is already the canonical channel; adding a parallel grammar would re-fragment the source of truth and re-introduce the same class of bug the next time an agent invents a fourth UI-prose variant.

### 3.5 — Phase 4 covered automatically

[src/dual_research/ledger/build.py:104-105](src/dual_research/ledger/build.py:104) reuses `_ingest_questions` and `_ingest_disagreements` for phase 4. The reconstructor-level fix therefore covers phase-4 ledger reconstruction with no separate code path.

## 4. User stories & acceptance criteria

The `src/dual_research/ui/` path namespace contains backend Python reconstructor modules (not frontend code), but the validator treats any path under that prefix as UI-touching. Stories and scenarios below describe the reconstructor's observable contract. The §5 regression-prevention tests remain the load-bearing gate.

### 4.1 — User stories

> As a `dev`, I want the ledger to recognize closures via the protocol's documented `STATUS.RESOLVED_THIS_TURN` / `WITHDRAWN_THIS_TURN` channel, so that phase-2 and phase-4 converge in the round the agents actually finish — not after three extra administrative-closeout rounds.

> As a `dev`, I want section-tail / `## Resolved or non-blocking differences` scanning to keep working for legacy turn files, so that older sessions and any future agent drift back to prose-only closures stay parseable.

### 4.2 — Acceptance scenarios (BDD)

> **Scenario 1:** STATUS-driven disagreement closure
> GIVEN a phase-2 round-3 turn file whose body contains `## Substantive disagreements I'm holding` listing `D-1` as open AND a STATUS block with `RESOLVED_THIS_TURN: [D-1]`
> WHEN the disagreement reconstructor runs over the session directory
> THEN the resulting `Disagreement` for `D-1` has `status` set to a resolved variant and `closed_round` equal to 3

> **Scenario 2:** Legacy section-tail fallback still resolves
> GIVEN a phase-2 turn file with no STATUS block (or with `RESOLVED_THIS_TURN: []`) and a `## Resolved or non-blocking differences` section that contains the line `- D-1: ... — status: resolved`
> WHEN the disagreement reconstructor runs over the session directory
> THEN the resulting `Disagreement` for `D-1` has `status` set to a resolved variant (the legacy path still fires)

> **Scenario 3:** STATUS-driven question closure
> GIVEN a phase-2 round-3 turn whose body has no answer block for `Q-c-r1-01` under `## Answers to claude's open questions` AND whose STATUS block contains `RESOLVED_THIS_TURN: [Q-c-r1-01]`
> WHEN the question reconstructor runs over the session directory
> THEN the resulting `Question` for `Q-c-r1-01` has `status` equal to `answered` and `answered_round` equal to 3

## 5. Regression-prevention test

Six unit tests, three per reconstructor (disagreements + questions). All under `tests/test_spec_0217_ledger_status_authoritative.py`. All MUST fail on `main` before the fix and pass after.

- [ ] **Test 5.1 — STATUS-only closure (disagreement).** Turn with `STATUS: RESOLVED_THIS_TURN: [D-1]` but no section-tail closure and no `## Resolved or non-blocking differences` body → ledger marks D-1 resolved at that round. Asserts the new STATUS-pass path fires.
- [ ] **Test 5.2 — Legacy section-tail fallback (disagreement).** Turn with no STATUS block (or `RESOLVED_THIS_TURN: []`) but a `## Resolved or non-blocking differences` section listing `D-1: ... — status: resolved` → ledger still marks D-1 resolved. Asserts the legacy path remains intact.
- [ ] **Test 5.3 — STATUS-wins conflict (disagreement).** Turn where STATUS says `RESOLVED_THIS_TURN: [D-1]` and the body still lists D-1 as open under `## Substantive disagreements I'm holding` → ledger marks D-1 resolved (STATUS wins).
- [ ] **Test 5.4 — STATUS-only closure (question).** Turn with `STATUS: RESOLVED_THIS_TURN: [Q-c-r1-01]` and no matching answer block in `## Answers to <other>'s open questions` → ledger marks Q-c-r1-01 answered at that round.
- [ ] **Test 5.5 — Legacy positional-match fallback (question).** Turn with no STATUS-listed Q-N but a matching positional answer block → ledger still marks the question answered (existing path intact).
- [ ] **Test 5.6 — STATUS-wins conflict (question).** STATUS lists Q-c-r1-01 as resolved but no answer block exists in the answers section → ledger marks Q-c-r1-01 answered (STATUS wins).
- [ ] **Test 5.7 (regression replay) — backend-language-choice round 3.** Replay the round-3-claude.md turn from session `20260525-135006-backend-language-choice` through the reconstructor (fixture copy lives under `tests/fixtures/spec_0217/` so the test is hermetic). Assert all 5 D-items (`D-plan-c-01..05`) and 2 Q-items (`Q-plan-c-01, 02`) close at round 3, **not** round 5. Locks in the headline regression.

## 6. Blast radius

The fix lives entirely in the two per-kind reconstructors ([src/dual_research/ui/disagreements.py](src/dual_research/ui/disagreements.py) and [src/dual_research/ui/questions.py](src/dual_research/ui/questions.py)). Downstream consumers:

- **`_ingest_disagreements` / `_ingest_questions`** at [src/dual_research/ledger/build.py:154-224](src/dual_research/ledger/build.py:154) — read the same `Disagreement.status` / `Question.status` fields they always have; no signature change.
- **Phase-2 orchestrator** at [src/dual_research/orchestrator/phase2.py:278-362](src/dual_research/orchestrator/phase2.py:278) — calls `build_phase_ledger(...).open_count(kind=...)`; sees fewer false-positive open items but no surface change.
- **Phase-4 orchestrator** — same call shape, same automatic fix coverage.
- **UI server / dashboard timeline** — both surfaces consume the same `Disagreement` / `Question` models. STATUS-driven closures will start appearing in the live timeline; this matches what the protocol already promises, so no UI bug.
- **`_apply_claim_escalations`** at [src/dual_research/ledger/build.py:284-365](src/dual_research/ledger/build.py:284) — scans section bodies for `D-N` tokens to escalate claims, **independent** of the closure path. Not touched.

The fix only changes closure recognition, not closure semantics. An item that was already being recognized as closed via section-tail keeps being recognized as closed; new items previously invisible to the ledger now become visible. Strictly monotonic in the "more closures recognized" direction — no item can become "less closed" because of this fix.

## 7. Out of scope

- **Phase-0 hash-drift escape (spec 0032).** May become redundant after this lands, but audit it in a separate spec rather than ripping it out here.
- **Per-phase runtime / round budget guardrail.** Separate spec — would catch this class of stall at the orchestrator level (defense in depth) rather than at the ledger level (root cause). Useful, not blocking.
- **`### RESOLVE D-N` block parsing.** Explicitly NOT added — see §3.4. Deferred to "never" by design; if a future protocol revision genuinely needs a third parsing surface, that's its own spec.
- **Any UI / DS-token / design-system work.** Out of scope.
- **`is_plan_agreed` semantics.** Already correct; not touched.

## 8. Risks

- **Risk: A legacy turn with malformed STATUS lists (e.g. `RESOLVED_THIS_TURN: [D-1` — missing close bracket) crashes the reconstructor.** Mitigation: reuse the existing `_parse_action_array` helper at [src/dual_research/protocol/parse.py:1357](src/dual_research/protocol/parse.py:1357) which is already battle-tested against malformed inputs (it's used in every parsed turn today). Don't write a second parser.
- **Risk: An agent emits `RESOLVED_THIS_TURN: [D-1]` for a D-N that was never raised in this session.** Mitigation: the reconstructor walks all turns in chronological order and only flips status on entries it has already seen `raised`. Spurious IDs are silently dropped (same as today's section-tail path). Add a debug log line for visibility but don't escalate.
- **Risk: A reopen edge case — agent emits `RESOLVED_THIS_TURN: [D-1]` in round 3, then re-raises D-1 in round 5.** The Disagreement model's existing per-round status logic already handles reopens via the chronological walk; the STATUS pass slots into the same per-round loop, so reopen semantics are inherited unchanged. Test 5.3's conflict-handling pattern covers this implicitly. No new edge case introduced.
- **Risk: Performance — adding a per-turn STATUS-block parse to every reconstructor call.** Trivially small (one regex per turn per reconstructor; STATUS block is already parsed elsewhere in the pipeline). No measurable impact.
