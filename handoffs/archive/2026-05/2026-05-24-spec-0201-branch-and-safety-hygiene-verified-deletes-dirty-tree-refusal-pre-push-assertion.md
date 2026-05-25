---
spec: "0201"
date: 2026-05-24
version: "1.41.2"
pr: "https://github.com/Lexiz/dual-research/pull/229"
---

# Spec 0201 — Branch & safety hygiene: verified deletes, dirty-tree refusal, pre-push branch assertion (v1.41.2)

Refactoring spec. Three independent safety nets land in `/dev-next` (plus one inherited gate in `/dev-queue-run`), and a backstop sweeper lands in this repo. Success-path orchestrator behavior is unchanged — only failure-path behavior tightens.

## What shipped

### In-repo (the PR diff)

- **`scripts/sweep_stale_branches.sh`** (new, +75 lines, mode 0755). Backstop sweeper for `spec/*` branches on origin. Lists branches via `git ls-remote --heads`, queries each PR's state via `gh pr view --json state,mergedAt`, deletes only when `state == "MERGED"`. Branches with `OPEN`, `CLOSED`-not-merged, or no PR are reported and kept; the script's exit code equals the count of branches kept-but-not-merged (`0` = clean origin). Modelled on `scripts/sweep_stale_blues.sh` (the precedent for short shell sweepers).
- **`pyproject.toml` + `src/dual_research/__init__.py`** — PATCH bump `1.41.1` → `1.41.2`.
- **`CHANGELOG.md`** — new `## [1.41.2] — 2026-05-24` section under `[Unreleased]` summarising the four-part change (verified delete + dirty-tree refusal + branch-identity assertion + backstop sweeper).
- **`uv.lock`** — auto-updated for the version bump (own-package entry only).
- **`specs/0201-…md`** — frontmatter walked `queued` → `in_progress` (started_at `2026-05-23T23:13:07Z`) → `merged` (merged_at `2026-05-23T23:20:01Z`, pr URL) → `deployed` (deployed_at + handover pointer).

### Out-of-band (skill prose, not repo-tracked)

`~/.claude/skills/dev-next/SKILL.md` and `~/.claude/skills/dev-queue-run/SKILL.md` are edited in place — they live in the user's Claude config dir, not in this repo. The skill prose changes are non-revertable via `git revert`; the spec body documents them precisely so they can be re-derived.

- **`~/.claude/skills/dev-next/SKILL.md` step 2** — replaces the prose "Confirm working tree clean (`git status -s` empty)" with an explicit hard-halt policy on non-empty `git status --porcelain`. Surface the file list verbatim; offer exactly two recovery paths — stash (preferred) or an explicit named-files-with-message instruction. Ambiguous phrases ("run it", "go ahead", "do it", "run it as-is") are NOT commit license. The 2026-05-22 incident (`933673d` → `b0ae421`) is cited inline as the canonical counter-example, with a link to [`feedback_dirty_tree_not_intentional`](/Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/feedback_dirty_tree_not_intentional.md).
- **`~/.claude/skills/dev-queue-run/SKILL.md` step 2** — spells out the same dirty-tree gate inline (rather than inheriting it implicitly from `/dev-next`), with the same recovery options + incident citation. Spec 0201 §2.2 line 92-93 called this out specifically — inheritance was ambiguous and worth duplicating.
- **`~/.claude/skills/dev-next/SKILL.md` step 19** — appends a verified-delete block after `gh pr merge --admin --squash --delete-branch`. Asserts `git ls-remote --heads origin spec/${SPEC_ID}-${SLUG}` and `git branch --list ...` are both empty; one explicit retry via `git push origin --delete` + `git branch -D`, then halt with `status: merged` (not `deployed`) on persistence. Branch-ID grammar accepts integer or decimal per spec 0199 (`SPEC_ID` is interpolated as an opaque string).
- **`~/.claude/skills/dev-next/SKILL.md` steps 17, 18, 15-CP** — pre-push branch-identity assertion. Before each feature-branch push, assert `$(git branch --show-current) == "spec/${SPEC_ID}-${SLUG}"`; hard halt on mismatch. Scope explicitly limited to feature-branch pushes; the post-merge `git push origin main` is governed by its explicit refspec and stays unguarded.

## Why this exists

Three independent gaps in the `/dev-next` orchestrator had compounded over ~70 spec runs.

1. **Stale remote branches via unverified delete** — `gh pr merge --delete-branch` is best-effort; if it silently fails (transient API issue, permissions, race against re-push), the spec flips to `deployed` anyway and the dangling ref accumulates. An earlier audit cited 44 dangling branches; the current origin count is `0` (whatever drained them was informal). Latent today; structural fix is the same either way and the backstop sweeper still earns its keep.
2. **Dirty working tree committed as "intent"** — on 2026-05-22, `/dev-next` pre-flight found a non-empty `git status`, interpreted the user's "run it" as license to commit, and pushed `933673d` to main. That commit dropped spec 0177 (dashboard-redesign-v3) and demoted 0176 (login-screen-v2) back to draft. Reverted in `b0ae421`. Documented in `feedback_dirty_tree_not_intentional`.
3. **No pre-push branch-identity assertion** — in resume mode, if `git checkout <branch>` silently fails (branch deleted upstream, stale local ref, hook interference), the orchestrator continues to implement and push against whatever happens to be checked out — potentially `main`. The `dev-queue-run` supervisor doesn't catch this either; it inspects exit codes, not branch identity.

## Acceptance evidence

Per spec §9 test plan:

- ✅ **`scripts/sweep_stale_branches.sh` executable, exits 0 with no-op output.** Live run vs origin: `sweep: no stale spec/* branches on origin`, exit `0`. Current baseline `git ls-remote --heads origin 'spec/*' | wc -l` = `0`. Confirms the no-op path works.
- ✅ **Branch-identity assertion dry-run, mismatch case.** Inline expansion with `SPEC_ID=0201 SLUG=foo` on the actual cycle branch: prints `ERROR: expected branch spec/0201-foo, on 'spec/0201-branch-and-safety-hygiene-...' — halting before push`, exit `1`. Hard halt as designed.
- ✅ **Branch-identity assertion dry-run, match case.** Same EXPECTED + ACTUAL: passes silently, exit `0`. (No output is the success signal — assertion is invisible on the happy path.)
- ✅ **Verified-delete block on this PR's own merge.** Live acceptance: after `gh pr merge --admin --squash --delete-branch` returned, `remote_left=0`, `local_left=''` on the **first attempt** — no retry triggered. The block fires correctly and is invisible on the happy path.
- ✅ **`uv run pytest tests/ -q` green.** 1774 passed in 20.89s. No code paths covered by the existing suite changed behavior — skill prose and shell scripts are not unit-tested today.
- ⏳ **Next-cycle pre-flight on clean tree completes without halt at the new dirty-tree gate.** Pending — validated live by the very next `/dev-next` invocation after this spec deploys. Its pre-flight must not halt at the new gate; if it does, this spec regressed the happy path and we know immediately.

## Deploy notes

- Strategy: rolling (per spec 0200). Both machines (`2872d65a660408`, `879634f0700698`) cycled through `Updating → started → smoke checks → good state` in sequence. No old-cohort lease errors.
- Post-deploy sweep: `sweep: no stale blues on dual-research-alex`. Image-based fallback found no off-image machines; the cluster converged cleanly.
- Smoke: `curl https://dual-research-alex.fly.dev/` → HTTP 200 in 33.7s (cold-boot post-rollout is expected to be slower than steady state; subsequent requests return in normal time).
- Fly's pre-deploy "app is not listening on 0.0.0.0:8080" warning is unrelated to this spec — pre-existing behavior, harmless.

## Mechanical layout of the PR

Two commits on the spec branch (plus the merged frontmatter commit), squash-merged onto main:

- `c000179` — step 1 sweeper script.
- `f6f858f` — version bump + CHANGELOG (steps 2–5 deliverables live in skill files out-of-band).
- `2b39b37` — frontmatter merged flip + uv.lock + trailing events.

The spec's §3 stepwise migration originally suggested one commit per step. Three commits is the practical reality: most of steps 2–5 live in `~/.claude/skills/dev-{next,queue-run}/SKILL.md` and are not repo-tracked; the only in-repo deliverables for those steps are the version/CHANGELOG bundle. The verified-delete block (step 4) and branch-identity assertion (step 5) are entirely out-of-band.

## Deviations from spec

None of substance. The §3 stepwise migration plan was authored assuming the skill files were in-repo; in practice they live in `~/.claude/skills/` and ride out-of-band. That has been the convention since spec 0152 (and was the same on spec 0200, which similarly amended `~/.claude/skills/dev-next/SKILL.md`). The deliverables specified in §2.1, §2.2, §2.3, §2.4 all landed; the per-step commit granularity in §3 collapsed to three commits for the in-repo subset.
