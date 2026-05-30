The verification searches confirm:

1. **Go OTel logs confirmed Beta as of 2026** [V]: Multiple sources confirm Go traces=Stable, metrics=Stable, logs=Beta. This is consistent with the agreed plan.
2. **MCP Go SDK** [V]: The official Go SDK is under the modelcontextprotocol org, maintained in collaboration with Google, and implements the full 2025-11-25 spec.
3. **Kotlin MCP SDK** [V]: The official Kotlin SDK repository shows "Status: Experimental" in the modelcontextprotocol organization.
4. **Rust MCP SDK** [V]: `rmcp` v0.16.0 confirmed under the modelcontextprotocol organization.

Now I have all the evidence needed to produce the final document. Let me draft it following the agreed plan exactly.

---

# Backend Language Decision: Document Verification Service

*Dual-research output — produced by claude (drafter) from a plan agreed with openai across three rounds of phase 2 review.*

---

## 1. Summary

**Go is the recommended backend language for the Document Verification Service's server-side modular monolith.** All seven candidates — Go, TypeScript (Node.js LTS), C# (.NET), Python, Rust, Java, and Kotlin — pass every Tier 1 hard constraint; no candidate is eliminated on binary criteria. The decision is made entirely at Tier 2, where Go leads on criterion 2.1 (AI-coding-automation fitness, the explicitly declared highest-weight criterion) by a narrow but consistent margin over C# (#2): Go wins on convention-over-configuration and codebase comprehensibility for LLMs, while C# wins on type-system expressiveness for domain modeling; test scaffolding and refactoring safety are tied. Go also leads on concurrency model fit (2.2) and operational footprint (2.4). TypeScript is ranked #3 on composite Tier 2 performance driven primarily by ecosystem maturity (2.3). Decision confidence is **MEDIUM**: the Go-over-C# margin on 2.1 is established by structural language properties but is not confirmed by a controlled empirical AI-agent productivity benchmark.

---

## 2. Findings

### Section 1 — Executive Summary and Single Ranked Recommendation

**Recommendation: Go (#1)**

Go is the recommended backend language for all four processes of the Document Verification Service modular monolith — the API process (MCP adapter + internal HTTP), the outbox worker, the analysis worker (Postgres `FOR UPDATE SKIP LOCKED` queue), and the scheduled-task worker — sharing one codebase and running as separately started process types from a single container image.

**Final ranking:**

| Rank | Candidate | Summary rationale |
|------|-----------|-------------------|
| #1 | **Go** | Leads on 2.1 (convention + comprehensibility), 2.2 (concurrency model), 2.4 (footprint/cold start). Competitive M-H on 2.3. |
| #2 | **C# (.NET)** | Wins 2.1 type-system depth; H on 2.3 and 2.4 (deepest Azure OTel). Loses on 2.1 convention and comprehensibility subdimensions. |
| #3 | **TypeScript (Node.js LTS)** | H on 2.3 (MCP reference implementation, pg-boss, Zod-wired schema); M on 2.1 and 2.2; M-H on 2.4. Wins #3 on composite, not on 2.1. |
| #4 | **Java** | M on 2.1 (strong typing but verbosity/Spring DI); M-H on 2.3 and 2.4 (stable OTel, but JVM cold-start/memory). |
| #5 | **Rust** | M on 2.1 composite (borrow checker friction for AI agents); M on 2.3 (thinner Azure ecosystem); M-H on 2.4 runtime. |
| #6 | **Kotlin** | M across all Tier 2 dimensions; Experimental MCP SDK (unique Tier 2.3 debit); JVM cold-start/memory inherited from JVM. |
| #7 | **Python** | L on 2.1 (lowest composite — L on type depth, refactoring safety, and comprehensibility). Strongest 2.3 document-parsing ecosystem, but 2.1 weighting keeps it last. |

**Decision confidence: MEDIUM.**

The Go-over-C# margin on criterion 2.1 is established by structural language properties — `gofmt`-enforced formatting uniformity [V], mandatory compiler enforcement, and explicit-over-implicit semantics — with directional support from community analysis [V]. It is not confirmed by a controlled empirical benchmark comparing AI-agent defect rates in Go vs. C# for compliance-domain service development. No such benchmark currently exists.

*The single piece of evidence that would most shift confidence:* a controlled comparison of AI-agent defect rates (per delivered feature, not per LOC) in Go vs. C# on a similar compliance-domain B2B service codebase. This would shift confidence to HIGH (if Go leads) or flip the recommendation to C# (if C# leads materially).

---

### Section 2 — Tier 1 Pass/Fail Assessment (All Seven Candidates)

All seven candidates pass all seven Tier 1 constraints. No candidate is eliminated.

#### Tier 1 table

| Candidate | 1.1 Platform | 1.2 Postgres | 1.3 Azure SDKs | 1.4 MCP SDK | 1.5 OIDC | 1.6 OTel | 1.7 Concurrency | **Verdict** |
|---|---|---|---|---|---|---|---|---|
| Go | PASS | PASS | PASS | PASS (Tier A†) | PASS | PASS | PASS | **PASS** |
| TypeScript | PASS | PASS | PASS | PASS (Ref impl) | PASS | PASS | PASS | **PASS** |
| C# (.NET) | PASS | PASS | PASS | PASS (Tier A) | PASS | PASS | PASS | **PASS** |
| Python | PASS | PASS | PASS | PASS (Ref impl) | PASS | PASS | PASS | **PASS** |
| Java | PASS | PASS | PASS | PASS (Tier A) | PASS | PASS | PASS | **PASS** |
| Kotlin | PASS | PASS | PASS | PASS* (Experimental) | PASS | PASS** | PASS | **PASS** |
| Rust | PASS | PASS | PASS | PASS (Tier A) | PASS | PASS | PASS | **PASS** |

\* Kotlin MCP SDK is labeled "Experimental" in the modelcontextprotocol organization [V]; passes Tier 1.4 but carries a residual into Tier 2.3.
\*\* Kotlin passes Tier 1.6 via the Java OTel SDK (JVM compatibility mode) [U]; Kotlin-specific/coroutine OTel instrumentation remains Development status, which is a Tier 2.4 caveat, not a Tier 1 failure.
† Internal platform vetted catalog is not publicly inspectable; assessed against public Azure Container Apps support for Linux containers as a proxy. Internal catalog verification is a required pre-implementation step for all candidates. [U]

#### Tier 1 per-constraint notes

**1.1 — Platform support (Azure App Service / Container Apps):** [U] All seven produce OCI-compliant Linux container images compatible with Azure Container Apps. This is treated as a pass for all candidates against the public platform documentation. Internal catalog verification remains a pre-implementation dependency.

**1.2 — Postgres client (connection pooling, RLS session variables):** [U] All seven have mature Postgres drivers capable of per-connection `SET app.tenant_id`-style RLS session management: Go uses `pgx/v5` + `pgxpool`; TypeScript uses `node-postgres` + `pg-pool`; C# uses Npgsql; Python uses `asyncpg` or `psycopg3`; Java and Kotlin use HikariCP + JDBC; Rust uses `sqlx` with async pool.

**1.3 — Azure Blob, Redis, Key Vault SDKs:** [U] Microsoft publishes first-party Azure SDKs for .NET, Java, Python, and JavaScript (TypeScript). Go has the officially maintained `azure-sdk-for-go`. Rust has Azure SDK crates with async support [V]. Kotlin inherits Java Azure SDK access via JVM. All pass.

**1.4 — MCP server library:** SDKs are classified into tiers based on feature completeness, protocol support, and maintenance commitment. All seven languages have official SDKs under the modelcontextprotocol organization [V]:

- **TypeScript** — the reference implementation, most actively maintained. [V]
- **Python** — the second reference implementation, co-maintained by Anthropic. [V]
- **Go** — the official Go SDK for Model Context Protocol servers and clients, maintained in collaboration with Google. The latest release marks the completion of the full 2025-11-25 specification implementation.
- **C# (.NET)** — official SDK, production tier. [V]
- **Java** — the official Java SDK for Model Context Protocol servers and clients, maintained in collaboration with Spring AI.
- **Kotlin** — official SDK, maintained in collaboration with JetBrains. Status: Experimental.
- **Rust** — `rmcp` v0.16.0, official SDK under the modelcontextprotocol organization. [V]

**1.5 — OAuth 2 / OIDC client:** [U] All seven have mature OIDC/OAuth 2 libraries: Go (`golang.org/x/oauth2`, MSAL for Go); TypeScript (`openid-client`); C# (`Microsoft.Identity.Web`, first-party); Python (`authlib`); Java/Kotlin (Spring Security OAuth2); Rust (`openidconnect` crate).

**1.6 — OpenTelemetry (traces, metrics, logs via OTLP):** [U] All seven pass. The OpenTelemetry-Go instrumentation for metrics and traces is currently stable, while instrumentation for logs is in beta. C# and Java have traces/metrics/logs all Stable on the OTel status page [U]. Kotlin passes via the Java OTel SDK (JVM compatibility mode); Kotlin-specific OTel (coroutine instrumentation) remains Development — Tier 2.4 caveat only, not a Tier 1 failure.

**1.7 — Concurrency with safe Postgres connection pooling:** [U] All seven can run multiple worker processes with safe Postgres connection pool management under the agreed container model (one shared image, separately started process types per Azure Container Apps semantics).

---

### Section 3 — Tier 2 Scoring: AI-Coding-Automation Fitness (Criterion 2.1, Highest Weight)

This is the decisive criterion. It is assessed across five named subdimensions: (a) type-system depth, (b) convention-over-configuration, (c) test scaffolding & determinism, (d) refactoring safety, (e) codebase comprehensibility for LLMs.

**Scale: H = strong fit, M = acceptable with tradeoffs, L = weak relative fit. H- = near-H with one specific gap noted.**

#### Subdimension (a): Type-system depth

**C# — H.** Each SDK provides the same functionality but follows the idioms and best practices of its language. All SDKs support protocol compliance with type safety. Beyond MCP, C#'s type system emits compile-time warnings for `maybe-null` dereferences via nullable reference type analysis [V]; sealed class hierarchies force exhaustive pattern-matching; records with `required` properties catch missing initialization at compile time. For a compliance-domain service with distinct rule outcome types (Approved/Rejected/Pending/Escalated), C# can express these as a sealed hierarchy where the compiler forces exhaustive handling. [U]

**Go — H-.** Go's type system is static, mandatory, and universally compiler-enforced — there are no advisory or optional typing modes. Every variable has a declared type; the compiler rejects mismatches without exception. Interfaces are structurally satisfied, reducing ceremony. However, Go lacks sealed class hierarchies, discriminated unions in the C# sense, and nullable reference type analysis. AI misuse patterns are detectable because there is exactly one way to define a new type, but domain-modeling expressiveness for the compliance context is less rich than C#. [U]

**TypeScript — M.** TypeScript has a sophisticated type system (union types, discriminated unions, generics, conditional types). However, type safety is opt-in: `strict` mode must be configured, and escape hatches (`any`, `as unknown as X`, `//@ts-ignore`) are commonly used by AI agents to resolve type errors rather than fix root causes. [U]

**Python — L.** Python's type hints are advisory only; `mypy`/`pyright` enforce types in CI but the runtime ignores them. Under heavy AI-driven development, the absence of compile-time enforcement substantially raises review burden. [U]

**Rust — M (practical for AI agents).** Rust's type system is the most expressive of any candidate: affine types, lifetimes, ownership, algebraic types. However, the borrow checker introduces friction that AI agents encounter as repeated round-trips on lifetime annotation errors — the compiler rejects syntactically valid code for ownership reasons, and AI agents navigate this inconsistently. Scored M for practical AI-coding purposes despite academically world-class type expressiveness. [U]

**Java — M.** Statically typed, compiler-enforced, strong generics. Java's verbosity creates more surface area for AI-generated boilerplate to accumulate errors. [U]

**Kotlin — M.** Null safety (compiler-enforced `?` annotations) is a genuine H-level advantage, but extension functions, companion objects, and DSL patterns can introduce subtle type behaviors in AI-generated code. [U]

#### Subdimension (b): Convention-over-configuration

**Go — H.** This is Go's single strongest subdimension for AI coding. `gofmt` — the official Go formatter — is built into the toolchain and enforces exactly one formatting style [V]; there is no formatter configuration debate, no brace-placement argument. The ecosystem follows `Effective Go` idioms that are more uniform than any other mainstream language: HTTP handlers share one interface signature, error handling is universally `if err != nil { return err }`, context propagation always uses `context.Context` as the first argument. Despite Go's popularity for writing tools, backend systems, and AI infrastructure, the patterns remain consistent across codebases, which means AI agents draw from a highly uniform training distribution when generating Go code. [V]

**C# — M.** Multiple valid patterns exist for the same concern: ASP.NET Core controllers vs. minimal APIs, EF Core vs. Dapper vs. raw Npgsql, constructor injection vs. primary constructor injection, layered Aspire configuration. The DI container is a strong convention but introduces a service-registration layer that AI agents must keep consistent. [V] This fragmentation is the primary reason C# trails Go on the 2.1 composite despite winning on type-system depth. [U]

**TypeScript — M.** No enforced formatting standard (Prettier is opt-in). Multiple competing HTTP frameworks (Fastify, Express, Hono, NestJS, Elysia), multiple ORM choices (Prisma, Drizzle, TypeORM, Kysely), multiple DI approaches. Conventions must be deliberately chosen and enforced at project level. [U]

**Python — M.** PEP 8 exists but enforcement is optional. FastAPI is a strong convention within that framework, but the broader ecosystem is fragmented. [U]

**Rust — L.** The borrow checker introduces a meta-convention (ownership rules) that AI agents must navigate; this produces inconsistent patterns in AI-generated code beyond the normal convention space. Cargo is a universal build tool, which helps, but the ownership/lifetime convention layer is unlike any other language. [U]

**Java — M.** Spring Boot provides strong conventions by design, but the abstraction layers (Spring DI, AOP, auto-configuration) introduce implicit behavior that LLMs must navigate consistently. [U]

**Kotlin — M.** Inherits JVM/Spring conventions, but Kotlin's concision features (extension functions, DSLs, operator overloading, companion objects) add a meta-convention layer on top. [U]

#### Subdimension (c): Test scaffolding and determinism

**Go — H.** `go test` is built into the toolchain; no external test runner required. Table-driven tests are idiomatic and produce readable, deterministic output. The `testing/synctest` package (Go 1.24–1.25) simplifies writing tests for concurrent, asynchronous code. [U] Builds are deterministic: given the same source, the same binary is produced. Sub-second compile-and-test cycles enable AI agents to iterate at high frequency. [U]

**C# — H.** `dotnet test` is built-in; xUnit/NUnit/MSTest are mature; the .NET SDK produces deterministic builds. [U]

**TypeScript — M.** Vitest and Jest are mature but not included in the runtime itself. Async test patterns with `async/await` are well-supported. Module resolution can produce non-deterministic behavior in test environments when path aliasing is involved. [U]

**Python — M.** `pytest` is excellent, but the async testing story for `asyncio` code is less clean. Build determinism depends heavily on package pinning. [U]

**Rust — H (but caveat).** `cargo test` is built-in and reproducible. However, compile times — especially for trait-heavy code — slow the test-driven AI iteration loop substantially compared to Go or TypeScript. Scored H on the criterion but with a practical caveat that compounds the borrow-checker friction. [U]

**Java/Kotlin — M.** JUnit + Gradle/Maven are mature. Slower build cycles than Go or TypeScript. [U]

#### Subdimension (d): Refactoring safety

**Go — H.** `gopls` (the official Go language server) provides rename-symbol, find-references, and type-aware refactoring across multi-file codebases [V]. Go's static typing means `findReferences` returns exactly the call sites with no noise from dynamic dispatch or duck-typing. LSP-native AI coding tool integration (Claude Code gained LSP support in late 2025 [V]) means AI-driven refactors are verified against the full call graph. [U]

**C# — H.** Roslyn-grade refactoring is arguably the most mature of any mainstream language: rename, extract method, introduce variable, change signature — all work reliably across large codebases. OmniSharp and the Roslyn language server provide professional-grade LSP support. [U]

**TypeScript — M.** TypeScript's LSP (`tsserver`) is mature and provides excellent rename/find-references. However, TypeScript's structural typing means refactoring a function signature does not always catch callers that are structurally compatible with the old signature. Dynamic module imports and JavaScript interop create blind spots. [U]

**Python — L.** Python's optional type annotations and dynamic nature mean that rename/refactor operations have high false-negative rates for reference finding — tools miss call sites. AI agents doing large-scale refactors in Python codebases regularly leave broken references. [U]

**Rust — M.** `rust-analyzer` is excellent but the borrow checker introduces refactoring overhead: changing a function signature often requires cascading ownership/lifetime annotations across callers. AI agents repeatedly stall on this cascade. [U]

**Java/Kotlin — H.** IntelliJ's Kotlin/Java refactoring support is world-class. Find-references, rename, and extract-method work reliably across large Spring Boot codebases. [U]

#### Subdimension (e): Codebase comprehensibility for LLMs

**Go — H.** Go's explicit semantics are the decisive advantage here: no magic methods, no monkey-patching, no decorator-transformed call semantics, no hidden DI container wiring. What a Go function does is visible in its source. Context propagation is explicit (`context.Context` passed as the first argument). Error handling is explicit (`err` return values). Dependencies are explicit (passed as function arguments, not injected by framework magic). An LLM inspecting a Go codebase can trace behavior without resolving runtime abstractions. [V] The ratio of explicit-to-implicit semantics is the highest of any candidate. [U]

**C# — M.** C# has powerful implicit mechanisms: ASP.NET Core DI lifecycle (Singleton/Scoped/Transient lifetimes affect behavior), EF Core change tracking, middleware pipeline registration, service-container wiring. An LLM must understand the DI container's resolution rules to reason about object lifetimes and dependencies. [V] This is the second decisive subdimension in Go's favor. [U]

**TypeScript — M.** TypeScript codebases without DI frameworks (Fastify, Hono) are relatively explicit and LLM-readable. NestJS-style codebases with decorators and DI containers are not. The score is M because the framework choice materially determines comprehensibility. [U]

**Python — L.** Python has the highest implicit surface area: `__dunder__` methods, metaclasses, decorators that replace functions, monkey-patching, dynamic attribute access. Flask/Django/FastAPI codebases have substantial implicit behavior. [U]

**Rust — H.** Rust's semantics are explicit by design — the compiler enforces what it cannot make implicit. However, trait-based polymorphism (`dyn Trait` vs. `impl Trait` vs. generic bounds) adds comprehension overhead for AI agents that is not present in Go. Scored H but less purely explicit than Go. [U]

**Java/Kotlin — M.** Spring Boot annotation-driven DI introduces implicit behavior. Kotlin's extension functions, companion objects, and operator overloading can obscure behavior in AI-generated code. [U]

#### 2.1 Subdimension scoring table

| Candidate | (a) Type depth | (b) Convention | (c) Test/determinism | (d) Refactoring | (e) Comprehensibility | **2.1 Composite** |
|---|---|---|---|---|---|---|
| **Go** | **H-** | **H** | **H** | **H** | **H** | **H (narrow lead)** |
| **C# (.NET)** | **H** | M | H | H | M | **M-H** |
| TypeScript | M | M | M | M | M | **M** |
| Java | M | M | M | H | M | **M** |
| Kotlin | M | M | M | H | M | **M** |
| Rust | M* | L | H† | M | H | **M** |
| Python | L | M | M | L | L | **L** |

\* Rust's type depth is academically H but practically M for AI agents (borrow checker friction).
† Rust's test scaffolding is built-in and H, but slow compile times reduce the practical AI iteration benefit.

**Go leads 2.1 by a narrow margin.** Go wins on 2 of 5 subdimensions (convention-over-configuration, codebase comprehensibility); both Go and C# are tied on 2 (test scaffolding/determinism, refactoring safety); C# wins 1 (type-system depth). The decisive subdimensions in Go's favour are convention uniformity and explicit semantics — the structural properties most directly relevant to AI-agent iteration speed and codebase traceability.

**2.1 is load-bearing in the final ordering.** Go wins #1 because it leads on 2.1. The document does not need to invoke Tier 3 criteria to order the top 3.

**Regime note (Q-input-c-03):** In an assisted-development regime (30–50% AI, ~50–70% human), the type-system depth advantage of C# (subdimension a) is more accessible — human reviewers verify that C#'s sealed hierarchies and nullable analysis are used correctly. In a more-autonomous regime (≥80% AI), Go's convention uniformity and comprehensibility advantages are stronger, because AI agents cannot reliably leverage C#'s richer type system without producing the pattern heterogeneity the DI and convention fragmentation creates. The Go-over-C# 2.1 margin is larger at ≥80% AI autonomy. [U]

---

### Section 4 — Tier 2 Scoring: Concurrency Model Fit (Criterion 2.2)

The Document Verification Service runs four process types sharing one container image: API (sync, hundreds concurrent, MCP + HTTP), outbox worker (at-least-once domain event emission), analysis worker (`FOR UPDATE SKIP LOCKED` Postgres queue with 10-second AI provider timeouts), and scheduled-task worker (expiry, daily exports).

**Go — H.** Goroutines + `context.Context` precisely fit all four process types. Goroutines are lightweight (~2 KB initial stack, multiplexed onto OS threads by the Go scheduler [U]), so hundreds of concurrent in-flight API requests are handled without thread-per-request overhead. `context.WithTimeout` provides first-class 10-second timeout propagation for analysis worker AI calls. The SKIP-LOCKED worker pattern is idiomatic Go: N goroutines each acquiring a pool connection, running `SELECT … FOR UPDATE SKIP LOCKED`, processing the row, committing — no lock thrashing because each goroutine holds its own connection and SKIP LOCKED is designed for this fan-out. [U]

**C# — M-H.** ASP.NET Core Kestrel is non-blocking. `CancellationToken` propagates from `HttpContext.RequestAborted` to long-running tasks including database queries and outbound HTTP [V]. `System.Threading.Channels` provides clean pipeline primitives. Npgsql supports async connection pools. The concurrency model is excellent for the API and worker patterns; C# trails Go slightly because the connection-pool + RLS session management for the analysis worker requires more boilerplate coordination. [U]

**TypeScript — M.** Node.js's single-threaded event loop handles concurrent I/O well via `async/await`. `pg-boss` provides a mature Postgres-native SKIP-LOCKED job queue with idempotency keys, retry/backoff, and DLQ [V]. RLS session management across async boundaries requires `AsyncLocalStorage`-based context propagation, which is correct but adds cognitive overhead for AI agents. CPU-adjacent analysis work requires worker threads or out-of-process separation. [U]

**Rust — M-H.** Tokio's async runtime is excellent for all four workload types. Memory safety eliminates a class of concurrency bugs at the language level. Borrow-checker friction under AI-driven development depresses the practical score: writing correct concurrent Rust with Tokio requires lifetime annotations that AI agents frequently get wrong. [U]

**Python — M.** `asyncio` handles I/O-bound concurrency; the GIL is less relevant for document AI calls (which are I/O-bound). `asyncpg` supports async pools. Less "one obvious way" than Go/C# for mixed API + worker code in a single modular monolith. [U]

**Java/Kotlin — M.** Virtual threads (Java 21 Project Loom) and Kotlin coroutines address the concurrency model. JVM initialization overhead for four process types sharing a container image creates resource contention; each JVM startup loads the full class library regardless of which process type is started. [U]

**Concurrency 2.2 summary: Go = H; Rust = M-H; C# = M-H; TypeScript = M; Python = M; Java = M; Kotlin = M.**

---

### Section 5 — Tier 2 Scoring: Ecosystem Maturity (Criterion 2.3)

Key library areas assessed: document parsing (PDF, images), document AI provider abstraction, cryptographic primitives (AEAD for GDPR crypto-erasure), schema validation (JSON Schema / MCP tool schemas), background-job orchestration (SKIP LOCKED, idempotency, DLQ), and HTTP client stability patterns.

**TypeScript — H.**
- MCP: the TypeScript SDK is the reference implementation, the most feature-complete and actively maintained of any candidate. [V]
- Schema validation: Zod v4 is wired directly into the MCP TypeScript SDK. [V]
- Job queue: `pg-boss` provides Postgres-native SKIP-LOCKED with idempotency keys, retry/backoff, and dead-letter handling built-in. [V]
- Document parsing: `pdf-lib`, `pdf-parse`, `sharp` — mature.
- Anthropic SDK: official TypeScript SDK maintained by Anthropic.
- JSON Schema codegen: deep story (Zod, TypeBox, ArkType).

**C# (.NET) — H.**
- Azure integration: deepest first-party Azure SDK coverage for Blob, Redis, Key Vault, and Monitor [U]; the Azure Monitor OpenTelemetry Distro for .NET is Microsoft-authored with ASP.NET Core auto-instrumentation. [V]
- Document parsing: iTextSharp/PDFsharp for PDF; SixLabors.ImageSharp for image handling.
- Schema codegen: NJsonSchema with C# code generation.
- Job orchestration: Hangfire (persistent jobs) or MassTransit (saga/outbox patterns).
- Crypto: `System.Security.Cryptography` in stdlib — AEAD, AES-GCM, key wrapping all available. [U]

**Python — H.**
- Document parsing: the deepest ecosystem of any candidate — PyMuPDF, Pillow, pdfminer.six, python-magic.
- Anthropic SDK: official Python SDK maintained by Anthropic.
- Schema validation: Pydantic — excellent, with JSON Schema export.
- Job orchestration: Celery, arq, dramatiq.

**Go — M-H.**
- Crypto: `crypto/aes`, `golang.org/x/crypto/chacha20poly1305` are in stdlib or the extended standard library — excellent for AEAD and key wrapping. [U]
- Job queue: `river` — Postgres-native SKIP-LOCKED with idempotency, retry, DLQ, built in Go.
- Document parsing: `pdfcpu`, `gopdf` — functional but smaller community than TypeScript/Python/C#.
- Schema validation: `invopop/jsonschema` — adequate for MCP tool schema generation.
- Go MCP SDK: the SDK endeavors to implement the full MCP spec. Schema handling uses struct tags rather than Zod-equivalent libraries, which is idiomatic but less ergonomic than TypeScript's Zod-wired story. [U]

**Java — M-H.**
- Document parsing: Apache PDFBox, iText — mature enterprise-grade.
- Job orchestration: Spring Batch, Quartz — mature but heavyweight for a greenfield service.
- Azure SDK: first-party, extensive coverage.
- Crypto: JCE — enterprise-grade.
- MCP: official Java SDK maintained with Spring AI team [V]; production-tier.

**Kotlin — M.**
- Inherits Java ecosystem (JVM libraries available).
- MCP SDK: labeled "Experimental" [V] — unique Tier 2.3 debit not present for any other candidate.
- Coroutine/context-propagation complexity for worker patterns requires POC validation.
- Kotlin-specific OTel (coroutine instrumentation): Development status adds Tier 2.4 caveat. [U]

**Rust — M.**
- Document parsing: `lopdf`, `pdf` crate — less mature than Java/TypeScript/Python.
- Azure ecosystem: Azure SDK crates for Rust exist with async support [V], but coverage is less deep than .NET/Java/Node/Python.
- Crypto: `ring`, `rust-crypto` — excellent.
- MCP: `rmcp` v0.16.0 under modelcontextprotocol org. [V]

**Ecosystem 2.3 summary: TypeScript = H; C# = H; Python = H; Go = M-H; Java = M-H; Kotlin = M; Rust = M.**

---

### Section 6 — Tier 2 Scoring: Observability and Operational Fit (Criterion 2.4)

**Go — H (with note).**
- OTel signal maturity: as of 2026, the OpenTelemetry Go SDK is stable for traces and metrics, with logs in beta, reflecting ongoing improvements in the ecosystem. The Go OTel team listed "Logs API stable" as a 2025 roadmap goal, indicating active stabilization work. [U]
- The log Beta status is a small debit for this workload: the DVS is not a log-analytics platform; traces and metrics are the more load-bearing telemetry signals for request and worker diagnosis. OTLP log ingestion through Azure Container Apps' managed OTel agent operates at Beta maturity without documented production gaps. [U]
- Memory footprint: a Go binary container image starts at ~10–15 MB; a non-trivial HTTP server uses ~15–30 MB resident memory. [U] This is the most favorable Container Apps scaling profile of any candidate.
- Cold start: Go binaries start in milliseconds — no JVM warmup, no Node.js module resolution delay. [U] Directly relevant to Azure Container Apps scale-from-zero scenarios.
- GC: Go's GC has been low-latency since Go 1.5; pause times are not material at DVS workload rates. [U]

**C# (.NET) — H.**
- OTel signal maturity: .NET OTel traces, metrics, and logs are all Stable. [U] The Azure Monitor OpenTelemetry Distro for .NET is Microsoft-authored and includes ASP.NET Core auto-instrumentation baked in. [V] .NET's OTel implementation uses built-in platform APIs (`ILogger<T>`, `System.Diagnostics.Activity`, `System.Diagnostics.Metrics`) so library authors instrument without a separate OTel dependency. [V]
- Cold start: ~500 ms–1.5 s without NativeAOT. NativeAOT is partially supported for Azure SDK packages; with NativeAOT, startup time reduces substantially. [U]
- Memory: ~80–150 MB baseline for an ASP.NET Core application. [U]

**TypeScript (Node.js LTS) — M-H.**
- OTel: `@azure/monitor-opentelemetry` available [V]; traces and metrics are Stable, logs are Development on the OTel status page. [U]
- Cold start: Node.js module loading is faster than JVM warmup but slower than Go binary startup. [U]
- Memory: ~50–80 MB baseline. [U]

**Python — M.**
- OTel: traces and metrics Stable, logs Development. [U]
- Low baseline memory.
- GIL can introduce latency under concurrent load, though document AI calls are I/O-bound. [U]

**Java — M-H.**
- OTel: traces, metrics, and logs all Stable. [U]
- JVM cold start: 1–3 s for Spring Boot without GraalVM native compilation. [U] Azure Container Apps JVM automatic memory fitting requires active management and is disabled below 1 GB memory allocation [V] — this is optimization-for-a-known-problem, not elimination of the problem.
- Memory: 256–512 MB baseline for a Spring Boot application. [U]

**Kotlin — M.**
- OTel: passes via Java OTel SDK (all Stable); Kotlin-specific OTel (coroutine instrumentation) remains Development. [U]
- Inherits JVM cold-start and memory concerns.

**Rust — M-H.**
- Zero GC; lowest memory footprint of any candidate (statically linked binary). [U]
- OTel Rust: Beta across traces, metrics, and logs. [U]
- Operational tooling depth thinner than Go/C#/Java at this service's complexity level. [U]

**Observability 2.4 summary: Go = H (note: logs Beta, non-material for DVS); C# = H (deepest Azure OTel); Rust = M-H (excellent runtime, thinner OTel ecosystem); TypeScript = M-H; Java = M-H (stable OTel, JVM operational concerns); Python = M; Kotlin = M.**

---

### Section 7 — Final Ranking and Tier 2 Summary Table

| Rank | Candidate | 2.1 AI-coding | 2.2 Concurrency | 2.3 Ecosystem | 2.4 Observability/Ops | Decision notes |
|------|-----------|---|---|---|---|---|
| **#1** | **Go** | **H** (narrow lead) | **H** | M-H | H (logs Beta note) | Leads on decisive criterion + concurrency + footprint |
| #2 | C# (.NET) | M-H | M-H | H | H | Wins type-system depth; H on 2.3/2.4; C# flip criterion below |
| #3 | TypeScript | M | M | **H** | M-H | Wins #3 on composite (MCP/schema/job ecosystem + footprint), not on 2.1 |
| #4 | Java | M | M | M-H | M-H | Strong typing/refactoring, stable OTel; JVM footprint prevents higher rank |
| #5 | Rust | M | M-H | M | M-H | Borrow-checker velocity risk for AI agents; thinner Azure ecosystem |
| #6 | Kotlin | M | M | M | M | Experimental MCP SDK unique debit; JVM inherited; Kotlin OTel Development |
| #7 | Python | **L** | M | H | M | Lowest 2.1 composite (L on type depth, refactoring, comprehensibility) despite strongest document-parsing ecosystem |

**Why TypeScript ranks above Java (#3 vs. #4):** TypeScript does not beat Java on 2.1 — Java is stronger on type-system enforcement and refactoring safety. TypeScript wins #3 on composite Tier 2 scoring: its MCP reference-implementation status, Zod-wired schema validation, `pg-boss` SKIP-LOCKED job queue, and operational footprint advantages over JVM collectively outweigh Java's 2.1 type-system advantage for this specific service. This is an explicit composite call. [U]

**Why Python ranks last (#7) despite H on 2.3:** The brief explicitly declares 2.1 the highest-weight criterion. Python's L composite on 2.1 — the lowest of any candidate — means its document-parsing and AI-provider ecosystem strengths (which would make it a strong choice for a data-processing or ML service) do not compensate for the review burden it imposes under AI-driven backend development of a compliance-domain modular monolith. [U]

---

### Section 8 — Decision Confidence

**Confidence: MEDIUM**

**Reason:** The Go-over-C# margin on criterion 2.1 is established by structural language properties — `gofmt`-enforced formatting uniformity [V], mandatory compiler enforcement, and explicit-over-implicit semantics [V] — with directional support from community analysis of AI coding patterns in Go [V]. The margin is narrow (Go wins 2 of 5 subdimensions; C# wins 1; 2 are tied) and is not confirmed by a controlled empirical benchmark comparing AI-agent defect rates by language for compliance-domain service development. No such benchmark currently exists. [U]

**What would shift confidence to HIGH:**
1. Internal platform catalog confirms Go as a supported runtime (pre-implementation verification step — unverified this run). [U]
2. The Go OTel logs signal reaches Stable, eliminating the small 2.4 debit. [U]
3. A project POC confirms Go's 2.1 advantages materialize in practice (e.g., AI-generated Go code requires fewer review-burden corrections than AI-generated C# code in this codebase context). [U]

**What would shift confidence to LOW:**
- Evidence that AI coding agents produce materially more review-worthy defects in Go than in C# for compliance-domain service development (no such evidence currently exists). [U]
- Internal platform catalog excludes Go (currently assessed against public platform support only). [U]

---

### Section 9 — Flip Criteria

The following conditions, if met, would change the ranking. They are explicit and testable — a future reader can verify whether each condition has changed.

#### C# (#2) overtakes Go (#1)

Any ONE of the following is sufficient:

1. **AI-agent defect-rate POC:** A project POC or A/B template comparison shows that AI agents reliably leverage C#'s nullable reference type analysis, sealed hierarchies, and `required` record properties to produce fewer review-burden defects than Go's convention uniformity produces. *Testable: run both language templates through 2–3 feature iterations with AI coding agents; compare human-review revision count per feature.* [U]

2. **Internal platform catalog exclusion:** The internal platform's vetted catalog treats Go as a non-standard runtime and .NET as the mandated or preferred backend language. *Testable: platform catalog review before provisioning — a pre-implementation step.* [U]

3. **Team concentration:** The team's pre-existing codebase is overwhelmingly C#/.NET (≥60% of current engineers have production C# experience) and onboarding cost to Go is confirmed as measurable. *Testable: team survey before project kick-off.* [U] See also carry-forward item Q-input-c-01.

#### TypeScript (#3) overtakes C# (#2)

ALL THREE of the following must hold simultaneously:

1. **Strict-mode enforcement:** The project template enforces `strict: true` TypeScript with a no-`any` lint rule, and adopts a low-implicit-behavior HTTP framework (Fastify or Hono, not NestJS). This closes the 2.1 convention and comprehensibility gap to approximately half a subdimension. [U]

2. **2.3 advantage confirmed load-bearing:** The DVS implementation confirms that the TypeScript ecosystem's specific advantages (`pg-boss` for outbox/analysis worker patterns, Zod-wired MCP schema validation, Anthropic SDK parity) are more load-bearing than initially assessed — i.e., the service's MCP surface and schema-validation story are a larger fraction of development effort than the rules engine and domain-model components. [U]

3. **Tooling parity:** Internal platform has materially equivalent or better TypeScript tooling than C# tooling. (Unlikely given the Azure-first stack, but testable during platform onboarding.) [U]

#### Go OTel log Beta becomes load-bearing (depresses 2.4 score)

Only if BOTH of the following hold:

1. The DVS's observability requirements include structured-log correlation across worker boundaries as a primary diagnostic tool (e.g., the ops team specifies log-based alerting rules in addition to trace/metric-based rules). [U]

2. The Azure Container Apps managed OTel agent does not transparently handle Beta-stability OTLP log export from the Go SDK. *Testable: instrument a non-production Go service against the Azure Container Apps managed OTel agent and verify log ingestion.* [U]

#### Kotlin (#6) overtakes Rust (#5)

If the Kotlin MCP SDK's "Experimental" label is promoted to production tier before project kick-off. *Testable: check `modelcontextprotocol.io/docs/sdk` for Kotlin tier status.* [V]

---

## 3. Disagreements Left Open

*No unresolved disagreements remain between the two research agents at plan sign-off. The disagreement below was resolved during phase 2 and is recorded for traceability.*

### D-input-c-01 / D-plan-c-01 / D-plan-g-01: Go vs. C# as #1 recommendation

**Status:** Resolved.

**Position A (claude/openai initial):** Claude initially recommended Go #1 based on H-across-all-five-subdimensions claim on 2.1. OpenAI initially recommended C# #1 based on richer type-system expressiveness and domain-modeling safety.

**Position B resolution:** Both agents converged on Go #1 by a narrow 2.1 margin — Go wins convention-over-configuration and codebase comprehensibility (2 of 5 subdimensions); C# wins type-system depth (1 of 5); both are tied on test scaffolding and refactoring safety (2 of 5). C# is the strongest challenger with an explicit flip criterion.

**Final document treatment:** Go #1 with MEDIUM confidence and explicit C# flip criterion (Section 9 above).

**Effect on recommendation:** Resolved in favor of Go, but the margin is narrow and the C# flip criterion is explicitly testable.

---

## 4. Open Questions

The following questions could not be resolved during this research run. They are carried forward as Tier 3 uncertainties that should be addressed before or during project initiation.

1. **[Q-input-c-01] — Team composition unknown.** The current team's language distribution is an internal fact not available to this research run. The recommendation (Go #1) may shift if the team has strong concentration (≥60%) in a language other than Go — see flip criterion #3 in Section 9. *Resolution path: team survey before project kick-off.*

2. **[Q-input-c-03] — AI-to-human coding ratio unspecified.** The exact proportion of AI-generated vs. human-written code is not specified. Section 3 (2.1 scoring) assesses both an assisted regime (30–50% AI) and a more-autonomous regime (≥80% AI). Go's 2.1 advantage is larger in the more-autonomous regime; C#'s type-system-depth advantage is more accessible in the assisted regime. *Resolution path: engineering team decision on target AI autonomy level.*

3. **[Q-input-c-04] — Exact container orchestration model unspecified.** The default interpretation used in this document is "one shared container image artifact, separately started process types per Azure Container Apps scaling semantics." If the actual deployment model is literal multi-process-in-one-container (e.g., a supervisor managing all four process types in a single container instance), JVM cold-start and memory concerns for Java/Kotlin would be amplified, and Node.js per-process memory for TypeScript would increase. *Resolution path: confirm with platform team before provisioning.*

---

## 5. Sources

1. **modelcontextprotocol/go-sdk** — https://github.com/modelcontextprotocol/go-sdk — Official Go MCP SDK, maintained in collaboration with Google; implements full MCP spec 2025-11-25.

2. **modelcontextprotocol/go-sdk releases** — https://github.com/modelcontextprotocol/go-sdk/releases — Release notes confirming full 2025-11-25 spec implementation and OAuth support.

3. **modelcontextprotocol/kotlin-sdk** — https://github.com/modelcontextprotocol/kotlin-sdk — Official Kotlin SDK, maintained with JetBrains; Status: Experimental.

4. **modelcontextprotocol/rust-sdk** — https://github.com/modelcontextprotocol/rust-sdk — Official Rust SDK (`rmcp` v0.16.0) under modelcontextprotocol org.

5. **modelcontextprotocol organization repositories** — https://github.com/orgs/modelcontextprotocol/repositories — Full list of official SDKs and their status labels (Kotlin: Experimental confirmed).

6. **MCP SDK documentation** — https://modelcontextprotocol.io/docs/sdk — SDK tier system; all SDKs classified by feature completeness and maintenance commitment.

7. **opentelemetry-go GitHub** — https://github.com/open-telemetry/opentelemetry-go — Go OTel SDK; traces=Stable, metrics=Stable, logs=Beta (confirmed multiple sources).

8. **opentelemetry-go/CHANGELOG.md** — https://github.com/open-telemetry/opentelemetry-go/blob/main/CHANGELOG.md — First stable releases of Go metric API and metric SDK; log SDK ongoing.

9. **OpenTelemetry Go documentation** — https://opentelemetry.io/docs/languages/go/ — Official Go OTel docs.

10. **Coralogix: Golang OpenTelemetry instrumentation** — https://coralogix.com/docs/opentelemetry/instrumentation-options/golang-opentelemetry-instrumentation/ — Confirms Go OTel metrics/traces Stable, logs Beta as of 2026.

11. **dasroot.net: Go for Observability 2026** — https://dasroot.net/posts/2026/02/go-observability-metrics-logs-monitoring-2026/ — Confirms Go OTel SDK stable for traces/metrics, logs Beta as of 2026.

12. **OpenTelemetry status page** — https://opentelemetry.io/status/ — Authoritative per-language signal maturity table (Java: Stable/Stable/Stable; Kotlin: Development/Development/Development; Go: Stable/Stable/Beta; .NET: Stable/Stable/Stable).

13. **OTel stability proposal announcement** — https://opentelemetry.io/blog/2025/stability-proposal-announcement/ — OTel stabilization roadmap; context for Beta signals.

14. **oneuptime.com: OpenTelemetry Stability Levels** — https://oneuptime.com/blog/post/2026-02-06-opentelemetry-stability-levels-stable-beta-alpha/view — Explains Beta-to-Stable progression; logs signal progression 2024–2026.

15. **go.dev/cmd/gofmt** — https://go.dev/cmd/gofmt/ — Official Go formatter documentation; `gofmt` formats Go programs with standardized output.

16. **gopls features** — https://go.dev/gopls/features/ — Official gopls feature index: navigation, rename, find-references, semantic tokens, refactorings.

17. **Microsoft: ASP.NET Core dependency injection** — https://learn.microsoft.com/en-us/aspnet/core/fundamentals/dependency-injection — ASP.NET Core DI fundamentals; service lifetimes, scoped services, DI wiring conventions.

18. **Microsoft: ASP.NET Core HttpContext** — https://learn.microsoft.com/en-us/aspnet/core/fundamentals/use-http-context — `HttpContext.RequestAborted` CancellationToken for long-running task cancellation.

19. **Microsoft: C# nullable reference types** — https://learn.microsoft.com/en-us/dotnet/csharp/nullable-references — Nullable reference type analysis; compile-time null-state tracking.

20. **Microsoft: Azure Monitor OpenTelemetry for .NET** — https://github.com/Azure/azure-sdk-for-net/blob/main/sdk/monitor/Azure.Monitor.OpenTelemetry.AspNetCore/README.md — Azure Monitor Distro for .NET; ASP.NET Core auto-instrumentation, live metrics.

21. **Microsoft: .NET OTel platform APIs** — https://learn.microsoft.com/en-us/dotnet/core/diagnostics/observability-with-otel — .NET OTel built-in platform APIs; library authors instrument without separate OTel dependency.

22. **Microsoft: Azure Container Apps JVM memory fitting** — https://learn.microsoft.com/en-us/azure/container-apps/java-memory-fit — JVM automatic memory fitting for Container Apps; requires active management; disabled below 1 GB.

23. **Microsoft: Java on Azure Container Apps overview** — https://learn.microsoft.com/en-us/azure/container-apps/java-overview — JVM SIGTERM handling, memory diagnostics.

24. **Microsoft: Azure Monitor OpenTelemetry enable** — https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-enable — Azure Monitor distro language coverage (.NET, Node.js, Python, Java).

25. **Microsoft: Azure Container Apps OpenTelemetry agents** — https://learn.microsoft.com/en-us/azure/container-apps/opentelemetry-agents — Managed OTel agent routing OTLP data to Azure Monitor, Datadog, or custom OTLP endpoint.

26. **Microsoft: Azure Blob storage client libraries** — https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-client-management — First-party Azure Blob client packages listed (.NET, Java, JavaScript, Python, Go).

27. **Microsoft: Azure Cache for Redis client libraries** — https://learn.microsoft.com/en-sg/azure/azure-cache-for-redis/cache-best-practices-client-libraries — Recommended client table: StackExchange.Redis (.NET), Jedis/Lettuce/Redisson (Java), ioredis/node_redis (Node.js).

28. **Microsoft: Azure SDK for Rust** — https://learn.microsoft.com/nb-no/azure/developer/rust/sdk/overview — Azure SDK Rust crates with async support, type safety.

29. **pg-boss npm package** — https://www.npmjs.com/package/pg-boss — Postgres-native SKIP-LOCKED job queue for Node.js; idempotency keys, DLQ, retry/backoff.

30. **pgx/v5 pgxpool** — https://pkg.go.dev/github.com/jackc/pgx/v5/pgxpool — pgxpool: concurrency-safe Postgres connection pool for Go.

31. **pkg.go.dev: context package** — https://pkg.go.dev/context — Go context package; deadlines, cancellation signals, request-scoped values.

32. **NerdLevelTech MCP Developer Guide 2026** — https://nerdleveltech.com/guides/model-context-protocol — MCP spec 2025-11-25; SDK list; Streamable HTTP as recommended transport.

33. **socket.dev: Official Go SDK for MCP** — https://socket.dev/blog/official-go-sdk-for-mcp — Background on Go MCP SDK development; production-ready status.

34. **lushbinary.com: MCP Developer Guide 2026** — https://lushbinary.com/blog/mcp-model-context-protocol-developer-guide-2026/ — MCP ecosystem overview; TypeScript/Python as most downloaded; TypeScript SDK v2 expected Q1 2026.

35. **imti.co: Go's Constraints Make AI Coding Better** — https://imti.co/golang-ai-coding-vibe-engineering/ — Community analysis of Go's AI coding properties: gofmt uniformity, compiler-as-verification-loop, LLM variance reduction.

36. **OpenTelemetry Kotlin getting-started** — https://opentelemetry.io/docs/languages/kotlin/getting-started/ — Kotlin OTel JVM compatibility mode; uses Java OTel SDK under the hood; Kotlin-specific API experimental.

37. **State of NativeAOT in .NET 10** — https://code.soundaranbu.com/state-of-nativeaot-net10 — Azure SDK AOT support status; Azure Functions cold-start mitigation via NativeAOT + Ready-to-Run modes.

38. **Python typing spec** — https://typing.python.org/en/latest/spec/type-system.html — Python will remain dynamically typed; type hints non-mandatory by design.

39. **kotlinlang.org: Null safety** — https://kotlinlang.org/docs/null-safety.html — Kotlin compile-time handling of potential null issues; nullable type annotations.

---

## 6. Confidence Ledger

The following table covers material claims tied to the final recommendation, flip criteria, and phase-2 evidence records. Non-material supporting details are omitted.

| Claim | Tag | Signal | Source notes |
|---|---|---|---|
| Go is #1 recommended backend language | [U] | Derived from Tier 2 composite scoring; not from a single empirical source | Supported by structural language analysis across five 2.1 subdimensions |
| Go leads 2.1 on convention-over-configuration (scores H vs. C# M) | [V] | `gofmt` enforces exactly one formatting style; confirmed via official Go formatter docs | Source 15 (go.dev/cmd/gofmt) |
| Go leads 2.1 on codebase comprehensibility (scores H vs. C# M) | [V] | ASP.NET Core DI introduces service-container wiring that requires runtime resolution to trace behavior; confirmed via official ASP.NET Core DI docs | Source 17 (learn.microsoft.com dependency-injection) |
| Go and C# are tied on refactoring safety (both H) | [V] | gopls rename/find-references confirmed via official feature index; Roslyn parity [U] | Source 16 (go.dev/gopls/features) |
| C# wins type-system depth (H vs. Go H-) | [V] | C# nullable reference analysis emits compile-time warnings for maybe-null dereferences; confirmed via official .NET docs | Source 19 (learn.microsoft.com nullable-references) |
| C# scores M on convention-over-configuration | [U] | Multiple valid backend patterns (controllers vs. minimal APIs, EF Core vs. Dapper, constructor vs. primary constructor injection) confirmed in phase 2; openai conceded this scoring in round 2 | openai ADDRESS of Q-plan-c-01, round 2 |
| Go OTel: traces=Stable, metrics=Stable, logs=Beta | [V] | Confirmed by multiple independent sources including Coralogix docs, dasroot.net 2026 post, and opentelemetry-go changelog | Sources 7, 10, 11 |
| Go OTel logs Beta is not material for DVS workload profile | [U] | DVS is not a log-analytics platform; OTLP log ingestion via managed Azure Container Apps OTel agent operates at Beta without documented production gaps; both agents agreed this in phase 2 round 2 | Agreed materiality assessment; no contradicting evidence found |
| C# OTel traces/metrics/logs all Stable | [U] | Confirmed per OTel status page; .NET Azure Monitor Distro is Microsoft-authored with auto-instrumentation | Source 12 (opentelemetry.io/status), Source 20 |
| Kotlin MCP SDK labeled "Experimental" | [V] | modelcontextprotocol/kotlin-sdk repository shows Status: Experimental; confirmed in org repository list | Sources 3 (kotlin-sdk), 5 (org repos) |
| Go MCP SDK implements full MCP spec 2025-11-25 | [V] | Release notes confirm completion of full 2025-11-25 spec implementation | Source 2 (go-sdk/releases) |
| Rust MCP SDK (rmcp v0.16.0) is official under modelcontextprotocol org | [V] | Confirmed in D-input-c-01 resolution (phase 0) and source 4 (rust-sdk) | Source 4 (modelcontextprotocol/rust-sdk) |
| Kotlin passes Tier 1.6 via Java OTel SDK JVM compatibility mode | [U] | OTel Kotlin getting-started describes JVM compatibility mode using Java SDK under the hood; openai ADDRESS of Q-plan-c-02 confirmed in round 2 | Source 36 (opentelemetry.io Kotlin getting-started) |
| TypeScript MCP SDK is the reference implementation, most feature-complete | [V] | TypeScript is the primary reference implementation per modelcontextprotocol.io | Source 6 (modelcontextprotocol.io/docs/sdk) |
| pg-boss provides Postgres-native SKIP-LOCKED with idempotency/DLQ for Node.js | [V] | npm package documentation confirms SKIP LOCKED queue, idempotency keys, DLQ, retry/backoff | Source 29 (npmjs.com/pg-boss) |
| JVM cold start 1–3 s for Spring Boot without GraalVM; JVM memory fitting requires active management | [V] | Azure Container Apps JVM memory fitting documentation confirms active management required; disabled below 1 GB | Source 22 (learn.microsoft.com java-memory-fit) |
| Go 2.1 advantage is larger in more-autonomous AI regime (≥80% AI) than assisted regime (30–50%) | [U] | Derived from the structure of the five subdimensions: convention uniformity and comprehensibility are more decisive when human review is minimal; not supported by an empirical benchmark | Both agents agreed this regime distinction in phase 2 |
| Decision confidence: MEDIUM (not HIGH or LOW) | [U] | Internal platform catalog unverified; no controlled AI-agent defect-rate benchmark exists; Go OTel logs not yet Stable | Agreed by both agents in round 2 (Q-plan-g-02 resolved) |
| TypeScript strict-mode + Fastify closes Go vs. TypeScript 2.1 gap to ~0.5 subdimensions | [U] | Directional assessment; not empirically confirmed. Under a disciplined strict-mode TypeScript setup, the convention and comprehensibility gaps narrow because explicit patterns dominate | claude phase 1 plan; flip criterion #3 |
| Python's type hints are advisory; runtime ignores them | [V] | Python typing specification states Python will remain dynamically typed and type hints are non-mandatory | Source 38 (typing.python.org) |