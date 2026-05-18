# Template: Sequence diagram

Use when the deliverable shows **time-ordered message exchanges between actors or services**. Reading direction is top-to-bottom (time flows down). Each actor has a vertical lifeline; messages are horizontal arrows crossing between lifelines. This is the standard diagram for API flows, authentication handshakes, and multi-service request traces.

## When this fits

- "Trace what happens when a user does X"
- "Show the API flow for Y"
- "How does authentication work end-to-end?"
- "What calls what, in what order?"
- Any scenario where ORDER of operations matters and there are 3+ distinct actors

## Use a different template if...

- Static structure (no time component) → `layered-architecture`
- Hub-and-spoke integrations → `connector-map`
- Async events through a bus → `event-flow`
- A pipeline of stages rather than messages between actors → `pipeline-flow`
- Data model not flow → `data-schema`

## Input contract

```
Title: <Scenario name, e.g. "Partner Vetting Run - Sequence">
Subtitle: <one-line description of the scenario>

Actors (left to right, in order of first appearance):
  - Name: <actor name>
    Type: person | browser | service | queue | database | external
    Color: indigo | slate | green | neutral (maps to gradient)

Messages (top to bottom):
  - From: <actor name>
    To: <actor name>
    Label: <short message name, e.g. "POST /partners/vet">
    Type: sync | async | return | event
    Note: <optional 1-line detail, shown italic below the arrow>
```

### Worked example

> **User input:** "User clicks login on the frontend, the frontend calls /auth on the API, the API verifies credentials with Cognito, returns a JWT, and the frontend stores it."

**Normalized canonical spec:**

```
Title: Login — Sequence
Subtitle: OAuth-style credential exchange

Actors (left to right):
  - User     | type: person   | color: light
  - Frontend | type: browser  | color: light
  - API      | type: service  | color: builderGrad
  - Cognito  | type: external | color: dashed light

Messages (top to bottom):
  1. User     → Frontend  | CLICK LOGIN              | sync
  2. Frontend → API       | POST /auth               | sync   | note: "email + password"
  3. API      → Cognito   | VerifyCredentials        | sync
  4. Cognito  → API       | 200 + claims             | return
  5. API      → Frontend  | 200 + JWT                | return
  6. Frontend → User      | Logged in                | return | note: "JWT in localStorage"

Animations: none
```

## Layout pattern

- **Canvas:** 1660 x ~800 for 8-10 messages; add ~50px per additional 2 messages.
- **Actor row:** at the top, y=100-160. Each actor is a labeled box (~180px wide x 50px tall). Space actors evenly across the canvas. Actor center x values drive the lifeline x positions.
- **Lifelines:** vertical dashed lines (`stroke="#9e9b95"`, `stroke-dasharray="4,4"`) from the bottom of each actor box (y=160) to the bottom of the last message region (~y=canvas_height-60).
- **Message rows:** spaced ~60-70px apart vertically, starting at y=220. Each message is a horizontal arrow from one lifeline to another.
- **Activation boxes:** thin semi-transparent rectangles (~10px wide, ~55px tall) on a lifeline to show "this actor is active" during a multi-step interaction. Fill: `rgba(79,95,184,0.15)` for indigo actors, `rgba(74,85,104,0.15)` for slate.
- **Return arrows:** dashed (`stroke-dasharray="5,3"`), pointing back in the opposite direction. Use `arrowGrey` marker.

## Actor colors

Map actor types to card gradients:
- **person** (human user): light card, `fill="white"`, person icon in card
- **browser/UI** (frontend): light card, `fill="white"`, browser icon indicator
- **service** (API, worker): dark card, `fill="url(#mainGrad)"` or `fill="url(#builderGrad)"` for primary service
- **queue** (Pub/Sub, SQS, Kafka): dark card, `fill="url(#researchGrad)"`, queue icon indicator
- **database** (SQL, Redis): dark card, `fill="url(#storageGrad)"`, cylinder icon
- **external** (third-party API): light card, dashed border, external indicator

## Message arrow types

- **Sync call** (solid, forward): `stroke="#4f5fb8"`, `stroke-width="1.8"`, marker `arrowAccent`. Label above line, italic note below.
- **Async / event publish** (solid, forward, indigo): same stroke, but add `(async)` or `[event]` to label.
- **Return / response** (dashed, backward): `stroke="#9e9b95"`, `stroke-dasharray="5,3"`, marker `arrowGrey`. Label: HTTP status or return value.
- **Fire-and-forget**: thin solid `stroke-width="1.2"`, no label refinement needed.

## Message label placement

- Label text: 10px, weight 600, color matches arrow stroke
- Place label 6px above the horizontal arrow line, horizontally centered between the two lifelines
- Italic note (if present): 9px, `#9e9b95`, 6px below the arrow line

## Step numbers (optional)

If the sequence has 8+ messages, add a small numbered circle at the left end of each arrow:
```xml
<circle cx="x_left+8" cy="arrow_y" r="8" fill="#4f5fb8"/>
<text x="x_left+8" y="arrow_y" text-anchor="middle" dominant-baseline="central"
      font-size="8" font-weight="700" fill="white">3</text>
```

## Animations

Sequence diagrams are documentation artifacts — **no animations**. The single exception: a `live-dot` pulse on the primary service actor's header if the diagram is illustrating a live system.

## Common pitfalls

- Too many actors (7+). Lifelines crowd each other. Split into two diagrams by scenario phase.
- Messages that skip across several lifelines visually. Place actors so related actors are adjacent; avoid long diagonal spans.
- Unlabeled return arrows. Every response arrow needs at minimum an HTTP status or "return value" label.
- Mixing system-context level detail with sequence detail. If an actor is "the whole backend", split it into specific services.
- Equal spacing for every message. Vary vertical spacing to show where time genuinely passes (async waits = larger gap).
