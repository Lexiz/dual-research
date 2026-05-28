---
kind: dev
spec: "0249"
slug: path-filter-deploy-only-image-affecting-commits
title: "Fix: path-filter deploy.yml so only image-affecting commits deploy"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-28
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
disposition_reason: "Directly authored fix for an active waste/latency problem in the /dev-next deploy path; ready to run."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0249 — Fix: path-filter deploy.yml so only image-affecting commits deploy

> **Type:** bug  |  **Severity:** P2  |  **Affects:** `.github/workflows/deploy.yml` CI deploy path; every `/dev-next` cycle
> **Bump:** PATCH — bug fix
> **Evidence:** `gh run list --workflow=deploy.yml` shows ~12 `spec(0246): queue-state update` deploy runs for spec 0246 alone; 147 of the last 200 commits on `origin/main` (74%) are `queue-state update` commits.

---

## 1. Reproduction

**Environment:** GitHub Actions on `lexiz/dual-research`, workflow `.github/workflows/deploy.yml`. Observed across the spec 0246–0248 `/dev-next` cycles.

**Steps:**
1. Run `/dev-next` on any queued spec. The cycle merges the spec PR, then pushes ~13 telemetry commits to `main` — each with message `spec(NNNN): queue-state update`, hardcoded at [`scripts/spec_lifecycle/queue_state.py:393`](scripts/spec_lifecycle/queue_state.py:393) — as lifecycle events flush to `dashboard/queue-state.json`.
2. Inspect `gh run list --workflow=deploy.yml` after the cycle.

**Expected:** One deploy per shipped spec — the merge-commit run that builds and ships the new image.

**Actual:** ~13 `deploy.yml` runs per spec, each running the full `test → flyctl deploy --remote-only → sweep` pipeline ([`deploy.yml:30-43`](.github/workflows/deploy.yml:30)) and shipping a **byte-identical** image. They serialize behind the `deploy-main` concurrency group ([`deploy.yml:27-29`](.github/workflows/deploy.yml:27), `cancel-in-progress: false`), so the operator waits through a backlog of redundant deploys per spec.

## 2. Root cause hypothesis

[`deploy.yml:14-17`](.github/workflows/deploy.yml:14) triggers on every push to `main` with **no `paths:` filter** — unlike [`dashboard.yml:4-11`](.github/workflows/dashboard.yml:4), which is path-filtered to `specs/**`, `handoffs/**`, `dashboard/**`, `scripts/spec_lifecycle/**`, `.github/workflows/dashboard.yml`. Queue-state telemetry commits touch only `dashboard/queue-state.json` (and occasionally `handoffs/**`) — files that never change the shipped image — yet each one fires a full deploy because the trigger is unconditional.

## 3. Fix

Add an allow-list `paths:` filter to `deploy.yml`'s `on.push`, scoped to the files that actually change the shipped image:

```yaml
on:
  push:
    branches: [main]
    paths:
      - "src/**"
      - "pyproject.toml"
      - "uv.lock"
      - "Dockerfile"
      - "fly.toml"
      - ".github/workflows/deploy.yml"
  workflow_dispatch:
```

`workflow_dispatch` is retained as the manual escape valve for force-deploying a commit that did not touch an allow-listed path. `pyproject.toml` and `uv.lock` are kept in the list specifically to preserve the deploy-on-every-spec-merge invariant (see §4) — not because version-only edits change runtime behavior.

No other change to `deploy.yml`; the `test`, `deploy`, and `sweep` jobs and the `deploy-main` concurrency group are untouched.

## 4. Why this is safe for `/dev-next` (load-bearing argument)

`/dev-next` step 20 ([`~/.claude/skills/dev-next/SKILL.md`](../.claude/skills/dev-next/SKILL.md), spec 0211) watches the `deploy.yml` run for `$MERGE_SHA` and **halts** with `deploy_run_not_found` if no run materializes within 30s. So the filter must guarantee that every spec **merge commit** still triggers a deploy.

It does — via the CLAUDE.md versioning rule: every merged PR bumps `pyproject.toml` and `src/dual_research/__init__.py`. Verified against real squash-merges on `origin/main`:

- **#285** (spec 0247.1, a `/dev-next`-skill-only spec) touched `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock`, plus a versioned static asset under `src/**` — all inside `src/**` / `pyproject.toml` / `uv.lock`.
- **#284** (spec 0247) touched the same set.

The allow-list is therefore a **superset of the files every spec PR is guaranteed to touch**, so the merge-commit deploy always fires; only the telemetry `queue-state update` commits (which touch `dashboard/**` and at most `handoffs/**`) stop triggering deploys. Side benefit: with no competing queue-state deploy runs, the spec 0211.3 concurrency-cancel pivot fires less often, not more.

## 5. Regression-prevention test

A pure-stdlib YAML-shape test `tests/test_spec_0249_deploy_path_filter.py` that parses `.github/workflows/deploy.yml` (stdlib only — the repo already ships PyYAML; the test reads `on.push.paths`):

- [ ] **Positive:** `on.push.paths` exists and contains `src/**`, `pyproject.toml`, and `uv.lock`. Fails before the fix (no `paths:` key present).
- [ ] **Antipodal-absence:** `dashboard/**`, `handoffs/**`, and `specs/**` are NOT in `on.push.paths` — locks in that telemetry commits do not deploy.
- [ ] **Invariant guard:** asserts the version-bump-guaranteed paths (`pyproject.toml` and `src/**`) are present in the allow-list — the property that keeps `/dev-next` step-20 deploy-watch alive (§4). A future edit that drops either entry fails this test.

## 6. Blast radius

Only the `on.push` trigger of `deploy.yml` changes. [`dashboard.yml`](.github/workflows/dashboard.yml) is already path-filtered and is unaffected. [`tests.yml`](.github/workflows/tests.yml) is a reusable workflow invoked via `uses:` by `deploy.yml` ([`deploy.yml:20-22`](.github/workflows/deploy.yml:20)) and its own triggers are untouched. The local working tree and the `queue_state.py` push-to-main plumbing are untouched — this spec changes only *when CI deploys*, not *what gets pushed*.

## 7. Out of scope

- Reducing the *number* of `queue-state update` commits emitted per `/dev-next` cycle (a separate concern in `scripts/spec_lifecycle/queue_state.py`) — deferred to a follow-up dev spec to be drafted post-merge if the commit volume itself becomes a problem.
- Adding or changing `paths:` filters on `tests.yml`'s own push trigger.

## 8. Risks

A future spec PR that ships an image change without touching any allow-listed path would silently skip deploy. Mitigated on two fronts: (a) the CLAUDE.md versioning rule guarantees every merge touches `pyproject.toml` + `src/dual_research/__init__.py`, both allow-listed; (b) `workflow_dispatch` remains as the manual force-deploy escape valve. The §5 invariant-guard test fails loudly if a future edit removes the version-bump paths from the allow-list.
