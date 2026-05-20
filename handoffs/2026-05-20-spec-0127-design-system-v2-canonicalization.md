# Handover — spec 0127 · Design system v2 canonicalization (first of 5-spec migration arc)

- Date: 2026-05-20
- Spec: [`specs/0127-design-system-v2-canonicalization.md`](../specs/0127-design-system-v2-canonicalization.md)
- PR: https://github.com/Lexiz/dual-research/pull/145
- Merge commit: see `git log --oneline -5` after merge — this handover was written before the merge commit existed
- Deployed version: `1.6.5`

## Bottom line for the next session

Spec 0127 is **the first of a 5-spec arc** that completes the v1 → v2 design-system migration. This first spec is **docs + folder restructure only** — no live frontend behavior change. It promotes the v2 (Material 3) design system to single source of truth, archives the v1 spec, dissolves `docs/design-system-v2/`, and rewrites `design-system/SPEC.md` end-to-end as v2-canonical.

**The next four specs (0128 → 0131) carry the live frontend migration**, and they must ship in order. The next one is **spec 0128 — `run-detail.jsx` v2 token migration** (242 v1 token references → 0).

## The 5-spec arc — context the next session needs

The dual-research codebase had drifted into a state where two design systems coexisted:
- A v1 design system in `design-system/SPEC.md` (text spec, "snapshot of v0.69.12")
- A v2 design system in `docs/design-system-v2/` (a one-shot Material 3 briefing that seeded specs 0092–0104)

The live frontend (`src/dual_research/ui/static/`) ran on an **additive layering pattern** introduced by spec 0092: v1 tokens (`--bg-*`, `--fg-*`, `--border-*`, `--t-*`, IBM Plex) and v2 tokens (`--md-*`, Roboto Flex + Roboto Serif, Material Symbols) coexisted, with each component free to use either vocabulary. Result: 46% of token references in live code were on v1, 54% on v2, with no enforced end-state.

The user decided to fully consolidate onto v2 and remove v1. Five specs (0127–0131):

| Spec | Scope | V1 token refs removed | Risk | Status |
|---|---|---:|---|---|
| **0127** | Design-system folder canonicalization (docs + restructure only) | 0 | L | **✅ shipped (this spec)** |
| 0128 | `run-detail.jsx` v2 token migration | 242 | M | **next** |
| 0129 | `design-language.jsx` v2 rebuild | 142 | M | planned |
| 0130 | Remaining JSX (`app/errors/compare/auth/search/shared.jsx`) v2 migration | 172 | M | planned |
| 0131 | CSS finalization: v1 token block removal + IBM Plex font removal + `theme.css` legacy-class drain | 345 + theme.css | H | planned |

After 0131 lands: every `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)` / `var(--t-*)` reference will fail visibly, IBM Plex will be unloaded from `index.html`, and `design-system/SPEC.md § 12 Migration status` will be removed in that same PR.

**Token mapping (mechanical for ~90% of cases):**
- `--bg-0` → `--md-surface`
- `--bg-1` → `--md-surface-container-low`
- `--bg-2` → `--md-surface-container`
- `--bg-3` → `--md-surface-container-high`
- `--bg-4` → `--md-surface-container-highest`
- `--fg-0` → `--md-on-surface`
- `--fg-1` → `--md-on-surface-variant`
- `--fg-2` → `--md-on-surface-muted`
- `--fg-3` → `--md-on-surface-faint`
- `--fg-4` → `--md-on-surface-decor`
- `--border-1` → `--md-outline-hair`
- `--border-2` → `--md-outline-variant`
- `--border-3` → `--md-outline`
- `--r-2` → `--md-shape-sm` (8px)
- `--r-3` → `--md-shape-md` (12px)
- `var(--mono)` → typically stays; `--mono` is aliased to `--sans` and only used for font-family. Once v1 is removed in 0131, this resolves to whatever `--sans` was aliased to. For JSX inline styles, the safer move is to replace `var(--mono)` references with `var(--md-font-data)` (the M3 data font alias that includes `tabular-nums`).

Spec 0108 (run-list M3 migration, already shipped) is the **prior-art reference** for how a single-file token sweep PR looks — read it before opening spec 0128 to match the style + acceptance criteria.

## What shipped in 0127

- Version bump: PATCH (refactoring) → 1.6.5
- Files touched: 42 (8 renames + 21 screenshot moves + 13 edits/creates)
- Pyproject ↔ `__init__` version drift caught up in the same commit (pyproject was at 1.5.0, `__init__` at 1.6.4 — both now at 1.6.5)
- Test suite: 1194 / 1194 pytest passing

### Folder restructure
```
design-system/
├── SPEC.md                              ← REWRITTEN as v2-canonical
├── README.md                            ← rewritten, drops v1/v2 framing
├── PROMPT-FOR-CLAUDE-DESIGN.md          ← Roboto/M3 vocabulary; --md-* token examples
├── CHANGELOG.md                         ← new entry
├── assets/
│   ├── Design System v2.html            ← moved from docs/design-system-v2/
│   └── styles/
│       ├── tokens-and-primitives.css    ← renamed from v2-m3.css
│       └── composed-components.css      ← renamed from v2-m3-page.css
├── notion-issues/
│   ├── ISSUES.md                        ← moved + path comment updated
│   └── screenshots/  (21 PNGs)
├── audits/                              ← unchanged
├── skills/                              ← unchanged
└── _archive/
    ├── v1/
    │   ├── SPEC.md                      ← old v1 spec
    │   └── README.md                    ← "deprecated, see ../../SPEC.md"
    └── seeding/
        ├── V2-BRIEFING.md               ← old docs/design-system-v2/README.md
        ├── CLAUDE-CODE-PROMPT.md        ← prompt that landed v2
        └── README.md                    ← context note

docs/design-system-v2/                   ← DELETED entirely
```

### Stale-pointer fixes
- `src/dual_research/ui/static/tokens.css` (2 places), `base.css`, `theme.css` — comments that pointed at `docs/design-system-v2/assets/styles/v2-m3.css` now point at `design-system/assets/styles/tokens-and-primitives.css`. Mechanical doc fix; no behavior change.
- `design-system/notion-issues/ISSUES.md` — discrepancies section now points at `_archive/seeding/V2-BRIEFING.md` with a path-change note.

### Notably untouched (deferred to 0128–0131)
- Every `.jsx` file in `src/dual_research/ui/static/` (run-detail, design-language, app, errors, compare, auth, search, shared)
- The v1 token block in `tokens.css` (lines 1-164)
- IBM Plex `<link>` tags in `index.html`
- `theme.css` legacy classes (`.phase-step-line`, `.uppercase-label`, `.dr-ghost-block`, `.dr-section-brief-btn`, `.cap-bar`, `.bg-grid`)
- All specs 0050-0126 (historical record of the migration; references to old paths preserved)
- Diagram skill at `design-system/skills/diagram/` (cream + indigo palette stays as-is)

## State of main after this PR merges

- Branch `spec-0127-design-system-v2-canonicalization` deleted after merge
- `main` carries spec 0127 commit
- `pyproject.toml` + `src/dual_research/__init__.py` + `uv.lock` all read 1.6.5
- Live frontend behavior unchanged from pre-PR (only docs + comments + version labels changed)

## What the next session needs to read before opening spec 0128

1. **`handoffs/2026-05-20-spec-0127-design-system-v2-canonicalization.md`** (this file) — for context on the 5-spec arc.
2. **`design-system/SPEC.md`** — the canonical v2 spec. Specifically § 2 (Foundations) for the token vocabulary and § 12 (Migration status) for the planned 0128–0131 sequence.
3. **`specs/0127-design-system-v2-canonicalization.md`** — the spec that just shipped, especially § 10 (Follow-up specs).
4. **`specs/0108-run-list-m3-migration.md`** — prior-art reference for what a single-file token sweep spec looks like. Match its structure.
5. **`src/dual_research/ui/static/run-detail.jsx`** — the target file for spec 0128. ~6000 lines. The 242 v1 token references are spread across the file. Run `grep -nE 'var\(--(bg|fg|border|t)-' src/dual_research/ui/static/run-detail.jsx` to enumerate them.

## What to confirm with the user before executing spec 0128

The plan I drafted in spec 0127 for 0128 is high-level. Before opening a real `specs/0128-*.md` file, the next session should:

1. Re-read the run-detail.jsx file (it may have changed since spec 0127 — likely small but worth checking).
2. Spot-check ~10 v1 token references to confirm the mechanical mapping in the "Token mapping" table above still applies cleanly.
3. Look for edge cases: any `var(--bg-*)` reference that's inside a conditional / theme override / animation where the v2 mapping might behave differently in light mode.
4. If the spec needs adjustment (e.g., the file got smaller, the mapping has surprise cases, run-detail.jsx imports something that needs migration first), surface the adjustment to the user **before** opening the PR.

The user has explicitly asked for **"pause between specs"** — so after writing spec 0128, present it for review before executing.

## Open questions / known-unknowns

- **Diagram skill palette alignment** (deferred per spec 0127 decision). If the user later wants the diagram skill to match the sable+sage palette instead of cream+indigo, that's a separate spec — not 0128/0129/0130/0131.
- **Pyproject ↔ __init__ drift** — caught up in 0127. If new hotfixes land between 0127 and 0128 they should bump both files in lockstep going forward.
- **Spec-numbering gap.** If a hotfix lands between 0127 and 0128 it'll claim 0128, pushing the run-detail migration to 0129. The next session should `ls specs/` first to confirm the next free number.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_investigation | done | ~15 min |
| 2_plan | done | ~10 min |
| 3_spec_draft | done | ~10 min |
| 4_implement | done | ~25 min |
| 5_verify | done | ~5 min |
| 6_pr | done | ~3 min |
| 7_merge | pending | — |
| 8_deploy | pending | — |
| 9_handover | done | ~10 min |

## What I learned

1. **Two parallel design-system locations is a 100% predictable drift trap.** As soon as `docs/design-system-v2/` was added "temporarily" for the briefing round, both folders started claiming canonical status. The clean fix is to never let "v2" live in a different folder from "v1" — promote it in place from day one.
2. **Additive token layering postpones the hard problem.** Spec 0092's pattern (v1 + v2 tokens coexist; components opt in to v2 individually) shipped M3 without breakage, but it left the cleanup work to do later, with no enforced end-state. Specs 0128–0131 are the bill coming due. A useful default for future migrations: define the end-state spec **first**, then ship the additive layer **and** the deprecation timeline together.
3. **Version-bump drift is a quiet bug class.** `pyproject.toml` was at 1.5.0 while `__init__.py` was at 1.6.4 because hotfixes had only updated `__init__`. Catching it in 0127 was opportunistic; a CI check `grep '^version' pyproject.toml == grep __version__ src/dual_research/__init__.py` would prevent future drift.
4. **The "no live-frontend code change" boundary needs a single-character exemption for doc comments.** Spec 0127 said "no live-frontend code change," but the renamed CSS files broke source-of-truth pointer comments in tokens.css / base.css / theme.css. Updating those comments isn't a behavior change but it does touch live files. Acceptable in this case; worth being explicit about in future "no code change" specs.
