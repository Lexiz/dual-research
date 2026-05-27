---
kind: dev
spec: "0154"
slug: orchestrator-hardening-ds-steering-and-queue-runner
title: Spec workflow hardening — design-system steering at spec time, run-queue-until-empty skill, project CLAUDE.md
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.19.0
status: deployed
depends_on: []
complexity: M
created: 2026-05-22
queued_at: 2026-05-22T12:38:45Z
started_at: "2026-05-22T12:57:33Z"
merged_at: "2026-05-22T13:04:31Z"
deployed_at: "2026-05-22T13:06:33Z"
pr: "https://github.com/Lexiz/dual-research/pull/177"
handover: "handoffs/2026-05-22-spec-0154-orchestrator-hardening-ds-steering-and-queue-runner.md"
failure_step: ""
source_session: orchestrator-hardening-2026-05-22
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0154 — Spec workflow hardening — design-system steering at spec time, run-queue-until-empty skill, project CLAUDE.md

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — adds new orchestrator capability (`/dev-queue-run`) and a new project-wide steering doc (`CLAUDE.md`); no breaking changes.
> **Evidence:** spec 0152 (lifecycle bootstrap), spec 0153 (DS dashboard redesign), this session's ideation thread.

---

## 1. Context

Spec 0152 introduced the four-skill spec workflow (`/spec-draft`, `/spec-queue`, `/spec-promote`, `/dev-next`). After two specs through the system (0152 itself, 0153), real-use friction surfaced:

- **No design-system steering anywhere.** The canonical reference at `design-system/SPEC.md` is never read by `/spec-queue`, `/spec-promote`, `/spec-draft`, or `/dev-next`. UI specs and UI implementations both drift away from the live tokens and primitives. Spec 0151 had to retroactively close four UI regressions that the original 0140-0150 batch never noticed because there was no DS gate at spec time.
- **Skills still pause for "ship it?" gates.** `/spec-queue/SKILL.md:27` and `/spec-promote/SKILL.md:36-38` surface classification and ask the user to confirm before proceeding, even though the user invoked the skill specifically to capture their already-formed intent.
- **Version-bump mapping is documented only in `CHANGELOG.md:5-9`** (`breaking`→MAJOR, `new-feature`→MINOR, `bug`/`refactoring`/`test`→PATCH), not inline in `/spec-queue/SKILL.md:49` or `/spec-promote/SKILL.md:79` where the `version_bump` field is actually set. Field can be misset.
- **`/dev-next/SKILL.md:80` instructs "Update CHANGELOG with an `[Unreleased]` entry"** but actual practice (`CHANGELOG.md:12-32`) writes directly under a new `## [X.Y.Z]` section per spec. Skill text and reality disagree.
- **`/dev-next` is single-spec only** (`/dev-next/SKILL.md:9`, `:125-127`). Draining a backlog of N queued specs requires N manual invocations.
- **Permission prompts fire repeatedly** for routine work in `~/dual-research-author/` (not in `additionalDirectories` at `~/.claude/settings.json:6-10`), for DS-rebuild scripts, and for `~/.claude/skills/` edits.
- **Queue session goes stale on informal checks.** `/dev-next/SKILL.md:18` does `git fetch` only; local `main` never advances unless `/dev-next`'s full preflight runs (step 3 would catch the lag and halt). Informal prompts like "is the queue ready?" that read local disk return wrong answers. Discovered during 0154's own creation: the queue session reported "queue empty" while `origin/main` carried 0154's two queued commits.

## 2. Proposed change

Seven concrete edits across four skill files, one new skill, one new project file, plus settings + memory updates.

### 2.1 — `~/.claude/skills/spec-queue/SKILL.md`

**Step 1** restructured from a single classify pass into three reads (numbering 1a / 1b / 1c):

- **1a. Classify.** Same five types (`new-feature`, `bug`, `refactoring`, `test`, `breaking`). Replace "Surface your classification with reasoning to the user before proceeding. Let them override." (`spec-queue/SKILL.md:27`) with: print the classification + one-sentence reasoning in the final report (step 9), do not pause to confirm — invocation IS the confirmation; if wrong, user corrects post-commit via frontmatter edit.
- **1b. Scope scan.** Re-read the conversation for explicit exclusion markers: "not part of this spec", "skip this", "out of scope", "follow-up", "separate spec", "leave out", "don't include". Capture each into an `## Out of scope` section in the spec body.
- **1c. Design-system check (UI specs only).** If the spec touches frontend (anything that would land under `src/dual_research/ui/static/` or `design-system/`), read `design-system/SPEC.md` before populating the template. For each proposed UI element, cite the DS section/primitive that governs it inline in the body (e.g. "uses the `card` composed component per SPEC.md §6.3"). If a proposed element has no DS equivalent, flag in the body as a prerequisite — either extend the DS in this same spec OR split the DS extension into a separate spec and add to `depends_on`. Carry implementation guidelines (palette, density, motion, badge governance, accessibility) from `SPEC.md` into the body where relevant.

**Step 4 frontmatter line** (`spec-queue/SKILL.md:49`): append inline mapping so `version_bump` can't be misset:

> `version_bump` (mechanical from type: `breaking`→MAJOR, `new-feature`→MINOR, `bug`/`refactoring`/`test`→PATCH)

### 2.2 — `~/.claude/skills/spec-promote/SKILL.md`

**Step 2** (`spec-promote/SKILL.md:32-38`): mirror the `/spec-queue` step 1a change. Print classification + reasoning in the final report, do not pause. If the type was set on the draft, use it as-is.

**Step 4** (`spec-promote/SKILL.md:46-52`): add **Scope scan** + **Design-system check** sub-steps mirroring `/spec-queue` step 1b + 1c. The walk-unresolved-questions gate in step 3 (`spec-promote/SKILL.md:37-45`) is **preserved** — dev specs can't carry questions, this is a genuine blocker not a confirmation gate.

**Step 6 frontmatter `version_bump` line** (`spec-promote/SKILL.md:79`): replace `<MAJOR/MINOR/PATCH per type>` with the explicit mechanical mapping.

### 2.3 — `~/.claude/skills/spec-draft/SKILL.md`

**Step 1** (`spec-draft/SKILL.md:17-24`): add two bullets.

- **Scope exclusions** — capture into `## Out of scope` in the draft body so promotion preserves them.
- **UI scope** — if the draft touches frontend, flag it in the body and point at `design-system/SPEC.md`. Full DS check happens at `/spec-promote` time; the draft just needs to flag that one is needed.

Add explicit "do not pause before writing — invocation IS the confirmation" line at the end of step 1.

### 2.4 — `~/.claude/skills/dev-next/SKILL.md`

**Step 1** (`dev-next/SKILL.md:18`): change `git fetch` to `git pull --ff-only origin main`. The current `fetch` updates remote-tracking refs but leaves local `main` stale, so any informal "is the queue ready?" prompt that reads disk without invoking `/dev-next` returns wrong answers. `--ff-only` is safe-by-default — fails noisily on divergence rather than auto-merging. Step 3's existing "up to date with `origin/main`" check then becomes a tautology (good — it should always pass after step 1).

**Step 15** (`dev-next/SKILL.md:80`): two changes folded into a restructured step.

- **Design-system gate (UI specs only).** Before writing any frontend code: if the spec's `type` is `new-feature` or `refactoring` AND the spec body cites any file under `src/dual_research/ui/static/` or `design-system/`, read `design-system/SPEC.md`. Honor the DS citations the spec already carries (per `/spec-queue` 1c or `/spec-promote` 4). Tokens-only colors. New components land in both `design-system/assets/styles/composed-components.css` AND `src/dual_research/ui/static/components.css` in the same commit. Reference `CLAUDE.md` at repo root.
- **Version + CHANGELOG.** Compute the new version from current `pyproject.toml` + spec's `version_bump`. Bump `pyproject.toml` and `src/dual_research/__init__.py`. Write a new `## [X.Y.Z] — YYYY-MM-DD` section in `CHANGELOG.md` directly. Drop the `[Unreleased]` convention — each spec is its own release.

### 2.5 — New skill `~/.claude/skills/dev-queue-run/SKILL.md`

New `user_invocable: true` skill. Description targets natural triggers: "run the queue", "drain the queue", "kick off all the queued specs", "run them all", "/dev-queue-run".

Behavior:

- Runs in `/Users/alexlisitzky/dual-research/` only. Refuses from author worktree (same `git rev-parse --show-toplevel` guard as `/dev-next/SKILL.md:14`).
- **Single greenlight at start.** List the full queue (N specs · titles · types · complexity), ask "Run all? y/n." This is the only forced confirmation in the cycle.
- On yes: loop `/dev-next`'s full body per spec (pre-flight → reconcile → branch → implement → tests → PR → admin merge → deploy → handoff). No per-spec pause. No per-spec "go-ahead" gate (the pre-flight confirmation at `/dev-next/SKILL.md:31` is suppressed inside `/dev-queue-run`).
- On any failure (test red, reconcile-semantic, deploy fail): halt immediately, surface what failed, list completed specs with their cycle times, leave failed spec at `status: failed, failure_step: <name>` for manual recovery. Do not auto-skip to the next spec.
- On empty queue: stop, report total cycle time + per-spec cycle times.

### 2.6 — New `/Users/alexlisitzky/dual-research/CLAUDE.md`

Auto-loaded by every Claude Code session in the dual-research repo. Three sections:

- **Design system rule.** Every frontend change reads `design-system/SPEC.md` first. Tokens-only colors (no hex codes in components). New components land in both `design-system/assets/styles/composed-components.css` AND `src/dual_research/ui/static/components.css` in the same commit. Live primitives at the `/#/language` route. Cite `design-system/README.md` and `design-system/SPEC.md` as canonical references.
- **Version + CHANGELOG rule.** Every merged PR bumps `pyproject.toml` + `src/dual_research/__init__.py` per the spec's `version_bump` (`breaking`→MAJOR, `new-feature`→MINOR, `bug`/`refactoring`/`test`→PATCH) and writes a new `## [X.Y.Z] — YYYY-MM-DD` section in `CHANGELOG.md`. Applies to manual PRs too, not only `/dev-next` output.
- **Spec workflow pointer.** Links to the five skills (`/spec-draft`, `/spec-queue`, `/spec-promote`, `/dev-next`, `/dev-queue-run`) with one-line descriptions.

### 2.7 — Settings + memory

- `~/.claude/settings.json` (`additionalDirectories` at `:6-10`): append `/Users/alexlisitzky/dual-research-author`. `permissions.allow` (`:25-126`): mirror the existing `cd /Users/alexlisitzky/dual-research && *` family (git, gh, fly, flyctl, uv, python, python3, pytest) for the author worktree path. Add `Edit(/Users/alexlisitzky/.claude/skills/**)` and `Write(/Users/alexlisitzky/.claude/skills/**)`.
- New `/Users/alexlisitzky/dual-research-author/.claude/settings.local.json`: mirror the existing `/Users/alexlisitzky/dual-research/.claude/settings.local.json` (currently 26 lines, `gh pr *`, `git push/fetch/pull/checkout/switch/branch *`, `uv run pytest/python/sync *` entries) so the author worktree gets the same project-local permissions.
- `~/.claude/projects/-Users-alexlisitzky/memory/feedback_pause_between_specs.md`: append an Exception note. Default behavior still pauses between specs, except when the user invokes `/dev-queue-run`, which is an explicit opt-out and runs the whole queue without per-spec pauses.

## 3. UX / Behavior

User-facing surface area:

- `/spec-queue`, `/spec-promote` stop pausing for classification confirmation. The classification appears inline in the final report.
- UI specs created via `/spec-queue` or `/spec-promote` now carry DS citations in their body. Specs without DS citations on UI content fail the implicit `/dev-next` step 15 gate.
- New command: `/dev-queue-run` drains the queue in a single invocation, halting on first failure.
- Fewer permission prompts in `~/dual-research-author/`, on DS-rebuild scripts, and on `~/.claude/skills/` edits.
- Default workflow remains unchanged: pause between specs unless the user opts in to `/dev-queue-run`.

## 4. Data / Schema deltas

No frontmatter changes to existing specs. `version_bump` is now documented inline in `/spec-queue` and `/spec-promote` instead of relying on out-of-band `CHANGELOG.md` guidance, but the field itself is unchanged. No migration. No backfill.

## 5. Out of scope

- `release-please` or any external release-automation tool. The manual per-spec bump model stays.
- Machine-readable validator enforcement of DS citations. Skills steer by prompt; if a UI spec lands without DS citations, `/dev-next` step 15 catches it at implementation time, but there is no schema check at `/spec-queue` commit time.
- Auto-classification of `type` from conversation regex. Classification stays human-judgment via the skill's read-then-decide flow.
- Retry-or-skip logic in `/dev-queue-run` on failure. Halt-only.
- Cross-repo or hosted scheduling.
- Bumping `target_version` automatically at `/spec-queue` time (still picked by user judgment in this spec).

## 6. Test plan

- [ ] `/spec-queue` on a fresh thread prints classification + reasoning in the final report without pausing for confirmation.
- [ ] `/spec-promote` on a draft prints classification + reasoning without pausing (separate from the unresolved-questions walk, which still gates).
- [ ] `/spec-queue` on a thread containing an explicit "out of scope" marker (e.g. "we're not touching X here") writes an `## Out of scope` section in the spec body capturing X.
- [ ] `/spec-queue` on a thread proposing a new UI component reads `design-system/SPEC.md` before writing, and the resulting spec body cites at least one DS section/primitive per proposed UI element.
- [ ] `/spec-queue` and `/spec-promote` set `version_bump` matching the type mapping (verify on one spec per type).
- [ ] `/dev-next` on a spec with `version_bump: MINOR` writes a new `## [X.Y.0] — YYYY-MM-DD` section in `CHANGELOG.md`, NOT under `[Unreleased]`.
- [ ] `/dev-next` step 1 fast-forwards local `main` to `origin/main` before any other check. Verify by: (a) `git -C /Users/alexlisitzky/dual-research reset --hard HEAD~1` to put local main behind, (b) invoke `/dev-next`, (c) confirm step 1 pulls forward and step 3's up-to-date check passes without intervention.
- [ ] `/dev-queue-run` invoked from `/Users/alexlisitzky/dual-research/` with N≥2 queued specs asks ONE confirmation, runs all sequentially, halts at first failure or empty queue.
- [ ] `/dev-queue-run` invoked from `/Users/alexlisitzky/dual-research-author/` refuses with the same guard message shape as `/dev-next/SKILL.md:14`.
- [ ] Editing a file under `~/.claude/skills/**` from any session does not prompt for permission.
- [ ] `cd /Users/alexlisitzky/dual-research-author && git fetch origin` from a fresh session does not prompt for permission.
- [ ] `/Users/alexlisitzky/dual-research/CLAUDE.md` is auto-loaded in a new session opened in that directory (verify by inspecting the session's claudeMd context).

## 7. Risks

- **`/dev-queue-run` runs unattended after the single greenlight.** Halt-on-failure caps the blast radius (a broken spec doesn't cascade), but the user implicitly trusts every spec body in the queue. Mitigation: the spec-creation DS check + scope scan + validator already catch most issues before they reach `/dev-queue-run`. If a spec is bad enough to fail at `/dev-next` step 15, halt-on-failure surfaces it.
- **Memory drift between `feedback_pause_between_specs` and `/dev-queue-run`.** Mitigated by the explicit Exception note appended to the memory in §2.7.
- **Permission expansion increases blast radius.** The author worktree and `~/.claude/skills/**` writes are new allows. Mitigated by the existing deny list at `~/.claude/settings.json:12-24` (`rm -rf`, `git push --force`, `git reset --hard`, `git clean -fd`) which still wins per Claude Code's deny-over-allow precedence.
- **CHANGELOG `[Unreleased]` removal is one-way.** No risk for past entries — `CHANGELOG.md:12-32` already writes direct under version headings; only the skill text is being updated to match observed practice.
- **DS-check prompt for UI specs may slow down spec creation.** Acceptable cost — the alternative (catch at `/dev-next` time) means reverting committed specs.
