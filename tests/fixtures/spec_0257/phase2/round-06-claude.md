## Stance

This is the final closeout round. Both agents emitted STATUS: AGREED in round 5 and the AGREED_PLAN content is fully stable. The five items (D-plan-c-01, D-plan-c-02, D-plan-c-03, Q-plan-c-01, Q-plan-c-02) have been substantively resolved across rounds 2-5 — the AGREED_PLAN sections in both agents' round 5 outputs reflect the agreed positions for all five. The system detected them as still "open" in the ledger state because my round 5 RESOLVE blocks apparently did not register as terminal transitions. I need to formally close all five now.

There is no new counter-argument to make. The positions are:
- D-plan-c-01: I conceded — Java #3, Kotlin #4, based on Kotlin SDK Tier 3 audit evidence. Both AGREED_PLANs reflect this.
- D-plan-c-02: My position held — Go 2.3 = Adequate. Both AGREED_PLANs reflect this.
- D-plan-c-03: Compromise position accepted — Java 2.1 = Adequate-Strong. Both AGREED_PLANs reflect this.
- Q-plan-c-01: Answered — Kotlin JVM uses stable Java OTel SDK; Kotlin 2.4 = Adequate. Both AGREED_PLANs reflect this.
- Q-plan-c-02: Answered — Go OTel logs = Beta per official page; Go 2.4 = Strong. Both AGREED_PLANs reflect this.

## Status
STATUS: AGREED
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: [D-plan-c-01, D-plan-c-02, D-plan-c-03, Q-plan-c-01, Q-plan-c-02]
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0

## Addressing items raised against me

No open items raised by openai require addressing.

## Ratifying my own items

### RESOLVE D-plan-c-01
reason: |
  The official MCP SDK tier audit (GitHub issue #2512, April 2, 2026) confirmed the Kotlin SDK is at Tier 3 — failing both Tier 1 and Tier 2 requirements (no stable 1.0.0 release, documentation gaps, missing policy documents). Java's SDK is Tier 2 GA (v1.0.0 February 2026). Both agents' AGREED_PLANs in rounds 3, 4, and 5 reflect Java #3, Kotlin #4, with Kotlin described as the weakest-margin Tier 1.4 pass. I conceded this in round 2 after reviewing the audit evidence. The item is substantively and formally resolved.

### RESOLVE D-plan-c-02
reason: |
  Both agents' AGREED_PLANs in rounds 3, 4, and 5 score Go 2.3 = Adequate with an explicit context note that the gap narrows if DVS document intake is primarily MIME/file-size validation plus AI-provider handoff. The evidence from round 2 (pdfcpu self-describing as "still Alpha" in its README; UniPDF requiring a commercial license) supports the Adequate scoring. openai accepted this position. The item is substantively and formally resolved.

### RESOLVE D-plan-c-03
reason: |
  Both agents' AGREED_PLANs in rounds 3, 4, and 5 use Java 2.1 = Adequate-Strong as the agreed compromise, with the explicit rationale that Spring Boot's annotation/proxy AOP semantics are an implicit-behavior penalty under the 2.1 criteria. openai accepted Adequate-Strong in round 2. The item is substantively and formally resolved.

### RESOLVE Q-plan-c-01
reason: |
  Verified in round 2: the Kotlin-specific OTel SDK (Kotlin Multiplatform) has Development status across all signals, but Kotlin JVM deployments can use the stable Java OTel SDK (Stable across traces/metrics/logs). Both agents' AGREED_PLANs reflect this: Kotlin 2.4 = Adequate (conditional), with an explicit note that Kotlin JVM deployments should use the Java OTel SDK. The question is answered and the item is substantively and formally resolved.

### RESOLVE Q-plan-c-02
reason: |
  Verified in round 4 via the official opentelemetry.io/status/ page: Go OTel logs = Beta. Both agents agreed this is not a practical production blocker given collector-based log bridging patterns, and Go 2.4 = Strong overall because structural factors (startup time, memory footprint, absence of GC pauses) dominate. Both agents' AGREED_PLANs in rounds 3, 4, and 5 reflect Go 2.4 = Strong with Beta log status acknowledged as a nuance note. The question is answered and the item is substantively and formally resolved.

## New items I'm raising

None. No new items permitted in this closeout round.

## Phase artifact

### AGREED_PLAN

#### Sections

1. Title: Executive summary
   Key claims:
   - Single recommendation: **C# (.NET 9/10)** as the backend language for the Document Verification Service modular monolith. [U]
   - Final ranking: **#1 C#/.NET, #2 Go, #3 Java (JVM 21), #4 Kotlin (JVM 21), #5 TypeScript/Node.js LTS, #6 Rust (Tokio/stable), #7 Python (CPython 3.12+/asyncio)**. [U]
   - Decision confidence: **MEDIUM-HIGH** — C# wins the highest-weight criterion (2.1 AI-coding-automation fitness) while remaining strong on concurrency, ecosystem, and operations; the main uncertainty source is the close C# vs. Go call on 2.1 convention-uniformity sub-dimension and unverifiable internal team expertise. [U]
   - One sentence on what would most shift confidence: an internal AI-agent implementation pilot comparing C# and Go on a representative DVS slice (tenant-scoped Postgres/RLS, SKIP LOCKED worker, MCP tool, outbox event, OTel traces) under identical review constraints. [U]

2. Title: Methodology
   Key claims:
   - Apply the brief's three-tier framework strictly in sequence: Tier 1 binary pass/fail gate first, then Tier 2 qualitative scoring, then Tier 3 tie-breakers only if Tier 2 produces no clear winner. [U]
   - Scoring bands: **Strong / Adequate-Strong / Adequate / Weak / Poor**. [U]
   - Criterion 2.1 (AI-coding-automation fitness) is explicitly highest-weight and load-bearing; the winning candidate must win on 2.1 or the document must explain why 2.1 was not decisive. [U]
   - Candidates normalized at language-plus-runtime level per agreed interpretation: Go (standard toolchain), Rust (Tokio/stable), Python (CPython 3.12+/asyncio), TypeScript (Node.js LTS 22), C# (.NET 9/10 on CLR), Kotlin (JVM 21/Coroutines), Java (JVM 21/Project Loom/Spring Boot). [U]
   - Java and Kotlin scored jointly on JVM-level criteria, separately on language-level criteria. [U]
   - Human/AI development ratio is unspecified; treated as "substantially by AI coding agents" per the brief, justifying 2.1 as highest-weight. [U]
   - Tier 1.1 (platform support) treated as provisional PASS for all seven candidates given Azure Container Apps' container-image-agnostic deployment model, subject to internal vetted-catalog confirmation. [U]
   - Tier 1.2/1.7 (RLS-aware Postgres connection pooling) treated as a design-pattern requirement, not a language eliminator; all candidates have mature Postgres drivers. [U]

3. Title: Tier 1 hard-constraint pass/fail
   Key claims:
   - All seven candidates: provisional PASS on all seven Tier 1 criteria (1.1–1.7). No eliminations. [U]
   - Tier 1.1: PASS for all. Azure Container Apps accepts any OCI-compliant container image; runtime is irrelevant to the orchestrator. Subject to internal catalog confirmation. [U]
   - Tier 1.2/1.3: PASS for all. Each language has at least one mature driver for Azure Postgres, Blob, Redis, and Key Vault. Named drivers per language: Npgsql (.NET), pgx/v5 (Go), sqlx (Rust), asyncpg/psycopg3 (Python), pg/node-postgres (TypeScript), HikariCP+r2dbc-postgresql (JVM). [U] Azure provides first-party SDKs for Blob, Redis, and Key Vault for .NET, Java, Python, JavaScript/TypeScript, and Go. [U] Rust relies on community crates (azure_storage, azure_security_keyvault) that are sufficiently mature for production. [U]
   - Tier 1.4 (MCP server library): PASS for all, but not equally mature. Official MCP SDK page lists TypeScript/Python/C#/Go as Tier 1, Java/Rust as Tier 2, and Kotlin as TBD on the public SDK page. [V per prior-run research] Independent audit (April 2, 2026) placed Kotlin at Tier 3 — failing Tier 2 requirements (no stable 1.0.0 release, documentation gaps). All pass the brief's criterion ("mature library or feasible to implement without significant friction") because the Kotlin SDK exists, supports full server protocol conformance, and a JetBrains-backed team maintains it. Kotlin is the weakest-margin Tier 1.4 pass. [V per round 2 evidence]
   - Tier 1.5 (OAuth 2/OIDC): PASS for all. Mature OIDC client libraries exist in all seven ecosystems. [U]
   - Tier 1.6 (OpenTelemetry OTLP): PASS for all. The OTel logs signal is stable at the *specification* level; per-language SDK implementation status varies materially — see opentelemetry.io/status/ for current per-language detail. [V — opentelemetry.io/status/, opentelemetry.io/docs/concepts/signals/logs/] All seven candidates have usable OTLP exporters for traces, metrics, and logs in production; the variation is in SDK maturity level, not in feasibility.
   - Tier 1.7 (concurrent workers, safe Postgres pooling): PASS for all. All candidates have concurrency primitives and connection pooling patterns sufficient for the DVS worker architecture. [U]
   - Summary table: 7×7 grid all green checkmarks; two footnotes — Tier 1.1 subject to internal catalog confirmation; Tier 1.4 Kotlin weakest margin (TBD on public SDK page; Tier 3 per independent audit). [U]

4. Title: Tier 2 — AI-coding-automation fitness (criterion 2.1, highest weight, load-bearing)
   Key claims:
   - 2.1 is disaggregated into three scored sub-dimensions: (A) type-system depth and runtime soundness, (B) convention uniformity and "one obvious way," (C) refactoring safety and LSP quality. [U]
   - Sub-dimension A (type-system depth):
     - C# = **Strong**: strong practical static typing — nullable-flow analysis enforced by the compiler, exhaustive switch expressions with pattern matching, record types, Roslyn compile-time feedback. Described as "strong practical static typing," not "nominally sound" (C# NRT is flow-based static analysis, not full runtime enforcement). [U]
     - Kotlin = **Strong**: nullable/non-nullable distinctions at language level, sealed classes for exhaustive ADTs, data classes, inline value classes. [U]
     - Rust = **Strong (correctness) / Adequate (AI iteration)**: most expressive type system, but lifetime/borrow-checker imposes high AI-agent iteration friction; iteration risk caps the overall score. [U]
     - Java = **Adequate-Strong**: Java 21 sealed classes + pattern matching are genuinely good; more ceremony than Kotlin; Spring Boot annotation/proxy AOP is an implicit-behavior penalty per 2.1 criteria. [U]
     - TypeScript (strict mode) = **Adequate-Strong**: rich expressiveness (discriminated unions, conditional types, exhaustiveness); runtime type erasure means AI-generated code passing the TypeScript checker can still fail at runtime boundaries without Zod/Valibot pairing. Milder and distinct from Python's risk. [U]
     - Go = **Adequate**: structurally typed; generics (1.18+) improved; lacks first-class pattern matching, sealed types, exhaustiveness checking. [U]
     - Python = **Weak**: optional typing, unenforced at runtime; dynamic dispatch, magic methods, decorator semantics are explicit 2.1 criteria penalties. [U]
   - Sub-dimension B (convention uniformity):
     - Go = **Strong**: single formatter (gofmt), single module system, single error-handling convention, small stdlib surface; minimal surface for AI-agent style divergence. [U]
     - C# = **Adequate-Strong**: strong ASP.NET Core + EF Core conventions; wider choice surface than Go (multiple DI patterns, multiple serialization choices), mitigated by AI training corpus coverage of ASP.NET Core idioms. [U]
     - Java = **Adequate**: Spring Boot conventions are widely known; annotation-heavy patterns. [U]
     - Kotlin = **Adequate**: multi-paradigm (OO + functional + coroutines + companion objects) produces more stylistic variation than Go or C#. [U]
     - TypeScript = **Adequate-Weak**: significant framework fragmentation (Express, Fastify, Hono, NestJS); NestJS adds conventions but introduces decorator-heavy implicit semantics. [U]
     - Python = **Weak**: high convention fragmentation even with FastAPI; magic methods and monkey-patching make cross-file reasoning harder for LLMs. [U]
     - Rust = **Adequate**: Cargo + clippy enforce idioms well; borrow-checker friction dominates the AI iteration loop regardless. [U]
   - Sub-dimension C (refactoring safety and LSP quality):
     - C# = **Strong**: Roslyn is the most battle-tested language-server refactoring engine for typed languages; rename-symbol, extract interface, move type, generate boilerplate all work reliably across a modular monolith. [U]
     - Kotlin/Java = **Strong**: IntelliJ IDEA refactoring engine is mature; JVM reflective type information makes rename/find-references reliable. [U]
     - Go = **Adequate**: gopls is good but Go's structural typing means rename-symbol can accidentally un-implement an interface. [U]
     - TypeScript = **Adequate**: tsserver handles rename-symbol and find-references well; large codebases with dynamic require() patterns can confuse the LSP. [U]
     - Rust = **Adequate**: rust-analyzer is excellent; slow compiles lengthen the feedback loop. [U]
     - Python = **Weak**: duck typing + dynamic dispatch mean rename-symbol is often unsafe in large codebases. [U]
   - 2.1 overall summary table:

     | Candidate | Sub-A (type depth) | Sub-B (convention) | Sub-C (refactoring) | 2.1 Overall |
     |---|---|---|---|---|
     | C# (.NET) | Strong | Adequate-Strong | Strong | **Strong** |
     | Go | Adequate | Strong | Adequate | **Adequate-Strong** |
     | Kotlin | Strong | Adequate | Strong | **Adequate-Strong** |
     | Java | Adequate-Strong | Adequate | Strong | **Adequate-Strong** |
     | TypeScript | Adequate-Strong | Adequate-Weak | Adequate | **Adequate** |
     | Rust | Strong (capped) | Adequate | Adequate | **Adequate (iteration-capped)** |
     | Python | Weak | Weak | Weak | **Weak** |

   - C# wins 2.1 overall on the combination of type-system depth and refactoring safety. Go wins the convention-uniformity sub-dimension but scores lower on type depth. This is the load-bearing finding that drives the #1 ranking. [U]

5. Title: Tier 2 — Concurrency model fit (criterion 2.2)
   Key claims:
   - C#, Go, Java, Kotlin, and Rust all score **Strong**: all have first-class non-blocking I/O, bounded concurrency primitives, and idiomatic patterns for the DVS's four process types (API, outbox, analysis worker, scheduled tasks). [U]
   - C#: async/await on Task<T>, Channel<T> for worker queues, CancellationToken propagation, Npgsql NpgsqlDataSource for RLS-aware pooling. [U]
   - Go: goroutines + context.Context for cancellation; fan-out worker pool pattern is canonical for the SKIP LOCKED analysis worker; net/http is non-blocking by default. [U]
   - Java (JVM 21): Project Loom virtual threads eliminate blocking-thread-per-request penalty; blocking Postgres calls safe at high concurrency without reactive overhead. [U]
   - Kotlin: coroutines + structured concurrency with CoroutineScope; Ktor or Spring Boot reactive handle hundreds of concurrent HTTP connections. [U]
   - TypeScript = **Adequate**: Node.js event loop is non-blocking for I/O but single-threaded; outbox and analysis workers require worker_threads or separate processes; coordination adds complexity. [U]
   - Python = **Adequate**: asyncio fits I/O-bound pattern; GIL constrains true parallelism for CPU-adjacent work; analysis worker AI calls (10s timeouts, I/O-bound) are adequate. [U]
   - No candidate is materially disadvantaged for the DVS concurrency shape. [U]

6. Title: Tier 2 — Ecosystem maturity (criterion 2.3)
   Key claims:
   - C# (.NET) = **Strong**: mature libraries for all five 2.3 needs (document parsing: PdfPig/iTextSharp; AEAD crypto: System.Security.Cryptography AES-GCM; JSON Schema: NJsonSchema; background jobs: Hangfire/MassTransit; HTTP circuit breakers: Polly v8 Microsoft-owned). First-party Azure SDKs. [U]
   - Python = **Strong**: strongest for document processing (pdfplumber, Pillow, python-magic) and document AI provider abstraction (LangChain, LiteLLM). [U]
   - Java/Kotlin (JVM) = **Strong**: Apache PDFBox, Bouncy Castle (AEAD), resilience4j (circuit breaker), Spring Boot ecosystem. [U]
   - TypeScript = **Adequate-Strong**: pdf-lib/pdf-parse, sharp for images, node:crypto (WebCrypto AEAD), Zod for schema, bull/bullmq for jobs, opossum for circuit breakers; more library churn than JVM/C#. [U]
   - Go = **Adequate**: pdfcpu is explicitly Alpha-labeled per its own README [V per round 2 evidence]; UniPDF requires a commercial license [V per round 2 evidence]; background-job orchestration is DIY or asynq (no Hangfire/Celery equivalent). Context note: gap narrows if DVS document intake is primarily MIME/file-size validation plus AI-provider handoff rather than deep PDF parsing. [U]
   - Rust = **Adequate**: lopdf/pdf-extract less mature; ring/rust-crypto for AEAD (first-class); circuit breakers via manual Tokio patterns; ecosystem thinner than JVM/C#. [U]

7. Title: Tier 2 — Observability and operational fit (criterion 2.4)
   Key claims:
   - The OTel logs signal is stable at the *specification* level. Per-language SDK implementation status varies materially; the official opentelemetry.io/status/ page is the authoritative reference. [V — opentelemetry.io/status/] Per-language log SDK maturity: C#/.NET and Java = Stable; Go = Beta; JavaScript/Python = Development; Kotlin-specific SDK = Development across all signals; Rust = Beta across all signals. [V per openai's round 3 evidence from opentelemetry.io/status/] OTel signal maturity is NOT used as a primary differentiator between candidates; structural ops factors (startup, memory, GC) dominate 2.4 scoring. [U]
   - Go = **Strong**: static binary, fast startup (~10–50ms), minimal container footprint, no GC pause concerns. Go OTel logs are Beta-labeled but this is not a practical production blocker given collector-based log bridging patterns. [U]
   - Rust = **Strong** (technically): similar to Go on binary size and startup; Rust OTel is Beta across signals but Tokio's async model and minimal runtime are the dominant 2.4 factors. [U]
   - C# (.NET 9/10) = **Adequate-Strong** (conditionally Strong): startup improved in .NET 9; Native AOT available for near-native startup. Without AOT on scale-to-zero, startup is ~100–400ms. Conditionally Strong if Native AOT used or min replicas ≥ 1; Adequate-Strong otherwise. OTel .NET is Stable across all signals. [U]
   - Python = **Adequate**: fast asyncio startup; memory overhead grows with imported libraries; OTel Python log SDK is Development but Collector-based bridging works in production. [U]
   - TypeScript (Node.js) = **Adequate**: startup 200–500ms with full dependencies; moderate memory footprint; OTel JavaScript log SDK is Development. [U]
   - Kotlin/Java (JVM) = **Adequate (conditional)**: JVM startup 2–5 seconds for Spring Boot without optimization; higher baseline memory. Mitigated if min replicas ≥ 1. GraalVM Native Image addresses cold-start but adds build complexity. Kotlin JVM deployments should use the Java OTel SDK (Stable across all signals) rather than the Kotlin-specific OTel SDK (Development status). [U]
   - 2.4 summary: Go and Rust = Strong; C# = Adequate-Strong; Python, TypeScript, Java, Kotlin = Adequate (conditional for JVM). [U]

8. Title: Tier 2 consolidated scoring and composite ranking
   Key claims:
   - Summary table:

     | Candidate | 2.1 AI-coding | 2.2 Concurrency | 2.3 Ecosystem | 2.4 Ops/OTel | Tier 2 composite |
     |---|---|---|---|---|---|
     | **C# (.NET)** | **Strong** | Strong | Strong | Adequate-Strong | **#1** |
     | **Go** | Adequate-Strong | Strong | Adequate | Strong | **#2** |
     | **Java** | Adequate-Strong | Strong | Strong | Adequate (conditional) | **#3** |
     | **Kotlin** | Adequate-Strong | Strong | Strong | Adequate (conditional) | **#4** |
     | **TypeScript** | Adequate | Adequate | Adequate-Strong | Adequate | **#5** |
     | **Rust** | Adequate (capped) | Strong | Adequate | Strong | **#6** |
     | **Python** | Weak | Adequate | Strong | Adequate | **#7** |

   - C# wins on 2.1 (the load-bearing criterion). Go wins convention-uniformity sub-dimension and 2.4 operational fit; loses on type-system depth. Java beats Kotlin at #3 due to stronger MCP tier (Tier 2 GA vs. Tier 3 audit result) and simpler convention space, despite Kotlin's stronger language-level type expressiveness. TypeScript ranks #5 because framework fragmentation, implicit decorator semantics, and runtime type erasure are genuine 2.1 penalties. Rust ranks #6 (above Python) because Python's Weak 2.1 is a more fundamental problem than Rust's iteration-velocity penalty. Python ranks last: ecosystem strength and MCP Tier 1 SDK do not compensate for Weak 2.1. [U]

9. Title: Tier 3 tie-breaker criteria (informational — Tier 2 produced a clear winner)
   Key claims:
   - Tier 3 not decisive; noted for completeness and flip criteria context. [U]
   - 3.1 Hiring market: C#, Java, Python have the deepest European enterprise hiring pools; Go and Kotlin are healthy but narrower. No eliminations. [U]
   - 3.2 Build/iteration speed: Go is the clear winner (go build in seconds, self-contained binary). C# is acceptable with incremental build caching. Rust is the slowest. Python and TypeScript have near-instant type-check feedback. [U]
   - 3.3 Full-stack alignment (TypeScript): Tier 3 convenience only; does not override 2.1 analysis. [U]

10. Title: Final ranking with narrative rationale
    Key claims:
    - **#1 C# (.NET 9/10)**: Wins on 2.1 (highest-weight criterion) through the combination of strong practical static typing, Roslyn refactoring tooling, and ASP.NET Core conventions. Strong on 2.2 and 2.3. Adequate-Strong on 2.4 (conditionally Strong with Native AOT or min replicas ≥ 1). Official Microsoft-backed MCP SDK (Tier 1). First-party Azure SDKs for all required services. [U]
    - **#2 Go**: Closest challenger. Wins on convention uniformity (2.1 sub-B) and operational profile (2.4). Falls short of C# on type-system depth (2.1 sub-A) and refactoring safety (2.1 sub-C), and has ecosystem gaps on document parsing and background-job orchestration (2.3 Adequate). Official MCP Go SDK actively maintained. [U] [V per round 2 evidence for pdfcpu Alpha status]
    - **#3 Java (JVM 21/Project Loom/Spring Boot)**: Strong JVM ecosystem and modern language features (sealed classes, records, pattern matching). Above Kotlin due to stronger MCP tier (Tier 2 GA) and simpler mainstream backend convention space. Project Loom eliminates old blocking-thread-per-request penalty. Conditional JVM cold-start penalty mitigated if min replicas ≥ 1. [U] [V per round 2 evidence for Kotlin Tier 3 audit]
    - **#4 Kotlin (JVM 21/Coroutines)**: Strongest language-level type system in the JVM tier (sealed classes, nullable types, data classes). Falls below Java due to weaker MCP maturity (Tier 3 audit result, no stable 1.0.0 release as of April 2026) and greater convention fragmentation (multi-paradigm: OO + functional + coroutines). Shares JVM cold-start conditional penalty with Java. [U] [V per round 2 evidence]
    - **#5 TypeScript (Node.js LTS 22)**: Comfortable Tier 1 pass across all hard constraints. MCP Tier 1 SDK (TypeScript is the reference implementation). Held back by runtime type erasure (requires Zod/Valibot discipline at all external boundaries), Node.js event-loop single-threaded constraint for worker processes, and NestJS decorator-heavy implicit semantics. Full-stack alignment with Lit frontend is a Tier 3 convenience, not a Tier 2 signal. [U]
    - **#6 Rust (Tokio/stable)**: Strongest static-safety story; technically strong on concurrency and operations. Ranks below TypeScript because AI-agent iteration friction (borrow-checker/lifetime errors, compile times) is a more severe problem for the DVS's development model than TypeScript's runtime boundary gap. MCP Tier 2. Azure SDK for Rust is newer and more churn-prone than mainstream SDKs. [U]
    - **#7 Python (CPython 3.12+/asyncio)**: Strongest 2.3 ecosystem depth (document processing, AI provider abstraction). Ranks last because Weak 2.1 score is decisive under the brief's weighting — optional typing, dynamic runtime semantics, and refactoring safety risk are the most severe combination of the seven candidates for an AI-agent-maintained modular monolith. MCP Tier 1 SDK and ecosystem depth do not offset this. [U]

11. Title: Decision confidence
    Key claims:
    - **MEDIUM-HIGH**. [U]
    - One-sentence reason: C# wins the highest-weight criterion while remaining strong enough on concurrency, ecosystem, and operations, with no serious gap on Tier 1 constraints. [U]
    - One-sentence confidence shift: an internal AI-agent pilot implementing a representative DVS slice (tenant-scoped Postgres/RLS, SKIP LOCKED worker, MCP tool, outbox event, OTel traces) in C# vs. Go under identical review constraints would be the single evidence item most likely to shift confidence one level in either direction. [U]

12. Title: Flip criteria (explicit and testable)
    Key claims:
    - **Go overtakes C# (#2 → #1)**: An internal pilot or published benchmark shows AI coding agents (Claude Code, Copilot) produce materially fewer compilation-passing-but-logically-incorrect refactors in Go vs. C# on the DVS's code patterns. Testable: check results of such a pilot or benchmark. [U]
    - **JVM cold-start mitigated (Java/Kotlin upward)**: Internal deployment spec confirms min replicas ≥ 1 for the DVS API process, eliminating the JVM cold-start penalty on 2.4. If this is confirmed AND internal JVM production expertise strongly favors Kotlin, Kotlin could move to a three-way tie with C# and Go for #1–#2. Testable: read the deployment spec and internal skills survey. [U]
    - **Kotlin overtakes Java (#4 → #3)**: Kotlin's MCP SDK reaches at least Tier 2 status (stable 1.0.0 release, documentation requirements met). Testable: check github.com/modelcontextprotocol/kotlin-sdk for a 1.0.0 release. [U]
    - **Native AOT confirmed infeasible for C#**: If reflection-heavy dependencies prevent Native AOT compilation in the DVS's actual stack, the 2.4 cold-start advantage for C# is not achievable. This does not drop C# below #1 but narrows the operational lead over Go on 2.4. Testable: audit DVS's dependency list against dotnet/runtime Native AOT compatibility requirements. [U]
    - **TypeScript full-stack alignment becomes a hard constraint (#5 → #1)**: If the frontend team mandates shared types via a monorepo (shared Zod schemas, tRPC contracts, or Lit component prop types), TypeScript's Tier 3 alignment advantage becomes a de facto Tier 1 requirement, overriding 2.1 scoring. Testable: confirm whether the frontend team intends to share types with the backend. [U]
    - **Strong internal Go or Kotlin expertise**: If an internal skills survey reveals substantial production Go or Kotlin experience, Tier 3 criteria elevate those candidates into functional top-tier contention for a close race. Testable: internal skills survey. [U]

13. Title: Final-surfaced disagreements
    Key claims:
    - No recommendation-changing unresolved disagreements remain. [U]
    - **Close call note 1 — C# vs. Go on 2.1**: Go wins the convention-uniformity sub-dimension; C# wins type-system depth and refactoring safety. Both agents agreed C# edges ahead overall, but the margin is narrow. The final document acknowledges this is the closest scoring call in the analysis. [U]
    - **Close call note 2 — Java vs. Kotlin ordering**: Resolved in favor of Java #3 due to MCP tier evidence (Java Tier 2 GA vs. Kotlin Tier 3 audit result). Kotlin has the stronger language-level type system. If the MCP condition clears (see flip criterion above), the ordering may reverse. [U]
    - **OTel precision note**: The OTel logs signal is stable at the specification level; per-language SDK implementation maturity varies materially (C#/.NET and Java Stable; Go Beta; JavaScript/Python Development; Kotlin Development across all signals; Rust Beta across all signals). [V — opentelemetry.io/status/] The drafter should cite the official opentelemetry.io/status/ page as the authoritative reference. OTel signal maturity is not a primary 2.4 differentiator — structural factors (startup time, memory footprint, GC pause profile) dominate 2.4 scoring. [U]

14. Title: Sources
    Key claims:
    - Cite official MCP SDK page (modelcontextprotocol.io/docs/sdk) for Tier 1/Tier 2/TBD labels. [V per prior runs]
    - Cite MCP SDK tiering system page (modelcontextprotocol.io/community/sdk-tiers) for tier definitions. [V per prior runs]
    - Cite MCP Kotlin SDK audit (GitHub issue #2512, April 2, 2026) for Tier 3 assessment evidence. [V per round 2 evidence]
    - Cite pdfcpu GitHub README for Alpha self-description. [V per round 2 evidence]
    - Cite official opentelemetry.io/status/ for current per-language SDK status. [V — retrieved round 4]
    - Cite opentelemetry.io/docs/concepts/signals/logs/ for the specification-vs-SDK-status distinction. [V — retrieved round 4]
    - Remove unsupported specific MCP download/package counts and Python typing survey statistics (Q-plan-g-01 and Q-plan-g-02 resolutions). [U]
    - All [U] claims not backed by a retrieved source this run are labeled as such in the body; the final document should not promote them to [V] without retrieval. [U]

#### Carry-forward items (from phase 2)

- [Q-plan-g-01] resolved: Unsupported MCP download/package counts and version-specific "stable/production-ready" claims removed — appears in Tier 1 MCP notes and Sources section (conservative official-tier language only).
- [Q-plan-g-02] resolved: Python typing survey statistics and Pyright conformance percentage removed; Python's Weak 2.1 score justified by structural reasoning only — appears in Python 2.1 narrative.
- [D-plan-g-01] resolved: Rust ranks above Python (#6 vs #7); 2.1 highest-weight drives this — appears in final ranking and Rust/Python narratives.
- [D-plan-g-02] resolved: Java ranks above Kotlin (#3 vs #4); MCP Tier 2 GA vs. Tier 3 audit result is the decisive margin, combined with simpler convention space — appears in final ranking, Tier 1 MCP nuance, and Java/Kotlin narratives.
- [D-plan-g-03] resolved: Go 2.3 = Adequate with context note that gap narrows for MIME/file-size-only intake pipelines — appears in 2.3 scoring table and Go narrative.
- [D-plan-g-04] resolved: OTel support is nuanced per-language; blanket "all seven equal" statement removed; OTel signal maturity is NOT a primary 2.4 differentiator given per-language SDK variation and structural factors dominating 2.4 — appears in 2.4 scoring narrative.
- [D-plan-g-05] resolved: C# described as "strong practical static typing with nullable-flow analysis" not "nominally sound type system" — appears in 2.1 sub-dimension A narrative and C# scoring justification.
- [D-plan-g-06] resolved: Corrected inaccurate techbytes.app "stable across every major language SDK" language. Final document cites official opentelemetry.io/status/ as authoritative; acknowledges specification-level vs. per-language SDK implementation maturity distinction; per-language log SDK breakdown (C#/.NET and Java Stable; Go Beta; JavaScript/Python Development; Kotlin Development; Rust Beta) used as 2.4 nuance note — appears in Tier 1.6, 2.4 scoring, and Sources.
- [D-plan-c-01] resolved: Kotlin MCP is weakest margin (Tier 3 per April 2026 audit, TBD on public page); Java #3, Kotlin #4 — appears in Tier 1 MCP table, final ranking, and Java/Kotlin narratives.
- [D-plan-c-02] resolved: Go 2.3 = Adequate (pdfcpu Alpha, commercial UniPDF, thin job orchestration); context note in 2.3 narrative — appears in 2.3 scoring.
- [D-plan-c-03] resolved: Java 2.1 = Adequate-Strong (not Strong = C#); Spring Boot annotation/proxy AOP is the explicit penalty — appears in 2.1 sub-dimension table and Java narrative.
- [Q-plan-c-01] resolved: Kotlin-specific OTel SDK is Development; Kotlin JVM deployments should use stable Java OTel SDK — appears in 2.4 Kotlin narrative.
- [Q-plan-c-02] resolved: Go OTel logs = Beta per official status page; Go 2.4 = Strong overall because structural factors dominate — appears in 2.4 scoring.

#### Drafter
DRAFTER: claude