# Queue v2 — operator runbook

The single command the product owner runs to fire the queue and open
the dashboard:

```bash
cd /Users/alexlisitzky/dual-research
./scripts/run-queue-v2.sh
```

What it does, in order:

1. `cd` to the repo root.
2. Verify the working tree is clean and on `main`. Abort with a
   helpful diff if not.
3. Verify all 13 spec files exist at `specs/0092-*.md` …
   `specs/0104-*.md`. Abort if any are missing (means the
   `specs-v2-draft` branch hasn't merged yet).
4. Verify the design-system briefing bundle is present at
   `docs/design-system-v2/` (README, Design System v2.html,
   notion-issues/). Abort if missing (means the `design-system-v2-
   briefing` branch hasn't merged yet).
5. Verify the queue Python package is importable
   (`from dual_research.queue_v2 import cli, state, timings`).
6. Seed `queue/state.json` with the 13 spec numbers — or, if the
   file already exists, resume from where the previous run left
   off.
7. Launch the dashboard at <http://127.0.0.1:8089/> (background;
   logs to `queue/dashboard.log`, pid in `queue/dashboard.pid`).
8. Print the dashboard URL plus a paste-ready prompt for the
   separate Claude Code session that drives the 8-step lifecycle.

## What the script does NOT do

It does **not** run Step 1 of the first spec. The queue is staged
but the lifecycle is driven by a separate Claude Code session
(reason: the lifecycle's Implement + Verify + PR + Deploy steps
need the full agent toolchain — file edits, preview_* MCP, git/gh
commands — and that work lives best in a dedicated session that
the operator monitors via the dashboard).

## Abort + resume

- **Abort the dashboard**: `Ctrl-C` in the terminal pane, or
  ```bash
  kill "$(cat queue/dashboard.pid)"
  ```
- **Resume**: re-run `./scripts/run-queue-v2.sh`. The queue picks up
  from `queue/state.json`, including the in-flight spec and which
  step it stopped at. Per-spec artifacts under `queue/runs/<NNNN>/`
  are preserved so partial Verify shots and rewrite logs survive.
- **Start fresh**: remove `queue/state.json` and `queue/runs/`
  before re-running.

## When a step fails

Step 5 Verify is the most common failure surface — a screenshot
verdict comes back `fail`. The queue halts the active spec, the
dashboard shows the failing row, and the operator goes back to
Step 4 Implement to fix the regression. Re-run Step 5 from the
CLI:

```bash
uv run python -m dual_research.queue_v2.cli verify-begin <NNNN>
# ... re-capture shots ...
uv run python -m dual_research.queue_v2.cli verify-finalize <NNNN>
```

`verify-begin` is idempotent: it overwrites the shot plan and
preserves previously captured PNGs that haven't been re-taken.

Other failure modes:

| Step | Failure | What to do |
|---|---|---|
| 1 Read | Spec file missing | `git pull` on main, confirm specs/ has the file. |
| 2 Reason | Previous handover missing | Halt; finish the prior spec cleanly first. |
| 4 Implement | Out-of-scope path | Either rescope via Step 3 Rewrite, or split the change into a follow-up spec. |
| 6 PR | gh auth error | `gh auth status`; refresh token if expired. |
| 7 Deploy | CI red | Check the failing job log; fix the regression; CI re-runs on push. |
| 7 Deploy | Health probe doesn't converge | Check `fly logs`; consider `fly deploy --build-only` to retry the build, or roll back. |

## Manual step invocation

Every step is callable in isolation for tests and recovery:

```bash
uv run python -m dual_research.queue_v2.cli <subcommand> [args]
```

Full subcommand list at `src/dual_research/queue_v2/cli.py`.

## Where the artefacts live

- `queue/state.json` — the queue position + active spec + per-step
  status. Recreated by `cli init`; updated by every step.
- `queue/timings.json` — accumulated per-step durations. Read by
  the dashboard "Avg" column. Empty arrays render as `—`.
- `queue/runs/<NNNN>/` — per-spec artefacts:
  - `spec-parsed.json`
  - `reason-notes.md`
  - `rewrite-log.md` (only if Step 3 ran)
  - `verify-plan.json`
  - `verify-report.md`
  - `screenshots/NN-<viewport>-<theme>.png`
  - `pr-body.md`, `pr-url.txt`
  - `deploy-log.md`
  - `handover-path.txt` — pointer to the final handover under
    `handoffs/`.
- `handoffs/<YYYY-MM-DD>-spec-<NNNN>-<slug>.md` — Step 8 output;
  committed to `main` alongside the squash-merge.
- `queue/dashboard.log` — uvicorn output.
- `queue/dashboard.pid` — backgrounded dashboard process PID.

## Dashboard

Right-panel columns:

| Col | Meaning |
|---|---|
| # | Step ordinal (1–8) |
| Step | Read · Reason · Rewrite · Implement · Verify · PR · Deploy · Handover |
| Status | pending · in-progress · done · skipped · failed |
| Avg | Median across all completed runs in `queue/timings.json` (`—` on a fresh queue) |
| Elapsed | Live counter on the in-progress step; final duration on done steps |
| Detail | Step-specific: alignment-note count · diff stats · PR URL · screenshot thumbnails · deployed version |

The left panel lists the 13 specs in queue order; the active spec
is highlighted, completed specs grey-out, failed specs flag red.

When the queue empties, the right panel collapses to a terminal
summary computed from `queue/timings.json`.
