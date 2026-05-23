# Handover — spec 0132 · Design-system pollution scrub (post-arc cleanup)

- Date: 2026-05-20
- Spec: [`specs/0132-design-system-pollution-scrub.md`](../specs/0132-design-system-pollution-scrub.md)
- PR: _(filled by `gh pr create` below)_
- Deployed version: `1.6.10` _(filled after `fly deploy`)_

## Bottom line for the next session

Spec 0132 was a **follow-up cleanup** to the 0127 → 0131 v1 → v2 migration arc. The arc closed the migration; this spec scrubs the residue the arc didn't scope:

1. One real correctness bug: `var(--w-semibold)` typo at 3 JSX sites (silent under-weight to 400).
2. One structural duplicate: `--w-*` (51 refs) ≡ `--md-w-*` (85 refs) — same values, two names.
3. One stale file banner: `components.css:2` still read `dual-research — V1 Component vocabulary`.
4. One dead class: `.chip-pill` (pill is the `.chip` default since spec 0119).
5. Two dead alias rules: `.chip.tone-a` / `.chip.tone-b` (zero JSX consumers).
6. One stale slot comment: `<Chip icon=…>` flagged "Legacy" but has 5 live consumers.
7. Four `border-radius: 999px` literals that should consume `var(--md-shape-full)`.
8. ~18 stale v1/migration narrative comments across the four CSS files.
9. One untracked draft spec sitting in the tree across the entire arc.

After this PR: zero stale v1/legacy/migration narrative in any CSS comment; one weight vocabulary in code (`--md-w-*` only); zero `999px` literals; zero `.chip-pill` references; one consolidated, accurately-described component vocabulary. The dormant draft is filed as spec 0133 (`status: proposed`).

**Pause here.** The user's directive was to make the live site reflect the changes and tell them when done. They have not yet asked for follow-ups (see § "Open follow-ups" below).

## What shipped in 0132

- **Version bump:** PATCH → **1.6.10**
- **Cache-bust:** `?v=0131a` → `?v=0132a` on every `<link>` / `<script>` in `index.html` (25 occurrences)
- **Files touched:** 14 (1 spec + 1 spec rename + 1 CHANGELOG + 4 CSS + 5 JSX + 3 version-bump files)
- **Net change:** -46 lines (193 deletions, 147 insertions)
- **Test suite:** 1194 / 1194 pytest passing
- **Live verification:** _(filled after deploy)_

### Per-phase landed scope

| Phase | Scope | Refs | Verified |
|---|---|---:|---|
| 1 | `var(--w-semibold)` → `var(--md-w-semi)` (3 JSX sites: `compare.jsx:91`, `search.jsx:71`, `shortcuts-overlay.jsx:44`) | 3 | preview: compare h2 `font-weight: 600`; search h2 `font-weight: 600` |
| 2 | `--w-*` → `--md-w-*` mechanical sweep in `base.css` + `components.css` (51 refs), `--w-*` definition block deleted from `tokens.css:72-75` | 51 | acceptance grep returns 0 |
| 3 | ~20 comments rewritten across `tokens.css` (file-header + 3 mid-file) + `base.css` (4) + `components.css` (8 incl. file-banner) + `theme.css` (file-header) — see § 5d table below | ~20 | acceptance grep for v1/legacy/migration narrative returns 0 |
| 4 | Deleted: `.chip-pill` from `run-detail.jsx:5001`, `shared.jsx:780` legacy-alias array entry, and `components.css:132-135` rule + comment. Deleted: `.chip.tone-a` / `.chip.tone-b` alias rules (0 JSX consumers). Rewrote: stale "Legacy slot" comment on `<Chip icon=…>` at `components.css:239`. Bonus: fixed stale `--r-pill` ref in the chip header comment. | — | preview: `.chip.tone-info` renders `border-radius: 9999px` without `.chip-pill` class |
| 5 | 4× `border-radius: 999px` → `var(--md-shape-full)` in `components.css:3576, 3605, 3646, 3687` | 4 | preview: `/#/runs` search input pill-shaped |
| 6 | Untracked `specs/NNNN-run-detail-header-rework.md` (513-line draft, dormant across 0128–0131) renamed to `specs/0133-run-detail-header-rework.md` with `status: proposed`. Frontmatter `spec:` updated, status banner added. **Not implemented — preserves the work as a discoverable proposal.** | — | `git status` clean post-rename |

### Comment-scrub disposition table (Phase 3, § 5d)

| File:line | Before | After |
|---|---|---|
| `tokens.css:1-12` | "This file used to carry the v1 token block... Spec 0131 closed the v1 → v2 migration arc..." | 5-line v2-only purpose statement |
| `tokens.css:115-119` | "Material 3 token layer (introduced by SPEC-0092 as the v2 additive layer; v1 → v2 migration completed in spec 0131)." | "Material 3 token layer — full M3 color / typography / shape / spacing / motion roles." |
| `tokens.css:295-299` | "...--e-1 / --e-2 v1 elevation... (was SPEC-0092)." | Dropped "v1" + "(was SPEC-0092)" framing |
| `tokens.css:321` | "M3 light-mode role-token overrides (originally SPEC-0092)." | "M3 light-mode role-token overrides." |
| `theme.css:1-17` | "After spec 0131 closed the v1 → v2 migration arc... No v1 component currently reads these — they exist so subsequent specs (0093…0104) can flip..." | 6-line purpose statement describing what the file currently does |
| `base.css:42-44` | "Global focus indicator — V1 fix." | "Global focus indicator." |
| `base.css:146` | "── Markdown rendering — tightened to V1 scale ───────" | "── Markdown rendering ───────" |
| `base.css:227-234` | "SPEC-0092 — Material 3 typography role utilities (additive). The 15 .t-display-l / -m / -s … plus .t-data. Existing v1 .t-display / .t-title / .t-h3 / ... untouched so v1 components keep rendering identically." | "Material 3 typography role utilities. The 15 .t-display-l / -m / -s … plus .t-data." |
| `base.css:254-255` | "On-surface colour helpers (additive — no collision with v1 .muted etc. if any were to be added)." | "On-surface colour helpers." |
| `base.css:260-262` | "M3 reduced-motion companion. The v1 @media block above is authoritative for live components; this one reinforces the contract with the M3-shaped declaration." | "M3 reduced-motion companion." |
| `components.css:2-17` | "dual-research — V1 Component vocabulary" + 14-line "Sections landed in SPEC-0052..." | "dual-research — Component vocabulary (Material 3)" + 9-line purpose statement |
| `components.css:92-107` (chip header) | "Replaces the v1 .chip + the M3 .chip.tone-* cascade that previously lived further down this file." + "(plus legacy aliases: a (=claude), b (=gpt), muted, info-strong)" + stale `--r-pill` ref | Dropped v1 cascade narrative + legacy aliases mention. `--r-pill` → `--md-shape-full`. |
| `components.css:150-153` | "Legacy tone names — alias to the canonical pair. Code is being migrated to tone-claude / tone-gpt; until then both work." + `.chip.tone-a` + `.chip.tone-b` rules | Deleted both rules + comment (0 JSX consumers) |
| `components.css:239` | "Legacy slot — kept for back-compat with `<Chip icon=…>`." | "Chip icon + unit slots — used by `<Chip icon=…>` across run-list, run-detail, and others." |
| `components.css:634-637` (was 651) | "Spec 0119 — timeline turn-card chip-row header. Replaces the legacy .qt-head composition for new-protocol render. Tighter..." | "Spec 0119 — timeline turn-card chip-row header. Tighter 6px gap fits..." |
| `components.css:762-768` (was 778) | "Spec 0119 §7.2 — legacy ``.qref*`` and ``.qt-pill / .qt-row / .qt-agent / .qt-sep / .qt-round / .qt-verdict`` rules retired..." | "QuestionThread timeline + footer hints. The timeline body uses .tl-card-head + Chip slots..." |
| `components.css:1128-1132` (was 1144) | "SPEC-0109 — modal chrome migrated to M3 surface tokens. The .md-dialog block below provides M3-only styling on the outer frame; these .dr-modal-* rules style the legacy header / tabs / body / close button markup..." | "Modal chrome (SPEC-0109). The .md-dialog block below provides M3-only styling on the outer frame; these .dr-modal-* rules style the header / tabs / body / close-button markup..." |
| `components.css:1340-1344` (was 1358) | "Mirrors v2-m3.css:299-494 verbatim. Additive — v1 classes above remain for call sites not yet migrated." | "Mirrors v2-m3.css:299-494." |
| `components.css:1517-1518` (was 1535) | "Tonal chip tones + auto-dot moved into the canonical .chip section near the top of this file (spec 0119). The duplicated cascade that lived here was the source of the v1/M3 split." | "Tonal chip tones + auto-dot live in the canonical .chip section near the top of this file (spec 0119)." |
| `components.css:1547-1553` (was 1568) | "SPEC-0092 — Material Symbols Outlined sizing helpers (additive). ... No live component reads these yet — subsequent specs migrate." | "Material Symbols Outlined sizing helpers. Use as `<span class=\"ms ms-20\">check_circle</span>` ..." |
| `components.css:3758-3768` | "Spec 0131 — legacy classes drained from theme.css... v1 → v2 finalization arc (0127 → 0131)." | "Misc class helpers used by specific routes." + the same per-class consumer list |

**Execution rule applied:** keep design intent + spec attribution; drop transitional narrative ("legacy", "v1 → v2", "additive — won't collide", "subsequent specs migrate", "until then both work", "originally SPEC-0XXXX").

### Acceptance grep results (pre-commit)

```
$ grep -rE 'var\(--w-(regular|medium|semi|bold|semibold)\)' src/dual_research/ui/static/   →  0
$ grep -E '^\s*--w-(regular|medium|semi|bold):' src/dual_research/ui/static/tokens.css     →  0
$ grep -nE 'border-radius:\s*999px' src/dual_research/ui/static/components.css             →  0
$ grep -rn 'chip-pill' src/dual_research/ui/static/                                        →  0
$ grep -nE "\bV1 Component vocabulary\b" src/dual_research/ui/static/components.css        →  0
$ grep -inE "(\bv1\b|legacy|migrat(e|ion|ed)|deprecated|back-compat)" \
    src/dual_research/ui/static/{tokens,base,components,theme}.css                         →  0
```

All six clean. (The last grep wasn't a goal-line acceptance check; it's the bonus signal that Phase 3 scrubbed every flagged narrative pollution point.)

### Preview verification (local dev server)

| Route | Check | Result |
|---|---|---|
| `/#/compare` | "Compare runs" h2 font-weight | **600** (was silently 400 pre-Phase 1) |
| `/#/search` | "Cross-run search" h2 font-weight | **600** |
| `/#/runs` | first `.chip` border-radius without `.chip-pill` class | `9999px` (pill default holds) |
| `/#/runs` | search-runs input visible pill shape | ✓ |
| `/#/runs/<bad-id>` | error route renders | ✓ (404 page shows "Could not load run" + "Back to runs" pill button) |
| any | console errors | 0 |
| any | version badge in nav | **v1.6.10** |

### Out-of-scope sweeps explicitly NOT done in this PR

Per spec § 3 non-goals:

1. **Spacing vocab consolidation.** `--s-*` (119 refs) ↔ `--md-sp-*` (23 refs) are identical values under two names. The codebase has voted heavily for `--s-*`; the M3-purity principle would push toward `--md-sp-*`. **142-ref migration is too big to bundle into a pollution scrub** + the direction is a real design decision. Proposed as the next spec (see "Open follow-ups" § 1).
2. **Elevation / motion / easing consolidation.** `--e-*` vs `--md-elev-*` (single-shadow vs M3 two-shadow), `--m-*` vs `--md-dur-*` (180/200ms scales differ), `--ease` vs `--md-easing-*` (single default vs multi-variant). **These are NOT duplicates** — they encode different design choices. Consolidating any of them would change visuals. Belongs in a deliberate design spec, not pollution scrub.
3. **Spec-attribution comment scrub** (e.g. `Spec 0111 — single source of truth for list-item card padding`). These are useful design-intent provenance. Kept.
4. **CHANGELOG history rewrite.** Past entries naming v1 stay as historical record.

## Open follow-ups

1. **Spacing vocab consolidation** — same shape as Phase 2 here, but bigger (142 refs vs 51). Decide direction (`--s-*` wins per codebase popularity; `--md-sp-*` wins per the "everything `--md-*`" principle). My read for cleanest maintainability: `--md-sp-*` wins, matching the weight decision. Worth its own spec because it's a real design call, not pollution.
2. **Elevation / motion / easing design review** — three M3-vs-internal dual-stack token families that encode genuinely different design choices. Each needs an "is the M3 shadow shape better than `--e-*` here?" decision per consumer. Bigger than a sweep.
3. **Spec 0133 (run-detail header rework)** filed by Phase 6 — 513-line draft, `status: proposed`. Either greenlight or close.
4. **Inherited from 0131:** the spec-attribution comments in components.css (Spec 0052/0053/0057/0073/0083/0086/0087/0098/0101/0109/0110/0111/0112/0113/0119/0124/0125/0131) are all kept here as useful provenance. They could be moved out of code into a per-section README if the codebase ever wants comments-pure code, but that's a project-style decision.

## Risk reflection

- **Phase 2's `--w-*` block deletion is a no-return commit in the same shape as 0131's v1 block deletion** — the moment `tokens.css:72-75` is gone, any leftover `var(--w-*)` reference resolves to undefined and breaks visibly. The acceptance grep gate (returned 0 before delete) + the live deploy verification (must also return 0) protect against this. The grep before delete was clean.
- **Phase 4 risk** was that `.chip-pill` had a JSX consumer outside `src/dual_research/ui/static/`. `git grep chip-pill` at repo root after deletion: 0 matches. No miss.
- **Phase 5 risk** (999 vs 9999 visual difference) was structurally null — every affected element renders < 100px, so both values clip the corner identically.

## What I learned

1. **"What's pollution" is a fuzzy question; the audit lens that worked was "is this duplicate or stale?"** Weight tokens were duplicate (identical values, different names). Banners were stale (described a system that no longer exists). The "Legacy slot — kept for back-compat" comment was stale (live, not legacy). Elevation tokens were NOT duplicates (different shadow shapes) — and that distinction is what kept this spec scoped tightly.
2. **The "kept --w-*" decision in the 0131 handover was a description, not a design intent.** When I treated it as design intent, I was leaning toward keeping both families. Once I noticed the principle the arc itself stated ("one token vocabulary in code: `--md-*` everywhere"), the reversal was obvious. Lesson: arc-handover language describing "what we kept" is a snapshot of the state at handover, not a permanent contract.
3. **`grep -inE "(\bv1\b|legacy|migrat...)" CSS_FILES` is a remarkably good pollution detector** for a post-arc codebase. It surfaced the file banner, every stale narrative comment, every "back-compat" claim, and the dead `tone-a/tone-b` aliases. Worth keeping as a periodic sanity-check pattern.
4. **The dormant draft was substantive.** 513 lines of real design thought from an earlier session, never committed. The conservative move (delete) would have lost real work; the over-eager move (commit as a new ready spec) would have implicitly endorsed an unreviewed proposal. The middle path (file as `0133` with `status: proposed` + a banner explaining it was filed-not-implemented) removes pollution without overcommitting. Recommended pattern for future stranded drafts.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| Spec draft + audit + scope decision | done | ~15 min (incl. probe of spacing/elevation/motion/easing duplicates) |
| Phase 1 — `--w-semibold` typo (3 sites) | done | ~2 min |
| Phase 2 — `--w-*` sweep + block deletion | done | ~3 min |
| Phase 4 — `.chip-pill` removal + comment fix | done | ~5 min |
| Phase 5 — 999px tokenization | done | ~2 min |
| Phase 3 — comment scrub (~20 edits across 4 files) | done | ~15 min |
| Phase 6 — NNNN → 0133 filing | done | ~3 min |
| Version bump + cache-bust + CHANGELOG | done | ~5 min |
| pytest + acceptance greps | done | ~2 min |
| Preview verification (compare/search/runs/runs-error) | done | ~5 min |
| Handover doc (this file) | done | ~10 min |
| Commit + push + PR + merge | _(in progress)_ | — |
| `fly deploy` + live grep verification | _(in progress)_ | — |

Total: ~70 minutes of execution from kickoff to handover-pre-commit.
