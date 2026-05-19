---
spec: 0109
title: Modal chrome + overlay JSX M3 token migration
label: refactoring
version-bump: PATCH
status: proposed
target-version: 0.76.8
created: 2026-05-19
pr: ""
---

# Spec 0109 — Modal chrome + overlay JSX M3 migration

> Depends on: 0096 (.md-dialog CSS), 0107, 0108
> Complexity: **S**
> Drive mode: **by hand**.

## 1. Goal

After v0.76.7 the run-list + run-detail pages are M3, but the modals that
overlay those pages — DraftReviewModal, NegotiateReviewModal, ArtifactModal,
DocumentModal, InputBriefModal, PreflightResponseModal — still read v1 because
the shared `.dr-modal-*` CSS rules used v1 tokens. Same problem for the
four overlay screens: `settings.jsx`, `shortcuts-overlay.jsx`,
`search-palette.jsx`, `how-it-works.jsx` (153 inline v1-token references
combined).

After this spec, opening any modal or visiting any overlay screen renders
M3 surfaces consistent with the rest of the app.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — swap v1 tokens in the
  `.dr-modal` / `.dr-modal-header` / `.dr-modal-title` / `.dr-modal-sub` /
  `.dr-modal-close` / `.dr-modal-tabs` / `.dr-modal-body` rules to M3
  equivalents. Outer frame already gets `.md-dialog` styling on top via
  spec 0096; this commit harmonises the legacy modal-chrome sub-rules so
  the cascade no longer pulls in v1 colours.
- `src/dual_research/ui/static/settings.jsx` (18 refs)
- `src/dual_research/ui/static/shortcuts-overlay.jsx` (11 refs)
- `src/dual_research/ui/static/search-palette.jsx` (21 refs)
- `src/dual_research/ui/static/how-it-works.jsx` (103 refs)
- `pyproject.toml`, `__init__.py`, `uv.lock`, `index.html` cache-bust →
  `?v=0098`, `CHANGELOG.md` 0.76.8 entry.

Same token mapping as spec 0108:
`--bg-N → --md-surface-container-{tier}`,
`--fg-N → --md-on-surface[-variant|-muted|-faint|-decor]`,
`--border-N → --md-outline-{tier}`,
`--r-N → --md-shape-{xs|sm|md|full}`.

Notably not touched: the Modal primitive JSX (`shared.jsx:382`) — already
emits `.md-dialog` + `.md-dialog--{basic,rich}` + `.md-dialog--agent-{a,b}`
classes from spec 0096. The migration is in the CSS layer only.

## 3. Acceptance criteria

- [ ] `grep -c "var(--bg-\|var(--fg-\|var(--border-" settings.jsx shortcuts-overlay.jsx search-palette.jsx how-it-works.jsx` returns 0.
- [ ] Opening a modal in run-detail (DraftReviewModal etc.): outer frame
      `border-radius: 28px` (= `--md-shape-xl`), background reads M3
      surface-container-low, header band reads surface-container-high.
- [ ] `uv run pytest tests/ -q` → 924+ passed.
- [ ] No new pageerror / console-error.
- [ ] Hand-shot via Playwright with a modal opened — confirm cream M3
      surface in light mode, dark M3 surface in dark mode, sable left
      border for Claude-tinted modals.

## 4. Backend touched?

**no.**
