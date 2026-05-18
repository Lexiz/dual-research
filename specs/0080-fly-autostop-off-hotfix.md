---
spec: 0080
title: "Hotfix: disable Fly auto_stop_machines to stop the proxy flap"
label: bug
version-bump: PATCH
status: merged
target-version: 0.69.4
created: 2026-05-18
pr: "https://github.com/Lexiz/dual-research/pull/80"
---

# Spec 0080 — Disable Fly auto_stop to stop the proxy flap

## Context

After [spec 0079](0079-hosted-ui-modal-load-perf.md) landed, the
hosted UI started failing intermittently for the user. Network probes
from outside the data centre were timing out at 30 s with HTTP 000
(connection never establishes), while the app itself was clearly
healthy in Fly's machine logs — uvicorn served `200 OK` responses to
internal traffic the whole time.

The Amsterdam edge proxy logs showed the smoking gun across many
seconds at a time:

```
proxy [ams] error: could not find a good candidate within 40 attempts
at load balancing
request.url: https://dual-research-alex.fly.dev/api/runs
```

`flyctl status` over a 30-minute window showed the two machines
**alternating** between `passing` and `critical`:

```
10:48Z  876d04a02251e8: 1 critical    148ee320f427e8: 1 passing
10:57Z  876d04a02251e8: 1 critical    148ee320f427e8: 1 passing
11:16Z  876d04a02251e8: 1 passing     148ee320f427e8: 1 critical   ← flipped
11:20Z  876d04a02251e8: 1 passing     148ee320f427e8: 1 critical
```

The trigger: spec 0079 set `min_machines_running = 1` while keeping
`auto_stop_machines = "stop"`. We have **two** machines deployed but
Fly's auto-scaler wants to stop the "extra" one because traffic is
low (only health checks + occasional user clicks). Each stop/restart
cycle leaves the proxy's routing table briefly out of sync with reality
— it routes a request to a machine that's just been stopped, the
connection hangs until proxy gives up after 40 attempts, and the user
sees 30-second timeouts. With two machines flapping in opposite phase,
roughly half of all proxy attempts hit a stale entry.

`min_machines_running = 1` does protect cold-starts for the warm
machine, but it doesn't prevent the auto-scaler from stopping
**other** machines above the floor — and "other" here is the second
deployed machine, not a phantom third one.

## Proposed change

`fly.toml`:

```diff
   auto_stop_machines = "stop"
+  auto_stop_machines = "off"
   auto_start_machines = true
   min_machines_running = 1
```

`auto_stop_machines = "off"` means Fly never proactively stops a
machine. Both deployed machines stay running permanently. The proxy
always has two healthy backends to route to and the flap can't happen.

`min_machines_running = 1` is left in place. It's now arithmetically
redundant (with auto_stop disabled, the running count can never drop
below the deployed count of 2) but it's a cheap insurance for a future
where someone scales the app down to 1 deployed machine — they'd still
get one warm at idle.

## Cost

Two `shared-cpu-1x:512MB` machines running 24/7 vs one running + one
flapping. Roughly **$4–6/month extra** at current Fly pricing,
depending on actual CPU usage. That's the price of consistent
sub-second reachability for a hobby/internal tool — easily justified.

## Out of scope

- **Run-snapshot latency.** `/api/runs/{id}` still does a full
  `SupabaseSessionData.materialize()` on every call — multiple
  paginated reads to Supabase per request, multi-second response even
  on warm machines. **That's the next spec, not this one.** This
  hotfix only fixes proxy reachability, not in-app perf.
- **Trying `auto_stop_machines = "suspend"` as a middle ground.**
  Suspend keeps RAM state but its semantics around proxy routing are
  the same as `"stop"`; the flap risk recurs. Not worth tasting until
  we know cost is a problem.
- **Reducing to a single machine.** Cuts cost but removes HA. Not the
  goal here.
- **Regional deploy in Europe.** Independent decision; separate spec
  if needed after the perf work lands.

## Test plan

- [ ] **Deploy:** `fly deploy` from this branch.
- [ ] **Both machines stable.** Wait 5 minutes, then
  `flyctl status -a dual-research-alex` shows both machines
  `started` with `1 passing` and **neither flips** within a further
  10 minutes of low-traffic observation.
- [ ] **External reachability restored.** 10 consecutive curls of
  `https://dual-research-alex.fly.dev/api/health` all return HTTP 200
  within < 2 s each (vs the 30 s timeouts before). No HTTP 000.
- [ ] **No new OOM.** `flyctl logs | grep -iE 'out of memory|code: 137'`
  remains clean for 30 min after deploy.
- [ ] **End-to-end:** open
  `https://dual-research-alex.fly.dev/#/runs/<id>` and confirm the
  run-list and run-detail pages render. They may still take seconds
  (that's spec 0081's job), but they should not 502/503 or hang on
  network.

No new automated tests — this is a Fly config flag with no code path.

## Risks

- **Costs more.** Acknowledged above; the trade-off is intentional.
- **Both machines down at once is now a single-fault-domain event.**
  Fly's machine-host failures don't usually correlate across machines,
  but if they do, the second machine no longer "auto-starts" — it
  needs an explicit `flyctl machine start`. Acceptable for the
  reachability win.
- **Rollback.** Revert this commit; both knobs return to spec 0079
  values. The flap returns, but no data loss.

## Open questions

None. The trade-off is small and the symptom is unambiguous.
