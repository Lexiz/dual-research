---
spec: "0152"
date: 2026-05-22
version: 1.17.0
pr: "https://github.com/Lexiz/dual-research/pull/175"
---

# Handover — Spec 0152 — Spec lifecycle system v1 (v1.17.0)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#175](https://github.com/Lexiz/dual-research/pull/175) (merged, squash, branch deleted)
- **Spec:** [specs/0152-spec-lifecycle-system-v1.md](../specs/0152-spec-lifecycle-system-v1.md)
- **Version:** `1.16.0 → 1.17.0` (MINOR — new operational surface, no breaking changes to the DR app, CLI, schema, or model code).
- **Tests:** 1462 passing (1432 pre-existing + 30 new for `tests/spec_lifecycle/`).

## What landed

A self-contained spec lifecycle system that replaces every prior ad-hoc workflow piece. Pre-spec there were four independent surfaces (`scripts/queue-autonomous/`, `src/dual_research/queue_v2/`, `specs/_kickoff-prompts/`, the host-side `prep-kickoff` skill); post-spec there's one: four skills, one validator, one dashboard, one filesystem-as-database.

### The four skills (installed at `~/.claude/skills/`)

- **`/spec-draft`** — captures the current authoring conversation into `specs/drafts/draft-NNN-<slug>.md`. Triggers: "save this as a draft", "park this idea", "draft spec from this". No branch, no dev-number reservation.
- **`/spec-queue`** — classifies the spec type, populates the matching template under `specs/_templates/`, runs the validator, previews to the user, commits `specs/NNNN-<slug>.md` to `main` with `status: queued`. Triggers: "queue this for dev", "make the dev spec", "this is ready to ship".
- **`/spec-promote <draft-id>`** — walks unresolved questions, validates against the dev-spec contract, writes the dev spec, deletes the draft. Triggers: "promote draft NNN to dev", "move this draft into the queue".
- **`/dev-next`** — runs the next queued spec end-to-end (pre-flight, reconcile against prior handoff, branch, implement, tests, PR, admin merge, fly deploy, write handoff, stop). Triggers: "next", "go", "kick off the next one".

### Type-specific templates

`specs/_templates/{new-feature,bug,refactoring,test,breaking}.md`. Each has a tight required-section contract enforced by `scripts/spec_lifecycle/validator.py`:

- **new-feature**: Context · Proposed change · Out of scope · Test plan · Risks (+ optional UX/Behavior and Data/Schema).
- **bug**: Reproduction (Expected/Actual/Evidence) · Root cause · Fix · Regression-prevention test · Blast radius · Out of scope · Risks.
- **refactoring**: Current state · Target state · Stepwise migration · Behavior preservation · Out of scope (must explicitly disclaim new features) · Risks.
- **test**: Coverage gap · Test approach · What it would catch · Risks.
- **breaking**: Inherits new-feature + Compatibility break · Migration plan · Rollback plan.

Dev specs do NOT carry "Open questions" — questions are queue blockers, resolved before queueing. Drafts can.

### Filesystem-as-database

No `state.json`. Spec frontmatter is the source of truth for status / queue position / timestamps / PR / handoff. The dashboard renders directly from frontmatter + event sidecars (`dashboard/events/<spec>.jsonl`). Every state transition is a git commit to `main`.

### Dashboard

Static HTML generator at [`scripts/spec_lifecycle/render_dashboard.py`](../scripts/spec_lifecycle/render_dashboard.py). Workflow at [`.github/workflows/dashboard.yml`](../.github/workflows/dashboard.yml) triggers on push to `main` and publishes to GitHub Pages.

**⚠ GitHub Pages not yet enabled.** The Lexiz/dual-research repo is currently PRIVATE, and GitHub Pages on the free plan only supports public repos (`gh api … pages` returns 422 "Your current plan does not support GitHub Pages for this repository"). To bring the dashboard online: either flip the repo to public (`gh repo edit Lexiz/dual-research --visibility public`) or upgrade the plan. Once Pages is enabled with source = "GitHub Actions", the workflow on `main` will publish automatically.

### Worktree layout

- **`~/dual-research/`** — primary checkout. Only place `/dev-next` runs.
- **`~/dual-research-author/`** — created via `git worktree add ~/dual-research-author main`. Currently in detached-HEAD state (see "Known limitations" below). Spec authoring runs here.
- **`~/dual-research-stable/`** — existing stable CLI worktree per CONTRIBUTING. Unchanged.

### Session-naming integration

New title format for DR sessions: `[DR · <ctx> · O/X] body` where `<ctx>` ∈ `{scratch, NNNN, draft-NNN, queue, queue · NNNN in flight, queue · NNNN failed, queue · idle}`.

`~/.claude/hooks/auto-prefix-session.py` now recognises this format alongside the legacy `[DR-O]` shape and leaves spec-tagged titles alone.

`~/.claude/hooks/cleanup-session-prefixes.py` parses lifecycle-tagged sessions in `list` and derives open/closed from spec frontmatter in `apply` (no LLM call for spec-tagged sessions; LLM still used for `scratch`).

### Parked pending work

Four drafts capture pre-lifecycle pending work. Each is ready for `/spec-promote` once the user is satisfied with the content (or can be discarded by `rm`-ing the file).

- **`specs/drafts/draft-001-summary-tab-v2.md`** ← was untracked `specs/0152-summary-tab-v2.md`; ~625 lines of new-feature spec. Fully fleshed out; should pass the validator.
- **`specs/drafts/draft-002-login-screen-v2.md`** ← was untracked `specs/0153-login-screen-v2.md`; ~423 lines of new-feature spec. Fully fleshed out.
- **`specs/drafts/draft-003-timeline-refresh.md`** ← thin placeholder over `prototypes/timeline-iteration/`. Has unresolved questions; will need iteration before promote.
- **`specs/drafts/draft-004-critique-refresh.md`** ← thin placeholder over `prototypes/critique-iteration/`. Same — has unresolved questions; needs iteration.

### Removed

- `scripts/queue-autonomous/` (5 files), `scripts/run-queue-v2.sh`.
- `src/dual_research/queue_v2/` (13 modules including the sub-package `dashboard/`).
- `tests/queue/` (4 test files).
- `docs/queue-v2/` (2 docs files).
- `queue/` runtime dir (state.json, runs/, etc. were git-ignored; the placeholder `.gitkeep` is gone).
- `specs/_kickoff-prompts/` (the 0140–0147 hand-pasted prompts).
- `~/.claude/skills/prep-kickoff/` (the host-side kickoff-prompt generator).
- `~/.claude/projects/.../memory/feedback_prep_kickoff_trigger.md`.

Net: −5286 lines, +5366 lines across 87 files (mostly content replacement).

## How to verify

```bash
# Run the validator on the spec itself
cd /Users/alexlisitzky/dual-research
uv run python -m scripts.spec_lifecycle.validator specs/0152-spec-lifecycle-system-v1.md

# Render the dashboard locally
uv run python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out /tmp/dr-dash
open /tmp/dr-dash/index.html

# Full test suite
uv run pytest tests/ -q
```

## Known limitations / follow-up

- **GitHub Pages config gate.** As noted above, the repo is private and the free plan doesn't allow Pages. The workflow YAML is in place; flip the repo to public (or upgrade) and Pages with source = "GitHub Actions" comes online automatically.
- **Author worktree branch conflict.** When the primary checkout returns to `main` after a `/dev-next` cycle, both the primary and the author worktree want to be on `main` — git refuses two worktrees on the same branch. Worked around manually this PR by `git -C ~/dual-research-author switch --detach`. The proper fix is to update the `/spec-*` skills to operate on detached HEAD pointing at `origin/main`: `git fetch && git checkout --detach origin/main && <write file> && git commit && git push HEAD:main`. Should be a small follow-up spec.
- **No `/spec-cancel` or `/spec-reorder` skills.** Out-of-scope per spec 0152 §4. Hand-edit frontmatter for v1. Add skills if they become frequent.
- **Cycle-time metric for backfilled specs is blank.** 0149/0150/0151 have `deployed_at` from git log but `started_at` is empty (we never recorded it). The dashboard shows "—" for their cycle. New specs going through `/dev-next` will have full data.

## Next test sequence

In a fresh authoring session at `~/dual-research-author/`:

1. *"promote draft 001 to dev"* → should produce `specs/0153-summary-tab-v2.md` with `status: queued, queue_position: 1`. Draft removed.
2. *"promote draft 002 to dev"* → `0154-…, queue_position: 2`.
3. (Optional) *"promote draft 003 to dev"* → validator should refuse (draft too thin / unresolved questions) and surface actionable gaps.

Then switch to the queue session at `~/dual-research/` and say *"go"* — `/dev-next` should pick 0153, walk pre-flight + reconcile, branch, implement, ship.
