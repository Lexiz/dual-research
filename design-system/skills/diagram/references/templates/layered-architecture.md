# Template: Layered architecture

Use when the system is naturally described as 2–4 horizontal **layers** stacked top-to-bottom, with components in each layer and handoff arrows between layers. The canonical example is `examples/layered-architecture.svg` (Arc 2.0 — user/UI layer → agent layer → execution & publish layer).

## When this fits

- "There's a frontend, an API layer, and a worker pool"
- "The main agent hands off to a builder sub-agent and a research sub-agent"
- "Three layers: ingestion, processing, serving"
- Any system where the natural reading order is top → bottom, with discrete tiers.

## Use a different template if...

- Left → right ordered stages → `pipeline-flow`
- Hub with peripheral integrations → `connector-map`
- Cloud deployment topology → `infrastructure`
- Time-ordered messages between actors → `sequence`
- Just the system boundary, no internal layers → `system-context`

## Input contract

```
Title: <one-line title>
Subtitle: <one-line summary — what the diagram is showing>

Layer 1 (top): <name>
  Components:
    - <Card name>: <type> — <1-line purpose>
      Sub-items: <bullets — middleware chips, tools, tabs, etc.>
      State: <e.g. "live dot", "active tab is Artifact">
  Connections out:
    - <from card> → <to card in next layer>: <style>, label "<UPPERCASE>"

Layer 2 (middle): <name>
  ...

Layer 3 (bottom): <name>
  ...

Cross-layer/intra-layer handoffs (optional):
  - <from> → <to>: <style>, label "<UPPERCASE>", animation: <yes/no>

Animations:
  - <element> pulses / rotates / has flowing dots
```

### Worked example

> **User input:** "We have a React SPA, a FastAPI backend with rate limiting and auth middleware, and a Postgres database with a Redis cache in front of it."

**Normalized canonical spec:**

```
Title: Web App — Layered Architecture
Subtitle: Frontend, API tier, data tier

Layer 1 (top): USER LAYER
  Components:
    - React SPA (light card)
      Sub-items: Pages · Components · Hooks
  Connections out:
    - React SPA → FastAPI Backend: solid-primary, label "HTTPS"

Layer 2 (middle): API LAYER
  Components:
    - FastAPI Backend (builderGrad)
      Sub-items: Rate limit · Auth · Routes
      State: live dot
      Middleware ring: yes
  Connections out:
    - FastAPI Backend → Postgres: solid-primary, label "READS · WRITES"
    - FastAPI Backend → Redis Cache: solid-primary, label "CACHE"

Layer 3 (bottom): DATA LAYER
  Components:
    - Postgres (sandboxGrad)
      Sub-items: Primary · RLS
    - Redis Cache (harnessGrad)
      Sub-items: Session · Hot rows

Animations: live-dot on FastAPI only
```

## Layout pattern

- **Canvas:** 1660 × ~940 for 3 layers, ~700 for 2 layers, ~1100 for 4 layers.
- **Title block:** centered at top, ~28–44px from canvas top.
- **Layer label:** small ALL-CAPS label flush-left at the top of each layer band (`AGENT LAYER`, `EXECUTION & PUBLISH LAYER`).
- **Layer spacing:** ~80px between the bottom of one layer's cards and the top of the next. This is where handoff arrows live, with labels above and italic subtitles below.
- **Within a layer:** cards distributed left-to-right with ~20–30px gaps. Cards can vary in width (size to content). Heights within a layer should match or come close.
- **Card types:**
  - Primary actor / hero: dark card with `builderGrad` (indigo).
  - Main / persistent / orchestrator: dark card with `mainGrad` (neutral dark).
  - Secondary actor / research / support: dark card with `researchGrad` (slate).
  - Light cards (white fill) for: user, UI surfaces, panels, lists, anything informational.
  - Specialized: `sandboxGrad` for execution/env, `harnessGrad` for gates/health, `artifactGrad` for catalogs/storage.
- **Middleware / capability rings:** wrap a dark agent card with a rotating dashed ring (`class="mw-ring"`) and place chips above the card for middleware/capability names. See the Arc main-agent layout for the canon.

## Connections inside this pattern

- **Top-down primary flows:** solid `#4f5fb8` with `arrowAccent`. Often labeled `TYPES`, `STREAMS`, `INVOKES`.
- **Intra-layer handoffs (agent → agent):** dashed indigo `stroke-dasharray="5,4"` with `arrowAccentSm`. Labeled `HANDOFF · <what>` and an italic subtitle if there's nuance (`"+ conversation excerpt (so builder never re-asks)"`).
- **Mirror / secondary flows:** dashed grey, labeled `MIRRORS`, `WATCHES`, `OBSERVES`.
- **SSE / event-stream backbones:** a thin dashed vertical line (or branching tree) with motion-path dots flowing along it. Label the bus inline: `SSE STREAM` ALL-CAPS at the midpoint.

## Animations to consider

Pick at most 3:
- Motion-path dots flowing along primary streams (`<animateMotion>`)
- Rotating dashed rings around middleware stacks (`mw-ring`)
- Live status dots on cards that have state (`live-dot`)
- Tick color-cycle on a list of passing checks (`tick1`, `tick2`, …)
- Terminal caret blink inside an embedded console (`caret-blink`)

## Common pitfalls

- Too many handoff arrows crossing each other. If a layer has 4+ cards with handoffs to multiple cards in the next layer, consider grouping cards or splitting into two diagrams.
- Layer labels missing — without `AGENT LAYER` / `EXECUTION LAYER` style markers, the eye doesn't know to scan in tiers.
- Cards crammed edge-to-edge. The Arc canon has ~28–40px from canvas edge to first card.
