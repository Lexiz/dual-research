---
kind: dev
spec: "0194"
slug: fix-cwd-flag-in-headless-dev-next
title: "Fix: build_headless_command passes --cwd which the installed claude CLI rejects"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 1
depends_on: []
complexity: S
created: 2026-05-23
queued_at: "2026-05-23T00:05:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: queue-drain-blocked-investigation
promoted_from_draft: ""
---

# Spec 0194 — Fix: `build_headless_command` passes `--cwd` which the installed claude CLI rejects

> **Type:** bug  |  **Severity:** P1 — blocks every `/dev-queue-run` invocation  |  **Affects:** spec-lifecycle plumbing
> **Bump:** PATCH — bug fix; no behavior change beyond unblocking the supervisor.
> **Evidence:** `runs/queue-drain/2026-05-22T23-20-42Z-spec-0170.log` line 1: `error: unknown option '--cwd'`. `claude --help` for v2.1.79 lists every flag — no `--cwd` in the surface. Spec 0186 §7 explicitly anticipated this drift mode and pinned [scripts/spec_lifecycle/checkpoint.py:147](scripts/spec_lifecycle/checkpoint.py) (`build_headless_command`) plus [~/.claude/skills/dev-queue-run/SKILL.md](~/.claude/skills/dev-queue-run/SKILL.md)'s per-iteration recipe as a paired patch site.

---

## 1. Reproduction

**Environment:** macOS, installed `claude` CLI v2.1.79, dual-research queue worktree at `/Users/alexlisitzky/dual-research/`.

**Steps:**
1. From the queue worktree, with the queue non-empty, invoke `/dev-queue-run`.
2. Greenlight the drain at the supervisor's pre-flight confirmation.
3. Observe the first per-iteration subprocess.

**Expected:** the subprocess reads the queue head, calls `/dev-next`, ships the spec end-to-end.

**Actual:** subprocess exits `RC=1` in ~1 second. The per-iteration log file at `runs/queue-drain/<ts>-spec-NNNN.log` contains a single line: `error: unknown option '--cwd'`. The supervisor halts on first failure per the skill's contract; the queue stays untouched.

## 2. Root cause hypothesis

`scripts.spec_lifecycle.checkpoint.build_headless_command` (current behaviour at [scripts/spec_lifecycle/checkpoint.py:129](scripts/spec_lifecycle/checkpoint.py) — see implementation at lines 147-153) returns:

```python
return [
    "claude",
    "-p",
    "/dev-next",
    "--cwd",
    str(project_dir),
]
```

The `--cwd` flag is not present in `claude --help` for the installed CLI version (verified: `claude --version` → `2.1.79 (Claude Code)`). The CLI's option parser exits 1 on the first unknown option without ever reading the prompt or invoking the slash command.

`~/.claude/skills/dev-queue-run/SKILL.md`'s "Per-iteration recipe" section also uses `--cwd /Users/alexlisitzky/dual-research` directly in its shell example. Both sites must change together per spec 0186 §7 ("Headless `claude -p` runtime drift").

## 3. Fix

Two paired changes:

1. **`scripts/spec_lifecycle/checkpoint.py:147`.** Drop `--cwd` from the argv. The caller must instead set the subprocess working directory via `subprocess.Popen(..., cwd=...)` (the Python API) or `cd <dir> && ...` (shell).

   ```python
   # before
   return [
       "claude",
       "-p",
       "/dev-next",
       "--cwd",
       str(project_dir),
   ]

   # after
   return [
       "claude",
       "-p",
       "/dev-next",
   ]
   ```

   The `project_dir` parameter stays in the function signature for now (callers may want it for `cwd=` plumbing in a Python-based supervisor — see spec 0191's planned extraction). If `project_dir` is unused inside the function body after this edit, leave it; do not delete the parameter as part of this bug fix (out of scope per §6).

2. **`~/.claude/skills/dev-queue-run/SKILL.md`.** Update the "Per-iteration recipe" code block to anchor cwd in the shell instead of passing `--cwd`:

   ```diff
   - DR_DEV_NEXT_NONINTERACTIVE=1 claude -p "/dev-next" \
   -   --cwd /Users/alexlisitzky/dual-research \
   -   > "$LOG" 2>&1
   + cd /Users/alexlisitzky/dual-research && \
   +   DR_DEV_NEXT_NONINTERACTIVE=1 claude -p "/dev-next" \
   +   > "$LOG" 2>&1
   ```

   Also strip the surrounding prose that mentions `--cwd` as the cwd-pinning mechanism — replace with a one-line note that the shell `cd` is the cwd anchor.

## 4. Regression-prevention test

Add an assertion to [tests/spec_lifecycle/test_checkpoint.py](tests/spec_lifecycle/test_checkpoint.py) that `--cwd` is NOT present in the argv returned by `build_headless_command`. Today's test (search for `build_headless_command` in that file) only asserts the shape; add a tightening assertion:

- [ ] **Test: `test_build_headless_command_does_not_pass_cwd_flag`** — calls `build_headless_command("0001", "/tmp/log", "/some/project")`, asserts `"--cwd" not in result`. Fails on current `main`, passes after the §3 patch.

## 5. Blast radius

- `build_headless_command` is called only from the `/dev-queue-run` skill body (currently as a documented argv shape; no Python caller imports it for invocation yet — spec 0191 plans that extraction).
- The SKILL.md change is text only; agents reading the skill on next invocation will get the corrected recipe.
- No production code paths in `src/dual_research/` are touched.
- No data schema, no event semantics, no fly deploy.

## 6. Out of scope

- **Headless `claude -p` auth (401)**: orthogonal environmental issue (parent CC session uses OAuth from macOS keychain; subprocess sees an invalid `ANTHROPIC_API_KEY` and can't fall back). This is a Claude Code CLI / user-environment issue, not a dual-research bug. Surface to the user; do not attempt to fix here.
- **Removing the now-unused `project_dir` parameter from `build_headless_command`**: cosmetic refactor; defer to spec 0191's Python supervisor extraction, which will reintroduce `project_dir` usage via `subprocess.Popen(..., cwd=...)`.
- **Updating spec 0186's body** to reflect the corrected recipe: spec bodies are historical artifacts; the §7 drift mitigation is being honored by the paired-patch this spec executes.

## 7. Risks

- **Forgetting one of the two paired sites.** Mitigated by §3 listing both explicitly and the §4 regression test asserting the helper's contract.
- **Skill prose drift.** The SKILL.md "Per-iteration recipe" code block is the load-bearing contract; agents reading the skill follow what's in that block. Make sure the rewritten block is syntactically copy-pasteable.
