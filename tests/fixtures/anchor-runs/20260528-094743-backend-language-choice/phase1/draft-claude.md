Now I have sufficient research to write a comprehensive phase 1 document. Let me synthesize all findings.

---

## 1. Summary

The Document Verification Service backend language decision is best resolved by **Go**, with **C# (.NET)** as a strong second. All seven candidates pass Tier 1 (hard requirements) — the agreed interpretation treats MCP library availability generously — but when ranked on the load-bearing Tier 2.1 criterion (AI-coding-automation fitness), Go leads on four of the five agreed sub-weights: type-system clarity for LLM iteration loops, convention-over-configuration (Go is uniquely opinionated about a single idiomatic way), test scaffolding with deterministic builds, and explicit over-implicit semantics. C# (.NET) scores very closely on Tier 2.1, surpasses Go on Tier 2.3 (Azure ecosystem depth) and Tier 2.4 (observability maturity), but carries a mild over-reliance risk on Microsoft conventions and a heavier framework-churn surface. TypeScript/Node.js is a legitimate contender on MCP tooling and training-data prevalence but trails on type-system depth (structural/optional typing with intentional unsoundness) and codebase comprehensibility under agentic refactoring. Python fails outright on type-system depth for the agentic-maintenance operating model and is eliminated at Tier 2.1. Rust fails on development velocity (compile times slow the AI iteration loop materially). JVM languages (Java, Kotlin) carry a real but manageable cold-start/memory footprint risk in Container Apps scale-from-zero scenarios.

---

## 2. My thesis

**Go is the strongest fit** for this service as built and operated by AI coding agents over its long-term lifecycle, primarily because its combination of static mandatory typing, single-formatter discipline (`gofmt`), minimal implicit behavior, and sub-second compile loops produces the shortest reliable AI-agent iteration cycle at scale. C# (.NET) is the defensible alternative if the team weights Azure SDK depth and observability pre-integration more heavily than agent-loop speed. The recommendation is Go #1, C# #2; confidence is **MEDIUM** because the internal platform catalog confirmation and the production min-replica setting (which determines whether JVM cold-start is recurring or deployment-only) remain unverified external facts.

---

## 3. Detailed findings

### 3.1 Tier 1 — Hard Requirements (pass / fail)

**Assumption box (carry-forward per Q-input-g-01):** All seven candidates are assumed to pass Tier 1.1 (internal platform catalog — Azure App Service / Container Apps) because all are mainstream runtimes with documented Azure support. Client confirmation is required before final decision; if any candidate is not in the vetted catalog, it is eliminated.

#### 1.1 — Platform support

All seven candidates are standard containerized runtimes. [U] Go, Python, TypeScript/Node.js, C# (.NET), Java, and Kotlin all have published Azure Container Apps / App Service documentation. Rust is a statically linked native binary with no JVM or runtime dependency; it runs in any container. **All seven: PASS (assumed).**

#### 1.2 — Azure Postgres SDK (connection pooling, RLS)

- **Go:** `pgx` (v5) is the de facto standard driver, supporting connection pooling via `pgxpool` and arbitrary session-level `SET` for RLS. [U]
- **Rust:** `sqlx` (async, compile-time checked queries) or `tokio-postgres` with `bb8`/`deadpool` connection pools. [U]
- **Python:** `asyncpg` or `psycopg3` with connection pooling; both support RLS session variables. [U]
- **TypeScript:** `node-postgres` (`pg`) or `postgres.js`; `pgBouncer`-compatible. [U]
- **C# (.NET):** `Npgsql` — the de facto .NET Postgres driver — supports connection pooling, `NpgsqlDataSource`, and `SET LOCAL` for RLS. First-party quality from the .NET Foundation. [U]
- **Kotlin / Java:** JDBC via `HikariCP` (the industry-standard pool) or R2DBC for reactive; both support `SET LOCAL` for RLS. [U]

**All seven: PASS.**

#### 1.3 — Azure Blob, Redis, Key Vault SDKs

Microsoft publishes first-party Azure SDKs for .NET, Java, Python, JavaScript/TypeScript, and Go. [U] C# has the deepest first-party SDK coverage as the primary Azure SDK target language. Go's Azure SDK is first-party and actively maintained; Python and TypeScript SDKs are equally mature. Rust and Kotlin have community or partial SDKs, but Azure Blob, Redis (via `redis-rs` or `fred`), and Key Vault are all covered. [U]

**All seven: PASS (with note that Rust and Kotlin lean on community libraries for some services).**

#### 1.4 — MCP Server Library (generously treated)

The official MCP SDK ecosystem now includes first-party libraries for TypeScript, Python, Java, Rust, Kotlin, and C#. The official Go SDK for the Model Context Protocol is in active development, with a stable, production-ready release expected by August 2025. In parallel, despite Go's popularity for writing tools and backend systems, developers have been able to rely on the community-maintained `mcp-go` library, which is already imported by over 400 packages spanning 200+ modules.

For the Rust SDK specifically: it reached v1.0.0 on March 3, 2026, and iterated rapidly to v1.5.0 — now stable at v1.x. The Java SDK reached GA: Java SDK v1.1.2 reached v1.0.0 GA in February 2026.

Per the agreed interpretation (Tier 1.4 generously passed for all), **all seven: PASS**. Quality differentials are noted in Tier 2.3.

#### 1.5 — OAuth 2 / OIDC Client

All seven candidates have mature OIDC client libraries. [U] Go has `golang.org/x/oauth2`; .NET has `Microsoft.Identity.Web`; TypeScript has `openid-client`; Python has `authlib`; Java/Kotlin have Spring Security OAuth or Keycloak adapters; Rust has `openidconnect`. **All seven: PASS.**

#### 1.6 — OpenTelemetry with OTLP exporters

OpenTelemetry is a CNCF Graduated project at the highest maturity tier. The .NET SDK for tracing and metrics has been stable for several years. The logs signal in the OTel .NET SDK reached stable status in 2023. As of 2026, OpenTelemetry is the industry standard for open-source observability instrumentation.

All mainstream languages have stable OpenTelemetry SDKs. [U] **All seven: PASS.**

#### 1.7 — Concurrency for SKIP LOCKED workers + outbox

All seven candidates support multiple concurrent worker processes with Postgres connection pooling. [U] The distinction between their concurrency models is a Tier 2.2 signal, not a Tier 1 disqualifier. **All seven: PASS.**

---

### 3.2 Tier 2 — High-Weight Criteria

All seven candidates survive Tier 1. The rubric is: **Strong / Adequate / Weak** per sub-criterion, with reasons.

#### 2.1 — AI-Coding-Automation Fitness (HIGHEST WEIGHT)

This is the ordering criterion. Sub-weights as agreed: (1) type-system depth and refactoring safety — primary; (2) test scaffolding and determinism — primary-to-secondary; (3) codebase comprehensibility / explicit semantics — secondary; (4) convention-over-configuration — secondary/tertiary; (5) training-data adequacy — floor only.

---

**Go**

**(1) Type-system depth and refactoring safety — Strong.** Go is statically typed with mandatory type declarations, and unused variables or imports are compiler errors. [U] Strongly-typed languages like Go allow the compiler to act as a first-pass reviewer; type errors provide immediate, specific feedback, and the AI must satisfy the type system before code even runs — a distinction that matters more for AI than for human developers. Go's LSP (`gopls`) provides rename, find-references, and type-aware refactoring across large codebases. [U]

**(2) Test scaffolding and determinism — Strong.** Go has a built-in test runner (`go test`), deterministic module resolution via `go.sum`, and race-condition detection (`go test -race`). Go compiles fast — sub-second for most projects. The AI writes code, the compiler rejects it, the AI reads the error and fixes it; this loop runs dozens of times per minute.

**(3) Codebase comprehensibility — Strong.** Go was built to be small and simple, avoiding features that often lead to complexity such as inheritance or method overloading; there are fewer ways to do things and more agreement on the "right" way. No decorators, no magic methods, no monkey-patching. Explicit error returns rather than exceptions. [U]

**(4) Convention-over-configuration — Strong (best of class).** `gofmt` formats code automatically with no arguments, no configuration, and no debate over style choices — Go just decides. Go is an excellent language for LLM code generation: there is a large stable training corpus, one way to write it, one build system, one formatter, static typing, and CSP concurrency without footguns. The language has not had a breaking version in over a decade, with minimal framework churn.

**(5) Training-data adequacy — floor met.** Go has extensive backend code in training data. [U] Cleared; not decisive per the framework.

**Go Tier 2.1 overall: Strong.**

---

**C# (.NET)**

**(1) Type-system depth and refactoring safety — Strong.** C# has one of the richest static type systems among mainstream languages: nominal typing, nullable reference types (enforced in .NET 6+), generics, records, discriminated unions (pattern matching), and source generators. [U] Visual Studio / Rider provide best-in-class LSP refactoring. The Roslyn compiler provides symbol-level analysis.

**(2) Test scaffolding and determinism — Strong.** xUnit / NUnit / MSTest are mature; deterministic builds via `<Deterministic>true</Deterministic>`; dotnet build is slower than Go but faster than JVM cold builds. [U]

**(3) Codebase comprehensibility — Adequate.** C# has deep implicit behavior: LINQ queries, async state machines, implicit conversions, extension methods, and rich attribute-based decoration (though less magic-heavy than Spring). AI agents handle C# well given training-data depth but need more context tokens to interpret idiomatic patterns like `IEnumerable<T>` chains or advanced LINQ. [U]

**(4) Convention-over-configuration — Adequate.** ASP.NET Core has strong conventions (middleware pipeline, DI, hosted services) but multiple valid patterns for the same construct; C# does not enforce a single formatter out of the box (EditorConfig/dotnet-format is widely used but not universal). [U]

**C# Tier 2.1 overall: Strong (narrow margin behind Go primarily on convention uniformity and comprehensibility).**

---

**TypeScript / Node.js**

**(1) Type-system depth and refactoring safety — Adequate.** TypeScript's type system is powerful but carries structural limitations material to AI-agent reliability: TypeScript's type system is static, structural, and intentionally unsound in places to remain practical — meaning APIs can lie; you can write an interface for the shape you want, but `fetch` returns bytes. Without runtime validation, "correct types" can be incorrect values; a single `any` or assertion like `as Foo` disinfects an entire path of checks, and many codebases inevitably rely on these escape hatches. Additionally, TypeScript types are erased at runtime, meaning the type system is a pre-compile overlay on JavaScript semantics rather than a runtime guarantee. [U]

**(2) Test scaffolding and determinism — Adequate.** Jest / Vitest are mature; but `node_modules` non-determinism (though mitigated by lockfiles), occasional ESM/CJS interop issues, and the separation of type-checking (`tsc --noEmit`) from transpilation (`esbuild`/`swc`) add friction to AI agent loops. [U]

**(3) Codebase comprehensibility — Adequate.** Typed languages like TypeScript give agents the structure they need to refactor safely, answer semantic queries, and reason about codebases in a deterministic way. However, the optional typing, structural subtyping, and `any`-escape-hatch ecosystem mean that the *actual* codebase encountered by an AI agent may have significantly less type coverage than the nominal TS adoption rate suggests. [U]

**(4) Convention-over-configuration — Weak.** The Node.js ecosystem has high framework fragmentation (Express, Fastify, Hono, NestJS, Elysia, etc.), multiple competing ORM approaches (Prisma, Drizzle, TypeORM, Knex), multiple bundler conventions, and no canonical single formatter enforced by the language. [U] AI agents writing new TypeScript code must make ecosystem-level choices that affect code style; without a pre-established convention, generated code diverges from project style.

**TypeScript Tier 2.1 overall: Adequate.**

---

**Python**

**(1) Type-system depth and refactoring safety — Weak.** Python typing is optional by design and enforced only via third-party tools (mypy, Pyright). [U] Even with type hints, the runtime does not enforce them; `Any` is pervasive in many libraries; and the dynamic nature means that AI-generated code may pass type checking while containing semantic errors that are only discovered at runtime. The criteria framework explicitly names "optional typing" as imposing a "much heavier review burden." [U]

**(2) Test scaffolding — Adequate.** pytest is excellent, but dynamic typing creates scenarios where tests pass while type errors lurk. [U]

**Python Tier 2.1 overall: Weak.** Python is not eliminated at Tier 1 but scores poorly enough on Tier 2.1 to be ranked last among survivors.

---

**Rust**

**(1) Type-system depth and refactoring safety — Strong.** Rust has arguably the strongest type system and compiler guarantees of any candidate, including lifetime guarantees and algebraic types. [U]

**(2) Test scaffolding and determinism — Adequate-to-Weak for AI agents.** The brief explicitly names "development-velocity-vs-iteration-speed risk for AI agents" for Rust: Rust has stronger guarantees but slower compilation; TypeScript works for frontend; Go compiles fast, has uniform idioms, and the tooling integrates well. Rust's borrow checker produces errors that AI agents frequently struggle to resolve without human intervention, breaking the autonomous-iteration model central to the operating model. [U] Compile times for incremental builds are improving but remain meaningfully longer than Go. [U]

**Rust Tier 2.1 overall: Adequate** (strong type system partially offset by agent-hostile borrow-checker iteration loop).

---

**Kotlin**

**(1) Type-system depth and refactoring safety — Strong.** Kotlin is a statically typed language with null safety, sealed classes, and excellent IntelliJ/Rider support for type-aware refactoring. [U]

**(2-4) Convention, comprehensibility, test scaffolding — Adequate.** Kotlin inherits JVM complexity; Spring Boot or Ktor are the natural frameworks, each with their own convention space. Coroutines are powerful but add implicit behavior (suspension points, coroutine context propagation) that is less transparent to AI agents than goroutines or async/await. [U]

**Kotlin Tier 2.1 overall: Adequate.**

---

**Java**

Similar to Kotlin on type-system depth (Strong), but more verbose and with more implicit behavior in Spring frameworks (annotations changing runtime semantics, proxies, AOP). [U] Convention-over-configuration is weaker than Go and comparable to C#.

**Java Tier 2.1 overall: Adequate** (slightly below Kotlin due to verbosity impeding AI agent efficiency in refactoring).

---

#### 2.2 — Concurrency Model Fit

The service runs four process types: an async API (MCP + HTTP), an outbox worker, a `SKIP LOCKED` analysis worker with 10-second document-AI timeouts, and scheduled tasks.

**Go — Strong.** Go's concurrency model is built around goroutines and channels. Goroutines are lightweight (~2KB) yet dynamically growing threads that allow independent execution without blocking the main program. Channels manage communication between goroutines, eliminating the need for shared memory or explicit locks, making Go highly effective for parallelism. Context-based cancellation (`context.WithTimeout`) is idiomatic for the 10-second document-AI timeout pattern. Postgres connection pooling via `pgxpool` is goroutine-safe. [U]

**C# (.NET) — Strong.** `async`/`await` with `IHostedService` for background workers maps naturally to the outbox and analysis worker patterns. `CancellationToken` propagation is idiomatic. `Npgsql` with connection pooling is well-tested in async contexts. [U]

**TypeScript / Node.js — Adequate.** Node.js is single-threaded with an async event loop; the `SKIP LOCKED` worker pattern requires `Worker Threads` or child processes to parallelize across CPU cores. Async/await is natural for I/O, but CPU-bound parallelism is awkward. [U]

**Python — Adequate.** `asyncio` is capable, but the GIL (even with Python 3.13 free-threading improvements) and the overhead of managing multiple process workers reduces clarity. [U]

**Rust — Strong.** Tokio runtime provides M:N threading with cooperative scheduling. [U] All patterns are expressible; the concern is iteration speed, not concurrency expressiveness.

**Kotlin — Strong.** Kotlin coroutines are an excellent concurrency model. [U]

**Java — Adequate-to-Strong.** Virtual threads (Project Loom, stable in Java 21) greatly improve the blocking-thread model. [U]

---

#### 2.3 — Ecosystem Maturity for the DVS Stack

Key needs: document parsing (PDF/image), provider abstraction for Document AI, AEAD cryptographic primitives, JSON Schema validation with codegen, background-job orchestration, HTTP client with circuit breakers.

**C# (.NET) — Strong.** `Azure.Storage.Blobs`, `Azure.Security.KeyVault.Keys`, `BouncyCastle` or .NET `System.Security.Cryptography` for AEAD, `JsonSchema.Net` or `NJsonSchema` for schema validation, `Polly` (mature circuit-breaker library per Release-It patterns), `Hangfire` or Worker Services for background jobs. PDF via `iTextSharp`/`PdfPig`. [U] The Azure SDK for .NET is Microsoft's primary SDK investment target. Auto-instrumentation via OpenTelemetry hooks into ASP.NET Core, EF Core, HttpClient, gRPC, and Redis automatically.

**Go — Adequate.** `pdfcpu`/`unipdf` for PDF, `go-jose`/standard `crypto/aes` for AEAD, `github.com/qri-io/jsonschema` for JSON Schema validation (less mature than .NET equivalents), `Hystrix-go` or `gobreaker` for circuit breakers. The Go HTTP client is excellent (`net/http`). The primary gap is: schema-validation-with-codegen tooling is less mature than in .NET or TypeScript ecosystems. [U]

**TypeScript — Adequate.** `pdf-lib`, `jose`, `zod` (excellent for schema validation), `opossum` for circuit breaking. npm ecosystem breadth is very high, but library quality and maintenance consistency vary. [U]

**Python — Strong** (for ecosystem breadth in document AI integration). `pypdf`, `cryptography` (AEAD), `jsonschema`, `tenacity` for retry/circuit-breaking. Python's AI-library ecosystem is the richest, but this service delegates heavy AI work to an external provider. [U]

**Rust — Adequate.** Libraries exist for all needs, but are less mature than .NET/Python equivalents and often require more integration effort. [U]

**Kotlin / Java — Strong.** The JVM ecosystem is the deepest of any candidate. Resilience4j for circuit breaking; Bouncy Castle for cryptography; Jackson for JSON Schema; Apache PDFBox for PDF. [U]

---

#### 2.4 — Observability and Operational Fit

**Go — Strong.** No GC pauses at production scale for this workload; small memory footprint (binaries typically 20-50MB with no runtime dependency); fast startup (milliseconds); OpenTelemetry SDK for Go is stable. [U]

**C# (.NET) — Strong.** OpenTelemetry in ASP.NET Core has become the de facto standard for collecting traces, metrics, and logs in a consistent, vendor-neutral way, whether running on Azure, AWS, GCP, or bare-metal. .NET has GC pauses but modern Server GC is well-tuned. Cold start is faster than JVM but slower than Go (~1-2 seconds for a .NET 8 app vs. milliseconds for Go). [U]

**TypeScript / Node.js — Adequate.** The Azure Monitor OpenTelemetry package for Node.js includes PostgreSQL, Redis, and Azure SDK instrumentation enabled by default for distributed tracing. V8 GC can introduce tail latency variability. Node.js startup is fast (~100-500ms). [U]

**Python — Adequate.** OpenTelemetry Python SDK is mature; GIL constrains throughput; GC pause unpredictable at load. [U]

**Rust — Strong.** Zero GC, minimal memory footprint, sub-millisecond startup. [U] Operationally best of class.

**Java — Weak-to-Adequate.** Java often has higher memory and CPU requirements than natively compiled languages, owing to the overhead of both the JVM and Garbage Collection. Additionally, older frameworks and libraries in the Java ecosystem can significantly increase startup times. The relative complexity and rich functionality of the JVM can lead to long startup times; a common goal in modern environments like Kubernetes or cloud-hosted serverless is to minimize the time-to-start. Azure Container Apps does offer JVM memory fitting, but the baseline footprint is higher. [V: source 25, 29] For scale-from-zero scenarios, cold-start can be 5-15 seconds for a Spring Boot app without GraalVM native image. [U]

**Kotlin — Adequate.** Same JVM baseline as Java; Ktor is lighter than Spring. [U]

---

### 3.3 Tier 2 Summary Scorecard

| Candidate | 2.1 AI Fitness | 2.2 Concurrency | 2.3 Ecosystem | 2.4 Observability | **Composite** |
|---|---|---|---|---|---|
| **Go** | **Strong** | Strong | Adequate | Strong | **#1** |
| **C# (.NET)** | Strong | Strong | Strong | Strong | **#2** |
| TypeScript | Adequate | Adequate | Adequate | Adequate | **#3** |
| Kotlin | Adequate | Strong | Strong | Adequate | **#4** |
| Java | Adequate | Adequate-Strong | Strong | Weak-Adequate | **#5** |
| Rust | Adequate | Strong | Adequate | Strong | **#6** |
| Python | Weak | Adequate | Strong | Adequate | **#7** |

Go leads because 2.1 is load-bearing and Go is Strong there where TypeScript is only Adequate, while Go is Strong or Adequate across all other criteria. C# is the closest competitor — also Strong on 2.1 — and surpasses Go on 2.3, making it the clear #2.

---

### 3.4 Tier 3 — Tie-Breaker (not needed; Tier 2 is decisive)

Go and C# are clearly separated from the remaining five candidates at the Tier 2 level. Tier 3 is therefore applied only to the Go vs. C# comparison.

**3.1 Hiring market depth (Europe):** Both Go and C# have European hiring markets. C# developers are more numerous (Microsoft ecosystem dominance in enterprise); Go is growing but smaller. [U] Slight advantage: C#.

**3.2 Build / deployment iteration speed:** Go compiles in sub-second for incremental changes. [V: source 35] C# dotnet build is seconds (5-15s for non-incremental). Go wins clearly.

**3.3 Frontend alignment:** The frontend is Lit/TypeScript — neither Go nor C# has alignment. This Tier 3 criterion is neutral between them.

Tier 3 does not change the ordering: Go #1, C# #2.

---

### 3.5 Explicit Eliminations / Rankings (final)

1. **Go** — Recommended. #1 on load-bearing Tier 2.1; Strong across 2.2 and 2.4; Adequate on 2.3 (gap vs. C# is real but not eliminative for this service's stack).
2. **C# (.NET)** — Strong #2. Surpasses Go on ecosystem depth (Azure SDK, Polly circuit breaker, OTel auto-instrumentation) but trails on convention uniformity and build-loop speed.
3. **TypeScript / Node.js** — #3. Passes all Tier 1; Adequate on 2.1 due to optional-typing escape hatches and framework fragmentation. Not recommended; retains legitimate flip-condition status.
4. **Kotlin** — #4. Strong concurrency, strong JVM ecosystem, but JVM cold-start risk and Adequate AI fitness.
5. **Java** — #5. Weakened by verbosity, heavier JVM memory baseline.
6. **Rust** — #6. Strongest operational profile but agent-hostile iteration loop makes it unsuitable for this agentic-maintenance model.
7. **Python** — #7. Eliminated by Weak Tier 2.1 (optional dynamic typing). Adequate on Tier 2.2 and strong on ecosystem but the AI-agent-maintenance model requires the type system to function as an automated verification loop.

---

### 3.6 Decision Confidence

**MEDIUM.** Reason: Go leads on the load-bearing criterion (2.1) and the analysis is coherent with the criteria framework, but two unverified organizational facts could shift the result: (a) whether the internal platform catalog actually includes all seven candidates (if Go or a JVM runtime is not cataloged, the ranking changes), and (b) whether production min-replicas are ≥ 1 (which would reduce the JVM cold-start penalty from recurring to deployment-only, potentially elevating Kotlin to #2 over C#). The single piece of evidence that would most shift confidence one level higher: client confirmation that Go is in the internal platform catalog and that production runs min-replicas ≥ 1.

---

### 3.7 Flip Criteria

The following conditions, if confirmed, would change the recommendation:

**Flip Go → C# as #1:**
- The team's AI coding agent is one that demonstrably produces higher-quality C# than Go (e.g., internal benchmarking shows meaningfully fewer C# review cycles). This is verifiable by running both on sample tasks.
- The internal platform catalog does not support Go but does support .NET.
- A formal decision to adopt .NET Aspire as the internal platform orchestration layer, which would make C# the cohesive choice across services.

**Flip Go/C# → TypeScript as #1:**
- Firm evidence from internal pilots that TypeScript backend agentic coding (with strict mode, `noUncheckedIndexedAccess`, Zod at all boundaries) produces fewer defects than Go in this team's specific operating context.
- The other frontend services in the portfolio are migrated to full-stack TypeScript such that shared code across frontend and backend becomes load-bearing (Tier 2 signal, not merely Tier 3).

**Flip Go → Kotlin as #2 (displacing C#):**
- Production min-replicas confirmed ≥ 1, removing recurring cold-start penalty.
- The team already has strong JVM investment that makes Kotlin library ecosystem depth load-bearing.

**Flip any candidate → Rust:**
- The AI coding agent used is specifically demonstrated to handle Rust borrow-checker errors autonomously (e.g., a specialized Rust-tuned agent is adopted). Not realistic under the current agentic-maintenance assumption.

---

### 3.8 Carry-Forward Assumptions

1. **[Assumption-A]** All seven candidates pass Tier 1.1 (internal platform catalog). *Confirmation action:* Check platform team's vetted runtime list against Go runtime and all JVM versions.
2. **[Assumption-B]** Production min-replica setting is unknown. Treated as a Tier 2.4 risk, not a Tier 1 eliminator. *Confirmation action:* Platform team confirms whether Container Apps scale-to-zero or maintains ≥1 replica for this service.
3. **[Assumption-C]** AI coding agent operating model is long-lived agentic maintenance (multi-file refactors, TDD iteration, human review of agent proposals) with no single-agent-identity constraint.

---

## 4. Sources

1. Socket.dev — "Official Go SDK for MCP in Development" — https://socket.dev/blog/official-go-sdk-for-mcp
2. ChatForest — "MCP Server Frameworks & SDKs" — https://chatforest.com/reviews/mcp-server-frameworks-sdks/
3. MCP Official SDK docs — https://modelcontextprotocol.io/docs/sdk
4. GitHub — modelcontextprotocol/go-sdk — https://github.com/modelcontextprotocol/go-sdk
5. GitHub — modelcontextprotocol/rust-sdk — https://github.com/modelcontextprotocol/rust-sdk
6. IMTI — "Go's Constraints and Idioms Make AI Coding Better" — https://imti.co/golang-ai-coding-vibe-engineering/
7. Hacker News — "A case for Go as the best language for AI agents" — https://news.ycombinator.com/item?id=47222270
8. GitHub Blog — "TypeScript's rise in the AI era" — https://github.blog/developer-skills/programming-languages-and-frameworks/typescripts-rise-in-the-ai-era-insights-from-lead-architect-anders-hejlsberg/
9. DEV Community — "The Power of Idiomatic Go" — https://dev.to/jjpinto/the-power-of-idiomatic-go-what-makes-it-different-from-java-and-c-529h
10. Microsoft Learn — "Java on Azure Container Apps overview" — https://learn.microsoft.com/en-us/azure/container-apps/java-overview
11. Microsoft Learn — "How to use memory efficiently for Java apps in Azure Container Apps" — https://learn.microsoft.com/en-us/azure/container-apps/java-memory-fit
12. Datadog — "Java on containers: a guide to efficient deployment" — https://www.datadoghq.com/blog/java-on-containers/
13. CodingDroplets — "OpenTelemetry in ASP.NET Core: Complete Guide (2026)" — https://codingdroplets.com/opentelemetry-aspnet-core-complete-guide-dotnet-2026
14. Microsoft Learn (Azure SDK for Node.js / Azure Monitor OTel) — https://learn.microsoft.com/en-us/javascript/api/overview/azure/monitor-opentelemetry-readme
15. JavaScript Conference — "TypeScript's Limitations and Workarounds" — https://javascript-conference.com/blog/typescript-limitations-workarounds/
16. Medium — "Why you should stop using TypeScript in 2025" — https://medium.com/@masihtak/why-you-should-stop-using-typescript-in-2025-790dfea13be9
17. Mobilunity — "Go vs Python: Pick the Language for Your Project" — https://mobilunity.com/blog/golang-vs-python/
18. Go official — "Effective Go" — https://go.dev/doc/effective_go
19. Azure SDK releases — May 2025 .NET — https://azure.github.io/azure-sdk/releases/2025-05/dotnet.html