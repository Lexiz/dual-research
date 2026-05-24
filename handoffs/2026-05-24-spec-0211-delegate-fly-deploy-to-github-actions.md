---
spec: "0211"
date: 2026-05-24
version: "1.44.10"
pr: "https://github.com/Lexiz/dual-research/pull/243"
---

# Spec 0211 — delegate `/dev-next`'s fly deploy to GitHub Actions

Shipped as PR [Lexiz/dual-research#243](https://github.com/Lexiz/dual-research/pull/243), squash-merged at commit `9203e2f`, deployed to `dual-research-alex.fly.dev` via `.github/workflows/deploy.yml` run [`26362546656`](https://github.com/Lexiz/dual-research/actions/runs/26362546656) (success). Live `/api/health` returns `{"version":"1.44.10"}`.

## What landed

- **`.github/workflows/deploy.yml`** — new `Sweep stale blue machines` step runs `bash scripts/sweep_stale_blues.sh || true` after `flyctl deploy --remote-only`, with `FLY_API_TOKEN` from repo secrets. The sweep moved with the deploy from the local skill into CI.
- **`~/.claude/skills/dev-next/SKILL.md`** (live file, outside the repo):
  - **Frontmatter description** — "fly deploy" → "watch GH Actions deploy" in the trigger sentence.
  - **Step 4** — now also asserts `gh auth status` carries `repo` + `workflow` scopes; halts with a refresh prompt if missing. Replaces the (non-existent today) `fly auth` check the spec assumed was there.
  - **Step 20** — entirely rewritten. Old body: `fly deploy` + 5-case `fly status` matrix (lines 320–344) + post-deploy sweep block (lines 346–352). New body: capture `MERGE_SHA` from `origin/main`, bounded-poll `gh run list --workflow=deploy.yml --commit "$MERGE_SHA"` for up to 30s, then `gh run watch "$RUN_ID" --exit-status`. On success emit `deployed` with version from `dual_research.__version__`. On failure surface the run URL plus `gh run view --log-failed` tail, flip to `status: failed, failure_step: deploy`, halt — no retry, no fallback `fly deploy`.
  - **Spec 0210 prose at line 310** — updated to reference step 20's `gh run watch` instead of the removed local `fly deploy`.
  - **Standing rules** — final-line "do not ask permission for ... `fly deploy`" → "watching the GH Actions deploy".
- **`CLAUDE.md:33`** — `/dev-next` bullet documents that deploys are driven by `.github/workflows/deploy.yml` on push-to-main; the skill watches the GH Actions run rather than invoking `flyctl` locally.
- **`tests/test_spec_0211_no_local_fly_deploy.py`** (new, pure stdlib) — four source-pattern assertions against the live SKILL.md: no bash line invokes `fly deploy`, no bash line invokes `scripts/sweep_stale_blues.sh`, the case-1–5 matrix prose is absent, `gh run watch` and `deploy.yml` are referenced. Skips when SKILL.md is absent locally (e.g. in CI runners). All 4 green; full suite 1900/1900 green.
- **Version bump** — `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` → 1.44.10. `CHANGELOG.md` carries a new `## [1.44.10] — 2026-05-24` section under `### Changed`.

## Deploy notes

- The squash-merge commit `9203e2f` triggered deploy.yml run `26362546656` — completed: success. That run reflects the actual spec 0211 code on main.
- Subsequent `--push-to-main` queue-state updates (pr_opened, status=merged, etc.) advanced `origin/main` to `8416888…`. The current `/dev-next` step 20 captured `MERGE_SHA` from `origin/main` AFTER those pushes had landed, so it watched run `26362575383` (the deploy for `8416888…`) — also success. Both deploys ship the same image content.
- **CI sweep step did NOT do its job.** Log line: `sweep: fly machine list failed for app=dual-research-alex`. Root cause: `scripts/sweep_stale_blues.sh:77` invokes `fly machine list …`, but `superfly/flyctl-actions/setup-flyctl@master` only installs `flyctl` on the runner — there is no `fly` alias. The redirect `2>/dev/null` swallows the "command not found" error, leaving only the script's generic failure line. The `|| true` in deploy.yml kept the step non-fatal as designed. Under rolling deploys this is cosmetic (the sweep finds zero candidates anyway), but the verification criterion in spec 0211 §3 step 1 ("log line matches `sweep: no stale blues …` or `sweep: destroyed N/M …`") is not met.

## Memory bookkeeping

Per spec 0211 §3 step 6, the following memory files are marked obsolete-as-of-0211:

- `~/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md` — the lease-drift recovery dance existed only when two deployers raced the same app; with the race gone, this is historical context only.
- `~/.claude/projects/-Users-alexlisitzky/memory/feedback_fly_deploy_cd.md` — the "always `cd` before `fly deploy`" rule applied only to the local `fly deploy` invocation that is now gone.

Both files are edited inline to prepend the obsolete-as-of note; the `MEMORY.md` index lines are updated in tandem. These edits land outside this commit (the memory dir is outside the repo).

## Deferred during implementation

- **CI sweep needs `fly` shim or script rewrite to use `flyctl`.** The new `Sweep stale blue machines` step in `.github/workflows/deploy.yml` runs `bash scripts/sweep_stale_blues.sh || true`, but the script at [scripts/sweep_stale_blues.sh:77](scripts/sweep_stale_blues.sh:77) calls `fly machine list --app "$APP" --json`. The CI runner has `flyctl` (from `superfly/flyctl-actions/setup-flyctl@master`) but no `fly` binary or alias, so the sweep fails immediately with "sweep: fly machine list failed for app=dual-research-alex" — verified in deploy.yml run [`26362575383`](https://github.com/Lexiz/dual-research/actions/runs/26362575383). The `|| true` keeps the step non-fatal as designed, and under rolling deploys the sweep would find zero candidates anyway, but the verification criterion in spec 0211 §3 step 1 is not met. Two viable fixes: (a) update [scripts/sweep_stale_blues.sh](scripts/sweep_stale_blues.sh) to prefer `flyctl` over `fly`, falling back where needed (the script is also invoked locally where `fly` is more common); or (b) add a one-line `ln -sf "$(command -v flyctl)" "$RUNNER_TEMP/fly" && export PATH="$RUNNER_TEMP:$PATH"` shim to the workflow step.

- **Step 20's `MERGE_SHA` capture is racy with post-merge `--push-to-main` calls.** The new step 20 logic uses `MERGE_SHA="$(git rev-parse origin/main)"`, but by the time step 20 runs, the queue-state update at step 18 (`status=merged`) has already pushed to `origin/main` via the `_push_state_to_main` plumbing — so `origin/main` is one or more commits past the actual squash-merge commit. Witnessed this cycle: the squash-merge landed at `9203e2f`, but `origin/main` was `8416888…` when step 20 ran. The watched run was the deploy for the later SHA, not the merge commit. In practice both runs ship the same image (queue-state-only commits don't change the Docker image), so the watched run's pass/fail still tracks the actual deploy. But the spec's design intent was "watch the run triggered by step 19's merge push" specifically. Fix: capture `MERGE_SHA` immediately after the `gh pr merge` call in step 19, before any `queue_state set --push-to-main` runs in step 18 (or restructure step ordering so the merge is the last main-side write before step 20).
