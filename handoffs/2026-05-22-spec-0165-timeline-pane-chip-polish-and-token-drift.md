---
spec: "0165"
date: 2026-05-22
version: 1.26.0
pr: https://github.com/Lexiz/dual-research/pull/188
---

# Spec 0165 — Timeline pane chip polish + light-mode token drift fix

v1.26.0 ships five scoped chip-readability fixes to the timeline pane after spec 0164's M3 card surface (`--md-surface-container-high`) swallowed the chip-primitive tonal-container backgrounds. All overrides scope to `.tl-card-head` or `.tl-phase__chips` — global `.chip.tone-*` rules and critique-pane chips are untouched.

## What landed

- **§2.1 token override — no-op.** The spec's central claim ("live tokens.css does NOT override `--md-on-primary-container` / `--md-on-secondary-container` in body.light") was stale. Both `src/dual_research/ui/static/tokens.css` (lines 339, 342) and `design-system/assets/styles/tokens-and-primitives.css` (lines 204, 207) already carry the canonical `#3b2810` / `#0a322d` light values. Skipped the code change; documented in CHANGELOG.
- **§2.2 Identity chip backgrounds (scoped `.tl-card-head`).** `.chip.tone-claude` → `color-mix(in srgb, var(--p-sable) 30%, transparent)`. `.chip.tone-gpt` → 30 % `--p-sage`. `.chip.tone-neutral:not(.mono)` (System) → 20 % `--p-idle` with forced `color: var(--md-on-surface)` (held at 20 % vs. 30 % because the idle palette is itself dimmer; 30 % reads too prominent; text colour forced because System identity is neutral, not branded).
- **§2.3 Activity chip surface bump (scoped `.tl-card-head`).** `.chip.tone-neutral.mono` → `--md-surface-container-highest` (one tier brighter than the card's surface-container-high). Without this the activity chip vanishes against the card.
- **§2.4 Phase-header category-bubble alpha dim (scoped `.tl-phase__chips`).** All four tones (`tone-info` / `tone-warn` / `tone-err` / `tone-idle`) drop their `.cat-bubble` to 70 % `color-mix`. Brand hue stays dominant, knockout-white Q/D/I/C letter stays legible. Scoped so critique-pane kind cluster keeps 100 % saturation.
- **§2.5 Cost precision.** New `fmtCost2(n)` helper in `src/dual_research/ui/static/run-detail.jsx`, placed next to the existing `fmtCost1` (spec 0146). Returns `<$0.01` for `0 < n < 0.01`, otherwise `$X.XX`. Handles null/NaN with `$—`. Call site at `.tl-thread__actions` (line ~1311) swaps `fmt.cost` → `fmtCost2`; the repair-case literal `$0.0000` → `$0.00`. The 4-decimal `fmt.cost` from `shared.jsx` stays the audit value for the run-detail footer aggregate.
- **§2.6 Light-mode chip-text backstop (scoped `.tl-card-head`).** `body.light` selectors carry explicit `#3b2810` / `#0a322d` on the Claude / GPT chips and their `.chip-label` children. Same values §2.1's tokens already produce — declared scoped as defensive overlay in case the tokens drift again.
- **DS catch-up.** `design-system/SPEC.md` §4.4 gained a chip-polish table + the cost-chip rule; §9.6 letter-bubble note allows alpha-modulated fills on `.tl-phase__chips`. `design-system/assets/Design System v2.html` §16 expanded-turn example cost chip: `$0.0566` → `$0.06`.

## Tests

- `uv run pytest tests/ -q` — **1532 passed in 19.42s**. No new tests added (visual/CSS spec).
- `npm test` (vitest, happy-dom) — **9 passed (9)**.
- Live-push end-to-end: every branch-phase event (`branched`, `implementing_started`, `implement_complete`, `tests_started`, `tests_green`, `pr_opened`, `merged`) landed on `origin/main` as its own commit within seconds.

## Deploy notes

- Fly bluegreen surfaced the now-familiar **lease-table error** on the first `fly deploy` attempt: `failed to get lease on VM e822e92c1e7d68: machine not found`. Build succeeded; rollout aborted. `/api/health` continued to return `1.25.0` (previous version) from unchanged machines.
- **Second `fly deploy` attempt** also hit a lease error (`failed to get lease on VM 1851d1ea539e48: machine not found`) but **the rollout still landed**. Cluster converged to version 308 (image `01KS8E81KMDJGR18BCM0ABD677`), 2/2 machines healthy. `/api/health` → `{"ok":true,"version":"1.26.0","backend":"supabase"}`.
- Post-deploy sweep: `sweep: no stale blues on dual-research-alex` (cluster size 2/2 expected).
- **Worktree-lock note.** After the squash-merge, `git checkout main` failed with `fatal: 'main' is already used by worktree at '/Users/alexlisitzky/dual-research-author'` because the authoring worktree has main checked out. Worked around with `git switch --ignore-other-worktrees main`. The queue worktree now tracks main correctly.
- **PR merge needed a second attempt.** Author worktree pushed `9ef00d0 spec(0167+0168): amend with iter 1-15 refinements` to main while the 0165 PR was open. First `gh pr merge --admin --squash` errored with `Base branch was modified`. After `git fetch origin main` + `git merge origin/main` on the branch (auto-resolved cleanly) and re-push, the second `gh pr merge` succeeded.

## Open follow-ups

- **Fly bluegreen lease-table flakes — 5 deploys in a row** (handoffs 0160 / 0161 / 0163 / 0164 / 0165). This is now consistent enough to be worth filing upstream with Fly or building a pre-deploy lease-clearing step.
- The author worktree's concurrent edits during the drain are unsynchronised. Going forward, may want to either (a) freeze author work during a `/dev-queue-run` or (b) make the merge re-base loop in `/dev-next` more robust.

## What's intentionally still rough

- §2.2's tonal % values (30 / 30 / 20) are educated guesses; visual smoke against the live deploy may suggest a 25/35 or other tuning.
- The §2.6 backstop is defensive duplication. If it's never needed, it's dead code; if it's ever needed, it's load-bearing. Kept as the spec requested.
