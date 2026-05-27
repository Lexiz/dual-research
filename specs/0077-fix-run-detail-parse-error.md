---
spec: 0077
title: "Hotfix: run-detail.jsx parse error (white-screen regression)"
label: bug
version-bump: PATCH
status: merged
target-version: 0.69.1
created: 2026-05-18
pr: "https://github.com/Lexiz/dual-research/pull/77"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0077 — Hotfix: run-detail.jsx parse error

## Context

Every run-detail page on the hosted app white-screens with a Babel parse error. The home page (run list) renders fine, but clicking any run produces a blank screen with:

```
SyntaxError: /run-detail.jsx: Unexpected token, expected "}"
```

### Root cause

A JSX comment (`{/* */}`) was placed inside a JSX prop expression slot (`left={...}`) in `run-detail.jsx`. Babel cannot parse this — the outer `{` of `left={` plus the inner `{/* */}` is interpreted as the start of a nested object literal.

### Provenance

The broken comment block was introduced in SPEC-0070's squash commit. Subsequent specs (0071-0075) shipped on top without catching it because their preview-verify steps did not navigate to a run-detail page.

## Design decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Move the comment OUT of the `left={...}` prop expression slot to JSX children position above `<PaneHeader>` | Matches existing convention (Spec-0046 comment block nearby) |
| D2 | PATCH version bump (0.69.0 -> 0.69.1) | Semver: bugfix, not feature |
| D3 | Add regression test detecting `prop={ {/* */}` pattern in all JSX files | Prevents same class of bug from shipping again |
| D4 | Bump cache-bust to `?v=0077` (currently `?v=0075`) | Force browsers to re-fetch the fixed file |
| D5 | No design-system alignment changes | Bugfix only, M1 N/A |

## Files touched

- `src/dual_research/ui/static/run-detail.jsx` — move comment out of prop slot
- `src/dual_research/ui/static/index.html` — cache-bust bump to `?v=0077`
- `tests/test_ui_jsx_syntax.py` — new regression test
- `pyproject.toml` + `src/dual_research/__init__.py` + `uv.lock` — 0.69.0 -> 0.69.1
- `CHANGELOG.md` — hotfix entry

## Out of scope

- Other potential bugs from 0070-0075
- Modifying per-spec.md preview-verify template
- Cosmetic improvements to surrounding code

## Test plan

- All existing tests pass + new regression test passes
- Preview-verify: run-detail page renders, zero console errors, both themes
- `/api/health` reports 0.69.1

## Risks

- R1: Browser cache — mitigated by cache-bust bump
- R2: Line numbers may have drifted — find by content, not line number

## Design system alignment (per arc M1)

N/A — bugfix spec, no design-system changes.
