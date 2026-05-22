---
kind: draft
draft_id: "005"
slug: post-deploy-blue-sweep
title: Post-deploy sweep for safe_to_destroy blue machines
type: bug
status: draft
created: 2026-05-22
source_session: dbc5aed3-25f2-4ed3-a7b1-4dc61161a4c0
---

# Draft 005 — Post-deploy sweep for safe_to_destroy blue machines

## Context

Bluegreen deploys under spec 0159's config are leaving stale blue machines alive when Fly's orchestrator can't acquire the destroy-lease in its cleanup phase. Observed in handoffs `2026-05-22-spec-0160` and `2026-05-22-spec-0161` — 2 of 2 bluegreens have hit it. The lease-holder is a Fly-internal token (`*@tokens.fly.io`) we can't revoke; only Fly can fix the orchestrator itself.

User-facing service is unaffected (the proxy routes to greens). The damage is cosmetic + ~$5/mo of idle blues accumulating across deploys. A post-deploy sweep in `/dev-next` is the cheapest workaround until Fly fixes the underlying lease bug.

## Sketch / proposed direction

- Add a sweep step at the end of `/dev-next`'s deploy stage (after `fly deploy` returns success).
- Mechanism:
  - `fly machine list --json` → list all machines for the app.
  - `jq` filter to those whose `metadata.fly_bluegreen_deployment_tag == "safe_to_destroy"`.
  - For each match: `fly machine destroy <id> --force`.
- Safety argument: Fly itself sets `fly_bluegreen_deployment_tag: safe_to_destroy` only on machines its orchestrator has already decided are eligible for destroy. The sweep filters on Fly's own verdict — it can never hit a live green.
- Surface area: the `/dev-next` skill's deploy section only. ~10 lines of bash (`fly machine list --json | jq … | xargs -n1 fly machine destroy --force`).
- No source-code changes; no `pyproject.toml`/`__init__.py` version bump implied by this on its own (skill files aren't versioned).
- Test surface: integration smoke against a saved `fly machine list --json` fixture to confirm the jq filter selects only `safe_to_destroy`-tagged entries.

## Unresolved questions

- Type classification: `bug` (deploy hygiene defect — we leave junk behind) vs `refactoring` (deploy-tooling improvement). Currently guessed `bug`. Affects whether the changelog entry sits under `### Fixed` or `### Changed`.
- Version bump: since the change is skill-file-only with no `src/` edits, does this still warrant a `pyproject.toml` PATCH bump per the project's "every merged PR ships a version bump" rule, or is a skill-only change explicitly exempt? Need to confirm against the policy.
- Should the sweep be **best-effort** (log + continue on any destroy failure, so a flaky machine doesn't fail the deploy stage) or **strict** (any destroy failure fails the deploy stage)? Recommend best-effort with a clearly-visible "swept N stale blues" log line, since the deploy itself already succeeded by the time we're sweeping.
- Should the sweep also run as a standalone hygiene command (`/dev-next` deploy is the trigger today, but a manual "sweep now" entry point might be useful for fixing the existing stragglers from spec 0160/0161)? Out of scope as written, but worth deciding before implementation.
- Scope of the integration smoke: hand-rolled fixture vs capturing a real `fly machine list --json` from the current Fly app state into `tests/fixtures/`. Real capture is more honest but bakes in a snapshot timestamp.

## Out of scope

- Fixing Fly's destroy-lease bug itself (we can't — internal Fly orchestrator concern).
- Retroactively cleaning the existing stale blues from specs 0160/0161 (separate one-shot task; the sweep only catches future ones).
- Any UI / dashboard surfacing of "stale machine" state.
