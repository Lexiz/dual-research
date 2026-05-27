---
kind: dev
spec: "0224"
slug: cli-signal-handlers-for-tombstone
title: "Fix: CLI registers SIGTERM/SIGHUP/SIGINT cancel handlers so the 0222 tombstone fires on raw signal kills"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: ["0222"]
complexity: S
created: 2026-05-26
queued_at: "2026-05-26T20:15:40Z"
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

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0224 — Fix: CLI registers SIGTERM/SIGHUP/SIGINT cancel handlers so the 0222 tombstone fires on raw signal kills

> **Type:** bug  |  **Severity:** P1  |  **Affects:** orchestrator local-CLI runs across all versions ≤ v1.45.4 (the 0222 tombstone is unreachable for the most likely silent-death signals).
> **Bump:** PATCH — bug fix
> **Evidence:** run-`20260526-102321` died silently mid-phase-2 (per Cowork resume snapshot [cowork/feedback/2026-05-26-orchestrator-stabilisation-resume.md](../cowork/feedback/2026-05-26-orchestrator-stabilisation-resume.md) §1–§2). Verified facts:
> - `grep -rn "signal\.SIG\|add_signal_handler" src/` returns nothing (no handlers anywhere in the source tree).
> - `src/dual_research/cli.py:352` is bare `result = asyncio.run(run_session(...))` — registers no handlers.
> - `src/dual_research/orchestrator/run.py:548` is the post-0222 `except BaseException as e:` tombstone-writer (line shifted from 543 by the 0222 `_terminal_written` flag at `run.py:411`).

## Source traceability (spec 0198)

| Source item | Source quote / ref | Spec section |
|---|---|---|
| Cowork resume snapshot §3 spec #1 — "SIGTERM signal handler (NEW — 0222 follow-up)" | "`cli.py` only — register `loop.add_signal_handler(SIGTERM, main_task.cancel)` at the asyncio entry; CancelledError then propagates into 0222's existing `except BaseException` + tombstone. ~10 lines." | §2, §3 |
| Cowork resume snapshot §2 verified findings (0222 gap analysis) | "0222 catches: SIGINT (→`KeyboardInterrupt`), in-process `asyncio.CancelledError`, `SystemExit`, all `Exception` subclasses. 0222 misses: raw `SIGTERM`, `SIGKILL`, OOM-kill, hard-crash." | §2 |
| Author correction — extend to SIGHUP for Mac-local-CLI runs | Terminal-launched CLI on macOS receives SIGHUP on window close, app quit, SSH disconnect, laptop sleep. Same CPython default disposition as SIGTERM (immediate termination, no exception). Bypasses 0222 identically. | §3, §7 |
| Cowork resume snapshot §4 deliberate-don'ts — no sidecar watchdog, no Fly log read, no SIGKILL/OOM coverage | "Acting now is cheaper than waiting for an answer we can't get… SIGKILL/OOM/hard-crash remain impossible to handle in-process; would require a sidecar watchdog — separate spec if ever needed." | §7 |

## 1. Reproduction

**Environment:** local-CLI orchestrator on macOS (the only deployment surface — the hosted Fly app at `dual-research-alex.fly.dev` serves only the UI, not the orchestrator).

**Steps:**
1. Start a long-running orchestrator: `uv run dr -p "<any prompt>" --tier prod`.
2. Once the run is mid-phase (any phase past `phase0_started`), send the process a SIGTERM or SIGHUP:
   - `kill -TERM <pid>` (or `kill -HUP <pid>`), OR
   - Close the terminal window the CLI was launched from (raises SIGHUP on shell exit), OR
   - Let the laptop sleep over SSH and lose the connection (raises SIGHUP on disconnect).
3. Inspect the run's `transcript.jsonl` and `metrics.json` after the process exits.

**Expected:** a terminal event — `run_completed`, `run_failed`, or `run_aborted` — appears as the last line of `transcript.jsonl`, and `metrics.ended_at` is non-null in `metrics.json`. (Spec 0222's Area-5 liveness invariant: "For every `run_started`, exactly one terminal event is emitted and `metrics.ended_at` is set — including on `BaseException`.")

**Actual:** the process terminates immediately with no exception raised. `transcript.jsonl` ends mid-phase with no terminal event; `metrics.ended_at` stays `null`. Neither the `except BaseException as e:` block at [src/dual_research/orchestrator/run.py:548](src/dual_research/orchestrator/run.py:548) nor the `if not _terminal_written:` fallback inside the `finally:` block at [src/dual_research/orchestrator/run.py:626](src/dual_research/orchestrator/run.py:626) runs.

Run-`20260526-102321` is a likely instance of this failure (Cowork resume snapshot §2).

## 2. Root cause hypothesis

CPython's default disposition for `SIGTERM` and `SIGHUP` is **immediate process termination without raising any exception**. Neither signal is converted to a Python-level exception by the runtime; both terminate the process before any `except` or `finally` clause runs.

The 0222 tombstone at [src/dual_research/orchestrator/run.py:548](src/dual_research/orchestrator/run.py:548) (`except BaseException as e:`) plus the `_terminal_written` finally-fallback at [src/dual_research/orchestrator/run.py:626](src/dual_research/orchestrator/run.py:626) is correct for everything that **does** flow through Python's exception machinery — `Exception` subclasses, `KeyboardInterrupt` (SIGINT → CPython converts automatically), `SystemExit`, and in-process `asyncio.CancelledError`. But the entry point at [src/dual_research/cli.py:352](src/dual_research/cli.py:352) is a bare `asyncio.run(run_session(...))`. With no `loop.add_signal_handler` calls anywhere in `src/`, the orchestrator inherits CPython's default — raw `SIGTERM` and `SIGHUP` kill the process before either the `except` or the `finally` block can write a terminal event.

This is a contract gap, not an implementation bug in 0222 itself: 0222 closed the in-process side (any exception is now tombstoned); this spec closes the signal-handling side (the two most likely local-CLI silent-death signals get routed into the exception machinery as `CancelledError`).

## 3. Fix

Register asyncio signal handlers for `SIGTERM`, `SIGHUP`, and `SIGINT` at the asyncio entry in [src/dual_research/cli.py:352](src/dual_research/cli.py:352) that cancel the main task. The cancellation surfaces as `asyncio.CancelledError` inside `run_session`, which the existing `except BaseException as e:` at [src/dual_research/orchestrator/run.py:548](src/dual_research/orchestrator/run.py:548) already catches, writing `run_failed` to the transcript (or, if `_terminal_written` is still `False` when control reaches `finally:`, the fallback writes `run_aborted` per [run.py:626](src/dual_research/orchestrator/run.py:626)).

Sketch (helper structure may vary — only the observable behaviour matters):

```python
import signal

async def _run_with_signal_handlers(**kwargs):
    loop = asyncio.get_running_loop()
    main_task = asyncio.current_task()
    for sig in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        loop.add_signal_handler(sig, main_task.cancel)
    return await run_session(**kwargs)

result = asyncio.run(_run_with_signal_handlers(...all current kwargs from cli.py:352...))
```

Notes for the implementer:

- The same handler set must apply to the `_ingest` path at [src/dual_research/cli.py:282](src/dual_research/cli.py:282) (the other `asyncio.run(...)` site), or the spec must document why ingest doesn't need it. Default decision: ingest is short-lived and rarely produces a transcript worth tombstoning, but applying the same wrapper costs nothing and keeps the two entries symmetric. Apply.
- `loop.add_signal_handler` is POSIX-only — it raises `NotImplementedError` on Windows. The orchestrator is verified Mac-local-CLI today (Cowork resume snapshot §4: "the orchestrator runs LOCALLY (Alex's Mac), not on Fly"). Acceptable as-is. If portability ever becomes a concern, gate behind `sys.platform != "win32"`.
- Registering `SIGINT` explicitly converts Ctrl-C from raising `KeyboardInterrupt` (CPython default) into raising `asyncio.CancelledError` (via the cancel handler). Both flow through `except BaseException as e:` and produce a tombstone, so the observable outcome is the same. The error_type field in the `run_failed` transcript event changes from `KeyboardInterrupt` to `CancelledError` — call this out in the test plan so the assertion accepts either, and so the implementer is aware.

## 4. User stories & acceptance criteria

Not a UI bug — §4 not required (per the bug template). The §5 regression-prevention tests are the load-bearing gate.

Acceptance criteria (functional):

- A live orchestrator process that receives `SIGTERM`, `SIGHUP`, or `SIGINT` mid-run writes a terminal event (`run_failed` or `run_aborted`) to `transcript.jsonl` and sets `metrics.ended_at` non-null in `metrics.json`. The 0222 Area-5 liveness invariant ("for every `run_started`, exactly one terminal event is emitted") holds for these three signals.
- Existing in-process exception handling (Exception subclasses, asyncio.CancelledError from in-process cancellation, SystemExit, KeyboardInterrupt from the default SIGINT path if SIGINT registration is skipped) continues to produce a tombstone — no regression in 0222's behaviour.
- The interactive Ctrl-C UX is preserved: a single Ctrl-C cancels the run cleanly (with a tombstone), not a half-cancelled hang. Double-Ctrl-C / Ctrl-\ still escape (default asyncio behaviour on second SIGINT).

## 5. Regression-prevention test

- [ ] **Test 1 — SIGTERM tombstone (in-process).** New test file `tests/test_spec_0224_signal_handler_tombstone.py`. Spawns the orchestrator entrypoint via `asyncio.create_task` against a mocked long-running phase (asyncio.sleep), schedules `os.kill(os.getpid(), signal.SIGTERM)` after the task is running, then awaits the entrypoint. Asserts: (a) `transcript.write` was called with `event="run_failed"` (error_type="CancelledError") or `event="run_aborted"`; (b) `metrics.ended_at` is non-null on the saved `metrics.json`; (c) the assertion passes against the post-fix code AND **fails against the current (pre-fix) cli.py** — confirms the test actually exercises the new handler path. Pure stdlib + pytest, same fixture style as `tests/test_spec_0222_liveness_tombstone.py`.
- [ ] **Test 2 — SIGHUP tombstone.** Same harness as Test 1 with `signal.SIGHUP`. Locks in the Mac-local-CLI most-likely-death case.
- [ ] **Test 3 — SIGINT preserves tombstone + interactive UX.** Same harness with `signal.SIGINT`. Asserts a terminal event is written AND the run exits via the new CancelledError path (not the legacy KeyboardInterrupt path). Confirms the SIGINT UX swap (KeyboardInterrupt → CancelledError) is intentional and tombstoned.

All three tests must fail against the current `cli.py:352` (bare `asyncio.run`) and pass after the fix.

## 6. Blast radius

- **`cli.py` entry point.** Two `asyncio.run` sites: line 282 (`_ingest`) and line 352 (`run_session`). The fix wraps both. No other entry points exist (verified: `grep -n asyncio.run src/`). The `dr` console-script and the `uv run dr ...` invocation both flow through `cli.main` → these two entry points.
- **`run.py:548` `except BaseException`.** Unchanged. This spec just routes new exception sources (SIGTERM/SIGHUP via CancelledError) into the existing handler.
- **Test surfaces.** `tests/test_spec_0222_liveness_tombstone.py` exercises the in-process CancelledError path. It does not race with the new test file — different fixtures, different mocked phases.
- **Tools that send SIGTERM externally.** Process supervisors (`systemd`, `launchd`, manual `kill -TERM`) and terminal-window-close (SIGHUP) now produce a clean tombstone instead of a silent kill. No regression: callers that previously relied on "process exit code != 0 means crashed" still see `EXIT_RUNTIME` (the `except BaseException` block returns `RunResult(exit_code=EXIT_RUNTIME, ...)` — same as before).

## 7. Out of scope

- **Sidecar watchdog / `psutil`-based external liveness monitor / external supervisor.** Per Cowork resume snapshot §3 ordering: only build this if a silent death recurs **after** spec 0224 ships. Deferred to a follow-up dev spec to be drafted post-merge **only if** new silent-death evidence appears. (Reasoning: SIGKILL, OOM-kill, and hard-crash are fundamentally impossible to handle in-process — they require an external watcher.)
- **SIGKILL / OOM-kill / hard-crash coverage.** Impossible in-process by design (the kernel terminates the process without notification). Same deferral as the watchdog above.
- **Changes to `run.py:548`'s `except BaseException` block or `run.py:626`'s `finally:` fallback.** Spec 0222 implemented these correctly. This spec only ensures they actually get reached for SIGTERM/SIGHUP.
- **Cross-platform support (Windows).** `loop.add_signal_handler` raises `NotImplementedError` on Windows. Out of scope until the orchestrator targets Windows (currently macOS-only per Cowork verification). No `sys.platform` gate needed yet.
- **Fly-side / hosted orchestrator handling.** The Fly app serves only the UI; the orchestrator runs locally. There is no hosted process to signal-handle.
- **Reading Fly logs for run-`20260526-102321` to confirm SIGTERM/SIGHUP was the cause.** Per Cowork resume snapshot §4: Fly logs for that window contain only UI traffic; the orchestrator was local. The fix is correct regardless of the specific cause. Deferred indefinitely (no follow-up spec).

## 8. Risks

- **SIGINT UX swap.** Registering `SIGINT` converts Ctrl-C from `KeyboardInterrupt` to `asyncio.CancelledError`. Both flow through `except BaseException` and produce a tombstone, but downstream code or operator muscle memory that distinguishes the two could be surprised. Mitigation: Test 3 explicitly locks in the new behaviour; if the swap turns out to be undesirable, drop `SIGINT` from the handler tuple — Python's default SIGINT path already raises `KeyboardInterrupt` which 0222 tombstones correctly.
- **Race between cancel and normal completion.** If `SIGTERM` arrives at the exact moment `run_session` is about to return `RunResult` cleanly, `main_task.cancel()` could fire after the success path's `_terminal_written = True` at [run.py:532](src/dual_research/orchestrator/run.py:532). The `except BaseException` block would then run on a CancelledError that arrived after the tombstone was already written. Outcome: a second terminal event (`run_failed`) appended after `run_completed`, violating the "exactly one terminal event" invariant. Mitigation: gate the except-block tombstone-write on `if not _terminal_written:` (the same flag 0222 uses for the finally-fallback) — implementer should check 0222's exact pattern and replicate it in the except block if not already done. Test 1 should include a variant that triggers SIGTERM during the success path's final transcript-write to lock this in.
- **`add_signal_handler` callback is sync, called from the loop thread.** `main_task.cancel()` is itself sync and thread-safe in this context. No additional wrapping needed. Low risk.
- **Test mocking of `os.kill(os.getpid(), ...)`.** Sending a real signal to the test process can disrupt pytest's own signal handling (pytest installs its own SIGINT handler for `--pdb`-on-keyboardinterrupt). Mitigation: scope handler registration to the test's event loop only; tear down handlers in test cleanup. Use `pytest --no-cov` for the signal tests if cov instrumentation interferes; document any pytest flags required.
- **`SIGHUP` on macOS terminals can be coalesced with `SIGCONT` after wake-from-sleep.** If the laptop sleeps and wakes before the signal handler installs, the wake-up sequence is normal — no edge case. If it sleeps mid-run, SIGHUP fires, handler runs, tombstone written, process exits cleanly on wake. Test 2 covers this.
