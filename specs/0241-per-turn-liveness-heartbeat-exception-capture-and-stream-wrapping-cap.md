---
kind: dev
spec: "0241"
slug: per-turn-liveness-heartbeat-exception-capture-and-stream-wrapping-cap
title: "Orchestrator: per-turn liveness — heartbeat thread, per-turn BaseException capture, whole-turn cap wrapping stream consumption; verifier I2.8"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: ["0222", "0239"]
complexity: M
created: 2026-05-27
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "Live re-run 20260527-200213 cleared phases 0-3 (parser fix worked, organic phase-2 convergence over 3 rounds, full draft-v1.md produced) then phase 4 issued turn_started -> turn_inputs and died silently with no terminal event, no tombstone, metrics.ended_at=None. Process was NOT killed by the user (verified). The existing 600s httpx timeout in anthropic_agent.py:79 / openai_agent.py:46 is request-establishment-only — does not bound mid-stream stalls. 0222's run-loop tombstone does not catch per-turn API-wrapper exceptions. Result: the orchestrator can die silently in any long-running streamed-agent turn, untraceable. This spec closes the per-turn liveness gap with one authoritative timeout, structured exception capture, and observable heartbeats."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0241 — Per-turn liveness: heartbeat thread + BaseException capture + whole-turn cap wrapping stream consumption; verifier I2.8

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** 0222 (extends the run-loop tombstone to the per-turn API-wrapper layer), 0239 (the per-(agent,phase,round) retry budget that an API-timeout consumes).
> **Bump:** MINOR — adds a new event kind (`turn_heartbeat`), two new `ProtocolViolation` kinds, a verifier invariant (I2.8 reporting), and orchestrator state for the heartbeat/timeout machinery. Per-turn liveness invariants ARE the contract per CLAUDE.md "contract-changing specs are not bugs".
> **Evidence:** live re-run [`runs/20260527-200213-backend-language-choice/`](runs/20260527-200213-backend-language-choice/) (phase-4 silent death after `turn_inputs` flush); HTTP-client config at [`src/dual_research/agents/anthropic_agent.py:79`](src/dual_research/agents/anthropic_agent.py:79) and [`src/dual_research/agents/openai_agent.py:46`](src/dual_research/agents/openai_agent.py:46) (existing `timeout=600.0` is request-establishment, not stream-read); streaming call sites at [`src/dual_research/agents/anthropic_agent.py:110`](src/dual_research/agents/anthropic_agent.py:110) and [`src/dual_research/agents/openai_agent.py:103`](src/dual_research/agents/openai_agent.py:103) (both consume async streams the existing timeout does not bound). Cowork design briefs: `cowork/feedback/2026-05-27-live-rerun-20260527-200213-investigation.md`, `cowork/briefs/2026-05-27-0241-per-turn-liveness-read.md`.

---

## 1. Context

The live re-run `20260527-200213-backend-language-choice` completed phases 0, 1, 2, and 3 cleanly — the spec-0238 parser fix did its job (phase 2 converged organically over 3 rounds with real `item_raised` event flow), and phase 3 produced a 52KB `draft-v1.md`. Phase 4 then issued `phase_entered` → `turn_started` → `turn_inputs` at `20:33:25.265–267 UTC` and **emitted nothing further** — no `turn_ended`, no `protocol_violation`, no tombstone, no error event. `metrics.json.ended_at` is `None`; the process was found dead later. The user did not kill it.

Two structural gaps allowed the silent death:

1. **The `timeout=600.0` set on both `AsyncAnthropic` ([anthropic_agent.py:79](src/dual_research/agents/anthropic_agent.py:79)) and `AsyncOpenAI` ([openai_agent.py:46](src/dual_research/agents/openai_agent.py:46)) is the httpx HTTP-request-establishment timeout.** It bounds the time-to-first-response on the underlying HTTP call. Both agents then consume the response as a stream ([anthropic_agent.py:110](src/dual_research/agents/anthropic_agent.py:110) `messages.stream`, [openai_agent.py:103](src/dual_research/agents/openai_agent.py:103) `responses.create(stream=True)`). A mid-stream stall — the stream opens, produces chunks, then the next chunk takes arbitrarily long or never arrives — is **not** bounded by the existing timeout. The `async for chunk in stream` await blocks indefinitely.

2. **Spec 0222's `except BaseException` tombstone is installed at the run loop level (`run.py:543`), not at the per-turn API-wrapper level.** If the per-turn coroutine raises (`httpx.ReadTimeout`, `anthropic.APIError`, a cancelled-task exception from the host session, a `MemoryError`) and that exception escapes via a path the run-loop's tombstone doesn't cover — for example, an unawaited asyncio task, an exception inside `async with self._client.messages.stream(...)` that the context manager swallows on `__aexit__`, or process-level signal handling 0224 doesn't see — the process exits without writing a terminal event. No `error` event lands in `transcript.jsonl`. The dashboard sees `turn_started` then silence forever.

Three failure hypotheses are consistent with the observed dead state:

- **H2 (leading): SDK exception escaped 0222's tombstone.** Most likely: the 600s httpx timeout did fire on a mid-stream stall (the wall clock between `turn_inputs` flush and process discovery exceeded 10 minutes by a wide margin), `httpx.ReadTimeout` was raised inside the stream context, the exception escaped via a path the run-loop's `except BaseException` doesn't cover, the process exited without a tombstone.
- **H3 (live): autonomous process death.** macOS jetsam / OOM-kill / host-session SIGHUP-on-suspend / container limit. SIGKILL is uncatchable; even 0224's signal handlers cannot trap it. The hosting Claude Code session that fired the dual-research run is a candidate trigger.
- **H1 (DEAD): user kills blind.** Verified: the user did not kill the run. This hypothesis is ruled out.

All three live hypotheses converge on the same fix layer: **per-turn liveness instrumentation** — make the wall-clock behaviour of a turn observable, structured, and bounded, so that the next silent death produces enough telemetry to distinguish H2 from H3 without further code archaeology.

## 2. Proposed change

Five layers ship together in one PR, ordered by priority (per Cowork sign-off in `cowork/briefs/2026-05-27-0241-per-turn-liveness-read.md`).

### 2.1 — Layer 1 (highest value): heartbeat events from a separate thread

While any per-turn API call is in flight, emit a `turn_heartbeat` event every 30 seconds to `transcript.jsonl`:

```json
{
  "ts": "2026-05-27T20:33:55.000Z",
  "event": "turn_heartbeat",
  "agent": "claude",
  "phase": "phase4",
  "round": 1,
  "elapsed_seconds": 30
}
```

**Threading**: the heartbeat runs on a **separate OS thread** (not an asyncio task on the same event loop), launched at `turn_started` and joined at `turn_ended` or terminal-violation emission. Rationale: if the event loop itself is blocked (busy-loop in a sync callback, GIL-held native code, kernel-level stall), an asyncio-scheduled heartbeat task would never run and we would still see dead silence. A separate OS thread writes directly to the transcript file with append-mode locking, surviving event-loop stalls. This is the differential diagnostic that lets us distinguish H2 from H3 from "event loop blocked" on the next silent death.

**Flush discipline**: each heartbeat write is `open(path, 'a').write(line) ; flush()` — line-buffered, fsync-optional. The cost is one syscall every 30s per active turn; budget is negligible.

**Configuration**: `TURN_HEARTBEAT_INTERVAL_SECONDS = 30` lives next to the wrapper, not promoted to config. Tunability is YAGNI until the data demands it.

### 2.2 — Layer 2: per-turn `try/except BaseException` → tombstone

Wrap every per-turn API call site in `try/except BaseException` at the agent-wrapper layer:

```python
async def run(self, prompt: str, *, ...) -> AgentResult:
    try:
        # existing call site:
        async with self._client.messages.stream(**kwargs) as stream:
            ...
    except BaseException as exc:
        emit_protocol_violation(
            kind="turn_api_call_exception",
            agent=self.label,
            phase=phase, round=round,
            data={
                "exception_type": type(exc).__name__,
                "exception_module": type(exc).__module__,
                "message": str(exc)[:1024],
            },
        )
        raise
```

The `emit_protocol_violation` call writes the structured event to `transcript.jsonl` **before** the exception propagates upward. The re-raise preserves 0222's run-loop tombstone behaviour (the run loop still gets to log its own tombstone, the per-turn site adds a more specific trace one layer down). This is a strict extension of 0222, not a replacement.

Two call sites need the wrap: [`anthropic_agent.py`'s `run()`](src/dual_research/agents/anthropic_agent.py) (around the `messages.stream` block at line ~110) and [`openai_agent.py`'s `run()`](src/dual_research/agents/openai_agent.py) (around the streaming call at line ~103). DRY via a small helper if the two wrap patterns end up identical; otherwise leave duplicated and paired in review.

New `ProtocolViolation` kind registered in [`src/dual_research/events/types.py`](src/dual_research/events/types.py): `"turn_api_call_exception"`.

### 2.3 — Layer 3: whole-turn wall-clock cap wrapping stream consumption

Reframe, do not duplicate. The existing `timeout=600.0` on both SDK clients is the request-establishment timeout. It is preserved as the inner-layer SDK behaviour. **On top of it**, the per-turn wrapper enforces a single authoritative wall-clock cap on the ENTIRE turn duration — including stream consumption:

```python
TURN_WALLCLOCK_CAP_SECONDS = 900  # see §7 for the 900 choice

async def run(self, ...) -> AgentResult:
    try:
        async with asyncio.timeout(TURN_WALLCLOCK_CAP_SECONDS):
            async with self._client.messages.stream(**kwargs) as stream:
                # full chunk consumption inside the timeout context
                async for chunk in stream:
                    ...
    except asyncio.TimeoutError:
        emit_protocol_violation(
            kind="turn_api_call_timeout",
            agent=self.label,
            phase=phase, round=round,
            data={
                "elapsed_seconds": TURN_WALLCLOCK_CAP_SECONDS,
                "sdk_timeout_seconds": 600.0,
                "phase_input_bytes": len(prompt),
            },
        )
        raise
```

**Why 900s and not 600s.** The SDK already has a 600s request-establishment cap. Stacking a second 600s wall-clock cap on top would race the SDK's cap and produce ambiguous failure modes ("which timeout fired first?"). 900s gives a 300s margin above the SDK cap, so a `turn_api_call_timeout` event is unambiguously a stream-consumption stall (the SDK's 600s would have fired first on a request-establishment hang) and would have raised its own typed exception caught by Layer 2.

**Why this is the authoritative cap.** The SDK's 600s bounds time-to-first-byte. This layer's 900s bounds the full turn. If a turn legitimately needs more than 900s on the data we have today (phase-1 claude this run took 428s, phase-3 claude took 303s — both well under), we are running outside reasonable parameters and should fail-fast rather than block. The cap is generous-but-not-unbounded; see §7 for revision criteria.

**Interaction with 0239's retry budget**: per Cowork's Q2 answer, a `turn_api_call_timeout` event counts as one consumed retry slot in the per-`(agent, phase, round)` budget — AND fail-fast applies: after one timeout, no retry is attempted. Re-issuing a byte-identical call that hung once is theater (the 142625 lesson); at 900s/attempt an uncapped retry would mean back-to-back 15-minute hangs. The orchestrator emits the violation, fails the turn, and routes to the run-loop tombstone.

New `ProtocolViolation` kind registered in [`src/dual_research/events/types.py`](src/dual_research/events/types.py): `"turn_api_call_timeout"`.

### 2.4 — Layer 4: verifier I2.8 (reporting)

Add `_check_i2_8` to [`src/dual_research/contract/verifier.py`](src/dual_research/contract/verifier.py), landing adjacent to the 0239-introduced I2.7 and registered in the same aggregator block.

**Invariant I2.8 — turn termination (Area 2: self-report ⇄ ledger).**

For every captured run transcript:

1. Group events by `(agent, phase, round)`.
2. For each `turn_started` event, find the next event for the same `(agent, phase, round)`.
3. If the next event is `turn_ended`, OR a `ProtocolViolation` with one of `{turn_api_call_timeout, turn_api_call_exception, empty_turn_persistent_identical_input, empty_turn_retry_cap_exceeded}`, OR a `tombstone` event — pass.
4. Otherwise (bare `turn_started` with no terminal counterpart) — emit Evidence row `(agent, phase, round): turn_started at {ts} has no terminal event (turn_ended / ProtocolViolation / tombstone)`.

Return `InvariantResult("I2.8", "reporting", ...)`. Reporting-only initially, mirroring I2.6 and I2.7. Promotion to gating is a separate small spec.

**The 200213 run violates this invariant.** Phase 4's bare `turn_started` followed by nothing else is the canonical case. After 0241 ships, the post-regen baseline for that fixture (via the spec-0240 machinery, if and when applied) would surface I2.8 = fail on this specific turn — locking the failure as a structured contract violation rather than ad-hoc human archaeology.

### 2.5 — Layer 5: unify timeout into 0239's retry budget

Extend [spec 0239's `empty_turn_retry_state` machinery in `src/dual_research/orchestrator/deep_research.py`](src/dual_research/orchestrator/deep_research.py) so that a `turn_api_call_timeout` increments the same per-`(agent, phase, round)` counter `empty_turn_detected` does. Additional rule per Cowork sign-off: on the FIRST `turn_api_call_timeout` for a given key, fail-fast — do NOT retry. The fail-fast supersedes 0239's `MAX_EMPTY_TURN_RETRIES = 2` cap for the timeout case; the cap still applies if multiple unique `empty_turn_detected` events stack up.

Single concrete rule:
- `empty_turn_detected` with byte-identical input → fail-fast (0239 Layer 1).
- `empty_turn_detected` with novel input → counter ticks, retry until cap (0239 Layer 2).
- `turn_api_call_timeout` → counter ticks, fail-fast NO RETRY (this spec). Retrying a hung call is theater.

The unified-counter approach prevents a timeout-then-empty-turn oscillation from circumventing either budget.

## 3. User stories & acceptance criteria

Not a UI spec. §3 is non-applicable per the new-feature template. Acceptance is encoded as falsifiable items in §6.

## 4. Data / Schema deltas

- **One new event kind** registered in [`src/dual_research/events/types.py`](src/dual_research/events/types.py): `TurnHeartbeat(ts, agent, phase, round, elapsed_seconds)`. Additive; no migration.
- **Two new `ProtocolViolation` kinds** registered in the same file: `"turn_api_call_exception"`, `"turn_api_call_timeout"`. Both reuse `ProtocolViolation`'s existing schema.
- **0239's `empty_turn_retry_state` dict gains no schema change** — the counter is integer-typed already; the timeout case writes to the existing `count` field.
- **No state-file fields change. No migrations.**

## 5. Out of scope

- **Promotion of I2.8 to `gating`.** Same pattern as I2.6 and I2.7 — reporting-only initially. Promotion lands in a follow-up spec once a clean reference run shows I2.8 = `pass` and we want enforcement.
- **Checkpoint-and-resume for autonomous process death.** If the next live re-run dies silently AGAIN with heartbeats stopping mid-stream and no tombstone, the failure class is H3 (OOM / SIGKILL / external reaper) and the next spec is checkpoint+resume, not more per-turn instrumentation. Cowork's debrief §9 carries that pointer. Deliberately not in scope here — this spec ships the diagnostic that DECIDES whether checkpoint+resume is needed.
- **Per-phase timeout tuning.** Cowork's Q1 answer: single global cap, YAGNI on per-phase. If data ever shows a phase-4 legit turn exceeding 900s and a phase-2 round routinely under 200s, revisit then.
- **Tunability via env var or config file.** All constants (`TURN_WALLCLOCK_CAP_SECONDS = 900`, `TURN_HEARTBEAT_INTERVAL_SECONDS = 30`) are module-level. Until a real callsite asks for runtime override, hardcoded is correct.
- **Mid-stream chunk-level timeout** (different from whole-turn cap). The whole-turn cap subsumes the chunk-level case for the failure modes we observe today; a chunk-level cap is finer-grained complexity we don't yet have evidence to justify.
- **Heartbeat sent over the wire** (e.g. to UI dashboard via websocket). Out of scope; the heartbeat is a transcript event; dashboard consumption is a separate UI spec if/when needed.

## 6. Test plan

Tests live in a new file [`tests/test_spec_0241_per_turn_liveness.py`](tests/test_spec_0241_per_turn_liveness.py). Pure stdlib + `pytest` + minimal `asyncio` test scaffolding.

### Layer 1 — heartbeat

- [ ] **`test_heartbeat_emitted_every_30s_during_long_turn`** — Spawn a fake agent whose `run()` blocks for 65 seconds before returning. The transcript receives **at least 2** `turn_heartbeat` events with monotonically increasing `elapsed_seconds` (≈30, ≈60).
- [ ] **`test_heartbeat_thread_survives_blocked_event_loop`** — Spawn a fake agent whose `run()` issues a busy CPU-bound `while True: pass` (no `await`) for 65 seconds before returning. The transcript still receives `turn_heartbeat` events (because the heartbeat is on a separate OS thread, not an asyncio task). If they don't appear, the test fails — proving the threading choice is load-bearing.
- [ ] **`test_heartbeat_stops_on_turn_ended`** — Normal-duration agent (returns in 1s). At most 0 or 1 heartbeat fires; no heartbeat fires after `turn_ended` is written. Thread is joined cleanly (no zombie threads).
- [ ] **`test_heartbeat_writes_are_atomic_under_concurrent_writers`** — Two concurrent fake turns; assert no `turn_heartbeat` events are corrupted in `transcript.jsonl` (each line parses as valid JSON).

### Layer 2 — per-turn exception capture

- [ ] **`test_turn_api_exception_emits_violation_before_propagating`** — Mock the SDK to raise `httpx.ReadTimeout("simulated")` mid-stream. Assert `transcript.jsonl` contains a `protocol_violation` event with `kind="turn_api_call_exception"`, `exception_type="ReadTimeout"`, `exception_module="httpx"`, BEFORE the exception propagates. Assert the exception still propagates (caller sees it raised).
- [ ] **`test_turn_api_exception_preserves_run_loop_tombstone`** — End-to-end: the exception propagates from the turn wrapper, the run loop's 0222 tombstone catches it and writes a tombstone event AFTER the per-turn violation. Both events are present in the transcript, in the correct order.
- [ ] **`test_basemexception_subclasses_captured`** — Parametrize over `KeyboardInterrupt`, `SystemExit`, `asyncio.CancelledError`, `MemoryError`, `httpx.ConnectError`. Each raises a `turn_api_call_exception` violation with the correct `exception_type`.

### Layer 3 — whole-turn wall-clock cap

- [ ] **`test_turn_under_cap_completes_normally`** — Fake agent returns in 5s; no `turn_api_call_timeout` violation; turn completes; `turn_ended` written.
- [ ] **`test_turn_over_cap_emits_timeout_violation`** — Fake agent that streams chunks for 5s then stalls indefinitely. With `TURN_WALLCLOCK_CAP_SECONDS` monkeypatched to 10s for the test, assert a `turn_api_call_timeout` violation fires at ~10s with `elapsed_seconds=10`, `sdk_timeout_seconds=600.0`. Assert the stream context manager exits cleanly (no resource leak).
- [ ] **`test_cap_wraps_stream_consumption_not_just_request`** — Fake agent where `messages.stream(...)` returns instantly (request established quickly) but `async for chunk` stalls. With the cap monkeypatched to 5s, assert `turn_api_call_timeout` fires. This is the specific failure mode the 200213 run hit; this test is the regression lock.
- [ ] **`test_timeout_does_not_double-fire_with_sdk_timeout`** — Verify the cap is 900s in production, well above the SDK's 600s. A simulated request-establishment hang fires the SDK's httpx timeout first (captured by Layer 2), not the wall-clock cap. The two timeouts do not race in practice.

### Layer 4 — verifier I2.8

- [ ] **`test_i2_8_negative_synthetic_bare_turn_started`** — Build a transcript with `turn_started` followed by `phase_exited` (no `turn_ended` or terminal violation). `_check_i2_8` returns `fail` with Evidence row naming the bare turn.
- [ ] **`test_i2_8_positive_synthetic_terminal_event_present`** — Build transcripts where the terminal event is each of: `turn_ended`, `protocol_violation(turn_api_call_timeout)`, `protocol_violation(turn_api_call_exception)`, `protocol_violation(empty_turn_persistent_identical_input)`, `protocol_violation(empty_turn_retry_cap_exceeded)`, `tombstone`. Each returns `pass`.
- [ ] **`test_i2_8_snapshot_on_200213_fixture`** — When the 200213 run is added to `tests/fixtures/anchor-runs/` (under a separate spec — out of scope here), the I2.8 entry will assert `fail` on the bare phase-4 `turn_started`. Pre-emptively documented in the spec; the actual snapshot test lands when the fixture lands.

### Layer 5 — retry-budget unification

- [ ] **`test_timeout_increments_0239_retry_counter`** — Issue one `turn_api_call_timeout` for `(claude, phase=4, round=1)`; assert the per-key counter at 1.
- [ ] **`test_timeout_fail_fast_no_retry`** — Issue one `turn_api_call_timeout` for `(claude, phase=4, round=1)`; assert that the orchestrator does NOT issue a retry `turn_started` for the same key (in contrast to `empty_turn_detected` which retries once before cap).
- [ ] **`test_mixed_timeout_and_empty_turn_obey_unified_cap`** — Synthetic: `empty_turn_detected` ticks counter to 1; subsequent `turn_api_call_timeout` for same key fails fast (counter to 2; no retry).

### Backwards compat + CHANGELOG

- [ ] **`uv run pytest tests/ -q` passes end-to-end.** No pre-existing test changes verdict.
- [ ] **`uv run pytest tests/test_verifier.py -q` passes.** I2.8 added as one new entry across all fixtures' `expected.json` baselines; existing verdicts unchanged.
- [ ] **CHANGELOG entry under a new `## [X.Y+1.0] — 2026-05-27` heading** (MINOR bump): `### Added` bullets for `turn_heartbeat` event, `turn_api_call_timeout` + `turn_api_call_exception` ProtocolViolation kinds, verifier I2.8; `### Changed` bullet for the per-turn API wrapper now enforcing `TURN_WALLCLOCK_CAP_SECONDS = 900`. `pyproject.toml` and `src/dual_research/__init__.py` bumped to the same X.Y+1.0.

## 7. Risks

- **Heartbeat thread leaks if `turn_started` is emitted but the agent never returns AND the wall-clock cap also fails to fire.** Mitigated: the heartbeat is started in a `try/finally` block whose `finally` joins the thread on ANY exit path (return, exception, timeout). The 900s wall-clock cap is the bound on the whole turn duration, so the `finally` joins within 900s in the worst case.
- **`asyncio.timeout(...)` (Python 3.11+) vs `asyncio.wait_for(...)` (legacy).** The spec writes `asyncio.timeout(...)`; project Python version is 3.11+ per [`pyproject.toml`](pyproject.toml) (verify at implementation time). Fallback to `asyncio.wait_for(self._inner_run(), timeout=...)` if for any reason 3.10-compat is needed.
- **900s cap is a guess.** No live phase-4 turn has ever completed in the project's run history; 900s is generous-but-finite. If a real phase-4 turn legitimately needs more (>900s of pure compute, not a stall), the cap false-kills a real run. Mitigation: the cap fail-fasts to a structured violation, not a silent crash — the next-run telemetry tells us exactly what to raise the cap to. Revision criterion: if a `turn_api_call_timeout` fires on a turn whose actual SDK behaviour (per Layer 2's exception capture + Layer 1's heartbeat trail) was a legitimate compute, not a stall, raise the cap by 50% and re-run.
- **Heartbeat output volume.** One line every 30s per active turn. A full run with ~20 turns averaging 100s each adds <70 heartbeat events to a transcript that already carries hundreds of events. Negligible.
- **Per-turn exception capture conflicts with 0222's run-loop tombstone.** Mitigation: Layer 2 emits its violation BEFORE re-raising. The run-loop tombstone still catches the re-raised exception and writes its own event. Both events are present in the transcript; the per-turn one is more specific. The test `test_turn_api_exception_preserves_run_loop_tombstone` is the executable lock against this conflict.
- **Heartbeat thread blocks process exit on a hung turn.** If the process is dying (Layer 2 captures an exception, the run loop is exiting), the heartbeat thread's `finally`-join must not block exit. Mitigated by setting the thread as `daemon=True` — daemon threads do not block interpreter shutdown.
- **The 200213 silent death may be H3 (OOM/SIGKILL), in which case Layers 1–3 do not prevent the next death** (SIGKILL is uncatchable; OS-level reapers leave no trace inside the process). Mitigation: this spec is the *diagnostic* that decides whether the next death is H2 (now legible via tombstone or violation) or H3 (heartbeats stop with no terminal event). If H3 is confirmed on the next re-run, the next spec is checkpoint+resume (§5 already names this). Shipping this spec is necessary regardless — we cannot diagnose H3 without ruling H2 out first.
- **Revert path.** All artefacts are additive: a new event kind, two new violation kinds, a new verifier check, a per-turn wrapper. Revert is a single `git revert` of this spec's PR; no migration to unwind. If post-merge surveillance shows the heartbeat thread or wall-clock cap misbehaves, revert and re-design before re-shipping.
