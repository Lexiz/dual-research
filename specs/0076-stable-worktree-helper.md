---
spec: 0076
title: Stable-worktree helper — isolate CLI runs from active orchestrator/feature-branch work
label: dev-experience
version-bump: MINOR
status: in-progress
target-version: 0.69.0
created: 2026-05-18
pr: ""
---

# Spec 0076 — Stable-worktree helper (CLI parallelism)

## Context

**This is a developer-experience spec, not a UI spec. Several arc-wide
conventions do NOT apply — read the "Overrides to standard workflow"
section below carefully.**

Today, the user's `~/dual-research/` working tree is the same one the
autonomous orchestrator operates on. While an arc is running, that
working tree spends ~75 minutes (per 6-spec arc) cycling through
feature branches (`spec/NNNN-…`) and pulling main between specs.

If the user wants to run `uv run dual-research --notion <url>` during
that window:

- Python imports source from `~/dual-research/src/dual_research/`.
- During import (~1-2 s startup) the working tree may be on a feature
  branch with mid-implementation code -> ImportError, parse errors,
  or analyses run against unverified code.
- After import the process is fine (modules are cached in-memory),
  but any subsequent file read (fixture, run artifact) sees the
  current branch's contents.

The fix is `git worktree`: a second working directory at
`~/dual-research-stable/` that shares the same `.git/` (disk-cheap)
but stays on a `stable` branch the orchestrator never touches. The
user runs the CLI from the stable worktree; the orchestrator keeps
operating in `~/dual-research/` exactly as today.

This spec ships:
1. A bootstrap script `scripts/setup-stable-worktree.sh` that creates
   the stable branch (if missing), adds the worktree, and runs
   `uv sync` inside it.
2. A `Makefile` target `make stable-worktree` for convenience.
3. A `CONTRIBUTING.md` section documenting the pattern and the
   roll-forward workflow.
4. A brief README pointer.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Stable worktree at `~/dual-research-stable/` by default.** Script accepts optional first arg to override path. | Fixed default = simple docs; arg = power-user flexibility. |
| D2  | **`stable` branch created at current `main` if missing.** Script is idempotent. | Bootstrap once, re-run safely. |
| D3  | **Worktree pinned to `stable` branch, not detached HEAD.** User fast-forwards manually. | Mental model = "stable" is a manual ratchet, never auto-advances. |
| D4  | **`uv sync` runs in the worktree** at the end of setup. | One-stop bootstrap. |
| D5  | **Makefile target `stable-worktree` wraps the script.** | `make` for muscle-memory; script for explicitness. |
| D6  | **CONTRIBUTING.md section "Running in parallel with active development"** added. | One search away from the answer. |
| D7  | **README brief pointer** in the existing "Development" section. | Discoverability without README bloat. |
| D8  | **No `runs/` symlinking.** Separate `runs/` per worktree; Supabase backend is shared. | Don't get clever with cross-worktree filesystem links. |
| D9  | **Script is bash, not Python.** | Right tool for a 30-line bootstrap. |
| D10 | **Script uses `set -euo pipefail` + `git rev-parse --show-toplevel`.** | Defensive bash. |
| D11 | **No pytest test for the script.** `bash -n` syntax check in CI. | Right level of rigor. |
| D12 | **Existing path detected gracefully.** Already-registered worktree = no-op exit 0. | Idempotency. |
| D13 | **No version bump in the worktree.** Standard versioning in primary checkout. | No special case. |
| D14 | **No UI changes.** No cache-bust. No preview-verify. No design-system alignment. No VERSION_NOTES. | Dev-experience spec. |

## Overrides to standard workflow

- **Preview-verify: SKIP.** No UI changes.
- **M1 design-system alignment: N/A.** No tokens, no primitives.
- **VERSION_NOTES: SKIP.** No user-visible behavior.
- **Cache-bust: SKIP.** No UI changes.
- **PR label: `dev-experience`** (not `spec/new-feature`).

## Files touched

- `scripts/setup-stable-worktree.sh` — **new**. Bootstrap helper.
- `Makefile` — **new**. Single `stable-worktree` target.
- `CONTRIBUTING.md` — amend. Add parallel-run section.
- `README.md` — amend. One-line pointer.
- `.github/workflows/tests.yml` — amend. Add `bash -n` step.
- `CHANGELOG.md` — new version entry.
- `pyproject.toml` + `src/dual_research/__init__.py` — version bump to 0.69.0.
- `uv.lock` — regenerated.

## Out of scope

- Orchestrator refactor to use ephemeral worktrees (blocked by hard constraint).
- Cross-platform support.
- Automatic stable-branch fast-forward.
- `runs/` symlinking or cross-pollination.

## Test plan

- Existing pytest suite stays green (744+ baseline).
- `bash -n scripts/setup-stable-worktree.sh` passes (CI step).
- Manual verification of script in implementing session.

## Risks

- R1: Existing `~/dual-research-stable` from prior experimentation — D12 handles.
- R2: Existing `stable` branch — detected and reused.
- R3: `uv sync` failure in worktree — clear error, exit non-zero.

## Design system alignment (per arc M1)

**N/A — dev-experience spec.** No tokens, primitives, or surface changes.
