---
spec: "0162"
date: 2026-05-22
version: 1.23.2
pr: "https://github.com/Lexiz/dual-research/pull/185"
---

# Handover — Spec 0162 — Post-deploy sweep for `safe_to_destroy` blue machines (v1.23.2)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#185](https://github.com/Lexiz/dual-research/pull/185)
- **Merge commit:** `3f9480b`
- **Cycle time:** ~18 minutes (started 15:32:34Z, deployed 15:50:02Z)

## What landed

### `scripts/sweep_stale_blues.sh` (new, executable)

- Reads `fly machine list --json` and destroys any machine whose `metadata.fly_bluegreen_deployment_tag` equals the literal string `"safe_to_destroy"`. Fly sets that tag; we never do; the selector cannot hit a live green by construction.
- Best-effort semantics — every error path logs to stderr and exits 0. The deploy that runs before the sweep determines success; the sweep can never fail the caller.
- Flags:
  - `--app NAME` (default `dual-research-alex`)
  - `--expected-count N` (default 2) — used by the diagnostic fallback (below)
  - `--input <file>` — testing-only flag that skips the `fly machine list` call and reads JSON from a file. Lets the regression suite exercise the bash flow without mocking the CLI.

### Diagnostic fallback (folded in during implementation)

The spec's filter expression — `select(.config.metadata.fly_bluegreen_deployment_tag == "safe_to_destroy")` — is a best-guess from the parallel investigation session that authored the spec. At implementation time the live cluster had no stale blues to verify against (Fly's orchestrator caught up between observation and implementation). **The filter may not match Fly's real tag scheme.**

To make that discoverable rather than silently a no-op forever:

- If the filter finds 0 stale blues but `fly machine list` returns more than `--expected-count` machines (default 2), the script dumps every machine's metadata to stderr.
- That dump lands in the deploy handoff's "Deploy notes" verbatim. The **next time the bug fires with whatever shape Fly actually uses**, we have full evidence to correct the filter without manual triage.

Until that evidence arrives, the script is a safe no-op (zero stale, no destroys, no dumps when the cluster is exactly 2).

### Host-side hook (NOT in this PR — lives at `~/.claude/skills/dev-next/SKILL.md`)

Step 21 now runs `scripts/sweep_stale_blues.sh` after `fly deploy` and surfaces the script's single-line summary verbatim in the handoff's Deploy notes section.

### Tests — 9 new cases (`tests/scripts/test_sweep_stale_blues_filter.py`)

- 5 filter cases that extract the actual `JQ_FILTER` expression from the script source and run it via subprocess against a mixed fixture (live greens, stale blues, unrelated tags, missing-metadata, empty input).
- 4 end-to-end cases that run the bash script via `bash scripts/sweep_stale_blues.sh --input <fixture>`: filter-misses-quiet, oversized-cluster-dumps, expected-size-quiet, --input-skips-fly.

All 9 pass on top of the 1510 prior Python tests → **1519 total**.

## Deploy notes

This deploy was unusually clean — **Fly's orchestrator destroyed both old blue machines itself**, no lease-lock errors. The `Deployment Complete` line included two `Machine ... destroyed` lines for the prior v283 blues. After the deploy, the sweep ran and reported:

```
sweep: no stale blues on dual-research-alex
```

(Exactly as expected — Fly cleaned up before the sweep got the chance.)

Final cluster state (clean, 2 machines on v284):

```
1854537b22d548  v284  started  1/1 passing
e826060a2d2708  v284  started  1/1 passing
```

Health: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.23.2","backend":"supabase"}`.

**Note on the verification gap:** because this round's bluegreen completed cleanly, we still don't have real-cluster evidence that the filter expression matches Fly's actual tag scheme. The diagnostic-dump path was correctly built and tested against fixtures, but it has not been exercised against a real stale machine. **The next time stragglers appear in production, the handoff will carry the metadata dump — that's the canary.**

## Open observations / what to watch

- **Filter unverified.** If a future deploy ends with `fly status` showing > 2 machines AND the sweep log says `no stale blues`, the diagnostic dump fires and the next handoff captures evidence. At that point we either correct the filter in a follow-up spec or write a new spec replacing the approach entirely (e.g. "destroy any machine on a release version older than the latest" — a different selector that doesn't depend on Fly's internal tag).
- **Fly's bug appears intermittent.** Specs 0160 and 0161 saw the lease-lock failure 2/2 deploys. Spec 0162's own deploy was clean. So the failure mode is intermittent, not deterministic — which means the sweep's value will only become visible the next time the bug fires. Until then it's defensive infrastructure.

## Deferred during implementation

(none — everything in scope landed cleanly; the diagnostic fallback was added during implementation, not deferred)

## Queue at handoff

- **Empty.** Ten specs shipped today.

## File map

```
# New (in this PR)
scripts/sweep_stale_blues.sh                              # +x
tests/fixtures/fly_machine_list_bluegreen.json
tests/fixtures/fly_machine_list_no_stale_extra.json
tests/scripts/test_sweep_stale_blues_filter.py            # 9 cases

# Modified
CHANGELOG.md                                              # [1.23.2] section
pyproject.toml, src/dual_research/__init__.py             # 1.23.2
specs/0162-post-deploy-blue-sweep.md                      # status: deployed
dashboard/events/0162.jsonl                               # full event stream
handoffs/2026-05-22-spec-0162-...md                       # this file

# Host-side (not in this PR)
~/.claude/skills/dev-next/SKILL.md                        # step 21 invokes the sweep
```
