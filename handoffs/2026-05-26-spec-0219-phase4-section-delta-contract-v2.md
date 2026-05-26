---
spec: "0219"
date: 2026-05-26
version: 1.44.25
pr: https://github.com/Lexiz/dual-research/pull/256
kind: deployed
---

# Spec 0219 — §3.2 section-delta drafter contract v2

## What landed

Six coordinated changes attack the four bugs spec 0218 left behind. The smoking-gun run `runs/20260526-000758-backend-language-choice/` looped six `revised_draft_delta_violation` events, three repair invocations, and a terminal `run_failed` exit 52 after the repair budget exhausted — with `draft-v2.md` ballooned to ~90KB of side-by-side duplicated sections because bug-2 silently promoted heading-mismatched REPLACE_SECTION ops to APPEND.

### §3.1 — Reviewer template drops `## Revised draft`

[`review_round_n_prompt_v2`](src/dual_research/protocol/prompts.py) now computes a role-conditional doctrine block. The drafter sees the section-delta op grammar plus the literal current-draft heading list (§3.3 below); the reviewer sees a one-line `_REVIEWER_REVISION_NOTE` instructing them to OMIT the `## Revised draft` section entirely. Reviewer no longer writes `(reviewer — no draft edits)` inside a `## Revised draft` heading, which is the literal text that tripped the spec 0218 §3.2 validator every phase-4 round and exhausted the repair budget.

### §3.2 — Validator gates the `## Revised draft` check on `is_drafter`

[`_assert_v2_well_formed_turn`](src/dual_research/orchestrator/repair.py) now takes `is_drafter: bool` and `prior_draft: str | None` keyword args. The §3.2 check fires only when `is_drafter=True`. `parse_v2_with_repair` threads both through so heading-mismatch / anchor-mismatch / missing-`reason:` failures route through the same one-shot repair plumbing. `_drive_interaction_phase` derives `is_drafter_turn = (phase_int == 4 and agent_name == ctx.state.drafter)` at the per-agent call site and reads `prior_draft` from `current_draft_path(...)` once per drafter turn.

Detection of `## Revised draft` heading presence in `raw_text` uses `SECTION_REVISED_DRAFT_RE` directly (not `parsed.revised_draft`), because `parse_turn_v2` strips empty-body sections to `None`. Drafter-emits-heading-with-empty-body is now a structural violation (`revised_draft_body_missing_delta_op`), per spec 0219 §3.5 doctrine.

### §3.3 — Literal current-draft headings injected into the drafter prompt

New [`extract_draft_headings`](src/dual_research/protocol/parse.py) helper parses the on-disk `## ` headings; [`_drafter_revision_doctrine_v2`](src/dual_research/protocol/prompts.py) inlines them into the drafter prompt as a bulleted list capped at 20 entries (the smoking-gun draft has 6). The drafter is told verbatim: "Each delta op MUST target a heading from this list — taken verbatim, no paraphrase, no renumbering, no substring drift." Wired at the `review_round_n_prompt_v2` call site in [`dr_run.py`](src/dual_research/orchestrator/dr_run.py); the `system_task` variant (cacheable framing) gets an empty headings list so per-round heading variance doesn't pollute the cache.

### §3.4 — Parser hard-fails on unknown REPLACE_SECTION / EDIT_SECTION heading

[`apply_revised_draft_deltas`](src/dual_research/protocol/parse.py) replaces the spec 0218 silent APPEND-on-mismatch promotion with `ProtocolParseError("drafter", ["replace_section_unknown_heading: …" / "edit_section_unknown_heading: …"])`. Error messages include the valid-headings list so repair can re-prompt with the actual draft headings. Failures across all ops in a payload accumulate before raising — a single repair attempt surfaces every issue.

### §3.5 — New `### EDIT_SECTION` surgical op + `reason:` requirement on REPLACE_SECTION

New `EditSectionOp` discriminant in the `DraftDeltaOp` union, parsed by a `_parse_edit_section_pairs` state-machine that walks `ANCHOR:` / `REPLACE_WITH:` line pairs. Multiple pairs per block, applied in document order. Anchor matching is byte-exact and must hit exactly once per section body — `0` matches raises `edit_section_anchor_not_found`, `>1` matches raises `edit_section_anchor_ambiguous`. A 5-line typo fix becomes ~100 output tokens vs ~2000 with `REPLACE_SECTION`, attacking the 16,758-token cap-overrun symptom by shrinking per-op payloads instead of raising `_TURN_MAX_OUTPUT_TOKENS`.

`REPLACE_SECTION` now requires a leading `reason: <one sentence>` line (validator-enforced via `_strip_replace_section_reason`); missing reason raises `replace_section_missing_reason`. Doctrine inline in the drafter prompt: "Default to `### EDIT_SECTION`. Use `### REPLACE_SECTION` only when rewriting > 50% of a section, and include a `reason:` line."

### §3.6 — Phase-4 round counter checkpointed per round

New `SessionState.phase4_round: int = 0` field at [`state.py:33`](src/dual_research/persistence/state.py:33) (backwards compatible — legacy state JSON without the field deserialises to 0). `_drive_interaction_phase` seeds `round_no` from it on phase-4 entry; persists after each round completes via the existing `ctx.session.save_state(ctx.state)` plumbing. Resumed phase-4 runs pick up at round N+1 instead of restarting at round 1, saving ~$1.40/resume per agent on prod-tier models. Reset to 0 on the phase-3→phase-4 transition.

## Test coverage

Twelve regression tests at [tests/test_spec_0219_section_delta_contract_v2.py](tests/test_spec_0219_section_delta_contract_v2.py):

- **§3.1 / §3.2 — reviewer pass / drafter still fails:** `test_reviewer_revised_draft_omitted_passes_validator`, `test_reviewer_revised_draft_prose_passes_validator`, `test_drafter_revised_draft_empty_still_fails` (covers both empty-body and prose-only cases).
- **§3.4 — heading-mismatch hard-fail:** `test_replace_section_unknown_heading_hard_fails` asserts the valid-headings list is in the error message.
- **§3.5 — EDIT_SECTION semantics:** `test_edit_section_anchor_roundtrip`, `test_edit_section_anchor_not_found_hard_fails`, `test_edit_section_anchor_ambiguous_hard_fails`, `test_replace_section_missing_reason_hard_fails`.
- **§3.6 — round counter survives resume:** `test_phase4_round_checkpoint_survives_resume` (round-trip + legacy-state-deserialises-to-0 + simulated fresh-process pick-up at round N+1).
- **End-to-end replay:** `test_replay_malformed_turn_from_smoking_gun_run` parses the vendored fixture at [tests/fixtures/spec_0219/round-02-claude.malformed-1.md](tests/fixtures/spec_0219/round-02-claude.malformed-1.md) (8 REPLACE_SECTION ops) against a stub draft with draft-v1's actual headings and asserts `replace_section_unknown_heading` surfaces with `2.1` among the rejected targets.
- **Helper:** `test_extract_draft_headings_returns_literal_in_order`, `test_extract_draft_headings_empty_draft_returns_empty_list`.

The 0218 test fixture at [tests/test_spec_0218_phase4_status_survives_truncation.py:200](tests/test_spec_0218_phase4_status_survives_truncation.py:200) gains a `reason:` line on its REPLACE_SECTION to honour the new validator contract. `uv run pytest tests/ -q` — 1988 / 1988 pass (1976 prior + 12 new).

## What's NOT in this spec (per §7)

- **Bumping `_TURN_MAX_OUTPUT_TOKENS` above 16K** — same disease, later symptom. EDIT_SECTION + REPLACE_SECTION-with-reason attack the root cause. Re-open if still busting 16K on > 5% of phase-4 turns.
- **Multi-turn drafter (one section per turn)** — doubles latency; deferred unless EDIT_SECTION proves insufficient.
- **Tool-use file-handle transport for the draft** — tool-input JSON counts as output tokens (already ruled out in spec 0218).
- **`empty_turn_detected` events in the smoking-gun run** — likely 2nd-order; re-evaluate post-merge.
- **Phase-2 reviewer template symmetry** — phase 2 has no `## Revised draft` section to remove (verified via grep).
- **Anchor matcher fuzziness (whitespace-tolerant ANCHOR matching)** — start strict (byte-exact); loosen only if real-world failures justify it.

## Verification

- `uv run pytest tests/ -q` — 1988 / 1988 pass.
- GH Actions deploy run [`26441624010`](https://github.com/Lexiz/dual-research/actions/runs/26441624010) for merge commit `804d784` — pytest + flyctl + sweep-stale-blues all green; deployed to `dual-research-alex.fly.dev` v1.44.25.
- App is up: `https://dual-research-alex.fly.dev/` returns HTTP 200.

## Follow-ups

None planned. The post-deploy validation is "the next prod-tier phase-4 run on `backend-language-choice` (or equivalent brief with hierarchy drift) emits no `revised_draft_delta_violation` events, the drafter reaches for `### EDIT_SECTION` by default, and `draft-vN.md` byte-size grows monotonically and modestly rather than ballooning."
