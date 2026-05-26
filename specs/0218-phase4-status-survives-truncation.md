---
kind: dev
spec: "0218"
slug: phase4-status-survives-truncation
title: "Fix: phase-4 drafter truncation destroys STATUS — STATUS-first ordering, section-delta drafter contract, and dr_run.py repair-flow wiring"
type: breaking
label: breaking
version_bump: MAJOR
target_version: TBD
status: queued
depends_on: ["0217", "0217.1"]
complexity: L
created: 2026-05-26
queued_at: "2026-05-25T22:33:53Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: "20260525-162909-backend-language-choice"
promoted_from_draft: "001"
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §7 Out of scope with a
named follow-up target. -->

# Spec 0218 — Fix: phase-4 drafter truncation destroys STATUS — STATUS-first ordering, section-delta drafter contract, and dr_run.py repair-flow wiring

> **Type:** bug  |  **Severity:** P1  |  **Affects:** phase-4 convergence on any draft ≥ ~6K tokens. Practically every prod-tier brief that produces a substantive phase-3 draft is in scope. Specs 0217 and 0217.1 (which made STATUS the authoritative ledger-op channel) become structurally unreachable because STATUS is the first thing destroyed when the response truncates.
> **Bump:** PATCH — bug fix
> **Evidence (run `20260525-162909-backend-language-choice`, fetched live from `dual-research-alex.fly.dev` via authenticated API):**
>
> Drafter is `claude` (`claude-sonnet-4-6`); per-round drafter turns from `metrics.json` + `transcript.jsonl`:
>
> | round | finish_reason | output tokens | turn file shape on disk |
> |------:|:---|---:|:---|
> | R1 | `end_turn` | 2,371 | 8,732 chars; clean; sections `Stance, Addressing, Ratifying, New items, Status`; **no `## Revised draft`** |
> | R2 | **`max_tokens`** | 8,454 | 32,528 chars; ends mid-table-cell `\| **Java** \| **`; **no `## Status` heading present at all** |
> | R3 | **`max_tokens`** | 8,586 | 31,509 chars; truncated mid-prose; **no `## Status`** |
> | R4 | **`max_tokens`** | 8,538 | truncated mid-cell `Low–moderate`; **no `## Status`** |
> | R5 | `end_turn` | 8,397 | 30,342 chars; intact; `## Status` lands at the end |
> | R6 | **`max_tokens`** | 8,192 | 30,660 chars; `## Status` heading present but body cut off at `STATUS: IN_PROGRESS\nRAISED_THIS_` mid-line |
>
> `metrics.json.ended_at: null`. Run state at fetch time: `status: "running", phase: 4, round.current: 0`. Phase 4 hit `hard_cap=6` → orchestrator exited 51 (`EXIT_HARD_CAP` per [src/dual_research/orchestrator/run.py:160](src/dual_research/orchestrator/run.py:160)) without writing a final state.
>
> Transcript event counts (also fetched live): **0** `repair_invoked` events, **0** `protocol_parse_failure` events, 3 `empty_turn_detected` events (phase 0 r3 openai; phase 4 r3 claude; phase 4 r4 openai). The truncated turns at R2 and R4-claude landed silently as canonical despite STATUS being absent or partial.

---

## 1. Reproduction

**Environment:** dual-research prod tier (`dual-research-alex.fly.dev`), phase-4 review convergence on any brief whose phase-3 draft exceeds ~6K tokens. The drafter is the agent chosen in phase 2 (claude in the smoking-gun run). The drafter's per-turn output is capped at 8192 tokens by [dr_run.py:104](src/dual_research/orchestrator/dr_run.py:104) (`_TURN_MAX_OUTPUT_TOKENS = 8192`). The Anthropic `claude-sonnet-4-6` default API output cap is 8192 tokens (no `output-128k-2025-02-19` beta header is sent by [src/dual_research/agents/anthropic_agent.py](src/dual_research/agents/anthropic_agent.py)). So the request budget AND the model's effective cap both sit at 8192 — anything that pushes the response past that point silently truncates.

**Steps:**

1. Run a prod-tier dual-research session with the `backend-language-choice` brief (or any brief whose phase-3 draft is ≥ ~6K tokens).
2. In phase 4 round ≥ 2, observe the drafter (claude) emitting `## Revised draft` containing the **full revised draft inline** (~8K-10K tokens of body) — even when there are no substantive reviewer items pointed at the drafter. Stance + addressing + ratifying + new raises + `## Revised draft` + `## Status` together blow past 8192 output tokens.
3. The Anthropic API returns `finish_reason="max_tokens"`. The streamed text on the wire ends wherever the budget ran out — usually mid-table-cell or mid-prose, BEFORE the `## Status` heading.
4. [dr_run.py:309](src/dual_research/orchestrator/dr_run.py:309) writes the truncated text to disk as the canonical turn file. No validator runs. [dr_run.py:328](src/dual_research/orchestrator/dr_run.py:328) calls `parse_turn_v2(result.text)` (tolerant — no raise) and [dr_run.py:356](src/dual_research/orchestrator/dr_run.py:356) calls `phase.apply_turn(...)` on the partial parse. Whatever ledger-affecting blocks made it onto the wire before truncation are applied; whatever STATUS arrays would have followed are simply absent.
5. Loop continues to round 6 (`hard_cap`); exits 51.

**Expected:**

- Phase 4 converges in 3-5 rounds when both agents emit AGREED.
- Every turn on disk has an intact `## Status` block whose `RAISED_THIS_TURN` / `ADDRESSED_THIS_TURN` / `RESOLVED_THIS_TURN` / `ACKNOWLEDGED_THIS_TURN` / `WITHDRAWN_THIS_TURN` arrays are machine-readable by the spec-0217 STATUS-pass at [src/dual_research/ui/disagreements.py:587-610](src/dual_research/ui/disagreements.py:587).
- No truncated turn is ever promoted as canonical. `finish_reason="max_tokens"` triggers the existing repair flow (1 attempt per agent per phase, exit 52 on second consecutive failure — same as any other malformed turn).

**Actual:** Phase 4 loops to `hard_cap=6` without converging. Four of six drafter turns (R2, R3, R4, R6) truncate with `finish_reason="max_tokens"`. All four land on disk as canonical. R2 and R6 have no usable STATUS. Three downstream symptoms cascade from the single root cause:

1. **Phase 4 never converges** — exit 51, ~$X of run cost lost, `metrics.json.ended_at: null`.
2. **R1 items "raised, addressed by other, never resolved"** in the timeline — because claude's R2 ratification STATUS array was destroyed before the `RESOLVED_THIS_TURN: [...]` line printed. Spec 0217's STATUS-pass had nothing to read.
3. **Phase-4 timeline turn-cards for rounds 2-4 show empty `+0 -0` deltas** at [src/dual_research/ui/static/run-detail.jsx:1298-1320](src/dual_research/ui/static/run-detail.jsx:1298) — because the per-turn `categories[cat].raised/.closed` aggregates at [src/dual_research/ui/items.py:149-154](src/dual_research/ui/items.py:149) get fed from the same `parsed.raised_this_turn` / `parsed.resolved_this_turn` arrays that no longer exist. Pure data starvation, not a UI rendering gap (see §7).

## 2. Root cause hypothesis

Three coupled defects, single root cause:

**(i) The `## Status` block lives at the END of every phase-2 / phase-4 prompt template** ([src/dual_research/protocol/prompts.py:1660-1662](src/dual_research/protocol/prompts.py:1660), [:2039-2054](src/dual_research/protocol/prompts.py:2039), [:2142-2143](src/dual_research/protocol/prompts.py:2142)). Every variable-length body section — `## Stance`, `## Addressing items raised against me`, `## Ratifying my own items`, `## New items I'm raising`, `## Revised draft`, `## Phase artifact` — precedes it. When the response truncates, STATUS is the first thing destroyed because the model emits top-down.

**(ii) The drafter re-emits the full revised draft inline on every round it speaks**, regardless of whether it has substantive changes to apply. The prompt template at [src/dual_research/protocol/prompts.py:2131-2132](src/dual_research/protocol/prompts.py:2131) says `## Revised draft  ← drafter only, if any revisions` but the wording "any revisions" is interpreted loosely. Verified from the run: R2, R3, R4, R5, R6 claude turns all contain a full `## Revised draft` section with the complete ~8K-token "Decision: Backend Language for the Modular Monolith" document inline; only R1 (round-1 cannot revise per protocol) omits it. Combined with stance + addressing + ratifying + raises + STATUS, the total response budget needed is ≈ 10-12K tokens. The drafter agent (`claude-sonnet-4-6`) caps at 8192 output tokens by default. Truncation is structurally guaranteed.

**(iii) `dr_run.py` (the active orchestrator path) never validates turn well-formedness and never invokes the repair flow.** The infrastructure exists — `parse_with_repair` at [src/dual_research/orchestrator/repair.py:76-181](src/dual_research/orchestrator/repair.py:76), validator `assert_well_formed_review_turn` at [src/dual_research/protocol/convergence.py:91-115](src/dual_research/protocol/convergence.py:91) which DOES raise `ProtocolParseError("missing STATUS:")` when `p.status is None`, `EXIT_PROTOCOL_PARSE_FAILURE = 52` at [src/dual_research/orchestrator/run.py:161](src/dual_research/orchestrator/run.py:161) — but [dr_run.py:309-365](src/dual_research/orchestrator/dr_run.py:309) writes the raw `result.text` to disk, then calls `parse_turn_v2` (tolerant, no raise) and `phase.apply_turn`, bypassing the validator entirely. The legacy `run_phase4` at [src/dual_research/orchestrator/phase4.py:281-310](src/dual_research/orchestrator/phase4.py:281) DOES call `parse_with_repair`, but [src/dual_research/orchestrator/run.py:36](src/dual_research/orchestrator/run.py:36) aliases `run_dr_phase4` as `run_phase4`, so the legacy path is dead in production. This is a regression: the new DR path forgot to port the validator wiring.

Additionally, `finish_reason in {"max_tokens", "length"}` is captured at [src/dual_research/orchestrator/_call.py:138](src/dual_research/orchestrator/_call.py:138) but is only ever used as **attribution metadata** (emitted on `TurnEnded`, threaded into `EmptyTurnDetected` at [src/dual_research/orchestrator/deep_research.py:584-592](src/dual_research/orchestrator/deep_research.py:584)) — never as a parse-failure signal. A truncated turn whose body happens to contain enough RAISE/ADDRESS/RESOLVE blocks to not trip the empty-turn detector silently lands as canonical even though STATUS is gone.

Spec 0217 and 0217.1 promised STATUS as the authoritative ledger-op channel. **They assume STATUS exists.** This spec is the structural follow-up: make STATUS structurally guaranteed to survive even under adversarial drafter response sizes, and ensure no truncated turn is ever written to disk as canonical.

## 3. Fix

Four coordinated changes, one PR. Each is load-bearing on its own; together they make the failure mode structurally impossible.

### 3.1 — STATUS-first ordering in every negotiation/review prompt

Move the `## Status` block from the END of the prompt template to **immediately after `## Stance`**, before all variable-length body sections. The rationale: STATUS is the smallest section in the response (≤ 200 tokens for the action arrays + counters), it carries the only metadata channel the orchestrator depends on for convergence, and it is the only section whose presence is non-negotiable for forward progress. The variable-length sections (`Addressing`, `Ratifying`, `New items`, `Revised draft`, `Phase artifact`) are precisely the sections that should be allowed to truncate — they carry prose redundancy that's largely recoverable from priors, whereas STATUS carries irrecoverable per-turn ledger-op state.

Sites to update:

- [src/dual_research/protocol/prompts.py:1567-1578](src/dual_research/protocol/prompts.py:1567) — phase 0 round 1 (`preflight_prompt_v2`).
- [src/dual_research/protocol/prompts.py:1620-1662](src/dual_research/protocol/prompts.py:1620) — phase 0 round N (`input_negotiation_prompt_v2`).
- [src/dual_research/protocol/prompts.py:2021-2054](src/dual_research/protocol/prompts.py:2021) — phase 4 round 1 (`review_round1_prompt_v2`).
- [src/dual_research/protocol/prompts.py:2111-2144](src/dual_research/protocol/prompts.py:2111) — phase 4 round N (`review_round_n_prompt_v2`). The DRAFTER's `## Revised draft` section moves to AFTER `## Status`, so even a max-sized revised-draft body cannot bury STATUS.

The shared `_status_footer_for_phase` helper at [src/dual_research/protocol/prompts.py:1408-1438](src/dual_research/protocol/prompts.py:1408) is just the string template; it doesn't move. The call-sites that splice it into the prompt are what moves it earlier.

**Parser: no change required.** [src/dual_research/contract/markers.py:42](src/dual_research/contract/markers.py:42) defines `SECTION_STATUS_RE` as `re.compile(r"^##\s+Status\b", re.MULTILINE | re.IGNORECASE)` — position-agnostic, matches anywhere in the body. `SECTION_PHASE_ARTIFACT_RE`, `SECTION_ADDRESSING_RE`, `SECTION_RATIFYING_RE`, etc. are all line-anchored regexes, not order-dependent. `extract_revised_draft_inclusive` at [src/dual_research/protocol/parse.py:373-413](src/dual_research/protocol/parse.py:373) walks forward from `## Revised draft` and absorbs sibling sub-sections until it hits a protocol-allowlisted heading; `status` is already in the allowlist at [parse.py:341](src/dual_research/protocol/parse.py:341), so `## Status` correctly ends the revised-draft body when STATUS precedes it. The "Revised draft after Status" order has already been parser-supported since spec 0036's tolerance work.

Update the prompt callouts immediately above STATUS to explain the new ordering, so the agents understand the structural intent: "The STATUS block lives near the top of your turn so that it always lands even if your revised draft is long. Treat it as a hard pre-commit: populate the action arrays in §3.2 with the canonical IDs for everything you're about to do in the body below."

### 3.2 — Drafter contract: section-delta `## Revised draft`

The drafter's `## Revised draft` body becomes a sequence of operation blocks, not a full inline re-emit:

```
## Revised draft

### REPLACE_SECTION <heading>
<new section body>

### APPEND_SECTION <heading>
<new section body>

### DELETE_SECTION <heading>

### REPLACE_DRAFT_FULL    ← escape hatch for major rewrites; full new draft body follows
```

Semantics:

- `### REPLACE_SECTION <heading>`: replace the body of the matching `## <heading>` section in `draft-vN.md`. Heading match is case-insensitive trim-equal. If no matching heading exists, the orchestrator promotes to `APPEND_SECTION` and logs a protocol-violation event.
- `### APPEND_SECTION <heading>`: append a new `## <heading>` section at the end of the draft.
- `### DELETE_SECTION <heading>`: remove the matching section.
- `### REPLACE_DRAFT_FULL`: full draft re-emit follows. Used only for structural rewrites that touch >half the sections. The orchestrator does not enforce a hard threshold; the prompt asks the drafter to honor the spirit.
- Two `### REPLACE_SECTION <same-h2>` blocks in one turn: apply in document order, last-writer-wins, log a protocol-violation event.

Parser surface: **add a new sibling function** `extract_revised_draft_deltas` alongside the existing `extract_revised_draft_inclusive` at [src/dual_research/protocol/parse.py:373-413](src/dual_research/protocol/parse.py:373). Returns a discriminated-union `RevisedDraftFull(content=str) | RevisedDraftDeltas(ops=list[DraftDeltaOp])` where `DraftDeltaOp` is a typed dataclass for each operation kind. Keeps the existing function unchanged for any legacy callers and gives the new contract its own typed return surface. The `on_revised_draft` callback wiring at [src/dual_research/orchestrator/dr_run.py:319-326](src/dual_research/orchestrator/dr_run.py:319) switches to the new function and dispatches on the union variant (full → write_atomic prior shape; deltas → apply ops to prior `draft-vN.md` on disk to produce `draft-v(N+1).md`).

**Two hard rules in the prompt:**

1. **The drafter MUST omit `## Revised draft` entirely on rounds where there are no substantive changes to apply.** The current prompt says "drafter only, if any revisions" ([prompts.py:2131-2132](src/dual_research/protocol/prompts.py:2131)) — tighten to "OMIT this section entirely unless the prior round contained substantive reviewer feedback you intend to address by editing the draft. Re-emitting an unchanged draft is a protocol violation."
2. **`### REPLACE_DRAFT_FULL` is the only path that allows a full draft re-emit.** Use it only when a structural rewrite touches more than half the sections; otherwise enumerate per-section operations. Truncation on `REPLACE_DRAFT_FULL` falls back to §3.3 (max_tokens → parse error → repair).

**Why option (a) section-deltas over option (b) `write_revision` tool call:** the user-proposed alternative — a `write_revision(draft=...)` tool call — does not solve the budget problem. Tool-use input JSON counts as **output tokens** of the assistant turn in both Anthropic and OpenAI APIs. Moving the 8K of draft bytes from inside `## Revised draft` text to inside a `tool_use` block's `input` JSON yields the same R6 truncation. Even a finer-grained tool like `replace_section(name, body)` called N times would emit N×body_size output tokens — same total. Real decoupling would require a filesystem write-ack transport where the tool input is just a small path and the draft bytes ride a separate transport that doesn't count against output tokens; that plumbing does not exist in either [src/dual_research/agents/anthropic_agent.py](src/dual_research/agents/anthropic_agent.py) or [src/dual_research/agents/openai_agent.py](src/dual_research/agents/openai_agent.py), and adding it is a multi-week protocol-layer rewrite. Section-deltas keep the markdown protocol surface, shrink the actual byte count of the response (which is what the budget constrains), and require only prompt-template + extractor changes.

### 3.3 — Wire `parse_with_repair` into `dr_run.py`; treat `max_tokens` / `length` as `ProtocolParseError`

Two changes at the same splice point in [src/dual_research/orchestrator/dr_run.py:308-365](src/dual_research/orchestrator/dr_run.py:308):

**(a) Insert validator + repair between `run_one_call` and `apply_turn`.** Today the flow is `run_one_call → write_atomic(canonical_path, text) → extract_revised_draft → parse_turn_v2 → apply_turn`. Change to: `run_one_call → write_atomic(audit_path, text) → parse_with_repair(validator=assert_well_formed_review_turn) → write_atomic(canonical_path, repaired_text) → extract_revised_draft → parse_turn_v2 → apply_turn`. The validator chain matches the legacy `run_phase4` path at [src/dual_research/orchestrator/phase4.py:281-310](src/dual_research/orchestrator/phase4.py:281), which has been correct since spec 0036. Reuse `RepairTracker` per-phase (one-shot budget per agent, exit 52 on second consecutive failure) per [src/dual_research/orchestrator/repair.py:42-68](src/dual_research/orchestrator/repair.py:42).

**(b) `finish_reason in {"max_tokens", "length"}` is a synthetic parse failure.** At [src/dual_research/orchestrator/_call.py:138](src/dual_research/orchestrator/_call.py:138) (or, cleaner, inside `parse_with_repair` as a pre-check via a new optional `finish_reason: str | None` param), if the upstream `AgentResult.extras["stop_reason"]` or `["finish_reason"]` is `"max_tokens"` or `"length"`, raise `ProtocolParseError(agent, ["truncated_by_max_tokens"])` regardless of whether the body happens to parse syntactically. Rationale: a truncated turn whose body coincidentally has STATUS-shaped trailing bytes is still untrustworthy — we don't know what got cut. Route through the same repair → exit-52 escalation as a malformed turn. The truncated text is saved as `<canonical_path>.malformed-<n>.md` for audit (same convention as [src/dual_research/orchestrator/repair.py:122-125](src/dual_research/orchestrator/repair.py:122)); the canonical path is only written after the repaired turn parses cleanly.

With §3.1 + §3.2 in place, the repair retry has a real chance of succeeding (response shape is bounded by the new drafter contract — total response shrinks from ≈ 10-12K tokens to ≈ 2-4K tokens on average). Without §3.1 + §3.2, the repair retry would just truncate again — but §3.3 still earns its keep on its own by guaranteeing **no truncated turn ever lands as canonical**, which is the only thing standing between "broken run, recoverable" and "broken run, corrupted ledger state."

### 3.4 — Bump `_TURN_MAX_OUTPUT_TOKENS` for phase-4 turns to 16384 + add Anthropic `output-128k-2025-02-19` beta header

At [src/dual_research/orchestrator/dr_run.py:104](src/dual_research/orchestrator/dr_run.py:104), `_TURN_MAX_OUTPUT_TOKENS = 8192` is the request budget for all phase-0/2/4 turns. With section-deltas in place, this is overkill for typical rounds (response is ~3K tokens) — but it's defense-in-depth for rounds that legitimately use `### REPLACE_DRAFT_FULL`, and for the `### REPLACE_SECTION` case where a single replaced section is itself long (e.g. a full findings rewrite). The Anthropic `claude-sonnet-4-6` API caps at 8192 output tokens by default; to actually request 16384 we additionally need the `output-128k-2025-02-19` beta header in [src/dual_research/agents/anthropic_agent.py:60-66](src/dual_research/agents/anthropic_agent.py:60) (parallel to the existing `EXTENDED_CACHE_TTL_BETA` plumbing at [agents/anthropic_agent.py:48-66](src/dual_research/agents/anthropic_agent.py:48)). Add the beta header to the Anthropic `messages.stream(**kwargs)` call in the same commit — same comma-joined `anthropic-beta` header pattern, no new code path. OpenAI has no analogous beta — the `gpt-5.5-2026-04-23` model's default `max_completion_tokens` covers it.

This change is the smallest of the four but is the only one whose absence reduces §3.2's section-delta contract to a single-section-at-a-time discipline. With §3.4, a drafter can emit one large `### REPLACE_SECTION` (e.g. a rewritten `## 4. Final Ranking` table) without re-tripping the budget.

### 3.5 — What we deliberately are NOT doing

- **Not implementing the `write_revision` tool call (option b).** See §3.2 rationale. Filed for never; if a future requirement makes the markdown surface untenable, that's a separate filesystem-transport spec.
- **Not parsing legacy full-draft `## Revised draft` bodies as an implicit `REPLACE_DRAFT_FULL`.** Backward compatibility is unnecessary — this is a `bug` spec fixing a regression in protocol shape; no in-flight session straddles the version. The parser raises `ProtocolParseError("revised_draft_body_missing_delta_op")` when `## Revised draft` body is non-empty but contains no `### REPLACE_*` / `### APPEND_*` / `### DELETE_*` operation block (other than the `### REPLACE_DRAFT_FULL` escape).
- **Not adding a per-phase `REPLACE_DRAFT_FULL` budget.** If a future agent abuses the escape hatch, a follow-up spec can add a hard cap (e.g. max 1 `REPLACE_DRAFT_FULL` per phase). Out of scope for the initial fix.
- **Not changing the OpenAI agent path.** OpenAI's `length` finish_reason is symmetric and handled by §3.3 (`finish_reason in {"max_tokens", "length"}` covers both providers). No separate OpenAI work.

## 4. User stories & acceptance criteria

The spec touches only backend code (`src/dual_research/protocol/`, `src/dual_research/orchestrator/`, `src/dual_research/agents/`). The body cites `src/dual_research/ui/...` paths for context (downstream reconstructor + chip-render are NOT modified — see §6 / §7), and the validator treats any spec citing those paths as UI-touching. The §5 regression-prevention tests remain the load-bearing gate; the scenarios below describe the observable contract.

### 4.1 — User stories

> As a `dev`, I want phase 4 to converge in 3-5 rounds on long drafts (≥ 6K tokens), so that prod-tier runs don't hit `hard_cap=6` and exit 51 on briefs that produce substantive phase-3 output.

> As a `dev`, I want the `## Status` block to land intact on every drafter turn regardless of how much body content precedes or follows it, so that spec 0217 / 0217.1's STATUS-pass actually has data to read and phase-4 timeline turn-cards populate their per-round category deltas.

> As a `dev`, I want a truncated turn (`finish_reason="max_tokens"` or `"length"`) to never be written to disk as a canonical turn, so that the ledger never ingests partial state and downstream reconstructors never silently lose closures.

> As a `dev`, I want the drafter to emit only the diff between draft versions (section-deltas), so that the response budget scales with the size of the change, not with the size of the document.

### 4.2 — Acceptance scenarios (BDD)

> **Scenario 1:** STATUS-first rendering in phase-4 round-N prompt
> GIVEN a rendered phase-4 round-N prompt produced by `review_round_n_prompt_v2` at [src/dual_research/protocol/prompts.py:2057](src/dual_research/protocol/prompts.py:2057)
> WHEN the rendered string is scanned for the character index of each top-level `## …` heading
> THEN the index of `## Status` is strictly less than the index of `## Revised draft`, `## Addressing items raised against me`, `## Ratifying my own items`, `## New items I'm raising`, and `## Phase artifact`

> **Scenario 2:** truncated drafter turn never lands as canonical
> GIVEN a phase-4 round-N drafter call whose agent returns text ending mid-section with `extras["stop_reason"]="max_tokens"`
> WHEN the `dr_run.py` per-turn driver processes the result via the new `parse_with_repair` wiring (§3.3)
> THEN the canonical turn file on disk contains the REPAIRED text (from the one-shot repair retry) — never the truncated text — and a sibling `<canonical_path>.malformed-1.md` audit file holds the discarded truncated bytes

> **Scenario 3:** section-delta `## Revised draft` produces a correct `draft-v(N+1).md`
> GIVEN a `draft-v1.md` with three sections (`## 1. Summary`, `## 2. Findings`, `## 3. Sources`) and a drafter turn whose `## Revised draft` contains `### REPLACE_SECTION 2. Findings`, `### APPEND_SECTION 4. Confidence ledger`, and `### DELETE_SECTION 3. Sources`
> WHEN the orchestrator applies the deltas via the new `extract_revised_draft_deltas` discriminated-union dispatch
> THEN the resulting `draft-v2.md` has `## 1. Summary` unchanged, `## 2. Findings` body replaced, no `## 3. Sources`, `## 4. Confidence ledger` appended at the end

## 5. Regression-prevention tests

Six unit tests under `tests/test_spec_0218_phase4_status_survives_truncation.py`. All MUST fail on `main` before the fix and pass after.

- [ ] **Test 5.1 — STATUS-first ordering in rendered phase-4 round-N prompt.** Render the phase-4 round-N prompt via the public helper at [src/dual_research/protocol/prompts.py:2057](src/dual_research/protocol/prompts.py:2057). Assert that the `## Status` heading appears at a character index BEFORE `## Revised draft`, `## Addressing items raised against me`, `## Ratifying my own items`, `## New items I'm raising`, and `## Phase artifact`. Mirror the test for phase-2 round-N, phase-4 round-1, phase-0 round-1, phase-0 round-N. Locks in §3.1 ordering across all five sites.

- [ ] **Test 5.2 — Section-delta application produces correct draft-v(N+1).md.** Construct an in-memory `draft-v1.md` with three sections (`## 1. Summary`, `## 2. Findings`, `## 3. Sources`). Construct a turn whose `## Revised draft` body contains one `### REPLACE_SECTION 2. Findings` (with new body), one `### APPEND_SECTION 4. Confidence ledger` (with new body), and one `### DELETE_SECTION 3. Sources`. Run the orchestrator's revised-draft application step. Assert the resulting `draft-v2.md` body has `## 1. Summary` unchanged, `## 2. Findings` replaced, no `## 3. Sources`, `## 4. Confidence ledger` appended. Locks in §3.2 application semantics.

- [ ] **Test 5.3 — Drafter `## Revised draft` with prose body (no delta blocks) raises `ProtocolParseError`.** Construct a turn whose `## Revised draft` body is plain prose (legacy full-draft shape, no `### REPLACE_*` / `### APPEND_*` / `### DELETE_*` / `### REPLACE_DRAFT_FULL` block). Run through `parse_with_repair`. Assert `ProtocolParseError` with errors containing `"revised_draft_body_missing_delta_op"`. Locks in §3.2 backward-incompatibility.

- [ ] **Test 5.4 — `finish_reason="max_tokens"` raises `ProtocolParseError` even on syntactically-parseable body.** Construct an `AgentResult` whose `text` looks like a valid turn (has `## Status` with all arrays intact) but whose `extras["stop_reason"] = "max_tokens"`. Run through `parse_with_repair`. Assert `ProtocolParseError` with errors `["truncated_by_max_tokens"]`. Mirror with `finish_reason="length"` (OpenAI). Locks in §3.3 escalation.

- [ ] **Test 5.5 — Truncated turn does NOT land as canonical; repaired turn does.** Mock the agent to return on first call: text ending mid-section + `extras["stop_reason"]="max_tokens"`. On the repair call (second invocation), return a clean, valid turn + `stop_reason="end_turn"`. Run through `dr_run.py`'s phase-4 round-N driver. Assert: (i) the canonical turn file on disk contains the REPAIRED text, not the truncated text; (ii) a `<turn>.malformed-1.md` file exists with the truncated text; (iii) `RepairTracker.budget["claude"] == 0` after the repair; (iv) one `RepairInvoked` event was published. Locks in §3.3 wire-up.

- [ ] **Test 5.6 (regression replay) — backend-language-choice R2 truncated turn.** Replay the captured R2-claude.md turn from `runs/20260525-162909-backend-language-choice/phase4/round-02-claude.md` (fixture copy lives under `tests/fixtures/spec_0218/` — 32,528 chars, ends mid-table-cell `| **Java** | **`, no STATUS). Feed through the dr_run.py validator chain. Assert `ProtocolParseError("missing STATUS:")` or `["truncated_by_max_tokens"]` is raised (whichever path fires first; both are valid). Assert the canonical write does not happen. Locks in the headline regression.

## 6. Blast radius

- **Phase 0 / phase 2 / phase 4 prompt templates** ([src/dual_research/protocol/prompts.py](src/dual_research/protocol/prompts.py)) — STATUS ordering reshuffled, `## Revised draft` contract changed. Agents read top-down; STATUS earlier is strictly easier to comply with than STATUS at the end. The section-delta contract is a behavioral change but the prompt restates it explicitly and the new parser rejects non-compliance with a clear error, which routes to repair.
- **`extract_revised_draft_deltas` (new sibling at [src/dual_research/protocol/parse.py:413](src/dual_research/protocol/parse.py:413))** — recognizes `### REPLACE_SECTION` / `### APPEND_SECTION` / `### DELETE_SECTION` / `### REPLACE_DRAFT_FULL` sub-headings as delta operations and returns a typed `RevisedDraftFull | RevisedDraftDeltas` discriminated union. The existing `extract_revised_draft_inclusive` is unchanged.
- **`dr_run.py:308-365`** — the per-turn drive sequence picks up validator + repair. New code lives between `run_one_call` and `write_atomic(canonical_path, ...)`. No other call-site changes.
- **`run_one_call`** at [src/dual_research/orchestrator/_call.py:138](src/dual_research/orchestrator/_call.py:138) — `finish_reason` plumbing untouched at the event-emission layer. The new max_tokens check lives at the call-site (inside or just before `parse_with_repair`) so the event bus continues to see `finish_reason` regardless of repair outcome.
- **`parse_with_repair`** at [src/dual_research/orchestrator/repair.py:76-181](src/dual_research/orchestrator/repair.py:76) — gains an optional `finish_reason: str | None` param. When `finish_reason in {"max_tokens", "length"}`, prepend a synthetic `["truncated_by_max_tokens"]` error to the validator's error list before the budget check. Existing repair-budget + consecutive-failure semantics inherited unchanged. Exit 52 on second consecutive failure unchanged.
- **Ledger reconstructors** ([src/dual_research/ui/disagreements.py](src/dual_research/ui/disagreements.py), [src/dual_research/ui/questions.py](src/dual_research/ui/questions.py), [src/dual_research/ui/items.py](src/dual_research/ui/items.py)) — **UNTOUCHED**. Their spec-0217 STATUS-pass already does the right thing once STATUS is present.
- **UI** — **UNTOUCHED**. Phase-4 turn-card chips at [src/dual_research/ui/static/run-detail.jsx:1298-1320](src/dual_research/ui/static/run-detail.jsx:1298) read `stats.categories[cat].raised/.closed`, populated by `_register_item` at [src/dual_research/ui/items.py:149-154](src/dual_research/ui/items.py:149). Once STATUS arrays survive, the existing chip-render lights up automatically. See §7.
- **Anthropic adapter** at [src/dual_research/agents/anthropic_agent.py:60-66](src/dual_research/agents/anthropic_agent.py:60) — gains the `output-128k-2025-02-19` beta header alongside the existing `EXTENDED_CACHE_TTL_BETA`. Same comma-joined `anthropic-beta` header pattern, no new code path.
- **Legacy `run_phase4` at [src/dual_research/orchestrator/phase4.py:55-449](src/dual_research/orchestrator/phase4.py:55)** — still aliased away as dead code by [run.py:36](src/dual_research/orchestrator/run.py:36); no functional change. This spec does not delete it (separate refactoring cleanup).

The fix is monotonic in two directions: (i) more turns land with valid STATUS → more closures recognized → fewer false-positive open items; (ii) no turn lands as canonical when truncated → no corrupted ledger state. No path becomes worse.

## 7. Out of scope

- **Phase-4 turn-card chip rendering for empty `+0 -0` deltas in the failed run.** Verified data-driven: chip-render at [src/dual_research/ui/static/run-detail.jsx:1298-1320](src/dual_research/ui/static/run-detail.jsx:1298) reads `categories[cat].raised/.closed` from `stats.categories`, populated by `_register_item` at [src/dual_research/ui/items.py:149-154](src/dual_research/ui/items.py:149) from the same arrays STATUS feeds. Once §3.1-§3.4 land, the empty-delta chips populate naturally. No UI work needed.
- **OpenAI `output-128k` equivalent.** OpenAI's `gpt-5.5-2026-04-23` has no analogous beta gate; its default `max_completion_tokens` covers the section-delta response shape.
- **Phase 1 / Phase 3 drafter turns.** Both are single-shot full-document emissions, not part of the negotiation loop, and not affected by this bug. Phase 3 already uses `max_output_tokens=16384` at [src/dual_research/orchestrator/phase3.py:93](src/dual_research/orchestrator/phase3.py:93) and runs once per session, so truncation pressure is much lower.
- **Phase 2 drafter behavior.** Phase 2 has no drafter (per-agent plan synthesis runs in phase 1; phase 2 is pure negotiation). §3.1 still applies to phase 2 prompts for symmetry against future protocol drift.
- **Removing the legacy `run_phase4` at [src/dual_research/orchestrator/phase4.py](src/dual_research/orchestrator/phase4.py).** Already dead code (aliased away); cleanup deferred to a separate refactoring spec.
- **`ProtocolViolation` event when the drafter re-emits a byte-identical `## Revised draft`.** §3.2 puts this in the drafter's prompt as a hard rule; orchestrator-level defense-in-depth (detect `## Revised draft` whose applied delta is byte-equal to the prior draft and emit a `ProtocolViolation` event) deferred to a separate hardening spec.
- **Per-phase `REPLACE_DRAFT_FULL` budget.** Deferred — only revisit if a future agent abuses the escape hatch in observed runs.

## 8. Risks

- **Risk: An agent emits `## Revised draft` containing prose rather than `### REPLACE_*` / `### APPEND_*` / `### DELETE_*` blocks (legacy drafter behavior).** Mitigation: parser raises `ProtocolParseError("revised_draft_body_missing_delta_op")`, routes through `parse_with_repair` for a one-shot repair. The repair prompt restates the §3.2 contract explicitly. If the agent loops back to full re-emit on the repair turn, the consecutive-failures counter trips exit 52 on the next round — same behavior as any other malformed-turn loop.
- **Risk: `### REPLACE_SECTION <heading>` references a heading that doesn't exist in `draft-vN.md`.** Mitigation: promote to `APPEND_SECTION`; log a `ProtocolViolation` event; do not raise. Drafters that misremember section names should not abort the run.
- **Risk: STATUS-first ordering changes downstream telemetry-consumer behavior.** Mitigation: the existing parser is position-agnostic by design ([markers.py:42](src/dual_research/contract/markers.py:42), [markers.py:114-133](src/dual_research/contract/markers.py:114)). `grep -rn "Status\|status_block" src/dual_research/ui/` returns only the spec-0217 STATUS-pass and the per-section regex consumers, all line-anchored.
- **Risk: `max_tokens` → `ProtocolParseError` escalation triggers a repair on turns where the truncation happened in a section the orchestrator doesn't actually need.** Mitigation: even for "harmless" truncation, the canonical guarantee is that no truncated turn lands as authoritative. The cost — 1 repair attempt per phase per agent, already budgeted at [repair.py:42](src/dual_research/orchestrator/repair.py:42) — is acceptable.
- **Risk: Section-delta application has merge edge cases (two `### REPLACE_SECTION <same-h2>` in one turn).** Mitigation: apply in document order, last-writer-wins, log `ProtocolViolation`. Don't raise.
- **Risk: The `output-128k-2025-02-19` beta header changes how Anthropic counts cache or input tokens.** Mitigation: this beta only changes the output cap; cache + input semantics are unchanged per Anthropic's docs. Spec 0143's cache regression detection at [src/dual_research/agents/anthropic_agent.py:160-180](src/dual_research/agents/anthropic_agent.py:160) is the safety net if the beta interaction is wrong.
- **Risk: Drafter interprets "OMIT this section entirely unless there are substantive changes" too literally and stops emitting `## Revised draft` even when there ARE small fixes worth landing.** Mitigation: the §3.2 prompt explicitly states small surgical edits (one `### REPLACE_SECTION` with a few lines) are encouraged; only the round-with-zero-changes case is forbidden. If observed in the wild, prompt-tightening follow-up.
