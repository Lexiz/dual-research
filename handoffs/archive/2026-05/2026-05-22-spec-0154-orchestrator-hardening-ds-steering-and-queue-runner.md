---
spec: "0154"
date: 2026-05-22
version: 1.19.0
pr: "https://github.com/Lexiz/dual-research/pull/177"
---

# Handover — Spec 0154 — Workflow hardening: DS steering, /dev-queue-run, project CLAUDE.md (v1.19.0)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#177](https://github.com/Lexiz/dual-research/pull/177)
- **Merge commit:** `002f914`
- **Cycle time:** ~9 minutes (started 12:57:33Z, deployed 13:06:33Z)

## What landed

### In-repo (this PR)

- **`CLAUDE.md` at repo root.** Auto-loaded by every Claude Code session opened in this repo. Three sections — design system, versioning + CHANGELOG, spec workflow + worktree split.
- **Version bump to 1.19.0.** Per the spec's `version_bump: MINOR`. `pyproject.toml` and `src/dual_research/__init__.py` updated in lockstep.
- **CHANGELOG entry written directly under `## [1.19.0] — 2026-05-22`** — no `[Unreleased]` accumulation, per the new convention encoded in `CLAUDE.md` and `/dev-next` step 15b.

### Host-side (NOT in the PR — lives under `~/.claude/` and `~/dual-research-author/`)

- **`~/.claude/skills/spec-queue/SKILL.md`** — step 1 restructured into three sub-reads (1a classify with no pause, 1b scope scan, 1c DS check for UI specs); step 4 inlines the explicit `version_bump` mechanical mapping.
- **`~/.claude/skills/spec-promote/SKILL.md`** — step 2 no longer pauses for type confirmation; step 4 picks up scope-scan (4a) and DS-check (4b) sub-steps; step 6 inlines the `version_bump` mapping.
- **`~/.claude/skills/spec-draft/SKILL.md`** — step 1 captures scope-exclusion markers and UI-scope flag; explicit "do not pause — invocation IS the confirmation" line added.
- **`~/.claude/skills/dev-next/SKILL.md`** — step 1 fast-forwards local `main` via `git pull --ff-only origin main`; step 15 split into 15a DS gate (reads `design-system/SPEC.md`, requires DS citations + tokens-only + dual-write of components) and 15b version + CHANGELOG (each spec is its own release, no `[Unreleased]` accumulation).
- **`~/.claude/skills/dev-queue-run/SKILL.md`** (new) — drains the whole queue from a single greenlight, halts on first failure. The skill description matched on this very session for confirmation.
- **`~/.claude/settings.json`** — `additionalDirectories` adds `/Users/alexlisitzky/dual-research-author`; `permissions.allow` mirrors the `cd && *` allow family for the author worktree (fly, flyctl, gh, git, pytest, python, python3, uv); adds `Edit(/Users/alexlisitzky/.claude/skills/**)` and `Write(/Users/alexlisitzky/.claude/skills/**)`.
- **`~/dual-research-author/.claude/settings.local.json`** (new) — mirrors the queue worktree's project-local permissions.
- **`feedback_pause_between_specs` memory** — Exception note appended: `/dev-queue-run` is the explicit opt-out, default `/dev-next` behavior unchanged.

## Tests

Full `uv run pytest tests/ -q` — **1474 passed**. No new automated tests added; the spec's test plan is a manual checklist of skill behaviors (printed inline in the PR body).

## Deploy notes

- `fly deploy` completed cleanly on the first attempt this time — no machines-API timeout. Both machines on `deployment-01KS7S98W4X4*` running v1.19.0. Smoke: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.19.0","backend":"supabase"}`.

## Verification still owed (manual)

The spec's test plan items are user-facing skill behaviors that will only fully manifest in future sessions. The ones to watch for:

- `/spec-queue` and `/spec-promote` should print classification + reasoning in the final report without ever pausing.
- UI specs created post-0154 must carry DS citations. `/dev-next` step 15a halts implementation if a UI spec lacks them.
- `/dev-queue-run` should refuse from the author worktree and ask exactly one confirmation from the queue worktree.
- New Claude Code sessions opened in `/Users/alexlisitzky/dual-research/` should pick up `CLAUDE.md` as an auto-loaded codebase doc.

## Queue state at handoff

- **0155 is queued** ("Fix: lifecycle skills' session-title stamping is unimplemented"). Was committed in a parallel author session while 0154 was in flight; merged into `main` alongside 0154's PR.
- Per `feedback_pause_between_specs`: this cycle stops here. Next `/dev-next` (or `/dev-queue-run`) is on the user.

## File map

```
CLAUDE.md                                       # new (repo root)
CHANGELOG.md                                    # [1.19.0] section
pyproject.toml                                  # 1.19.0
src/dual_research/__init__.py                   # 1.19.0
specs/0154-orchestrator-hardening-...md         # status: deployed
dashboard/events/0154.jsonl                     # full eleven-stage stream
handoffs/2026-05-22-spec-0154-...md             # this file

# Host-side (not in repo)
~/.claude/skills/spec-queue/SKILL.md            # 1a/1b/1c restructure
~/.claude/skills/spec-promote/SKILL.md          # no-pause + scope/DS
~/.claude/skills/spec-draft/SKILL.md            # scope + UI flag + no pause
~/.claude/skills/dev-next/SKILL.md              # pull --ff-only + step 15 split
~/.claude/skills/dev-queue-run/SKILL.md         # new
~/.claude/settings.json                         # author dir + ~/.claude/skills/** writes
~/dual-research-author/.claude/settings.local.json  # new, mirrors queue
~/.claude/projects/-Users-alexlisitzky/memory/feedback_pause_between_specs.md  # Exception note
```
