---
kind: dev
spec: "0220"
slug: in-app-changelog-auto-generated
title: In-app Changelog auto-generated from CHANGELOG.md
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: M
created: 2026-05-26
queued_at: 2026-05-26T12:16:51Z
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0220 — In-app Changelog auto-generated from CHANGELOG.md

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — new build artifact + new fetch path + new chip wiring + new internal-entry surface.
> **Evidence:** Live Changelog tab at `https://dual-research-alex.fly.dev/#how-it-works` ends at v1.35.0 while `CHANGELOG.md` HEAD is v1.44.24 — 33 shipped releases never reached the in-app surface. Hand-maintained `VERSION_NOTES` array at [src/dual_research/ui/static/how-it-works.jsx:22](src/dual_research/ui/static/how-it-works.jsx:22). Inert version chip at [src/dual_research/ui/static/app.jsx:364](src/dual_research/ui/static/app.jsx:364).

---

## 1. Context

The in-app Changelog tab at `/#how-it-works` is 33 releases behind. Last entry is v1.35.0; current shipped version is v1.44.24. The renderer reads from a hand-maintained `VERSION_NOTES` array at [src/dual_research/ui/static/how-it-works.jsx:22](src/dual_research/ui/static/how-it-works.jsx:22). [CONTRIBUTING.md §5](CONTRIBUTING.md) currently mandates that every PR shipping user-visible change append a new entry to that array — a contract that's been silently violated for 33 consecutive releases because nothing enforces it, and the entries that did make it in are written in dense engineer-prose (file:line citations, single-paragraph bullets) rather than normal release notes.

`CHANGELOG.md` is complete, current, and structurally parseable — it's enforced by `/dev-next` step 15b via the `changelog_written` checkpoint flag, so every merged PR ships an entry. The data exists; we just don't surface it. Separately, the version chip in the top chrome bar ([src/dual_research/ui/static/app.jsx:364](src/dual_research/ui/static/app.jsx:364)) carries a comment claiming "Click → how-it-works page" but **has no `onClick` handler wired** — it's currently inert, not just pointing at the wrong target.

## 2. Proposed change

CHANGELOG.md becomes the single source of truth for the in-app changelog. A build-time generator parses it into a JSON sidecar with deterministic regex-only prettification; the frontend fetches the sidecar on Changelog-tab mount.

```
CHANGELOG.md
    → scripts/build_version_notes.py
        → src/dual_research/ui/static/version-notes.json
            → ChangelogList fetches on mount
    ▲
    └── src/dual_research/ui/static/version-notes-overrides.json (hand-curated)
```

### 2.1 — `scripts/build_version_notes.py` (new)

Pure-Python parser/prettifier. No LLM, deterministic, idempotent.

- **Parse.** Walks `CHANGELOG.md` top-to-bottom. Heading regex `^## \[(?P<version>\d+\.\d+\.\d+)\] — (?P<date>\d{4}-\d{2}-\d{2})$` opens an entry; subsequent `### Added|Changed|Removed|Fixed` blocks aggregate bullets into a single `items[]` list (the section label becomes a `<strong>` lead chip on the first bullet of each section; multiple sections in one entry are preserved). `## [Unreleased]` is skipped.
- **Bump inference.** Compare against the previous entry's version: MAJOR-bump if MAJOR digit advanced, MINOR-bump if MINOR digit advanced, else PATCH. v1.2.0 (oldest) inherits MINOR.
- **Spec ID extraction.** Markdown link pattern `\[spec (?P<id>\d+(?:\.\d+)?)\]\(specs/[^)]+\)` → populates `specs: ["NNNN", …]`.
- **Aggressive prettify pass (regex-only, deterministic).** Per the user-confirmed taste call (see §5 — "prettify aggressiveness"):
  - Strip `[file.py:N](path)` markdown link wrappers → keep visible text; if the visible text is `path:N` shape, drop the whole reference (and elide the sentence if it becomes a fragment).
  - Strip `[tests/...](path)` references entirely; drop the containing sentence if its remainder is < 30 chars.
  - Convert `**bold**` → `<strong>bold</strong>`; backticks → `<code>code</code>`. Spec-link `[spec NNNN](specs/…)` preserved verbatim.
  - **Reshape passive engineer-prose into active "Now: X / Was: Y" anatomy.** Sentence-level regex pass detects the pattern `<subject> was <verb-past-participle>` / `<subject> is now <verb>` / `Previously <clause>; now <clause>` and rewrites to a fixed `<strong>Now</strong> <clause>. <strong>Was</strong> <clause>.` shape. When a bullet contains both a "before" and an "after" clause separated by a connector (`now`, `previously`, `before`, `after`), emit the Now/Was anatomy; when only one clause is present, leave the bullet as a single sentence.
  - Split bullets longer than 240 chars at sentence boundaries; preserve any HTML tags across the split.
- **Summary derivation.** First sentence of the first bullet → `summary` field. If that summary is > 180 chars, fall back to the section-label string (`Fixed`, `Added`, etc.) + the first 6 words of the bullet.
- **User-vs-internal classification (per user-confirmed taste call).** An entry is `user_facing: false` if the spec body (loaded via the `specs/NNNN-*.md` link extracted in spec-ID extraction) contains zero file references under `src/dual_research/ui/` or `design-system/`. Specs that ARE the application UI surface (the Design System v2 + the live `src/dual_research/ui/static/` JSX/CSS) are user-facing by definition; everything else (skill plumbing, CI, dashboard, orchestrator-only refactors) is internal. Falls back to `user_facing: true` if the spec file is missing on disk.
- **Override merge.** After auto-generation, read `src/dual_research/ui/static/version-notes-overrides.json`. For every version present there, the override entry replaces the auto-generated entry verbatim (full-record override; not field-level merge — keeps the contract simple). Versions not in overrides flow through unchanged.
- **Output.** Write `src/dual_research/ui/static/version-notes.json`: an array of entries `[{version, date, bump, summary, items[], specs[], user_facing}, …]` newest-first. Idempotent — re-running with no CHANGELOG.md change produces a byte-identical file.
- **CLI:** `uv run python scripts/build_version_notes.py [--check]`. `--check` exits non-zero if the on-disk JSON sidecar doesn't match what would be regenerated (CI-friendly).

### 2.2 — `src/dual_research/ui/static/version-notes-overrides.json` (new, seeded)

Hand-curated escape hatch. Initial commit seeds it with the existing v1.2.0–v1.35.0 entries from today's `VERSION_NOTES` array at [src/dual_research/ui/static/how-it-works.jsx:22-502](src/dual_research/ui/static/how-it-works.jsx:22) — verbatim, so the prettifier doesn't regress copy that's already good. Future per-entry hand-edits land here via the same channel; the existing `screenshots[]` field on each entry is preserved through the override.

### 2.3 — `src/dual_research/ui/static/how-it-works.jsx` — drop the hardcoded array

- Delete the `const VERSION_NOTES = […]` literal at [how-it-works.jsx:22-502](src/dual_research/ui/static/how-it-works.jsx:22) (~480 lines).
- `ChangelogList` at [how-it-works.jsx:1293](src/dual_research/ui/static/how-it-works.jsx:1293) gains a `React.useEffect` that fetches `/static/version-notes.json?v=0220a` on mount; entries land in component state. Loading state renders `window.LoadingState` (already imported for `SpecModal`); fetch error renders an `err`-toned `.hiw-note` with `Couldn't load the changelog — try refreshing.`
- The `HowItWorksBody` menu at [how-it-works.jsx:1433](src/dual_research/ui/static/how-it-works.jsx:1433) currently calls `VERSION_NOTES.slice(0, 12).map(…)` — now reads from the same fetched-state.
- **Hash routing for landing-via-anchor.** On `ChangelogList` mount, read `window.location.hash`; if it matches `#how-it-works#cl-<digits>`, mark the matching entry as `forceOpen` regardless of its `persistKey` localStorage state. `ChangelogEntry` at [how-it-works.jsx:1222](src/dual_research/ui/static/how-it-works.jsx:1222) takes a new `forceOpen` prop that overrides the CollapsibleSection's `defaultOpen` + persisted state on initial render.
- Cache-bust query strings on the JSX module bump to `?v=0220a` per the CONTRIBUTING.md convention.

### 2.4 — Internal-entry rendering (per user-confirmed taste call)

- **One-liner row.** Entries where `user_facing: false` render as a flat `<div className="changelog-internal-row">` instead of a `<CollapsibleSection>`-wrapped card. Anatomy: `<chip mono tone-neutral no-dot>v1.44.18</chip>` · date · `Internal — <summary>` · spec chips · bump chip. No expand affordance, no body — the summary is the whole payload.
- **Filter chip.** `ChangelogList`'s `.cl-filter-row` at [how-it-works.jsx:1310](src/dual_research/ui/static/how-it-works.jsx:1310) gains a fourth bump-style chip `[Internal N]` (tone `neutral`) **default-OFF**. When off, internal entries are filtered out of the rendered list entirely. When on, internal entries appear in chronological position as `.changelog-internal-row` items interleaved with user-facing `.cl-list` cards.
- **CSS.** New rule block `.changelog-internal-row { … }` lands in **both** [src/dual_research/ui/static/components.css](src/dual_research/ui/static/components.css) AND [design-system/assets/styles/composed-components.css](design-system/assets/styles/composed-components.css) in the same commit per the CLAUDE.md two-file CSS sync rule. Uses tokens only (`--md-surface-container`, `--md-on-surface-variant`, `--md-outline-hair`); no hex codes. Mirrors the `.changelog-head` row shape but flattened (no chevron, no hover affordance, no padding-on-open animation).
- **DS SPEC entry.** [design-system/SPEC.md](design-system/SPEC.md) §4 (composed components) gains a `.changelog-internal-row` row in the changelog-anatomy table, citing the existing chip vocabulary the row composes.

### 2.5 — `AppVersionChip` rewire ([src/dual_research/ui/static/app.jsx:364](src/dual_research/ui/static/app.jsx:364))

The chip is currently inert (no `onClick`). Replace the bare `<div><Chip>` with a `<button>` wrapper carrying `onClick={() => { window.location.hash = `#how-it-works#cl-${meta.version.replace(/\./g, '')}`; }}` plus a `title="Open the changelog at this version"` tooltip. Visual treatment unchanged — same `Chip` primitive, same mono font, same `v{meta.version}` label.

### 2.6 — `CONTRIBUTING.md` §5 update

Strip the bullet at [CONTRIBUTING.md:115](CONTRIBUTING.md:115) instructing PR authors to append to `VERSION_NOTES`. Replace with a single line: "The in-app Changelog tab is auto-generated from `CHANGELOG.md` at build time (see `scripts/build_version_notes.py`). To override a specific entry's prose, hand-edit `src/dual_research/ui/static/version-notes-overrides.json` in the same PR." `/dev-next` step 15b's `changelog_written` checkpoint is unchanged — it already enforces the upstream source of truth.

### 2.7 — `/dev-next` step 15 wiring

After the existing `changelog_written` checkpoint clears in [/dev-next step 15b], invoke `uv run python scripts/build_version_notes.py` and `git add src/dual_research/ui/static/version-notes.json`. The regenerated JSON ships in the same PR commit as the CHANGELOG.md entry. A new test (per §6) runs `--check` in CI so a stale sidecar fails the build.

### 2.8 — Backfill (first-cycle behavior)

The initial commit runs the generator once over all of CHANGELOG.md (v1.2.0 → v1.44.24, ~46 entries). v1.2.0–v1.35.0 land in `overrides.json` verbatim from today's hand-curated `VERSION_NOTES`; v1.36.0–v1.44.24 (the 33 missing entries) are freshly auto-prettified. Both flow through the same generator into `version-notes.json` in the same commit.

## 3. User stories & acceptance criteria

### 3.1 — User stories

> As a **researcher**, I want to see every shipped release surfaced in the app's Changelog tab, so that I can understand what's new without leaving the app.

> As a **researcher**, I want to click the version chip in the top chrome bar and land directly on the matching Changelog entry, so that I can answer "what changed in this version?" in one click.

> As a **dev** shipping a spec, I want the in-app changelog to update automatically when I update `CHANGELOG.md`, so that I never ship a release that's invisible in-app and I don't carry the manual VERSION_NOTES-append step.

### 3.2 — Acceptance scenarios (BDD)

> **Scenario 1:** Changelog tab shows every shipped release
> GIVEN the app is deployed at v1.45.0 and `CHANGELOG.md` contains entries back to v1.2.0
> WHEN the user navigates to `/#how-it-works` and clicks the Changelog tab
> THEN the rendered entry list contains ≥ 40 entries AND the most-recent entry's version matches the deployed `window.useAppMeta().version`

> **Scenario 2:** Version chip jumps to the current entry
> GIVEN the user is on the run list at `/#runs`
> WHEN the user clicks the version chip (e.g. `v1.45.0`) in the top chrome bar
> THEN `window.location.hash` becomes `#how-it-works#cl-1450` AND the Changelog tab is active AND the v1.45.0 `ChangelogEntry` is rendered expanded (regardless of any prior `localStorage` collapsed state for that version's `persistKey`)

> **Scenario 3:** Internal entries hidden by default; toggleable
> GIVEN the user is on the Changelog tab with no filter interaction
> WHEN the page loads
> THEN entries where the underlying spec's body cites zero files under `src/dual_research/ui/` or `design-system/` are absent from the rendered list AND the `[Internal N]` filter chip shows the hidden count
> WHEN the user clicks the `[Internal N]` filter chip
> THEN internal entries render as single-row `.changelog-internal-row` items interleaved chronologically with the user-facing `ChangelogEntry` cards

## 4. Data / Schema deltas

None. New build artifact (`version-notes.json`) and new hand-curated input file (`version-notes-overrides.json`) are static assets under `src/dual_research/ui/static/`. No database changes, no API changes.

## 5. Out of scope

- **Automatic screenshot extraction.** The `screenshots[]` field stays in the entry schema, but the prettifier never populates it. Hand-curated via `version-notes-overrides.json` only. Deferred indefinitely — no follow-up spec target.
- **Retroactive `user_facing:` annotation on spec frontmatter.** Classification runs at build time from spec body content; not added as a frontmatter field on already-shipped specs. Re-classifying a single entry happens via `overrides.json`.
- **CSS rewrite of `ChangelogEntry`.** The existing `CollapsibleSection`-based card renders unchanged for user-facing entries; only the new `.changelog-internal-row` class is introduced.
- **Paginated / lazy-load Changelog.** All entries render in one DOM tree on tab mount. Acceptable for ≤ ~100 entries; revisit if/when the count exceeds that.
- **LLM-based prose rewriting.** The §2.1 "aggressive rewrite" is regex-only and deterministic. No LLM in the build pipeline.
- **Migration of `VERSION_NOTES` consumers outside `how-it-works.jsx`.** A grep confirms the array is referenced only inside that file (lines 22, 1299, 1302, 1305, 1320, 1433); no other JSX module reads it. If a future consumer needs the same data, it fetches the JSON sidecar.

## 6. Test plan

- [ ] `scripts/build_version_notes.py` parses `CHANGELOG.md` and emits a `version-notes.json` with ≥ 40 entries; each entry carries `version`, `date`, `summary`, `items`, `bump`, `specs[]`, `user_facing` keys; newest entry first; idempotent under re-run.
- [ ] Unit test: the prettifier's regex passes — citation-strip, `**bold**` → `<strong>`, backtick → `<code>`, sentence-split-at-240-chars, Now/Was anatomy reshape — each have a positive + antipodal-absence test pair per spec 0206.
- [ ] Unit test: bump inference (MAJOR/MINOR/PATCH derived from version delta), spec-ID extraction (composite IDs like `0211.1` survive), user-facing classification (an entry whose spec body contains `src/dual_research/ui/foo.jsx` is user-facing; an entry whose spec body contains zero such references is internal; missing spec file defaults to user-facing).
- [ ] Source-pattern test at `tests/test_spec_0220_in_app_changelog.py`: `src/dual_research/ui/static/how-it-works.jsx` no longer contains the literal string `const VERSION_NOTES = [`; ChangelogList contains a `fetch('/static/version-notes.json` call site; ChangelogList contains hash-routing logic recognising the `#cl-` anchor pattern.
- [ ] Source-pattern test: `src/dual_research/ui/static/app.jsx` `AppVersionChip` carries an `onClick` (or `<a href>`) that includes the literal substring `cl-`; the comment claiming click-navigates is no longer a lie.
- [ ] Source-pattern test: `CONTRIBUTING.md` §5 no longer contains the substring `append a new entry to the VERSION_NOTES array`; instead contains `auto-generated from CHANGELOG.md`.
- [ ] Source-pattern test: the new `.changelog-internal-row` CSS rule block is present in BOTH `src/dual_research/ui/static/components.css` AND `design-system/assets/styles/composed-components.css` (two-file CSS sync rule).
- [ ] CI guard: `uv run python scripts/build_version_notes.py --check` exits 0 (committed `version-notes.json` matches the regenerated output for the current `CHANGELOG.md`).
- [ ] Runtime cross-check via Claude Preview MCP screenshot in the PR description: `/#how-it-works` Changelog tab showing ≥ 40 entries; second capture showing the chip-click landing on the current version's entry expanded; third capture showing the `[Internal N]` filter chip toggled ON and an internal one-liner row visible inline.

## 7. Risks

- **Prettifier mis-shapes a specific bullet.** The aggressive Now/Was rewrite pass is the highest-risk piece — a passive sentence the regex doesn't recognise stays as-is (acceptable), but a sentence that partially matches and gets badly reshaped is the failure mode. Mitigation: `version-notes-overrides.json` is the per-entry escape hatch; any entry that looks wrong gets dropped in there verbatim. The first-cycle backfill already seeds it with all of v1.2.0–v1.35.0, so today's hand-curated prose is protected end-to-end.
- **JSON fetch fails at runtime.** Browser sees a blank Changelog tab + an `err`-toned `.hiw-note` saying "Couldn't load the changelog". Intentional: an empty Changelog is a loud, visible signal that the build pipeline didn't run — preferable to baking a stale fallback into the JS bundle, which would re-create the staleness problem this spec solves.
- **User-vs-internal classifier mis-flags an edge case.** Some specs touch the UI without citing files under `src/dual_research/ui/` (e.g. a spec that only edits a `<script>`-tag URL in `index.html`). Mitigation: `overrides.json` carries an optional per-entry `user_facing: true|false` field that wins over the heuristic.
- **JSON sidecar drifts behind CHANGELOG.md on a manual PR.** Mitigation: `--check` mode in the build script + a CI assertion (item 8 of §6) makes a stale sidecar a hard build failure, mirroring the existing `changelog_written` checkpoint pattern.
- **File size.** Regenerated JSON for ~46 entries is estimated at ~80–120 KB. Fetched once on Changelog-tab mount, served via the existing static-asset pipeline. Acceptable; not gzip-blocked. Revisit only if the count crosses ~150 entries.
