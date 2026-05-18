# Template: Freeform (catch-all)

The fallback template for anything that doesn't fit the other eight. Use this when the user's input is a composite view — multiple structures stitched together — or when the natural deliverable is a "full landscape" diagram covering research → development → application, or similar wide-scope overviews.

This template does NOT mean "anything goes." It enforces the same design-system constraints as every other template; it just gives you a procedure for composing a diagram from primitives when no canonical pattern applies.

## When this fits

- "Show the full project landscape" — multiple workstreams in one view
- "I want a diagram that combines context AND data model" — composite structures
- "Show the relationship between [research / dev / ops] pipelines" — multi-pipeline overviews
- An input that mentions both static structure AND time-ordered flow AND data and would need three diagrams under the canonical set
- Anything where the user's first instinct is "this is going to be a big diagram"

## When this DOESN'T fit (use another template instead)

- The input maps cleanly to one of the 8 specific templates — use that. Freeform is the fallback, not the default.
- "Show me how X calls Y" → `sequence`
- "Show me the database tables" → `data-schema`
- "Show me the cloud topology" → `infrastructure`
- "Show me who uses the system" → `system-context`

If you can write a one-line answer to "what's this diagram for?" using one of the canonical pattern names, use that pattern. Reserve freeform for genuinely mixed scopes.

## Input contract

Freeform's input is the most flexible, so the normalization step matters most. Extract:

```
Title: <e.g. "Partner Vetting — Full Project Landscape">
Subtitle: <one-line description of the scope>

Regions (columns or zones):
  - Name: <e.g. "Brainstorm Pipeline", "Development Pipeline", "Application">
    Position: column-left | column-center | column-right | top | bottom
    Purpose: <one-line description>
    Cards (in display order within the region):
      - Name: <card name>
        Variant: primary | secondary | reference | deferred | highlighted
        Icon: <icon name from icon-library, or null>
        Sub-items: <optional, 1-3 short lines>
        Footer: <optional italic caption>

Cross-region connectors (the ones that span regions — these are the most visible):
  - From: <region.card>
    To: <region.card>
    Type: solid-primary | dashed-handoff | mirror-secondary
    Label: <SHORT ALL-CAPS, MUST FIT HORIZONTALLY>
    Subtitle: <optional italic, 9px>

Intra-region connectors (within a single region):
  - From: <card> | To: <card> | Type: ... | Label: ...

Highlights (optional):
  - Card: <region.card>
    Reason: <one-line explanation; will be rendered as a callout chip>

Animations (optional, max 3 classes):
  - Type: motion-dots | pulse | rotate | tick
    Path: <which connector or card>

Manifest (REQUIRED for multi-diagram sets):
  - Read or write references/manifest.html (schema) + diagram-set-manifest.yaml (data) before generating.
    Entity → gradient and entity → icon assignments must match across diagrams.
```

If the user's prose doesn't fill every field, ask one focused question per missing required field. Don't make up content.

## Decomposition procedure (the freeform method)

When the input is loose prose, decompose it with this procedure. Do this in writing during Step 4 of the workflow — it produces the canonical spec above.

### 1. Identify nouns → cards

List every distinct *thing* the user mentioned. Each thing becomes a card.

- People, services, databases, queues, files, pipelines, products — all nouns.
- Group nouns by what they belong to. If three nouns belong to "the research pipeline," that's a region with three cards.
- If the user mentions a noun in passing but it's not load-bearing for the diagram's purpose, drop it. Don't draw what you don't need to draw.

### 2. Identify verbs → arrows

List every distinct *action* or *flow* the user mentioned. Each action becomes an arrow.

- "X feeds into Y" → arrow X → Y
- "X reads from Y" → dashed arrow X → Y, label "READS"
- "X triggers Y" → solid arrow X → Y, label "TRIGGERS"
- An action that's internal to one card (e.g. "the worker retries on failure") goes inside the card as sub-text, not as a self-loop arrow.

### 3. Identify groupings → boundaries

If multiple cards share a common context, wrap them in a soft dashed boundary:

- Cards belonging to the same pipeline / region / bounded context
- Cards owned by the same team or running on the same infrastructure
- Cards representing a single phase of a multi-phase process

Each group gets a small ALL-CAPS label at its top-left.

### 4. Identify ordering → lanes or numbered stages

If the cards in a region are ordered (stage 1, stage 2, stage 3...), apply pipeline-style numbered tokens. If they're parallel (all of these run independently), use a row layout with equal-height cards.

If a region has both ordered and parallel elements, use lanes (vertical columns within the region) rather than trying to encode order in connectors.

### 5. Identify deferred / future state → variant assignment

If the user marks something as "v2", "future", "stub", or "not yet built", assign the `deferred` variant. **Use one consistent treatment across the diagram** — don't dim some deferred cards and dash others. (This was a recurring inconsistency in old diagrams.)

### 6. Identify highlights → callouts

If the user marks something as "this is the key thing", give it the `highlighted` variant AND a small `callout.note` chip explaining why. Highlights without explanations are silent and confusing.

## Layout strategies

Freeform diagrams typically need one of these layouts. Pick based on the region count:

### Strategy A: Single-column vertical (1 region, 4–8 cards)

Fall back to `pipeline-flow` or `layered-architecture` instead — they're designed for this. Freeform is overkill for single-column.

### Strategy B: Two-column landscape (2 regions, 4–6 cards each)

- Canvas: viewBox 1660 × ~700–900
- Left region: x=40 to x=810
- Right region: x=850 to x=1620
- Inter-region gutter: 40px (this is where cross-region connector labels live)
- Each region has a top-of-region ALL-CAPS label, 9–10px, weight 600

### Strategy C: Three-column landscape (3 regions, 3–5 cards each)

This is the layout from the canonical "full landscape" example.

- Canvas: viewBox 1660 × ~800–1000
- Each region: ~520px wide, ~40px gutters between
- Region columns: x=40–560, x=600–1120, x=1160–1620
- Each region has a top ALL-CAPS label

**Important:** Do NOT widen viewBox past 1660 to fit a fourth column. If you genuinely need four columns, split into two diagrams (e.g. "Research → Dev" and "Dev → Application").

### Strategy D: Hub-and-zones (1 central region + surrounding zones)

- Central region: ~600px wide, centered
- Surrounding zones (top, bottom, left, right): smaller, each holding 2–4 cards
- Connectors flow from hub to zones and back

Use this when one of the regions is clearly the focal point and the others are supporting.

## Connector geometry (high importance)

Freeform diagrams are connector-heavy. The biggest visible failures in old freeform output were arrow problems. Apply these rules strictly:

1. **No vertical labels.** If a label can't fit horizontally above or below its line, the line must jog to make room, OR the label goes in a small inline chip on the line. Never rotate a label 90°.
2. **Reserve gutters.** Cross-region connectors live in the inter-region gutters (the gaps between regions). Never route a cross-region arrow through the body of a region.
3. **Label clearance.** Every connector label must have ≥6px clearance from the line and ≥12px clearance from any other label or card.
4. **Lane sharing.** If 2+ arrows flow between the same two regions, space them at ≥16px parallel separation. If you'd need more than 3 parallel arrows, collapse them into a single labeled trunk ("X DATA STREAMS").
5. **Crossings.** If two arrows must cross, the shorter / secondary arrow jogs with a small arc over the primary. Maximum 2 crossings per diagram before the layout needs rework.
6. **Card clearance.** Connectors don't pass within 12px of any card they don't connect.

## Components used (from the design system / component library)

Freeform draws on the widest range of components:

- **Cards:** primary (hero), secondary (supporting), reference (lookup), deferred (v2/future), highlighted (the focal element)
- **Chips:** status (live/healthy/blocked), label (ALL-CAPS taxonomy), version
- **Groups:** dashed soft boundary with top-left label
- **Callouts:** note chips paired with highlighted cards
- **Lanes:** for ordered sub-regions
- **Connectors:** solid-primary, dashed-handoff, mirror-secondary
- **Icons:** from the icon library; if you need an icon not in the library, apply the icon-library fallback rule

## Animations

Freeform is busy. Be conservative:

- Maximum 2 animation classes (one less than the global cap of 3).
- Prefer motion-dots on the most important cross-region connector to indicate primary flow direction.
- A single `live-dot` on the focal/highlighted card.
- No rotating rings, no terminal carets — those distract in a dense diagram.

## Common pitfalls

- **Trying to show everything.** Freeform isn't permission to dump every system detail in one diagram. If you can't read every card label at standard zoom, split.
- **Icons crashing through card titles.** Use `card.with-icon` (from the component library), which has a defined icon slot. Never overlay an icon on the title text.
- **Rotated vertical labels.** Never. Route around or use inline chips.
- **Floating labels.** Every label must visibly belong to a specific connector or region. Floating ALL-CAPS labels look like orphaned text.
- **Inconsistent deferred-state styling.** Pick one deferred variant (faded dark with dashed border) and apply it to every deferred card.
- **Silent highlights.** A dashed indigo border on one card with no callout chip explaining why = orphan highlight. Always pair.
- **viewBox widening.** If your three-column layout doesn't fit, split — don't widen.
- **Same-rank cards with inconsistent heights.** Cards in the same row must height-lock to the tallest card in the row.

## Worked example

> User said: "I want a full landscape of the partner vetting project. Three pipelines — research, development, and the actual application. The research pipeline has human input, web/Notion URLs, and pasted documents flowing into a research wiki with sources, discovery, decisions, and design docs. Development has brainstorming → create-spec → agent-coding → pr-review → spec-retro → merged-PRs. Application has profile/consent, document intake/auth, rules/vetting, and a deferred network signal v2. There's a Postgres persistence layer with RLS. There are 4 web components and 4 consumer types."

Decomposition:

- **Regions** (Strategy C, three-column):
  - LEFT — "Brainstorm Pipeline": 3 input cards (light) → research wiki card (dark, primary)
  - CENTER — "Development Pipeline": 6 stage cards stacked vertically with numbered tokens, last one (Merged PRs) is harness-green variant
  - RIGHT — "Partner Vetting Application": top row of 4 dark cards (Profile, Document Intake, Rules, Network Signal-deferred); persistence layer card below; web components row of 4 light cards; consumers row of 4 light cards
- **Cross-region connectors:**
  - LEFT.design-docs → CENTER.brainstorming (solid-primary, label "DESIGN DOCS", horizontal)
  - CENTER.merged-prs → RIGHT.application (solid-primary, label "TO PROD", horizontal)
- **Intra-region connectors:** within each region as appropriate
- **Deferred variant:** apply to Network Signal AND MCP Adapter consistently
- **Highlight:** ARC/Mario consumer card highlighted with callout "MCP integration"
- **Animations:** motion-dots on the two cross-region connectors. Nothing else.

Then write the canonical spec, then generate.
