# Template: Data schema (ER-style)

Use when the deliverable is a **data model** — entities with typed fields and relationships. There's no equivalent in the reference SVGs (the canon doesn't include an ER diagram), so you'll be synthesizing the style. Use the existing typography, palette, and card geometry as the anchor.

## When this fits

- "Show me the schema for the knowledge tables"
- "I need an ER diagram for the new domain model"
- "What are the entities and how do they relate?"
- Any structural data view: tables, collections, types, with relationships (1:1, 1:N, N:N).

## Use a different template if...

- Data flow through stages rather than data structure → `pipeline-flow`
- Storage topology (where data lives physically) → `infrastructure`
- Components and how they communicate → `layered-architecture`
- The data model spans multiple bounded contexts that should be shown separately → split into multiple `data-schema` diagrams

## Input contract

```
Title: <e.g. "OrderFlow · Data Model">
Subtitle: <one-line summary>

Entities:
  - Name: <EntityName>
    Variant: primary | secondary | reference
    Fields (in display order):
      - <field_name>: <type> [PK] [FK→Other.id] [INDEX] [NULLABLE]
    Notes (optional, 1 line italic footer): <e.g. "content-addressed", "versioned, never deleted">

Relationships:
  - <FromEntity>.<field> → <ToEntity>.<field>
    Cardinality: 1:1 | 1:N | N:N
    Label (optional): <relationship name, e.g. "cites", "supersedes">

Groups (optional):
  - <GroupName>: [Entity1, Entity2, Entity3]
    Subtitle: <e.g. "Postgres", "GCS", "Read replica">
```

### Worked example

> **User input:** "Users place Orders which contain OrderItems. Each OrderItem references a Product. Users belong to a Tenant."

**Normalized canonical spec:**

```
Title: Commerce — Data Model
Subtitle: Tenant-scoped order graph

Entities:
  - Tenant (secondary)
    Fields:
      - id        : uuid           [PK]
      - name      : varchar(80)

  - User (primary)
    Fields:
      - id        : uuid           [PK]
      - tenant_id : uuid           [FK → Tenant.id]
      - email     : varchar(255)   [INDEX]

  - Order (primary)
    Fields:
      - id        : uuid           [PK]
      - user_id   : uuid           [FK → User.id]
      - placed_at : timestamptz

  - OrderItem (secondary)
    Fields:
      - id          : uuid         [PK]
      - order_id    : uuid         [FK → Order.id]
      - product_id  : uuid         [FK → Product.id]
      - qty         : integer

  - Product (reference)
    Fields:
      - id    : uuid               [PK]
      - sku   : varchar(40)        [INDEX]
      - name  : varchar(120)

Relationships:
  - User.tenant_id       → Tenant.id  | N:1 | belongs to
  - Order.user_id        → User.id    | N:1 | placed by
  - OrderItem.order_id   → Order.id   | N:1 | line of
  - OrderItem.product_id → Product.id | N:1 | references

Groups: none
```

## Layout pattern

- **Canvas:** 1660 × variable. For ~6 entities use ~700–820. For 10–14 entities use ~1000–1200. If it doesn't fit, split into two diagrams (one per bounded context) rather than cram.
- **Entity layout:** roughly two columns, or a radial layout if there's a clear hub entity. Avoid a single tall column or wide row — readers need to scan in both axes.
- **Entity cards:**
  - **Primary entity** (the main aggregate, the hub): dark card with `mainGrad`. Use white text. Title 15px weight 600.
  - **Secondary entities** (related but lighter-weight): light card (white fill, `#e8e2d8` border). Title 14px weight 600, `#1a1a18`.
  - **Reference / lookup entities** (small enums, dim tables): light card with a slightly tinted fill (`#f5f1ea`).
  - Width: 220–280px. Height: depends on field count, ~24px header + 22px per field row + 12px padding.
- **Field rows inside an entity:**
  - 22px row height
  - Left: field name (monospace, 10–11px, color matches card body — `#4a4845` or `rgba(255,255,255,0.85)`)
  - Right: type (monospace, 10px, dimmer — `#706e67` or `rgba(255,255,255,0.55)`)
  - PK rows: prefix with a small indigo bullet `#4f5fb8`. The row label can be bold.
  - FK rows: prefix with a small slate bullet `#6b7280`. Add `→ <Target>.<field>` in 9px italic to the right of the type.
  - Index rows: subtle tint on the row background (`rgba(79,95,184,0.10)`) and a tiny `INDEX` chip on the right.
- **Field separator:** thin horizontal rule (`stroke="#e8e2d8"` on light cards, `rgba(255,255,255,0.10)` on dark) between header and first row, and optionally between PK block and the rest.

## Relationships

- **1:N:** solid `#4f5fb8` line from the FK side of the child to the PK side of the parent. Arrowhead at the parent (`arrowAccentSm`). Label centered: lowercase italic relationship name (e.g. `cites`, `belongs to`), 10px, color `#4f5fb8`.
- **N:N:** two-line representation — either show the join table as its own small light card with an INDEX badge, or use a thicker dashed line with `N:N` text inline.
- **1:1:** thin solid line, no arrowhead, with a small `1:1` text label.
- **Self-reference** (e.g. supersedes): a small loop arc on one side of the entity card, with the relationship name inline.

Avoid arrows that cross the entity cards themselves — route relationships through the gaps. If unavoidable, fade the crossing line (`opacity="0.6"`) so it's visually subordinate.

## Groups (storage / bounded contexts)

If entities are grouped by storage system (e.g., Postgres vs GCS vs cache), wrap each group in a soft dashed boundary rectangle:
- Stroke: `#9e9b95`, `stroke-width="1"`, `stroke-dasharray="6,5"`, no fill
- Group label at the top-left of the boundary: 9px ALL-CAPS, weight 600, color `#9e9b95`, letter-spacing 1.5
- Boundary padding: ~24px from boundary edge to entity cards inside

## Animations

ER diagrams are static info. **No animations.** Don't add pulsing dots, motion paths, or rotating rings. They distract from the structural reading. The single allowed exception: a `pulse` on the title of a single entity if the diagram is meant to highlight one entity ("the new table we're adding").

## Common pitfalls

- Too many fields per entity (15+). If an entity has that many, you're over-modeling for the diagram. Show the load-bearing fields (PKs, FKs, the 3–5 fields the reader actually cares about) and add an italic footer "+ 12 metadata columns".
- Crossing relationships. Re-layout entities to avoid crossings before resorting to opacity tricks.
- Inconsistent type notation. Pick one — `uuid`, `varchar(255)`, `timestamptz`, `jsonb` (Postgres style) or `string`, `int`, `datetime`, `text` (generic) — and stick to it across the diagram.
- Treating every entity as primary. Use the variant levels (primary / secondary / reference) to establish hierarchy. The reader's eye should land on the 1–2 hub entities first.
