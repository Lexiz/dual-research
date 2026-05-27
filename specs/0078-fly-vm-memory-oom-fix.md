---
spec: 0078
title: Fly VM memory bump to fix UI-server OOM-on-boot
label: bug
version-bump: PATCH
status: merged
target-version: 0.69.2
created: 2026-05-18
pr: "https://github.com/Lexiz/dual-research/pull/78"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0078 — Fly VM memory bump to fix UI-server OOM-on-boot

## Context

The hosted UI at `https://dual-research-alex.fly.dev` started returning
HTTP 502/503 across all `/api/*` requests. From a user's perspective the
list and detail pages render their shell from cached static assets, but
every API call fails — including the active run-detail page, which
shows "Could not load run · Error: HTTP 503".

Symptoms in the Fly machine logs followed an unhelpful pattern: the
init process printed `Starting init`, `Preparing to run uv run
dual-research serve --host 0.0.0.0 --port 8080`, then `uv` resolved
deps (`Built dual-research`, `Installed 5 packages`), then **complete
silence** — no startup banner, no uvicorn output, no traceback. Health
check on port 8080 stays critical, Fly's init restarts the process,
loop repeats.

`PYTHONUNBUFFERED=1` is set in the Dockerfile, so this is not a stdio
buffering artefact. After enabling lower-level kernel logs the actual
cause showed up:

```
[110.91s] Out of memory: Killed process 662 (dual-research)
          total-vm:290652kB, anon-rss:142608kB
INFO Main child exited normally with code: 137
INFO Process appears to have been OOM killed!
```

Exit 137 = 128 + SIGKILL (9) = the kernel OOM-killer fired. The Python
3.14 import chain pulls in `fastapi`, `uvicorn`, `sse_starlette`,
`watchfiles`, `supabase-py` (which transitively requires `pyiceberg`),
`starlette`, plus our own modules. Total virtual memory at boot is
**~290 MB**, but the machine is provisioned at **256 MB**
(`shared-cpu-1x:256MB` in `fly.toml`). The process dies before it can
print anything to stderr, which is why the failure looks like a hang.

This is recent — earlier runs from May 15–16 deployed and served fine.
The most likely trigger is a transitive dependency growing slightly (a
new minor of `supabase-py` or `pyiceberg`) and pushing peak import
memory just over the threshold. We have not pinned exact versions of
the transitive deps; investigation here is out of scope for this hotfix
(see "Open questions").

## Proposed change

One file, two knobs.

**`fly.toml`** — bump the VM memory from 256 MB to 512 MB and widen the
health-check grace period:

```diff
 [[vm]]
   size = "shared-cpu-1x"
-  memory = "256mb"
+  memory = "512mb"

 [[http_service.checks]]
   interval = "30s"
   timeout = "5s"
-  grace_period = "10s"
+  grace_period = "30s"
   method = "GET"
   path = "/api/health"
```

**Why these values:**

- **512 MB** is the next standard `shared-cpu-1x` tier on Fly. It doubles
  headroom on the documented import-time peak (~290 MB virt / ~143 MB
  RSS) and leaves room for the request-handling working set, the
  in-memory auth cache (60 s TTL, small), and SSE connection state. We
  do **not** need a larger CPU shape; this is a memory issue, not a
  compute issue.
- **30 s grace_period** acknowledges that Python 3.14 + the supabase
  client chain takes longer than 10 s to import + bind on a shared CPU.
  The previous 10 s window meant the health check could fail before the
  app even finished starting, even if the OOM hadn't fired. With the
  memory headroom now in place, this is the second source of
  false-negative health failures we want to remove.

Both changes ship in the same deploy. Roll forward only — no code
changes, no schema migration.

## Out of scope

- **Trimming the import footprint.** The right long-term fix is to
  avoid pulling `pyiceberg` (which `supabase-py` drags in for storage
  features we don't use) into the read-path server. That's a larger
  refactor — lazy-import on first push, or split the server image from
  the orchestrator image — and belongs in its own spec.
- **Pinning transitive deps.** We can lock down `supabase` and
  `pyiceberg` versions in `pyproject.toml` to defend against future
  drift, but that's a hardening pass, not part of this hotfix.
- **Switching off the Python 3.14 base image.** Python 3.13 has a
  smaller startup footprint but the Dockerfile comment notes pyiceberg
  doesn't yet ship a 3.14 wheel, which led to the full image choice.
  Out of scope until the pyiceberg dependency itself is questioned.
- **Auto-stop / cold-start behaviour.** `auto_stop_machines = "stop"`
  with `min_machines_running = 0` means each cold start still pays the
  python-import cost. A separate decision; see Open questions.
- **Modal-load latency / per-request caching.** Separate problem (see
  the follow-up spec for input-bundle perf). Not bundled here because
  this hotfix is config-only and rolls forward in seconds; the perf
  spec touches server code and warrants its own review pass.
- **Local UI server (`dual-research serve` on the developer's laptop).
  ** This spec only touches the Fly deployment.

## Test plan

- [ ] **Deploy:** `fly deploy` from this branch.
- [ ] **Health check passes:** after deploy completes, run
      `flyctl status -a dual-research-alex` and confirm both machines
      report `CHECKS: 1 total, 1 passing` within the new 30 s grace
      window.
- [ ] **No OOM in logs:** `flyctl logs -a dual-research-alex --no-tail
      | grep -iE 'out of memory|killed|sigkill|code: 137'` returns no
      hits for the deployment window. Re-check after 30 minutes of
      normal traffic to catch later OOMs caused by request-handling
      allocations.
- [ ] **End-to-end UI:** open
      `https://dual-research-alex.fly.dev/#/runs/<known-run-id>` and
      confirm the run-list, run-detail, and SSE stream all return 200s.
      Test against the `20260518-083618-backend-language-choice` run
      that motivated this spec.
- [ ] **Auth still gated:** unauthenticated curl to
      `/api/runs` returns 401 (middleware still attached). curl to
      `/api/health` and `/api/config` returns 200 (ungated paths).

No new automated tests — this is a config bump. We rely on the Fly
deploy gate and the manual verification above.

## Risks

- **Cost.** 512 MB shared-cpu-1x is roughly 2x the unit price of
  256 MB but still well under $5/month with `auto_stop_machines =
  "stop"` and two-machine HA. Acceptable.
- **The bump masks rather than fixes the underlying bloat.** We're
  paying for memory we wouldn't need if the import graph were trimmed.
  Flagged as future work (see "Out of scope"). The risk is that we
  forget and quietly grow into 512 MB too. Mitigation: capture the
  observed boot RSS in the deploy PR description so future hotfixes
  have a reference number.
- **Longer grace period hides genuine app breakage.** A truly stuck
  startup now takes 30 s instead of 10 s to be flagged. Acceptable —
  in a 2-machine HA setup the second machine still serves while the
  first is wedged, and we'd notice the broken state on the first
  health-check tick after grace expires.
- **Rollback.** If 512 MB still OOMs (some transitive dep we haven't
  seen yet), `flyctl scale memory 1024 -a dual-research-alex` is the
  one-shot escape. Roll the spec forward in the same PR if it sticks.

## Open questions

1. **Should `min_machines_running` go from 0 → 1?** Cold-start cost
   becomes much more painful when the import graph is large. Keeping
   one machine warm is a few dollars/month and would eliminate the
   cold-start hang the user just hit. Not bundled into this hotfix
   because the immediate symptom (OOM) is fixed without it, but worth
   discussing alongside the follow-up perf spec.
2. **Do we want a follow-up spec to slim the server image?** The
   server module-graph doesn't need `pyiceberg`; only `RemoteSession.
   push_session_dir` does, and that lives on the orchestrator side.
   Splitting the read-path server from the push-path orchestrator
   would also shrink cold-start time and let the server target a
   smaller VM tier.
