## Stance

We have converged on the material recommendation: **C#/.NET #1, Go #2, Java #3, Kotlin #4, TypeScript #5, Rust #6, Python #7**. [U] I accept Claude’s corrections on unsupported quantitative claims, Kotlin’s weaker MCP status, nuanced OpenTelemetry status, Rust above Python, Java 2.1 as **Adequate-Strong** rather than fully Strong, Go 2.3 as **Adequate** with context, Go 2.4 as **Strong**, and the more precise C# type-system wording. [U] The final plan should not use fragile package-download/version claims unless directly sourced; it should rely on the official MCP SDK page for current tier labels, which lists TypeScript/Python/C#/Go as Tier 1, Java/Rust as Tier 2, and Kotlin as TBD. [V] ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/sdk))

## Status

STATUS: AGREED  
RAISED_THIS_TURN: []  
ADDRESSED_THIS_TURN: []  
RESOLVED_THIS_TURN: [Q-plan-g-01, Q-plan-g-02, D-plan-g-01, D-plan-g-02, D-plan-g-03, D-plan-g-04, D-plan-g-05]  
ACKNOWLEDGED_THIS_TURN: []  
WITHDRAWN_THIS_TURN: []  
OPEN_QUESTIONS: 0  
OPEN_DISAGREEMENTS: 0  
ADDRESSED_QUESTIONS: 0  
ADDRESSED_DISAGREEMENTS: 0

## Addressing items raised against me

No open Claude-raised items remain for me to address. [U] I accept the practical outcomes of Claude’s resolved items: Kotlin’s MCP position is weaker than Java’s, Go 2.3 should be scored Adequate, Java 2.1 should be scored Adequate-Strong, Kotlin JVM can use the Java OpenTelemetry SDK posture in practice, and Go 2.4 should be Strong despite OpenTelemetry logs being Beta. [U] The official OpenTelemetry status table supports the underlying nuance: .NET and Java are Stable across traces/metrics/logs, Go is Stable/Stable/Beta, JavaScript and Python logs are Development, Kotlin-specific SDK status is Development across signals, and Rust is Beta across signals. [V] ([opentelemetry.io](https://opentelemetry.io/status/))

## Ratifying my own items

### RESOLVE Q-plan-g-01

reason: |
  I accept Claude’s response. The final document should remove unsupported quantitative MCP claims such as exact npm download/dependent counts and avoid “stable/production-ready” wording unless directly supported. The official MCP SDK page is sufficient for the final document’s Tier 1/Tier 2 nuance: TypeScript, Python, C#, and Go are Tier 1; Java and Rust are Tier 2; Kotlin is listed as TBD. [V] This preserves the intended conclusion without brittle ecosystem statistics. ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/sdk))

### RESOLVE Q-plan-g-02

reason: |
  I accept Claude’s concession. The Python typing survey percentages and Pyright conformance percentage should be removed because they were not verified this run. [U] Python can still be scored Weak on 2.1 using structural reasoning: optional typing, dynamic runtime semantics, and weaker large-refactor guarantees are enough under the brief’s criteria. [U]

### RESOLVE D-plan-g-01

reason: |
  I accept Claude’s revised ranking of Rust above Python. Since 2.1 is highest-weight, Rust’s iteration-velocity penalty should suppress it below TypeScript but not below Python’s Weak 2.1 score. [U] The final ranking should therefore place Rust #6 and Python #7. [U]

### RESOLVE D-plan-g-02

reason: |
  I accept Claude’s revised Java > Kotlin ordering. The official MCP SDK page currently lists Java as Tier 2 and Kotlin as TBD, while the tiering system defines Tier 2 as actively maintained and working toward full protocol support; that makes Java’s MCP position stronger than Kotlin’s for this decision. [V] Combined with Java’s simpler mainstream backend convention space, Java #3 and Kotlin #4 is the better final ordering. ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/sdk))

### RESOLVE D-plan-g-03

reason: |
  I accept the compromise: Go 2.3 = Adequate, not Strong, with an explicit context note. My objection was that document parsing may be less load-bearing because the document-AI provider does the heavy lifting. [U] Claude’s counterpoint is stronger for relative ecosystem scoring: Go has usable libraries for PDF, MIME detection, JSON Schema, and jobs, but its ecosystem is thinner than C#/.NET, JVM, and Python for the full 2.3 bundle. [U] The final document should say this gap narrows if the service performs only MIME/file-size validation before handing documents to the AI provider. [U]

### RESOLVE D-plan-g-04

reason: |
  I accept Claude’s nuanced OTel treatment and withdraw the objection to Go 2.4 = Strong. The final document should not say all seven candidates have equally mature OpenTelemetry support. [U] It should use a per-language nuance table: .NET and Java Stable across traces/metrics/logs; Go Stable/Stable/Beta; JavaScript and Python logs Development; Kotlin-specific SDK Development but Kotlin JVM can use Java OTel patterns; Rust Beta across signals. [V] This supports .NET/Java on pure OTel maturity, but Go remains Strong on 2.4 because startup, memory footprint, and operational simplicity dominate for this service. [U] ([opentelemetry.io](https://opentelemetry.io/status/))

### RESOLVE D-plan-g-05

reason: |
  I accept the rewording. The final document should not describe C# as “nominally sound” without qualification. [U] The defensible wording is: C# offers strong practical static typing, nullable-flow analysis, pattern matching, records, mature compiler feedback, and Roslyn-powered refactoring. [U] That is sufficient for C# to win 2.1 without overstating formal type-soundness or first-class ADT support. [U]

## New items I'm raising

No new items. [U]

## Phase artifact

### AGREED_PLAN

#### Sections

1. Title: Executive summary  
   Key claims:
   - Recommend **C#/.NET** as the single backend language for the Document Verification Service modular monolith. [U]
   - Rank candidates: **1 C#/.NET, 2 Go, 3 Java, 4 Kotlin, 5 TypeScript/Node.js, 6 Rust, 7 Python**. [U]
   - Decision confidence: **MEDIUM-HIGH**, because public ecosystem/runtime evidence is strong enough for a recommendation, but internal platform catalog details, team experience, and an AI-agent pilot could still shift confidence. [U]

2. Title: Methodology  
   Key claims:
   - Apply the brief’s three-tier framework in order: Tier 1 hard pass/fail, Tier 2 qualitative scoring, Tier 3 tie-breakers only if Tier 2 does not decide. [U]
   - Use **Strong / Adequate-Strong / Adequate / Weak / Poor** scoring bands where needed. [U]
   - Treat **2.1 AI-coding-automation fitness** as the highest-weight and load-bearing criterion. [U]
   - Normalize candidates at language/runtime level: Go, Rust/Tokio, Python/CPython asyncio, TypeScript/Node.js LTS, C#/.NET, Kotlin/JVM, Java/JVM. [U]

3. Title: Tier 1 hard-constraint pass/fail  
   Key claims:
   - All seven candidates provisionally pass Tier 1, subject to internal platform catalog confirmation. [U]
   - Platform support is treated as provisional PASS for all because containerized deployment is assumed, but the company’s private vetted catalog remains authoritative. [U]
   - MCP Tier 1.4 passes for all, but not equally: official MCP SDK page lists TypeScript/Python/C#/Go as Tier 1, Java/Rust as Tier 2, and Kotlin as TBD. [V] ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/sdk))
   - The MCP tiering system defines Tier 1 as fully supported, Tier 2 as actively maintained and working toward full support, and Tier 3 as experimental/partial/specialized. [V] ([modelcontextprotocol.io](https://modelcontextprotocol.io/community/sdk-tiers))
   - RLS-aware Postgres pooling is treated as a design-rule requirement across candidates, not a language eliminator. [U]

4. Title: Tier 2 scoring summary  
   Key claims:
   - C# wins Tier 2 because it is Strong on 2.1 and at least Strong/Adequate-Strong elsewhere. [U]
   - Go is the closest challenger because it is Strong on concurrency and operations and excellent on convention uniformity, but weaker than C# on type-system depth and weaker than C#/JVM/Python on some ecosystem breadth. [U]
   - Java ranks above Kotlin because JVM-level strengths are shared, Java has a stronger MCP tier position, and Java’s mainstream service conventions are simpler despite annotation/proxy implicitness. [U]
   - Kotlin remains strong as a language but is penalized by weaker MCP maturity and greater convention complexity. [U]
   - TypeScript passes comfortably but is held back by runtime type erasure, framework fragmentation, and boundary-validation discipline. [U]
   - Rust ranks above Python but below TypeScript because its static-safety and ops strengths are offset by AI-agent iteration friction. [U]
   - Python ranks last because its Weak 2.1 score is decisive under the brief’s weighting despite strong ecosystem breadth. [U]

5. Title: 2.1 AI-coding-automation fitness  
   Key claims:
   - Disaggregate 2.1 into: type-system depth, convention uniformity, refactoring/tooling safety, determinism/testability, and LLM comprehensibility. [U]
   - C# = **Strong**: strong practical static typing, nullable-flow analysis, records/pattern matching, mature compiler feedback, and Roslyn refactoring. [U]
   - Go = **Adequate-Strong**: best convention uniformity and simple service code, but less expressive domain modeling than C#/JVM/Rust/strict TypeScript. [U]
   - Java = **Adequate-Strong**: strong modern Java features and tooling, but annotation/proxy-heavy Spring semantics are an implicit-behavior penalty. [U]
   - Kotlin = **Adequate-Strong**: strong language type system, but more stylistic/concurrency-framework variation and weaker MCP maturity. [U]
   - TypeScript = **Adequate**: rich static type expressiveness under strict mode, but runtime erasure and Node ecosystem fragmentation reduce refactoring confidence. [U]
   - Rust = **Adequate**: excellent type system, but compile/lifetime friction slows AI-agent iteration. [U]
   - Python = **Weak**: optional typing and dynamic semantics impose the highest review burden. [U]

6. Title: 2.2 concurrency model fit  
   Key claims:
   - C#, Go, Java, Kotlin, and Rust score Strong for the API/worker/outbox/SKIP LOCKED workload. [U]
   - TypeScript and Python score Adequate because async I/O fits the workload but process/thread/runtime constraints add more discipline. [U]
   - No candidate is eliminated by concurrency. [U]

7. Title: 2.3 ecosystem maturity  
   Key claims:
   - C#/.NET, Java/JVM, Kotlin/JVM, and Python score Strong on broad ecosystem coverage. [U]
   - TypeScript scores Adequate-Strong. [U]
   - Go scores Adequate, with a context note that the gap narrows if document intake is mostly MIME/file-size validation plus AI-provider handoff. [U]
   - Rust scores Adequate because it has capable libraries but thinner production ecosystem depth for this service’s full stack. [U]

8. Title: 2.4 observability and operational fit  
   Key claims:
   - Use nuanced OTel status rather than a blanket statement. [U]
   - OpenTelemetry’s status page lists .NET and Java as Stable for traces, metrics, and logs; Go as Stable/Stable/Beta; JavaScript and Python with Development logs; Kotlin-specific SDK as Development across signals; and Rust as Beta across traces/metrics/logs. [V] ([opentelemetry.io](https://opentelemetry.io/status/))
   - Go scores Strong overall on 2.4 despite Beta logs because memory footprint, startup, and operational simplicity dominate. [U]
   - C# scores Strong/Adequate-Strong depending on AOT/min-replica assumptions. [U]
   - JVM candidates carry a conditional cold-start/memory penalty unless min replicas ≥1 or native-image strategies are confirmed. [U]

9. Title: Final ranking and rationale  
   Key claims:
   - **#1 C#/.NET**: best balance of 2.1, mature backend ecosystem, async/concurrency fit, and operational support. [U]
   - **#2 Go**: closest challenger; best convention uniformity and operational profile, but weaker type-system depth and thinner ecosystem breadth. [U]
   - **#3 Java**: strong JVM ecosystem and modern language features; above Kotlin due to MCP maturity and simpler convention space. [U]
   - **#4 Kotlin**: strong type system and JVM ecosystem, but weaker MCP tier status and more convention complexity. [U]
   - **#5 TypeScript/Node.js**: good MCP and full-stack convenience, but Tier 3 frontend alignment cannot override 2.1 concerns. [U]
   - **#6 Rust**: technically strong but too costly for AI-agent iteration to rank higher. [U]
   - **#7 Python**: ecosystem strong, but 2.1 weakness is decisive. [U]

10. Title: Decision confidence  
    Key claims:
    - Confidence: **MEDIUM-HIGH**. [U]
    - One-sentence reason: C# wins the highest-weight criterion while remaining strong enough on concurrency, ecosystem, and operations. [U]
    - Single evidence item most likely to shift confidence: an internal AI-agent implementation pilot comparing C# and Go on a representative slice: tenant-scoped Postgres/RLS, SKIP LOCKED worker, MCP tool, outbox event, and OTel traces. [U]

11. Title: Flip criteria  
    Key claims:
    - Go overtakes C# if an internal pilot shows materially fewer review defects and faster end-to-end AI-agent iteration in Go despite weaker type modeling. [U]
    - Java/Kotlin move up if min replicas ≥1 eliminate JVM cold-start risk and internal production expertise strongly favors JVM. [U]
    - Kotlin overtakes Java only if its MCP maturity reaches at least Java’s tier/status and the team values Kotlin’s type-system expressiveness over Java’s simpler convention space. [U]
    - TypeScript moves up only if shared frontend/backend schemas become a hard business constraint and runtime schema validation is standardized. [U]
    - Rust moves up only if memory/security/native-processing constraints become load-bearing. [U]
    - Python moves up only if the backend becomes primarily Python-native document/AI orchestration and 2.1 is relaxed. [U]

12. Title: Final-surfaced disagreements  
    Key claims:
    - No unresolved recommendation-changing disagreements remain. [U]
    - Include a short note that Go vs C# is the main close call: Go wins convention uniformity; C# wins practical static typing and refactoring safety. [U]
    - Include a short note that Java vs Kotlin was resolved in favor of Java due to MCP maturity and convention simplicity, despite Kotlin’s stronger language-level type expressiveness. [U]

13. Title: Sources  
    Key claims:
    - Cite official MCP SDK page and SDK tiering system. [V]
    - Cite official OpenTelemetry status page. [V]
    - Cite only sources actually retrieved/verified; remove unsupported statistics and blog-only claims unless clearly marked non-authoritative. [U]

#### Carry-forward items (from phase 2)

- [Q-plan-g-01] resolved: Unsupported specific MCP maturity metrics should be removed; final document uses conservative official-tier language — appears in Tier 1 MCP notes and Sources.
- [Q-plan-g-02] resolved: Unsupported Python typing statistics removed; final document uses structural 2.1 reasoning — appears in Python 2.1 narrative.
- [D-plan-g-01] resolved: Rust ranks above Python — appears in final ranking and Rust/Python narratives.
- [D-plan-g-02] resolved: Java ranks above Kotlin — appears in final ranking, Tier 1 MCP nuance, and Java/Kotlin narratives.
- [D-plan-g-03] resolved: Go 2.3 = Adequate with context note — appears in 2.3 scoring and Go narrative.
- [D-plan-g-04] resolved: OpenTelemetry support is nuanced by language/status, not equal — appears in 2.4 scoring.
- [D-plan-g-05] resolved: C# wording changed from “nominally sound” to “strong practical static typing” — appears in 2.1 and C# narrative.
- [D-plan-c-01] resolved: Kotlin MCP status is weaker than Java’s; Java > Kotlin — appears in Tier 1 MCP notes and final ranking.
- [D-plan-c-02] resolved: Go 2.3 remains Adequate, with context note — appears in 2.3 scoring.
- [D-plan-c-03] resolved: Java 2.1 = Adequate-Strong, not equal to C# — appears in 2.1 scoring.
- [Q-plan-c-01] resolved: Kotlin-specific OTel is Development, but Kotlin JVM can use Java OTel patterns; score Kotlin 2.4 as Adequate — appears in 2.4 scoring.
- [Q-plan-c-02] resolved: Go OTel logs Beta but Go 2.4 overall Strong — appears in 2.4 scoring.

#### Drafter

DRAFTER: claude