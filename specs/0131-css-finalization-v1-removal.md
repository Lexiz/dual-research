---
spec: 0131
title: CSS finalization + v1 token block removal + IBM Plex removal (close the migration arc)
label: refactoring
version-bump: PATCH
status: proposed
target-version: 1.6.9
created: 2026-05-20
pr: ""
---

# Spec 0131 — CSS finalization + v1 token block removal

> Depends on: 0127, 0128, 0129, 0130 (entire JSX side of the migration arc).
> Part of: 5-spec migration arc 0127 → 0131. **Fifth and final spec; closes the loop.**
> Complexity: **H** (~374 CSS token replacements + theme.css legacy-class drain + v1 token block deletion + IBM Plex removal + SPEC § 12 deletion + cross-route visual matrix). The riskiest spec in the arc because it's the no-return moment.
> Drive mode: **by hand** (mechanical token sweep + targeted deletions + careful verification).

> Pre-flight: this branch was created off `main` at the time of spec 0127 planning. Before executing, run `git fetch && git rebase origin/main` to pick up specs 0128 + 0129 + 0130. Re-run the audit greps in § 4 to confirm CSS v1 counts still match — drift > ~20 references means the spec needs a refresh.
>
> **HARD PREREQUISITE.** Run `grep -clE 'var\(--(bg|fg|border|r|t)-' src/dual_research/ui/static/*.jsx` first. If this returns any matches, **stop and do not execute 0131**. Some JSX file from spec 0130 still has v1 references; that work must finish before 0131 can delete the v1 token definitions.

## 1. Context

After specs 0127 (canonicalization), 0128 (run-detail.jsx), 0129 (design-language.jsx), and 0130 (other JSX) ship, **every `.jsx` file in `src/dual_research/ui/static/` reads from the v2 (`--md-*`) token vocabulary**. The remaining v1 token consumers live in three places:

1. **CSS files** — `base.css` (~36 v1 refs), `components.css` (~323 v1 refs), `theme.css` (~15 v1 refs + 8 legacy classes). Combined ~374 v1 references across CSS.
2. **The v1 token *definition* block** at the top of `src/dual_research/ui/static/tokens.css` (roughly lines 1–164). These DEFINE the v1 tokens (`--bg-0: #...`, `--fg-1: #...`, etc.); deleting them is the act that retires v1.
3. **IBM Plex font `<link>` tags** in `index.html` plus the `--sans` / `--serif` / `--mono` v1 font aliases in `tokens.css`. With JSX migrated to `--md-font-data` / `--md-font-plain` / `--md-font-brand`, these are unused.
4. **`design-system/SPEC.md § 12 Migration status`** — the temporary tracking table introduced by spec 0127. Deleting it is the formal "the migration is done" signal.

This spec ships all four in one PR. After it lands:

- Any leftover `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)` / `var(--r-*)` / `var(--t-*)` / `var(--mono)` / `var(--sans)` / `var(--serif)` reference in the repo resolves to undefined and breaks visibly — **no silent fallback masks a missed migration**.
- IBM Plex stops loading. Roboto Flex + Roboto Serif + Material Symbols are the only font stacks.
- `design-system/SPEC.md` no longer carries the migration-status section; the design system is documented as a single coherent state.

This is the **no-return** spec. Treat it accordingly: visual regression matrix is comprehensive (every routed surface in both themes at both density breakpoints), and the implementer must hold the PR until each matrix shot has been hand-verified against `main`.

## 2. Goals

1. Migrate every v1 token reference inside `base.css`, `components.css`, `theme.css` to its v2 equivalent per § 5.
2. Drain `theme.css` of its 8 legacy v1 component classes — for each: either rewrite under v2 tokens and move into `components.css`, or delete if no consumer remains.
3. Delete the v1 token *definition* block from `tokens.css` (the `--bg-*`, `--fg-*`, `--border-*`, `--r-*`, `--t-*` definitions + the `--sans` / `--serif` / `--mono` font aliases + the light-mode `body.light` v1 overrides).
4. Remove the IBM Plex `<link>` tags from `index.html`.
5. Delete `design-system/SPEC.md § 12 Migration status` (the section becomes obsolete once 0131 ships).
6. Acceptance grep `grep -rE 'var\(--(bg|fg|border|r|t|mono|sans|serif)-?[0-9]*\)' src/dual_research/ui/static/` returns **0** matches.
7. Acceptance grep `grep -i "IBM Plex" src/dual_research/ui/static/index.html` returns **0** matches.
8. Full pytest suite (1194+) passes.
9. Every routed surface renders without visible regression in dark + light, comfortable + compact density.

## 3. Non-goals

- **No JSX edits.** Every `.jsx` was migrated by 0128/0129/0130; 0131 doesn't touch them.
- **No new components or features.** Pure removal + token sweep.
- **No design system spec rewrite beyond removing § 12.** SPEC.md content is already v2-canonical (set by spec 0127); this spec only deletes the temporary migration-status section.
- **No diagram skill alignment.** The cream + indigo palette of the diagram skill stays as-is (deferred to a future optional spec per the spec 0127 decision).
- **No CHANGELOG history rewrite.** Old entries that reference v1 tokens stay as historical record.
- **No removal of the `_archive/v1/` folder.** Historical reference preserved per spec 0127.

## 4. Current-state audit

CSS v1 token counts (audited 2026-05-20 against main `93d0538`):

| File | v1 refs | Notes |
|---|---:|---|
| `tokens.css` | 0 in `var(…)` usage (definitions only) | The v1 *definition* block lives here (~lines 1–164). Deletion target. |
| `base.css` | 36 | Likely concentrated in the v1 `.t-*` type utility classes + scrollbar / focus / selection helpers. |
| `components.css` | 323 | The biggest single CSS surface. Spans the entire pre-M3 component catalog (every `.chip`, `.card`, `.tab`, `.as`, `.sb`, `.cs-*`, `.qthread`, `.consumption-*`, `.phase-rail-*`, `.dr-modal-*`, etc. — plus all SPEC-0050..0091 era selectors). |
| `theme.css` | 15 | Eight legacy classes — `.phase-step-line`, `.uppercase-label`, `.dr-ghost-block` + `.dr-ghost-block::before` + `.dr-ghost-block-kind`, `.dr-section-brief-btn` + `:hover`, `.cap-bar` + `> i` + `> .soft-mark`, `.bg-grid`. |
| **Total** | **~374** | Plus the v1 token block (definitions) in `tokens.css`. |

> **Execution note:** re-run counts at execution start:
> ```
> for f in tokens.css base.css components.css theme.css; do printf "%4d  %s\n" $(grep -cE 'var\(--(bg|fg|border|r|t)-[0-9]+\)' src/dual_research/ui/static/$f) $f; done
> ```

### Theme.css legacy-class disposition

For each legacy class, decide one of: **migrate** (rewrite under v2 tokens, move to `components.css`), **delete** (no consumer remains), **keep** (still needed; rewrite under v2 tokens in place).

| Class | Current consumers (grep at execution time) | Disposition (decide at execution) |
|---|---|---|
| `.phase-step-line` | (re-grep) | likely: migrate to `components.css` under M3 tokens |
| `.uppercase-label` | (re-grep) — superseded by `.t-label-s` | likely: delete if no consumer; otherwise migrate |
| `.dr-ghost-block` family | (re-grep) | likely: keep / migrate — used by review-item placeholders |
| `.dr-section-brief-btn` | (re-grep) | likely: migrate to `components.css` |
| `.cap-bar` family | (re-grep) | likely: migrate — used by consumption cards |
| `.bg-grid` | (re-grep) | likely: migrate — used by streaming surfaces |

Recommended: a one-pass grep per class to enumerate consumers (`grep -rl "<class>" src/dual_research/ui/static/`) and document the disposition decisions in the PR description.

### IBM Plex disposition

- `index.html:10` — `<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@400;500;600;700&display=swap" rel="stylesheet" />` — **delete**.
- `index.html:11` — comment about SPEC-0092 keeping IBM Plex as the body default — **delete** (the comment is stale).
- `tokens.css:82-84` — `--sans` / `--serif` / `--mono` v1 font aliases — **delete** as part of the v1 token block removal.

After deletion, the only `<link>` font stacks loaded are Roboto Flex + Roboto Serif + Material Symbols.

## 5. Token mapping (mechanical, applies to all three CSS files)

Same as 0128 / 0129 / 0130:

| Find | Replace with |
|---|---|
| `var(--bg-0)` | `var(--md-surface)` |
| `var(--bg-1)` | `var(--md-surface-container-low)` |
| `var(--bg-2)` | `var(--md-surface-container)` |
| `var(--bg-3)` | `var(--md-surface-container-high)` |
| `var(--bg-4)` | `var(--md-surface-container-highest)` |
| `var(--fg-0)` | `var(--md-on-surface)` |
| `var(--fg-1)` | `var(--md-on-surface-variant)` |
| `var(--fg-2)` | `var(--md-on-surface-muted)` |
| `var(--fg-3)` | `var(--md-on-surface-faint)` |
| `var(--fg-4)` | `var(--md-on-surface-decor)` |
| `var(--border-1)` | `var(--md-outline-hair)` |
| `var(--border-2)` | `var(--md-outline-variant)` |
| `var(--border-3)` | `var(--md-outline)` |
| `var(--r-1)` | `var(--md-shape-xs)` |
| `var(--r-2)` | `var(--md-shape-sm)` |
| `var(--r-3)` | `var(--md-shape-md)` |
| `var(--mono)` | `var(--md-font-data)` |
| `var(--sans)` | `var(--md-font-plain)` |
| `var(--serif)` | `var(--md-font-brand)` |
| `var(--t-display)` | `var(--md-display-s-size)` + `var(--md-display-s-lh)` |
| `var(--t-title)` | `var(--md-title-l-size)` + `var(--md-title-l-lh)` |
| `var(--t-h3)` | `var(--md-title-m-size)` + `var(--md-title-m-lh)` |
| `var(--t-body)` | `var(--md-body-m-size)` + `var(--md-body-m-lh)` |
| `var(--t-meta)` | `var(--md-body-s-size)` + `var(--md-body-s-lh)` |
| `var(--t-mono)` | `var(--md-label-s-size)` + `var(--md-label-s-lh)` |
| `var(--t-label)` | `var(--md-label-s-size)` + `var(--md-label-s-lh)` (10/11 px shift acceptable) |

## 6. Execution order (recommended)

Strict order — earlier steps must be green before later steps run.

1. **Pre-flight gate.** Confirm `grep -rclE 'var\(--(bg|fg|border|r|t|mono)-?[0-9]*\)' src/dual_research/ui/static/*.jsx` returns 0. If not, stop — 0130 isn't done.
2. **Migrate `base.css`** per § 5. Visual-check `/#/runs` chrome.
3. **Migrate `theme.css`** per § 5. For each legacy class: re-grep consumers; either rewrite under v2 in place, move to `components.css`, or delete (record decision in PR description).
4. **Migrate `components.css`** per § 5. Largest file; expect 300+ replacements. After: visual-check every routed surface (the full matrix in § 8).
5. **Delete the v1 token *definition* block** from `tokens.css`. Specifically:
   - Lines roughly 1–164: every `--bg-*` / `--fg-*` / `--border-*` / `--r-*` / `--t-*` definition.
   - The `--sans` / `--serif` / `--mono` v1 font aliases.
   - The v1 `body.light` overrides for the deleted tokens.
   - The header comment "dual-research — Design System V1 — Tokens" line; replace with v2-canonical comment.
   - Leave intact: agent-identity tokens, status hues, and every `--md-*` block.
6. **Remove IBM Plex from `index.html`.** Delete the `<link>` tag + the stale SPEC-0092 comment about IBM Plex.
7. **Delete `design-system/SPEC.md § 12 Migration status`.** The section becomes obsolete; this is the formal completion signal.
8. **Bump versions** (pyproject + __init__ + uv.lock) → `1.6.9`. Cache-bust to next increment.
9. **Run pytest.** Must be 1194+ passing.
10. **Visual matrix.** Capture every shot in § 8. Compare against `main`. Hold the PR until all shots are clean.

## 7. Files touched

- `src/dual_research/ui/static/tokens.css` — delete v1 token *definition* block (~164 lines removed); update header comment; remove v1 light-mode overrides.
- `src/dual_research/ui/static/base.css` — migrate 36 v1 refs to v2.
- `src/dual_research/ui/static/components.css` — migrate 323 v1 refs to v2.
- `src/dual_research/ui/static/theme.css` — migrate 15 v1 refs to v2; drain or rewrite 8 legacy classes. After drain, the file may be empty enough to consider deleting; if so, also drop the `<link rel="stylesheet" href="theme.css?v=…">` from `index.html` and the cache-bust string.
- `src/dual_research/ui/static/index.html` — remove IBM Plex `<link>` tags; remove stale comment; cache-bust to next increment.
- `design-system/SPEC.md` — delete § 12 Migration status; update SPEC version notes (the "spec authoritative" note at the top can drop its reference to "migration in flight").
- `design-system/CHANGELOG.md` — new entry: "v1 → v2 migration arc complete (spec 0131)".
- `CHANGELOG.md` (root) — new `[1.6.9]` / `### Changed` (or `### Removed`) entry referencing this spec; calls out the v1 token block deletion + IBM Plex removal as the headline change.
- `pyproject.toml` — `1.6.8` → `1.6.9`.
- `src/dual_research/__init__.py` — `__version__` `"1.6.8"` → `"1.6.9"`.
- `uv.lock` — refresh.

## 8. Test plan

### Acceptance criteria

- [ ] `grep -rE 'var\(--(bg|fg|border|r|t)-[0-9]+\)' src/dual_research/ui/static/` returns **0**.
- [ ] `grep -rE 'var\(--(mono|sans|serif)\)' src/dual_research/ui/static/` returns **0**.
- [ ] `grep -i "IBM Plex" src/dual_research/ui/static/index.html` returns **0**.
- [ ] `grep -nE '^\s*--(bg|fg|border|r|t)-[0-9]+:' src/dual_research/ui/static/tokens.css` returns **0** (v1 definitions deleted).
- [ ] `grep -c "Migration status" design-system/SPEC.md` returns **0** (§ 12 deleted).
- [ ] `grep -c "V1" src/dual_research/ui/static/tokens.css` returns **0** (header comment updated).
- [ ] `uv run pytest tests/ -q` → **1194+ passed**, 0 new failures.
- [ ] Visual matrix (§ below) shows no regression beyond the documented shape bump on residual classes (if any).

### Visual regression matrix

This is the comprehensive matrix. Every routed surface, both themes, both density breakpoints. Capture from `main` before branch; compare side-by-side at PR review time.

| Route | Dark 2200×1300 | Light 2200×1300 | Dark 1400×900 | Light 1400×900 |
|---|---|---|---|---|
| `/#/runs` | ✓ | ✓ | ✓ | ✓ |
| `/r/<finished-run>` top | ✓ | ✓ | ✓ | ✓ |
| `/r/<finished-run>` items panel scrolled | ✓ | ✓ | — | — |
| `/r/<finished-run>` consumption panel | ✓ | ✓ | — | — |
| `/#/compare` (≥ 2 runs) | ✓ | ✓ | — | — |
| `/#/search?q=test` | ✓ | ✓ | — | — |
| `/#/settings` allowlist | ✓ | ✓ | — | — |
| `/#/settings#users` (admin) | ✓ | — | — | — |
| `/#/how-it-works` overview | ✓ | ✓ | — | — |
| `/#/how-it-works#cost` | ✓ | — | — | — |
| `/#/language` DNA | ✓ | ✓ | ✓ | — |
| `/#/language?full=1` | ✓ | ✓ | — | — |
| Onboarding step 4 (modal) | ✓ | — | — | — |
| 404 / error route | ✓ | ✓ | — | — |
| `body.compact` active (force via DevTools) | spot-check 3 routes | spot-check 3 routes | — | — |

**Total: ~32 hand-captured shots.** Yes, this is a lot — it's the cost of the no-return spec. Don't shortcut.

### Smoke checks during execution

- After each file migration: load `/#/runs` once, look at console, look at network, scroll. If any new red flag, stop and investigate before proceeding to the next file.
- After the v1 token block deletion: load every route once. **Any visible regression here means a `var(--bg-*)` consumer was missed** — find it via DevTools (search computed styles for "undefined" or fallback values) and fix before continuing.

## 9. Risks

1. **A consumer was missed.** Most consequential risk. Mitigation: pre-flight gate in § 6, comprehensive visual matrix in § 8. If a regression slips into prod, roll back the merge and identify the missed consumer.

2. **A `--md-*` token has wrong contrast in a corner case.** Every mapping in § 5 has shipped via 0128 + 0129 + 0130 across JSX without incident, so CSS-level swaps should behave identically. Mitigation: full visual matrix in both themes.

3. **`theme.css` legacy class drain misjudges a consumer.** Mitigation: re-grep before each class disposition; document decisions in PR description; if uncertain, **migrate rather than delete** — leftover classes are cheap, missing classes break the consumer.

4. **Light mode shadow opacity tuning.** The v1 token block contained per-theme shadow tuning. Confirm the M3 elevation tokens (which already have light-mode overrides in `tokens.css`) cover every shadow consumer. If a `box-shadow: var(--e-1)` style reference exists somewhere, that's a v1 elevation token — map to `--md-elev-1`.

5. **Cache-bust collision.** If two specs land cache-bust at the same time, browsers may serve stale CSS. Mitigation: pick a fresh `?v=` string distinct from anything used by 0127–0130.

6. **`design-system/SPEC.md § 12` removal misses a reference.** Other docs may link to § 12 (e.g., the v1 archive README). Re-grep `grep -rn "§ 12\|Migration status" design-system/` and update any pointer accordingly.

7. **Counts have drifted significantly from the audit.** The ~374 number is from 2026-05-20; by the time this spec executes, several other specs may have touched CSS. Re-run § 4 audit at execution start.

## 10. Roll-out and roll-back

- **Roll-out.** Single PR to `main`. CI green + full visual matrix captured + PR description lists every theme.css class disposition decision. Fly deploy on merge. **After deploy, smoke-test prod immediately** — every route, both themes.
- **Roll-back.** Revert the merge commit. Because this spec is comprehensive, a revert is safer than a forward fix if any post-deploy regression is unclear. The pre-merge state is byte-for-byte recoverable.

## 11. After this ships — the migration arc is complete

Final state, post-0131:

- **One design system**: v2 (Material 3), documented in `design-system/SPEC.md`, canonical visual reference at `design-system/assets/Design System v2.html`, source-of-truth CSS at `design-system/assets/styles/{tokens-and-primitives,composed-components}.css`.
- **One token vocabulary in code**: `--md-*` everywhere. Agent identity tokens (`--agent-*`) and status hues (`--ok`/`--info`/`--warn`/`--err`/`--idle`) preserved as M3-orthogonal extras.
- **One font stack**: Roboto Flex + Roboto Serif + Material Symbols Outlined. No IBM Plex.
- **One historical record**: the v1 spec preserved at `design-system/_archive/v1/SPEC.md`; the seeding artifacts at `design-system/_archive/seeding/`. Specs 0050–0126 reference v1 paths as historical record of how the migration unfolded; nothing is rewritten retroactively.
- **No drift trap**: the additive layering pattern is gone. Any `var(--bg-*)` reference fails visibly. CI vocabulary checks (already in `tests/contract/test_ui_vocabulary.py`) can be extended to grep for `var(--bg|fg|border)-` and fail builds that re-introduce v1 syntax.

**Optional follow-ups** (outside the 5-spec arc, low priority):
- Diagram skill palette alignment (cream + indigo → sable + sage) — if/when the diagram-skill output should share visual DNA with the in-app UI.
- CI lint that asserts `pyproject.toml` and `__init__.py` versions agree, preventing the kind of drift that spec 0127 had to catch up.
