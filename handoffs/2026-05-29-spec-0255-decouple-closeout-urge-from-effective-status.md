---
spec: "0255"
date: 2026-05-29
version: "1.64.0"
pr: "https://github.com/Lexiz/dual-research/pull/295"
kind: post-deploy
---

# Spec 0255 — Decouple the closeout-urge gate from effective status

## What landed

Phase 2 was deadlocking to its 8-round hard cap (exit 51, no `final.md`,
$7.19 wasted on the captured run `20260529-091956-backend-language-choice`)
whenever one agent's `STATUS: AGREED` was demoted by the spec-0229
addressee-obligation rule. The single spec-0229 **effective** status (a
demoted AGREED → `IN_PROGRESS`) was being fed into **both** end-of-round
gates — `check_convergence` *and* `should_urge_closeout` — so the
closeout → ghost-cap escape valve was disarmed alongside the convergence
gate (0 `CloseoutUrged` events in the captured transcript).

The fix decouples the two gates at both end-of-round assembly sites in
[`deep_research.py`](../src/dual_research/orchestrator/deep_research.py):

- `process_round_end` (the live `run_dr_phase2 → _drive_interaction_phase`
  path, ~line 855).
- `run_round` (the synchronous parity path, ~line 1011).

`check_convergence` keeps consuming the effective statuses
(`eff_claude` / `eff_openai`) — a spec-0229-demoted AGREED must not
*converge*. `should_urge_closeout` now consumes the **raw self-reported**
statuses (`self_claude` / `self_openai`) — per spec 0114 a demoted AGREED
is still a convergence *attempt*, so the demotion no longer also disarms
the escape valve. Two call-argument swaps plus an explanatory comment at
each site; no change to `closeout.py` (the demotion was always applied by
the caller).

On the captured shape the phase now arms closeout at the first both-raw-
AGREED round, spends the per-phase closeout budget (2 for phase 2), and
converges `via_ghost_cap` (exit 0) — claude's stuck items transition to
`capped` before `PhaseConverged` — instead of dead-ending at the hard cap.

## Spec-0229 interaction preserved

Every spec-0229 mechanism is untouched: `_effective_status_for` and the
`agreed_with_open_addressed_items` ProtocolViolation emission still fire
every offending round, so the demotion still blocks convergence on a
non-compliant AGREED. Verifier invariant I2.4 stays gating-green — every
offending AGREED remains HANDLED (its matching PV still fires), and the
eventual convergence is `via_ghost_cap` where the blocking items are
`capped` (terminal) **before** `phase_converged` is emitted, so no AGREED
ever converges with an open addressed-at-me item.

## Tests

- New `tests/test_spec_0255_phase2_addressee_obligation_deadlock.py` drives
  the **real** `run_dr_phase2` entry point (spec-0238 live-failure
  doctrine) with scripted stub agents reproducing the captured shape (5
  claude items raised, openai addresses none, both emit empty AGREED).
  Asserts `converged=True`, `hard_capped=False`, `rounds<8`, ≥1
  `CloseoutUrged`, a single `PhaseConverged` with `via_ghost_cap=True` /
  `via_hard_cap=False`, and claude's 5 items end `capped` via `ghost_cap`.
- Falsifiability verified during authoring: reverting both swaps converges
  with `hard_capped=True` at `rounds=8` (the captured deadlock).
- `uv run pytest tests/ -q` → **2447 passed**. Spec-0229 and verifier-I2.4
  suites pass unchanged.

## Deploy note

The first `deploy.yml` run (`26642303682`) on the merge commit was recorded
`failure`: machine 1 deployed healthy, but machine 2's health check timed
out because fly's control-plane API (`api.machines.dev`) was transiently
unreachable (`net/http: request canceled`) — a fly.io infra false-negative,
not a code issue. The image built and pushed cleanly and the live app was
already serving v1.64.0. A re-run of `deploy.yml` (`26642749295`) concluded
`success` and reconciled machine 2. Live `/api/health` reports
`version: 1.64.0`.

## Links

- PR: https://github.com/Lexiz/dual-research/pull/295
- Spec: [specs/0255-decouple-closeout-urge-from-effective-status.md](../specs/0255-decouple-closeout-urge-from-effective-status.md)
- Captured failure: `runs/20260529-091956-backend-language-choice/phase2-deadlock.md`
