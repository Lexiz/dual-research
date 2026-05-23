---
spec: "0192"
date: 2026-05-23
version: 1.38.0
pr: "https://github.com/Lexiz/dual-research/pull/221"
---

# Spec 0192 — L-spec checkpoint trigger predicate — shipped

Fills in the heuristic that spec 0186 §2.2 explicitly deferred. The L-spec
checkpoint cadence (per top-level `## 2.N`) now has a deterministic
trigger predicate: wall-clock session age ≥ 30 minutes. No token-counter
infra, no Claude-internal probes — exactly the "simple coarse signal"
spec 0186 §5 prescribed.

## What landed

- **[scripts/spec_lifecycle/checkpoint.py:154](../scripts/spec_lifecycle/checkpoint.py)** — new helper `should_checkpoint_now(session_started_at, *, now=None, threshold=DEFAULT_SESSION_AGE_THRESHOLD) -> bool`. Pure, dependency-free, deterministically testable via the `now=` injection. The `>=` boundary means True at exactly the threshold value (matters for the boundary test). New module-level constant `DEFAULT_SESSION_AGE_THRESHOLD = timedelta(minutes=30)`. The module imports `datetime`, `timedelta`, `timezone` from `datetime` (added at the top of the file).
- **[tests/spec_lifecycle/test_checkpoint.py](../tests/spec_lifecycle/test_checkpoint.py)** — 6 new tests: threshold-not-met, threshold-met, exact-boundary, custom threshold, `now=` injection overrides wall clock, default constant guard. Each constructs frozen `datetime` instances so the helper's behaviour is unit-testable.
- **[~/.claude/skills/dev-next/SKILL.md](~/.claude/skills/dev-next/SKILL.md) step 15-CP** — rewritten to call the predicate instead of eyeballing "context pressure". The new prose includes the `uv run python -c "..."` invocation pattern (with `session_started_at` read from either spec frontmatter or the most recent `resume_started` event). Skill file is on the user's machine, not in this PR's diff (same pattern as spec 0191 / 0194).
- **CHANGELOG / version** — `1.37.3` → `1.38.0` (MINOR per new-feature type — visible behavior change for L-spec drains, even though no L-specs exist yet).

Full suite: 1716 passed (was 1710).

## Live smoke

```
>>> from datetime import datetime, timedelta, timezone
>>> from scripts.spec_lifecycle.checkpoint import should_checkpoint_now, DEFAULT_SESSION_AGE_THRESHOLD
>>> DEFAULT_SESSION_AGE_THRESHOLD
datetime.timedelta(seconds=1800)  # 30 minutes
>>> now = datetime.now(timezone.utc)
>>> should_checkpoint_now(now - timedelta(minutes=10), now=now)
False
>>> should_checkpoint_now(now - timedelta(minutes=35), now=now)
True
```

The dashboard renderer (post-deploy) doesn't surface this predicate
directly — it'll only show up in real-world L-spec drain logs once the
first L spec ships and checkpoints.

## Deploy notes

- `fly deploy` hit the "machine not found" lease error variant
  ([memory: project-fly-lease-drift-recovery](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md)).
  New v504 greens came up healthy alongside two stale v502 blues; fly's
  orchestrator didn't tag the blues `safe_to_destroy` so the
  `sweep_stale_blues.sh` filter wouldn't catch them. Manual
  `fly machine destroy --force <v502-machine-id>` on both zombies
  restored a clean 2-machine cluster.
- Image: `dual-research-alex:deployment-01KSATBKNEDBWMZZAGNV6P6VF8` on two v504 machines.

## What this DOES NOT do

- **Calibrate the 30-minute default.** First real L-spec drain will produce
  evidence; tuning is a one-line follow-up that doesn't touch the helper
  signature.
- **Add per-spec threshold overrides via frontmatter.** Out of scope per
  spec §5; every L spec uses the default today.
- **Token-counter infra.** Banned by spec 0186 §5; reaffirmed here.
- **Read `session_started_at` for the caller.** The helper takes a parsed
  `datetime`; the skill step is responsible for parsing the frontmatter
  field or the `resume_started` event timestamp. Keeping the helper pure
  makes it trivially testable.
- **Test the skill body's invocation pattern.** The skill text is prose,
  not Python; testing it would require a fragile regex over `SKILL.md`.
  The 6 helper unit tests cover the predicate; the skill step is exercised
  by the next real L-spec drain.

## Rebase note

PR #221's first squash-merge attempt failed with `DIRTY` mergeable state,
same conflict pattern as every prior spec in this drain (the
`--push-to-main` event commits advance main while the branch is open).
Resolved by rebasing onto `origin/main`, keeping both sides' append-only
additions on `dashboard/events/0192.jsonl`, force-with-lease-pushing,
then admin-squashing. Spec 0191's supervisor extraction is the
groundwork that lets a future spec batch event emission and eliminate
this conflict class entirely — that batching is not done here.

## Stray-tree note

The branch had unstaged modifications under `prototypes/critique-iteration/`
when staging this PR — leftover canvas-skill sandbox state, not related
to this spec. Left unstaged per
[memory: feedback_dirty_tree_not_intentional](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/feedback_dirty_tree_not_intentional.md).
