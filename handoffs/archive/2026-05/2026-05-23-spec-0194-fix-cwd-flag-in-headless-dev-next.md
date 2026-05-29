---
spec: "0194"
date: 2026-05-23
version: 1.34.1
pr: "https://github.com/Lexiz/dual-research/pull/198"
---

# Spec 0194 — Fix: drop `--cwd` flag in headless dev-next launcher — shipped

`/dev-queue-run`'s per-iteration subprocess no longer dies in ~1 s on
`error: unknown option '--cwd'`. The supervisor's launch contract for the
installed `claude` CLI (v2.1.79) now correctly omits the unsupported flag
and pins cwd via the shell instead.

## What landed

- **[scripts/spec_lifecycle/checkpoint.py:129](../scripts/spec_lifecycle/checkpoint.py)** — `build_headless_command()` returns `["claude", "-p", "/dev-next"]`. The `project_dir` parameter is kept in the signature for callers that thread it into `subprocess.Popen(..., cwd=...)`; the docstring was rewritten to spell out the new contract.

- **[~/.claude/skills/dev-queue-run/SKILL.md](~/.claude/skills/dev-queue-run/SKILL.md)** — Per-iteration recipe rewritten:

  ```bash
  cd /Users/alexlisitzky/dual-research && \
    DR_DEV_NEXT_NONINTERACTIVE=1 claude -p "/dev-next" \
    > "$LOG" 2>&1
  ```

  This change is to user-machine state (not in the repo), so it does NOT appear in PR #198's diff. The fix is local to this machine; future drains will use the corrected recipe.

- **[tests/spec_lifecycle/test_checkpoint.py](../tests/spec_lifecycle/test_checkpoint.py)** — `test_build_headless_command_shape` updated to assert the new argv; new regression guard `test_build_headless_command_does_not_pass_cwd_flag` asserts `"--cwd" not in cmd`. Full suite: 1589 passed.

- **CHANGELOG / version** — `1.34.0` → `1.34.1` (PATCH per bug type).

## Live smoke

```
$ uv run python -c "from scripts.spec_lifecycle.checkpoint import build_headless_command; print(build_headless_command('0001', '/tmp/log', '/some/project'))"
['claude', '-p', '/dev-next']
```

Confirmed: no `--cwd` in argv.

## What this DOES NOT fix

- **Headless `claude -p` auth failure (401).** Orthogonal issue, explicitly out of scope per spec §6. The shell that invokes the supervisor exports an `ANTHROPIC_API_KEY` (value redacted) that returns 401. Unsetting it doesn't help — the keychain-based OAuth that authenticates the interactive Claude Code session doesn't propagate to spawned `claude -p` subprocesses. Until the user either fixes the env API key (regenerate at console.anthropic.com, update `~/.zshrc`) or configures CLI-side auth, `/dev-queue-run` will get past the `--cwd` error only to 401 on the next line. The interactive `/dev-next` flow (which this very session uses) is unaffected.

- **Removing `project_dir` from the helper signature.** Defer to spec 0191's Python supervisor extraction, which will thread it into `subprocess.Popen(cwd=...)`.

## Deploy notes

- `fly deploy` hit `failed to get lease on VM <id>: machine not found` twice before succeeding on the third attempt, the same lease-drift pattern seen during spec 0170. Existing machines were on a stale image group; once fly converged the cluster, bluegreen swapped cleanly.
- Post-deploy `scripts/sweep_stale_blues.sh`: `sweep: no stale blues on dual-research-alex`.
- Smoke: `GET https://dual-research-alex.fly.dev/` → 200.
- Image: `dual-research-alex:deployment-01KS92SW0HMYSNRDQ9MPNFYN9Q` running on two machines.
