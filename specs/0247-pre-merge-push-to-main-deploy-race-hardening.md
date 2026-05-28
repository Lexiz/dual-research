---
kind: dev
spec: "0247"
slug: pre-merge-push-to-main-deploy-race-hardening
title: "Refactor: stop /dev-next pre-merge step-18 --push-to-main commits from racing the merge-commit deploy"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
depends_on: ["0211", "0211.3"]
complexity: S
created: 2026-05-28
queued_at: "2026-05-28T19:06:20Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
# Spec 0229 §2.5 carve-out-disposition convention. Pick one of:
#   ship     — high-priority follow-up, should reach /dev-next
#   defer    — recorded but not actionable soon
#   archive  — informational record only (the default for carve-outs)
disposition: ship
disposition_reason: "Closes a recurring live deploy-race that cancelled the spec 0246 merge-commit deploy and forced a manual workflow_dispatch recovery this cycle; the prevention angle that spec 0211.3 explicitly deferred."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0247 — Refactor: stop `/dev-next` pre-merge step-18 `--push-to-main` commits from racing the merge-commit deploy

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** 0211, 0211.3
> **Bump:** PATCH — `/dev-next` skill-body change (the skill lives outside the repo); the in-repo commit carries a source-pattern test + version bump + CHANGELOG, no app runtime code change.
> **Evidence:** spec 0246 carve-out, recorded in `handoffs/2026-05-28-spec-0246-all-runs-card-layout-rewrite.md:82`–`:93` and the deploy-anomaly note at `handoffs/2026-05-28-spec-0246-all-runs-card-layout-rewrite.md:57`–`:69`. The spec 0246 merge commit `fdd2218`'s deploy run (`26595372492`) had its deploy job **cancelled** by the `deploy-main` concurrency group while a stale ancestor queue-state run was mid-deploy of the 1.59.0 tree; recovery required a manual `gh workflow run deploy.yml --ref main` (`26595775343`). This is the *prevention* counterpart of the *detection* fix in [spec 0211.3](specs/0211.3-deploy-concurrency-cancels-merge-commit-run.md), whose §5 Out of scope explicitly deferred this exact alternative.

---

## 1. Current state

`/dev-next` step 18 ("Merge-time state update", spec 0202 §2.2) writes the
`merged` lifecycle state to `origin/main` via the push-to-main plumbing
**before** step 19 runs `gh pr merge`. Two pushes land in step 18: a `set`
(`status=merged pr=… merged_at=…`) and an `append-event … merged`, each a
separate commit on `origin/main` driven by the message-only plumbing at
`scripts/spec_lifecycle/queue_state.py:393`. Read the skill body:

- **Step 18** at `~/.claude/skills/dev-next/SKILL.md:284`–`:290` runs
  `queue_state set --push-to-main NNNN status=merged pr=… merged_at=…` then
  `queue_state append-event --push-to-main NNNN merged …` — both **before** the
  step-19 `gh pr merge --admin --squash` at `~/.claude/skills/dev-next/SKILL.md:294`.
- **`deploy.yml` concurrency policy** at
  [.github/workflows/deploy.yml:27](.github/workflows/deploy.yml)–`:29`:
  `concurrency.group: deploy-main`, `cancel-in-progress: false`. Every push to
  `main` triggers a fresh `deploy.yml` run ([.github/workflows/deploy.yml:14](.github/workflows/deploy.yml)–`:16`).
  GitHub Actions' queue-collapse rule cancels all but the most-recent *pending*
  run in a group when ≥ 2 queue behind the in-flight job — independent of
  `cancel-in-progress`.
- **The spec 0212 buffer doctrine does not cover this window.** The skill's own
  comments at `~/.claude/skills/dev-next/SKILL.md:352` and `:390` scope the
  "no `--push-to-main` between merge and step 23" rule to the **post-merge**
  window only. The step-18 pushes are **pre-merge**, so the buffer doctrine
  leaves them racing.

**Pain points:**

- **Recurring real cancellation.** The pre-merge step-18 commits queue deploy
  runs immediately ahead of the merge commit. When a stale ancestor run is still
  deploying (or Actions cache flakiness slows the merge run's start), the
  `deploy-main` group cancels the merge-commit's deploy job — exactly what
  happened to spec 0246's `fdd2218` deploy run `26595372492`
  (`handoffs/2026-05-28-spec-0246-all-runs-card-layout-rewrite.md:60`).
- **0211.3's watch-side pivot is detection, not prevention.** [spec 0211.3](specs/0211.3-deploy-concurrency-cancels-merge-commit-run.md)
  teaches step 20 to pivot to the surviving run when the merge run is cancelled;
  it does not stop the cancellation from happening, and its correctness rests on
  the emergent "queue-state commits don't change Docker layers" property
  (0211.3 §1, the image-equivalence risk). Removing the *cause* shrinks the
  window the pivot has to cover.
- **Manual recovery this cycle.** The operator had to run
  `gh workflow run deploy.yml --ref main` by hand to deploy 1.60.0
  (`handoffs/2026-05-28-spec-0246-all-runs-card-layout-rewrite.md:65`). The
  cycle did not self-heal.

## 2. Target state

Only **one** `main` commit fires a deploy in the merge window: the squash-merge
commit itself. The `merged` lifecycle state is no longer pushed before the merge;
it is folded into the step-23 atomic `push-files-to-main`, exactly as the
post-merge buffer doctrine (spec 0212) already does for `pr_merged` /
`deploy_started` / handoff writes. This is the alternative (b) that
[spec 0211.3 §5](specs/0211.3-deploy-concurrency-cancels-merge-commit-run.md)
deferred.

### 2.1 — Convert step 18's two pushes to local-only buffered writes

In the skill body at `~/.claude/skills/dev-next/SKILL.md:284`–`:290`, drop the
`--push-to-main` flag from both the step-18 `set` and the step-18
`append-event merged`. They become local-only writes to the worktree's
`dashboard/queue-state.json`, mirroring the local-only `handoff_written` write
the post-merge window already buffers at `~/.claude/skills/dev-next/SKILL.md:442`.
The `merged_at` timestamp is still captured at merge time; only its *push* is
deferred.

### 2.2 — Flush the buffered `merged` state in the step-23 atomic push

Step 23 ("Post-deploy state update + handoff + archive", spec 0202 §2.2/§2.3,
spec 0210) at `~/.claude/skills/dev-next/SKILL.md:458`–`:474` already lands
`status=deployed`, `deployed_at`, `handover` and the archive moves in **one**
`push-files-to-main` commit. Because the local-only step-18 writes already
mutated `dashboard/queue-state.json` in the worktree, that file's content at
step 23 already carries `pr` + `merged_at` + the `merged` event. The step-23
`push-files-to-main --file dashboard/queue-state.json …` therefore flushes them
in the same atomic commit — no new push call is added; the existing one carries
the buffered fields. The only required change is ensuring `dashboard/queue-state.json`
is in step 23's `--file` set (it already is, per the step-23 invocation that
ships `status=deployed`).

### 2.3 — Detached-HEAD safety

The local-only step-18 writes mutate the queue worktree's working-tree copy of
`dashboard/queue-state.json` while it is detached at `origin/main` (spec 0210
baseline pose). This is the same buffering shape spec 0212 already relies on for
the post-merge window, where local-only events accumulate in the working tree and
are flushed by step 23. The branch-cleanup re-detach at
`~/.claude/skills/dev-next/SKILL.md:308` force-detaches because "the local
content already equals `origin/main`" — with this change the local content
additionally carries the buffered `merged` fields, which is safe because step 23
flushes them to `origin/main` before any later cycle reads them.

### 2.4 — Regression guard

Per the UI test doctrine's source-pattern convention extended to skill-body
specs (the same shape as `tests/test_spec_0211_3_concurrency_pivot.py` and
`tests/test_spec_0211_2_merge_sha_captured_at_merge_time.py:31`'s `_step_block`
helper), add `tests/test_spec_0247_pre_merge_no_push.py` asserting against the
live `~/.claude/skills/dev-next/SKILL.md` (SKIP when absent, matching the parent
tests):

- **Antipodal absence:** step 18's block contains **no** `--push-to-main` token
  (locks the pre-merge pushes out).
- **Positive:** step 18's block still contains `status=merged` and `merged_at`
  (the state is still computed, just buffered).
- **Breadcrumb:** the string `spec 0247` appears in a comment in step 18's block
  (locks the design citation so a future re-shuffle leaves a trail).

## 3. Stepwise migration

Each step independently shippable / revertable. The SKILL.md edits land in the
`/dev-next` cycle that runs this spec; the skill file is outside the repo, so the
git commit carries only the test + version bump + CHANGELOG.

- **Step 1: Drop `--push-to-main` from step 18's two writes** in
  `~/.claude/skills/dev-next/SKILL.md:284`–`:290` and add a `# spec 0247:
  buffer the merged state — flushed by step 23's push-files-to-main` comment.
  - Verified by: a `/dev-next` cycle for this spec produces exactly one
    deploy-triggering main commit in the merge window (the merge commit); the
    handoff records that no pre-merge queue-state deploy run was created.
- **Step 2: Confirm step 23's `push-files-to-main` already lists
  `dashboard/queue-state.json` in its `--file` set** at
  `~/.claude/skills/dev-next/SKILL.md:474`. If it does (it ships
  `status=deployed`), no edit is needed — the buffered `merged` fields ride along.
  If a future re-shuffle ever drops the file from the set, this step adds it back.
  - Verified by: post-cycle `dashboard/queue-state.json` on `origin/main` shows
    the spec's entry with `status=deployed`, `pr`, `merged_at`, and the `merged`
    event all present in the single step-23 commit.
- **Step 3: Add `tests/test_spec_0247_pre_merge_no_push.py`** (per §2.4), pure
  stdlib, SKIP-when-SKILL.md-absent.
  - Verified by: `uv run pytest tests/test_spec_0247_pre_merge_no_push.py -v`
    green (or SKIP in CI where the skill file is absent).
- **Step 4: PATCH version bump + CHANGELOG.** Bump `pyproject.toml`,
  `src/dual_research/__init__.py`, refresh `uv.lock`. Add a `## [X.Y.Z] — YYYY-MM-DD`
  section to `CHANGELOG.md` under `### Changed`, citing this spec: "`/dev-next`
  step 18 now buffers the `merged` lifecycle state locally and flushes it in the
  step-23 atomic push, so only the squash-merge commit triggers a deploy in the
  merge window (removes the pre-merge `--push-to-main` deploy-race)."
  - Verified by: the dashboard at `https://lexiz.github.io/dual-research/`
    renders the new CHANGELOG entry post-deploy.

## 4. Behavior preservation

- [ ] Existing `tests/` suite passes unchanged — `~/.claude/skills/dev-next/SKILL.md` is not in the pytest collection; the new test is additive.
- [ ] `tests/test_spec_0211_3_concurrency_pivot.py` (the detection-side fix) continues to pass — its step-20 pivot assertions are orthogonal to step 18's push removal; the pivot remains a defence-in-depth fallback for any residual race.
- [ ] The final `dashboard/queue-state.json` on `origin/main` after a cycle carries the same fields as today — `status=deployed`, `pr`, `merged_at`, `deployed_at`, `handover`, and the `merged` / `deployed` events — only the *timing* of the `merged` field's arrival on `origin/main` changes (step 23 instead of step 18). No field is dropped.
- [ ] `.github/workflows/deploy.yml` is unchanged — same `concurrency.group: deploy-main` at [.github/workflows/deploy.yml:27](.github/workflows/deploy.yml)–`:29`, same `cancel-in-progress: false`, same `flyctl deploy --remote-only`.
- [ ] `scripts/spec_lifecycle/queue_state.py` is unchanged — the `set` / `append-event` / `push-files-to-main` plumbing is reused as-is; only the skill body's choice of when to pass `--push-to-main` changes.
- [ ] The dashboard timeline still shows a `merged` event — it lands in the step-23 flush instead of a standalone pre-merge commit; the renderer at `scripts/spec_lifecycle/render_dashboard.py` orders by event `ts`, which is still captured at merge time.

## 5. Out of scope

**Explicit: this spec adds no new feature.** It does NOT add a new feature — no
new dashboard signal, no new `/dev-next` step, no new deploy mechanic. It moves
two existing pushes from the pre-merge window into the existing step-23 atomic
flush.

- **Always `workflow_dispatch` the deploy of main HEAD** (the handoff's second
  candidate fix, `handoffs/2026-05-28-spec-0246-all-runs-card-layout-rewrite.md:91`).
  Rejected as the primary fix: it would add a `gh workflow run deploy.yml --ref main`
  call to every cycle and a second watched run, racing the push-triggered run it
  is meant to replace. Removing the cause (the pre-merge pushes) is simpler and
  leaves the push-triggered deploy as the single source. (Deferred to: no
  follow-up planned — closed by this spec choosing the buffer-and-flush approach.)
- **Loosening `.github/workflows/deploy.yml`'s `concurrency.group` to per-SHA**
  — already rejected by [spec 0211.3 §5](specs/0211.3-deploy-concurrency-cancels-merge-commit-run.md)
  because per-SHA groups would let parallel deploys race the same Fly app.
  (Deferred to: no follow-up planned.)
- **Reworking the post-merge buffer window or step 23's atomic push** — the
  post-merge doctrine (spec 0212) is unchanged; this spec only extends the
  buffering backward to cover step 18. (Deferred to: no follow-up planned.)
- **Removing the 0211.3 watch-side pivot** now that the cause is gone — kept as
  defence-in-depth for any residual race (e.g. an out-of-band push to main during
  the merge window). (Deferred to: future spec only if the pivot is shown to be
  permanently dead code across many cycles.)
- **Touching `scripts/spec_lifecycle/queue_state.py` or `render_dashboard.py`** —
  no plumbing change is needed. (Deferred to: no follow-up planned.)

## 6. Risks

- **Risk: a later cycle reads `dashboard/queue-state.json` from `origin/main` and sees the spec stuck at the pre-step-18 status because the `merged` state was buffered and the cycle halted before step 23.** *Mitigation:* if the cycle halts between step 18 and step 23, the spec's `origin/main` status is whatever step 17/pre-merge left it (e.g. `in_progress`), and the dangling-branch / `merged`-state halt guard at `~/.claude/skills/dev-next/SKILL.md:339` already refuses the next cycle and surfaces the partial state to the operator — the same recovery posture as today, except the partial state is now "not yet merged on the board" rather than "merged but not deployed". The operator reconciles by hand exactly as the existing halt guard intends.
- **Risk: step 23's `push-files-to-main` does not include `dashboard/queue-state.json` in its `--file` set, so the buffered `merged` fields never reach `origin/main`.** *Mitigation:* step 23 already ships `status=deployed` via that file, so the file is necessarily in the set; the §2.4 antipodal-absence test plus the Step 2 verification (post-cycle `origin/main` shows `merged_at` + `merged` event) catch any drift.
- **Risk: the dashboard timeline shows the `merged` event with a later push-time than today, confusing operators reading commit times.** *Mitigation:* the renderer orders by the event's `ts` (captured at merge time), not by commit time, so the timeline ordering is unchanged; only the git commit that carries the event differs.
- **Risk: the cycle that ships this spec hits the very race it fixes (its own merge run is cancelled).** *Mitigation:* spec 0211.3's watch-side pivot is still in place and auto-recovers; the handoff records whether the race fired one last time before the fix took effect.
