---
spec: "0214"
date: 2026-05-25
version: 1.44.19
pr: https://github.com/Lexiz/dual-research/pull/250
kind: deploy
---

# Spec 0214 — Drop phase-4 agent-emitted hash gate; converge on version equality

Shipped as v1.44.19. The phase-4 cross-review convergence gate no longer asks
each agent to compute a SHA-256 of the draft body. Convergence is anchored to
orchestrator-owned `ctx.state.draft_round`; provenance moves to a new
`Phase4Complete.draft_file_sha256` field that the orchestrator computes from
the on-disk draft.

## What landed

- **Gate rewrite** at [src/dual_research/orchestrator/dr_run.py](src/dual_research/orchestrator/dr_run.py):
  `_phase4_artifact_hash_match` → `_phase4_artifact_version_match`, a thin
  closure that delegates to the new module-level `phase4_version_gate(parsed_a,
  parsed_b, *, ctx_draft_round)` helper. The gate accepts iff both agents emit
  `AGREED_DRAFT_ACCEPTANCE` with the same `draft_version` AND that version
  equals `ctx_draft_round`. The third clause rejects same-round revise-then-
  AGREE (drafter bumps to v<N+1> and emits AGREED before the orchestrator
  advances the pointer).
- **Orchestrator-side provenance** at the publish site: new
  `_compute_draft_sha_if_present(ctx)` reads `current_draft_path(...)` and
  returns `hash_draft_content(text)` (or `None` if no draft on disk). The
  result threads through `Phase4Complete.draft_file_sha256` and the
  `phase4_complete` transcript event.
- **Phase4Complete schema** in [src/dual_research/events/types.py](src/dual_research/events/types.py): new
  optional kw-only field `draft_file_sha256: str | None = None`. Additive —
  `PhaseConverged` is unchanged (phase-agnostic invariant preserved).
- **Subtractive prompt + contract changes:**
  - [src/dual_research/protocol/prompts.py](src/dual_research/protocol/prompts.py) — convergence-description paragraph rewritten; `draft_hash:` line dropped from the `AGREED_DRAFT_ACCEPTANCE` block.
  - [src/dual_research/contract/artifacts.py](src/dual_research/contract/artifacts.py) — module docstring rewritten; `draft_hash:` line dropped from `AGREED_DRAFT_ACCEPTANCE_TEMPLATE`; `hash_draft_content` docstring rewritten to point at `Phase4Complete.draft_file_sha256`.
  - [src/dual_research/contract/markers.py](src/dual_research/contract/markers.py) — `DRAFT_HASH_RE` removed (sole consumer was the parser).
  - [src/dual_research/protocol/parse.py](src/dual_research/protocol/parse.py) — `extract_agreed_draft_acceptance` return narrowed from `tuple[int, str, str]` to `tuple[int, str]`; `DRAFT_HASH_RE` import dropped.
- **Test migration:** `tests/protocol/test_parse_v2.py:test_extract_agreed_draft_acceptance` updated to the two-tuple shape and the post-fix template (no `draft_hash:` line).
- **New regression-prevention suite** at [tests/orchestrator/test_spec_0214_phase4_version_gate.py](tests/orchestrator/test_spec_0214_phase4_version_gate.py) — 9 tests covering accept/reject branches of the gate, the orchestrator-side SHA helper, the `Phase4Complete` field contract, and a replay smoke against committed fixtures.
- **Replay fixtures** at [tests/fixtures/phase4_hash_gate_replay/](tests/fixtures/phase4_hash_gate_replay/) — synthetic post-fix Claude + OpenAI round-3 pair (consumed by the test) plus the historical Claude round-3 turn from the local `20260521-010637-dvs-backend-language-choice` run for forensic reference. Fixture README explains why the literal-replay approach (parsing the real round-3 transcripts) doesn't work: at round 3 of the historical run, OpenAI refused to emit AGREED entirely (hash-exposure refusal), so there is no AGREED+AGREED pair on disk to replay. The synthetic pair represents what the same content-converged moment would look like under the post-fix prompt.

## Verification

- Full suite: `uv run pytest tests/ -q` → **1944 passed** locally; deploy-pipeline pytest job ✅.
- Deploy: GH Actions run [26400785034](https://github.com/Lexiz/dual-research/actions/runs/26400785034) — `conclusion: success`.
- Live: `curl https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.44.19","backend":"supabase"}` (HTTP 200).

## Implementation notes

- The spec referenced the `DRAFT_HASH_RE` definition as living at `src/dual_research/protocol/markers.py:197` — it is actually at `src/dual_research/contract/markers.py:197`. Minor doc nit only; the line number and definition itself were correct.
- The spec's `## 5.` test-plan bullet "the actual failing run would now converge at round 3 instead of hard-capping at round 8" turns out not to be literally testable via raw replay: at round 3 of the historical run OpenAI didn't emit an `AGREED_DRAFT_ACCEPTANCE` block at all (procedural refusal driven by the hash gate). Even at round 7 — where both agents engaged with the AGREED machinery — only Claude emitted AGREED while OpenAI continued to emit IN_PROGRESS. The replay smoke uses a synthetic post-fix pair (Claude + OpenAI both AGREED at v3) to lock the gate-passes-when-content-converges direction; the historical Claude turn is committed alongside for forensic reference. This is documented in the fixture README and the test docstring.
- The gate's `_phase4_artifact_version_match` closure stays in place for backwards-compatible call-site shape against `_drive_interaction_phase(artifact_hash_match=...)`. Renaming the `artifact_hash_match` parameter to a phase-neutral name is out of scope per §7.
- `dashboard/queue-state.json` was kept out of the feature-branch commit deliberately: the queue-state file diverged from branch-base only because `--push-to-main` writes go direct to `origin/main`. Committing it on the branch would have rolled back later `--push-to-main` events at squash-merge time.

## Pointers

- Failing run that motivated the spec: local `runs/20260521-010637-dvs-backend-language-choice/` (untracked).
- Investigation notes: local `phase4-hash-gate-investigation.md` (untracked).
- Spec 0137 / 0140 escape valve (`via_artifact_promotion`) — preserved as dead-letter safety net; unaffected by this change.
- Sibling specs in the same bug-fix batch (queued, not yet shipped): [spec 0215](specs/0215-fix-in-round-partner-blindness.md), [spec 0216](specs/0216-raiser-self-address-observability.md).
