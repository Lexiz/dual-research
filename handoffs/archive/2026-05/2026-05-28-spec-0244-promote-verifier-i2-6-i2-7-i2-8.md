---
spec: "0244"
date: 2026-05-28
version: 1.58.0
pr: https://github.com/Lexiz/dual-research/pull/279
kind: post-deploy
---

# Handoff — spec 0244 — Verifier I2.6 / I2.7 / I2.8 promoted to gating

## What landed

Three trivial `severity=` flips on existing invariants in
[`src/dual_research/contract/verifier.py`](../src/dual_research/contract/verifier.py):

- **I2.6** — STATUS-RAISED-array event cross-check ([spec 0232](../specs/0232-verifier-raised-array-cross-check-i2-6.md)) → `gating`.
- **I2.7** — empty-turn retry hardening ([spec 0239](../specs/0239-empty-turn-retry-hardening.md)) → `gating`.
- **I2.8** — turn termination ([spec 0241](../specs/0241-per-turn-liveness-heartbeat-exception-capture-and-stream-wrapping-cap.md)) → `gating`.

Promoted as a single atomic PR per Cowork's
[`2026-05-28-arc-closeout-signoff.md`](../cowork/briefs/2026-05-28-arc-closeout-signoff.md)
Q3. Reversibility preserved (demote-don't-patch).

Promotion precondition satisfied by the **clean reference run**
`20260528-094743-backend-language-choice` — the first end-to-end clean
run in project history ($8.66, 39KB `final.md`, `metrics.ended_at`
populated, plain-Terminal.app post-[spec 0243](../specs/0243-operational-guard-refuse-running-inside-claude-code.md)
operational guard). That run is now a permanent fixture at
[`tests/fixtures/anchor-runs/20260528-094743-backend-language-choice/`](../tests/fixtures/anchor-runs/20260528-094743-backend-language-choice/)
with its `fixture-notes.md` documenting why.

All six anchor-run fixtures' `expected.json` baselines were regenerated
via `tests._fixture_regen.regenerate_baseline`; the delta is exactly
three lines per pre-existing fixture (the I2.6 / I2.7 / I2.8 severity
fields) plus a full new baseline on 094743. Three stale
`severity == "reporting"` asserts in `tests/test_spec_0239_*.py` /
`tests/test_spec_0241_*.py` updated to `"gating"`.

New
[`tests/test_spec_0244_i2_678_gating.py`](../tests/test_spec_0244_i2_678_gating.py)
adds 41 cases: live verifier × frozen baseline × 6 fixtures × 3
invariants severity-flip matrix (36); 094743 fixture present-and-clean
check; named-fixture sweep across the spec §2.2 table; a
synthetic-violation test proving the gating contract actually gates
(bare `turn_started` → I2.8 = gating fail → CLI rc=1 with "I2.8" +
"[gating]" in output).

`pyproject.toml` + `src/dual_research/__init__.py` + `uv.lock` bumped
to 1.58.0; in-app `version-notes.json` sidecar regenerated.
`pytest tests/ -q` reports 2324 passed (41 new + 2283 pre-existing).

## State at handoff

- **PR**: [#279](https://github.com/Lexiz/dual-research/pull/279) — squash-merged at `3803347`.
- **Live**: `dual-research-alex.fly.dev` serving v1.58.0 (verified
  `/api/health` → `{"ok":true,"version":"1.58.0","backend":"supabase"}`).
- **Branch**: `spec/0244-promote-verifier-i2-6-i2-7-i2-8` deleted on
  both sides (verified delete block passed first attempt).
- **Queue state**: `0244.status = deployed`.

## Deploy retry note

The merge-commit deploy run
([26573152076](https://github.com/Lexiz/dual-research/actions/runs/26573152076))
**failed** on the Fly.io machine-update phase with
`Get "https://api.machines.dev/v1/apps/dual-research-alex/machines/2873d39cd92438": net/http: request canceled` —
Fly.io's machines API was unreachable from the CI runner; health-check
polling timed out after 5 minutes. The image built and pushed cleanly;
only the rollout failed. Queue state was flipped to `failed` per skill
protocol, the operator was surfaced the failure + the recovery options,
and a manual `gh workflow run deploy.yml --ref main` retry
([26573567042](https://github.com/Lexiz/dual-research/actions/runs/26573567042))
succeeded in 45s. State was then re-flipped to `deployed`. No code
change between the two runs; the failure was infrastructure-side.

This was caught by the `feedback_handle_full_delivery` standing rule
that says deploy-watch is part of "done" — the orchestrator did not
silently abandon the cycle, surfaced the failure with a focused
recovery question, and resumed cleanly on the operator's choice.

## Downstream unblocked

- **CI gating now fires on I2.6 / I2.7 / I2.8.** Any future run that
  silently drops a STATUS-RAISED declaration, hits the empty-turn
  retry cap with byte-identical inputs, or leaves a bare
  `turn_started` will fail the verifier rather than reporting in the
  background. The synthetic-violation test in `tests/test_spec_0244_*`
  is the executable lock that this gating actually gates.

- **Demote-don't-patch reversibility precedent.** If a future surveillance
  fixture surfaces a legitimate `gating fail` on one of these three,
  the recovery path is a one-line `severity="gating"` → `"reporting"`
  follow-up commit, not a logic patch. The §7 wording in spec 0244
  + Cowork sign-off Q3 establishes the precedent for future promotions.

- **Reference-fixture promotion pattern.** Spec 0244 is the first time a
  run was promoted to the corpus solely on the basis of having
  verified its verdicts match the gating contract. Future
  fixture-corpus additions should follow this pattern (verify
  first, promote second).

## Deferred during implementation

Nothing. The spec was a tight scope; the only judgement call was
including the two non-spec-named fixtures (`135006`, `102321`) in the
regen sweep — done because the spec said "every fixture under
tests/fixtures/anchor-runs/" and the table named the four worth
calling out, not the four to limit to. All test asserts were updated
in lockstep with the severity change.
