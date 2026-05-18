# Template: System context

Use when the deliverable is a **high-level view of the system boundary** — who the users are, what external systems the platform integrates with, and where the system sits in its environment. This is the C4 Level-1 "context" diagram. It is the standard first diagram in any architectural proposal.

## When this fits

- "Show me the big picture of this system"
- "Who uses it and what does it connect to?"
- "System boundary diagram", "C4 context", "stakeholder view"
- Opening slide of a technical proposal that needs to orient the reader before going deeper
- Any time the audience is non-technical and needs to understand scope before implementation detail

## Use a different template if...

- Internal components or layers are the focus → `layered-architecture`
- Cloud topology and deployment matter → `infrastructure`
- The flow is time-ordered → `sequence` or `pipeline-flow`
- The data model is the deliverable → `data-schema`
- Many integrations on a hub-and-spoke shape → `connector-map`

## Input contract

```
Title: <system name> - System Context
Subtitle: <one-line system purpose>

System (hub):
  Name: <name>
  Variant: main | builder (which dark gradient)
  Capabilities: <2-4 bullet capabilities>

External actors:
  - Name: <actor name>
    Type: person | system
    Role: <1-line description of who/what this is>
    Relationship to system: <direction: uses / notified by / provides data to>
    Label: <SHORT CONNECTION LABEL in CAPS>

Grouping (optional):
  - Group actors by category: users | data providers | outputs | infrastructure
```

### Worked example

> **User input:** "Our partner vetting platform is used by carriers and vendors who submit profile documents, and by Trimble Tenant Admins who configure rulesets. It syncs with Salesforce for CRM data and sends notifications via Slack."

**Normalized canonical spec:**

```
Title: Partner Vetting — System Context
Subtitle: External actors and integrations around the vetting platform

System (hub):
  Name: Partner Vetting Platform
  Variant: main
  Capabilities:
    - Profile + document submission
    - Ruleset evaluation
    - Notification delivery

External actors:
  - Carrier              | type: person | label: SUBMITS    | direction: in
  - Vendor               | type: person | label: SUBMITS    | direction: in
  - Trimble Tenant Admin | type: person | label: CONFIGURES | direction: in
  - Salesforce           | type: system | label: CRM SYNC   | direction: in
  - Slack                | type: system | label: NOTIFIES   | direction: out

Grouping: [users (left), data providers (right top), outputs (right bottom)]
```

## Layout pattern

Two layout strategies:

### Strategy A: Left-right split (up to 8 actors)
- Canvas: 1660 x ~700
- System hub: centered horizontally, vertically centered (~x=580, y=180, w=500, h=240)
- Human actors (persons) on the LEFT, stacked vertically, ~2-3
- External systems on the RIGHT, stacked vertically, ~3-5
- Arrows: horizontal, labeled

### Strategy B: Radial (8-14 actors)
- Canvas: 1660 x ~820
- System hub: centered at canvas midpoint
- Actors at angular positions around the hub, grouped by category (users top-left, data sources top-right, outputs bottom-right, infrastructure bottom-left)
- Arrows from hub edge to actor edge or vice versa

## Person icon (humans/users)

Render users as a distinctive person silhouette inside a light card. Use this inline SVG construction centered at (cx, cy):

```xml
<!-- Person icon centered at cx, cy -->
<circle cx="cx" cy="cy-10" r="8" fill="#1a1a18"/>
<rect x="cx-10" y="cy" width="20" height="16" rx="5" fill="#1a1a18"/>
```

Place the icon at the top-left of the actor card. Label below: actor name (14px weight 600) and role (10px, `#4a4845`).

## External system icon

External systems use a light card with a category-colored swatch (same as connector-map spoke card) plus a monogram. Add a subtle dashed border to distinguish from internal components:
- Light card: `fill="white"`, `stroke="#ddd8ce"`, `stroke-dasharray="4,3"` (dashed = external)
- Internal (the hub): solid stroke or no stroke

## Connections

- **Person uses system:** solid `#4f5fb8`, arrowhead at system
- **System notifies/sends to person:** solid `#4f5fb8`, arrowhead at person
- **System reads from external:** dashed `#9e9b95`, arrowhead at system
- **System writes to external:** dashed `#9e9b95`, arrowhead at external
- Connection labels: ALL-CAPS short phrase. Optionally italic 9px subtitle describing the protocol.

## Animations

- One `live-dot` on the system hub's status indicator. Nothing else. Context diagrams are static informational views.

## Common pitfalls

- Too much detail. The system hub should say WHAT the system does, not HOW. Keep capabilities to 3-4 bullets max.
- Showing internal components. Save those for layered-architecture.
- Labeling every arrow with a protocol stack. One short label per connection; add a protocol subtitle only if it's genuinely important for the audience.
- Drawing the system hub the same size as the actor cards. The hub must be visually dominant — at least 2x the width of any actor card.
