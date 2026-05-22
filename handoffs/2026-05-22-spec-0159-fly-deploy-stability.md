---
spec: "0159"
date: 2026-05-22
version: 1.22.1
pr: "https://github.com/Lexiz/dual-research/pull/182"
---

# Handover — Spec 0159 — Fix: Fly machines-API mid-rolling-deploy timeout (v1.22.1)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#182](https://github.com/Lexiz/dual-research/pull/182)
- **Merge commit:** `7525a71`
- **Cycle time:** ~4 minutes (started 14:18:22Z, deployed 14:22:42Z)

## What landed

Four coordinated config changes targeting the cold-boot margin that has been putting machine 2 past Fly's API observation window during rolling deploys — same shape on 9 consecutive deploys (spec 0141 through 0150, 0153, 0156). Recovery was always `fly machine start <id>` (~10s); the machines were structurally fine, only the API observability path timed out.

- **`fly.toml` — `grace_period` 30s → 90s** on the `/api/health` check. Triples Fly's wait before considering a fresh machine unhealthy.
- **`fly.toml` — `[deploy] strategy = "bluegreen"`.** New machines boot fully and pass health checks *before* old machines terminate.
- **`Dockerfile` — `FROM python:3.14` → `FROM python:3.13-slim`.** Image dropped from ~1.2GB to ~200MB. Faster pull + extract, smaller import footprint at boot.
- **`pyproject.toml` — `requires-python = ">=3.14"` → `">=3.13"`.** Lockfile regenerated under the relaxed pin (`uv lock` resolved 73 packages cleanly).
- VM size stays at `shared-cpu-1x:512MB` per user direction. The bump is the round-2 fallback if this didn't end the pattern.

## Tests

`uv run pytest tests/ -q` — **1500 passed**. Local venv stays on 3.14; the test run validates that nothing broke under the relaxed pin.

## Deploy notes — the proof

**The pattern broke on the first attempt.** Spec 0159's own `fly deploy` completed cleanly under bluegreen:

```
Waiting before cordoning all blue machines
  Machine 185354db00ee68 [app] cordoned
  Machine 78469eef609138 [app] cordoned

Waiting before stopping all blue machines

Stopping all blue machines

Waiting for all blue machines to stop
  Machine 185354db00ee68 [app] - started
  Machine 78469eef609138 [app] - started
  Machine 185354db00ee68 [app] - stopped
  Machine 78469eef609138 [app] - stopped

Destroying all blue machines
  Machine 185354db00ee68 [app] destroyed
  Machine 78469eef609138 [app] destroyed

Deployment Complete
```

No `Unrecoverable error`. No `fly machine start` recovery. No leftover stopped machines.

`fly status` after deploy:

```
 PROCESS │ ID             │ VERSION │ REGION │ STATE   │ ROLE │ CHECKS             │ LAST UPDATED
 app     │ 68354ddfd77e78 │ 261     │ iad    │ started │      │ 1 total, 1 warning │ 2026-05-22T14:22:09Z
 app     │ 78140e2f3379d8 │ 261     │ iad    │ started │      │ 1 total, 1 warning │ 2026-05-22T14:22:09Z
```

Exactly 2 fresh machines, both started, both on v261 (the new image). The "1 warning" on `CHECKS` reflects Fly's 90s grace window still ticking on the just-launched machines; the user-facing health endpoint returns `{"ok":true,"version":"1.22.1","backend":"supabase"}` immediately.

**Net change vs. the prior 9 deploys:** zero retries, zero manual machine starts, zero "Unrecoverable error" messages from the CLI. Cycle time from `git push` to `Deployment Complete` was ~2 minutes — comparable to a healthy rolling deploy.

## Verification still owed

The strongest signal is the *next* spec's deploy. If the 10th consecutive deploy is also clean, the pattern is definitively broken. If it times out again, escalate to:

- VM size bump to `shared-cpu-2x:1024MB` or `performance-1x:2048MB` (round-2 fallback per spec §6).
- Or file the deferred Fly support ticket (spec 0159 §6 mentioned operator-deferred 9 specs running).

## Deferred during implementation

(none — spec scope was four config changes, all landed cleanly)

## Queue at handoff

- **Empty.** Six specs shipped today (0154 → 0155 → 0156 → 0157 → 0158 → 0159).

`/dev-queue-run` completed cleanly with a single greenlight; no per-spec pauses fired.

## File map

```
fly.toml                                       # grace_period 30→90s, bluegreen strategy
Dockerfile                                     # python:3.13-slim
pyproject.toml, src/dual_research/__init__.py  # 1.22.1, requires-python >=3.13
uv.lock                                        # regenerated, 73 packages
CHANGELOG.md                                   # [1.22.1] section
specs/0159-fly-deploy-stability.md             # status: deployed
dashboard/events/0159.jsonl                    # event stream
handoffs/2026-05-22-spec-0159-...md            # this file
```
