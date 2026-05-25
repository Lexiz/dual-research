---
spec: "0218"
date: 2026-05-26
version: 1.44.24
pr: https://github.com/Lexiz/dual-research/pull/255
kind: deployed
---

# Spec 0218 — phase-4 STATUS survives truncation

## What landed

Four coordinated changes make phase-4 STATUS-block survival structural rather than aspirational. The smoking-gun session `20260525-162909-backend-language-choice` looped phase 4 to `hard_cap=6` because the drafter (claude) re-emitted the full ~8K-token revised draft on every round; combined with the 8192 output-token cap, 4 of 6 turns truncated with `finish_reason="max_tokens"` **before** the `## Status` block printed — destroying STATUS, the canonical ledger-op channel spec 0217 / 0217.1 made authoritative.

### §3.1 — STATUS-first ordering across all 6 prompt sites

The `## Status` block now sits immediately after `## Stance` in every negotiation / review prompt at [src/dual_research/protocol/prompts.py](src/dual_research/protocol/prompts.py): `preflight_prompt_v2` (phase 0 round 1), `input_negotiation_prompt_v2` (phase 0 round N), `plan_negotiation_round1_prompt_v2` (phase 2 round 1, added for symmetry beyond the 5 sites the spec listed), `plan_negotiation_round_n_prompt_v2` (phase 2 round N), `review_round1_prompt_v2` (phase 4 round 1), `review_round_n_prompt_v2` (phase 4 round N). A new `_STATUS_FIRST_ORDERING_CALLOUT` constant explains the rationale inline above the section list so agents understand WHY STATUS is at the top rather than the end. The shared `_status_footer_for_phase` template is unchanged — only the call-site positions moved.

### §3.2 — Section-delta drafter contract

The drafter's `## Revised draft` body is now a sequence of `### REPLACE_SECTION <heading>` / `### APPEND_SECTION <heading>` / `### DELETE_SECTION <heading>` operation blocks applied against the prior `draft-vN.md` to produce `draft-v(N+1).md`. `### REPLACE_DRAFT_FULL` is the escape hatch for structural rewrites. New parser surface at [src/dual_research/protocol/parse.py](src/dual_research/protocol/parse.py): `extract_revised_draft_deltas` + `apply_revised_draft_deltas` returning a typed `RevisedDraftDeltas | RevisedDraftFull` discriminated union; the existing `extract_revised_draft_inclusive` is unchanged. The dr_run.py drafter-revision callback at [src/dual_research/orchestrator/dr_run.py](src/dual_research/orchestrator/dr_run.py)'s `_on_revised_draft` dispatches on the union variant. Legacy full-prose `## Revised draft` bodies (no `### REPLACE_*` / `### APPEND_*` / `### DELETE_*` / `### REPLACE_DRAFT_FULL` sub-heading) raise `ProtocolParseError("revised_draft_body_missing_delta_op")` and route through repair. Mismatched-heading `REPLACE_SECTION` promotes to `APPEND_SECTION` with a logged protocol-violation; same-heading double `REPLACE_SECTION` applies last-writer-wins with a logged violation; `### REPLACE_DRAFT_FULL` is exclusive (per-section ops in the same turn are dropped). Typical response shrinks from ~10-12K tokens to ~2-4K tokens.

### §3.3 — `parse_with_repair` wired into `dr_run.py`

New `parse_v2_with_repair` sibling at [src/dual_research/orchestrator/repair.py](src/dual_research/orchestrator/repair.py) runs validator + one-shot repair between `run_one_call` and the canonical write in `_drive_interaction_phase`. `_assert_v2_well_formed_turn` rejects turns whose `## Status` block is missing (`parsed.status is None`) and turns whose `## Revised draft` body lacks delta-op sub-headings. `finish_reason in {"max_tokens", "length"}` is treated as a synthetic parse failure regardless of body shape — a truncated turn whose tail bytes coincidentally look STATUS-valid is still untrustworthy. Truncated text is saved to `<turn>.malformed-<n>.md` via the `next_malformed_n` helper; the canonical path is only written after the repaired turn parses clean. The existing v1 `parse_with_repair` also gained the `finish_reason` optional param for symmetry, although it remains called only by the legacy `run_phase4` (dead code per [src/dual_research/orchestrator/run.py:36](src/dual_research/orchestrator/run.py:36)). RepairTracker semantics unchanged — one-shot budget per agent per phase, exit 52 on second consecutive failure.

### §3.4 — Output-budget bump + Anthropic beta header

`_TURN_MAX_OUTPUT_TOKENS = 16384` (up from 8192) at [src/dual_research/orchestrator/dr_run.py:104](src/dual_research/orchestrator/dr_run.py:104). The matching `OUTPUT_128K_BETA = "output-128k-2025-02-19"` constant is added to [src/dual_research/agents/anthropic_agent.py](src/dual_research/agents/anthropic_agent.py) and merged into the `anthropic-beta` header alongside the existing `EXTENDED_CACHE_TTL_BETA` so the API actually serves 16K output tokens. The beta only affects the output cap; cache + input semantics are unchanged per Anthropic's docs (verified through the spec 0143 cache-regression detection at [src/dual_research/agents/anthropic_agent.py:160-180](src/dual_research/agents/anthropic_agent.py:160) as the safety net).

## Test coverage

Eleven regression tests at [tests/test_spec_0218_phase4_status_survives_truncation.py](tests/test_spec_0218_phase4_status_survives_truncation.py):

- **5.1 × 5** — STATUS-first ordering across all 5 prompt sites (phase 4 rN, phase 4 r1, phase 2 rN, phase 0 r1, phase 0 rN).
- **5.2** — Section-delta application: `REPLACE_SECTION 2. Findings` + `APPEND_SECTION 4. Confidence ledger` + `DELETE_SECTION 3. Sources` produces the expected `draft-v(N+1).md` with no violations.
- **5.3** — Legacy prose `## Revised draft` body raises `ProtocolParseError("revised_draft_body_missing_delta_op")`.
- **5.4 × 2** — `finish_reason="max_tokens"` AND `finish_reason="length"` both trigger repair via `parse_v2_with_repair`, with `truncated_by_max_tokens` in the error list and `RepairInvoked` published exactly once.
- **5.5** — Truncated original → canonical write contains the REPAIRED text, not the truncated text; `<turn>.malformed-1.md` sidecar holds the discarded truncated bytes; tracker budget exhausted; exactly one `RepairInvoked` event published.
- **5.6** — Captured R2-claude truncated turn shape (no STATUS heading, ends mid-table-cell) is rejected by `_assert_v2_well_formed_turn` with `missing STATUS:`. Fixture is synthesised in-test to match the shape described by the spec body since the live run text is not checked into the repo.

`uv run pytest tests/ -q` — 1976 / 1976 pass (1965 prior + 11 new). Spec 0217 / 0217.1 suites continue green — the STATUS-pass at [src/dual_research/ui/disagreements.py:587-610](src/dual_research/ui/disagreements.py:587) is unchanged; it now finds STATUS arrays that actually land.

## What's NOT in this spec (per §7)

- **Phase-4 turn-card chip rendering for empty `+0 -0` deltas in the failed run** — verified data-driven; populates naturally once STATUS arrays survive.
- **OpenAI `output-128k` equivalent** — `gpt-5.5-2026-04-23` has no analogous beta gate; default `max_completion_tokens` covers section-delta responses.
- **Phase 1 / Phase 3 / Phase 2-drafter turns** — not affected by this bug; phase 3 already runs at 16384 cap; phase 2 has no drafter.
- **Removing the legacy `run_phase4` at [src/dual_research/orchestrator/phase4.py](src/dual_research/orchestrator/phase4.py)** — already dead code; cleanup deferred.
- **`ProtocolViolation` event when the drafter re-emits a byte-identical `## Revised draft`** — defense-in-depth deferred; the prompt-level hard rule is the primary mechanism.
- **Per-phase `REPLACE_DRAFT_FULL` budget** — only revisit if observed abuse.

## Verification

- `uv run pytest tests/ -q` — 1976 / 1976 pass.
- GH Actions deploy run `26424091372` for merge commit `3fd34fc` — pytest + flyctl + sweep-stale-blues all green; deployed to `dual-research-alex.fly.dev` v1.44.24.
- App is up: `https://dual-research-alex.fly.dev/` returns HTTP 200.

## Follow-ups

None planned. The follow-up specs flagged in §7 (`ProtocolViolation` for byte-identical re-emit; per-phase `REPLACE_DRAFT_FULL` budget; full removal of legacy `phase4.py`) remain optional hardening. The primary mechanism (validator + repair + structurally bounded response shape) shipped here and will be verified by the next prod-tier session that produces a substantive phase-3 draft.
