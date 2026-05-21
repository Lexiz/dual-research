# Template: Infrastructure / deployment diagram

Use when the deliverable shows **where components run** — cloud provider services, regions, availability zones, networking, databases, caches, queues, and how traffic flows between them. This is a deployment diagram. It uses standardized technical icons (cylinders for databases, cloud shapes, queue rectangles) rather than abstract boxes.

## When this fits

- "Show the infrastructure"
- "Deployment diagram", "cloud architecture", "how is this hosted?"
- "What GCP / AWS / Azure services are used?"
- Any time the audience needs to understand compute topology, data residency, scaling, or networking
- Security reviews, cost estimation, and ops runbooks all reference this diagram

## Use a different template if...

- Service-to-service API flow over time → `sequence`
- Event topology (producer/topic/consumer) → `event-flow`
- Logical layers without cloud detail → `layered-architecture`
- Data model → `data-schema`
- System boundary view → `system-context`

## Input contract

```
Title: <System name> - Infrastructure
Subtitle: <cloud provider + deployment model, e.g. "GCP - Cloud Run + managed services">

Cloud boundary:
  Provider: GCP | AWS | Azure | multi-cloud
  Regions: <list of region names if relevant>

Services (one entry per deployed unit):
  - Name: <service name>
    Type: compute | database | cache | queue | storage | cdn | gateway | auth | external
    Spec: <key sizing/config, e.g. "Cloud Run min=2 max=20", "Cloud SQL Postgres 15">
    Location: <region or zone if relevant>
    Connections: <which services it calls or receives from>

Network zones (optional):
  - Public zone: <services exposed to internet>
  - Private zone: <services behind VPC>
```

### Worked example

> **User input:** "GCP setup. Cloud Run for the API (min=2, max=20), Cloud SQL Postgres 15 for primary data, GCS for document uploads, Pub/Sub for event fan-out, Cloud Load Balancing in front of the API."

**Normalized canonical spec:**

```
Title: OrderFlow — Infrastructure
Subtitle: GCP — Cloud Run + managed services

Cloud boundary:
  Provider: GCP
  Regions: [us-central1]

Services:
  - Cloud Load Balancing | type: gateway  | spec: "Global HTTPS LB"
  - Cloud Run (API)      | type: compute  | spec: "min=2 max=20"
  - Cloud SQL Postgres   | type: database | spec: "PG15, db-custom-2-7680"
  - GCS (documents)      | type: storage  | spec: "Standard, CMEK"
  - Pub/Sub (events)     | type: queue    | spec: "Topic: order.events"

Connections:
  - External            → Cloud Load Balancing : public  | label "HTTPS"
  - Cloud Load Balancing → Cloud Run (API)     : internal
  - Cloud Run (API)     → Cloud SQL Postgres   : db      | label "TCP 5432"
  - Cloud Run (API)     → GCS (documents)      : db
  - Cloud Run (API)     → Pub/Sub (events)     : async   | label "PUBLISH"

Network zones:
  Public zone:  [Cloud Load Balancing]
  Private zone: [Cloud Run (API), Cloud SQL Postgres, GCS (documents), Pub/Sub (events)]
```

## Layout pattern

- **Canvas:** 1660 x ~820. Add height for additional regions.
- **Cloud provider boundary:** large dashed outer rectangle (~x=60, y=100, w=1540, h=650). Label at top-left: provider name ALL-CAPS, 9px, `#9e9b95`, letter-spacing 2.
- **Region boundaries:** inner dashed rectangles for each cloud region. Same visual treatment as provider boundary but smaller.
- **Network zones:** use a lightly-filled rectangle (`fill="rgba(79,95,184,0.04)"`) for private zone inside the region.
- **External actors:** placed outside the cloud boundary (top or bottom).

## Icon construction patterns

Each service is rendered as a **labeled card with a type-specific icon** in the upper-left. Use these SVG constructions:

### Database / cylinder icon (at icon group origin 0,0, fits in a ~32x40 space)
```xml
<ellipse cx="16" cy="8"  rx="16" ry="5" fill="currentColor"/>
<rect    x="0"  y="8"   width="32" height="26" fill="currentColor"/>
<ellipse cx="16" cy="34" rx="16" ry="5" fill="currentColor"/>
<ellipse cx="16" cy="8"  rx="16" ry="5" fill="rgba(255,255,255,0.15)"/>
```
Use for: Cloud SQL, Redis, any relational or key-value store.
Fill with `sandboxGrad` color for postgres; `harnessGrad` color for cache/Redis.

### Queue / message bus icon (at origin 0,0, fits in ~36x28 space)
```xml
<rect x="0"  y="4"  width="36" height="20" rx="3" fill="currentColor"/>
<rect x="0"  y="4"  width="8"  height="20" rx="3" fill="rgba(0,0,0,0.20)"/>
<rect x="28" y="4"  width="8"  height="20" rx="3" fill="rgba(0,0,0,0.20)"/>
```
Use for: Pub/Sub, SQS, Kafka, RabbitMQ.

### Storage bucket icon (at origin 0,0, fits in ~32x36 space)
```xml
<path d="M4,10 L0,36 L32,36 L28,10 Z" fill="currentColor"/>
<ellipse cx="16" cy="10" rx="16" ry="5" fill="currentColor"/>
<ellipse cx="16" cy="10" rx="16" ry="5" fill="rgba(255,255,255,0.15)"/>
```
Use for: GCS, S3, Azure Blob.

### Cloud shape (at origin 0,0, fits in ~48x32 space)
```xml
<circle cx="12" cy="20" r="12" fill="currentColor"/>
<circle cx="24" cy="14" r="16" fill="currentColor"/>
<circle cx="38" cy="20" r="12" fill="currentColor"/>
<rect   x="12"  y="20" width="26" height="14" fill="currentColor"/>
```
Use for: cloud provider label, CDN, external cloud services.

### Service / compute box (at origin 0,0, fits in ~32x28 space)
```xml
<rect x="0"  y="0"  width="32" height="28" rx="4" fill="currentColor"/>
<rect x="4"  y="6"  width="24" height="3"  rx="1" fill="rgba(255,255,255,0.3)"/>
<rect x="4"  y="12" width="16" height="3"  rx="1" fill="rgba(255,255,255,0.3)"/>
<rect x="4"  y="18" width="20" height="3"  rx="1" fill="rgba(255,255,255,0.3)"/>
```
Use for: Cloud Run, EC2, containers, Lambda functions.

### Load balancer icon (at origin 0,0, fits in ~32x32 space)
```xml
<circle cx="16" cy="16" r="15" fill="currentColor" stroke="rgba(255,255,255,0.2)" stroke-width="1"/>
<line x1="16" y1="4"  x2="8"  y2="24" stroke="rgba(255,255,255,0.6)" stroke-width="2"/>
<line x1="16" y1="4"  x2="24" y2="24" stroke="rgba(255,255,255,0.6)" stroke-width="2"/>
<line x1="16" y1="4"  x2="16" y2="28" stroke="rgba(255,255,255,0.6)" stroke-width="2"/>
```
Use for: Cloud Load Balancing, ALB, Nginx, Cloudflare.

## Service card design

Each service gets a card with:
- Width: 200-260px depending on content
- Height: ~90px (icon + name + spec line + optional tag)
- Fill: mapped by type:
  - compute (Cloud Run, containers): `mainGrad` dark
  - database (SQL, Postgres): `sandboxGrad` deep blue
  - cache (Redis, Memcached): `harnessGrad` green
  - queue (Pub/Sub, SQS): `researchGrad` slate
  - storage (GCS, S3): `artifactGrad` warm brown
  - gateway/CDN: light card, white fill
  - external: light card, dashed border
- Icon in upper-left at 24px from edges
- Service name: 13px weight 600, white (dark cards) or `#1a1a18` (light)
- Spec line: 10px, dimmer color

## Connections (network traffic)

- **Public internet traffic:** solid `#4f5fb8`, stroke-width 2, `arrowAccent`
- **Internal service-to-service:** solid `#9e9b95`, stroke-width 1.5, `arrowGrey`
- **Database reads/writes:** dashed `#6b7280`, stroke-dasharray "4,3", `arrowGrey`
- **Event / async:** dashed `#4f5fb8`, stroke-dasharray "6,4", `arrowAccentSm`
- Label connections only when the protocol or port is architecturally significant (HTTPS, gRPC, TCP 5432). Omit obvious internal calls.

## Animations

- `live-dot` pulse on the primary compute service (the API or main worker)
- One set of motion-path dots on the highest-traffic path (e.g. user request to load balancer to API)
- Nothing else. Infrastructure diagrams are reference documents, not demos.

## Common pitfalls

- Drawing every network connection. Show only the architecturally significant paths; a full mesh is unreadable.
- Equal-size cards for a 2-node Redis and a 20-instance Cloud Run cluster. Size cards to reflect relative importance.
- Forgetting the network zone boundary. Without it the reader can't tell what's internet-facing vs. internal.
- Leaving external dependencies off the diagram. Auth, payment, email — any third-party service the system depends on should appear outside the cloud boundary with a labeled connection.
