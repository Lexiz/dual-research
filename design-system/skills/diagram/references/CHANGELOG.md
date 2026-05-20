# Changelog · diagram skill

## v2.0.0 — mode-aware split + Material mode (in progress)

The skill becomes mode-aware: the existing cream + indigo design system is preserved verbatim as **Pixel** mode (the default), and a second design system — **Material**, modeled on the dual-research Material 3 dashboard — is being added alongside as an opt-in mode. Both modes ship light + dark variants. Mode is part of the output filename so both versions of a diagram coexist without collision.

### Phase 1 — Pixel cleanup + mode scaffold (this release)

Files-only; no Material content yet.

- **`SKILL.md` frontmatter** — added `version: 2.0.0` field. Description rewritten to name both modes and the mode-aware trigger surface.
- **Workflow becomes mode-aware.** Step 1 detects mode (`pixel` / `material`, default `pixel`). Steps 3 and 5 route to `references/<mode>/...` for foundations / components / connectors / icons / templates / examples. Step 7 emits `<slug>.<mode>.{light,dark}.svg`.
- **Destination convention inlined.** SKILL.md previously punted the save-path question to an external `design-doc/references/open-questions.md` Q12 (a reference to a different repo). Convention is now self-contained in the skill: save to `diagrams/<slug>.<mode>.{light,dark}.svg` adjacent to the document referencing them; if no anchoring document exists, ask the user.
- **Reorganized `references/` into mode subfolders.** All mode-specific pages moved into `references/pixel/`: `foundations.html`, `components.html`, `connectors.html`, `icons.html`, `templates.html`, `examples.html`, `_shared.css`. Mode-agnostic content stays at root: `README.md`, `CHANGELOG.md`, `troubleshooting.md`, `OPEN-QUESTIONS-answers.md`, `index.html`, `manifest.html`, `templates/<name>.md`.
- **Renamed 18 canonical Pixel SVGs.** `<slug>.{light,dark}.svg` → `<slug>.pixel.{light,dark}.svg`. **Clean break — no backward-compatibility symlinks.** Any external document linking to the old filenames will 404 and need a one-character path update.
- **`references/material/` stub** — placeholder for the Material design system; full content lands in Phase 2 (foundations + anchor SVG) and Phase 3 (rest of the reference pages).
- **Manifest gains `mode:` field.** Defaults to `pixel`. Pinned per-set; per-diagram override is a hard error (same rule as the existing `theme:` pin). New §07.5 "Mode pinning" in `manifest.html` mirrors §07.4 "Theme pinning". Schema and pin table updated.
- **README rewrite.** First 30 lines now answer in order: what is this skill, what does it produce, when to invoke, input contract, output contract. Two-mode story up front. Folder map reflects the new structure.
- **`index.html` reframed.** v2.0.0 hero; sidebar nav points the per-mode pages into `pixel/` (default mode); warn callout flags that the showcase below documents Pixel and Material's parallel showcase is deferred to P5.
- **Footer text refreshed** across all reference pages: `v2.0.0 · mode-aware · pixel + material · light + dark`.

### Phases 2–6 (forthcoming)

- **P2** — Material `foundations.html` + `_shared.css` + anchor `system-context.material.{light,dark}.svg`.
- **P3** — Material `components.html`, `connectors.html`, `icons.html` (78 icons hand-drawn in M3 style), `templates.html`.
- **P4** — Remaining 16 Material canonical SVGs + regeneration of the 14 `dual-research/diagrams/` how-it-works SVGs in Material mode + `how-it-works.jsx` wiring.
- **P5** — Cross-mode wiring: README polish, troubleshooting cross-mode entries, `index.html` Material showcase, final manifest doc.
- **P6** — Sync personal copy ↔ `dual-research/design-system/skills/diagram/`; close `dual-research/design-system/SPEC.md` § 13 open item (alignment with dual-research palette shipped as the Material mode).

---

## v1.1 — dark-theme extension

Where the brief left a choice open, here's what we picked and why.

### Decisions

- **Two-file output** over single-file-with-media-query. Notion's SVG `<style>` handling is unreliable; we tested. Every diagram ships as `<slug>.light.svg` + `<slug>.dark.svg`. *(v2.0.0 note: filename convention is now `<slug>.<mode>.{light,dark}.svg`.)*
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
| `OPEN-QUESTIONS-answers.md` | **New.** Our answers to all 11 questions. |
| `README.md` | One paragraph added about dual-output. |

### What we didn't do

- **Did not add a `<metadata>` "sibling pointer" inside the SVGs.** Open question A4 in `OPEN-QUESTIONS-answers.md`.
- **Did not add a brighter `tick-dark` animation keyframe.** The existing greens clear the contrast bar. Trivial to add if you want; open question A2.
- **Did not change WCAG conformance gating.** Aiming AAA-adjacent; not measuring formally.
