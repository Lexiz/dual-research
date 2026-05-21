# diagram skill · reference bundle · v2.0.1

**What this skill is.** The `diagram` skill produces polished SVG architecture diagrams from prose. It restates the user's intent, classifies the dominant structure (static / time-ordered / data model / topology / integration surface), picks one of nine templates, and renders.

**What it produces.** A pair of self-contained SVG files — `<slug>.<mode>.light.svg` + `<slug>.<mode>.dark.svg` — no external assets, all gradients / filters / markers / keyframes inlined in `<defs>`. ViewBox 1660 × height-to-fit. Light and dark renders share layout, arrows, icons, and labels; only canvas, surface, ink, shadow, and connector colors swap.

**When to invoke.** Any time the user wants to visualise, diagram, or chart a system — "draw this", "show me X as a diagram", "create a chart for this", "visualise this architecture / data model / flow / topology", or "give me a Material dark version of this". Skip for prose-only explanations, mermaid-style text diagrams, or hand-drawn aesthetics.

**Input contract.** Free prose. The skill detects (a) the mode + theme requested and (b) the dominant structure to classify into a template. If the input is genuinely ambiguous about either, the skill asks one focused question before drawing — see `SKILL.md` Step 1.

**Output contract.** Two SVG files per requested theme variant (or four if `theme: both`), written by convention to `diagrams/<slug>.<mode>.{light,dark}.svg` adjacent to the document referencing them. Self-contained — Notion, GitHub, Slack, and PDF all paste-friendly.

---

## Two design systems, one skill

The skill ships **two parallel design systems** — pick one per request:

| Mode | Identity | Type | Icons |
|---|---|---|---|
| **Pixel** (`pixel`, default) | cream + indigo on a polished doc page | Inter | 78-icon custom library |
| **Material** (`material`) | Material 3 design system — sable + sage palette | Roboto Flex (plain) + Roboto Serif (brand) | Material Symbols Outlined (~80 curated glyphs + monogram fallback) |

Both modes ship light + dark variants. Mode is part of the filename so both versions of the same diagram can coexist in one folder without collision.

**The skill defaults to Pixel** when the user doesn't say which mode they want — this preserves the behavior of every existing invocation.

A multi-diagram proposal pins one mode for the whole set via the manifest; mixing modes within a single proposal is a hard error (a proposal is a coherent reader experience).

---

## How to use this bundle

Two ways to consume it:

1. **For humans reviewing the system** — open `index.html` in a browser. The reviewer site has a per-mode bundle: `pixel/` covers the cream + indigo design system; `material/` covers the Material 3 design system. Each mode bundle has the same shape: foundations → components → icons → connectors → templates → examples. Mode-agnostic pages (set manifest, input contracts) live at the bundle root.

2. **For the skill generating diagrams** — `SKILL.md` is the orchestrator. After detecting the requested mode in Step 1, every subsequent `references/<mode>/...` reference in Steps 3–7 routes to the right bundle. Template input contracts (`templates/<name>.md`) are mode-agnostic and live at `references/` root.

The HTML reference pages are the visual reviewer; the canonical truth is the cumulative spec captured across both mode bundles. Treat any rendered SVG primitive on a page as a copy-pasteable fragment for that mode.

---

## Folder map

```
references/
├── README.md                       ← you are here
├── index.html                      ← entry · overview · mode picker · deliverables map
├── gallery.html                    ← tabbed showcase: V2 reference · Pixel flow · Material flow
├── manifest.html                   ← cross-diagram consistency mechanism · mode + theme pinning
├── troubleshooting.md              ← common failure modes (mode-tagged where relevant)
├── CHANGELOG.md                    ← release history
├── templates/                      ← per-template input contracts · mode + theme agnostic
│   └── <name>.md  × 9
├── pixel/                          ← Pixel mode (cream + indigo) — the default
│   ├── foundations.html            ← D1 · color (light + dark), type, spacing, shadow, animation tokens
│   ├── components.html             ← D2 · cards, chips, shapes, lanes, stages, groups, callouts
│   ├── icons.html                  ← D3 · 78 icons × theme matrix + monogram fallback
│   ├── connectors.html             ← D4 · arrow taxonomy, gutters, labels, crossings, density caps
│   ├── templates.html              ← D5 · per-template visual contracts (all 9 filled)
│   ├── examples.html               ← D6 · canonical worked SVGs viewer (9 paired galleries)
│   ├── flow.html                   ← all 6 reference pages concatenated for end-to-end reading
│   ├── _shared.css                 ← all Pixel styles: tokens + doc chrome + primitives
│   └── examples/                   ← 18 canonical SVGs (9 templates × 2 themes)
│       ├── <name>.pixel.light.svg  × 9    ← cream canvas, indigo accent
│       └── <name>.pixel.dark.svg   × 9    ← near-black canvas, lifted surfaces
└── material/                       ← Material mode (Material 3 · sable + sage)
    ├── foundations.html            ← D1 · M3 tokens + 8 diagram-specific service-card extensions
    ├── components.html             ← D2 · M3 primitives (md-card / md-chip / md-status / …) + extensions
    ├── icons.html                  ← D3 · Material Symbols Outlined catalog + inline-path conversion
    ├── connectors.html             ← D4 · arrow taxonomy in M3 palette + M3 motion notes
    ├── templates.html              ← D5 · per-template visual contracts in M3 vocabulary
    ├── examples.html               ← D6 · canonical worked SVGs viewer
    ├── flow.html                   ← all 6 reference pages concatenated for end-to-end reading
    ├── _tokens.css                 ← M3 design tokens + M3 primitive classes (owned by this skill)
    ├── _shared.css                 ← doc-site chrome + the 8 md-card--service-* extensions
    └── examples/                   ← 18 canonical SVGs (9 templates × 2 themes)
        ├── <name>.material.light.svg  × 9
        └── <name>.material.dark.svg   × 9
```

Both mode folders are fully self-contained: copy `references/` anywhere and every page renders without external dependencies (the Google Fonts CDN is the only network resource, and only the doc-site pages load it — emitted SVGs are entirely offline).

---

## What's locked (do not change)

These are the load-bearing contracts. They hold across both modes.

| Contract | Value | Why locked |
|---|---|---|
| `--canvas-width` | **1660** | Visual rhythm across diagrams. Wide variant `2200` exists only for explicit landscape three-column overviews. |
| Output format | **Two** self-contained SVGs per diagram — `<slug>.<mode>.light.svg` + `<slug>.<mode>.dark.svg`, no external assets, all gradients/filters/keyframes inline | Notion embedability + theme parity. |
| Mode is in the filename | `.pixel.` or `.material.` segment between slug and theme | Lets both design-system versions of one diagram coexist; reader can see the mode at a glance. |
| Animation cap | **Max 3 animation classes per diagram** | Calm aesthetic — codified in each mode's `foundations.html` §01.6. Theme-portable. |
| Mode pin per set | Manifest's `mode:` field is authoritative; per-diagram override is a hard error | A proposal is a coherent reader experience — mixing design systems is a design failure. |
| Theme pin per set | Manifest's `theme:` field is authoritative; per-diagram override is a hard error | Same logic as mode pin. |

**Per-mode identity (the mode-specific load-bearing surfaces):**

| Mode | Canvas (light / dark) | Accent | Type |
|---|---|---|---|
| **Pixel** | `#f5f1ea → #ece8e0` / `#1a1a1f → #14141a` | indigo `#4f5fb8` / `#7785d4` | Inter |
| **Material** | `#faf9f6 → #ece8de` / `#0d0f12 → #08090b` | info-blue `#6b9cf0` (`--md-tertiary`) | Roboto Flex (plain) + Roboto Serif (brand) |

---

## The six deliverables, at a glance

Each deliverable exists in both `pixel/` and `material/`. The mode-shared content (template input contracts, manifest schema) sits at the root.

### D1 · Foundations (`<mode>/foundations.html`)
Locked registries for everything in the mode: canvas, semantic color palette, surface gradients, typography roles, spacing tokens (`--gap-card`, `--lane-gutter`, `--label-clearance`, etc.), shadow registry, and animation registry.

**Use it when:** any spatial or stylistic decision needs a value — never invent a hex, font-size, or pixel offset.

### D2 · Components (`<mode>/components.html`)
A closed library of slotted primitives:
- **Cards** — 7 variants: `card.primary` / `card.secondary` / `card.reference` / `card.compact` / `card.deferred` / `card.highlight` (+ optional icon, status, footer slots)
- **Chips** — `chip.status` (5 states) · `chip.count` · `chip.version` · `chip.label`
- **Shapes** — `node.circle` · `node.pill` · `node.diamond` · `node.hexagon` · `node.star` · `node.note` (6 shapes for non-card nodes — events, decisions, mesh nodes, highlights, annotations)
- **Stages** — `stage.numbered-token` · `stage.divider`
- **Lanes** — `lane.header` · `lane.vertical` · `lane.activation-box`
- **Groups** — `group.boundary` · `group.label`
- **Callouts** — `callout.note` · `legend.chip`

**Use it when:** drawing any structural element. If a primitive isn't in this list, the generator does not invent one — it picks the closest match, or uses the documented fallback.

### D3 · Icons (`<mode>/icons.html`)
The two modes use different icon strategies:

- **Pixel** — **78 icons** in 9 categories drawn to one density spec (32 × 32 bounding box, filled silhouettes, consistent radii), each with explicit light-card and dark-card variants. Hand-tuned for the cream + indigo system.
- **Material** — **Material Symbols Outlined**, the same icon font Material 3 ships with. Reference pages load the Google Fonts CDN; canonical SVGs pre-convert glyphs to inline `<path>` data so output stays self-contained. ~80 curated glyphs across 9 service categories, plus a monogram fallback host (`extension` glyph + 2-letter overlay) for third-party services without a canonical glyph.

The Pixel category breakdown:

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

### D4 · Connectors (`<mode>/connectors.html`) — the highest-value page
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

### D5 · Templates (`<mode>/templates.html` + shared `templates/<name>.md`)
A visual contract per template — five fields: components used, icons used, layout rules, arrow types, anti-patterns. **All nine templates are filled in both modes.** The nine: `layered-architecture`, `pipeline-flow`, `sequence`, `system-context`, `data-schema`, `infrastructure`, `event-flow`, `connector-map`, `freeform`. Each has a dark-variant note.

**Input contracts (`templates/<name>.md`) are mode-shared** — they describe what the user must supply, not how it renders. One contract drives both modes.

The `freeform` template is the catch-all — when no other template fits, decompose the request into nouns → cards, verbs → arrows, groupings → boundaries, ordering → stages or lanes.

### D6 · Worked canonical examples (`<mode>/examples.html`)
**Eighteen** end-to-end SVGs per mode — nine templates × two themes — of the same proposal ("OrderFlow") built only from that mode's system:

- `<mode>/examples/<name>.<mode>.light.svg` × 9
- `<mode>/examples/<name>.<mode>.dark.svg`  × 9

Open a `.light.svg` next to its `.dark.svg` sibling and they read as the same diagram on different backgrounds — same layout, same arrows, same icons, same labels, only colors swap. The pairs are the anchors a fresh generation should match. Across modes, the same diagram in `pixel/` and `material/` shares structure but expresses it in different visual languages — useful for comparing the two systems side-by-side.

### Cross-diagram consistency · the set manifest (`manifest.html`)
A small YAML file authored on the first diagram of a proposal that pins:
- service → label
- service → surface gradient
- service → icon
- group → boundary color
- animations used (running tally vs the 3-class cap)
- third-party long tail (monogram + tile color per integration)

Every later diagram in the set reads this manifest before generating. The example for the OrderFlow set is on `manifest.html` §07.2.

---

## How a diagram gets generated, end-to-end

When the skill is asked to produce a diagram, the workflow is:

1. **Detect mode + theme** — parse the request for `pixel` / `material` and `light` / `dark` / `both`. Default to `pixel` + `both` if unstated. Surface the choice in the restatement.
2. **Load the mode's foundations** — read `<mode>/foundations.html`. Start with §01.0 "Theme model", then the locked tokens. Apply verbatim.
3. **Pick template** — read the matching contract in `<mode>/templates.html` plus the shared input contract `templates/<name>.md`. If user request doesn't match any of the nine named templates cleanly, use `freeform` with its decomposition procedure.
4. **Consult the set manifest** — if this is not the first diagram in the set, read the existing `diagram-set-manifest.yaml`. Use pinned `mode:` / `theme:` and pinned service → label / surface / icon mappings. A per-diagram mode or theme override is a hard error.
5. **Compose from the mode's library** — every card is a named variant from `<mode>/components.html`. Every icon is from `<mode>/icons.html` (or that mode's `icon.generic-service` fallback). Every shape is a `node.*` primitive.
6. **Apply the connector contract** — every arrow has a taxonomy name; every label sits in a legal zone; every parallel run respects gutters; every crossing follows the jog priority. Check against the contract checklist on `<mode>/connectors.html`.
7. **Animate sparingly** — at most 3 animation classes per diagram, from the mode's registry. If a fourth feels needed, drop one or split the diagram.
8. **Theme pass** — render once with the mode's light tokens, once with its dark tokens, producing `<slug>.<mode>.light.svg` + `<slug>.<mode>.dark.svg`. The two files share structure; only color values, shadow filter bodies, and canvas gradient stops differ.
9. **Self-check both renders** against the canonical example pair for the template (`<mode>/examples/<name>.<mode>.{light,dark}.svg`). Apply the standard checks (arrow routing, label clearance, height locking, icon alignment) to each PNG plus the five dark-specific checks (canvas leakage, invisible elevation, accent legibility, text contrast, layout parity). Iterate against the *worse* variant.
10. **Update the manifest** — if new services were drawn, append them so the next diagram in the set inherits.

---

## The failure modes this system prevents

For each historically observed failure mode, the prevention now lives in a specific spec section:

| Original failure | Prevented by |
|---|---|
| Icons crash through card titles | `card` anatomy — reserved icon slot (top-left, 36×36 with 20/20 inset) — `<mode>/components.html` §02.1 |
| Connector labels rotated vertically | Zone A/B/C rule, no rotation ever — `<mode>/connectors.html` §04.5 |
| Floating labels with no anchor | Every connector label bound to a line; orphan labels become `chip.label` on a card — §04.5b |
| Inconsistent "deferred" treatment | `card.deferred` is the single canonical look — `<mode>/components.html` §02.2 |
| Floating chip row with no flow | Chips never freestanding — adjacency rule — `<mode>/components.html` §02.3 |
| Unexplained highlight border | `card.highlight` requires a paired `chip.label` — `<mode>/components.html` §02.2 |
| Inconsistent card heights in a row | Height-lock via the row primitive — referenced from the per-template contract |
| Diagram exceeds locked viewBox | `--canvas-width-wide` 2200 variant + split rule — `<mode>/foundations.html` §01.1 |
| Arrows route through unrelated cards | `--arrow-clearance` 16 + lane gutter system — `<mode>/connectors.html` §04.4, §04.7 |

---

## What's not in this bundle (future work)

- **Static-only (no-animation) SVG export** for PDF embedding — not currently supported; PDF consumers paste the `.light.svg` and accept that animations freeze at first frame.
- **Single-file `prefers-color-scheme` SVGs** — tested unreliable on Notion (strips `<style>` blocks). Two-file output is canonical; the single-file pattern is documented in `troubleshooting.md` as a "GitHub-only" footnote.

---

## Quality bar (for the downstream generator)

A diagram passes if every one of these is true:
- Both `<slug>.<mode>.light.svg` AND `<slug>.<mode>.dark.svg` were emitted
- The two files share structure — only color values, shadow filter bodies, and canvas gradient stops differ
- Background, font, viewBox width, accent identity all match the mode's foundations verbatim (theme-appropriate)
- Every card is a named variant from the mode's `<mode>/components.html` (slot positions locked)
- Every icon is from the mode's `icons.html` or the mode's `icon.generic-service` fallback
- Every arrow is one of the eight taxonomy types
- Every connector label is in zone A, B, or C — no rotation
- Parallel arrows obey the gutter rule; > 3 collapse to a trunk
- Crossings ≤ 3 with the jog priority applied
- No arrow passes within `--arrow-clearance` (16) of an unrelated card
- ≤ 3 animation classes
- Cross-diagram services use manifest-pinned label + surface + icon
- Mode pin honored: every diagram in a manifested set uses the same `mode:` and `theme:`

Anything else and the diagram is wrong — not a matter of taste.

---

## Contact / iteration

Open `index.html` in a browser to navigate the reviewer site. Each mode bundle has anchor-linked sections (e.g. `pixel/connectors.html#labels` or `material/connectors.html#labels`) so a tighter feedback loop is easy. The reviewer site is the spec — comments and changes should reference its section numbers.
