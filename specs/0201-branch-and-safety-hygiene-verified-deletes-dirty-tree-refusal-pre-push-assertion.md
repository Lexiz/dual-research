---
kind: dev
spec: "0201"
slug: branch-and-safety-hygiene-verified-deletes-dirty-tree-refusal-pre-push-assertion
title: "Branch & safety hygiene — verified deletes, dirty-tree refusal, pre-push branch assertion"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: in_progress
depends_on: ["0198", "0199"]
complexity: M
created: 2026-05-24
queued_at: ""
started_at: "2026-05-23T23:13:07Z"
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: "orchestrator-hardening-series-2026-05-23"
promoted_from_draft: ""
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0201 — Branch & safety hygiene: verified deletes, dirty-tree refusal, pre-push branch assertion

> **Type:** refactoring  |  **Complexity:** M  |  **Depends on:** 0198 (validator gates this spec passes), 0199 (decimal branch-ID grammar used by the assertion)
> **Bump:** PATCH — internal safety nets only; success-path behaviour unchanged.
> **Evidence:** 2026-05-22 dirty-tree commit incident (`933673d`, reverted in `b0ae421`) recorded in the `feedback_dirty_tree_not_intentional` memory; current `gh pr merge --delete-branch` step at `~/.claude/skills/dev-next/SKILL.md` step 19 has no post-merge verification; no `git push` step asserts branch identity, leaving resume-mode silent-checkout-failure unprotected.

## 1. Current state

Three independent gaps in the `/dev-next` orchestrator have compounded over ~70 spec runs. Each one is latent today and has at least one concrete failure path; one of them already fired and lost real queued work.

### 1.1 Stale remote branches — unverified delete
The current merge step relies on `gh pr merge --admin --squash --delete-branch` at `~/.claude/skills/dev-next/SKILL.md` step 19 to clean up the feature branch. There is no verification — if the `--delete-branch` flag silently fails (transient API issue, permissions glitch, race against a re-push), the skill flips the spec to `deployed` anyway and the dangling ref accumulates on origin.

**Current origin count, verified at author time:** `git ls-remote --heads origin 'spec/*' | wc -l` returns `0`. An earlier audit cited 44 dangling branches; whatever drained them happened informally (likely a side effect of recent admin merges propagating cleanly). The gap is latent rather than actively bleeding, but the structural fix is the same either way and the backstop sweeper still earns its keep.

### 1.2 Dirty working tree committed as "intent"
On 2026-05-22, `/dev-next` pre-flight found a non-empty `git status` at step 2 (`~/.claude/skills/dev-next/SKILL.md` line 30: "Confirm working tree clean (`git status -s` empty)"), interpreted the user's "run it" as license to commit, and pushed commit `933673d` to main. That commit dropped spec 0177 (dashboard-redesign-v3) and demoted spec 0176 (login-screen-v2) back to draft. The user lost real queued work and reverted via `b0ae421`. Documented in the memory file at `/Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/feedback_dirty_tree_not_intentional.md`. The skill has no hard rule against this interpretation — only a positive policy ("clean tree expected") with no defined behaviour on the negative branch.

### 1.3 No pre-push branch-identity assertion
The skill's `git push` calls (notably step 17 `git push -u origin spec/NNNN-<slug>` and step 18's frontmatter-update push on the same branch) assume the checkout is on the expected branch. In resume mode (`~/.claude/skills/dev-next/SKILL.md` step 5 / step 9 resume branch — handoff at `scripts/spec_lifecycle/checkpoint.py`), if `git checkout <branch>` fails silently (branch deleted upstream, stale local ref, hook interference), the orchestrator continues to implement and push against whatever happens to be checked out — potentially `main`. The supervisor at `scripts/queue_drain_supervisor.py` doesn't catch this either; it inspects exit codes, not branch identity.

### 1.4 Source traceability

| source item | source quote/ref | spec section |
| --- | --- | --- |
| Verified branch delete after merge | user brief "The fix — three parts" item 1 | §2.1 |
| Dirty-tree refusal in pre-flight | user brief "The fix — three parts" item 2; `feedback_dirty_tree_not_intentional` memory | §2.2 |
| Pre-push branch-identity assertion | user brief "The fix — three parts" item 3 | §2.3 |
| One-time cleanup of stale remote branches (now: backstop sweeper) | user brief "One-time cleanup" | §2.4 + §9 |
| Risk: sweeper deletes unmerged branch | user brief "Risks" item 1 | §6.1 |
| Risk: dirty-tree refusal feels obstructive | user brief "Risks" item 2 | §6.2 |
| Risk: verified-delete retry loops forever | user brief "Risks" item 3 | §6.3 |
| Baked-in: stash preferred over commit | user brief "Three baked-in design decisions" item 1 | §2.2 |
| Baked-in: verified delete is post-merge, not best-effort | user brief "Three baked-in design decisions" item 2 | §2.1 |
| Baked-in: branch-identity assertion is hard halt | user brief "Three baked-in design decisions" item 3 | §2.3 |

## 2. Target state

### 2.1 Verified branch delete after merge

After `gh pr merge --admin --squash --delete-branch` succeeds at `~/.claude/skills/dev-next/SKILL.md` step 19, append a verification block that asserts the branch is gone from both remote and local refs. The block accepts both integer and decimal spec-IDs per the spec 0199 grammar (`^[0-9]{4}(\.[0-9]+)?$`):

```bash
BRANCH="spec/${SPEC_ID}-${SLUG}"   # SPEC_ID is NNNN or NNNN.M
remote_left=$(git ls-remote --heads origin "$BRANCH" | wc -l | tr -d ' ')
local_left=$(git branch --list "$BRANCH")
if [ "$remote_left" -ne 0 ] || [ -n "$local_left" ]; then
    # one retry — explicit delete on both sides
    git push origin --delete "$BRANCH" 2>/dev/null || true
    git branch -D "$BRANCH" 2>/dev/null || true
    remote_left=$(git ls-remote --heads origin "$BRANCH" | wc -l | tr -d ' ')
    local_left=$(git branch --list "$BRANCH")
    if [ "$remote_left" -ne 0 ] || [ -n "$local_left" ]; then
        echo "ERROR: $BRANCH persists after retry (remote=$remote_left local='$local_left') — halting"
        exit 1
    fi
fi
```

On halt, the spec frontmatter stays at `status: merged` — it is **not** flipped to `deployed`. A spec is not "deployed" until the branch is gone from both sides. This is part of the baked-in decision "verified delete is post-merge, not best-effort." The next `/dev-next` run will refuse to start (one spec at `in_progress`/`merged` is the usual halt signal) and surface the dangling branch to the user.

### 2.2 Dirty-tree refusal at pre-flight

Replace the prose at `~/.claude/skills/dev-next/SKILL.md` step 2 ("Confirm working tree clean — `git status -s` empty") with an explicit halt-with-options policy. The same gate applies in `/dev-queue-run` pre-flight step 2 (`~/.claude/skills/dev-queue-run/SKILL.md` line 23 — "same gates as `/dev-next`") and must be spelled out there too so the next reader does not miss it.

The new behaviour:

- Run `git status --porcelain`. If empty → proceed (unchanged).
- If non-empty → **halt**. Surface the file list verbatim (do not summarise, do not interpret).
- Offer exactly two safe paths:
  1. `git stash push -u -m "dev-next pre-flight stash $(date -Iseconds)"` — preferred (reversible).
  2. An explicit, scoped user instruction that names (a) the exact file list to commit and (b) the commit message preview.
- Ambiguous phrases ("run it", "go ahead", "do it", "run it as-is", "these are real edits") are **not** commit license. The orchestrator must not synthesise a "queue reshuffle" commit, a "cleanup" commit, or any other interpretation of dirty state. The 2026-05-22 incident is the canonical counter-example.

### 2.3 Pre-push branch-identity assertion

Before every `git push` issued from a feature branch in `/dev-next` (step 17's `-u` push, step 18's frontmatter-update push, and any in-spec checkpoint push from step 15-CP), assert that `git branch --show-current` equals the expected `spec/${SPEC_ID}-${SLUG}`:

```bash
EXPECTED="spec/${SPEC_ID}-${SLUG}"
ACTUAL="$(git branch --show-current)"
if [ "$ACTUAL" != "$EXPECTED" ]; then
    echo "ERROR: expected branch $EXPECTED, on '$ACTUAL' — halting before push"
    exit 1
fi
git push -u origin "$EXPECTED"
```

Halt is hard — no warning, no retry. Per the baked-in decision: "soft warnings get ignored." The 2026-05-22 incident demonstrates the failure mode soft warnings produce.

Scope clarification: the assertion applies to **feature-branch pushes only**. The post-merge pushes at step 24 (`git push origin HEAD:main` style — explicit destination) are governed by their explicit refspec and do not need the same assertion; they target `main` deliberately. The assertion specifically protects pushes that name the spec branch implicitly via the current checkout.

### 2.4 Backstop sweeper script

New executable at `scripts/sweep_stale_branches.sh`:

- Lists remote branches matching `spec/*` via `git ls-remote --heads origin 'spec/*'`.
- For each, calls `gh pr view "$branch" --json state,mergedAt`.
- Deletes from origin only if `state == "MERGED"`.
- Prints one line per branch: `swept spec/NNNN-foo (merged YYYY-MM-DD)` or `kept spec/NNNN-foo (state=OPEN)` or `kept spec/NNNN-foo (no PR)`.
- Exit code = count of branches kept-but-not-merged that an operator should investigate (`0` = clean origin).

Modelled on the existing `scripts/sweep_stale_blues.sh` (precedent for a short shell sweeper invoked from skill steps and runnable standalone). Idempotent. Safe to re-run.

The sweeper is a **backstop**, not the primary mechanism. §2.1 is the primary — the sweeper is recurring insurance against the rare case where the post-merge verified delete itself loses to a race that survives one retry, plus a recovery path for any historical drift.

## 3. Stepwise migration

Each step is independently shippable / revertable.

- **Step 1:** Ship `scripts/sweep_stale_branches.sh`. Make executable. Dry-run against origin (current count 0 — confirms the no-op path works). Commit.
- **Step 2:** Amend `~/.claude/skills/dev-next/SKILL.md` step 2 with the dirty-tree refusal policy (§2.2). Commit.
- **Step 3:** Amend `~/.claude/skills/dev-queue-run/SKILL.md` step 2 prose to spell out the dirty-tree refusal explicitly (inherits from /dev-next per the existing "same gates" line). Commit.
- **Step 4:** Amend `~/.claude/skills/dev-next/SKILL.md` step 19 with the verified-delete block (§2.1). Commit.
- **Step 5:** Amend `~/.claude/skills/dev-next/SKILL.md` step 17, step 18, and the in-spec checkpoint push in step 15-CP with the branch-identity assertion (§2.3). Commit.
- **Step 6:** Run `scripts/sweep_stale_branches.sh` against origin as the test-plan acceptance check — expected output: "no stale branches" / exit 0. Evidence captured in the handoff.

Each step lands as its own commit on the spec branch so a partial revert is mechanically cheap if any one piece misbehaves in the first post-merge cycle.

## 4. Behavior preservation

This is a refactoring spec. **Existing success-path behaviour is unchanged**; only failure-path behaviour tightens. The acceptance bar is "the next spec after this one still ships end-to-end with no new friction on the happy path."

- [ ] Existing clean-tree pre-flight still proceeds without any halt at the new dirty-tree gate (verified by the very next `/dev-next` invocation after this spec deploys — its own pre-flight must not regress).
- [ ] Existing single-spec merge cycle still completes through to `deployed` (verified by this spec's own merge — the verified-delete block must pass on the first attempt; if it doesn't, this spec ships broken and we know immediately).
- [ ] Decimal-grammar branch IDs from spec 0199 (`NNNN.M`) work for both the assertion (§2.3) and the delete-verify block (§2.1) — the `SPEC_ID` variable accepts either form because both are interpolated as opaque strings into `spec/${SPEC_ID}-${SLUG}`.
- [ ] `uv run pytest tests/ -q` green. No new test files; no behaviour change in code paths covered by the existing suite (skill files and shell scripts are not unit-tested today).

Because the changes live in skill prose and a new shell script — neither of which the existing pytest suite exercises — the acceptance evidence is **dry-run + the next live cycle**, not new automated tests. Test plan §9 captures the dry-runs.

## 5. Out of scope

**Explicit: no new feature ships here.** This spec does NOT add any new feature surface — observable orchestrator behaviour on the success path is unchanged; only failure-path behaviour tightens. No new commands, no new UI, no new dashboard events, no new public surface.

- **Status-commit noise reduction on main.** Deferred to spec 0202 (next spec in the orchestrator-hardening series, brief pending from the user).
- **Handoff doc lifecycle.** Deferred to spec 0202.
- **Rewriting git history of already-merged commits.** Out of scope — only dangling branch refs get cleaned. The squashed commits on `main` stand as-is.
- **Replacing `gh pr merge --delete-branch` with a different merge primitive.** Out of scope — we add verification around the existing call, we do not change the merge.
- **Adding the assertion to merges/pushes from outside `/dev-next`** (manual operator pushes, `/spec-queue` author-side pushes). Out of scope — those have different invariants (`/spec-queue` pushes to `main` deliberately from a detached HEAD; manual pushes are operator judgement).
- **Audit/recovery for the 44 historically stale branches the user's earlier audit referenced.** The current origin count is 0; whatever drained them is done. No retroactive audit needed.

## 6. Risks

### 6.1 Sweeper accidentally deletes an unmerged branch
**Mitigation:** per-branch `gh pr view "$branch" --json state,mergedAt` confirmation; only `state == "MERGED"` triggers delete. Branches with `state == "OPEN"` or with no PR at all are reported and kept, and contribute to the script's non-zero exit code so an operator notices. The script never deletes "by name pattern alone."

### 6.2 Dirty-tree refusal feels obstructive when there is legitimate WIP
**Mitigation:** `git stash push -u -m "..."` is the offered first-class path; it is one line, reversible via `git stash pop`, and preserves both tracked and untracked changes. The file list is surfaced verbatim so the operator can immediately see what is at risk. If the WIP is genuine, the operator stashes, runs the cycle, then pops — total friction is two commands.

A more structural mitigation already exists: the authoring worktree at `/Users/alexlisitzky/dual-research-author/` is the intended home for in-progress edits. The queue checkout at `/Users/alexlisitzky/dual-research/` is supposed to be a clean tree at rest. Dirty state there is almost always stray.

### 6.3 Verified-delete retry loops forever on a broken GitHub API
**Mitigation:** the retry is capped at exactly one attempt (the explicit `git push origin --delete` + `git branch -D` block above), then the script halts with a clear error. There is no `while`-loop, no exponential backoff, no second retry. If the API stays broken across the single retry, the operator deletes by hand and flips the spec status manually — surfacing the breakage to a human is the correct outcome.

### 6.4 Branch-identity assertion fires false positive
The assertion is a hard halt — if it ever fires on a correct checkout, the cycle aborts and the operator must intervene. **Mitigation:** the assertion compares two simple strings: `git branch --show-current` against `spec/${SPEC_ID}-${SLUG}`. Both inputs are deterministic at the point of comparison. The only way a false positive can fire is if the orchestrator has the wrong `SPEC_ID` / `SLUG` in scope — which would itself be a serious bug worth halting on.

## 7. User stories

- As a dev shipping a spec, I want the feature branch deleted from both local and remote after merge, with verification, so that no stale branches accumulate on GitHub and the "deployed" state is trustworthy.
- As a dev kicking off `/dev-next` after a previous session left dirty state, I want the orchestrator to refuse to commit that state — preserve it via stash and ask me what to do — so that queued specs cannot be silently dropped or demoted.
- As a dev whose resume-mode checkout silently failed, I want the orchestrator to refuse to push to whatever branch happens to be checked out, so that spec-branch-targeted commits cannot leak onto `main`.

## 8. BDD acceptance scenarios

- **Given** a PR is squash-merged via `/dev-next` step 19, **WHEN** the post-merge verification block at the new §2.1 runs, **THEN** `git ls-remote --heads origin spec/NNNN-<slug>` returns empty AND `git branch --list spec/NNNN-<slug>` returns empty AND the spec frontmatter is flipped to `deployed`.
- **Given** `/dev-next` pre-flight finds `git status --porcelain` non-empty, **WHEN** the user replies with an ambiguous phrase such as "run it" or "go ahead", **THEN** the orchestrator halts, lists the dirty files verbatim, offers `git stash` as the preferred recovery, and does NOT create any commit.
- **Given** the working tree is on `main` (not the expected `spec/NNNN-<slug>`) at the step-17 push point, **WHEN** `/dev-next` reaches that push step, **THEN** it halts with a clear error message and does NOT execute the push.
- **Given** the sweeper script `scripts/sweep_stale_branches.sh` runs against origin, **WHEN** each candidate branch's PR is confirmed merged via `gh pr view`, **THEN** that branch is deleted from origin; **AND** any branch whose PR is OPEN or missing is reported on stdout and contributes to a non-zero exit code without being deleted.

## 9. Test plan — acceptance evidence required at merge time

- [ ] `scripts/sweep_stale_branches.sh` is executable, runs against origin, and exits 0 with output indicating no stale branches found. Current pre-cycle baseline: `git ls-remote --heads origin 'spec/*' | wc -l` returns `0`.
- [ ] Dry-run of the dirty-tree refusal: in the queue checkout, synthesize a non-empty `git status` (e.g. `touch .scratch-dirty-test`), invoke `/dev-next`, confirm the skill halts at pre-flight step 2, lists `.scratch-dirty-test`, and offers stash. Confirm no commit is created. Clean up.
- [ ] Dry-run of the branch-identity assertion: from `main`, set `SPEC_ID=0201`, `SLUG=foo`, run the assertion snippet from §2.3 inline, confirm it prints the error and exits 1. Then `git checkout spec/0201-...` (the actual cycle branch), re-run, confirm it succeeds silently.
- [ ] Verified-delete block: the merge of this spec's own PR exercises §2.1. After `gh pr merge --admin --squash --delete-branch` returns, the new verification block must report both `git ls-remote --heads origin spec/0201-...` and `git branch --list spec/0201-...` empty on the first attempt (no retry needed). This is the live acceptance test.
- [ ] `uv run pytest tests/ -q` green. No code paths covered by the existing suite change behaviour.
- [ ] Cycle pre-flight on the **next** spec after 0201 deploys completes cleanly with no halt at the new dirty-tree gate (proves §2.2's clean-tree fast path is unchanged).
