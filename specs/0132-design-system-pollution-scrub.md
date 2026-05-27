---
spec: 0132
title: Design-system pollution scrub (post-arc cleanup)
label: refactoring
version-bump: PATCH
status: proposed
target-version: 1.6.10
created: 2026-05-20
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0132 — Design-system pollution scrub

> Follows: 0127 → 0131 arc (now closed and grep-verified clean against production).
> Complexity: **M** (~58 small replacements + ~20 comment rewrites + 1 file-banner rewrite + 1 dead-class deletion).
> Drive mode: **by hand** (small mechanical sweeps + targeted edits + verification).

## 1. Context

Spec 0131 closed the 5-spec v1 → v2 design-system migration arc. Production greps confirm zero `var(--(bg|fg|border|r|t|mono|sans|serif)-?[0-9]*)` references remain in CSS or JSX. But a post-arc pollution audit (2026-05-20) surfaced residue that the arc did not target — pre-existing typos, duplicate vocabulary, and narrative comments that no longer reflect reality.

The arc's job was to retire v1. This spec's job is to remove what's left over from having lived in two design systems simultaneously:

1. **One real correctness bug:** `var(--w-semibold)` typo at 3 JSX sites, resolving silently to default 400 instead of intended 600.
2. **One structural duplicate:** `--w-regular/medium/semi/bold` (51 refs) and `--md-w-regular/medium/semi/bold` (85 refs) define identical values under two names. The arc's stated principle is "one token vocabulary in code: `--md-*` everywhere"; the `--w-*` short alias is the holdover.
3. **One file-banner lie:** `components.css:2` reads `dual-research — V1 Component vocabulary`. After 0131, that header documents a system that no longer exists.
4. **One dead class with two consumers:** `.chip-pill` is a no-op (pill is the default for `.chip` since spec 0119), but lingers in `run-detail.jsx:5001` and as a legacy alias in `shared.jsx:780`.
5. **One stale comment on a live slot:** `components.css:239` calls `<Chip icon=…>` a "Legacy slot — kept for back-compat". The slot has 5 active consumers; the comment is wrong.
6. **Four `border-radius: 999px` literals** in `components.css` that should consume `var(--md-shape-full)`, matching the convention the 0131 theme drain established.
7. **~18 stale v1/migration narrative comments** spread across the four CSS files. These narrate a transition that's complete.
8. **One untracked draft spec** sitting in the working tree across the entire 0127 → 0131 arc.

After this spec lands, the codebase carries one weight vocabulary, one shape-full token, accurate banners and comments, no dead classes, and no untracked drafts. Spec-attribution comments stay — they're useful provenance, not pollution.

## 2. Goals

1. Fix the `--w-semibold` typo at 3 JSX call sites.
2. Consolidate weight vocabulary onto `--md-w-*`. Replace every `var(--w-regular|medium|semi|bold)` reference in CSS/JSX with its `--md-w-*` equivalent. Delete the `--w-*` definition block from `tokens.css`.
3. Rewrite the `components.css` file banner to reflect post-arc state.
4. Delete `.chip-pill` from JSX (`run-detail.jsx:5001`) + CSS (`components.css:132-135`) + the legacy alias in `shared.jsx:780`.
5. Rewrite the `components.css:239` "Legacy slot" comment on `<Chip icon=…>` to reflect that the slot is live.
6. Replace 4× `border-radius: 999px` in `components.css` with `var(--md-shape-full)`.
7. Scrub stale v1/migration narrative from CSS comments (see § 5d). Keep spec-attribution lines that describe design intent.
8. Dispose of `specs/NNNN-run-detail-header-rework.md` per user direction (commit-as-draft / move / delete).
9. Acceptance grep `grep -rE 'var\(--w-(regular|medium|semi|bold|semibold)\)' src/dual_research/ui/static/` returns **0**.
10. Acceptance grep `grep -E '^\s*--w-(regular|medium|semi|bold):' src/dual_research/ui/static/tokens.css` returns **0**.
11. Acceptance grep `grep -nE 'border-radius:\s*999px' src/dual_research/ui/static/components.css` returns **0**.
12. Acceptance grep `grep -rnE 'chip-pill' src/dual_research/ui/static/` returns **0**.
13. Acceptance grep `grep -nE "\\bV1 Component vocabulary\\b" src/dual_research/ui/static/components.css` returns **0**.
14. Full pytest suite (1194+) passes.
15. Live deploy at 1.6.10 / `?v=0132a` renders without visible regression.

## 3. Non-goals

- **No spacing vocab consolidation.** `--s-*` (119 refs) vs `--md-sp-*` (23 refs) is a separate structural decision worth its own spec — 119 refs is too big to absorb here, and a future reader looking at this PR shouldn't be asked to also re-decide spacing.
- **No elevation/motion/easing consolidation.** `--e-*` vs `--md-elev-*`, `--m-*` vs `--md-dur-*`, `--ease` vs `--md-easing-*` are NOT duplicates — they encode different design choices (single vs two-shadow elevation, 180ms vs 200ms, single default vs multi-variant easing). Consolidating them would change visuals.
- **No new components or features.** Pure cleanup.
- **No spec-attribution comment scrub** (e.g. `Spec 0111 — single source of truth for list-item card padding`). These are useful design-intent provenance, not pollution.
- **No CSS comment rewrite beyond § 5d.** Anything not listed there stays.
- **No JSX rewrites beyond the 3 typo sites, the 1 `.chip-pill` consumer, and the 1 legacy-alias line in `shared.jsx`.**
- **No CHANGELOG history rewrite.** Past entries that name v1 stay as historical record.

## 4. Current-state audit (re-confirmed 2026-05-20)

```
$ grep -nE 'var\(--w-semibold\)' src/dual_research/ui/static/*.jsx
src/dual_research/ui/static/compare.jsx:91:            fontWeight: 'var(--w-semibold)',
src/dual_research/ui/static/search.jsx:71:            fontWeight: 'var(--w-semibold)',
src/dual_research/ui/static/shortcuts-overlay.jsx:44:              fontWeight: 'var(--w-semibold)',

$ grep -rE 'var\(--w-(regular|medium|semi|bold)\)' src/dual_research/ui/static/ \
    --include='*.css' --include='*.jsx' | grep -v tokens.css | wc -l
51

$ grep -nE '^\s*--w-[a-z]+:' src/dual_research/ui/static/tokens.css
72:  --w-regular: 400;
73:  --w-medium:  500;
74:  --w-semi:    600;
75:  --w-bold:    700;

$ grep -nE 'border-radius:\s*999px' src/dual_research/ui/static/components.css
3576:  display: inline-block; padding: 1px 8px; border-radius: 999px;
3605:.settings-input--search { padding: 6px 12px; border-radius: 999px; min-width: 240px; }
3646:  padding: 4px 10px; border-radius: 999px;
3687:  padding: 2px 8px; border-radius: 999px;

$ grep -rn 'chip-pill' src/dual_research/ui/static/
src/dual_research/ui/static/run-detail.jsx:5001:                className="chip tone-muted chip-pill"
src/dual_research/ui/static/shared.jsx:780:        pill && 'chip-pill',                                 // legacy no-op (pill is default)
src/dual_research/ui/static/components.css:132:/* Legacy: .chip-pill was the opt-in to pill shape. Pill is now the
src/dual_research/ui/static/components.css:135:.chip-pill { border-radius: var(--md-shape-full); }
```

## 5. Concrete edits

### 5a. Phase 1 — `--w-semibold` typo fix

| File:line | Find | Replace |
|---|---|---|
| `compare.jsx:91` | `fontWeight: 'var(--w-semibold)'` | `fontWeight: 'var(--md-w-semi)'` |
| `search.jsx:71` | `fontWeight: 'var(--w-semibold)'` | `fontWeight: 'var(--md-w-semi)'` |
| `shortcuts-overlay.jsx:44` | `fontWeight: 'var(--w-semibold)'` | `fontWeight: 'var(--md-w-semi)'` |

### 5b. Phase 2 — weight vocab consolidation

**Mechanical sweep across `base.css` + `components.css` (CSS only; no JSX uses the bare `--w-*`):**

- `var(--w-regular)` → `var(--md-w-regular)` (replace_all)
- `var(--w-medium)`  → `var(--md-w-medium)`  (replace_all)
- `var(--w-semi)`    → `var(--md-w-semi)`    (replace_all)
- `var(--w-bold)`    → `var(--md-w-bold)`    (replace_all)

51 refs total across the two files. After the sweep, delete the four `--w-*` definition lines from `tokens.css:72-75` and the surrounding comment that introduces them.

### 5c. Phase 4 — `.chip-pill` dead-code removal + `<Chip icon=>` comment fix

- `run-detail.jsx:5001`: `className="chip tone-muted chip-pill"` → `className="chip tone-muted"` (pill is default since spec 0119).
- `shared.jsx:780`: delete the line `pill && 'chip-pill',                                 // legacy no-op (pill is default)`. Adjust surrounding `clsx`/array syntax as needed.
- `components.css:132-135`: delete the `/* Legacy: .chip-pill ... */` comment block and the `.chip-pill { border-radius: var(--md-shape-full); }` rule entirely.
- `components.css:239`: rewrite `/* Legacy slot — kept for back-compat with <Chip icon=…>. */` to `/* Chip icon + unit slots — used by <Chip icon=…> consumers in run-list, run-detail. */`.

### 5d. Phase 3 — CSS comment scrub (full list)

Each row is an exact edit. Spec-attribution lines NOT in this list stay.

| File:line | Action |
|---|---|
| `tokens.css:1-12` (file-header block) | Rewrite to a 4-line v2-only purpose statement. Drop the "used to carry v1... migration arc... migrating every consumer to --md-*" narrative. |
| `tokens.css:128-129` | Rewrite `Material 3 token layer (introduced by SPEC-0092 as the v2 additive layer; v1 → v2 migration completed in spec 0131).` → `Material 3 token layer — full M3 color / typography / shape / spacing / motion roles.` |
| `tokens.css:310-311` | Delete the `--e-1 / --e-2 v1 elevation. The M3 color roles themselves flip at the body.light block farther down (was SPEC-0092).` comment. Replace with a one-liner: `Light-mode overrides for elevation shadows + M3 color roles.` |
| `tokens.css:334` | Rewrite `M3 light-mode role-token overrides (originally SPEC-0092).` → `M3 light-mode role-token overrides.` |
| `theme.css:1-15` (file-header block) | Rewrite to drop the `After spec 0131 closed the v1 → v2 migration arc...` narrative + `No v1 component currently reads these` line. Keep the spec-0092 attribution for the M3 tint/density body classes if it remains accurate. |
| `base.css:42` | Rewrite `Global focus indicator — V1 fix.` → `Global focus indicator.` |
| `base.css:146` | Rewrite `── Markdown rendering — tightened to V1 scale ───────` → `── Markdown rendering ───────` |
| `base.css:228-233` | Rewrite the `SPEC-0092 — Material 3 typography role utilities (additive)... Existing v1 .t-display / .t-title / .t-h3 / ... untouched so v1 components keep rendering identically.` comment to drop the v1-coexistence narrative. Keep the M3 attribution line. |
| `base.css:254` | Rewrite `On-surface colour helpers (additive — no collision with v1 .muted etc.` → `On-surface colour helpers.` |
| `base.css:260` | Rewrite `M3 reduced-motion companion. The v1 @media block above is` → `M3 reduced-motion companion.` (drop the v1 @media reference; check that the trailing line continues to make sense). |
| `components.css:2-15` (file-banner block) | Rewrite. Drop `V1 Component vocabulary`. Replace with `dual-research — Component vocabulary (Material 3)` and a concise one-paragraph purpose statement. Keep the table of component sections + spec attributions (SPEC-0052..0058 references) if still informative. |
| `components.css:98-110` | Rewrite the Chip header comment to drop `v1 .chip + the M3 .chip.tone-* cascade that previously lived` + `legacy aliases: a (=claude), b (=gpt),`. Keep the spec-0119 attribution. |
| `components.css:159-163` | Decide on legacy tone aliases. If `tone-a` / `tone-b` have no JSX consumers, delete the alias rules + comment. If they do, keep but rewrite the comment to drop `Code is being migrated to tone-claude / tone-gpt; until then both work.` (Verify at execution time.) |
| `components.css:651-653` | Rewrite `Replaces the legacy .qt-head composition for new-protocol render.` → drop the "legacy" reference, keep the spec-0119 attribution. |
| `components.css:778-784` | This is a kept-class rule for `.qref / .qt-pill / .qt-row` styled "for legacy data". Keep the rule (it's still load-bearing for old data), but rewrite the comment to drop the meta-narrative about it being from spec 0119 — just describe what the rule does. Verify at execution time that no JSX currently emits `.qref` / `.qt-pill` / `.qt-row`; if none, also flag for deletion in a follow-up. |
| `components.css:1144-1146` | Rewrite the `SPEC-0109 — modal chrome migrated to M3 surface tokens. The .md-dialog .dr-modal-* rules style the legacy header / tabs / body / close button` comment. Drop "migrated to" and "legacy" framing. Keep what the rule does. |
| `components.css:1358-1361` | Rewrite `Mirrors v2-m3.css:299-494 verbatim. Additive — v1 classes above remain for call sites not yet migrated.` → drop entirely or replace with a one-line section description. |
| `components.css:1535` | Rewrite `that lived here was the source of the v1/M3 split.` → drop the v1/M3 framing. Describe the current rule's purpose only. |
| `components.css:1568` | Delete `No live component reads these yet — subsequent specs migrate.` (the subsequent specs landed; this is stale). Verify the rule is still useful before deleting the rule itself; if no consumer, delete the rule too. |
| `components.css:3782-3785` | Rewrite the `Spec 0131 — legacy classes drained from theme.css... v1 → v2 finalization arc (0127 → 0131).` comment to a one-line section header describing what the migrated classes do. |

**Execution rule:** when rewriting any comment, keep design intent + spec attribution. Drop transitional narrative ("legacy", "v1 → v2", "additive — won't collide", "subsequent specs migrate", "until then both work").

### 5e. Phase 5 — 999px literals → `var(--md-shape-full)`

Four `replace_all`-style edits in `components.css`, but each in a different rule context — do them as individual `Edit` calls to be safe:

| Line | Find | Replace |
|---|---|---|
| 3576 | `padding: 1px 8px; border-radius: 999px;` | `padding: 1px 8px; border-radius: var(--md-shape-full);` |
| 3605 | `padding: 6px 12px; border-radius: 999px; min-width: 240px;` | `padding: 6px 12px; border-radius: var(--md-shape-full); min-width: 240px;` |
| 3646 | `padding: 4px 10px; border-radius: 999px;` | `padding: 4px 10px; border-radius: var(--md-shape-full);` |
| 3687 | `padding: 2px 8px; border-radius: 999px;` | `padding: 2px 8px; border-radius: var(--md-shape-full);` |

### 5f. Phase 6 — NNNN-run-detail-header-rework.md disposition

Pause and ask the user at execution time. Three options:
- **Commit as draft** — rename to `specs/NNNN-run-detail-header-rework.md` lives at e.g. `specs/_drafts/run-detail-header-rework.md` and gets committed.
- **Move to a /drafts/ folder** untracked but documented.
- **Delete** — the user has not picked this back up across 0128–0131, evidence suggests it's stale.

Default: **delete** unless user picks otherwise. (4+ specs of dormancy + no current arc owner.)

## 6. Files touched (estimate)

- `src/dual_research/ui/static/tokens.css` — file-header rewrite + 2 mid-file comment edits + 4 lines of `--w-*` block deletion
- `src/dual_research/ui/static/base.css` — ~4 comment rewrites + ~30 `--w-*` → `--md-w-*` replaces
- `src/dual_research/ui/static/components.css` — banner rewrite + ~12 mid-file comment edits + ~21 `--w-*` → `--md-w-*` replaces + 4× 999px → `--md-shape-full` + delete `.chip-pill` rule
- `src/dual_research/ui/static/theme.css` — file-header rewrite
- `src/dual_research/ui/static/compare.jsx` — 1 line
- `src/dual_research/ui/static/search.jsx` — 1 line
- `src/dual_research/ui/static/shortcuts-overlay.jsx` — 1 line
- `src/dual_research/ui/static/run-detail.jsx` — 1 line
- `src/dual_research/ui/static/shared.jsx` — 1 line (delete the legacy alias array entry)
- `src/dual_research/ui/static/index.html` — cache-bust `?v=0131a` → `?v=0132a` (25 occurrences)
- `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock` — 1.6.9 → 1.6.10
- `CHANGELOG.md` — append 1.6.10 entry
- `specs/NNNN-run-detail-header-rework.md` — disposition per § 5f

**Total: ~12 files touched.**

## 7. Test plan

- [ ] Pre-execution: re-run § 4 audit greps and confirm counts match.
- [ ] Acceptance greps (§ 2 goals 9-13) all return 0.
- [ ] `pytest` — full suite passes (target 1194+).
- [ ] Visual spot-check at production URL post-deploy:
  - [ ] `/#/runs` — chip rendering, weight on filter labels (Phase 1 affects compare/search chips)
  - [ ] `/#/compare` — labels at `compare.jsx:91` render at weight 600
  - [ ] `/#/search` — labels at `search.jsx:71` render at weight 600
  - [ ] Shortcuts overlay (`?` key) — `shortcuts-overlay.jsx:44` labels at weight 600
  - [ ] `/#/runs/<id>` — chip in `run-detail.jsx:5001` still renders pill (default) without the `.chip-pill` class
  - [ ] `/#/settings` — `.settings-input--search` (Phase 5) still pill-shaped via `--md-shape-full`
- [ ] No console errors on any route at production.
- [ ] Health endpoint reports `1.6.10`.

## 8. Risks

- **Phase 2 risk:** misnaming a `--w-*` ref in JSX. Mitigation: grep-clean check after the sweep + visual spot-check on a chip-heavy route.
- **Phase 3 risk:** deleting a comment that a future reader genuinely needs. Mitigation: scope to explicit narrative pollution (v1, migration, legacy, additive) — keep spec-attribution + design-intent lines.
- **Phase 4 risk:** the `.chip-pill` removal misses a JSX consumer outside `src/dual_research/ui/static/` (e.g. a test fixture). Mitigation: `git grep chip-pill` at repo root before deletion.
- **Phase 5 risk:** the 999px literal has different rounded-corner semantics than `--md-shape-full` (`9999px`). Mitigation: visually inspect each affected element — `999` vs `9999` is identical for any element shorter than ~999px (every affected element is < 100px tall).
- **Boundary risk:** the `--w-*` block deletion + cache-bust must land together. If `tokens.css` deploys with `--w-*` deleted but a JSX file still references it (e.g. due to a forgotten one), that label renders at the CSS default. Mitigation: acceptance grep gate before the deletion commit; grep-verify against production after deploy.

## 9. Open questions

- **Phase 6 NNNN draft** — user decision required at execution time.
- **`tone-a` / `tone-b` aliases** (in scope of § 5d:159-163) — depending on grep result at execution, either keep + relabel or delete. Default: delete if 0 JSX consumers.
- **`.qref` / `.qt-pill` / `.qt-row` rules** at components.css:778-784 — flagged in § 5d. If 0 JSX consumers, propose deletion; defer the actual deletion to a follow-up spec if the user wants this PR small.

## 10. After this spec

- Cleanup follow-ups deliberately out of scope here, in declining order of impact:
  1. **Spacing vocab consolidation** — `--s-*` (119 refs) ↔ `--md-sp-*` (23 refs). Same shape as Phase 2 but bigger. Decide direction (the codebase has voted for `--s-*` 5:1, but the M3-purity principle voted the other way for weight).
  2. **`.qref / .qt-pill / .qt-row` and `tone-a / tone-b` audit** — separate small spec if § 5d sweep finds no consumers but PR scope prevents inline deletion.
- Neither follow-up is committed; both depend on user direction.
