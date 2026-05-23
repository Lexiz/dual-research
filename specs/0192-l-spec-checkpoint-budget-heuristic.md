---
kind: dev
spec: "0192"
slug: l-spec-checkpoint-budget-heuristic
title: L-spec checkpoint budget heuristic — wall-clock session age trigger
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
queue_position: 6
depends_on: ["0186"]
complexity: S
created: 2026-05-23
queued_at: "2026-05-23T00:00:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: deferred-from-0186
promoted_from_draft: ""
---

# Spec 0192 — L-spec checkpoint budget heuristic — wall-clock session age trigger

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** 0186
> **Bump:** MINOR — new mechanism (`should_checkpoint_now` helper + skill-step wiring) that decides when the per-`## 2.N` cadence actually halts the session. Without it the cadence is dormant.
> **Evidence:** Spec 0186 handoff `## Deferred during implementation` second bullet — [handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:61](handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:61): *"spec 0186 §5 ('Out of scope') explicitly says 'no token-counter infra' and 'the L-spec checkpoint trigger uses a simple heuristic'. The current spec body shipped the cadence (per-`## 2.N`) and the artefact shape, but does not specify what the heuristic should be — 'session age' or 'coarse signal' are both gestured at."* This spec picks **wall-clock session age** as the coarse signal and wires it into [scripts/spec_lifecycle/checkpoint.py:1](scripts/spec_lifecycle/checkpoint.py) so the per-`## 2.N` step in `~/.claude/skills/dev-next/SKILL.md` step 15-CP has something falsifiable to ask.

---

## 1. Context

Spec 0186 §2.2 (cited at [specs/0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:67](specs/0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:67)) shipped the L-spec checkpoint **cadence** (per top-level `## 2.N` subsection) and the **artefact** (the `kind: in-spec-checkpoint` handoff written by [scripts/spec_lifecycle/checkpoint.py:76](scripts/spec_lifecycle/checkpoint.py) consumers in `~/.claude/skills/dev-next/SKILL.md` step 15-CP). What it explicitly punted on, per [specs/0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:142](specs/0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:142): *"The L-spec checkpoint trigger uses a simple heuristic: 'after each completed `## 2.N`, decide whether to halt based on session age or a coarse signal.' No new token-counter infra."*

So today the checkpoint cadence exists but the trigger predicate is whatever the agent eyeballs in the moment. That's fine for the first L-spec to test the round-trip, but it's not a contract — there's nothing for the skill body to point at when it asks "should I halt now?" The deferral text in the spec 0186 handoff says the first real L-spec drain will be the calibration moment; this spec proposes a deterministic starting heuristic so that calibration has a fixed point to evaluate against, instead of a moving target across implementer instincts.

The token-counter ban from spec 0186 §5 still holds — no new infra that reads context window utilisation. The simplest coarse signal that survives that constraint is **wall-clock session age**: how long ago did this session start. That number is cheap to compute, has no dependency on Claude internals, and is exactly the kind of "coarse signal" the deferral language gestures at.

## 2. Proposed change

Add one helper to [scripts/spec_lifecycle/checkpoint.py:1](scripts/spec_lifecycle/checkpoint.py) and wire its result into the skill step that already gates the checkpoint write.

### 2.1 New helper: `should_checkpoint_now`

In [scripts/spec_lifecycle/checkpoint.py:154](scripts/spec_lifecycle/checkpoint.py) (after `build_headless_command`), add:

```python
from datetime import datetime, timezone, timedelta

# Spec 0192 §2 — first calibrated threshold. Re-evaluate after the first
# real L-spec drain produces evidence of where the agent actually starts
# degrading. Tune up if drains routinely fit in one session; tune down
# if the agent reports compaction warnings before this fires.
DEFAULT_SESSION_AGE_THRESHOLD = timedelta(minutes=30)


def should_checkpoint_now(
    session_started_at: datetime,
    *,
    now: datetime | None = None,
    threshold: timedelta = DEFAULT_SESSION_AGE_THRESHOLD,
) -> bool:
    """Return True when the L-spec session has been running long enough
    that the per-``## 2.N`` checkpoint cadence should halt cleanly.

    The signal is wall-clock session age. No token-counter dependency,
    no Claude-internal probe. ``session_started_at`` is the timestamp the
    session began (today: the ``started_at`` frontmatter field of the spec
    currently being implemented, or — under resume mode — the ``ts`` of
    the most recent ``resume_started`` event in the spec's sidecar log).

    Spec 0186 §7 calls out that this heuristic may be wrong in either
    direction. Tuning happens in a follow-up if real drains show the
    threshold mis-firing — the predicate signature is stable, only the
    default changes.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    return (now - session_started_at) >= threshold
```

The function is pure, dependency-free, and unit-testable with frozen timestamps.

### 2.2 Wire into the skill body

Edit `~/.claude/skills/dev-next/SKILL.md` step 15-CP (the L-spec checkpoint cadence cited in the spec 0186 handoff at [handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:23](handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:23)). Today the prose says "After each `## 2.N`, assess coarse context pressure; if past threshold, write the checkpoint handoff." Replace the "assess coarse context pressure" phrase with a single bullet:

> After each completed `## 2.N`, call `should_checkpoint_now(session_started_at)` from [scripts/spec_lifecycle/checkpoint.py:154](scripts/spec_lifecycle/checkpoint.py). If True, write the checkpoint handoff, commit + push the branch, emit `checkpoint_written`, leave status at `in_progress`, exit `RC == 0`. The default threshold is 30 minutes of wall-clock session age; the helper accepts a `threshold=` override for testing or one-off tuning.

`session_started_at` is read from the spec's frontmatter `started_at` field (set at step 11 of `/dev-next` per the in-progress flip) — or, under resume mode, the timestamp of the most recent `resume_started` event in `dashboard/events/NNNN.jsonl` (read via [scripts/spec_lifecycle/append_event.py:221](scripts/spec_lifecycle/append_event.py) `read_events`).

### 2.3 What does NOT change

- The cadence (per `## 2.N`) is unchanged. This spec only fills in the trigger predicate that was previously hand-waved.
- The checkpoint handoff format ([scripts/spec_lifecycle/checkpoint.py:56](scripts/spec_lifecycle/checkpoint.py) `CheckpointHandoff`) is unchanged.
- `/dev-queue-run` supervisor model is untouched.
- M/S specs continue to be untouched by the cadence — the dormancy gate at `complexity: L` in the skill body is the same.

## 3. UX / Behavior

The user's experience changes only for L-spec drains. Before this spec, the implementer eyeballs context pressure and decides ad-hoc when to checkpoint. After this spec, the implementer calls `should_checkpoint_now` after each `## 2.N` and halts when it returns True. The threshold is 30 minutes of wall-clock session age, chosen as a deterministic starting point that's coarse enough to never fire on small L specs (which finish in under 10 minutes) but conservative enough to catch the first session-burn case (where the agent has already been editing files for 30+ minutes).

User-visible artifacts unchanged: same checkpoint handoff filename, same resume path on the next iteration, same dashboard event names (`checkpoint_written`, `resume_started`).

## 4. Data / Schema deltas

None. No new frontmatter fields, no new event kinds, no DB changes. The new helper reads existing data (`started_at`, event log) and returns a bool.

## 5. Out of scope

- **Token-counter infra.** Spec 0186 §5 banned it; this spec respects that. Wall-clock age is the entire signal.
- **Calibrating the 30-minute default.** First-real-drain feedback determines whether this is too aggressive or too lax. Tuning is a separate (one-line-change) spec; the predicate signature is stable so retuning never touches the skill body.
- **Per-spec threshold overrides via frontmatter.** Could be added later (e.g. `checkpoint_threshold_minutes:` on a per-spec basis) but every L spec uses the default today.
- **Smarter signals.** Per-subsection token estimate, edit count, file count, test runtime — all plausible richer signals, all out of scope here. The deferred-spec text says "session age or coarse signal"; this spec picks session age and ships.
- **Changes to M/S specs.** The cadence dormancy gate (`complexity: L`) is unchanged; M and S specs still ship in one session.

## 6. Test plan

- [ ] **Threshold-not-met returns False.** Construct `session_started_at = now - 10 minutes`. Assert `should_checkpoint_now` returns False with the default threshold.
- [ ] **Threshold-met returns True.** Construct `session_started_at = now - 35 minutes`. Assert `should_checkpoint_now` returns True with the default threshold.
- [ ] **Exact-threshold boundary returns True.** Construct `session_started_at = now - 30 minutes` exactly. The `>=` in the predicate body means True at the boundary. Assert.
- [ ] **Custom threshold respected.** Pass `threshold=timedelta(minutes=5)`. Assert a 6-minute-old session returns True; a 4-minute-old session returns False.
- [ ] **`now` injection works.** Pass `now=fixed_dt` to the helper. Assert the result reflects the fixed offset, not real wall clock. (This is what makes the helper deterministically testable.)
- [ ] **Helper signature stable.** Importing `should_checkpoint_now` and `DEFAULT_SESSION_AGE_THRESHOLD` from `scripts.spec_lifecycle.checkpoint` does not raise. The full suite `uv run pytest tests/ -q` stays green.

## 7. Risks

- **Threshold is wrong.** 30 minutes may be too aggressive (most L specs would never trigger; the cadence stays dormant in practice) or too lax (sessions are already degraded by 30 minutes for spec sizes that exhaust context fast). *Mitigation:* the helper accepts a `threshold=` override, so tuning is a one-liner without touching callers. The first L-spec drain after this lands is the calibration moment, exactly as spec 0186 said it would be.
- **`started_at` may be stale across resumes.** Under resume mode the original `started_at` reflects the *first* iteration's start, not the current iteration. *Mitigation:* the §2.2 wiring specifies that under resume mode the helper consumes the most recent `resume_started` event timestamp instead — that's the actual age of the *current* session. The event lookup uses [scripts/spec_lifecycle/append_event.py:221](scripts/spec_lifecycle/append_event.py) `read_events`, no new infra.
- **Wall-clock isn't a perfect proxy for context pressure.** A session that mostly waits on the user / tool calls might be 30+ minutes old without any context burn. *Acceptance:* spec 0186 explicitly took this risk — "simple heuristic" is the contract. Smarter signals are out of scope until the simple one demonstrably fails.
- **Clock skew between session start and now.** `datetime.now(timezone.utc)` and `started_at` (already stored as UTC ISO strings in the frontmatter and event logs) are both UTC. No skew expected. *Mitigation:* the helper signature requires `datetime` objects, not strings — callers parse with `datetime.fromisoformat`, which raises loudly on malformed input rather than silently returning a wrong delta.
