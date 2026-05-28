---
spec: "0249"
date: 2026-05-29
version: 1.61.1
pr: https://github.com/Lexiz/dual-research/pull/287
kind: post-deploy
---

# Spec 0249 — Fix: path-filter deploy.yml so only image-affecting commits deploy

**Type:** bug · **Bump:** PATCH (v1.61.0 → v1.61.1) · **PR:** [#287](https://github.com/Lexiz/dual-research/pull/287) · **Deploy:** GH Actions run `26605256881` → `success`, live root 200.

## What landed

Added an allow-list `on.push.paths` filter to [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) so only image-affecting commits trigger the `test → flyctl deploy --remote-only → sweep` pipeline:

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

Before this fix, `deploy.yml` triggered on *every* push to `main` — so each `/dev-next` cycle's ~13 `queue-state update` telemetry commits (touching only `dashboard/**`, at most `handoffs/**`) fired a full deploy that shipped a byte-identical image and serialized behind the `deploy-main` concurrency group (`cancel-in-progress: false`). The operator waited through a backlog of redundant deploys per spec.

The allow-list is a **superset of the files every spec PR is guaranteed to touch** — the CLAUDE.md versioning rule bumps `pyproject.toml` + `src/dual_research/__init__.py` on every merge, both allow-listed — so the merge-commit deploy that `/dev-next` step 20 watches always fires. `workflow_dispatch` is retained as the manual force-deploy escape valve. The `test`/`deploy`/`sweep` jobs and the `deploy-main` concurrency group are untouched.

## Validation

This very cycle is the validating case: the spec 0249 merge commit (#287) touched `deploy.yml`, `pyproject.toml`, `uv.lock`, and `src/**` (version-notes.json + `__init__.py`) — all allow-listed — and the deploy.yml run materialized within the step-20 30s window and concluded `success`. The previous cycle's queue-state telemetry commits will no longer trigger deploys.

## Tests

- New regression test [`tests/test_spec_0249_deploy_path_filter.py`](tests/test_spec_0249_deploy_path_filter.py) (PyYAML, already a repo dep):
  - **Positive:** `on.push.paths` exists and contains `src/**`, `pyproject.toml`, `uv.lock`.
  - **Antipodal-absence:** `dashboard/**`, `handoffs/**`, `specs/**` are NOT in the allow-list.
  - **Invariant guard:** version-bump paths (`pyproject.toml`, `src/**`) present — the property that keeps `/dev-next` step-20 deploy-watch alive.
- Full suite: `2379 passed`.

## Follow-ups / risk

- **Risk (spec §8):** a future spec PR shipping an image change without touching any allow-listed path would silently skip deploy. Mitigated by (a) the versioning rule guaranteeing every merge touches `pyproject.toml` + `src/__init__.py`, and (b) `workflow_dispatch`. The §5 invariant-guard test fails loudly if a future edit drops the version-bump paths.
- **Out of scope (spec §7):** reducing the *number* of `queue-state update` commits emitted per `/dev-next` cycle — deferred to a follow-up dev spec only if commit volume itself becomes a problem.
