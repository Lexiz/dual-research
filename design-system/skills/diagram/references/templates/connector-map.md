# Template: Connector / integration map

Use when the deliverable is showing **what a system talks to** — a central system (hub) with external integrations (spokes) for data sources, sinks, auth, observability, etc. There's no exact equivalent in the reference SVGs, so style tokens come from `examples/layered-architecture.svg` (hub-style center card with connections out).

## When this fits

- "Show all the systems our platform integrates with"
- "Where does our data come from and where does it go?"
- "What MCP servers / APIs / connectors are we using?"
- Any inventory-style view where one system is the focus and the rest are peripheral.

## Use a different template if...

- Components are peers (no clear hub) → `layered-architecture` or `pipeline-flow`
- Cloud topology with regions/services → `infrastructure`
- Event-driven flow through a bus → `event-flow`
- System boundary at high level (C4-L1) → `system-context`

## Input contract

```
Title: <e.g. "Arc 2.0 · Integration Surface">
Subtitle: <one-line summary>

Hub:
  Name: <e.g. "Arc Platform">
  Variant: main | builder | research (which dark gradient)
  Sub-items: <1–3 capabilities or version info>

Spokes (one per integration):
  - Name: <External System>
    Category: data source | data sink | auth | observability | model provider | storage
    Direction: incoming (→ hub) | outgoing (hub →) | bidirectional (↔)
    State: live | planned | deprecated
    Subtitle: <optional 1-line, e.g. "OAuth", "REST + webhooks", "gRPC streaming">

Grouping (optional):
  - Group spokes by category, with a faint group label

Animations:
  - Optional pulse on "live" spokes
```

### Worked example

> **User input:** "Our platform integrates with Salesforce (read CRM), Slack (send notifications), Stripe (payments), Sentry (error tracking), and uses Cognito for auth."

**Normalized canonical spec:**

```
Title: Partner Vetting — Integration Surface
Subtitle: External connectors around the platform

Hub:
  Name: Partner Vetting
  Variant: main
  Sub-items: [v1.4, multi-tenant, REST + webhooks]

Spokes:
  - Salesforce | category: data source   | direction: incoming     | state: live | subtitle: "REST · webhooks"
  - Slack      | category: data sink     | direction: outgoing     | state: live | subtitle: "Webhook"
  - Stripe     | category: data sink     | direction: outgoing     | state: live | subtitle: "REST"
  - Sentry     | category: observability | direction: outgoing     | state: live | subtitle: "SDK"
  - Cognito    | category: auth          | direction: bidirectional | state: live | subtitle: "OAuth 2"

Grouping: by category
Animations: live-dot pulse on each live spoke
```

## Layout pattern

Two layout strategies — pick based on spoke count:

### Strategy A: Hub with side panels (≤ 8 spokes)
- Canvas: 1660 × ~720.
- Hub card centered horizontally, vertically centered. Width ~360–420px, height ~200px.
- Spokes arranged on the left and right of the hub, ~3–4 per side, stacked vertically. Each spoke is a small light card (~220 × 64px) with category icon + name + subtitle.
- Connections: short horizontal lines from spoke right-edge → hub left-edge (and vice versa for the right side).

### Strategy B: Radial (9–16 spokes)
- Canvas: 1660 × ~900–1000.
- Hub card centered. Width ~340 × 200px.
- Spokes arranged in two concentric "halos" around the hub at angular positions. Inner halo (closer, more important integrations) at ~360px radius. Outer halo (less critical) at ~560px radius. Use 8 angular slots (every 45°) for the inner halo; fill outer halo at the gaps.
- Connections: line from hub edge along the spoke's angular bearing to the spoke card. Curve slightly for visual softness.

If neither fits cleanly, fall back to Strategy A and split into two diagrams.

## Spoke card design

- Light card (white fill, border `#e8e2d8`), corner radius 10.
- 220 × 64px (or 220 × 80px if subtitle present).
- Inside, left-to-right:
  1. **Category icon swatch** (28 × 28 circle) — use a category-specific color:
     - data source: `#1e3f52` (sandbox blue)
     - data sink: `#5e3f1c` (artifact brown)
     - auth: `#2a5e40` (harness green)
     - observability: `#4a5568` (slate)
     - model provider: `#4f5fb8` (indigo — primary accent)
     - storage: `#1a1a18` (neutral dark)
     - integration / generic: `#9e9b95` (grey)
  2. Single uppercase letter or 1–3 char monogram inside the swatch, white, 13px, weight 700.
  3. Spoke name: 14px, weight 600, `#1a1a18`.
  4. Subtitle: 11px, `#4a4845`. Italic optional.
  5. Live-state dot (4–5px) in the upper-right corner of the card: `#4f5fb8` (live), `#9e9b95` (planned/inactive), `#cc6e55` (deprecated). Use `class="live-dot"` only on live spokes.

## Hub card design

Dark card with `mainGrad` (default), `builderGrad`, or `agentGrad` depending on what the hub conceptually is.

- Title: 16–18px, weight 600, white.
- Subtitle: 11px, `rgba(255,255,255,0.7)`.
- Inside, list 2–4 hub capabilities as small dark chips (`rgba(0,0,0,0.22)` fill, white text, 10px monospace).
- Optionally include a small "live" status pill at the upper-right.

## Connections

- **Incoming (spoke → hub):** solid `#4f5fb8`, stroke-width 1.5, with `arrowAccent` at the hub.
- **Outgoing (hub → spoke):** solid `#4f5fb8`, stroke-width 1.5, with `arrowAccent` at the spoke.
- **Bidirectional:** two parallel lines (or a single line with `marker-start` AND `marker-end`), color `#4f5fb8`.
- **Deprecated:** dashed grey `#9e9b95`, `stroke-dasharray="4,3"`, opacity 0.5.
- **Connection labels:** optional. Use only if the integration has a notable protocol or pattern — "gRPC", "OAuth · webhooks", "S3 ↔ GCS". Place inline along the connection, 9px, color-matched.

## Grouping (optional)

If spokes naturally fall into categories (data sources / data sinks / observability), draw a faint dashed boundary around each category and label it:
- Stroke: `#9e9b95`, `stroke-width="1"`, `stroke-dasharray="6,5"`, no fill
- Label: 9px ALL-CAPS, weight 600, `#706e67`, letter-spacing 1.5, placed at the top of the group

This works best in Strategy A where spokes are clustered by side. For radial, prefer color-coding the icon swatches instead.

## Animations

- `live-dot` pulse on each "live" spoke's status indicator. Keep it.
- Optional motion-path dots flowing along 1–2 high-traffic connections. Don't animate all of them — pick the most semantically meaningful (e.g., the primary data source).
- No rotating rings, no loop arcs. Connector maps are inventory views, not flow views.

## Common pitfalls

- Too many spokes (16+). The diagram becomes a hairball. Group by category and show one representative spoke per category, with an italic footer "+ 5 other observability sinks". Or split.
- Inconsistent spoke card sizes. Pick 220 × 64 (or 80 with subtitle) and stick to it across the diagram.
- Hub too small. If the hub feels visually equivalent to the spokes, the reader can't tell what's central. Hub width should be at least 1.5× spoke width.
- Bare lines everywhere. If 12 spokes all have unlabeled lines, add direction-implying arrows AND group the spokes by category so the reader has another way to parse the map.
