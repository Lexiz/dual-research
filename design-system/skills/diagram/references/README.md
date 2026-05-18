# architecture-diagram · design system v1.1 (dual-theme extension)

A complete, locked visual specification for the `architecture-diagram` Claude Code skill. **v1.1 adds a full dark-theme token registry alongside the v1 cream palette.** Every diagram now ships as a pair: `<slug>.light.svg` + `<slug>.dark.svg`.

For the dark-theme extension specifically:
- `OPEN-QUESTIONS-answers.md` — decisions for the 11 questions in the briefing, with reasoning.
- `CHANGELOG.md` — what changed in v1.1, file-by-file.
- `foundations.html` §01.0 “Theme model” — the contract for dual-theme tokens (same names + `-dark` suffix; gradient and filter IDs stable across themes).
- `examples/*.{light,dark}.svg` — 18 canonical anchor files (9 templates × 2 themes).
- `SKILL.md` Steps 3, 5, 6, 7 — the dual-output workflow.
- `troubleshooting.md` — 5 new entries for dark-theme failure modes.

This bundle is the source of truth for the visual side of the skill. Read it top-to-bottom and apply verbatim. Nothing in here is a suggestion.

---

## What this is

A drop-in replacement for the visual side of the `architecture-diagram` skill. It defines — by closed registries and named primitives — every visual decision the skill is allowed to make. A downstream generator that follows this spec produces diagrams that look like siblings across a proposal, not strangers.

The brief was to fix nine specific failure modes visible in current output (icons crashing through titles, labels rotated 90°, arrows passing through unrelated cards, unexplained dashed borders, inconsistent dim-state treatments, floating labels, parallel arrow bunching, viewBox-width overflow, ad-hoc routing). Each is addressed below by a named primitive or rule the generator references instead of inventing.

---

## How to use this bundle

You have two ways to consume it:

1. **For humans reviewing the system** — open `index.html` in a browser. Top-to-bottom navigation in the left sidebar covers everything: foundations → components → icons → connectors → templates → examples → set manifest. Each page has rendered SVG specimens so the spec is visible, not just described.

2. **For the skill generating diagrams** — feed this entire folder into the skill's context (or commit it into `architecture-diagram/`). The skill should:
   - Read `index.html` (overview) and `foundations.html` first to load token vocabulary
   - Reference `components.html`, `icons.html`, `connectors.html` whenever generating
   - Use the per-template contracts in `templates.html` to drive each diagram type
   - Use `examples/*.svg` as anchor files for what correct output looks like
   - Maintain a `diagram-set-manifest.yaml` (schema in `manifest.html`) across any multi-diagram proposal

The HTML site is the reviewer; the source-of-truth for the downstream generator is the cumulative spec captured across all eight pages. Treat any rendered SVG primitive on a page as a copy-pasteable fragment — they're built from the same locked tokens.

---

## Folder map

```
references/
├── README.md                       ← you are here
├── index.html                      ← entry · overview · deliverables map
├── foundations.html                ← D1 · color (light + dark), type, spacing, shadow, animation tokens
├── components.html                 ← D2 · cards, chips, shapes, lanes, stages, groups, callouts (paired light/dark notes)
├── icons.html                      ← D3 · 78 icons × theme matrix + monogram fallback
├── connectors.html                 ← D4 · arrow taxonomy, gutters, labels, crossings, density caps (+ theme behavior table)
├── templates.html                  ← D5 · per-template visual contracts + dark-variant notes (all 9 filled)
├── examples.html                   ← D6 · canonical worked SVGs viewer (9 paired galleries)
├── manifest.html                   ← cross-diagram consistency mechanism + theme pinning (§07.4)
├── troubleshooting.md              ← common failure modes (incl. 5 dark-theme entries)
├── CHANGELOG.md                    ← v1.1 dual-theme extension changelog
├── OPEN-QUESTIONS-answers.md       ← decisions + reasoning for the 11 brief questions
├── _shared.css                     ← styles for the reviewer site (with .pair, .frame.dark, .theme-banner)
├── templates/                      ← per-template input contracts (theme-agnostic)
│   └── <name>.md  × 9
└── examples/                       ← 18 canonical SVGs (9 templates × 2 themes)
    ├── <name>.light.svg  × 9       ← cream canvas, v1 palette
    └── <name>.dark.svg   × 9       ← near-black canvas, lifted surfaces
```

---

## What's locked (do not change)

These are the load-bearing brand surfaces. Every diagram inherits them.

| Token | Value | Why locked |
|---|---|---|
| `--canvas-width` | **1660** | Visual rhythm across diagrams. Wide variant `2200` exists only for explicit landscape three-column overviews. |
| `--canvas-bg` / `--canvas-bg-dark` | `#f5f1ea → #ece8e0` (light) · `#1a1a1f → #14141a` (dark) | Identity. Every diagram emits in both themes. |
| `--font-family` | `Inter, system-ui, ...` | Identity. Theme-agnostic. |
| `--indigo` / `--indigo-dark` | `#4f5fb8` (light) · `#7785d4` (dark, AAA-adjacent) | Primary accent. The only color that crosses every template. |
| Output format | **Two** self-contained SVGs per diagram — `<slug>.light.svg` + `<slug>.dark.svg`, no external assets, all gradients/filters/keyframes inline | Notion embedability + theme parity. |
| Animation cap | **Max 3 animation classes per diagram** | Calm aesthetic — see `foundations.html` §01.6. Theme-portable. |

---

## The six deliverables, at a glance

### D1 · Foundations (`foundations.html`)
Locked registries for everything: canvas, semantic color palette (8 surface gradients incl. new `--surface-cache` and `--surface-deferred`), typography roles, 14 spacing tokens (`--gap-card`, `--lane-gutter`, `--label-clearance`, etc.), shadow registry (2 entries), and animation registry (5 keyframes + 7 classes). 

**Use it when:** any spatial or stylistic decision needs a value — never invent a hex, font-size, or pixel offset.

### D2 · Components (`components.html`)
A closed library of slotted primitives:
- **Cards** — 7 variants: `card.primary` / `card.secondary` / `card.reference` / `card.compact` / `card.deferred` / `card.highlight` (+ optional icon, status, footer slots)
- **Chips** — `chip.status` (5 states) · `chip.count` · `chip.version` · `chip.label`
- **Shapes** — `node.circle` · `node.pill` · `node.diamond` · `node.hexagon` · `node.star` · `node.note` (6 shapes for non-card nodes — events, decisions, mesh nodes, highlights, annotations)
- **Stages** — `stage.numbered-token` · `stage.divider`
- **Lanes** — `lane.header` · `lane.vertical` · `lane.activation-box`
- **Groups** — `group.boundary` · `group.label`
- **Callouts** — `callout.note` · `legend.chip`

**Use it when:** drawing any structural element. If a primitive isn't in this list, the generator does not invent one — it picks the closest match, or uses the documented fallback.

### D3 · Icons (`icons.html`)
**78 icons** in 9 categories drawn to one density spec (32 × 32 bounding box, filled silhouettes, consistent radii), each with explicit light-card and dark-card variants:

| Category | Count | Examples |
|---|---|---|
| Compute | 10 | service, container, function, worker, scheduled, agent, model, browser, mobile, terminal |
| Compute · extended | 5 | vm, k8s, edge, batch, gpu |
| Data | 9 | sql, nosql, cache, queue, stream, bucket, fs, search, vector |
| Data · extended | 5 | warehouse, lake, etl, ml, timeseries |
| Network | 6 | lb, cdn, gateway, vpc, firewall, dns |
| Network · extended | 5 | proxy, mesh, ingress, tunnel, nat |
| Security | 5 | lock, key, cert, oauth, vault |
| Security · extended | 4 | rbac, signing, audit, mfa |
| Observability | 5 | metrics, logs, trace, alert, dashboard |
| Observability · extended | 3 | health, slo, error |
| People | 3 | user, admin, analyst |
| External / generic | 4 | external, api-external, connector, generic-service |
| Workflow | 6 | start, end, branch, timer, signal, manual |
| Integration | 5 | webhook, websocket, graphql, grpc, polling |
| Domain | 5 | payment, email, notification, calendar, media |

Plus the **fallback rule**: when no icon matches, use `icon.generic-service` — a monogram tile (first letter or first two initials of the service name) in the service's canonical surface color. Never invent a new bespoke shape.

### D4 · Connectors (`connectors.html`) — the highest-value page
The biggest source of visible failures today. Fixed in spec:

- **Arrow taxonomy (8 types)** — `solid-primary` · `dashed-handoff` · `mirror-secondary` · `sync-call` · `return` · `async-event` · `bidirectional` · `error-path`
- **Marker registry** — 7 named arrowhead markers with exact dimensions
- **Curve rules** — L (straight) / Q (single bend) / C (S-curve); `--bend-radius` 24, `--max-bend-angle` 60°; no right-angle elbows
- **Lane & gutter system** — `--lane-gutter` 16 between parallel arrows; collapse to a single trunk + `chip.count` when > 3 parallel
- **Label placement** — three zones (A: above-line caps, B: below-line italic, C: on-line pill on curves); **no rotated labels, ever**; every label is bound to a specific line
- **Crossing rules** — secondary jogs over primary; shorter jogs over longer; 6px arc; max 3 crossings per diagram
- **Clearance** — `--arrow-clearance` 16 from any unrelated card; `--arrow-stub` 8 from card edge
- **Density caps** — 6 arrows per card; 3 parallel per pair; 18 cards per diagram; 4 arrow types; 5 surface gradients

The "no rotated labels" rule alone eliminates two of the screenshot's most visible failures.

### D5 · Templates (`templates.html`)
A visual contract per template — five fields: components used, icons used, layout rules, arrow types, anti-patterns. **All nine templates are filled** (v1.1): `layered-architecture`, `pipeline-flow`, `sequence`, `system-context`, `data-schema`, `infrastructure`, `event-flow`, `connector-map`, `freeform`. Each has a dark-variant note (mostly "swap surface tokens, no layout change").

The `freeform` template is the catch-all — when no other template fits, decompose the request into nouns → cards, verbs → arrows, groupings → boundaries, ordering → stages or lanes.

### D6 · Worked canonical examples (`examples.html`)
**Eighteen** end-to-end SVGs — nine templates × two themes — of the same proposal ("Partner Vetting") built only from the new system:

- `examples/<name>.light.svg` × 9 — cream canvas, v1 palette
- `examples/<name>.dark.svg`  × 9 — near-black canvas, lifted surfaces, AAA-adjacent indigo

Open a `.light.svg` next to its `.dark.svg` sibling and they read as the same diagram on different backgrounds — same layout, same arrows, same icons, same labels, only colors swap. The pairs are the anchors a fresh generation should match.

### Cross-diagram consistency · the set manifest (`manifest.html`)
A small YAML file authored on the first diagram of a proposal that pins:
- service → label
- service → surface gradient
- service → icon
- group → boundary color
- animations used (running tally vs the 3-class cap)
- third-party long tail (monogram + tile color per integration)

Every later diagram in the set reads this manifest before generating. The example for the Partner Vetting set is on `manifest.html` §07.2.

---

## How a diagram gets generated, end-to-end

When the skill is asked to produce a diagram, the workflow is:

1. **Load foundations** — read `foundations.html`. Start with §01.0 "Theme model" (the dual-theme contract), then the locked tokens. Apply verbatim.
2. **Pick template** — read the matching contract in `templates.html`. If user request doesn't match any of the nine named templates cleanly, use `freeform` with its decomposition procedure.
3. **Consult the set manifest** — if this is not the first diagram in the set, read the existing `diagram-set-manifest.yaml`. Use pinned service → label / surface / icon mappings; honor the `theme:` field (`light` / `dark` / `both`, default `both`).
4. **Compose from the library** — every card is a named variant from `components.html`. Every icon is from `icons.html` (or `icon.generic-service` fallback). Every shape is a `node.*` primitive.
5. **Apply the connector contract** — every arrow has a taxonomy name; every label sits in a legal zone; every parallel run respects gutters; every crossing follows the jog priority. Check against the contract checklist on `connectors.html` §04.8.
6. **Animate sparingly** — at most 3 animation classes per diagram, from the registry. If a fourth feels needed, drop one or split the diagram.
7. **Theme pass** — render once with light tokens, once with dark tokens, producing `<slug>.light.svg` + `<slug>.dark.svg`. The two files share structure; only color values, shadow filter bodies, and canvas gradient stops differ.
8. **Self-check both renders** against the canonical example pair for the template (`examples/<name>.{light,dark}.svg`). Apply the standard checks (arrow routing, label clearance, height locking, icon alignment) to each PNG plus the five dark-specific checks (cream leakage, invisible elevation, indigo legibility, text contrast, layout parity). Iterate against the *worse* variant.
9. **Update the manifest** — if new services were drawn, append them so the next diagram in the set inherits.

---

## The failure modes this system prevents

For each historically observed failure mode, the prevention now lives in a specific spec section:

| Original failure | Prevented by |
|---|---|
| Icons crash through card titles | `card` anatomy — reserved icon slot (top-left, 36×36 with 20/20 inset) — `components.html` §02.1 |
| Connector labels rotated vertically | Zone A/B/C rule, no rotation ever — `connectors.html` §04.5 |
| Floating labels with no anchor | Every connector label bound to a line; orphan labels become `chip.label` on a card — §04.5b |
| Inconsistent "deferred" treatment | `card.deferred` is the single canonical look — `components.html` §02.2 |
| Floating chip row with no flow | Chips never freestanding — adjacency rule — `components.html` §02.3 |
| Unexplained highlight border | `card.highlight` requires a paired `chip.label` — `components.html` §02.2 |
| Inconsistent card heights in a row | Height-lock via the row primitive — referenced from the per-template contract |
| Diagram exceeds locked viewBox | `--canvas-width-wide` 2200 variant + split rule — `foundations.html` §01.1 |
| Arrows route through unrelated cards | `--arrow-clearance` 16 + lane gutter system — `connectors.html` §04.4, §04.7 |

---

## What's not in this bundle (future work)

- **Static-only (no-animation) SVG export** for PDF embedding — not currently supported; PDF consumers paste the `.light.svg` and accept that animations freeze at first frame.
- **Single-file `prefers-color-scheme` SVGs** — tested unreliable on Notion (strips `<style>` blocks). Two-file output is canonical; the single-file pattern is documented in `troubleshooting.md` as a "GitHub-only" footnote.

---

## Quality bar (for the downstream generator)

A diagram passes if every one of these is true:
- Both `<slug>.light.svg` AND `<slug>.dark.svg` were emitted
- The two files share structure — only color values, shadow filter bodies, and canvas gradient stops differ
- Background, font, viewBox width, indigo identity all match foundations verbatim (theme-appropriate)
- Every card is a named variant from `components.html` (slot positions locked)
- Every icon is from `icons.html` or the `icon.generic-service` fallback
- Every arrow is one of the eight taxonomy types
- Every connector label is in zone A, B, or C — no rotation
- Parallel arrows obey the gutter rule; > 3 collapse to a trunk
- Crossings ≤ 3 with the jog priority applied
- No arrow passes within `--arrow-clearance` (16) of an unrelated card
- ≤ 3 animation classes
- Cross-diagram services use manifest-pinned label + surface + icon

Anything else and the diagram is wrong — not a matter of taste.

---

## Contact / iteration

Open `index.html` in a browser. Each page has anchor-linked sections (e.g. `connectors.html#labels`) so a tighter feedback loop is easy. The reviewer site is the spec — comments and changes should reference its section numbers.
