# Handover — spec 0134 · JSX fontWeight bypass cleanup

- Date: 2026-05-20
- Spec: [`specs/0134-fontweight-token-fixes.md`](../specs/0134-fontweight-token-fixes.md)
- PR: _(filled by `gh pr create` below)_
- Deployed version: `1.6.11` _(filled after `fly deploy`)_

## Bottom line for the next session

The user observed that after the 0127→0131 v1→v2 migration arc closed, no pixels moved on the live site. They reasonably suspected the components weren't actually wired to the new design system. A live computed-style audit confirmed the migration IS correctly wired — `:root` exposes `--md-*` tokens, `body` background reads `--md-surface`, header borders read `--md-outline-hair`, etc. The pixel-level continuity is explained by intentional design: 13 of 16 v1↔M3 token values are byte-identical (the migration was vocabulary cleanup, not visual redesign).

BUT — the audit also caught a real bypass. **33 JSX call sites hardcode `fontWeight: NNN`** instead of reading `var(--md-w-*)`. The hardcoded numbers happen to match the M3 token values, so visuals are unchanged today. But these 33 elements are NOT subscribed to the design system. Spec 0134 fixes that.

Same shape as the v1-token consumption gap the 0127→0131 arc closed in CSS — just hidden in JSX inline-style props.

## What shipped in 0134

- **Version bump:** PATCH → **1.6.11**
- **Cache-bust:** `?v=0132a` → `?v=0133a` on every `<link>` / `<script>` in `index.html` (25 occurrences)
- **Files touched:** 13 (8 JSX + CHANGELOG + 3 version-bump + index.html)
- **Net change:** +87 / -78 (mostly format-neutral: replacing `600` with `'var(--md-w-semi)'` adds characters per occurrence)
- **Test suite:** 1194 / 1194 pytest passing
- **Live verification:** preview server confirmed RUN ID column header (was `fontWeight: 600` literal) now resolves to `font-weight: 600` through `var(--md-w-semi)`. Same value, different binding.

### Per-file scope (33 fontWeight sites + 2 rgba)

| File | 600 → `--md-w-semi` | 500 → `--md-w-medium` | 700 → `--md-w-bold` | Total |
|---|---:|---:|---:|---:|
| `app.jsx` | 1 | 0 | 0 | 1 |
| `auth.jsx` | 2 | 1 | 0 | 3 + 2 rgba |
| `design-language.jsx` | 0 | 3 | 0 | 3 |
| `errors.jsx` | 1 | 2 | 0 | 3 |
| `run-list.jsx` | 3 | 0 | 0 | 3 |
| `run-detail.jsx` | 11 | 4 | 2 | 17 (incl. `current ? 700 : 600` ternary) |
| `settings.jsx` | 2 | 0 | 0 | 2 |
| `shared.jsx` | 1 | 0 | 0 | 1 |
| **Total** | **21** | **10** | **2** | **33 + 2 rgba** |

### auth.jsx rgba decoration cleanup

| Line | Before | After |
|---|---|---|
| 163 | `rgba(124, 196, 184, 0.06)` (sage / agent-b raw) | `color-mix(in srgb, var(--md-secondary) 6%, transparent)` |
| 163 | `rgba(212, 165, 116, 0.06)` (sable / agent-a raw) | `color-mix(in srgb, var(--md-primary) 6%, transparent)` |
| 208 | `rgba(124, 196, 184, 0.06)` (duplicate of :163 sage) | covered by the replace_all on :163 |
| 182 | `rgba(0,0,0,0.10)` (button box-shadow) | **kept as-is** — matches the shadow-recipe pattern in `--md-elev-*` (raw rgba inside box-shadow declarations is on-pattern for this codebase) |

### Acceptance grep (pre-commit, on local clone)

```
$ grep -rnE "fontWeight:\s*[0-9]+\b" src/dual_research/ui/static/*.jsx | grep -v "var("   → 0
$ grep -rnE "fontWeight:\s*['\"][0-9]+['\"]" src/dual_research/ui/static/*.jsx           → 0
$ grep -nE 'rgba\(124, 196, 184' src/dual_research/ui/static/auth.jsx                    → 0
$ grep -nE 'rgba\(212, 165, 116' src/dual_research/ui/static/auth.jsx                    → 0
```

### Why this isn't visible

Every replaced site went from a hardcoded `400`/`500`/`600`/`700` to a token reference that resolves to the **same** number. The CSSOM produces identical computed `font-weight` values pre- and post-sweep. The user's mental model "if I change the design system, I should see something move" is correct — but **the design system wasn't changed in this spec**, only the wiring of components to it.

The value of this spec is **structural integrity**, not visual movement:

- Before: 33 elements ignore the design system; their weight is hardcoded.
- After: 33 elements read from the design system. If `--md-w-semi` is ever set to 650 (or `--md-w-medium` to 450), all 33 elements move with the rest of the system. Today they wouldn't have.

The proof this matters lives in two places:
1. **Computed-style verification** at runtime — every previously-hardcoded element now resolves its font-weight through `getPropertyValue('--md-w-*')`, not a literal.
2. **The next time the design system changes** — when (not if) someone decides to ship a real visual redesign, these 33 sites will move with it. They wouldn't have before this spec.

## Audit findings that this spec deliberately does NOT touch

The same audit (run as a sub-agent) also surfaced lower-impact bypass patterns that are out of scope here:

- **~280 hardcoded pixel values in CSS** (font-size, padding, etc.). Some are deliberate micro-scale tweaks (10.5 px, 11.5 px) that don't fit the M3 type roles cleanly. Most should not be tokenized without a deliberate "do we accept M3 sizes or keep our microscale?" decision. Separate decision; defer.
- **Legacy `.chip` / `.btn` / `.card` class usage** vs `.md-chip` / `.md-btn` / `.md-card` (5.8:1 ratio). The legacy primitives have been internally migrated to consume M3 tokens (per spec 0131), so they ARE subscribed to the system — they just use a different class API. This is a visual-dialect split, not a bypass. No fix needed.
- **3 hex color literals in `components.css`** (`#ffffff` knockout-white letter, `#faf9f6` + `#04060a` light-mode frame, `#04060a` fill). Edge cases; minimal impact. Could token-ize as a follow-up.
- **5 `IBM Plex` references** in auth.jsx SVG text + design documentation. The SVG falls back to `system-ui`; the design docs are intentional historical reference. Not a bypass.

## Open follow-ups

1. **Spec 0133 (run-detail header rework)** — sitting as `status: proposed`, 513 lines. If you actually want to see pixels move, this is the kind of spec that does that.
2. **Spacing vocab consolidation** — `--s-*` (119 refs) ↔ `--md-sp-*` (23 refs). Same shape as 0132's weight consolidation, larger surface. Probably the right next post-arc cleanup.
3. **CSS font-size fragmentation review** — 280-ish hardcoded pixel values. Decide: M3 roles enforce, or keep microscale? Belongs in a deliberate scope discussion.

## Risk reflection

- **The `current ? 700 : 600` ternary at `run-detail.jsx:3079`** (phase-header band) was the one non-mechanical edit. Manually rewrote to `current ? 'var(--md-w-bold)' : 'var(--md-w-semi)'`. Visually identical at the affected element.
- **`auth.jsx:182` button box-shadow** — left as raw `rgba(0,0,0,0.10)`. Tokenizing would have meant either inventing a new shadow token or using `--md-elev-1` (visually slightly different). Punted on the design call.
- **No JSX behavior changes.** Every edit was an inline-style value swap; no markup, no event handlers, no logic touched. pytest 1194/1194 passes (which mostly covers backend, not JSX).

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| Audit (sub-agent) + v1↔M3 hex comparison + diagnosis | done | ~10 min |
| Spec draft (0134) | done | ~5 min |
| Per-file replace_all (8 files, ~7 edits per file × 5 weight patterns) | done | ~8 min |
| auth.jsx rgba sweep | done | ~2 min |
| Version bump + cache-bust + CHANGELOG | done | ~3 min |
| pytest + acceptance greps | done | ~2 min |
| Preview verification (computed-style trace) | done | ~3 min |
| Handover (this file) | done | ~7 min |
| Commit + push + PR + merge | _(next)_ | — |
| `fly deploy` + live verification | _(next)_ | — |

Total: ~40 minutes from audit kickoff to handover-pre-commit.
