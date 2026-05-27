---
kind: dev
spec: "0211"
slug: delegate-fly-deploy-to-github-actions
title: "Refactor: /dev-next step 21 — delegate fly deploy to .github/workflows/deploy.yml (eliminate local-vs-GHA deploy race)"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
depends_on: ["0210"]
complexity: M
created: 2026-05-24
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0211 — Refactor: delegate `/dev-next`'s fly deploy to GitHub Actions

> **Type:** refactoring  |  **Complexity:** M  |  **Depends on:** 0210
> **Bump:** PATCH — restructure of the `/dev-next` skill's deploy step plus a one-line addition to `.github/workflows/deploy.yml`; no app runtime code change
> **Evidence:** every `/dev-next` cycle today fires two concurrent deployers against `dual-research-alex` — the skill's local `fly deploy` at `~/.claude/skills/dev-next/SKILL.md:309` AND `.github/workflows/deploy.yml:36` triggered by step 19's `gh pr merge` push. The lease-drift incidents captured in the `project_fly_lease_drift_recovery` memory, the scar-tissue `fly status` case-1–5 matrix at `~/.claude/skills/dev-next/SKILL.md:320`–`:352`, the `feedback_fly_deploy_cd` memory's "always `cd` before fly" rule, and the standing reliance on `scripts/sweep_stale_blues.sh` are all symptoms of the race. Operator confirmed during 2026-05-24 design conversation that the duplicate-deploy pattern is the root pain, not the worktree mechanics that 0210 closes.

---

## 1. Current state

`/dev-next` is the queue-side spec driver. Its deploy block lives in step 21 at `~/.claude/skills/dev-next/SKILL.md:309`:

- **Step 21 invokes `fly deploy` locally** from the queue worktree (`~/.claude/skills/dev-next/SKILL.md:309`–`:316`). The deploy uses the operator's `FLY_API_TOKEN` from local env, against `dual-research-alex.fly.dev`.
- **Step 21 then routes the result through a five-case `fly status` matrix** at `~/.claude/skills/dev-next/SKILL.md:320`–`:344`, distinguishing "all new image / mixed healthy / only old / mixed unhealthy / status errored" — the matrix's stated purpose is to recover from spurious `fly deploy` non-zero exits when the deploy actually succeeded server-side.
- **Step 21 finally runs `scripts/sweep_stale_blues.sh`** on the success branches and matrix cases 1+2 (`~/.claude/skills/dev-next/SKILL.md:346`–`:352`).

Meanwhile, `.github/workflows/deploy.yml` already exists and fires on every `push: branches: [main]` (`deploy.yml:14`–`:17`), gated by `needs: test` (`deploy.yml:24`–`:25`), running `flyctl deploy --remote-only` (`deploy.yml:36`) with `FLY_API_TOKEN` from repo secrets (`deploy.yml:38`). The workflow has been in place since spec 0115 (`tests.yml:12`–`:14` documents the callable-workflow seam).

The race surfaces every cycle:

1. `/dev-next` step 19 invokes `gh pr merge --admin --squash --delete-branch` (`~/.claude/skills/dev-next/SKILL.md:284`–`:303`). The merge lands a commit on `origin/main`.
2. The push to `main` fires `.github/workflows/deploy.yml` — GH Actions begins building + deploying.
3. Seconds later `/dev-next` step 21 runs `fly deploy` locally. Two Fly deploys now race for machine leases on the same app.
4. Whichever loses prints a lease-conflict error. Today the operator follows `project_fly_lease_drift_recovery.md`: check `fly status` (the new image is usually already live from the *other* deployer), run `scripts/sweep_stale_blues.sh`, hand-edit state.

**Pain points:**

- **Structural duplicate-deploy.** Two deployers, one app, every cycle. The race is not transient — it fires every successful merge.
- **Recovery scar tissue.** The case-1–5 matrix (`~/.claude/skills/dev-next/SKILL.md:320`–`:344`), the explicit "DO NOT retry blind" guard at `:320`, and the operator-memory `project_fly_lease_drift_recovery` all exist *because* of the race. Remove the race and the matrix becomes dead code.
- **Local token + cwd ceremony.** `feedback_fly_deploy_cd` reminds the operator to `cd` before `fly deploy` because the queue worktree's default cwd doesn't carry the app context; `FLY_API_TOKEN` must be in local env. Both disappear when no local `fly deploy` runs.
- **Source-of-truth ambiguity.** "Did deploy succeed?" today is answered by `fly status` interpretation. With the local deploy gone, GH Actions' deploy-job conclusion is the single authoritative answer.
- **Cycle-time noise.** When the race fires, the operator spends 30–120 seconds in recovery per incident. The same wall-clock buys nothing — the GH Actions deploy was always going to land.

Spec 0210 closes a complementary but distinct problem (queue worktree never holds `main`). 0210 leaves step 21's local `fly deploy` in place; 0211 removes it.

## 2. Target state

`/dev-next` step 21 stops running `fly deploy` locally. Instead, after step 19's merge, it captures the merge commit SHA and observes the GH Actions `deploy.yml` workflow run that the push triggered, surfacing the run's conclusion as the deploy outcome.

Two artifacts change:

- **`~/.claude/skills/dev-next/SKILL.md`** — step 21 is rewritten end-to-end. The bash block becomes: capture the merge commit SHA (already in scope from step 19), bounded-poll `gh run list --workflow=deploy.yml --commit <sha>` until the run appears (deploy.yml is triggered by the push, so the run is created within seconds — typical < 5s, hard cap 30s), then `gh run watch <run-id> --exit-status`. On `--exit-status` zero, emit `deployed` with the version captured from the project's bumped `pyproject.toml`. On non-zero, surface the GH run URL plus `gh run view <id> --log-failed` tail, call the existing `queue_state set --push-to-main NNNN status=failed failure_step=deploy` path, emit `failed` event, halt — no retry, no fallback `fly deploy`. The case-1–5 `fly status` matrix at `~/.claude/skills/dev-next/SKILL.md:320`–`:344` and the post-deploy-sweep section at `:346`–`:352` are deleted entirely.

- **`.github/workflows/deploy.yml`** — gains a single post-deploy step that runs `bash scripts/sweep_stale_blues.sh dual-research-alex || true`, placed after the existing `Deploy to fly.io` step at `deploy.yml:35`–`:38`. The `|| true` keeps the sweep non-fatal (same semantics as `/dev-next`'s current "exit code intentionally ignored" treatment at `~/.claude/skills/dev-next/SKILL.md:352`). No change to `flyctl deploy --remote-only`, the `needs: test` gate, the `FLY_API_TOKEN` secret, or the concurrency group.

The `/dev-next` step 22 smoke (`~/.claude/skills/dev-next/SKILL.md:353`–`:357`) and `deploy_health_check_ok` event stay unchanged — they verify app-level behavior against the live URL, independent of which deployer pushed the image. The step 24 post-deploy commit (state + handoff + archive in one commit on `main`, per `~/.claude/skills/dev-next/SKILL.md:370`–`:382`) is also unchanged structurally; under 0210 it goes through `push_files_to_main` plumbing rather than `git checkout main`.

Resting state of the queue worktree across step 21 is whatever 0210 leaves it in — detached at `origin/main`. `gh run watch` reads no git state; it only consumes the merge SHA captured in step 19's bash scope.

The duplicate deploy disappears: the merge push fires GH Actions; `/dev-next` watches that run; no second deployer exists.

## 3. Stepwise migration

Each step independently shippable / revertable. Step ordering puts the GH-Actions side change first so the post-deploy sweep is already living in CI when the local invocation is removed.

- **Step 1: Add the post-deploy sweep step to `.github/workflows/deploy.yml`.** Insert a new step after `Deploy to fly.io` at `deploy.yml:35`–`:38`:
  ```yaml
  - name: Sweep stale blue machines
    run: bash scripts/sweep_stale_blues.sh dual-research-alex || true
  ```
  The script lives at the same path the skill calls today (`scripts/sweep_stale_blues.sh`), reads no local env beyond what GH Actions provides, and uses `flyctl` already on PATH from the `setup-flyctl` action at `deploy.yml:33`. `|| true` matches the existing "exit code intentionally ignored" treatment.
  - Verified by: one merge-to-main lands, GH Actions deploy run shows the new step executed; its log line matches the script's known output shape (`sweep: no stale blues on dual-research-alex` or `sweep: destroyed N/M …`). No app-side regression.

- **Step 2: Replace `/dev-next` step 21 body with `gh run watch` logic.** In `~/.claude/skills/dev-next/SKILL.md:309`–`:352`, delete the existing step 21 body (the `fly deploy` invocation, the case-1–5 matrix at `:320`–`:344`, and the post-deploy sweep section at `:346`–`:352`). Replace with:
  ```bash
  # Step 21 — watch the deploy.yml run that step 19's merge push triggered.
  MERGE_SHA="$(git rev-parse origin/main)"  # captured post-merge; deploy.yml runs on push:main
  uv run python -m scripts.spec_lifecycle.queue_state append-event NNNN deploy_started '{}'

  # Bounded poll for the run row to materialise (deploy.yml triggers within seconds).
  RUN_ID=""
  for i in $(seq 1 30); do
      RUN_ID="$(gh run list --workflow=deploy.yml --commit "$MERGE_SHA" \
          --json databaseId --jq '.[0].databaseId' 2>/dev/null)"
      [ -n "$RUN_ID" ] && break
      sleep 1
  done
  if [ -z "$RUN_ID" ]; then
      echo "ERROR: deploy.yml run for $MERGE_SHA did not appear within 30s — halting"
      uv run python -m scripts.spec_lifecycle.queue_state set --push-to-main NNNN \
          status=failed failure_step=deploy
      uv run python -m scripts.spec_lifecycle.queue_state append-event --push-to-main NNNN failed '{"reason":"deploy_run_not_found"}'
      exit 1
  fi

  # Watch the run; --exit-status returns non-zero on failure or cancellation.
  if gh run watch "$RUN_ID" --exit-status; then
      VERSION="$(uv run python -c 'import dual_research; print(dual_research.__version__)')"
      uv run python -m scripts.spec_lifecycle.queue_state append-event NNNN deployed "{\"version\":\"$VERSION\"}"
  else
      RUN_URL="$(gh run view "$RUN_ID" --json url --jq '.url')"
      echo "ERROR: deploy.yml run $RUN_ID failed — see $RUN_URL"
      gh run view "$RUN_ID" --log-failed | tail -50
      uv run python -m scripts.spec_lifecycle.queue_state set --push-to-main NNNN \
          status=failed failure_step=deploy
      uv run python -m scripts.spec_lifecycle.queue_state append-event --push-to-main NNNN failed "{\"run_url\":\"$RUN_URL\"}"
      exit 1
  fi
  ```
  No `fly` invocation. No case matrix. No local sweep — that's now in GH Actions per step 1. The `deploy_started` and `deployed` events fire in the same order as today; `--push-to-main` is omitted on `deploy_started`/`deployed` because step 24 still bundles them into the post-deploy commit (per `~/.claude/skills/dev-next/SKILL.md:316`).
  - Verified by: one `/dev-next` cycle lands a spec with no `fly` invocation in the local shell history; `dashboard/events/NNNN.jsonl` shows `deploy_started`, `deployed`, `deploy_health_check_ok` in order; the GH Actions run linked from `gh run list` matches the merge SHA.

- **Step 3: Update step 1's pre-flight checks.** `~/.claude/skills/dev-next/SKILL.md` step 1 currently verifies operator's `fly auth` is live (find the exact location during implementation; the section is named "Pre-flight"). Replace the `fly auth` check with: "Verify `gh auth status` is live AND has `repo` + `workflow` scopes — these gate `gh run watch` and `gh run view --log-failed` for private repos. If missing, halt and prompt the operator to run `gh auth refresh -s repo,workflow`." Remove any `fly auth whoami` invocation from step 1.
  - Verified by: a deliberately mis-scoped `gh auth login` causes step 1 to refuse before any merge or deploy work begins.

- **Step 4: Update `CLAUDE.md` "Spec workflow" section.** In `CLAUDE.md:43`–`:48` (the two-worktree block), append one sentence after the `/dev-next` description: "Deploys to `dual-research-alex.fly.dev` are driven by `.github/workflows/deploy.yml` on push-to-main; `/dev-next` watches the GH Actions run rather than invoking `flyctl` locally." Keep the rest of the spec-workflow prose intact.
  - Verified by: a reader of `CLAUDE.md` alone (no skill source) understands that local `fly deploy` is not part of the cycle.

- **Step 5: Tighten spec 0210 §5 Out of scope to name 0211.** Add one bullet to `specs/0210-dev-next-worktree-cross-conflict-on-main-checkout.md:117`–`:125`: "Local `fly deploy` invocation in step 21 — the worktree mechanics here are the only blocker spec 0211 removes from `/dev-next`, but the deploy-race fix itself is addressed in follow-up spec 0211." This lands in the SAME commit as the 0211 spec file at queue time, per the skill's spec-0202 §2.2 single-commit pattern.
  - Verified by: post-commit, `git log -1 --stat` shows both `specs/0210-*.md` and `specs/0211-*.md` in the same commit; spec 0210's §5 contains the new bullet.

- **Step 6: Mark obsolete memories during the implementing cycle.** During `/dev-next` for 0211, after the deploy succeeds, edit `~/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md` and `~/.claude/projects/-Users-alexlisitzky/memory/feedback_fly_deploy_cd.md` to prepend a one-line note: "**Obsolete as of spec 0211 (YYYY-MM-DD)** — local `fly deploy` no longer fires from `/dev-next`; deploys run only via `.github/workflows/deploy.yml`. Retained for historical context." Update `MEMORY.md`'s pointer line for each so the obsolete state is visible in the index. The memory dir is outside the repo, so this edit is not part of the spec's git commit — it's a side-effect bookkeeping step the implementing cycle owns.
  - Verified by: post-cycle, the two memory files lead with the obsolete-as-of note; the index lines reflect it.

- **Step 7: PATCH version bump + CHANGELOG + behavior-preservation test.** Bump `pyproject.toml`, `src/dual_research/__init__.py`, and refresh `uv.lock`. Add a `## [X.Y.Z] — YYYY-MM-DD` section to `CHANGELOG.md` directly under the file header, under `### Changed`, citing this spec. Add `tests/test_spec_0211_no_local_fly_deploy.py` (new file) that greps `~/.claude/skills/dev-next/SKILL.md` (or its in-repo mirror if one exists; otherwise the test reads from the spec's documented skill path and skips if absent locally) for forbidden patterns: a bare `fly deploy` line, `scripts/sweep_stale_blues.sh` outside a comment, the strings `case-1`/`matrix below is its actionable distillation`. The test is pure stdlib per the UI-test doctrine convention (still applicable to non-UI source-pattern tests for the same robustness reasons).
  - Verified by: `uv run pytest tests/test_spec_0211_no_local_fly_deploy.py -v` green; the CHANGELOG entry renders correctly on the dashboard at `https://lexiz.github.io/dual-research/`.

## 4. Behavior preservation

- [ ] Existing `tests/` suite passes unchanged — no production code path touched.
- [ ] `flyctl deploy --remote-only` continues to be the exact deploy command — it just runs once per merge (in GH Actions) instead of twice (once in GH Actions, once locally).
- [ ] Post-deploy sweep (`scripts/sweep_stale_blues.sh`) continues to run on every successful deploy — just from GH Actions instead of from the local skill.
- [ ] `dashboard/events/NNNN.jsonl` continues to receive `deploy_started`, `deployed`, `deploy_health_check_ok` events in the same order with the same payload shapes.
- [ ] The `status: deployed` frontmatter flip in step 24's commit on `origin/main` has identical shape to today's.
- [ ] `deploy_health_check_ok` (step 22's smoke) continues to assert app-level behavior end-to-end against the live URL; the source-of-truth for "the deploy worked" remains observable from outside the deployer.
- [ ] Cycle wall-clock: the GH Actions deploy duration was already on the critical path (the local `fly deploy` raced it but didn't shorten it). Removing the local invocation removes recovery-dance overhead on race-loss; expected cycle time is equal or slightly lower.

## 5. Out of scope

**Explicit: this spec does NOT add any new feature.** It removes the local `fly deploy` invocation from `/dev-next` step 21 and moves the post-deploy sweep into the existing GH Actions workflow. No new feature surfaces — no new dashboard signals, no new spec-lifecycle stages, no changes to spec frontmatter or queue-state schema, no new CI workflows.

- **Moving step 22's smoke into GH Actions.** The smoke (`~/.claude/skills/dev-next/SKILL.md:353`–`:357`) verifies app behavior end-to-end via an anchor research run against the live URL. Keeping it in `/dev-next` preserves the operator's view of "did the *thing the spec promised* actually work" as a cycle-side check, independent of GH Actions' "did the image deploy" check. Different layers, different owners. (Deferred to: no follow-up planned. A future spec could move it if the smoke logic grows complex enough to deserve CI residency, but not now.)
- **Removing `FLY_API_TOKEN` from local env.** Operators may still want `fly status` / `fly logs` for manual cluster inspection. The local token's only blast-radius improvement would be deletion; that's purely operator hygiene, not a `/dev-next` concern. (Deferred to: operator discretion, no spec needed.)
- **Hard-deleting `scripts/sweep_stale_blues.sh`.** The script is invoked by `.github/workflows/deploy.yml` (per step 1 above) and remains useful for manual operator recovery. Deleting it would break the GH Actions step and the operator's escape hatch. (Deferred to: no follow-up planned.)
- **Changing `.github/workflows/dashboard.yml` or `tests.yml`.** Both workflows are orthogonal to deploy. Dashboard regen and CI tests already run correctly on push-to-main; neither references `/dev-next`'s deploy invocation. (Deferred to: no follow-up planned.)
- **Touching `/dev-queue-run`.** That skill drives `/dev-next` end-to-end across multiple specs; its own logic doesn't invoke `fly` or `gh run watch`. The fix here cascades automatically when `/dev-next` is updated. (Deferred to: no follow-up planned.)
- **Generalising the `gh run watch` pattern to a reusable helper.** Today this is the only place `/dev-next` consumes a GH Actions run conclusion. If a second consumer appears (e.g. a future "watch dashboard.yml on handoff push" step), extract then. YAGNI for one caller. (Deferred to: future spec when a second caller exists.)
- **Adding rollback automation on deploy failure.** Today the operator decides whether to roll back, redeploy from a clean state, or investigate. That decision shape doesn't change — the spec only changes where the deploy runs. (Deferred to: future spec if rollback becomes routine enough to script.)

## 6. Risks

- **Risk: deploy.yml itself fails for reasons unrelated to the merge** (GH Actions runner outage, flyctl version drift, transient registry pull failure). *Mitigation:* `gh run watch --exit-status` surfaces the failure with a clean URL; operator inspects via `gh run view --log-failed` and decides whether to `gh workflow run deploy.yml` to retry or roll back manually. Same decision surface as today's local `fly deploy` failures, just routed through the GH Actions UI. The five-case `fly status` matrix being deleted was never recovering from genuine deploy failure anyway — it was recovering from the race the new design removes.

- **Risk: `gh run list --workflow=deploy.yml --commit <sha>` returns empty during the bounded poll.** *Mitigation:* the poll runs 30 iterations at 1s — empirically deploy.yml's run row appears within ~3s of the push (GitHub creates the run row before the runner is provisioned). If 30s elapses without a row, that itself is a signal something is wrong (e.g. workflow file deleted, branch protection misconfigured, GH API outage); halting with `deploy_run_not_found` is correct behavior. The bounded poll has no exponential backoff because the failure mode is a structural problem, not flakiness.

- **Risk: `gh run watch` hangs indefinitely if the GH Actions run stalls.** *Mitigation:* `gh run watch` honors GH Actions' own job timeout. `deploy.yml` doesn't currently set `timeout-minutes`, so it inherits GH Actions' 6h default — adequate as a safety net; a hanging deploy that long indicates a Fly outage worth waking the operator for anyway. Adding an explicit `timeout-minutes: 15` to `deploy.yml`'s `deploy` job would be a defensible tightening; deferring to a future hygiene spec because it's orthogonal to the race fix and would itself warrant per-step verification.

- **Risk: GH Actions concurrency group `deploy-main` cancels an in-flight deploy.** `.github/workflows/deploy.yml:27`–`:29` declares `concurrency: { group: deploy-main, cancel-in-progress: false }`. If two merges land in quick succession, the second is queued, not cancelled — and the first's `gh run watch` in `/dev-next` still reports the first run's true conclusion. `/dev-next` runs one spec at a time per session; under `/dev-queue-run`, the per-cycle merge waits for the prior `gh run watch` to complete before the next merge fires, so the concurrency group is structurally never exercised with overlap. No mitigation needed beyond the existing concurrency declaration.

- **Risk: GH CLI auth scopes drift** (operator runs `gh auth refresh` without `workflow` scope; `gh run watch` then errors on private-repo runs). *Mitigation:* step 1 pre-flight check (step 3 of this migration) verifies scopes BEFORE any merge fires. If the check fails, the cycle halts pre-merge — no destructive state. Operator runs `gh auth refresh -s repo,workflow` and re-invokes `/dev-next`. The check is cheap (one `gh auth status` invocation).

- **Risk: removing the local `fly deploy` removes a defense against a misconfigured GH Actions deploy.** Today, if `deploy.yml` is broken (e.g. someone deleted the workflow file), the local `fly deploy` still ships. After this spec, a broken `deploy.yml` means no deploy. *Mitigation:* the test in step 7 covers the inverse (no local `fly deploy` in the skill); a sibling concern — that `deploy.yml` itself stays well-formed — is covered by GH Actions' workflow-file validation at push time (a broken YAML rejects the push). A workflow file that is *syntactically* valid but *semantically* broken (e.g. removed deploy step) would slip through; that risk is the same as today's risk that someone deletes the local `fly deploy` from the skill. Not a regression. The trade-off is intentional: one deployer, one source of truth.
