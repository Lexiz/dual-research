# Phase 4 hash-gate replay fixtures (spec 0214)

Sources: local `runs/20260521-010637-dvs-backend-language-choice/phase4/`
(untracked; `runs/` is gitignored).

## Files

- `round-03-claude-historical.md` — verbatim copy of the historical
  Claude round-3 turn. Captures the "content-converged but no Phase
  artifact / Status footer" shape that drove the deadlock: Claude
  delivered a long revised draft but did not emit `STATUS: AGREED`
  because the protocol required a hash neither agent could compute.
  Kept for forensic reference; not parsed by tests.

- `round-03-claude-post-fix.md` /  `round-03-openai-post-fix.md` —
  synthetic transcripts representing the same content-converged moment
  under the post-spec-0214 prompt. Both turns emit `STATUS: AGREED`
  with matching `draft_version: v3` in the new (hashless)
  `AGREED_DRAFT_ACCEPTANCE` shape. Consumed by
  `tests/orchestrator/test_spec_0214_phase4_version_gate.py`'s replay
  smoke to lock in that the actual failing run would have converged at
  round 3 instead of hard-capping at round 8.

The synthetic pair is the test artifact; the historical Claude turn is
the receipt that the spec 0214 fix matches a real run.
