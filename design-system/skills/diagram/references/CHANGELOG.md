# Changelog · diagram skill

## v2.0.1 — Material rebuilt natively, fully self-contained skill

The Material design system is rewritten as a first-class peer of Pixel: it owns its own M3 design tokens (`material/_tokens.css`), composes from M3 primitive classes verbatim, and pulls Material Symbols Outlined as its icon library. The skill directory is now fully autonomous — both modes are complete, parallel, copy-anywhere bundles with zero external dependencies beyond the Google Fonts CDN for doc-site rendering.

### What changed
- **Material design tokens are now first-party.** `material/_tokens.css` owns the M3 color roles, surface tiers, 15-role type scale, spacing, shape, elevation, motion, plus the M3 primitive classes (`.md-card`, `.md-chip`, `.md-status`, `.md-btn`, `.md-tabs`, `.md-seg`, `.md-list`) that the generator composes. Paired with `_shared.css` (doc-site chrome + diagram-specific extensions). Both files live in `material/`.
- **Material reference pages** (`foundations.html`, `components.html`, `connectors.html`, `icons.html`, `templates.html`, `examples.html`) are rewritten using the M3 primitive vocabulary throughout. Each page loads `_tokens.css` first and `_shared.css` second.
- **8 service-card extensions** (`md-card--service-{primary,secondary,sql,secure,store,cache,slate,neutral}`) are defined in `material/_shared.css` as `color-mix` tints over `--md-surface-container`. This replaces the dark-saturated categorical surfaces from the v2.0.0 mechanical transform with a "calm dense observability" look at low saturation.
- **Material Symbols Outlined** replaces the 78 hand-drawn icons. Reference pages load the Google Fonts CDN; canonical SVGs pre-convert glyphs to inline `<path>` data so output stays self-contained. `icons.html` catalogs ~80 glyphs across 9 categories plus a monogram fallback host.
- **System-context anchor pair** (`system-context.material.{light,dark}.svg`) is hand-rebuilt from scratch in M3 vocabulary as the canonical Material reference. The other 8 canonical Material example SVGs remain mechanical transforms from their Pixel counterparts and are flagged with a "pending hand-rebuild" callout in `material/examples.html` — a future release rebuilds the rest using the §06.1 anchor as the pattern.
- **Skill directory is now fully self-contained.** Removed: the vendored upstream reference at `references/app-v2/` (development scaffolding from the rewrite phase; design tokens now owned by `material/`). Both Pixel and Material modes are independent, complete, copy-anywhere bundles.
- **Reader-facing surfaces cleaned.** Internal project names, internal spec numbers, personal file paths, and historical planning artifacts removed from `SKILL.md`, `README.md`, `index.html`, `manifest.html`, `gallery.html`, `troubleshooting.md`, and the Material foundations. `gallery.html` collapses to two tabs — Pixel and Material side-by-side.
- **CHANGELOG and README rewritten** to match shipped state.

### What didn't change
- **Pixel mode** — all files unchanged. Same SKILL.md routing, same 18 canonical SVGs, same reference pages.
- **Mode + theme detection** — same SKILL.md Step 1 logic (`pixel` is the default; `material light` / `material dark` / `material both` opts in).
- **Filename convention** — `<slug>.<mode>.{light,dark}.svg` unchanged.
- **Manifest schema** — `mode:` and `theme:` pins unchanged.

---

## v2.0.0 — mode-aware split + Material mode

The skill becomes mode-aware: the existing cream + indigo design system is preserved verbatim as **Pixel** mode (the default), and a second design system — **Material**, a Material 3 sibling — is added alongside as an opt-in mode. Both modes ship light + dark variants. Mode is part of the output filename so both versions of a diagram coexist without collision.

### What changed
- **`SKILL.md` frontmatter** — added `version: 2.0.0`. Description rewritten to name both modes and the mode-aware trigger surface. Workflow Step 1 detects mode (`pixel` / `material`, default `pixel`); Steps 3 and 5 route to `references/<mode>/...`; Step 7 emits `<slug>.<mode>.{light,dark}.svg`.
- **Destination convention inlined.** SKILL.md previously punted the save-path question to an external doc. Convention is now self-contained: save to `diagrams/<slug>.<mode>.{light,dark}.svg` adjacent to the document referencing them; if no anchoring document exists, ask the user.
- **`references/` reorganized into mode subfolders.** Mode-specific pages moved into `references/pixel/`: `foundations.html`, `components.html`, `connectors.html`, `icons.html`, `templates.html`, `examples.html`, `_shared.css`. Mode-agnostic content stays at root: `README.md`, `CHANGELOG.md`, `troubleshooting.md`, `index.html`, `manifest.html`, `templates/<name>.md`.
- **Renamed 18 canonical Pixel SVGs.** `<slug>.{light,dark}.svg` → `<slug>.pixel.{light,dark}.svg`. Clean break — no backward-compatibility symlinks. Any external document linking to the old filenames will 404 and need a one-character path update.
- **`references/material/` added.** Mirrors `pixel/` structure with foundations / components / connectors / icons / templates / examples / `_shared.css` and 18 canonical example SVGs.
- **Manifest gains `mode:` field.** Defaults to `pixel`. Pinned per-set; per-diagram override is a hard error (same rule as the existing `theme:` pin). New §07.5 "Mode pinning" mirrors §07.4 "Theme pinning".
- **README rewrite.** First 30 lines answer in order: what is this skill, what does it produce, when to invoke, input contract, output contract. Two-mode story up front. Folder map reflects the new structure.
- **`index.html` reframed.** v2.0.0 hero; sidebar nav points the per-mode pages into `pixel/`; identity panels for both modes side-by-side.
- **Footer text refreshed** across all reference pages: `v2.0.0 · mode-aware · pixel + material · light + dark`.
- **`troubleshooting.md` extended** with three cross-mode entries (mode mixing in a set, wrong mode for purpose, token-name confusion).

---

## v1.1 — dark-theme extension

Where the brief left a choice open, here's what we picked and why.

### Decisions
- **Two-file output** over single-file-with-media-query. Notion's SVG `<style>` handling is unreliable. Every diagram ships as `<slug>.light.svg` + `<slug>.dark.svg`. *(v2.0.0 note: filename convention is now `<slug>.<mode>.{light,dark}.svg`.)*
- **Theme suffix on token names** (`--canvas-bg-dark`). Token registry doubles but every legacy reference keeps working unchanged. Surface gradient *IDs* inside SVGs stay theme-agnostic (`surfaceSql`); only their stop values differ between files.
- **Always emit both.** Default `theme: both` for any ad-hoc diagram and any manifest without an explicit pin.
- **Mixed elevation strategy.** Light cards on dark canvas: 1px stroke at `rgba(255,255,255,0.08)`, drop shadow removed. Dark categorical cards on dark canvas: deeper drop shadow with `#000000` flood at 0.55 (the `#1a1a18` flood from the light filter is a no-op against `#1a1a1f` canvas).
- **Neutral mid-tone light surfaces** (`#252531`, `#2c2c38`, `#1f1f29`). No hue commitment; barely-cool tilt for indigo sympathy.
- **Renamed existing 9 SVGs** to `<name>.light.svg`. Asymmetric naming would rot. *(v2.0.0: renamed again to `<name>.pixel.light.svg` for the same reason — symmetric naming across modes.)*
- **Manifest theme is authoritative.** Per-diagram override is a hard error — a set is a coherent reader experience.
- **AAA-adjacent dark inks.** We picked `#7785d4` over `#6573c9` for primary indigo to clear AAA against the dark canvas.

### Files changed
| File | What |
|---|---|
| `foundations.html` | Added §01.0 "Theme model" + dark column / dark variant for every token (canvas, palette, surfaces, inks, shadows, rules, status). Side-by-side light/dark previews. |
| `components.html` | Every primitive section now has a paired light + dark preview block. Notes inline where dark differs structurally (light cards lose drop shadow → stroke). |
| `connectors.html` | Arrow stroke colors and marker fills documented for both themes. Callout chip fills get dark equivalents. Geometry unchanged. |
| `icons.html` | Re-stated as a 2×2 matrix: (icon variant) × (theme). Cell pairs that end up visually identical are marked. |
| `templates.html` | Each template gains a "Dark-theme variant" note (mostly "swap tokens"). |
| `manifest.html` | Added `theme:` field + worked `theme: both` example. |
| `examples/<name>.svg` × 9 | Renamed to `.light.svg`. |
| `examples/<name>.dark.svg` × 9 | **New.** Same layout, dark tokens. |
| `_shared.css` | Added `.frame.dark` and `.pair` for side-by-side previews. |
| `SKILL.md` | Steps 3, 5, 6, 7 updated. Output rules rewritten. "What this produces" now says two files. |
| `troubleshooting.md` | Four new dark-theme entries (cream leakage, invisible elevation, indigo legibility, light/dark drift). |
| `README.md` | One paragraph added about dual-output. |

### What we didn't do
- **Did not add a `<metadata>` "sibling pointer" inside the SVGs.** Bytes vs. value tradeoff; the filename pair is enough.
- **Did not add a brighter `tick-dark` animation keyframe.** The existing greens clear the contrast bar.
- **Did not change WCAG conformance gating.** Aiming AAA-adjacent; not measuring formally.
