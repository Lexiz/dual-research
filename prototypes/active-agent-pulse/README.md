# Active-agent badge pulse — prototype

A pre-implementation experiment for **Spec 0138**. Five candidate animations
for signalling "this model is currently busy" on the Timeline agent badges.

## What's in this folder

| File | Purpose |
|---|---|
| `mockup.html` | Self-contained static HTML. Five animation variants (A–E) rendered against the real production Material 3 tokens, with dark/light + reduced-motion toggles. |
| `README.md` | This file. |

## How to view

```bash
open prototypes/active-agent-pulse/mockup.html
```

The page inlines a copy of the v1.7.x `--md-*` token block from
[tokens.css](../../src/dual_research/ui/static/tokens.css) and reproduces
the `.tl__head` / `.tl__tabs` / `.as.in-header` markup verbatim so the
badge proportions match what ships.

## The variants

| | Variant | Recipe |
|---|---|---|
| A | Soft halo pulse | Existing `pulse-a`/`pulse-b` dot-halo recipe (base.css:82-83) scaled to ring the whole badge. Lowest contrast. |
| B | Gradient sweep | An agent-tinted gradient sheen slides across the surface. **Chosen.** |
| C | Elevation breathing | `--md-elev-1` ↔ `--md-elev-3` with a 1px translateY. Pure shadow. |
| D | Border-tint glow | No motion — hairline border cycles to the agent hue. Best for reduced-motion. |
| E | Elevation + halo | Subtle lift plus an agent-tinted halo. |

## Decision

The user picked **Variant B (gradient sweep)** after seeing all five side
by side. Spec 0138 §5.1 carries the CSS to land. The other variants stay
in this prototype as historical context — useful if the gradient ever
reads as too busy in production and we need to fall back.
