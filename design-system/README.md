# Design system — `dual-research/design-system/`

This folder is the **canonical text reference** for the dual-research design system. It is the source of truth for design conventions, paired with the **live implementation** in [`src/dual_research/ui/static/`](../src/dual_research/ui/static/) and the **in-app visual reference** at [`/#/language`](../src/dual_research/ui/static/design-language.jsx).

This folder exists for one reason: to enable a clean **two-way collaboration loop** between Claude Code (terminal) and Claude Design (claude.ai chat), with GitHub as the synchronisation layer.

---

## What lives where

| Artifact                                                           | Role                                                                 |
|--------------------------------------------------------------------|----------------------------------------------------------------------|
| [`SPEC.md`](SPEC.md)                                               | Canonical design system spec in text form. The single source of truth for Claude Design.                |
| [`CHANGELOG.md`](CHANGELOG.md)                                     | Human-readable history of design system changes. Append-only.                                            |
| [`PROMPT-FOR-CLAUDE-DESIGN.md`](PROMPT-FOR-CLAUDE-DESIGN.md)       | Paste-able prompt for the Claude Design project on claude.ai. Use this any time you start a new design exercise. |
| [`audits/`](audits/)                                               | Research audits feeding into future design system updates (e.g., responsive density audit).              |
| [`../src/dual_research/ui/static/tokens.css`](../src/dual_research/ui/static/tokens.css)         | Live implementation: CSS custom properties for palette, type, spacing, motion. **Authoritative for token values.**       |
| [`../src/dual_research/ui/static/theme.css`](../src/dual_research/ui/static/theme.css)           | Live implementation: theme overrides (light mode swaps).                                                 |
| [`../src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) | Live implementation: component CSS. **Authoritative for component visual rules.**                        |
| [`../src/dual_research/ui/static/base.css`](../src/dual_research/ui/static/base.css)             | Live implementation: base/reset styles.                                                                  |
| [`../src/dual_research/ui/static/design-language.jsx`](../src/dual_research/ui/static/design-language.jsx) | Live in-app visual reference, served at `/#/language`. The DNA one-pager + full reference.        |

---

## The invariant

> **Every PR that modifies design must touch SPEC.md AND the live implementation files in the same commit.**

The text spec, the live page, and the actual app must always agree. If they don't, the design system has drifted — the next PR's first job is to bring them back in sync.

---

## The two-way PR flow

### Flow A — Claude Design originates change

1. User opens the Claude Design project on claude.ai.
2. User pastes [`PROMPT-FOR-CLAUDE-DESIGN.md`](PROMPT-FOR-CLAUDE-DESIGN.md) (or its key parts) at session start so Claude Design knows where everything lives.
3. User asks Claude Design to propose a change.
4. Claude Design opens a PR against a `design-system/<descriptor>` branch:
   - Updates `SPEC.md` with the proposed new state + a `## Changes from current state` section.
   - Updates `CHANGELOG.md` with a one-line entry.
   - Updates the live implementation files (`tokens.css`, `components.css`, `design-language.jsx`, etc.) to match.
5. Claude Code (this assistant, in the terminal) reviews the PR, runs preview-verify against both viewports + both themes, may push fixup commits.
6. User merges the PR (squash-merge per repo convention).

### Flow B — Claude Code originates change

When implementing a spec that touches design (e.g., adding a new primitive, changing spacing, restyling a component):

1. The spec branch's PR must update `SPEC.md` and `CHANGELOG.md` alongside the implementation.
2. The PR description notes "design system change" so Claude Design (on the next round-trip) can read it.
3. On merge, `SPEC.md` reflects the new reality.

The key property: **the GitHub repo is always the synchronisation point.** Neither Claude Design nor Claude Code holds a private snapshot.

---

## Paths Claude Design may modify

**Whitelist** (the only paths Claude Design should touch):

- `design-system/**` (this folder)
- `src/dual_research/ui/static/tokens.css`
- `src/dual_research/ui/static/theme.css`
- `src/dual_research/ui/static/base.css`
- `src/dual_research/ui/static/components.css`
- `src/dual_research/ui/static/design-language.jsx`
- `src/dual_research/ui/static/shared.jsx` — *only* for shared design-system primitives (LoadingState, Chip, Card, Tab, AgentStrip, StatusBadge, CollapsibleSection, QuoteCallout, etc.). Application-logic edits in `shared.jsx` are out of scope.

**Blacklist** (Claude Design must never touch):

- Any Python file (`*.py`, all of `src/dual_research/` outside `ui/static/`).
- `tests/`, `runs/`, `supabase/`, `reconcile/`, `.github/`, `scripts/`, `pyproject.toml`, `uv.lock`.
- Per-surface JSX (`run-detail.jsx`, `runs-list.jsx`, `how-it-works.jsx`, `compare.jsx`, etc.) — design system primitives only.
- `specs/` — specs are for engineering work; design proposals live in PR descriptions + SPEC.md.

If Claude Design needs to change a per-surface JSX file (e.g., because a new pattern needs to be adopted there), it should call this out in the PR description and Claude Code will handle the implementation in a follow-up.

---

## Branch + PR conventions

- **Branch name**: `design-system/<short-slug>` (e.g., `design-system/density-tokens`, `design-system/v1.1-typography-revision`).
- **PR title**: `Design system — <descriptor>`.
- **PR description** must include:
  - A summary of intent.
  - A `## Changes from current state` section enumerating what's added/changed/removed.
  - Mention of any live-implementation files updated.
  - Note any out-of-scope items needing Claude Code follow-up.
- **Merge**: squash-merge to `main` (matches repo convention).

---

## When in doubt

- If the live implementation (CSS/JSX) and SPEC.md disagree, **trust the live implementation** and update SPEC.md to match. The app is what users see.
- If SPEC.md and the design-language.jsx page disagree, **trust SPEC.md** (assuming the live CSS agrees with SPEC.md) and update design-language.jsx — the page is documentation, not behavior.
- If you're proposing a change that conflicts with the principles in SPEC.md § Principles, document the conflict in the PR — don't silently violate.

---

## Maintenance owner

Claude Code (in-terminal). Reorganisation, drift-fix sweeps, and structural enforcement happen from here. Claude Design proposes; Claude Code integrates.
