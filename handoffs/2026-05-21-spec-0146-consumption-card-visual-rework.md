# Handover — Spec 0146 — Consumption card visual rework (v1.12.0)

- **Date:** 2026-05-21
- **PR:** [Lexiz/dual-research#168](https://github.com/Lexiz/dual-research/pull/168) (merged, squash, branch deleted)
- **Spec:** [specs/0146-consumption-card-visual-rework.md](../specs/0146-consumption-card-visual-rework.md)
- **Anchor run:** `20260521-010637-dvs-backend-language-choice`
- **Backlog row closed:** B16 (consumption-card visual rework + spec-preview rendering)
- **Version:** `1.11.0 → 1.12.0` (**MINOR** — third feature spec of the 0140–0147 batch; pure UI rework + one load-bearing 1-line server fix + a 6-line frontend de-camelCase pass; no protocol, schema, or contract changes)

## What landed

Pure UI rework on top of correct cost/token data (0143) and per-attachment tracking (0145). Five visible changes to `CcxCard` plus one load-bearing serialiser fix that unblocks the per-piece sub-row token attribution that was silently dead before this spec.

- **Header grid.** `.ccx-header` is now a 3-column grid that mirrors the bar-row grid below it (`minmax(140px, 28%) 1fr minmax(110px, max-content)`). The icon + agent name live inside a new `.hd-id` wrapper at column 1; the bracketed `(X.X% of 1M)` percentage sits at column 2 with `justify-self: end` so its closing `)` lands at the same x-coordinate as the right edge of the bar fill below it; the chevron sits at column 3 with `justify-self: end` at the card's right edge. Tokens and cost are removed from the header — they live at the right end of the Total-tokens bar (collapsed) or inside the totals block (unfolded).

- **Per-attachment sub-rows auto-show on card unfold.** Spec 0145 added the data path (`userPromptRowBreakdown` + `SubInputRow` + chevron on the User-prompt row) but kept the affordance default-collapsed; this spec retires the chevron + `userPromptExpanded` state and renders the User-prompt sub-rows (`Chat message` + one `Attachment · {title}` per attachment) automatically when the card is in its unfolded state. No second click required.

- **`.ccx-totals` block on the unfolded view.** Replaces the free-text web-search mono line with a structured 3- or 4-line block: `input tokens · billed` · `input cost` · `web search · N queries` (when N > 0) · `total input` (with a bold rule above per `.line.is-grand`). Labels left, values right (mirrors the bar-row grid). Verified on the anchor-run phase0-r2-claude card: `52,723` / `$0.2` / `$0.0` / `$0.2`.

- **`fmtCost1` helper scoped to the Consumption card.** New one-decimal cost formatter applied to every cost display inside `CcxCard` (Total-tokens bar, `renderInputRow`, `SubInputRow`, Output row, every totals-block `.v`). The global `fmt.cost` keeps 4-decimal precision for the run-detail footer aggregate (`$13.5110`), reconcile delta, status chips, and tooltips.

- **Server fix: `_to_camel` skips dotted keys.** [`ui/server.py::_to_camel`](../src/dual_research/ui/server.py) now passes keys containing a `.` through verbatim instead of recursively camelCasing them. This fixes a pre-existing wire-shape bug acknowledged in the 0145 handover: without the fix, `user_prompt.message` arrives at JS as `userPrompt.message`, `prior_turns.phase0` as `priorTurns.phase0`, and the snake_case canonical lookups silently miss. Single-segment canonical IDs (`user_prompt`, `current_draft`, `all_p2_turns`) are still camelCased by the server because they have no dot; the frontend `normalisePiecesRaw` helper covers them by inverting the transform on read (adds the snake_case alias for any camelCased key it sees). The two fixes together make every canonical-ID lookup in the Consumption card succeed.

- **Cache-buster.** Bumped `?v=0145a → ?v=0146a` across all 25 static-asset imports in `index.html`.

- **Design-system back-port.** `design-system/SPEC.md` §4.3 rewritten to describe the new anatomy. `design-system/assets/styles/composed-components.css` mirrors the `.ccx-header` grid + `.hd-id` wrapper. `design-system/assets/Design System v2.html` §14 lede + every `.ccx-header` in the showcase updated (9 cards rewritten to use the new markup); `.ccx-totals .line` children re-ordered from `<v><l>` to `<l><v>` (8 lines swapped) per the new label-left / value-right convention. `design-system/CHANGELOG.md` gets a 2026-05-21 entry pointing at this spec.

## Files touched

### Frontend
- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) — `fmtCost1` + `normalisePiecesRaw` helpers; header markup rewritten (3-column grid + `.hd-id` wrapper); `userPromptExpanded` state and chevron deleted; sub-rows auto-render in `renderInputRow` when `attachmentBreakdown` is non-null; all cost displays inside `CcxCard` swapped to `fmtCost1`; `.ccx-totals` block instantiated after the Output row (replaces the free-text web-search mono line); `piecesRaw` runs through `normalisePiecesRaw` so canonical lookups land on legacy single-segment IDs.
- [`src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) — `.ccx-header` flex → grid; `.hd-id` rule added; `.stats` swapped from `margin-left: auto` to `justify-self: end` + `white-space: nowrap`; `.chev` gains `justify-self: end`.
- [`src/dual_research/ui/static/index.html`](../src/dual_research/ui/static/index.html) — cache-bust `?v=0145a → ?v=0146a` across all 25 static-asset imports.

### Backend
- [`src/dual_research/ui/server.py`](../src/dual_research/ui/server.py) — `_to_camel` skips keys containing a `.`. 3-line guard inside the existing dict branch; docstring updated to document the spec-0146 invariant.

### Tests
- [`tests/ui/test_to_camel.py`](../tests/ui/test_to_camel.py) — new; 9 cases covering dotted-key preservation, single-segment snake_case camelCasing (unchanged), mixed payloads, nested dicts, attachment-ID keys, lists of dicts, int keys (regression-pin), and primitives.

### Design system
- [`design-system/SPEC.md`](../design-system/SPEC.md) — §4.3 "Consumption row" rewritten.
- [`design-system/assets/styles/composed-components.css`](../design-system/assets/styles/composed-components.css) — `.ccx-header` mirror updated.
- [`design-system/assets/Design System v2.html`](../design-system/assets/Design System v2.html) — §14 lede + every `.ccx-header` block + every `.ccx-totals .line` child order updated.
- [`design-system/CHANGELOG.md`](../design-system/CHANGELOG.md) — 2026-05-21 entry.

### Spec rewrite
- [`specs/0146-consumption-card-visual-rework.md`](../specs/0146-consumption-card-visual-rework.md) — re-validated against current main: anchor-run numbers refreshed ($10.3127 → $13.5110, etc.), §4 file:line citations updated post-0145, §5.3 spec-preview path and §5.7 round plumbing dropped, §5.2 rewritten to consume 0145's `groupPiecesForPhase` + `userPromptRowBreakdown` + `SubInputRow` instead of adding parallel helpers, §5.6 added for the `_to_camel` fix + `normalisePiecesRaw` complement, §7 test plan + §9 files-touched updated, §10 open questions marked resolved.

### Misc
- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — `1.11.0 → 1.12.0`.
- `CHANGELOG.md` — `[1.12.0]` entry.

## Open-question resolutions

Five spec-internal questions plus two new questions discovered during re-validation:

1. **Sub-cent cost display.** Keep `$0.0` for non-zero amounts under 5¢. The totals block + run-detail footer carry the audit truth; one-decimal precision in the card is a deliberate glance-view choice. **Default kept.**
2. **`fmtCost1` footer scope.** Keep 4-decimal in the footer; it's the audit number, the card is the glance. **Default kept.**
3. **Capital-T direction.** Bar-row section headers (`Total tokens`, `Output`) are title case; `.ccx-totals` block lines use lowercase (`input cost`, `total input`). Design-system §14 back-port locks both rules in. **Resolved as title case on bar-row headers only.**
4. **§5.3 spec-preview rendering — still needed?** No. 0145 shipped the per-attachment emitter and the legacy-shim, so the synthetic-row scaffolding (preview chips, diagonal stripes, `PREVIEW_ATTACHMENTS`, `FILL_CLASS_FOR`, `buildSpec0145InputBuckets`) has nothing to render. §5.3 + §5.7 (round plumbing) **removed from scope**.
5. **Preview-row totals reconciliation.** Moot — no preview rows in the shipped spec.

### Additional resolutions captured during re-validation

6. **camelCase wire-shape bug.** Adopt a 1-line server fix in `_to_camel` (skip dotted keys) so per-attachment sub-rows render real token counts. Spec §5.6 shipped it. Single-segment canonical IDs (`user_prompt`, `current_draft`, `all_p2_turns`) are still camelCased server-side; the 6-line frontend `normalisePiecesRaw` helper covers them by inverting the transform on read. The two fixes together make every canonical-ID lookup in the Consumption card succeed. **Resolved with hybrid server + frontend approach.**
7. **Per-attachment row visibility.** Auto-show sub-rows when the card is unfolded; retire 0145's `▸` chevron + `userPromptExpanded` state. **Resolved as auto-show.**

## New design-system tokens / chip primitives

**None added.** This spec reuses every existing M3 token (`--md-surface-container*`, `--md-outline-hair`, `--md-on-surface-*`, `--md-shape-*`, etc.) and every existing primitive (`.ccx-bar-row`, `.ccx-totals`, `.ccx-icon`, `.ccx-bar`). The new `.hd-id` wrapper inside `.ccx-header` is a layout-only class (no design-system semantic) that lives inside the existing `.ccx-header` rule.

## Visual regressions caught + waived

- **None caught.** The Consumption tab cards render with the new anatomy; the Compare tab uses the same `CcxCard` primitive and inherits cleanly via CSS; the Search palette and cross-run hover cards don't render full `CcxCard` (different component path) so they're insulated by construction. Light-mode parity verified at 1280px viewport — cream / sage / sable carry over correctly.
- **Anchor-run User-prompt row token count.** Pre-fix, the row showed `0t · $0.0` because of the wire-shape bug; post-fix it shows `5.3kt · $0.0`. This is real data flowing through, not a regression. The shape `5.3k + 6.7k + 3.6k = 15.6k` against an `input + output = 56.3kt` total is expected — `prompt_pieces` only captures the structured request payload; tokenizer overhead and dynamic context not in the captured pieces account for the remainder. This matches the spec-0118 contract; not introduced by 0146.

## Deploy status

- **Version:** `1.12.0`
- **Deploy timestamp:** 2026-05-21T21:56Z (machine 1 healthy on first pass at 21:47Z; machine 2 recovered after the recurring `machines.dev` mid-rolling-deploy flake — same shape as the 0141/0142/0144 handovers documented).
- **Live health:** `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.12.0","backend":"supabase"}`.
- **Both machines:** version 199, started, 1/1 health passing. Recovered machine 2 via `fly machine start 148ee320f427e8`.

### Smoke

1. **Anchor run (legacy-shim path) — local preview.** Loaded `/#/runs/20260521-010637-dvs-backend-language-choice/consumption` against the local server (`v1.12.0`). The Consumption tab rendered 42 `.ccx` cards with the new anatomy. Header pixel-alignment check: `stats.right === bar.right` (delta `0px`). The new totals block on P0-R2-Claude reads `input tokens · billed 52,723` / `input cost $0.2` / `web search · 2 queries $0.0` / `total input $0.2` — matching the spec sanity check exactly. User-prompt row shows `5.3kt · $0.0` post-normalisation (was `0t` pre-fix); P2-R2-Claude exercises `phase1.claude`, `phase1.openai`, `prior_turns.phase2`, `ledger.standing_items` cleanly.
2. **Hosted-UI bundle-marker probe.** `curl https://dual-research-alex.fly.dev/run-detail.jsx?v=0146a | grep -c 'fmtCost1\|normalisePiecesRaw\|ccx-totals'` → 11 hits. Confirms the new JSX bundle landed on both machines under the new cache-bust string.
3. **Light + dark mode parity.** Verified at 1280×800 viewport — cream/sage/sable carry over the new anatomy correctly, no theme-specific regressions.
4. **Hosted-UI visual smoke.** Auth-gated (`/api/runs/<id>/...` returns 401 without a session token, same pattern as specs 0141-0145). The JSX is deterministic given Supabase data and the local-preview smoke covers the rendering path; left as a user-side check.
5. **Fresh attachment-bearing run.** Pending — same convention as the 0145 handover ("Pending — firing a fresh run with attachments is the remaining live-data check"). The data path is end-to-end on the deployed code; a fresh run will exercise the per-attachment row rendering at the production aggregator boundary.

## Known follow-ups

- **Cosmetic .ccx-header .pct / .sep CSS rules unused.** `.ccx-header .stats .sep` and `.ccx-header .stats .pct` rules ([components.css:2531-2532](../src/dual_research/ui/static/components.css)) became orphaned when the trio collapsed to a single percentage. Left in place this PR (harmless). A cosmetic PR can remove them.
- **`closeout.request` row still suppressed.** The aggregator doesn't yet emit `was_closeout: bool` per turn (B16 §10.4 backend follow-up). The closeout row is not rendered.
- **`outputBreakdown` rendering deferred.** The output row stays a single `Output` row until reasoning / response / tool-calls are split (B16 §10.1 backend follow-up).
- **`cacheSavingsUsd` line in totals block deferred.** The `cache savings · ×N reuse on Xk` line from design-system §14 is not rendered until the backend ships `usage.cacheSavingsUsd` (B16 §10.2).
- **Single-segment canonical IDs not in the server fix.** The 1-line `_to_camel` guard only catches dotted keys; `user_prompt`, `current_draft`, `all_p2_turns` are handled by the frontend `normalisePiecesRaw` pass. A future cleanup could either extend the server-side guard with an explicit canonical-ID allowlist (brittle) or change the prompt-pieces wire shape to always use dotted IDs (would require a registry rename — `user_prompt → user_prompt.aggregate` etc., which is more invasive).
- **Spec 0147 unblocked.** Final spec in the 0140–0147 batch; standalone, no batch dependencies, no open questions per the prompt. After 0147 ships, the full batch 0140–0147 is on main.
