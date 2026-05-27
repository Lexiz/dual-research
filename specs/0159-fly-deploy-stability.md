---
kind: dev
spec: "0159"
slug: fly-deploy-stability
title: "Fix: Fly machines-API mid-rolling-deploy timeout (9-in-a-row)"
type: bug
label: bug
version_bump: PATCH
target_version: 1.22.1
status: deployed
depends_on: []
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T14:05:00Z"
started_at: "2026-05-22T14:18:22Z"
merged_at: "2026-05-22T14:20:28Z"
deployed_at: "2026-05-22T14:22:42Z"
pr: "https://github.com/Lexiz/dual-research/pull/182"
handover: "handoffs/2026-05-22-spec-0159-fly-deploy-stability.md"
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0159 — Fix: Fly machines-API mid-rolling-deploy timeout (9-in-a-row)

> **Type:** bug  |  **Severity:** P1  |  **Affects:** `dual-research-alex` Fly app, every deploy since spec 0140
> **Bump:** PATCH — bug fix
> **Evidence:** Handoffs `2026-05-22-spec-0141…0150,0153,0156`; audit row D24; live `fly status` at 2026-05-22T13:56Z showed machine `78469eef609138` stuck in `stopped` state from v252 deploy with this exact flake.

---

## 1. Reproduction

**Environment:** `dual-research-alex` Fly app, IAD region, 2× `shared-cpu-1x:512MB` machines, rolling-deploy strategy (Fly default).

**Steps:**
1. Run `fly deploy` from `/Users/alexlisitzky/dual-research/` against a clean main.
2. Fly builds the image, pushes to registry, starts the rolling update.
3. Machine 1 reboots into the new image, passes the `/api/health` check on first try.
4. Machine 2 reboots; Fly's `api.machines.dev` times out waiting on its health check before observing it healthy.
5. CLI reports "Unrecoverable error"; the release is marked `failed`; machine 2 is left in state `stopped`.

**Expected:** `fly deploy` completes cleanly; both machines reach `started`+`1/1 health passing` without manual intervention.

**Actual:** 9 consecutive deploys (specs 0140 through 0150, 0153, 0156) hit the same shape. Recovery is always `fly machine start <id>` (~10s) — the machine is structurally fine; only the API observability path times out. Live confirmation in `handoffs/2026-05-22-spec-0156-dashboard-liveness-improvements.md` and again at queue time today.

## 2. Root cause hypothesis

Cold-boot time exceeds the 30s `grace_period` on the `shared-cpu-1x:512MB` tier, on the wrong side of Fly's API observation window during rolling deploys.

Three contributing factors:

- **Image is huge.** [Dockerfile:8-12](Dockerfile) pins `FROM python:3.14` (the full image, not `-slim`) because the comment cites `pyiceberg` having no Python 3.14 wheel as of writing and needing gcc to build from source. The resulting image is ~1.2GB+. Pull + extract on a tiny VM is slow.
- **Heavy dependency graph at import time.** `supabase>=2.9`, `pyiceberg` (transitive), `anthropic>=0.102.0`, `openai>=2.36.0`, `fastapi`, `uvicorn[standard]` — non-trivial import cost during `dual-research serve` boot ([Dockerfile:32](Dockerfile) `CMD`).
- **Tight grace_period.** [fly.toml:30-35](fly.toml) sets `grace_period = "30s"` on the health check. Combined with the slow boot and `shared-cpu-1x`'s shared-CPU jitter, machine 2 routinely lands past the 30s mark — the moment Fly's machines API gives up.

There is also a real Fly control-plane flakiness component (live `fly status` at queue time returned `Metrics token unavailable: ... context canceled`), but the *consistent* trigger across 9 deploys is the boot-margin problem.

## 3. Fix

Four config changes plus a clean machine sweep. All bundled into this one spec per user direction ("combine everything in one flow to try first").

### 3.1 `fly.toml` — grace_period bump

```toml
[[http_service.checks]]
  interval = "30s"
  timeout = "5s"
  grace_period = "90s"  # was "30s"
  method = "GET"
  path = "/api/health"
```

Triples the window Fly waits before considering a fresh machine unhealthy. No runtime cost (only affects first-boot observability).

### 3.2 `fly.toml` — bluegreen deploy strategy

Add a top-level block:

```toml
[deploy]
  strategy = "bluegreen"
```

New machines boot **fully** and pass health checks *before* old machines terminate. Far more forgiving than rolling on 2 machines — a slow boot can't strand a half-rolled deploy because the old machines stay up until the new ones are observably healthy.

### 3.3 `Dockerfile` — pin Python 3.13 + use slim image

```Dockerfile
FROM python:3.13-slim
```

…replacing the current `FROM python:3.14`. Drop the multi-line comment block at [Dockerfile:8-11](Dockerfile) about pyiceberg's missing 3.14 wheel — irrelevant under 3.13. Image size drops from ~1.2GB → ~200MB. Faster pull, faster extract, smaller memory footprint at boot.

Slim drops `gcc` and other build tooling. If `uv sync --frozen --no-dev` fails because some transitive dep needs to build from source on 3.13-slim, add a minimal `apt-get install -y --no-install-recommends gcc` before `RUN uv sync` (and clean apt lists in the same RUN to keep the layer small). Try without first.

### 3.4 `pyproject.toml` — relax Python pin

```toml
requires-python = ">=3.13"
```

…was `>=3.14`. Regenerate the lockfile: `uv lock --upgrade-package python` (or equivalently `uv lock` after editing). Commit the updated `uv.lock`.

### 3.5 Clean machine sweep after deploy lands

`bluegreen` will replace both machines as part of the strategy, but make it explicit: after `fly deploy` reports success, run `fly status -a dual-research-alex` and verify there are no `stopped` leftover machines. If any exist, `fly machine destroy <id> --force -a dual-research-alex`. Goal: post-deploy state is exactly 2 fresh machines, both `started`, both `1/1` health passing, both on the v1.22.x image.

### 3.6 Keep VM size at `shared-cpu-1x:512MB`

Per user direction ("try first…then if it's still an issue, consider maybe bumping up machines"). The VM bump is the next-round fallback, not this spec.

## 4. Regression-prevention test

This is infra config — no pytest assertion captures the symptom. The regression test is **the next deploy cycle itself.**

- [ ] **Test:** the `/dev-next` deploy step for spec 0160 (whatever lands next on the queue) completes cleanly on first attempt — no `Unrecoverable error`, no `fly machine start` recovery needed, both machines reach `1/1` health passing without manual intervention.
- [ ] **Test:** the spec 0159 deploy itself (the one shipping this fix) completes cleanly under bluegreen. The first-deploy-with-bluegreen will *use the old `grace_period = 30s` machines* while the new ones boot — the old machines stay up the whole time, so even if Fly's API flakes, the user-facing service does not degrade.
- [ ] **Documentation test:** the next handoff (spec 0160) explicitly states "no machines-API timeout" in its deploy-status section, breaking the 0141→0156 pattern. If the next handoff says "10th consecutive timeout," this spec failed and we escalate to the VM bump.

## 5. Blast radius

- **`fly.toml`** — change is config-only; reverts via `git revert`. No code path affected.
- **`Dockerfile` Python pin** — needs every transitive dep to have a 3.13 wheel. Spot-check of `pyproject.toml` direct deps (`anthropic>=0.102.0`, `fastapi>=0.115`, `httpx>=0.28.1`, `openai>=2.36.0`, `sse-starlette>=2.1`, `supabase>=2.9`, `uvicorn[standard]>=0.32`, `watchfiles>=0.24`, `pytest>=9.0.3`, `pytest-asyncio>=1.3.0`) — all of these have shipped 3.13 wheels for months. pyiceberg (transitive via supabase) has had a 3.13 wheel since its v0.7 line. `uv sync` failure on the resolver step would surface this in `/dev-next`'s implement phase, before deploy — safe to find out at build time.
- **bluegreen during deploy** — briefly runs 3 machines instead of 2 (~60s overlap window). Within Fly's machine quotas for `personal` org. No user-facing degradation; in fact strictly better than rolling because old machines stay up until new ones are observably healthy.
- **Clean machine sweep** — destroys at most 2 machines that are already stopped/replaced post-bluegreen. Bluegreen-replaced machines are already drained, so destroy is safe.

## 6. Out of scope

User explicitly deferred the following ("if it's still an issue, consider maybe bumping up machines or whatever"):

- **VM size bump** — `shared-cpu-1x:512MB` → `shared-cpu-2x:1024MB` or `performance-1x:2048MB`. Saved for the round-2 fallback if this spec doesn't end the timeout pattern.
- **Provider migration** — Cloud Run / Railway / Render / DigitalOcean App Platform. Same round-2 fallback path.
- **Multi-stage Dockerfile refactor** — splitting build stage (gcc, compilation) from runtime stage (slim). Try the simple slim+3.13 swap first; if some dep still needs gcc, escalate to multi-stage in a follow-up.
- **Filing the D24 Fly support ticket.** Operator-deferred 9 specs running; if this spec ends the pattern, ticket becomes moot. If not, ticket becomes urgent.
- **The `Metrics token unavailable` GraphQL error** observed in `fly status` at queue time. Likely orthogonal control-plane noise; track only if it recurs after this deploy.

## 7. Risks

- **Python 3.13 dep-resolution failure.** Low probability per the wheel spot-check, but `uv sync --frozen --no-dev` could fail in the build stage. Mitigation: surfaces immediately at build time (no production exposure); fix is either to allow source builds (add `gcc` to the slim image as a follow-up edit in this same spec's implementation pass) or fall back to `python:3.13` (non-slim) which already has the toolchain.
- **bluegreen + secrets.** Fly secrets (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `UI_BASIC_AUTH_PASSWORD`) propagate to the new machines automatically — same mechanism rolling uses. No risk.
- **bluegreen during this spec's own deploy.** First bluegreen attempt happens on machines that are still on the old config. Bluegreen itself works regardless of the *old* machines' config — it's the new machines' boot path that matters, and they boot under the new `fly.toml`+`Dockerfile`. Safe.
- **grace_period:90s masking real boot failures.** If a future deploy genuinely breaks (e.g. import error), Fly waits 3× longer to surface that. Acceptable trade — first-boot import errors will still show in `fly logs` immediately; the deploy will fail at the 90s mark instead of the 30s mark. Minor UX cost in the genuine-failure case for major UX win in the 9-in-a-row-timeout case.
- **Verification window.** The "did this work" signal is the *next* spec's deploy, not this one. This spec's own deploy still runs under bluegreen so it's already protected, but the user-visible "yes the pattern broke" verdict is one spec away.
