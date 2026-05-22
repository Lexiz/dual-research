# Contributing — engineering workflow

Single-author repo. The discipline below exists because the codebase is moving from scaffold into orchestrator + UI territory and we want every change to be traceable, scoped, and versioned.

## Running in parallel with active development

If the autonomous orchestrator (or any active feature-branch work) is running in `~/dual-research/`, your `main` checkout may be on a feature branch with mid-implementation code. Running the CLI from that checkout can fail at import-time or yield analyses against unverified code.

Use a stable worktree to isolate CLI runs:

```bash
make stable-worktree         # one-time bootstrap
cd ~/dual-research-stable
uv run dual-research --notion <url>
```

The stable worktree shares git objects with the primary checkout (disk-cheap) but is pinned to a `stable` branch that doesn't move unless you explicitly fast-forward it. The orchestrator never touches `stable`.

To roll forward to the latest shipped main:

```bash
cd ~/dual-research-stable
git fetch origin
git merge --ff-only origin/main
uv sync --quiet
```

Runs from the stable worktree write to the same Supabase backend as the primary checkout, so they appear in the hosted dashboard identically.

## TL;DR

```
draft / queue → /dev-next → branch → implement → PR (admin squash-merge) → deploy → handoff → stop
```

Every change touching code, data, prompts, or infrastructure starts with a spec file. No exceptions. The spec lives in the repo forever — it is the architectural memory.

As of spec 0152, the workflow is automated via four user-facing skills (see `~/.claude/skills/`) — `/spec-draft`, `/spec-queue`, `/spec-promote`, `/dev-next`. The skills know which template to pick, validate the spec, set queue state, and drive the dev cycle. A dashboard at `https://lexiz.github.io/dual-research/` shows queue, history, and timings (regenerated on every push to `main` via `.github/workflows/dashboard.yml`).

The sections below describe the manual moves the skills perform — useful when something goes wrong and you need to drive a step by hand.

## Workflow

### 1. Write a spec

In normal operation, the `/spec-draft` or `/spec-queue` skill creates the file from a conversation. To do it manually:

- For a draft (no number reservation, lives at `specs/drafts/draft-NNN-<slug>.md`): copy frontmatter shape from another draft.
- For a queued dev spec: pick the right template under `specs/_templates/` (`new-feature.md`, `bug.md`, `refactoring.md`, `test.md`, or `breaking.md`) and copy it to `specs/NNNN-<slug>.md` where `NNNN` is the next zero-padded sequential number and `<slug>` is a short kebab-case description (under ~40 chars).

Fill in the front-matter (new schema as of spec 0152):

```yaml
kind: dev
spec: "NNNN"                            # quoted to survive YAML octal parsing
slug: <kebab>
title: <short imperative phrase>
type: new-feature | bug | refactoring | test | breaking
label: <mirror of type>                 # kept for legacy version-bump table compat
version_bump: MAJOR | MINOR | PATCH     # derived from type
status: queued | in_progress | merged | deployed | failed | cancelled
queue_position: <int, meaningful only while queued>
target_version: X.Y.Z | TBD
depends_on: []
complexity: S | M | L
created: YYYY-MM-DD                     # absolute date
pr: ""                                 # fill in after opening the PR
```

Body sections are type-specific. See the templates under [`specs/_templates/`](specs/_templates/) for the exact required shape per type. The validator at `scripts/spec_lifecycle/validator.py` enforces the contract per type — run it on any spec before queueing:

```bash
uv run python -m scripts.spec_lifecycle.validator specs/NNNN-<slug>.md
```

**Dev specs do not contain an "Open questions" section.** Questions are queue blockers — resolve them before queueing. Drafts may have an "Unresolved questions" section; the `/spec-promote` skill walks through each before promoting to a dev spec.

The template is a maximum, not a minimum. A typo fix can be three sentences. A new subsystem might be three pages.

### 2. Branch

```bash
git checkout main && git pull
git checkout -b spec/NNNN-<slug>
```

Branch name matches the spec filename. One spec ↔ one branch ↔ one PR.

### 3. Implement

Code, tests, docs. Update `CHANGELOG.md` with an `[Unreleased]` entry (or a versioned entry — see step 5). Bump `pyproject.toml` and `src/dual_research/__init__.py` version per the spec's `version_bump`.

Before opening the PR, flip the spec front-matter:
- `status: queued` → `status: in_progress` (during work) → `status: merged` (just before merge) → `status: deployed` (after `fly deploy` + handoff).

`/dev-next` does this automatically; you only do it manually for failure recovery.

### 4. Open the PR

```bash
gh pr create --label "spec/<label>" --body-file <<<...
```

PR title = the spec title. PR body uses `.github/PULL_REQUEST_TEMPLATE.md` and links to the spec. Apply the matching `spec/*` GitHub label.

Fill the spec's `pr:` front-matter field with the PR URL.

### 5. Version + CHANGELOG + in-app release notes

In the same PR:

- Bump version in `pyproject.toml` and `__init__.py` per the table below.
- Move the `[Unreleased]` CHANGELOG entry to a versioned heading: `## [X.Y.Z] — YYYY-MM-DD`. Add the new `[Unreleased]` placeholder back at the top.
- If the spec changes **user-visible** protocol behaviour (parallelism, phase semantics, caps, tiebreak, retry rules) or ships a visible UI feature, append a new entry to the `VERSION_NOTES` array at the top of [`src/dual_research/ui/static/how-it-works.jsx`](src/dual_research/ui/static/how-it-works.jsx). Newest entry first; format mirrors existing entries. Specs that only touch internal plumbing can skip — `VERSION_NOTES` is the user-facing "what changed in the protocol or UI" log, not a duplicate of the CHANGELOG.

| Spec label    | Version bump | Example                |
| ------------- | ------------ | ---------------------- |
| `breaking`    | MAJOR        | 0.4.2 → 1.0.0          |
| `new-feature` | MINOR        | 0.4.2 → 0.5.0          |
| `bug`         | PATCH        | 0.4.2 → 0.4.3          |
| `refactoring` | PATCH        | 0.4.2 → 0.4.3          |
| `test`        | PATCH        | 0.4.2 → 0.4.3          |

Pre-1.0 still follows strict semver; we do not collapse 0.x changes.

### 6. Admin squash-merge

```bash
gh pr merge --admin --squash --delete-branch
```

`--squash` keeps `main` history linear and readable: one merge commit per spec. The squash subject = the PR title = the spec title.

After merge: `git checkout main && git pull` and you're ready for the next spec.

## Labels (GitHub)

Created once via `gh label create` (the `0001-engineering-workflow` spec did this). Color codes are conventional, not load-bearing.

- `spec/new-feature` — green
- `spec/bug` — red
- `spec/refactoring` — blue
- `spec/test` — yellow
- `spec/breaking` — dark red

## Branch protection

Not enforced via GitHub API. The discipline is "don't push directly to main; always go through a spec PR." If we slip, a future spec wires `gh api repos/Lexiz/dual-research/branches/main/protection` with admin bypass.

## Commit messages

Commit messages inside a feature branch are working-state — they get squashed away. The merge subject (= PR title = spec title) is what shows on `main`. Don't over-engineer per-commit messages inside a spec branch; they're disposable.

## Edge cases

- **Multi-spec PR.** Don't. Split into separate PRs in dependency order.
- **Spec that touches no code.** Still legitimate (e.g., changing this workflow itself). Bump version anyway because the repo's effective behaviour changed.
- **PR that decides not to merge.** Mark spec `status: cancelled` and merge ONLY the spec file (with the rationale appended to the body). Captures the decision durably.
- **Hotfix.** Same workflow, but the spec body can be terse and the branch can ship in an hour. The discipline is the spec FILE, not its length.

## Skills + dashboard (spec 0152 onwards)

The four skills under `~/.claude/skills/` drive the workflow:

- **`/spec-draft`** — in an authoring session, captures the current thread into `specs/drafts/draft-NNN-<slug>.md`. No branch, no dev-number reservation. Triggers: "save this as a draft", "park this idea", "draft spec from this".
- **`/spec-queue`** — in an authoring session, classifies the type, populates the right template, validates, previews in chat, commits to `main` as `specs/NNNN-<slug>.md` with `status: queued`. Triggers: "queue this for dev", "make the dev spec", "this is ready to ship".
- **`/spec-promote <draft-id>`** — takes a draft, walks unresolved questions, validates, writes the dev spec, deletes the draft.
- **`/dev-next`** — in your queue-control session, runs the next queued spec end-to-end (pre-flight → reconcile → branch → implement → tests → PR → admin merge → deploy → handoff → stop). Triggers: "next", "go", "kick off the next one".

Authoring sessions run from the worktree at `~/dual-research-author/` so they never touch the queue session's checked-out branch. The queue session runs from `~/dual-research/` (this checkout).

The dashboard at `https://lexiz.github.io/dual-research/` shows the queue, in-flight spec, recently shipped, drafts, and aggregate metrics. It's regenerated on every push to `main` via `.github/workflows/dashboard.yml` — no manual deploy step.

Spec lifecycle code lives in `scripts/spec_lifecycle/` (validator, picker, reconciler, dashboard renderer, event log). Tests at `tests/spec_lifecycle/`.
