---
spec: 0001
title: Engineering workflow — specs, branches, PRs, semver
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.2.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/1"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0001 — Engineering workflow

## Context

The codebase is moving from the initial scaffold (skeleton, ingest, agents, protocol) into the orchestrator and then a UI. Past changes landed as direct commits to `main` while the foundation was small enough to inspect at a glance. From here forward — orchestrator state machine, event bus, web search wiring, FastAPI/SSE backend, frontend — the surface is large enough that we need a documented process that locks in:

- What we are changing and why (recorded in repo, not just in chat scrollback)
- A predictable cadence of small, reviewable PRs
- Semver discipline so the version on disk tracks the substance of changes
- A `CHANGELOG.md` that summarises what shipped in each version without reading every commit

The cost of this process at this size is small. The cost of not having it once a UI is wired up is high (untraceable changes, unbounded PR scope, version stuck at 0.1.0 forever).

## Proposed change

### 1. Spec-first workflow

Every code, schema, prompt, or infrastructure change starts with a spec file at `specs/NNNN-<slug>.md`, where:

- `NNNN` is a zero-padded 4-digit sequential number (this spec is `0001`)
- `<slug>` is a short kebab-case description (under ~40 chars)

The spec has YAML front-matter with the fields:

```yaml
spec: NNNN              # the number, again, for parsers
title: <imperative>     # short title
label: new-feature | bug | refactoring | test | breaking
version-bump: MAJOR | MINOR | PATCH
status: proposed | in-progress | merged
target-version: X.Y.Z   # version this spec ships in
created: YYYY-MM-DD     # absolute date
pr: "<URL>"             # filled in after PR is opened
```

The spec body uses the structure in `specs/TEMPLATE.md`: Context, Proposed change, Out of scope, Test plan, Risks, Open questions.

Specs are checked into the repo. They are durable architectural memory, not throwaway docs.

### 2. Labels and version bumps

GitHub labels with one-to-one mapping to spec labels:

| Spec label      | GitHub label       | Version bump | When to use                                                  |
| --------------- | ------------------ | ------------ | ------------------------------------------------------------ |
| `new-feature`   | `spec/new-feature` | MINOR        | New capability — endpoint, command, panel, module            |
| `bug`           | `spec/bug`         | PATCH        | Fix that restores expected behaviour                         |
| `refactoring`   | `spec/refactoring` | PATCH        | Internal change, no observable behaviour change              |
| `test`          | `spec/test`        | PATCH        | New tests, expanded fixtures, test infrastructure            |
| `breaking`      | `spec/breaking`    | MAJOR        | CLI / data / API shape changes that break existing callers   |

Pre-1.0 still uses semver semantics; we do not collapse all 0.x changes to patch.

### 3. Branch and PR mechanics

- Branches off `main`, named `spec/NNNN-<slug>` to match the spec file
- Spec and implementation land in the **same PR**, never separately
- PR title = the spec title (used as the squash-merge commit subject)
- PR body uses `.github/PULL_REQUEST_TEMPLATE.md` and references the spec file
- Squash-merge via `gh pr merge --admin --squash --delete-branch`
- After merge: spec front-matter `status` flips to `merged` and `pr` gets the URL — done as part of the PR itself before merging

### 4. CHANGELOG

A `CHANGELOG.md` at the repo root follows [Keep a Changelog](https://keepachangelog.com) conventions. Every spec PR appends or updates the `[Unreleased]` section under its version. On release (or as part of the PR for now), the `[Unreleased]` block is renamed to the version + date.

### 5. Version on disk

Two locations track the version:

- `pyproject.toml` → `[project] version = "X.Y.Z"`
- `src/dual_research/__init__.py` → `__version__ = "X.Y.Z"`

Both are updated in the spec PR. If they ever drift, the source of truth is `pyproject.toml`.

### 6. Retroactive baseline

The four pre-existing main-branch commits (skeleton, ingest, agents, protocol) collapse into a single `[0.1.0] — 2026-05-15` CHANGELOG entry. No retro specs are written — the work is already on `main` and inspectable.

### 7. Files added or changed by this spec

- `CHANGELOG.md` (new) — version history with `[0.1.0]` baseline + `[0.2.0]` for this spec
- `CONTRIBUTING.md` (new) — operator-readable summary of the workflow rules
- `specs/TEMPLATE.md` (new) — front-matter + body template for future specs
- `specs/0001-engineering-workflow.md` (this file)
- `.github/PULL_REQUEST_TEMPLATE.md` (new) — PR-body scaffold
- `pyproject.toml` — version 0.1.0 → 0.2.0
- `src/dual_research/__init__.py` — `__version__` 0.1.0 → 0.2.0
- GitHub labels (created via `gh label create`): the five `spec/*` labels above

## Out of scope

- **Branch protection rules.** Not enforced via GitHub API in this spec — workflow discipline lives in CONTRIBUTING.md. If we later find ourselves accidentally pushing to main, a follow-up spec enables `gh api .../branches/main/protection` with admin bypass.
- **CI / automated checks.** No GitHub Actions yet. `pytest` is the only automated check and it runs locally.
- **Release tags.** No `git tag` discipline yet; the version on disk and CHANGELOG are sufficient. A follow-up spec adds tag-on-merge if the project ever ships beyond personal use.
- **External contributor handling.** Single-author repo; no review-required gates.

## Test plan

- [ ] All five `spec/*` labels exist on the GitHub repo and apply on PR
- [ ] `pyproject.toml` and `__init__.py` both report `0.2.0` after merge
- [ ] `CHANGELOG.md` shows `[0.2.0] — 2026-05-15` with the bullet for this spec
- [ ] `CHANGELOG.md` shows `[0.1.0] — 2026-05-15` covering steps 1-4
- [ ] This spec's `status` flips to `merged` and `pr` field is populated before admin-merge
- [ ] Branch `spec/0001-engineering-workflow` is deleted after merge
- [ ] On `main` post-merge: `git log --oneline` shows the squash-merge commit with the spec title
- [ ] Next code change (spec 0002, whatever it is) follows the new workflow end-to-end

## Risks

- **Process overhead bloats small fixes.** Mitigation: spec file can be terse — three sentences of context + one Proposed change bullet is fine for a typo fix. The template is a maximum, not a minimum.
- **CHANGELOG and spec front-matter drift.** Mitigation: every spec PR touches both. If they drift, it's caught on the next PR review.
- **Forgetting to bump version.** Mitigation: it's a PR checklist item in the template and a test-plan bullet for every spec.
