# Template: Event-driven / async flow

Use when the deliverable shows a **producer-topic-consumer topology** — which services emit events, which event topics/queues they publish to, and which services subscribe and what they do. This is the standard diagram for Pub/Sub, Kafka, SQS/SNS, and any event-driven architecture.

## When this fits

- "Show the event architecture"
- "What produces and consumes events?"
- "Pub/Sub topology", "Kafka topic map", "async flow"
- "Which service handles which event?"
- Any system where services communicate primarily through a message bus rather than direct API calls

## Use a different template if...

- Synchronous REST / gRPC calls → `sequence` or `layered-architecture`
- Cloud topology → `infrastructure`
- Static service structure → `layered-architecture`
- Integration surface (external connectors) → `connector-map`

## Input contract

```
Title: <System name> - Event Flow
Subtitle: <one-line description of the async topology>

Producers (services that emit events):
  - Name: <service name>
    Events emitted:
      - <event-name>: <1-line description>
      - <event-name>: <1-line description>

Topics / Queues (the bus):
  - Name: <topic or queue name>
    Type: topic (fan-out) | queue (competing consumers) | stream (ordered)
    Description: <1-line>

Consumers (services that subscribe):
  - Name: <service name>
    Subscribes to: <topic name>
    Action: <1-line what it does on receiving the event>

Dead-letter / retry config (optional):
  - <any retry or DLQ notes worth showing>
```

### Worked example

> **User input:** "Orders service publishes order.placed events. Notifications service sends a confirmation email. Inventory service decrements stock."

**Normalized canonical spec:**

```
Title: Commerce — Event Flow
Subtitle: order.placed fan-out

Producers:
  - Orders Service
    Events emitted:
      - order.placed : "After successful payment"

Topics / Queues:
  - order.placed | type: topic (fan-out) | description: "Downstream services react"

Consumers:
  - Notifications Service
    Subscribes to: order.placed
    Action: "Send confirmation email"
  - Inventory Service
    Subscribes to: order.placed
    Action: "Decrement SKU stock"

Dead-letter / retry: "DLQ after 5 attempts; alert via PagerDuty"

Animations: one motion-dots class on Orders → order.placed → Notifications
```

## Layout pattern

- **Canvas:** 1660 x ~660. Add height if there are many topics or consumer action detail.
- **Three columns:**
  - Column 1 (PRODUCERS): x=40–340. Service cards stacked vertically.
  - Column 2 (TOPICS/BUS): x=560–1100. Topic cards centered vertically. May span the full height.
  - Column 3 (CONSUMERS): x=1320–1620. Service cards stacked vertically.
- **Column labels:** ALL-CAPS at top of each column band: `PRODUCERS`, `TOPICS / BUS`, `CONSUMERS`.
- **Topic cards:** distinct from service cards — use a queue-style visual (wider rect with double-wall ends, see icon library). Fill: `researchGrad`.

## Card designs

### Producer / consumer service card
- Light card (white fill) with category swatch (28x28 circle) + service name + events list.
- Same design as connector-map spoke card but taller to accommodate event list.
- Event names: 9px monospace, `#4a4845`, indented 8px.
- Width: 280px. Height: varies by event count (~60px base + 18px per event).

### Topic / queue card
- Dark card with `researchGrad`.
- Width: 480px.
- Header: topic name (14px, white, weight 600) + type badge (`TOPIC` / `QUEUE` / `STREAM` chip).
- Body: 1-line description (10px, `rgba(255,255,255,0.75)`).
- Optional: retention/ordering spec chip at bottom right.

## Connections

- **Producer to topic (publish):** solid `#4f5fb8`, stroke-width 1.8, `arrowAccent`. Label: the event name in ALL-CAPS, 9px, color `#4f5fb8`.
- **Topic to consumer (subscribe/deliver):** solid `#4f5fb8`, stroke-width 1.8, `arrowAccent`. Label: subscription name or filter.
- **Dead-letter queue:** dashed `#cc6e55`, stroke-dasharray "4,3", `arrowGrey`. Label: `DLQ` or `RETRY`.
- **Fanout (one topic to many consumers):** single line from topic right edge splits into branches — one branch per consumer. Use `Q x y x2 y2` curves for clean fan-out.

## Animations

- Motion-path dots flowing from each producer → through the topic → to its consumers. Use one dot per main event flow; stagger with `begin` offsets.
- Cap at 3 animation classes. For a dense topology, animate only the highest-volume path.

## Common pitfalls

- Showing both event-driven and synchronous calls on the same diagram. Keep them separate unless the hybrid is the whole point.
- Unlabeled topic-to-consumer arrows. Every subscription line must show what event triggers it.
- Too many topics (8+). Group related topics by domain and show one representative per group.
- Missing the consumer action. The consumer card should say what it DOES when it receives the event, not just what it is.
- Treating a queue (FIFO, competing consumers) and a topic (fan-out) identically. The card design and arrows should distinguish them.
