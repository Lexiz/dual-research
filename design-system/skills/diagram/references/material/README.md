# Material mode — under construction

This folder will hold the Material design system bundle, mirroring the structure of `references/pixel/`. As of the v2.0.0 P1 release, this folder is a stub; the actual content lands in phases P2–P3.

## Status

| Phase | Scope | Status |
|---|---|---|
| **P2** | `foundations.html` + `_shared.css` + anchor `system-context.material.{light,dark}.svg` | **not started** |
| **P3** | `components.html`, `connectors.html`, `icons.html` (78 icons hand-drawn in M3 style), `templates.html`, `examples.html` | not started |
| **P4** | Remaining 16 Material canonical SVGs + how-it-works regeneration | not started |
| **P5** | Cross-mode polish (this README replaced by a real overview) | not started |

## What goes here when complete

```
material/
├── foundations.html            ← Material 3 tokens: sable + sage palette, Roboto Flex/Serif, M3 surfaces, shape, motion
├── components.html             ← cards, chips, shapes, lanes, stages, groups, callouts — in M3 vocabulary
├── icons.html                  ← 78 icons hand-drawn in M3 stroke/density spec
├── connectors.html             ← arrow taxonomy, gutters, labels, crossings — Material accent colors
├── templates.html              ← per-template visual contracts in Material vocabulary
├── examples.html               ← canonical worked SVGs viewer
├── _shared.css                 ← styles for this reviewer site
└── examples/                   ← 18 canonical SVGs (9 templates × 2 themes)
    ├── <name>.material.light.svg  × 9
    └── <name>.material.dark.svg   × 9
```

## What the skill does today if you ask for Material mode

If a user invokes the `diagram` skill with `material light` / `material dark` / `material both` before P2 ships, SKILL.md Step 3 will attempt to load `material/foundations.html` and fail (file does not yet exist). The skill should surface this clearly: "Material mode is under construction; the reference bundle isn't ready yet. Want me to render this as Pixel instead?"

## Source spec for the Material design system

The Material mode is modeled on the dual-research V2 design system:

- Canonical text spec: `/Users/alexlisitzky/dual-research/design-system/SPEC.md`
- Visual reference: `/Users/alexlisitzky/dual-research/design-system/assets/Design System v2.html`
- Token source-of-truth CSS: `/Users/alexlisitzky/dual-research/design-system/assets/styles/tokens-and-primitives.css`

The Material mode adapts that system for diagram authoring (general-purpose architecture diagrams, not in-app UI). Where dual-research has no analog — most notably the 7 categorical surface gradients used for cards — Material derives them from the V2 palette tokens via documented `color-mix` recipes that live in `material/foundations.html` §01.2 once that file ships.
