---
kind: dev
spec: "0222"
slug: liveness-tombstone-baseexception-and-remove-stdout-streaming
title: "Fix: liveness tombstone (BaseException + finally-fallback) and remove asymmetric stdout streaming"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-26
queued_at: "2026-05-26T17:36:03Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

<!-- DEV SPEC RULE: this body contains no open questions, unresolved items,
or TBD markers. Every decision is answered here or deferred via §7 with a
named follow-up. -->

# Spec 0222 — Fix: liveness tombstone (BaseException + finally-fallback) and remove asymmetric stdout streaming

> **Type:** bug  |  **Severity:** P0 — silent death hides every other failure mode
> **Bump:** PATCH — honest implementation fix, no contract change
> **Affects:** orchestrator runtime (all runs, all phases)
> **Evidence:** run `runs/20260526-102321-backend-language-choice/` died silently at `phase2-r5-claude turn_inputs`; six runs since 2026-05-24 died with the same last-event signature (`turn_inputs` with no terminal event).

---

## 1. Context — source-artifact traceability

This spec implements action 1 of the logic-cutoff synthesis (Bug B + Bug C, folded together per §2.3 of the synthesis: same fix under every mechanism hypothesis). It also establishes Area 5 [NEW] of the unified contract (liveness / terminal events — previously uncontracted).

| Source item | Source quote / ref | Spec section |
|---|---|---|
| Synthesis §6 action 1 — ship the liveness tombstone | "`run.py:543` → catch `BaseException`, re-raise after writing a terminal event; add a `finally` that sets `metrics.ended_at` and writes `run_aborted` if no terminal event fired." | §3.1, §3.3 |
| Synthesis §5 Bug B — silent death | "contract-incomplete (no liveness invariant, Area 5) + impl bug (`except Exception`)". Fix: catch `BaseException` + `finally` tombstone. | §2, §3.1, §3.3 |
| Synthesis §5 Bug C — `stdout` SIGPIPE | "Fix folded into B: remove asymmetric `stream_to=sys.stdout` (`dr_run.py:319`)." | §3.2 |
| Synthesis §3 Area 5 [NEW] — liveness invariant | "For every `run_started`, exactly one terminal event (`run_completed`/`run_failed`/`run_aborted`) is emitted and `metrics.ended_at` is set — including on `BaseException`." | §2, §6 |
| Claude Code feedback §"Action 1 — what I'm starting now" | Items 1–3 of the four-item action plan (item 4 — do not restore `via_self_report` — is a no-op since the tree is already in that state, see §5). | §3.1, §3.2, §3.3 |
| Synthesis §6 action 1 acceptance criterion | "a kill-test (SIGTERM mid-phase) and a replay both leave a terminal event + non-null `ended_at`" | §5 |
| Synthesis §6 action 2 — Fly exit reason | "OOM vs SIGTERM vs CancelledError identified; decides whether the external reaper … is load-bearing." | §7 (deferred — owned by user / separate session) |
| Synthesis §6 action 3 — `ProtocolViolation` on dropped op | Bug A root; observability fix at `deep_research.py:482`. | §7 (deferred — separate spec) |
| Synthesis §6 action 3.5 — `_build_standing_items_text` blind-spot investigation | Feedback §"§7 blind spot" — read end-to-end + cross-reference round-02-claude inputs. | §7 (deferred — separate spec, pending Cowork greenlight) |
| Synthesis §6 actions 4–6 — verifier, reclassification, addressee-obligation | Sequenced after this spec by design. | §7 (deferred — separate specs) |

## 2. Reproduction

**Environment:** Python 3.13 (`asyncio` task tree); macOS local runs and `dual-research-alex.fly.dev` production runs. Affects every orchestrator run, every phase. Observed concretely on six runs since 2026-05-24, most recently `runs/20260526-102321-backend-language-choice/`.

**Steps:**
1. Start a dual-research run via `dr-run` (or in-app).
2. During any phase-2 turn (concretely seen at `phase2-r5-claude`), the process dies — by signal (SIGTERM/SIGKILL), `asyncio.CancelledError`, or any other `BaseException` subclass.
3. Inspect the run directory's `transcript.jsonl` and `metrics.json`.

**Expected:** Per the (until-now uncontracted) Area-5 liveness invariant: every `run_started` is followed by **exactly one** terminal event (`run_completed` / `run_failed` / `run_aborted`), and `metrics.ended_at` is non-null. The run is observably terminated.

**Actual:** The last transcript event is `turn_inputs` (the round's prelude). No `run_failed`, no `run_aborted`, no `run_completed`. `metrics.ended_at` remains `null`. The run is **silently dead** — indistinguishable from "still running" to the dashboard, the queue runner, and any reaper that checks the transcript tail.

## 3. Root cause hypothesis

The orchestrator's top-level handler at [src/dual_research/orchestrator/run.py:543](src/dual_research/orchestrator/run.py:543) catches `except Exception as e:`. Python's exception hierarchy splits at `BaseException` — `asyncio.CancelledError`, `KeyboardInterrupt`, and `SystemExit` are `BaseException` subclasses, **not** `Exception` subclasses. Any of those escapes the handler entirely, the `finally:` block at [src/dual_research/orchestrator/run.py:575](src/dual_research/orchestrator/run.py:575) runs (drains the push-watch loop) but writes no terminal event, and the process exits with the transcript unterminated.

A plausible (synthesis ⚠️-marked) chain that turns benign I/O into one of those `BaseException` deaths: `stream_to=sys.stdout` on claude turns at [src/dual_research/orchestrator/dr_run.py:319](src/dual_research/orchestrator/dr_run.py:319) and [src/dual_research/orchestrator/dr_run.py:951](src/dual_research/orchestrator/dr_run.py:951) — asymmetric vs. the openai path at `dr_run.py:965` which sets `stream_to=None` — turns any broken pipe (stdout closed mid-run, terminal scrollback overflow, parent killed) into a `BrokenPipeError` inside an asyncio task. The task's cancellation cascade can surface as `asyncio.CancelledError` at the orchestrator's top level. That's `BaseException`; `except Exception` doesn't catch it; silent death.

The mechanism is unproven without the Fly.io exit log for 10:23–10:47 UTC (synthesis §2.3 — deferred to action 2, owned outside this spec). **The fix is identical under every hypothesis** — that's why §2.3 folded B and C — so this spec ships the fix now and leaves the mechanism question to action 2.

The shape of the bug — silent death with no terminal event — is what made the recurring failures hard to see in the first place. Until this lands, every downstream observability gap (Bug A's silent `continue`, action 3) is invisible behind a missing-tombstone wall.

## 4. Fix

Three coordinated code changes plus one test. All within `src/dual_research/orchestrator/`.

### 4.1 — `run.py:543` — widen the handler, add the `_terminal_written` flag, re-raise `BaseException`

The except block at [src/dual_research/orchestrator/run.py:543](src/dual_research/orchestrator/run.py:543) widens from `except Exception as e:` to `except BaseException as e:`. The body keeps the existing `metrics.save` + `bus.publish(RunFailed)` + `transcript.write("run_failed", ...)` sequence, wrapped in an inner `try / except BaseException` so a bus-publish failure during shutdown cannot suppress the transcript tombstone (the transcript write is the load-bearing observable; the bus publish is best-effort during a shutdown).

After writing the tombstone, the handler **re-raises** `KeyboardInterrupt`, `SystemExit`, and `asyncio.CancelledError` so that structured-concurrency cancellation propagates correctly and shells see the right exit code. Other `Exception` subclasses continue to fall through to the existing return-`RunResult(exit_code=EXIT_RUNTIME, …)` path — no behaviour change for the cases the old handler already covered.

A `_terminal_written = False` flag is initialised before the `try:` block at the top of the orchestrator body. It is set to `True` in two places:
1. Immediately after the success-path `transcript.write("run_completed", …)` at [src/dual_research/orchestrator/run.py:521](src/dual_research/orchestrator/run.py:521).
2. Immediately after the except-path `transcript.write("run_failed", …)` at the new line 554-equivalent.

### 4.2 — `dr_run.py:319` and `dr_run.py:951` — remove asymmetric stdout streaming

Both call sites set `stream_to=sys.stdout` for claude turns only (openai turns set `stream_to=None`). The streaming was a foreground-debug convenience; turn output is fully captured by the per-turn `.md` files and by the transcript event stream, so removing it loses nothing observable. The asymmetry is also one of the three plausible chains in §3.

- [src/dual_research/orchestrator/dr_run.py:319](src/dual_research/orchestrator/dr_run.py:319): change `stream_to=sys.stdout if agent_name == "claude" else None,` to `stream_to=None,` and drop the unused `stream_prefix` argument on the same call (or pass `""`).
- [src/dual_research/orchestrator/dr_run.py:951](src/dual_research/orchestrator/dr_run.py:951): change `stream_to=sys.stdout,` to `stream_to=None,` and drop the `stream_prefix="[claude] "` argument at line 952 (or pass `""`).

If `sys` becomes unused in `dr_run.py` after these edits, also drop the `import sys` (only if it was added solely for these two call sites — check before deleting).

### 4.3 — `run.py:575` `finally:` — defensive tombstone fallback

The existing `finally:` block at [src/dual_research/orchestrator/run.py:575](src/dual_research/orchestrator/run.py:575) currently only drains the push-watch loop. Extend it so that if `_terminal_written` is still `False` when the `finally:` block runs (i.e. neither the success path nor the except path got far enough to write a terminal event — for example because the inner `try / except BaseException` inside the except block itself raised, or because of a synchronous failure between the top of `try:` and the first `_terminal_written = True`), it:

1. Calls `metrics.mark_done()` + `metrics.save(session.metrics_path)` inside its own `try / except BaseException: pass` — best-effort, must not raise.
2. Calls `transcript.write("run_aborted", phase_reached=phase_reached, reason="terminal-event-fallback")` inside its own `try / except BaseException: pass`.

This is the belt-and-braces guarantee that Area-5 [NEW] of the unified contract requires: **for every `run_started`, exactly one terminal event is emitted and `metrics.ended_at` is set.** The fallback covers the partial-shutdown failure modes the except-block alone cannot.

The existing push-watch drain at [src/dual_research/orchestrator/run.py:579-589](src/dual_research/orchestrator/run.py:579) is preserved verbatim — it stays the first thing the `finally:` does, so the hosted UI still gets the final push.

### 4.4 — Order of operations in `finally:`

The defensive tombstone runs **after** the push-watch drain in the `finally:` block, so the terminal-event write is included in the final push to the hosted UI. Push-watch drain → metrics save → tombstone write.

## 5. Regression-prevention test

The regression-prevention test is the load-bearing gate for this spec (this is a non-UI bug; per the bug template, user stories / BDD scenarios are optional for non-UI bugs).

- [ ] **Test 1 — kill-test for the BaseException path.** New test file `tests/test_spec_0222_liveness_tombstone.py`. Mocks the phase runner to raise `asyncio.CancelledError` mid-phase, calls the orchestrator entrypoint, asserts: (a) `transcript.write` was called with `event="run_failed"` (or with `event="run_aborted"` if the defensive-fallback path fired); (b) `metrics.ended_at` is non-null on the saved `metrics.json`; (c) the `asyncio.CancelledError` was re-raised (caught by the test harness, not swallowed). Uses pure stdlib + `pytest` + the existing orchestrator test fixtures.

- [ ] **Test 2 — defensive-fallback path.** Same harness; mocks both the success-path and except-path `transcript.write` calls to raise (simulates a corrupted transcript handle), asserts the `finally:` block still writes `run_aborted` and still calls `metrics.mark_done()`. Locks in the §4.3 invariant.

Both tests must fail against the current `except Exception` code and pass after the fix.

`uv run pytest tests/ -q` — full suite must still pass (currently 2021 passed prior to this spec being queued; the user verified this against the same edits applied manually in the queue worktree before re-stashing).

## 6. Acceptance criteria (synthesis §6.1)

1. SIGTERM a phase-2 run mid-turn (concretely: start a run locally, `kill -TERM <pid>` between `turn_inputs` and `turn_output`). The run dir's `transcript.jsonl` MUST contain a `run_aborted` or `run_failed` event as its last line, AND `metrics.json`'s `ended_at` MUST be non-null. This is the live-process counterpart to test 1.
2. Replaying an existing run (`uv run dr-run --replay runs/20260526-102321-backend-language-choice/`) MUST NOT produce any new failures vs. the current behaviour.
3. The orchestrator test suite passes end-to-end: `uv run pytest tests/ -q`.

## 7. Out of scope

Each item below is **deferred to a named follow-up** so this PATCH spec stays on the single liveness/tombstone change.

- **External reaper for SIGKILL / OOM.** A SIGKILL'd process cannot self-report; the synthesis §5 names an external reaper as the load-bearing piece. Deferred to a follow-up spec that depends on action 2 (Fly exit log read) since the reaper design depends on which kill mode dominates in practice.
- **`ProtocolViolation` on dropped state-machine ops at `deep_research.py:482`.** Synthesis §6 action 3 (Bug A root). Deferred to its own spec.
- **`_build_standing_items_text` blind-spot investigation.** Synthesis §7 / feedback action 3.5. Deferred to its own spec, pending Cowork greenlight on slotting (per the feedback file's "what I expect from Cowork next").
- **Lifecycle-trace verifier.** Synthesis §6 action 4. Deferred to its own spec; depends on Cowork shipping the invariant list.
- **Spec reclassification (0137 / 0140 / 0218 / 0219) + CLAUDE.md process rule "contract-changing specs are not bugs".** Synthesis §6 action 5. Deferred to its own spec.
- **Addressee-obligation + RESOLVE-from-open coercion feature spec.** Synthesis §6 action 6 — explicitly a `feature` spec, not a `bug` (synthesis §2.1 — rejects `open→resolved`).
- **No change to `via_self_report` convergence path.** Per the feedback file, the `via_self_report` edits Claude Code shipped earlier were already stashed away by a `dev-next pre-flight stash` and the working tree is back to the four-`via_*` partition. This spec verifies that state remains intact (no `via_self_report` references in `dr_run.py` / `events/types.py` / `deep_research.py`) but does not re-edit those files.
- **No contract amendment.** This is `bug`-typed PATCH work establishing the (previously-uncontracted) Area-5 liveness invariant via implementation. The written contract for Area 5 lives in synthesis §3 and will be re-asserted in the action-5 reclassification spec / CLAUDE.md process rule, not here.

## 8. Blast radius

- **`run.py` top-level handler.** Every orchestrator run flows through this `try / except / finally`. Widening to `BaseException` catches three new exception classes (`CancelledError`, `KeyboardInterrupt`, `SystemExit`); the re-raise after tombstone-write means callers that depended on the old `RunResult(exit_code=EXIT_RUNTIME, …)` return on those (none did — those classes weren't caught at all before) see the re-raised exception propagate, which matches Python's standard cancellation semantics.
- **`dr_run.py` claude-turn streaming.** Removing `stream_to=sys.stdout` only suppresses the foreground console output for claude turns. No observable change for hosted runs (where stdout is captured by the launcher anyway), no behaviour change for the orchestrator's structured event flow, no change to per-turn `.md` files. Brings claude in line with openai (already `stream_to=None`).
- **`finally:` block.** The defensive fallback only runs when both the try-success and except-path tombstones failed to write — a path that is unreachable in the current code (and rare even after the fix). When it does run, it best-effort writes one extra transcript line; the worst-case cost is one extra `transcript.write` per run.

## 9. Risks

- **Re-raising `BaseException` subclasses might surprise call sites that previously got `RunResult` back.** Mitigation: those classes weren't being caught at all before — they were already escaping the orchestrator. The re-raise after tombstone-write is the same observable failure mode the callers already had to handle, plus the new tombstone. No new contract for callers.
- **The defensive fallback's `metrics.save` could fail too** (e.g. the session dir is unwritable). Mitigation: it's wrapped in `try / except BaseException: pass`. If `metrics.save` fails, the transcript still gets the `run_aborted` event (separate try), and if both fail, the process exits unchanged from current behaviour. Cannot regress.
- **Inner `try / except BaseException` around the bus publish could hide a bus-stack regression** in the success-rare case where the bus publish is the only thing that failed. Mitigation: the bus publish is best-effort during a shutdown path by design (the transcript is the source of truth, per the synthesis's "reconstructed ledger is authoritative" line of reasoning §1.6); the transcript write is the load-bearing observable, and a bus failure during shutdown should not suppress the transcript tombstone.
- **`asyncio.CancelledError` re-raise inside a task that's not part of structured concurrency** could be ignored. Mitigation: the orchestrator entrypoint is awaited directly by `dr-run` / by the test harness; re-raise propagates to the awaiting frame, which matches standard asyncio shutdown semantics.
