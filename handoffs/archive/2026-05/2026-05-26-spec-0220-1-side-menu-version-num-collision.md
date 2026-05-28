---
spec: "0220.1"
date: 2026-05-26
version: 1.45.1
pr: https://github.com/Lexiz/dual-research/pull/258
---

# Spec 0220.1 handoff — Fix Changelog side-menu version-num column overlap on long versions

Ships v1.45.1. Tight CSS-only fix for the layout regression spec 0220 surfaced: the Changelog tab's side menu rendered the version chip and the truncated summary against each other for every 6-character version (`1.45.0`, `1.44.25`, …), producing strings like `1.45In-app Changelog auto-generate` because `.hiw-overlay__menu-list .menu-section-num` was hard-coded to `width: 18px` — fit for the legacy hand-curated 3-character versions, broken for the post-spec-0220 auto-generated list.

## What landed

- `src/dual_research/ui/static/components.css` — `.hiw-overlay__menu-list .menu-section-num` changed from `width: 18px` to `min-width: 48px; margin-right: var(--s-2);`. `min-width` keeps overflow graceful (a future 7-character version like `100.0.0` widens the column rather than colliding); `var(--s-2)` (8px) gives a stable visual gap between the version column and the summary text.
- `design-system/assets/styles/composed-components.css` — the same rule landed on the DS side with `var(--md-sp-2)` (the DS-side spacing token, also 8px). The DS file previously had **no** `.menu-section-num` rule at all — this commit closes that pre-existing DS-sync gap as a bonus. A comment block above the rule cross-references spec 0220.1 and the CLAUDE.md two-file CSS sync rule.
- `tests/test_spec_0220_1_side_menu_version_num.py` — two source-pattern tests (positive regex + antipodal-absence regex, per the spec 0206 doctrine), one pair per file. Locks in both the post-fix shape and the absence of the pre-fix `width: 18px` shape. Full suite 2018 passed.
- `CHANGELOG.md` — new `## [1.45.1] — 2026-05-26` section under `## [Unreleased]`. Bumps `pyproject.toml` + `src/dual_research/__init__.py` + `uv.lock` mirror to 1.45.1 (PATCH).
- `src/dual_research/ui/static/version-notes.json` — regenerated via `scripts/build_version_notes.py` per the dev-next step 15b rule, now 209 entries (was 208), with v1.45.1 at the top.

## Decisions made during implementation

- **Two parallel spacing tokens.** Live `components.css` uses `var(--s-2)` (defined in `src/dual_research/ui/static/tokens.css`); DS `composed-components.css` uses `var(--md-sp-2)` (defined in `design-system/assets/styles/tokens-and-primitives.css`). Both equal 8px. Followed the conventions already in each file rather than forcing one token system to dominate — that's a separate cleanup, not in scope.
- **Placement in DS file.** Added the new rule directly below the `.changelog-internal-row` block (spec 0220's most-recent landing) since both rules govern Changelog-tab anatomy and the spec 0220 → 0220.1 lineage is the natural narrative. No structural reshuffle of the DS file.
- **PR description embedded prose verification, not screenshots.** Followed the pattern from PR #257 (spec 0220) — cited the `getBoundingClientRect()` numbers from `preview_eval` directly. Avoids the extra step of hosting an image attachment when the BCR check + the spec's scenario-1 acceptance criteria are mechanically verifiable from the eval output.

## Verified runtime behavior

Verified via Claude Preview MCP against the local dev server before push, then again against `dual-research-alex.fly.dev/version-notes.json` after the GH Actions deploy:

1. `.menu-section-num` for `v1.45.1`, `v1.45.0`, `v1.44.25`, `v1.44.24` all report `getBoundingClientRect().width === 48`. Pre-fix the span was `width: 18px`, so the post-fix delta is exact.
2. Adjacent summary text node's `left` is exactly 8px (= `var(--s-2)`) beyond the version span's `right`. Spec scenario 1 acceptance: `numRect.width >= 48` AND `textRect.left > numRect.right` — both pass for every sampled entry.
3. Gap is stable across 6-char (`1.45.1`), 7-char (`1.44.25`), and short legacy versions — `min-width` (not `width`) lets the column grow without breaking layout.
4. Live `dual-research-alex.fly.dev/version-notes.json` returns 209 entries with `v1.45.1` at the top, confirming the deploy carried both the JSX/CSS bump and the regenerated sidecar.

## Next

`/dev-next` for whichever's queued next (queue is empty after this — spec 0220.1 was the only entry).
