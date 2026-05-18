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
spec → branch → implement → PR (admin squash-merge) → next spec
```

Every change touching code, data, prompts, or infrastructure starts with a spec file. No exceptions. The spec lives in the repo forever — it is the architectural memory.

## Workflow

### 1. Write a spec

Copy `specs/TEMPLATE.md` to `specs/NNNN-<slug>.md`, where `NNNN` is the next zero-padded sequential number and `<slug>` is a short kebab-case description (under ~40 chars).

Fill in the front-matter:

```yaml
spec: NNNN
title: <short imperative phrase>
label: new-feature | bug | refactoring | test | breaking
version-bump: MAJOR | MINOR | PATCH    # derived from label
status: proposed
target-version: X.Y.Z                  # the version this spec ships in
created: YYYY-MM-DD                    # absolute date
pr: ""                                 # fill in after opening the PR
```

Body sections (omit `Open questions` if there are none): Context, Proposed change, Out of scope, Test plan, Risks, Open questions.

The template is a maximum, not a minimum. A typo fix can be three sentences. A new subsystem might be three pages.

### 2. Branch

```bash
git checkout main && git pull
git checkout -b spec/NNNN-<slug>
```

Branch name matches the spec filename. One spec ↔ one branch ↔ one PR.

### 3. Implement

Code, tests, docs. Update `CHANGELOG.md` with an `[Unreleased]` entry (or a versioned entry — see step 5). Bump `pyproject.toml` and `src/dual_research/__init__.py` version per the spec's `version-bump`.

Before opening the PR, flip the spec front-matter:
- `status: proposed` → `status: in-progress` (during work) → `status: merged` (just before merge)

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
- **PR that decides not to merge.** Mark spec `status: rejected` and merge ONLY the spec file (with the rejection rationale appended to the body). Captures the decision durably.
- **Hotfix.** Same workflow, but the spec body can be terse and the branch can ship in an hour. The discipline is the spec FILE, not its length.
