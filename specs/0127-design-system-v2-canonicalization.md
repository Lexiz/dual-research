---
spec: 0127
title: Design system v2 canonicalization — promote v2 to single source of truth, archive v1
label: refactoring
version-bump: PATCH
status: proposed
target-version: 1.6.5
created: 2026-05-20
pr: ""
---

# Spec 0127 — Design system v2 canonicalization

> Ship bucket: **First of a 5-spec arc that completes the v1 → v2 migration.**
> Depends on: nothing (this spec only restructures docs; subsequent specs 0128–0131 carry the live-code migration).
> Complexity: **M** — pure docs/folder restructure, but the SPEC.md rewrite is a substantial writing task and the touch list spans several locations.
> Targeted version bump: **PATCH (1.6.4 → 1.6.5)** — no runtime change, no API change. Documentation + folder shape only.

---

## 1. Context

The dual-research design system currently lives in three places, two of which describe themselves as authoritative:

1. **`design-system/`** — labelled V1 canonical text spec (`SPEC.md` says *"snapshot of v0.69.12"*). Holds the GitHub-collaboration scaffolding (`PROMPT-FOR-CLAUDE-DESIGN.md`, audits, vendored skills).
2. **`docs/design-system-v2/`** — added in the M3 briefing PR (#?, seeded by `CLAUDE-CODE-PROMPT.md`). Was a one-shot planning artifact that seeded specs 0092–0104. Holds the canonical visual reference (`Design System v2.html`), the M3 CSS (`v2-m3.css`, `v2-m3-page.css`), and 17 Notion-issue screenshots. Was never meant to become the living spec.
3. **`src/dual_research/ui/static/`** — the live implementation. CSS files contain both v1 and v2 token vocabularies (v1: 345 refs; v2: 629 refs). The header of `tokens.css` still reads *"dual-research — Design System V1 — Tokens"*.

A new contributor has no single answer to "what is the canonical design system?" — `design-system/SPEC.md` and `docs/design-system-v2/README.md` each present themselves as authoritative for different things, the file naming creates the misleading impression that V2 is *somewhere else*, and Claude Design's prompt still describes the V1 type system (*"IBM Plex Sans"*) even though the live app uses Roboto Flex + Roboto Serif.

This spec is the **first of five** that close the migration. The remaining four specs (0128–0131) migrate the live frontend code:

- **0128** — `run-detail.jsx` token migration (242 v1 refs → 0)
- **0129** — `design-language.jsx` token migration (142 v1 refs → 0)
- **0130** — Remaining JSX token migration (`app.jsx`, `errors.jsx`, `compare.jsx`, `auth.jsx`, `search.jsx`, `shared.jsx`)
- **0131** — CSS finalization, v1 token block removal, IBM Plex font removal

0127 deliberately does no live-code work. It moves docs, rewrites the spec, and updates the collaboration prompt. Live code keeps running on the additive-layering pattern until 0128–0131 land.

---

## 2. Goals

1. **One canonical design-system location: `design-system/`.** `docs/design-system-v2/` ceases to exist as an active folder; its contents either move into `design-system/` or get archived.
2. **`design-system/SPEC.md` is rewritten as a V2-canonical document.** It describes the Material 3 design system (tokens, primitives, composed components, patterns, conventions) as the single, current design system. No "V1" / "V2" framing in active text — that distinction is a migration artifact and belongs in the archive.
3. **V1 SPEC.md is archived, not deleted.** Moves under `design-system/_archive/v1/` with a short README explaining that this is the deprecated v1 spec; the current spec is at `design-system/SPEC.md`.
4. **CSS source-of-truth files are renamed for clarity.** `v2-m3.css` → `tokens-and-primitives.css`; `v2-m3-page.css` → `composed-components.css`. The `v2-m3-` prefix was a briefing-phase artifact; with v1 archived it's noise.
5. **`PROMPT-FOR-CLAUDE-DESIGN.md` is updated to reflect V2 (Material 3) conventions** — Roboto Flex + Roboto Serif as the type system, M3 token vocabulary, Material Symbols Outlined for icons, M3 elevation / state-layer / motion language.
6. **A migration-status section in the new SPEC.md tracks the 0128–0131 progress.** Once those four specs land, the migration-status section is removed.

## 3. Non-goals

- **No live-frontend code changes.** `tokens.css`, `base.css`, `components.css`, `theme.css`, every `*.jsx`, `index.html` — untouched in this spec. They keep their dual-vocabulary state until 0128–0131.
- **No removal of v1 tokens from `tokens.css`.** That happens in 0131 after every consumer has been migrated.
- **No removal of the IBM Plex `<link>` tag in `index.html`.** Same reason — until JSX/CSS consumers have migrated, both font stacks must load.
- **No diagram-skill changes.** The skill at `design-system/skills/diagram/` stays as-is. (Future optional spec may align its palette to V2; deferred.)
- **No CHANGELOG history rewrite.** Old CHANGELOG entries that referenced V1 stay as historical record. The new CHANGELOG entry for 1.6.5 explains the canonicalization.
- **No `pyproject.toml` ↔ `__init__.py` version-drift fix.** That's an unrelated bug (pyproject says 1.5.0, __init__ says 1.6.4); follow-up.
- **No changes to specs 0050–0126.** Their references to V1 tokens stay as historical record of how the migration unfolded.

---

## 4. Current-state audit

### 4.1 — What `design-system/` holds today

```
design-system/
├── CHANGELOG.md                          ← append-only history
├── PROMPT-FOR-CLAUDE-DESIGN.md           ← V1-flavored ("IBM Plex Sans", v1 token examples)
├── README.md                             ← describes V1 spec + live impl + collaboration flow
├── SPEC.md                               ← V1 text spec ("snapshot of v0.69.12")
├── audits/
│   ├── README.md
│   ├── 2026-05-18-responsive-audit/      ← 52 screenshots + capture scripts + 392-line briefing
│   └── 2026-05-20-hiw-rework/            ← mockup.html for the HiW rework
└── skills/
    ├── README.md
    └── diagram/                          ← vendored diagram skill (SKILL.md + references/)
```

### 4.2 — What `docs/design-system-v2/` holds today

```
docs/design-system-v2/
├── CLAUDE-CODE-PROMPT.md                 ← the prompt that seeded this folder into the repo
├── README.md                             ← the V2 briefing (528 lines)
├── assets/
│   ├── Design System v2.html             ← canonical visual reference
│   └── styles/
│       ├── v2-m3.css                     ← M3 token + primitive CSS (source brief)
│       └── v2-m3-page.css                ← page-level component CSS (source brief)
└── notion-issues/
    ├── ISSUES.md
    └── screenshots/                      ← 17 PNGs (issue 01 … issue 17)
```

### 4.3 — V1 references in active documentation (must be re-pointed or removed by 0127)

| File | What's V1 |
|---|---|
| `design-system/SPEC.md` | Entire spec describes V1 design system |
| `design-system/README.md` | Describes V1 paths and the V1 spec as canonical |
| `design-system/PROMPT-FOR-CLAUDE-DESIGN.md` | Tells Claude Design V1 fonts (*"IBM Plex Sans"*), V1 token vocabulary, V1 conventions |
| `design-system/CHANGELOG.md` | Recent entries mention V1; pre-V2 entries describe V1 evolution |
| `docs/design-system-v2/README.md` | Frames V2 as a "briefing" with a "spec plan" deliverable — stale, that planning round shipped as specs 0092–0104 |
| `docs/design-system-v2/CLAUDE-CODE-PROMPT.md` | Instructions for landing the V2 brief — stale, already done |
| Root `CHANGELOG.md` | Multiple entries point at V1 paths (historical, do not rewrite) |

---

## 5. Proposed changes

### 5.1 — File moves and renames

| From | To |
|---|---|
| `docs/design-system-v2/assets/Design System v2.html` | `design-system/assets/Design System v2.html` |
| `docs/design-system-v2/assets/styles/v2-m3.css` | `design-system/assets/styles/tokens-and-primitives.css` |
| `docs/design-system-v2/assets/styles/v2-m3-page.css` | `design-system/assets/styles/composed-components.css` |
| `docs/design-system-v2/notion-issues/ISSUES.md` | `design-system/notion-issues/ISSUES.md` |
| `docs/design-system-v2/notion-issues/screenshots/*.png` | `design-system/notion-issues/screenshots/*.png` |
| `docs/design-system-v2/CLAUDE-CODE-PROMPT.md` | `design-system/_archive/seeding/CLAUDE-CODE-PROMPT.md` |
| `docs/design-system-v2/README.md` | `design-system/_archive/seeding/V2-BRIEFING.md` (renamed to make its archival nature explicit) |
| `design-system/SPEC.md` (V1) | `design-system/_archive/v1/SPEC.md` |

After moves, **delete `docs/design-system-v2/` entirely** (empty folder).

### 5.2 — New files

- **`design-system/SPEC.md`** — rewritten as a V2-canonical document. Structure:
  - § 0 — Mission (carried forward from V1, lightly adapted)
  - § 1 — Principles (carried forward from V1, lightly adapted — most still apply; "Mono is sans" rephrased for Roboto Flex + Roboto Serif)
  - § 2 — Foundations (M3 tokens: color roles, surface tiers, shape scale, type scale, fonts, elevation, state layers, motion, icons, density)
  - § 3 — Primitives (M3 atoms: buttons, FAB, icon button, chips, status pills, switches, segmented buttons, cards, tabs, dialogs, top app bar, navigation rail, list items)
  - § 4 — Composed components (critique pane header, QuestionThread, consumption row, timeline pane, agent input panel, modal · PhaseRail · RoundScrubber)
  - § 5 — Page-level patterns (onboarding tour overlay, How-It-Works + Changelog overlay, admin · ProgressSegs)
  - § 6 — Themes (dark + light)
  - § 7 — Density + responsiveness
  - § 8 — Accessibility
  - § 9 — Pointers (canonical visual ref: `assets/Design System v2.html`; live implementation: `src/dual_research/ui/static/*`; in-app reference: `/#/language`)
  - § 10 — **Migration status** (temporary section, removed after spec 0131 ships): tracks 0128–0131 progress with a status table
- **`design-system/_archive/v1/README.md`** — short note: *"This is the deprecated v1 design system, archived 2026-05-20 as part of spec 0127. The current spec is at `design-system/SPEC.md`. This folder is reference-only and not actively maintained."*
- **`design-system/_archive/seeding/README.md`** — short note: *"Artifacts from the seeding of design system v2 (mid-2026). `V2-BRIEFING.md` was the planning brief that produced specs 0092–0104. `CLAUDE-CODE-PROMPT.md` was the prompt that landed the briefing PR. Both are historical record."*

### 5.3 — File edits

- **`design-system/README.md`** — rewritten:
  - Drop V1/V2 framing
  - Describe: "This folder is the canonical text reference for the dual-research design system. The live implementation lives at `src/dual_research/ui/static/`. The in-app visual reference is at `/#/language`."
  - Update folder map to reflect new structure (assets/, notion-issues/, _archive/, etc.)
  - Update file table — point at the rewritten `SPEC.md`, the new `assets/` path, the new `notion-issues/` location
  - Preserve the existing "invariant" section ("Every PR that modifies design must touch SPEC.md AND the live implementation files in the same commit"), updated to reference the new file names
- **`design-system/PROMPT-FOR-CLAUDE-DESIGN.md`** — updated:
  - Update "Where the design system lives" section to point at new paths (`design-system/assets/Design System v2.html`, `design-system/assets/styles/tokens-and-primitives.css`)
  - Update conventions:
    - Replace "Mono is sans. The project deliberately uses one family (IBM Plex Sans)" with the V2 type vocabulary (*"Roboto Flex (plain) + Roboto Serif (brand). M3 fifteen-role type scale."*)
    - Replace token-vocabulary examples (`var(--bg-1)`, `var(--fg-0)`) with M3 equivalents (`var(--md-surface)`, `var(--md-on-surface)`)
    - Update icons section to point at Material Symbols Outlined
    - Update elevation language to M3 (`--md-elev-0..5`, tonal-overlay surface tint)
    - Update motion language to M3 (emphasized + standard easings, 8 duration tokens)
  - Whitelist / blacklist sections stay structurally identical; just update file names where they reference the renamed CSS files
- **`design-system/CHANGELOG.md`** — new top entry:
  ```
  ## 2026-05-20 — v2 canonicalization (spec 0127)
  - V2 (Material 3) design system promoted to canonical. SPEC.md rewritten to describe v2 as the single current design system.
  - V1 SPEC.md archived under _archive/v1/.
  - V2 brief contents moved from docs/design-system-v2/ into design-system/ (assets/, notion-issues/). Old docs/design-system-v2/ folder deleted.
  - CSS source-of-truth files renamed for clarity: v2-m3.css → tokens-and-primitives.css; v2-m3-page.css → composed-components.css.
  - PROMPT-FOR-CLAUDE-DESIGN.md updated to v2 conventions (Roboto, M3 tokens, Material Symbols).
  - Live frontend migration deferred to specs 0128–0131 (see SPEC.md § 10 — Migration status).
  ```
- **Root `CHANGELOG.md`** — new `[1.6.5]` entry following existing conventions:
  ```
  ## [1.6.5] — 2026-05-20

  ### Refactor

  - **Spec 0127 — Design system v2 canonicalization** ([spec 0127](specs/0127-design-system-v2-canonicalization.md)). Promotes v2 (Material 3) to single source of truth. Rewrites `design-system/SPEC.md` as v2-canonical, archives v1 spec under `design-system/_archive/v1/`. Moves v2 brief contents from `docs/design-system-v2/` into `design-system/` (assets/, notion-issues/); old folder deleted. Renames CSS sources to drop the briefing-phase `v2-m3-` prefix (`tokens-and-primitives.css`, `composed-components.css`). Updates `PROMPT-FOR-CLAUDE-DESIGN.md` to v2 vocabulary (Roboto Flex/Serif, --md-* tokens, Material Symbols). Live frontend code untouched; deferred to specs 0128–0131.
  ```

### 5.4 — Version bumps

- `pyproject.toml` — `1.5.0` → `1.6.5` (catching up the existing drift in the same commit since we're touching version anyway)
- `src/dual_research/__init__.py` — `1.6.4` → `1.6.5`
- `uv.lock` — `uv lock` refresh

> **Note on the pyproject.toml drift:** the file currently reads `1.5.0` while `__init__.py` reads `1.6.4`. This is a pre-existing bug from earlier hotfixes that didn't update pyproject. We're bumping pyproject to `1.6.5` (skipping 1.6.4 in pyproject's history) so it converges with `__init__.py` going forward. If you'd rather fix the drift in a separate hotfix PR first, say so and we'll leave pyproject at 1.5.0 here and bump it only after the hotfix lands.

### 5.5 — Cache-busting

- `src/dual_research/ui/static/index.html` — **no change.** This spec doesn't modify any CSS or JS the page loads; cache-bust version stays at `?v=0126a`.

---

## 6. File touch summary

**Moved (8 items):**
1. `docs/design-system-v2/assets/Design System v2.html` → `design-system/assets/Design System v2.html`
2. `docs/design-system-v2/assets/styles/v2-m3.css` → `design-system/assets/styles/tokens-and-primitives.css`
3. `docs/design-system-v2/assets/styles/v2-m3-page.css` → `design-system/assets/styles/composed-components.css`
4. `docs/design-system-v2/notion-issues/ISSUES.md` → `design-system/notion-issues/ISSUES.md`
5. `docs/design-system-v2/notion-issues/screenshots/` (21 PNGs, batch move) → `design-system/notion-issues/screenshots/`
6. `docs/design-system-v2/CLAUDE-CODE-PROMPT.md` → `design-system/_archive/seeding/CLAUDE-CODE-PROMPT.md`
7. `docs/design-system-v2/README.md` → `design-system/_archive/seeding/V2-BRIEFING.md`
8. `design-system/SPEC.md` → `design-system/_archive/v1/SPEC.md`

**Deleted:**
- `docs/design-system-v2/` folder (entirely, after moves complete)

**Created:**
- `design-system/SPEC.md` (rewritten V2-canonical, ~800–1200 lines)
- `design-system/_archive/v1/README.md` (~15 lines)
- `design-system/_archive/seeding/README.md` (~15 lines)
- `specs/0127-design-system-v2-canonicalization.md` (this file)

**Edited:**
- `design-system/README.md` (rewrite — drop V1/V2 framing, update folder map)
- `design-system/PROMPT-FOR-CLAUDE-DESIGN.md` (V2 vocabulary throughout)
- `design-system/CHANGELOG.md` (new top entry)
- `CHANGELOG.md` (root — new `[1.6.5]` entry)
- `pyproject.toml` (`1.5.0` → `1.6.5`)
- `src/dual_research/__init__.py` (`1.6.4` → `1.6.5`)
- `uv.lock` (refresh)

**Notably untouched:**
- All `src/dual_research/ui/static/*.css`
- All `src/dual_research/ui/static/*.jsx`
- `src/dual_research/ui/static/index.html`
- `design-system/skills/` (entire subtree)
- `design-system/audits/` (entire subtree)
- All specs 0001–0126 (historical record)
- All Python code outside `__init__.py`

---

## 7. Test plan

This spec ships no runtime code change. Verification is structural + documentation-quality.

- [ ] `find docs/design-system-v2 -type f 2>/dev/null | wc -l` returns **0** (folder gone).
- [ ] `ls design-system/assets/styles/` shows exactly `tokens-and-primitives.css` and `composed-components.css` (no `v2-m3*` filenames).
- [ ] `ls design-system/notion-issues/screenshots/` shows **21** PNGs (17 issues, with issues 2 / 3 / 5 each carrying multiple shots).
- [ ] `cat design-system/_archive/v1/SPEC.md | head -1` shows the old V1 SPEC.md first line.
- [ ] `cat design-system/SPEC.md | head -5` shows the new V2-canonical opening (no "snapshot of v0.69.12" string).
- [ ] `grep -i "IBM Plex" design-system/PROMPT-FOR-CLAUDE-DESIGN.md` returns **0** matches (replaced with Roboto vocabulary).
- [ ] `grep -E "var\(--bg-|var\(--fg-|var\(--border-" design-system/PROMPT-FOR-CLAUDE-DESIGN.md` returns **0** matches (replaced with `--md-*` examples).
- [ ] `grep -rn "docs/design-system-v2" design-system/ src/ specs/ CHANGELOG.md README.md 2>/dev/null | grep -v "_archive/" | grep -v "0127-" | grep -v "^CHANGELOG.md:"` returns **0** non-historical matches (only the spec itself and the root CHANGELOG history entries that talk about the old path should reference it).
- [ ] App still builds and renders: `uv run dual-research-server` → load `/#/runs`, `/#/language`, `/#/settings`, `/#/how-it-works` → no console errors, no broken styles (since no live code changed, this should be unchanged).
- [ ] `uv run pytest tests/ -q` → all green (no runtime change, but sanity-check that no Python file inadvertently broke).
- [ ] PR description includes a screenshot of `design-system/` tree after the change.

## 8. Risks

- **Risk: SPEC.md rewrite drifts from live CSS.** Mitigation: while writing the new SPEC.md, cross-reference against `src/dual_research/ui/static/tokens.css` (the `--md-*` block) and `design-system/assets/styles/tokens-and-primitives.css` to confirm every token name and value documented in SPEC.md exists in the live code. If a token in the brief was never adopted, drop it from SPEC.md.
- **Risk: external bookmarks to `docs/design-system-v2/README.md` break.** Mitigation: low-impact. The path was only referenced internally + in the seeding PR; no external consumers. If anyone hits a 404, the new location is one folder up.
- **Risk: pyproject version bump conflicts with another open hotfix.** Mitigation: check open PRs before opening the 0127 PR; if there's an in-flight version bump, rebase on top of it before merging.
- **Risk: SPEC.md rewrite is too long for a single spec.** Mitigation: the V2 brief README is already ~528 lines and covers most of what SPEC.md needs to say; rewriting is largely a re-organization + carry-forward exercise, not a from-scratch authoring effort. If during execution the writing balloons past ~1500 lines, split into multiple files (e.g., `SPEC.md` summary + `SPEC-foundations.md`, `SPEC-primitives.md`, `SPEC-components.md`) and update the README's folder map.
- **Risk: archived files trip up future grep operations.** Mitigation: `_archive/` prefix is the standard convention here and existing tooling already skips it (e.g., spec searches use `specs/0*.md`, not glob).

## 9. Roll-out and roll-back

- **Roll-out:** single PR. Merge directly to `main`. Fly deploy is a no-op (no live-code change) but run it anyway to confirm no build / packaging side-effects.
- **Roll-back:** if anything goes wrong, `git revert` the merge commit. All changes are file moves + text edits; no schema, no runtime state, no DB migration. Safe.

## 10. Follow-up specs (already planned)

After 0127 merges, the remaining four specs complete the migration:

| Spec | Scope | V1 refs removed | Risk |
|---|---|---:|---|
| 0128 | `run-detail.jsx` v2 token migration | 242 | M |
| 0129 | `design-language.jsx` v2 rebuild | 142 | M |
| 0130 | Remaining JSX (`app/errors/compare/auth/search/shared.jsx`) | 172 | M |
| 0131 | CSS finalization, v1 token block removal, IBM Plex removal | 345 + theme.css drain | H |

After 0131 ships, `design-system/SPEC.md` § 10 (the temporary migration-status section) is removed in the same PR.
