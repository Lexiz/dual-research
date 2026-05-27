---
spec: 0136
title: Unify run-status derivation — single source of truth across the All-Runs list, the run-detail page, and the orchestrator's exit-code emission
label: bug
version-bump: PATCH
status: ready
target-version: 1.8.1
created: 2026-05-21
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0136 — Unify run-status derivation

> Ship bucket: **Status-truth-table consolidation across list / detail / orchestrator.**
> Depends on: **0017** (deadlock rendering at the Phase 2 hard cap — established that "exit 51 = deadlocked" semantics), **0089** (convergence escape hatches: `via_canonical_promotion` / `via_canonical_fsd_synthesis` / `via_stuck_agreed` — escape branches that legitimately produce `exit_code == 0` with `state.phase == "done"`), **0114** (Deep Research protocol — moved Phase 0 / 2 / 4 to the shared `_drive_interaction_phase` coroutine that this spec touches).
> Complexity: **S** — one new helper, two call-site swaps, one orchestrator predicate fix, one tail-scan extension. No protocol / contract / wire-format changes.
> Targeted version bump: **PATCH (1.8.0 → 1.8.1)** — bug fix. Status values on the wire stay in the existing vocabulary (`running` / `completed` / `deadlocked` / `errored`); only the assignment logic changes.

---

## 1. Context

Two independent live runs surfaced the same symptom on the same day:

- **`20260520-170146-dvs-backend-language-choice`** — All-Runs list shows `running`; run-detail page shows `completed`. The run actually exited 36 minutes ago (`run_completed` event in the transcript) but Phase 2 ran 8/8 rounds without converging (`phase2_complete{converged: false, drafter: null}`). Truthfully it's **deadlocked**, but neither surface says so. The detail-page timeline also drops the last round's output card — a downstream symptom of the wrong terminal status.
- **`20260520-232251-llm-vs-human-grading`** — same pattern observed earlier in the run (the divergence resolves itself when both surfaces eventually settle on `running`, but the transient mismatch is visible while the surfaces disagree on whether `run_completed` has fired).

This is the third time we're patching this surface (specs 0009, 0016, 0017 all touched it at various phases). The recurring root cause: **two independent status derivers** running against the same data and disagreeing on the answer.

### 1.1 The two divergent code paths

**Path A — All-Runs list** (`ui/aggregator.summarize_run` → `ui/labels.derive_run_status`):

```python
# aggregator.py:270-316  (summarize_run)
state = _read_state(session_dir / "state.json")
hard_cap_hit, run_failed = _scan_terminal_signals(session_dir / "transcript.jsonl")
status = derive_run_status(
    state_phase=state.phase,
    final_emitted=bool(state and state.final_emitted_to),
    hard_cap_hit=hard_cap_hit,
    run_failed=run_failed,
)
```

```python
# labels.py:113-130  (derive_run_status)
if run_failed:
    return "errored"
if hard_cap_hit and not final_emitted:
    return "deadlocked"
if final_emitted or state_phase == "done":
    return "completed"
return "running"   # ← FALL-THROUGH
```

The fall-through swallows the *"run exited cleanly without reaching done"* case as `running` indefinitely. `_scan_terminal_signals` (lines 1088-1109) only looks for `hard_cap_hit` / `run_failed` — `run_completed` is invisible to this path.

**Path B — Run-detail page** (`ui/aggregator.apply_event` → `_on_run_completed` / `_on_run_failed`):

```python
# aggregator.py:846-857  (_on_run_completed)
exit_code = int(event.get("exit_code", 0))
if exit_code == 0:
    run.status = "completed"   # ← UNCONDITIONAL
elif exit_code == 51:
    run.status = "deadlocked"
elif exit_code in (1, 2, 52):
    run.status = "errored"
```

```python
# aggregator.py:859-868  (_on_run_failed)
run.status = "errored"
run.error = TopLevelError(...)
```

This path trusts the orchestrator's `exit_code` blindly and never cross-checks against `state.phase` or `final_emitted_to`. Whatever the orchestrator emitted wins.

### 1.2 The orchestrator's silent-exit gap

The shared interaction-phase driver `dr_run._drive_interaction_phase` (lines 199-372) loops until `round_no < caps.hard`. After the loop:

```python
# dr_run.py:336-345
if not converged and round_no >= caps.hard:
    await event_bus.publish(HardCapHit(...))
    hard = phase.hard_cap_remaining_items(round=round_no)
    if hard:                                # ← GATING PREDICATE
        for ev in hard:
            await event_bus.publish(ev)
        via_hard_cap = True
        converged = True
```

When the hard cap is reached AND `hard_cap_remaining_items` returns a non-empty list, the function emits `HardCapHit` + flips `via_hard_cap = True` + `converged = True` — those propagate up to `phase2_outcome.hard_capped = True`, then to `exit_code = EXIT_HARD_CAP (51)`, then `_on_run_completed` maps to `deadlocked`. Healthy path.

When `hard_cap_remaining_items` returns an empty list (every raised item already terminal — withdrawn / resolved / acknowledged — but the negotiation still never reached `STATUS: AGREED`), the **`HardCapHit` event isn't even emitted**. `via_hard_cap` stays False, the outcome reports `hard_capped=False`, the orchestrator's `run.py` falls through all three `phase2_outcome.{parse_failure,hard_capped,converged}` branches without bumping `exit_code` off `EXIT_OK`. The run emits `RunCompleted(exit_code=0)` despite Phase 2 having silently failed to converge.

**This is exactly what happened on the DVS run.** `phase2_complete{rounds: 8, converged: false, drafter: null}` followed by `run_completed{exit_code: 0}`. State stays at `phase2`. `final_emitted_to` stays null. The two UI paths disagree precisely because the orchestrator handed them an ambiguous terminal signal.

### 1.3 Why this surfaces as a user-facing inconsistency

The two paths read the same transcript + state but apply different rules:

| Run | Transcript signals | State | Path A says | Path B says | Truth |
|-----|--------------------|-------|-------------|-------------|-------|
| DVS-backend (silent-exit Phase 2) | `run_completed{exit_code: 0}`; no `hard_cap_hit`; no `run_failed` | `phase: phase2`, `final_emitted_to: null` | `running` | `completed` | **deadlocked** |
| Pre-spec-0089 stuck-AGREED escape | `run_completed{exit_code: 0}`; no `hard_cap_hit` | `phase: done`, `final_emitted_to: …` | `completed` | `completed` | completed ✓ |
| Hard-cap with remaining items | `run_completed{exit_code: 51}`; `hard_cap_hit` present | `phase: phase2`, `final_emitted_to: null` | `deadlocked` | `deadlocked` | deadlocked ✓ |
| Crashed mid-Phase-2 | `run_failed` present | `phase: phase2` | `errored` | `errored` | errored ✓ |
| Live in-flight | `phase_entered{phase2}`; no terminal | `phase: phase2` | `running` | `running` | running ✓ |

Only the silent-exit row diverges — but it's a frequent enough failure mode (the spec-0089 escape hatches only catch specific *patterns* of stuck-AGREED; arbitrary "no agreement, no remaining items, hit hard cap" still leaks through) that the user has noticed it twice in one day.

---

## 2. Proposed change

Three coordinated changes — one orchestrator, two UI — that collapse the two paths onto one truth table.

### 2.1 Orchestrator — emit `hard_cap_hit` whenever the loop exits unresolved at hard cap

In [`src/dual_research/orchestrator/dr_run.py:336-345`](src/dual_research/orchestrator/dr_run.py), drop the `if hard:` gating predicate so `hard_cap_hit` fires whenever the loop reaches `caps.hard` without convergence:

```python
if not converged and round_no >= caps.hard:
    await event_bus.publish(
        HardCapHit(phase=phase_label, round=round_no, cap=caps.hard)
    )
    hard = phase.hard_cap_remaining_items(round=round_no)
    for ev in hard:                # may be empty; that's fine
        await event_bus.publish(ev)
    via_hard_cap = True
    converged = True
```

Rationale: `HardCapHit` is the canonical marker for *"we ran the negotiation to exhaustion without an organic agreement"*. Whether there are leftover non-terminal items is orthogonal — the leftover items are an artefact of how convergence is gated, not a condition on whether the cap was hit. Today's gate produces a silent-success exit code for the "every item terminal, no AGREED status" pattern, which is precisely the failure mode the DVS run hit.

This flip cascades correctly through the existing pipeline:
- `phase2_outcome.hard_capped = result.via_hard_cap` ([dr_run.py:946](src/dual_research/orchestrator/dr_run.py#L946)) becomes `True`.
- `run.py:287-289` ([orchestrator/run.py:287](src/dual_research/orchestrator/run.py#L287)) sets `exit_code = EXIT_HARD_CAP (51)`.
- `RunCompleted` emits with `exit_code = 51` instead of `0`.
- Both UI paths agree: `deadlocked`.

Identical change applies to Phase 4's branch in the same file (it reuses `_drive_interaction_phase` via `run_dr_phase4` — same predicate, same fix).

### 2.2 UI — single status function consumed by both paths

Extend [`src/dual_research/ui/labels.py:113`](src/dual_research/ui/labels.py) `derive_run_status` to accept the full terminal-event surface, not just two bools:

```python
def derive_run_status(
    *,
    state_phase: str,
    final_emitted: bool,
    hard_cap_hit: bool,
    run_failed: bool,
    run_completed_exit_code: int | None = None,
) -> str:
    """Single source of truth for Run.status.

    Precedence (highest first):
    1. run_failed event present → "errored"
    2. run_completed.exit_code ∈ {EXIT_RUNTIME (2), EXIT_PROTOCOL_PARSE_FAILURE (52)} → "errored"
    3. run_completed.exit_code == EXIT_HARD_CAP (51) OR hard_cap_hit event present → "deadlocked"
    4. final_emitted OR state.phase == "done" → "completed"
    5. run_completed.exit_code == 0 AND not (final_emitted OR state.phase == "done") → "deadlocked"
       (the silent-exit case § 1.2 — the orchestrator exited cleanly but never reached done;
       after § 2.1 ships, this branch becomes unreachable for new runs but stays as defence-in-depth
       for transcripts produced by the buggy emitter)
    6. else → "running"
    """
    if run_failed:
        return "errored"
    if run_completed_exit_code in (2, 52):
        return "errored"
    if hard_cap_hit or run_completed_exit_code == 51:
        return "deadlocked"
    if final_emitted or state_phase == "done":
        return "completed"
    if run_completed_exit_code == 0:
        return "deadlocked"        # silent-exit defence
    return "running"
```

(Exit-code constants stay in `orchestrator/run.py`; importing them into `labels.py` would invert the dependency direction, so the magic numbers `2, 51, 52` are kept inline with a comment pointing at the source-of-truth file. Same convention `_on_run_completed` already uses today.)

### 2.3 UI — All-Runs path reads `run_completed`

Extend [`_scan_terminal_signals`](src/dual_research/ui/aggregator.py#L1088) to also pull the exit code out of any `run_completed` event:

```python
def _scan_terminal_signals(transcript_path: Path) -> tuple[bool, bool, int | None]:
    """Tail-scan for hard_cap_hit / run_failed / run_completed markers."""
    hard_cap = False
    run_failed = False
    run_completed_exit_code: int | None = None
    # … loop …
        if event.get("event") == "hard_cap_hit":
            hard_cap = True
        elif event.get("event") == "run_failed":
            run_failed = True
        elif event.get("event") == "run_completed":
            try:
                run_completed_exit_code = int(event.get("exit_code", 0))
            except (TypeError, ValueError):
                run_completed_exit_code = 0
    return hard_cap, run_failed, run_completed_exit_code
```

Then [`summarize_run`](src/dual_research/ui/aggregator.py#L270) passes the new value into `derive_run_status`:

```python
hard_cap_hit, run_failed, run_completed_exit_code = _scan_terminal_signals(...)
status = derive_run_status(
    state_phase=state.phase if state else "phase0",
    final_emitted=final_emitted,
    hard_cap_hit=hard_cap_hit,
    run_failed=run_failed,
    run_completed_exit_code=run_completed_exit_code,
)
```

### 2.4 UI — Run-detail path defers to the same function

Replace the imperative branches in [`_on_run_completed`](src/dual_research/ui/aggregator.py#L846) and [`_on_run_failed`](src/dual_research/ui/aggregator.py#L859) with a stash-and-recompute pattern. Both handlers record the terminal signal on a private field; `load_run_snapshot` (or a small `_finalise_status` helper called at the end of `apply_event` replay) runs `derive_run_status` once after the replay completes:

```python
# aggregator.py — new private fields on Run, populated by event handlers
@dataclass
class _TerminalSignals:
    run_completed_exit_code: int | None = None
    run_failed: bool = False
    hard_cap_hit: bool = False
    run_failed_error: TopLevelError | None = None

def _on_run_completed(run: Run, event: dict) -> None:
    run._terminal_signals.run_completed_exit_code = int(event.get("exit_code", 0))
    # Agents go idle on terminal — preserved from the old handler.
    for ag in run.agents.values():
        ag.status = "idle"

def _on_run_failed(run: Run, event: dict) -> None:
    run._terminal_signals.run_failed = True
    run._terminal_signals.run_failed_error = TopLevelError(
        when=event.get("ts", ""),
        where=event.get("phase_reached", "orchestrator"),
        code=event.get("error_type", "ORCHESTRATOR_PANIC"),
        detail=event.get("message", ""),
    )
    for ag in run.agents.values():
        ag.status = "idle"

# Dispatch already catches hard_cap_hit at aggregator.py:262
# Update that branch to set run._terminal_signals.hard_cap_hit = True instead of
# (or in addition to) the current direct `run.status = "deadlocked"` assignment.

def _finalise_status(run: Run) -> None:
    """Called after transcript replay. Applies the unified status truth table."""
    sigs = run._terminal_signals
    state_phase = "done" if run.phase == 5 else f"phase{run.phase}"
    run.status = derive_run_status(
        state_phase=state_phase,
        final_emitted=bool(getattr(run, "final_path", None)),
        hard_cap_hit=sigs.hard_cap_hit,
        run_failed=sigs.run_failed,
        run_completed_exit_code=sigs.run_completed_exit_code,
    )
    if sigs.run_failed and sigs.run_failed_error is not None:
        run.error = sigs.run_failed_error
```

`load_run_snapshot` calls `_finalise_status(run)` once at the end of replay (right before the `_populate_current_bodies` step that already runs there). The live SSE stream calls it after each event apply so the run-detail surface re-derives status the same way on every push (cheap — pure dict reads).

`_TerminalSignals` is private (leading underscore) and not serialized to the wire — only `run.status` + `run.error` go out.

### 2.5 Existing-transcript backfill

Pre-fix transcripts that emitted `RunCompleted{exit_code: 0}` without reaching `done` (the DVS-backend case + any historical run with the same pattern) are picked up correctly by branch #5 of the new `derive_run_status` (the "silent-exit defence" line). No data migration needed — the truth table handles legacy transcripts on the fly.

---

## 3. Out of scope

- **The deeper convergence math.** Whether the orchestrator *should* have been able to declare "every item terminal but no AGREED" as a converged-via-stuck-agreement case is a separate question (spec 0089 handled some patterns of stuck-AGREED via dedicated escape hatches; this spec doesn't extend those). We're fixing the *reporting* — the underlying "Phase 2 ran 8 rounds without an AGREED plan and exited cleanly" pattern stays a hard-cap deadlock until a future spec broadens the convergence semantics.
- **Renaming `deadlocked` to something more precise** for the silent-exit case (e.g. `failed_to_converge`). The existing four-value enum (`running` / `completed` / `deadlocked` / `errored`) is canon across the frontend, the status pills, the run-list filter chips, and the API contract. Adding a fifth value is a frontend-wide change out of scope for a PATCH bug-fix.
- **Process-level liveness detection.** A run whose orchestrator process died without emitting `run_failed` (OOM kill, host reboot, network partition mid-write) shows up as `running` indefinitely. Detecting that requires a heartbeat — the queue-v2 subsystem already has this for hosted runs (the `runs.heartbeat_at` column + 60 s reaper), but local runs don't. Out of scope here.
- **Per-phase status badges.** This spec is about the top-level `Run.status`; the timeline cards and phase headers derive their own per-phase status independently from the same underlying events. Untouched.

---

## 4. Test plan

**Backend unit tests** (new fixtures in `tests/ui/test_aggregator_status.py`):

- [ ] **Healthy completion**: transcript ends with `run_completed{exit_code: 0}`, `state.phase = "done"`, `final_emitted_to = "out.md"`. Both `summarize_run` and `load_run_snapshot` return `status = "completed"`.
- [ ] **Hard-cap deadlock**: transcript contains `hard_cap_hit` + `run_completed{exit_code: 51}`, `state.phase = "phase2"`, `final_emitted_to = None`. Both paths return `status = "deadlocked"`.
- [ ] **Silent-exit deadlock** (the DVS regression): transcript contains `run_completed{exit_code: 0}`, no `hard_cap_hit`, `state.phase = "phase2"`, `final_emitted_to = None`. Both paths return `status = "deadlocked"` (covers the legacy-transcript defence branch).
- [ ] **Runtime error**: transcript contains `run_failed{error_type: ORCHESTRATOR_PANIC}`. Both paths return `status = "errored"`.
- [ ] **Parse-failure exit**: transcript contains `run_completed{exit_code: 52}`. Both paths return `status = "errored"`.
- [ ] **In-flight (no terminal yet)**: transcript ends with `phase_entered{phase2}`, no `run_completed`. Both paths return `status = "running"`.
- [ ] **Phase 4 → done**: `state.phase = "done"`, `run_completed{exit_code: 0}`. Both paths return `status = "completed"`.

**Orchestrator unit test** (new in `tests/orchestrator/test_dr_run_hardcap.py`):

- [ ] **Hard-cap with no remaining items**: drive `_drive_interaction_phase` with a stub that emits `STATUS: NEGOTIATING` on every round and never raises an item that survives a transition. After `caps.hard` rounds the function publishes `HardCapHit` (the predicate fix in § 2.1) and the returned `PhaseRunResult` has `via_hard_cap = True`.
- [ ] **Hard-cap with remaining items**: existing test stays green (the `for ev in hard` loop now runs unconditionally but is a no-op when `hard` is empty; non-empty inputs still emit the same per-item events as today).

**Regression check on the DVS transcript on disk**:

- [ ] Load `runs/20260520-170146-dvs-backend-language-choice` through both `summarize_run` and `load_run_snapshot` after the patch. Both must return `status = "deadlocked"` (was: `running` / `completed`).

**Manual UI verification**:

- [ ] Open the All-Runs list and the run-detail page for at least one each of: healthy `completed`, `deadlocked`, `errored`, in-flight `running`. Status pills agree across the two surfaces.
- [ ] The deadlocked detail-page timeline now renders the last-round output card (the missing card the user flagged — falls out of spec-0017 once the status is set correctly).

---

## 5. Risks

- **Hosted transcript replay**. Any existing run with `run_completed{exit_code: 0}` + non-done state flips from `completed` → `deadlocked` on the All-Runs list after this ships. This is the correct outcome — those runs *are* deadlocked, the UI was just lying about it. Mitigated by the fact that the run-detail page already shows correct timeline content (the issue was the top-line pill); users will see the pill change but no data goes missing.
- **`_TerminalSignals` private field on `Run`**. The dataclass is wire-serialised via `dataclasses.asdict` in [`server.py:1591`](src/dual_research/ui/server.py#L1591). Leading-underscore fields are NOT skipped by `asdict` by default — need an explicit pop after the asdict call, or use a `field(metadata={"wire": False})` pattern and a custom serializer. Implementation note: easiest path is a `_to_jsonable` helper that strips underscore-prefixed keys, which `to_jsonable` already does for `_round_index_*` book-keeping fields in the same module (verify before relying on it; if not, do the pop explicitly).
- **Live SSE re-derivation cost**. `_finalise_status` runs on every event apply. The function is pure dict reads + 5 short-circuit branches — sub-microsecond. Verified by the existing `apply_event` benchmarks that already do similar per-event work on hot paths.
- **`derive_run_status` signature change**. The new `run_completed_exit_code` parameter defaults to `None`, so existing callers (if any beyond `summarize_run` and tests) continue to work. The two production callers both update in this spec.
- **Rollback shape**. If the orchestrator predicate change (§ 2.1) misfires for some edge case I'm not seeing, the UI fix alone (§ 2.2 – § 2.4) is sufficient to fix the user-facing inconsistency — branch #5 of the new `derive_run_status` covers the silent-exit case directly. So the rollback story is "revert just § 2.1 if anything goes wrong; the UI fix stays in place independently."

---

## 6. Open questions

- **Should `_finalise_status` run on every SSE push, or only on snapshot/disk loads?** Per-push is the safest answer (the truth table is cheap and idempotent) but adds a tiny per-event cost. **Default: per-push.** Revisit if profiling surfaces it.
- **Should `_TerminalSignals` be public for the JSON wire?** Knowing the exit code on the detail page would let the UI surface a small "exited with code 51 (deadlocked)" tooltip. **Default: keep private for this spec; surface in a follow-up if requested.** This spec is about correctness, not new surface.
