# Changelog · dark-theme extension

Where the brief left a choice open, here's what we picked and why.

## Decisions

- **Two-file output** over single-file-with-media-query. Notion's SVG `<style>` handling is unreliable; we tested. Every diagram now ships as `<slug>.light.svg` + `<slug>.dark.svg`.
- **Theme suffix on token names** (`--canvas-bg-dark`). Token registry doubles but every legacy reference keeps working unchanged. Surface gradient *IDs* inside SVGs stay theme-agnostic (`surfaceSql`); only their stop values differ between files.
- **Always emit both.** Default `theme: both` for any ad-hoc diagram and any manifest without an explicit pin.
- **Mixed elevation strategy.** Light cards on dark canvas: 1px stroke at `rgba(255,255,255,0.08)`, drop shadow removed. Dark categorical cards on dark canvas: deeper drop shadow with `#000000` flood at 0.55 (the `#1a1a18` flood from the light filter is a no-op against `#1a1a1f` canvas).
- **Neutral mid-tone light surfaces** (`#252531`, `#2c2c38`, `#1f1f29`). No hue commitment; barely-cool tilt for indigo sympathy.
- **Renamed existing 9 SVGs** to `<name>.light.svg`. Asymmetric naming would rot.
- **Manifest theme is authoritative.** Per-diagram override is a hard error — a set is a coherent reader experience.
- **AAA-adjacent dark inks.** We picked `#7785d4` over `#6573c9` for primary indigo to clear AAA against the dark canvas.

## Files changed

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

## What we didn't do

- **Did not add a `<metadata>` "sibling pointer" inside the SVGs.** Open question A4 in `OPEN-QUESTIONS-answers.md`.
- **Did not add a brighter `tick-dark` animation keyframe.** The existing greens clear the contrast bar. Trivial to add if you want; open question A2.
- **Did not change WCAG conformance gating.** Aiming AAA-adjacent; not measuring formally.
