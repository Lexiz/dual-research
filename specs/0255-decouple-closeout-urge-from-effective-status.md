---
kind: dev
spec: "0255"
slug: decouple-closeout-urge-from-effective-status
title: "Decouple the closeout-urge gate from effective status: fire should_urge_closeout on RAW self-reported AGREED so a spec-0229 addressee-obligation demotion no longer disarms the closeout → ghost-cap escape valve and deadlocks phase 2/4 to the hard cap"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: "1.64.0"
status: queued
depends_on: ["0114", "0229"]
complexity: S
created: 2026-05-29
queued_at: "2026-05-29T12:57:08Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "Deterministic phase-2 hard-cap deadlock on a fully-agreed run that wastes a full prod-tier run and produces no final.md, so it ships now."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0255 — Decouple the closeout-urge gate from effective status

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** 0114 (closeout mechanism + convergence rules), 0229 (addressee-obligation invariant + effective-status demotion)
> **Bump:** MINOR — per [CLAUDE.md](CLAUDE.md) "Contract-changing specs are not `bug`s": this modifies the **convergence / closeout / escape-valve partition** (one of the named contract surfaces). It is NOT labelled `bug`. It is a behaviour change (the closeout-urge gate now fires on a strictly larger set of rounds), so it is not behaviour-preserving `refactoring` either; `new-feature` is the honest classification with an explicit `disposition: ship`.
> **Evidence:** captured live failure `runs/20260529-091956-backend-language-choice/phase2-deadlock.md` (exit 51, $7.19, no `final.md`); transcript signals (0 `CloseoutUrged` events, 30 `agreed_with_open_addressed_items` ProtocolViolations all on openai, 5 claude items stuck `open` across rounds 3–8).

---

## 1. Context

On run `runs/20260529-091956-backend-language-choice` the two agents reached full agreement — both emitted `STATUS: AGREED` with byte-identical AGREED_PLAN blocks across rounds 3–8, zero self-reported open items — yet phase 2 ground to its hard cap (8 rounds), wrote `phase2-deadlock.md`, exited 51, and produced no `final.md`. The cost of the dead rounds was $7.19.

The root cause is an over-broad reuse of spec 0229's **effective status**. Spec 0229 §2.2 demotes a self-reported `AGREED` to an effective `IN_PROGRESS` for the convergence gate whenever the agent emitted `AGREED` while items raised by the *other* agent are still `open` and un-`ADDRESS`ed by this agent — the `agreed_with_open_addressed_items` ProtocolViolation, emitted at [src/dual_research/orchestrator/deep_research.py:751](src/dual_research/orchestrator/deep_research.py:751) and folded into effective status by `_effective_status_for` at [src/dual_research/orchestrator/deep_research.py:170](src/dual_research/orchestrator/deep_research.py:170). On this run openai `ADDRESS`ed only 1 of claude's 6 raised items, so 5 (`D-plan-c-02`, `D-plan-c-03`, `D-plan-c-04`, `Q-plan-c-01`, `Q-plan-c-02`) stayed `open` and openai's `AGREED` was demoted **every round**.

The defect is that this single demoted "effective" status is fed into **both** end-of-round gates in `process_round_end` — the convergence gate `check_convergence` ([src/dual_research/orchestrator/deep_research.py:855](src/dual_research/orchestrator/deep_research.py:855)) **and** the closeout-urge gate `should_urge_closeout` ([src/dual_research/orchestrator/deep_research.py:863](src/dual_research/orchestrator/deep_research.py:863)). Because openai's effective status was `IN_PROGRESS` every round, `should_urge_closeout` (defined at [src/dual_research/orchestrator/closeout.py:101](src/dual_research/orchestrator/closeout.py:101)) returned `False`, so `CloseoutUrged` was never emitted (0 in the transcript), `is_closeout_round` was never armed at [src/dual_research/orchestrator/dr_run.py:547](src/dual_research/orchestrator/dr_run.py:547), and the closeout → ghost-cap escape valve never fired. The substantive-convergence escape at [src/dual_research/orchestrator/dr_run.py:503](src/dual_research/orchestrator/dr_run.py:503) is doubly blocked: it requires both a terminal ledger (False — 5 items `open`) AND effective-both-agreed (False — openai demoted). The loop ran to `caps.hard` and exited 51.

The active path is confirmed: `run.py` imports `run_dr_phase2 as run_phase2` ([src/dual_research/orchestrator/run.py:34](src/dual_research/orchestrator/run.py:34)) and calls it; `run_dr_phase2` drives `_drive_interaction_phase` → `process_round_end`. The escape-valve code in `phase2.py:run_phase2` is dead legacy — its only callers are `tests/orchestrator/test_phase2.py` and the unreachable `run.py` branch shadowed by the alias import. The fix touches the live path only.

The structurally correct fix is to **decouple the two gates** per spec 0114's own definition. Spec 0114 ([specs/0114-deep-research-protocol.md](specs/0114-deep-research-protocol.md)) defines closeout as firing "when convergence is *attempted* (both AGREED) but blocked by non-terminal items" — see the `should_urge_closeout` docstring at [src/dual_research/orchestrator/closeout.py:110](src/dual_research/orchestrator/closeout.py:110). A spec-0229-demoted `AGREED` is still an *attempt*: the agent did emit `AGREED`. The convergence gate must keep consuming effective status (a demoted `AGREED` must not *converge*), but the closeout-urge gate must consume the **raw self-reported** status so the escape valve arms on the attempt. This is the smallest high-confidence fix in the root-cause brief and is sufficient on its own — the deeper item-ID-aliasing and un-demotion options are evaluated and deferred in §5.

### Source-artifact traceability

| source item | source quote/ref | spec section |
|---|---|---|
| Captured hard-cap deadlock, both agents AGREED | `runs/20260529-091956-backend-language-choice/phase2-deadlock.md` | §2.1 + §6 |
| 0 `CloseoutUrged` emitted; 30 demotions all on openai; 5 items stuck `open` | transcript of `runs/20260529-091956-backend-language-choice` | §1 + §6 |
| Both gates fed effective status | `src/dual_research/orchestrator/deep_research.py:855` | §2.1 |
| `should_urge_closeout` spec-0114 "attempt" definition | `src/dual_research/orchestrator/closeout.py:101` | §2.1 |
| Escape valve gated on `closeout_event` / `is_closeout_round` | `src/dual_research/orchestrator/dr_run.py:547` | §2.1 |
| Substantive-convergence escape doubly blocked | `src/dual_research/orchestrator/dr_run.py:503` | §2.1 |
| Effective-status demotion (`_effective_status_for`) | `src/dual_research/orchestrator/deep_research.py:170` | §2.4 (0229 interaction) |
| Deferred alternatives (item-ID aliasing, un-demotion, early abort) | root-cause brief candidates 2–5 | §5 |

## 2. Proposed change

### 2.1 — Decouple the closeout-urge gate from effective status

In [src/dual_research/orchestrator/deep_research.py](src/dual_research/orchestrator/deep_research.py), at the two end-of-round assembly sites — `process_round_end` (the live `run_dr_phase2 → _drive_interaction_phase` path, ~line 855) and `run_round` (the synchronous parity path, ~line 1011) — keep `check_convergence` consuming the effective statuses (`eff_claude` / `eff_openai`) but change the `should_urge_closeout` call to consume the **raw self-reported** statuses (`self_claude` / `self_openai`). Add an explanatory comment at both sites stating the partition: convergence on effective status (spec 0229 demotion blocks convergence); closeout-urge on raw status (spec 0114 — a demoted AGREED is still a convergence *attempt*, and demotion must not also disarm the escape valve).

No change to `closeout.py`: `should_urge_closeout` and `check_convergence` already take status arguments verbatim; the demotion was applied entirely by the caller. The fix is two call-argument swaps plus comments.

Result on the captured shape: at the first both-raw-AGREED round, `should_urge_closeout` returns `True` → `CloseoutUrged` is emitted → `is_closeout_round` arms → the closeout request now surfaces openai's addressed-at-me items (spec 0229 §2.1, already wired) → after the per-phase closeout budget (2 for phase 2) is spent without the items reaching terminal, `spend_failed_closeout_budget` triggers ghost-cap → the phase converges `via_ghost_cap` with the blocking items transitioned to `capped` (terminal). The phase exits 0 and proceeds to phase 3 instead of dead-ending at the hard cap.

### 2.2 — Regression test against the active path (spec 0238 live-failure doctrine)

Add `tests/test_spec_0255_phase2_addressee_obligation_deadlock.py` that drives the **real** `run_dr_phase2` entry point (not a helper in isolation) with scripted stub agents reproducing the captured shape: claude raises 5 items in round 1; openai `ADDRESS`es none; both emit empty `STATUS: AGREED` for the remaining rounds so openai is demoted every round. Assert: `outcome.converged is True`; `outcome.hard_capped is False` (the live mirror of `via_hard_cap`; `hard_capped` True is exactly the captured exit-51 deadlock); at least one `CloseoutUrged` event is emitted (the transcript signal that was 0 pre-fix); the single `PhaseConverged` event has `via_ghost_cap True` / `via_hard_cap False`; and claude's 5 items end `capped` via `ghost_cap`. The test must fail on the pre-fix code (it converges with `hard_capped=True` at `rounds=8`) and pass post-fix.

### 2.3 — Version bump + CHANGELOG

- Bump [src/dual_research/__init__.py](src/dual_research/__init__.py) `__version__` `1.63.5` → `1.64.0`.
- Bump [pyproject.toml](pyproject.toml) `version` `1.63.5` → `1.64.0`.
- Add a `## [1.64.0] — 2026-05-29` section to [CHANGELOG.md](CHANGELOG.md) with a `### Fixed` bullet (the deadlock) and a `### Changed` bullet (the gate decoupling + the spec-0229 interaction note).

### 2.4 — Interaction with spec 0229

This spec deliberately preserves every spec-0229 mechanism. `_effective_status_for` and the `agreed_with_open_addressed_items` ProtocolViolation emission are untouched, so the demotion still fires every offending round and still blocks *convergence* on a non-compliant AGREED via `check_convergence`. The only change is which status the *closeout-urge* gate reads.

Crucially this keeps verifier invariant I2.4 green. Spec 0229 §2.4 promoted I2.4 to gating with a **handled-vs-unhandled** detector: an `AGREED`-while-owing turn passes as long as a matching `agreed_with_open_addressed_items` ProtocolViolation exists for the same `agent + phase + round`; it fails only if such a turn produced a `phase_converged` event with open addressed-at-me items still in the ledger. Under this fix (a) the demotion violations still fire every round, so every offending AGREED remains **HANDLED**, and (b) the eventual convergence is `via_ghost_cap`, where the blocking items are transitioned to `capped` (terminal) **before** `PhaseConverged` is emitted — so no AGREED ever converges with an open addressed-at-me item. I2.4 stays a vacuous/handled pass. The regression in §6 includes a verifier check on the post-fix run to lock this in.

### 2.5 — Evaluated alternatives (deferred, see §5)

The root-cause brief ranked five candidates. This spec ships the smallest high-confidence one (§2.1) and explicitly defers the rest with dispositions in §5: item-ID aliasing (semantic IDs in `RAISED_THIS_TURN` vs positional `D-plan-c-NN` ledger IDs), addressee-obligation un-demotion after K stuck rounds, and an early-deadlock abort. Each is evaluated there with a named follow-up target.

## 3. User stories & acceptance criteria

Not a UI-touching spec — user stories / BDD scenarios omitted per template (§3 is REQUIRED only for frontend specs).

Implementer-facing acceptance criteria (mirrors §6):

- `uv run pytest tests/ -q` passes.
- The new `tests/test_spec_0255_*` test fails on the pre-fix code and passes post-fix.
- `__version__ == "1.64.0"` and `CHANGELOG.md` carries a `## [1.64.0]` section.
- The existing spec-0229 and verifier-I2.4 test suites still pass unchanged.

## 4. Data / Schema deltas

None. No new event type, no event-field change, no on-disk schema change. The fix re-routes which in-memory status value an existing gate reads; `CloseoutUrged` / `PhaseConverged` / `ProtocolViolation` shapes are unchanged.

## 5. Out of scope

- **Item-ID aliasing fix (brief candidate 4).** Claude's `RAISED_THIS_TURN` used semantic IDs (`D-java-vs-ts-rank`, `D-go-mcp-sdk-tier`, …) while the ledger assigns positional IDs (`D-plan-c-01`, …); this divergence is *why* openai's `ADDRESS` ops never landed on the ledger items, so the items stayed `open` and convergence had to fall through to ghost-cap (which buries the raiser's legitimately-raised items as `capped`). Fixing the aliasing would let convergence happen via genuine resolution rather than ghost-cap. It is a larger, parser-and-prompt-touching change, orthogonal to the liveness guarantee this spec delivers. **Disposition: defer** — drafted as a follow-up dev spec once an anchor run is captured that isolates the aliasing from the deadlock.
- **Addressee-obligation un-demotion after K stuck rounds (brief candidate 3).** An alternative liveness mechanism (auto-`ADDRESS`/`ACKNOWLEDGE` on the agent's behalf after K stuck rounds). This is redundant with the ghost-cap path that §2.1 re-arms, and it fabricates protocol ops the agent never emitted, which undercuts the addressee-obligation's intent. **Disposition: archive** — not pursued unless ghost-cap proves insufficient on a future run.
- **Early-deadlock abort (brief candidate 5).** K consecutive empty-turn rounds with a frozen ledger + both self-AGREED should abort fast with a legible diagnostic instead of grinding to the hard cap. With §2.1 in place ghost-cap already bounds the cost to ~2–3 closeout rounds past the first AGREED, so this is a legibility/cost nicety rather than a liveness requirement, and it must not pre-empt the ghost-cap convergence this spec relies on. **Disposition: defer** — carved as a follow-up dev spec targeting the cost/observability surface (`_drive_interaction_phase` round loop) once §2.1 has shipped and the ghost-cap path is the confirmed exit.
- **Removing ghost-cap or hard-cap as escape valves.** The four `via_*` flags remain a first-class partition; this spec restores the path to ghost-cap, it does not retire any valve.
- **Touching the legacy `phase2.py:run_phase2` escape-valve code.** Confirmed dead on the live path; left untouched.

## 6. Test plan

- [ ] **Regression — active path converges via ghost-cap.** `tests/test_spec_0255_phase2_addressee_obligation_deadlock.py` drives `run_dr_phase2` with scripted stubs reproducing the captured shape (5 claude items raised, openai addresses none, both emit empty AGREED for K rounds). Assert `outcome.converged is True` and `outcome.hard_capped is False`.
- [ ] **Regression — the broken signal now fires.** In the same test assert ≥1 `CloseoutUrged` event is published (0 in the captured transcript), the single `PhaseConverged` has `via_ghost_cap True` / `via_hard_cap False`, and claude's 5 items end `capped` via `ghost_cap`.
- [ ] **Falsifiability — fails pre-fix.** Confirm the regression test fails against the pre-fix code (the run converges with `hard_capped=True` at `rounds=8`) and passes post-fix. (Verified during authoring by reverting both call-argument swaps.)
- [ ] **No spec-0229 regression.** `tests/test_spec_0229_addressee_obligation.py` passes unchanged — the demotion and the `agreed_with_open_addressed_items` emission are untouched.
- [ ] **No verifier-I2.4 regression.** `tests/test_verifier.py` passes unchanged; I2.4 stays gating-green because every offending AGREED remains HANDLED and ghost-cap caps the items before `phase_converged`.
- [ ] **CHANGELOG + version smoke check.** Assert `__version__ == "1.64.0"` and that `CHANGELOG.md` contains a `## [1.64.0]` section.

## 7. Risks

- **R1 — Closeout fires too eagerly and suppresses a legitimate organic convergence.** *Mitigation:* the closeout-urge call is still guarded by `if not conv.converged and should_urge_closeout(...)` — when the effective convergence gate would pass (both genuinely AGREED, terminal ledger, artifact match), `conv.converged` is `True` and the closeout branch is skipped. Closeout only arms on rounds the phase was *not* going to converge anyway, so it strictly adds liveness without pre-empting a clean exit. The existing `test_organic_convergence_after_closeout_cleanup` and the three-gate convergence tests in `tests/orchestrator/test_deep_research.py` cover this and pass unchanged.
- **R2 — Ghost-cap buries claude's legitimately-raised items as `capped`.** This is pre-existing spec-0114/0229 ghost-cap semantics, not introduced here; this spec only makes the already-designed path reachable. The proper cure (make openai actually `ADDRESS` the items) is the item-ID-aliasing follow-up deferred in §5. Net effect of this spec: a buried-but-converged run (exit 0, `final.md` written) instead of a deadlocked run (exit 51, no `final.md`) — strictly better.
- **R3 — The fix lands on the wrong (dead) path.** *Mitigation:* §2.2's regression test exercises the real `run_dr_phase2` entry point per the spec-0238 live-failure doctrine, so a fix applied only to the dead `phase2.py` path would leave the test red.
