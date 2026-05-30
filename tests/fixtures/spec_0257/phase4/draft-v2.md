# Backend Language Choice — Document Verification Service

## Decision: C# (.NET 9/10)


---

## 1. Summary


After applying the brief's three-tier criteria framework to all seven candidates, **C# (.NET 9/10) is the recommended backend language** for the Document Verification Service's server-side modular monolith. [U] All seven candidates pass every Tier 1 hard constraint, so the decision is decided entirely at Tier 2, where criterion 2.1 (AI-coding-automation fitness) is explicitly highest-weight and load-bearing. [U] C# wins 2.1 on the combination of strong practical static typing with nullable-flow analysis, Roslyn-powered refactoring tooling, and ASP.NET Core convention uniformity; it remains strong on concurrency (2.2) and ecosystem maturity (2.3), and adequate-strong on operational fit (2.4). [U] Go is the closest challenger, winning the convention-uniformity sub-dimension of 2.1 and the operational profile on 2.4, but falling short on type-system depth and refactoring safety. [U] Python ranks last: its Weak score on the highest-weight criterion is decisive despite its strong ecosystem, and Rust ranks above Python but below TypeScript because AI-agent iteration friction is a more severe problem for this development model than TypeScript's runtime boundary gap. [U]

---

## 2. Findings


### 2.1 Methodology

This analysis applies the brief's three-tier framework strictly in sequence: Tier 1 binary pass/fail first, Tier 2 qualitative scoring next, Tier 3 tie-breakers only if Tier 2 produces no clear winner. [U] Scoring bands used throughout are **Strong / Adequate-Strong / Adequate / Weak / Poor**. [U]

Criterion 2.1 (AI-coding-automation fitness) is explicitly the highest-weight and load-bearing criterion: the winning candidate must win on 2.1, or the document must explain why 2.1 was not decisive. The Document Verification Service will be developed and maintained substantially by AI coding agents per the brief; the human/AI development ratio is unspecified but this framing justifies 2.1 remaining highest-weight throughout. [U]

Candidates are normalized at language-plus-runtime level: Go (standard toolchain), Rust (Tokio/stable), Python (CPython 3.12+/asyncio), TypeScript (Node.js LTS 22), C# (.NET 9/10 on CLR), Kotlin (JVM 21/Coroutines), Java (JVM 21/Project Loom/Spring Boot). [U] Java and Kotlin are scored jointly on JVM-level criteria (cold-start, memory, OTel SDK availability) and separately on language-level criteria (type system, convention uniformity). [U]

Two design-level scope decisions apply uniformly: Tier 1.1 (platform support) is treated as a provisional PASS for all seven candidates given Azure Container Apps' container-image-agnostic deployment model, subject to internal vetted-catalog confirmation. [U] Tier 1.2/1.7 (RLS-aware Postgres connection pooling) is treated as a design-pattern requirement — SET LOCAL role before query, release on return — applied equally across all candidates, not a language eliminator. [U]

---

### 2.2 Tier 1 — Hard-Constraint Pass/Fail

All seven candidates receive a provisional PASS on all seven Tier 1 criteria. No eliminations.

#### Criterion 1.1 — Platform support (Azure App Service / Container Apps)

**All seven: PASS.** Azure Container Apps accepts any OCI-compliant container image; the runtime inside the image is irrelevant to the orchestrator. [U] Subject to internal vetted-catalog confirmation, which is unverifiable externally.

#### Criterion 1.2 / 1.3 — Azure Postgres, Blob, Redis, Key Vault SDKs

**All seven: PASS.** Each language has at least one mature driver for Azure Postgres, plus first-party or mature community SDKs for Blob, Redis, and Key Vault. [U] Named drivers: Npgsql (.NET), pgx/v5 (Go), sqlx (Rust), asyncpg/psycopg3 (Python), pg/node-postgres (TypeScript), HikariCP + r2dbc-postgresql (JVM). [U] Azure provides first-party SDKs for Blob, Redis, and Key Vault for .NET, Java, Python, JavaScript/TypeScript, and Go. [U] Rust relies on community crates (`azure_storage`, `azure_security_keyvault`) that are sufficiently mature for production. [U]

#### Criterion 1.4 — MCP server library

**All seven: PASS** — but not equally mature. The official MCP SDK page lists TypeScript, Python, C#, and Go as Tier 1, Java and Rust as Tier 2, and Kotlin as TBD. [V] The MCP tiering system defines Tier 1 as fully supported with complete protocol implementation, Tier 2 as actively maintained and working toward full protocol support, and Tier 3 as experimental or partial. [V]

An independent community audit of the Kotlin SDK (April 2, 2026, GitHub issue #2512) found it at **Tier 3** — the Kotlin SDK has excellent server conformance (100%) and strong client conformance (90%), but lacks a stable 1.0.0 release, has significant documentation gaps (25/48 features documented with examples), and is missing required policy documents (roadmap, versioning policy). The audit found: Tier 2: FAIL — 5/8 requirements met (failing: stable release, documentation, roadmap). [V]

All seven pass the brief's Tier 1.4 criterion ("mature library or feasible to implement without significant friction") because the Kotlin SDK exists, supports full server protocol conformance, and a JetBrains-backed team maintains it. **Kotlin is the weakest-margin Tier 1.4 pass.** [U]

#### Criterion 1.5 — OAuth 2 / OIDC client

**All seven: PASS.** Mature OIDC client libraries exist in all seven ecosystems. [U]

#### Criterion 1.6 — OpenTelemetry OTLP exporters

**All seven: PASS.** The OTel logs signal is stable at the specification level. For the individual language-specific implementations of the Logs API & SDK, the status varies. [V] When looking for a status, make sure to look for the status from the right component page — the status of a signal in the specification may not be the same as the signal status in a particular language SDK. [V] Per the official opentelemetry.io/status/ page, per-language log SDK maturity is: C#/.NET and Java = Stable; Go = Beta; JavaScript/Python = Development; Kotlin-specific SDK = Development across all signals; Rust = Beta across all signals. [V — opentelemetry.io/status/] All seven candidates have usable OTLP exporters for traces, metrics, and logs in production; the variation is in SDK maturity level, not in feasibility.

#### Criterion 1.7 — Concurrent workers, safe Postgres pooling

**All seven: PASS.** All candidates have concurrency primitives and connection pooling patterns sufficient for the DVS worker architecture (API process, outbox worker, analysis worker, scheduled tasks). [U]

#### Tier 1 Summary Table

| Candidate | 1.1 Platform | 1.2/1.3 Azure SDKs | 1.4 MCP SDK | 1.5 OIDC | 1.6 OTel | 1.7 Workers | **Verdict** |
|---|---|---|---|---|---|---|---|
| C# (.NET) | ✓ | ✓ | ✓ (Tier 1) | ✓ | ✓ | ✓ | **PASS** |
| Go | ✓ | ✓ | ✓ (Tier 1) | ✓ | ✓ | ✓ | **PASS** |
| Java | ✓ | ✓ | ✓ (Tier 2) | ✓ | ✓ | ✓ | **PASS** |
| Kotlin | ✓ | ✓ | ✓ (TBD/Tier 3†) | ✓ | ✓ | ✓ | **PASS** |
| TypeScript | ✓ | ✓ | ✓ (Tier 1) | ✓ | ✓ | ✓ | **PASS** |
| Rust | ✓ | ✓ | ✓ (Tier 2) | ✓ | ✓ | ✓ | **PASS** |
| Python | ✓ | ✓ | ✓ (Tier 1) | ✓ | ✓ | ✓ | **PASS** |

_† Tier 1.1: subject to internal vetted-catalog confirmation. Tier 1.4 Kotlin: listed as TBD on public MCP SDK page; independent audit (April 2, 2026) found Tier 3 — no stable 1.0.0 release, documentation gaps. Still passes brief criterion as feasible to implement without significant friction._

---

### 2.3 Tier 2 — AI-Coding-Automation Fitness (Criterion 2.1, Highest Weight, Load-Bearing)

Criterion 2.1 is disaggregated into three sub-dimensions: **(A) type-system depth and runtime soundness**, **(B) convention uniformity and "one obvious way"**, and **(C) refactoring safety and LSP quality.** The winning candidate must win on 2.1 overall, or the document must explain why 2.1 was not decisive.

#### Sub-Dimension A: Type-System Depth

**C# (.NET) — Strong.** C# provides strong practical static typing: nullable reference types use compiler static analysis to track null-state and warn when potentially null values are dereferenced unsafely. [U] Exhaustive switch expressions with pattern matching, record types for structural immutability, and Roslyn's compile-time feedback give AI agents immediate correction signals on incorrect refactors. [U] Described as "strong practical static typing with nullable-flow analysis," not "nominally sound" — C# NRT is flow-based static analysis, not full runtime enforcement, and discriminated unions require `OneOf` or similar third-party packages rather than being first-class language features. [U]

**Kotlin (JVM 21) — Strong.** Kotlin's type system is the deepest in the JVM tier: nullable/non-nullable distinctions at the language level (enforced by the compiler), sealed classes for exhaustive algebraic data types, data classes, and inline value classes. [U] JetBrains-native LSP support is first-class. [U]

**Rust (Tokio/stable) — Strong (correctness) / Adequate (AI iteration).** Rust's type system is the most expressive of the seven: ownership, lifetimes, sum types with exhaustive match. [U] However, the lifetime/borrow-checker imposes unusually high cognitive load on AI agents — generated code frequently fails to compile due to lifetime errors, creating long iteration cycles. [U] The type-system depth benefit is real but is capped for this use case by iteration-loop friction.

**Java (JVM 21) — Adequate-Strong.** Java 21's sealed classes and pattern matching in switch are genuinely good, but more ceremony-heavy than Kotlin's equivalent. [U] Spring Boot's `@Component`, `@Service`, `@Transactional`, `@Cacheable`, and `@Async` annotations change runtime call semantics in ways opaque to static analysis — the proxy-bypass (self-invocation) problem being a canonical example of the kind of "decorators that change call semantics" the 2.1 criteria explicitly penalize. [U]

**TypeScript (strict mode) — Adequate-Strong.** Rich type-system expressiveness: discriminated unions, conditional types, template literal types, and exhaustiveness checks. [U] However, type erasure at runtime means AI-generated code that passes the TypeScript checker can still fail at runtime boundaries (JSON deserialization, external calls) unless runtime validation (Zod, Valibot) is systematically paired. [U] This is a milder, distinct risk from Python's.

**Go — Adequate.** Go is structurally typed with generics (Go 1.18+) having improved the situation, but Go lacks first-class pattern matching, sealed types, or exhaustiveness checking. [U] AI agents writing domain models must rely on convention rather than type-system enforcement. [U]

**Python (CPython 3.12+) — Weak.** Python's type annotations are optional and not enforced at runtime by the interpreter. [U] Dynamic dispatch, magic methods (`__getattr__`, `__setattr__`), and decorator semantics are exactly the kind of implicit behavior the 2.1 criteria explicitly penalize as "harder for LLMs to reason about across a large codebase." [U]

#### Sub-Dimension B: Convention Uniformity

**Go — Strong.** Go has a single formatter (`gofmt`), a single module system (`go mod`), a single error-handling convention (explicit `error` return), and a deliberately small standard library surface. [U] This minimal surface area means AI agents have very few axes on which to diverge from idiomatic style. [U]

**C# — Adequate-Strong.** The ASP.NET Core + EF Core stack establishes strong conventions: dependency injection via `IServiceCollection`, middleware pipeline, repository/service patterns are widely standardized in the training corpus. [U] The .NET ecosystem historically offers multiple patterns for the same problem (multiple DI lifetimes, Entity Framework vs. Dapper vs. raw Npgsql, multiple serialization choices), creating a wider choice surface than Go — but AI agent training on ASP.NET Core idioms mitigates divergence risk. [U]

**Java — Adequate.** Spring Boot's conventions are widely known and heavily represented in AI training corpora. [U] Annotation-heavy patterns (`@RestController`, `@Service`, etc.) are consistent but increase implicit-behavior surface area. [U]

**Kotlin — Adequate.** Kotlin's multi-paradigm nature (OO + functional + coroutines + companion objects + extension functions) produces more stylistic variation than Go or C# within a codebase. [U]

**TypeScript — Adequate-Weak.** Significant framework fragmentation: Express, Fastify, Hono, NestJS — each with distinct patterns. [U] NestJS adds strong conventions but introduces decorator-heavy implicit semantics of the same kind the 2.1 criteria penalize. [U]

**Python — Weak.** High convention fragmentation even within the FastAPI ecosystem; magic methods and runtime monkey-patching make cross-file semantic reasoning harder for LLMs. [U]

**Rust — Adequate.** Cargo and clippy enforce idiomatic conventions well. [U] Borrow-checker friction dominates the AI iteration loop regardless of convention clarity. [U]

#### Sub-Dimension C: Refactoring Safety and LSP Quality

**C# — Strong.** Roslyn is the most battle-tested language-server refactoring engine for typed languages in the mainstream. [U] Rename-symbol, extract interface, move type, and generate-boilerplate-from-interface all work reliably across a modular monolith with multiple bounded contexts. AI agents (Claude Code, GitHub Copilot) have deep training on C# refactoring patterns. [U]

**Kotlin / Java — Strong.** IntelliJ IDEA's refactoring engine is mature and JVM-native; JVM reflective type information makes rename/find-references reliable. [U]

**Go — Adequate.** `gopls` is good, but Go's structural typing means rename-symbol can accidentally un-implement an interface by renaming a method that was the sole satisfier of an interface constraint — a silent failure mode. [U]

**TypeScript — Adequate.** `tsserver` handles rename-symbol and find-references well under strict mode. [U] Large codebases with dynamic `require()` patterns or extensive decorator use can confuse the LSP. [U]

**Rust — Adequate.** `rust-analyzer` is excellent in quality; slow compilation lengthens the feedback loop that AI agents depend on for test-driven iteration. [U]

**Python — Weak.** Duck typing and dynamic dispatch mean rename-symbol is often unsafe in large codebases — the tool cannot reliably determine whether a renamed method is called reflectively or via dynamic lookup. [U]

#### 2.1 Summary Table

| Candidate | Sub-A (type depth) | Sub-B (convention) | Sub-C (refactoring) | **2.1 Overall** |
|---|---|---|---|---|
| **C# (.NET)** | Strong | Adequate-Strong | Strong | **Strong** |
| **Go** | Adequate | Strong | Adequate | **Adequate-Strong** |
| **Kotlin** | Strong | Adequate | Strong | **Adequate-Strong** |
| **Java** | Adequate-Strong | Adequate | Strong | **Adequate-Strong** |
| **TypeScript** | Adequate-Strong | Adequate-Weak | Adequate | **Adequate** |
| **Rust** | Strong (capped) | Adequate | Adequate | **Adequate (iteration-capped)** |
| **Python** | Weak | Weak | Weak | **Weak** |

**C# wins 2.1 overall** on the combination of type-system depth and refactoring safety. Go wins the convention-uniformity sub-dimension but scores lower on type depth and refactoring safety. This is the load-bearing finding that drives the #1 ranking. [U]

---

### 2.4 Tier 2 — Concurrency Model Fit (Criterion 2.2)

The DVS runs four process types: API (hundreds of concurrent connections), outbox worker (at-least-once delivery), analysis worker (`FOR UPDATE SKIP LOCKED` queue with 10s document-AI timeouts), and scheduled tasks. All languages must handle these concurrently without lock thrashing or blocking-thread-per-request overhead.

**C# (.NET) — Strong.** `async`/`await` on `Task<T>` provides non-blocking concurrency for all four process types. `Channel<T>` primitives map cleanly to the outbox/analysis worker fan-out patterns. `CancellationToken` propagation is idiomatic for the 10s timeout requirement. Npgsql's `NpgsqlDataSource` provides connection pooling with per-connection session context, enabling RLS session management. [U]

**Go — Strong.** Goroutines are the textbook fit for this workload: hundreds of concurrent HTTP requests map directly to goroutines, `context.Context` is the standard cancellation primitive across the codebase, and the SKIP LOCKED polling pattern maps naturally to a goroutine fan-out worker pool pulling from a channel. `net/http` is non-blocking by default. [U]

**Java (JVM 21) — Strong.** Project Loom virtual threads eliminate the traditional blocking-thread-per-request penalty: blocking Postgres calls are safe at high concurrency without reactive overhead, which substantially simplifies the analysis worker pattern relative to earlier JVM versions. [U]

**Kotlin (JVM 21) — Strong.** Kotlin coroutines with structured concurrency (`CoroutineScope`, `SupervisorJob`) align naturally with the DVS's worker lifecycle. Ktor or Spring Boot reactive handle hundreds of concurrent HTTP connections. [U]

**Rust (Tokio) — Strong.** Tokio's async runtime handles the I/O-bound patterns at high efficiency. [U] The iteration-velocity concerns from 2.1 persist but do not affect the runtime's ability to handle the concurrency shape.

**TypeScript (Node.js) — Adequate.** Node.js's event loop is non-blocking for I/O, but single-threaded: the outbox and analysis workers require `worker_threads` or separate processes to avoid blocking, and coordination between workers and the API process adds complexity. [U] The brief's "separate processes inside the same container image" pattern mitigates this but does not eliminate the coordination overhead.

**Python (asyncio) — Adequate.** `asyncio` fits the I/O-bound pattern and document-AI calls (10s timeouts, I/O-bound) are handled adequately. [U] The GIL constrains true parallelism for CPU-adjacent work in CPython 3.12, with free-threading (PEP 703) still experimental. [U]

No candidate is materially disadvantaged for the DVS concurrency shape. The five Strong candidates are effectively tied on 2.2.

---

### 2.5 Tier 2 — Ecosystem Maturity (Criterion 2.3)

Key DVS library needs: document parsing (PDF, image, MIME), AEAD cryptographic primitives (GDPR crypto-erasure), JSON Schema / MCP tool schema validation, background job orchestration (idempotency keys, retry, dead-letter), HTTP client with circuit breakers.

**C# (.NET) — Strong.** Mature libraries for all five needs: `PdfPig`/`iTextSharp` for PDF parsing; `System.Security.Cryptography` with AES-GCM for AEAD; `NJsonSchema`/`System.Text.Json` for JSON Schema; `Hangfire`/`MassTransit` for background jobs with full durable-queue semantics; `Polly` v8 (now Microsoft-owned) for circuit breakers, retry, and bulkhead patterns. First-party Azure SDKs (`Azure.Storage.Blobs`, `Azure.Security.KeyVault.Secrets`, `Azure.Identity`) cover all required services. [U]

**Python — Strong.** Strongest of the seven for document processing (`pdfplumber`, `Pillow`, `python-magic`) and document AI provider abstraction (LangChain, LiteLLM for multi-provider routing). [U] `cryptography` library for AEAD; `pydantic` / `jsonschema` for schema validation; `celery`/`arq` for background jobs; `tenacity` for retry/circuit-break patterns. [U]

**Java / Kotlin (JVM) — Strong.** Apache PDFBox for PDF processing; Bouncy Castle for AEAD and key wrapping; `resilience4j` for circuit breakers and bulkhead; Spring Boot ecosystem for background jobs, HTTP clients, and schema validation. [U]

**TypeScript — Adequate-Strong.** `pdf-lib`/`pdf-parse` for PDF; `sharp` for image handling; Node.js `crypto` (WebCrypto AEAD) for cryptographic primitives; `zod` for JSON Schema and runtime validation; `bull`/`bullmq` for background jobs; `opossum` for circuit breakers. [U] The ecosystem is deep but shows more library churn than JVM/C#. [U]

**Go — Adequate.** pdfcpu is a PDF processing library written in Go that is still Alpha — bugfixes are committed on the fly and will be mentioned in the next release notes. pdfcpu is stable but still Alpha and occasionally undergoing heavy changes. [V] UniPDF (unidoc) is commercially licensed, adding procurement friction for a production service. [U] Background-job orchestration is DIY or via `asynq` (third-party, narrower in scope than Hangfire or Celery). [U] AEAD cryptographic primitives and HTTP circuit breakers (`gobreaker`) are adequate. *Context note: this gap narrows materially if the DVS document intake pipeline is primarily MIME/file-size validation plus AI-provider handoff rather than deep PDF parsing — a likely scenario given that document AI does the heavy lifting per the brief.* [U]

**Rust — Adequate.** `lopdf`/`pdf-extract` are less mature than JVM or Python equivalents; `ring`/`rust-crypto` for AEAD is first-class; circuit breakers via manual Tokio patterns rather than a mature framework. [U] Ecosystem is thinner than JVM/C# for the full DVS stack. [U]

---

### 2.6 Tier 2 — Observability and Operational Fit (Criterion 2.4)

**OpenTelemetry SDK status:** When looking for a status, make sure to look for the status from the right component page — the status of a signal in the specification may not be the same as the signal status in a particular language SDK. [V] Per the official opentelemetry.io/status/ page, per-language log SDK maturity: C#/.NET and Java = Stable across all signals; Go = Stable/Stable/Beta (traces/metrics/logs); JavaScript/Python = Development for logs; Kotlin-specific SDK = Development across all signals; Rust = Beta across all signals. [V — opentelemetry.io/status/] **OTel signal maturity is not used as a primary 2.4 differentiator** — structural operational factors (startup time, memory footprint, GC pause profile) dominate 2.4 scoring, and collector-based log bridging is the standard production path for languages where the log SDK is not yet Stable. [U]

**Go — Strong.** Go compiles to a single static binary with minimal startup overhead (~10–50ms for a typical HTTP server). [U] Container images are small. No GC pause concerns for the DVS's throughput profile. Go OTel logs are Beta-labeled but this is not a practical production blocker given collector-based log bridging patterns. [U]

**Rust — Strong (technically).** Similar to Go on binary size and startup time; Rust OTel is Beta across signals but Tokio's async model and minimal runtime are the dominant 2.4 factors. [U] The iteration-velocity concerns from 2.1 persist but do not affect operational fit.

**C# (.NET 9/10) — Adequate-Strong (conditionally Strong).** Startup has improved substantially in .NET 9. Native AOT (available since .NET 8) can produce near-native startup times comparable to Go. Without AOT on a scale-to-zero scenario, typical startup is 100–400ms for an ASP.NET Core application. [U] *Conditionally Strong if Native AOT is used or min replicas ≥ 1 (standard for a B2B service); Adequate-Strong otherwise.* OTel .NET SDK is Stable across all signals. [U] Native AOT feasibility depends on the dependency graph — reflection-heavy libraries may be incompatible; see flip criteria below.

**Python — Adequate.** asyncio startup is fast; memory overhead grows with imported libraries. OTel Python log SDK is Development-status but Collector-based bridging works in production. [U]

**TypeScript (Node.js) — Adequate.** Startup 200–500ms with full dependency loading; moderate memory footprint. OTel JavaScript log SDK is Development-status. [U]

**Kotlin / Java (JVM) — Adequate (conditional).** JVM startup time for a Spring Boot application is 2–5 seconds without optimization; baseline memory is higher than Go/Rust/C#. [U] *Mitigated if min replicas ≥ 1 — which is the expected configuration for a B2B production service, though not confirmed from this run.* GraalVM Native Image addresses cold-start but adds significant build complexity. [U] **Kotlin JVM deployments should use the Java OTel SDK** (Stable across all signals) rather than the Kotlin-specific OTel SDK (Development status). [U]

#### 2.4 Summary

| Candidate | Memory/cold-start | OTel practical | GC profile | **2.4 Overall** |
|---|---|---|---|---|
| Go | Strong (static binary) | Adequate (Beta logs, bridging OK) | Strong | **Strong** |
| Rust | Strong (static binary) | Adequate (Beta, bridging OK) | Strong | **Strong** |
| C# (.NET) | Adequate-Strong† | Strong (Stable OTel) | Adequate-Strong | **Adequate-Strong** |
| Python | Adequate | Adequate | Adequate | **Adequate** |
| TypeScript | Adequate | Adequate | Adequate | **Adequate** |
| Java (JVM) | Adequate (conditional)‡ | Strong (Stable OTel) | Adequate | **Adequate (conditional)** |
| Kotlin (JVM) | Adequate (conditional)‡ | Strong (via Java OTel SDK) | Adequate | **Adequate (conditional)** |

_† Conditionally Strong with Native AOT or min replicas ≥ 1._
_‡ Conditionally Adequate; Cold-start mitigated if min replicas ≥ 1._

---

### 2.7 Tier 2 — Consolidated Scoring and Composite Ranking

| Candidate | 2.1 AI-coding | 2.2 Concurrency | 2.3 Ecosystem | 2.4 Ops/OTel | **Tier 2 composite** |
|---|---|---|---|---|---|
| **C# (.NET)** | **Strong** | Strong | Strong | Adequate-Strong | **#1** |
| **Go** | Adequate-Strong | Strong | Adequate | Strong | **#2** |
| **Java** | Adequate-Strong | Strong | Strong | Adequate (conditional) | **#3** |
| **Kotlin** | Adequate-Strong | Strong | Strong | Adequate (conditional) | **#4** |
| **TypeScript** | Adequate | Adequate | Adequate-Strong | Adequate | **#5** |
| **Rust** | Adequate (capped) | Strong | Adequate | Strong | **#6** |
| **Python** | Weak | Adequate | Strong | Adequate | **#7** |

**Rationale for ordering:**
- C# wins on 2.1 (load-bearing). Go wins convention-uniformity sub-B and operational 2.4; loses on type-system depth sub-A and refactoring safety sub-C. The C# edge over Go on 2.1 is narrow but consistent across two sub-dimensions vs. one. [U]
- Java ranks above Kotlin (#3 vs #4) due to stronger MCP tier position (Tier 2 GA vs. Tier 3 audit result) and a simpler mainstream backend convention space, despite Kotlin's stronger language-level type expressiveness. [U]
- TypeScript ranks #5 — not eliminated, but framework fragmentation, NestJS decorator-heavy implicit semantics, and runtime type erasure are genuine 2.1 penalties that prevent ranking above the JVM candidates or C#/Go. [U]
- Rust ranks #6 above Python because Python's **Weak** 2.1 score is a more fundamental problem for an AI-agent-maintained modular monolith than Rust's iteration-velocity penalty — the latter is severe but addressable with CI guardrails and human review of compile-failing patches. [U]
- Python ranks #7 despite the strongest ecosystem depth (2.3) and a Tier 1 MCP SDK — Weak on the highest-weight criterion is decisive under the brief's explicit weighting. [U]

---

### 2.8 Tier 3 — Tie-Breaker Criteria (Informational — Tier 2 Produced a Clear Winner)

Tier 3 is not decisive. Noted for completeness and flip-criteria context. [U]

**3.1 Hiring market depth:** C#, Java, and Python have the deepest enterprise-oriented hiring pools in European markets. [U] Go and Kotlin are healthy but somewhat shallower. No candidate should be eliminated on this basis; this is background context for the flip criteria. [U]

**3.2 Build / iteration speed:** Go is the clear Tier 3 winner: `go build` completes in seconds for moderate codebases, producing a self-contained binary. [U] C# is acceptable with incremental build caching (`dotnet build` with SDK incremental compilation). [U] Rust is the slowest. Python and TypeScript have near-instant type-check feedback via pyright/tsc but slower runtime startup. [U]

**3.3 Full-stack alignment (TypeScript bias check):** The frontend uses Lit web components (and potentially React framing). TypeScript sharing a language with the frontend is a Tier 3 convenience, not a structural advantage. [U] Per the brief's explicit guidance and the agreed interpretation, this does not override the 2.1 analysis. [U]

---

### 2.9 Final Ranking with Narrative Rationale

#### #1 — C# (.NET 9/10 on CLR)

C# wins on 2.1 — the highest-weight, load-bearing criterion — through the combination of: strong practical static typing with nullable-flow analysis enforced by the compiler; exhaustive switch expressions with pattern matching; Roslyn-powered type-aware refactoring (rename-symbol, extract interface, move type, generate boilerplate) that works reliably across a modular monolith with multiple bounded contexts; and ASP.NET Core + EF Core convention depth. [U] It is strong on 2.2 (`async`/`await`, `Channel<T>`, `CancellationToken`) and 2.3 (mature libraries for all five DVS stack needs, first-party Azure SDKs). On 2.4, it is Adequate-Strong — conditionally Strong with Native AOT or min replicas ≥ 1. The official MCP SDK is Tier 1 with direct Microsoft backing. [U]

The case for C# is not "Azure plus .NET is the natural fit" — that reasoning is explicitly rejected by the brief. The case is that C# earns #1 on the criteria that matter most for an AI-agent-maintained service, independent of vendor alignment. [U]

#### #2 — Go (standard toolchain)

Go is the closest challenger and a genuinely strong alternative. It wins the convention-uniformity sub-dimension of 2.1 and the operational profile on 2.4 (static binary, fast startup, minimal GC concerns). [U] It falls short of C# on type-system depth (lacks sealed types, first-class pattern matching, exhaustiveness checking) and refactoring safety (structural typing means gopls rename-symbol can silently un-implement interfaces). [U] Go also carries ecosystem gaps on document parsing (pdfcpu is self-labeled Alpha [V]) and background-job orchestration (no Hangfire/Celery equivalent). [U] The official Go MCP SDK is actively maintained. [U]

The C# vs. Go decision is the closest call in this analysis. Go would be a defensible #1 if an internal pilot demonstrated substantially fewer AI-agent review errors in Go's simpler semantic model.

#### #3 — Java (JVM 21 / Project Loom / Spring Boot)

Java earns #3 through strong JVM ecosystem depth, modern language features (sealed classes, records, pattern matching in switch), and Project Loom virtual threads that eliminate the old blocking-thread-per-request penalty. [U] Java ranks above Kotlin due to a stronger MCP tier position (Tier 2 GA, v1.0.0 released February 2026 [V]) and a simpler mainstream backend convention space. [U] The JVM cold-start conditional penalty (2–5 second startup for Spring Boot without optimization) is mitigated if min replicas ≥ 1, which is the expected configuration for a B2B production service. [U]

#### #4 — Kotlin (JVM 21 / Coroutines)

Kotlin has the strongest language-level type system in the JVM tier: nullable/non-nullable distinctions at language level, sealed classes for exhaustive ADTs, data classes, inline value classes. [U] It falls below Java due to weaker MCP SDK maturity (Tier 3 per April 2026 audit, lacking a stable 1.0.0 release and with significant documentation gaps [V]) and greater convention fragmentation from Kotlin's multi-paradigm design (OO + functional + coroutines + companion objects + extension functions). [U] Shares Java's JVM cold-start conditional penalty. If Kotlin's MCP SDK reaches Tier 2 and the deployment spec confirms min replicas ≥ 1, the Java vs. Kotlin ordering may reverse — see flip criteria below. [U]

#### #5 — TypeScript (Node.js LTS 22)

TypeScript passes all Tier 1 constraints comfortably and carries the TypeScript reference implementation as its MCP SDK (Tier 1). [U] It is held back on 2.1 by: runtime type erasure requiring systematic Zod/Valibot discipline at all external boundaries (a milder risk than Python's, but real); Node.js's single-threaded event loop requiring worker_threads or separate processes for the outbox and analysis workers; and NestJS decorator-heavy implicit semantics if NestJS is the chosen framework. [U] Full-stack alignment with the Lit frontend is a Tier 3 convenience, explicitly not a Tier 2 signal per the brief and agreed interpretation. [U]

#### #6 — Rust (Tokio / stable)

Rust has the strongest static-safety story of the seven candidates and is technically strong on concurrency (Tokio) and operations (static binary, low memory). [U] It ranks below TypeScript because AI-agent iteration friction — borrow-checker/lifetime errors causing compilation failures, longer compile-test cycles — is a more severe problem for the DVS's development model than TypeScript's runtime boundary gap. [U] The MCP SDK is Tier 2; the Azure SDK for Rust is newer and more churn-prone than the mainstream SDKs. [U] Rust would move up only if the service's constraints change toward very low memory footprint, high-throughput local document parsing, or security-critical native processing where Rust's static guarantees become load-bearing.

#### #7 — Python (CPython 3.12+ / asyncio)

Python has the strongest ecosystem depth of the seven candidates for document processing and AI provider abstraction, and carries a Tier 1 MCP SDK. [U] It ranks last because its Weak score on the highest-weight criterion is decisive under the brief's explicit weighting: optional typing, dynamic runtime semantics, and the weakest refactoring-safety profile of any candidate create the most severe combination of 2.1 risks for an AI-agent-maintained modular monolith. [U] Python's strengths do not compensate for this under the stated criteria. [U]

---

### 2.10 Decision Confidence

**MEDIUM-HIGH.**

C# wins the highest-weight criterion while remaining strong enough on concurrency, ecosystem, and operations, with no serious gap on Tier 1 constraints. [U] The main uncertainty source is the close C# vs. Go call on the 2.1 convention-uniformity sub-dimension — Go is a genuine, well-supported alternative — combined with unverifiable internal team expertise and deployment-spec assumptions (scale-to-zero vs. min replicas ≥ 1). [U]

**Single evidence item most likely to shift confidence one level:** An internal AI-agent implementation pilot comparing C# and Go on a representative DVS slice — tenant-scoped Postgres/RLS session management, `FOR UPDATE SKIP LOCKED` analysis worker, MCP tool definition, outbox event emission, and OTel trace propagation through worker boundaries — under identical review constraints, would be the most direct evidence available to either confirm or challenge the 2.1 ordering. [U]

---

### 2.11 Flip Criteria (Explicit and Testable)

Each condition below, if confirmed, changes the ranking in the stated direction. All are testable against artifacts that exist or can be created.

1. **Go overtakes C# (#2 → #1).** An internal pilot or published benchmark demonstrates that AI coding agents (Claude Code, Copilot) produce materially fewer compilation-passing-but-logically-incorrect refactors in Go vs. C# on the DVS's code patterns (domain event modeling, RLS session management, typed MCP tool schemas, bounded-context boundaries). *Testable: check results of such a pilot or any SWE-bench-derived language-specific benchmark covering these patterns.* [U]

2. **JVM cold-start penalty confirmed mitigated (Java/Kotlin upward).** Internal deployment spec confirms min replicas ≥ 1 for the DVS API process, eliminating the JVM cold-start penalty on 2.4. If confirmed AND internal JVM production expertise strongly favors Kotlin, Kotlin could move to a genuine three-way tie with C# and Go for positions #1–#3. *Testable: read the deployment spec and run an internal skills survey.* [U]

3. **Kotlin overtakes Java (#4 → #3).** Kotlin's MCP SDK reaches at least Tier 2 status (stable 1.0.0 release, documentation requirements met per the official tiering system). Combined with a min-replicas ≥ 1 deployment spec confirmation, Kotlin's stronger language-level type system would tip the Java vs. Kotlin balance in Kotlin's favor. *Testable: check github.com/modelcontextprotocol/kotlin-sdk for a 1.0.0 release tag.* [U]

4. **Native AOT confirmed infeasible for C# in the DVS stack.** If the DVS's actual dependency graph includes reflection-heavy libraries incompatible with .NET Native AOT (e.g., certain EF Core features, certain middleware), the conditional 2.4 strength for C# on scale-to-zero scenarios is not achievable. This would not drop C# below #1 — the gap with Go is driven by 2.1, not 2.4 — but it would narrow the operational lead over Go on 2.4 and make the flip condition in item 1 easier to trigger. *Testable: audit the DVS dependency list against dotnet/runtime Native AOT compatibility requirements.* [U]

5. **TypeScript full-stack alignment becomes a hard architectural constraint (#5 → #1).** If the frontend team mandates shared types via a monorepo integration (shared Zod schemas, tRPC contracts, or Lit component prop types generated from a shared schema), TypeScript's Tier 3 alignment advantage becomes a de facto Tier 1 requirement, overriding the 2.1 ordering entirely. *Testable: confirm with the frontend team whether they intend to share type definitions with the backend at build time.* [U]

6. **Strong asymmetric internal expertise in Go or Kotlin.** If an internal skills survey reveals substantial production Go or Kotlin experience in the team, Tier 3 criteria (3.1 hiring market / team continuity) would elevate those candidates into functional top-tier contention for a close race. *Testable: internal skills survey.* [U]

---

### 2.12 Analysis Precision Notes

**C# vs. Go on 2.1 — closest call in the analysis.** Go wins the convention-uniformity sub-dimension decisively; C# wins type-system depth and refactoring safety. Both agents agreed C# edges ahead on the overall 2.1 score, but the margin is the narrowest scoring call in this document. A reader who weights convention uniformity more heavily than type-system depth in the AI-agent context would reach a different #1. [U]

**Java vs. Kotlin ordering — resolved by MCP evidence.** Both agents agreed Java #3 and Kotlin #4, with the deciding margin being Java's Tier 2 MCP SDK (v1.0.0 GA, February 2026) vs. Kotlin's Tier 3 audit result (April 2026, lacking stable release and documentation). Kotlin has the stronger language-level type system and would be the preferred JVM language on 2.1 sub-dimension A alone. The ordering reflects the MCP evidence combined with Java's simpler convention space. If the MCP condition clears, the ordering may reverse. [U]

**OTel SDK maturity — precision note.** The OTel logs signal is stable at the *specification* level as of mid-2025; per-language SDK implementation maturity varies materially. The official opentelemetry.io/status/ page is the authoritative reference. [V — opentelemetry.io/status/] OTel signal maturity was not used as a primary 2.4 differentiator in this analysis — structural factors (startup time, memory footprint, GC pause profile) dominate 2.4 scoring, and collector-based log bridging provides a viable production path for languages where the log SDK is Beta or Development. [U]

---

## 3. Disagreements Left Open


No carry-forward disagreements remain. All substantive disagreements (D-plan-c-01 through D-plan-g-06) were resolved during Phase 2, with agreed positions reflected throughout Section 2 above. The closest-call items (C# vs. Go on 2.1 convention uniformity; Java vs. Kotlin ordering) are documented as analysis precision notes in Section 2.12, not as unresolved disagreements — both agents converged on the same positions.

---

## 4. Open Questions


No carry-forward questions remain. All questions raised in Phase 2 (Q-plan-g-01, Q-plan-g-02, Q-plan-c-01, Q-plan-c-02, and associated items) were resolved with evidence during Phase 2 rounds.

Internal questions that remain open by nature (unverifiable externally) are documented as conditional assumptions in the body:
- Tier 1.1 (platform support): provisional PASS pending internal vetted-catalog confirmation.
- JVM cold-start penalty: conditional on deployment-spec min-replica setting (see Flip Criterion 2).
- C# Native AOT feasibility: conditional on DVS dependency graph (see Flip Criterion 4).
- Internal team expertise distribution: unknown/neutral in base ranking (see Flip Criterion 6).

---

## 5. Sources


1. **Official MCP SDK page** — https://modelcontextprotocol.io/docs/sdk *(Tier 1/Tier 2/TBD labels per language)*
2. **MCP SDK tiering system** — https://modelcontextprotocol.io/community/sdk-tiers *(Tier definitions: Tier 1 = fully supported, Tier 2 = actively maintained, Tier 3 = experimental/partial)*
3. **MCP Kotlin SDK audit — GitHub issue #2512, April 2, 2026** — https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2512 *(Tier 3 assessment: failing stable release and documentation requirements)*
4. **OpenTelemetry logs signal documentation** — https://opentelemetry.io/docs/concepts/signals/logs/ *(Specification-level stability vs. per-language SDK implementation distinction)*
5. **OpenTelemetry status page** — https://opentelemetry.io/status/ *(Authoritative per-language SDK maturity: .NET/Java Stable; Go Stable/Stable/Beta; JS/Python Development logs; Kotlin Development; Rust Beta)*
6. **pdfcpu GitHub repository (main branch README)** — https://github.com/pdfcpu/pdfcpu *(Alpha self-description: "pdfcpu is still Alpha and occasionally undergoing heavy changes")*
7. **MCP Server Frameworks & SDKs review — ChatForest, updated May 1, 2026** — https://chatforest.com/reviews/mcp-server-frameworks-sdks/ *(MCP ecosystem overview, Java SDK v1.1.2, Rust SDK v1.5.0)*
8. **Azure Container Apps containers documentation** — https://learn.microsoft.com/en-ca/azure/container-apps/containers *(Language/runtime-agnostic container deployment)*
9. **Npgsql documentation — basic usage and connection pooling** — https://www.npgsql.org/doc/basic-usage.html *(Connection pooling behavior, disposed connections returned to internal pool)*
10. **pgxpool Go documentation** — https://pkg.go.dev/github.com/jackc/pgx/v4/pgxpool *(Concurrency-safe PostgreSQL connection pool for Go)*
11. **C# nullable reference types documentation** — https://learn.microsoft.com/en-us/dotnet/csharp/nullable-references *(Flow-based static analysis for null-state tracking)*
12. **Go language specification** — https://go.dev/ref/spec *(Goroutine and channel primitives)*
13. **Java virtual threads documentation** — https://dev.java/learn/new-features/virtual-threads/ *(Project Loom: blocking in virtual threads unmounts from carrier thread)*
14. **Kotlin coroutines overview** — https://kotlinlang.org/docs/coroutines-overview.html *(Suspending functions that pause and resume without blocking a thread)*
15. **Node.js blocking vs. non-blocking I/O guide** — https://nodejs.org/en/docs/guides/blocking-vs-non-blocking/ *(Single-threaded JavaScript execution, event loop behavior)*
16. **TypeScript FAQ — type erasure** — https://github.com/microsoft/TypeScript/wiki/FAQ *(Type annotations removed during compilation; no runtime type information)*
17. **Python asyncio documentation** — https://docs.python.org/3.11/library/asyncio.html *(asyncio concurrent async/await support)*
18. **Rust ownership documentation** — https://rust-book.cs.brown.edu/ch04-01-what-is-ownership.html *(Ownership checked at compile time)*
19. **Azure Key Vault client libraries** — https://learn.microsoft.com/en-us/azure/key-vault/general/client-libraries *(Per-language SDK availability)*
20. **Azure Cache for Redis client library best practices** — https://learn.microsoft.com/en-sg/azure/azure-cache-for-redis/cache-best-practices-client-libraries *(Per-language recommended clients)*
21. **Build an MCP server in C# — .NET Blog (Microsoft)** — https://devblogs.microsoft.com/dotnet/build-a-model-context-protocol-mcp-server-in-csharp/ *(Official Microsoft MCP SDK for C# documentation)*
22. **JetBrains Kotlin Blog — Next-Level Observability with OpenTelemetry, April 2026** — https://blog.jetbrains.com/kotlin/2026/04/next-level-observability-with-opentelemetry/ *(Kotlin + Spring Boot + Java OTel SDK integration pattern)*
23. **SigNoz — OpenTelemetry Logs, May 2026** — https://signoz.io/blog/opentelemetry-logs/ *(Per-language OTel log SDK maturity status as of May 2026)*
24. **Build AI Tooling in Go with the MCP SDK — Azure Cosmos DB Blog, January 2026** — https://devblogs.microsoft.com/cosmosdb/build-ai-tooling-in-go-with-the-mcp-sdk-connecting-ai-apps-to-databases/ *(Official Go MCP SDK usage)*
25. **Official Go SDK for MCP — Socket.dev** — https://socket.dev/blog/official-go-sdk-for-mcp *(Go MCP SDK release and stability information)*

---

## 6. Confidence Ledger


| Claim | Tag | Signal | Source notes |
|---|---|---|---|
| C# (.NET 9/10) is the recommended #1 language | [U] | Both agents converged; no counter-evidence found | Load-bearing 2.1 reasoning is structural, not benchmark-backed |
| All seven candidates pass Tier 1.1 (platform support) | [U] | Azure Container Apps is container-image-agnostic | Subject to internal vetted-catalog confirmation; unverifiable externally |
| Tier 1.4 PASS for all seven | [V] + [U] | Official MCP SDK page (source 1); Tier definitions (source 2) | Kotlin weakest margin; see below |
| Kotlin MCP SDK is at Tier 3 per April 2026 audit | [V] | GitHub issue #2512, April 2, 2026 (source 3) | Audit found: no stable 1.0.0 release, documentation gaps, missing policy docs |
| Java MCP SDK is Tier 2 GA | [V] | ChatForest review (source 7) — Java SDK v1.1.2, v1.0.0 GA February 2026 | Corroborated by official SDK page listing Java as Tier 2 |
| OTel log SDK maturity varies materially by language | [V] | Official opentelemetry.io/status/ (source 5); OTel logs docs (source 4) | C#/.NET and Java = Stable; Go = Beta; JS/Python = Development; Kotlin-specific = Development; Rust = Beta |
| OTel spec-level vs. SDK-level stability distinction | [V] | opentelemetry.io/status/ (source 5) and opentelemetry.io/docs/concepts/signals/logs/ (source 4) | Official page explicitly warns these are different; techbytes.app secondary source that conflated them was rejected |
| pdfcpu (Go PDF library) is self-labeled Alpha | [V] | pdfcpu GitHub README, main branch (source 6) | "pdfcpu is still Alpha and occasionally undergoing heavy changes" |
| UniPDF / unidoc requires a commercial license | [U] | From prior-run research; not re-verified this run | Accepted by both agents; no counter-evidence |
| C# NRT is flow-based static analysis, not full runtime enforcement | [U] | Structural language fact; corroborated by Microsoft docs (source 11) | Agreed by both agents; "strong practical static typing" not "nominally sound" |
| Go wins 2.1 sub-dimension B (convention uniformity) | [U] | Structural reasoning: gofmt, single module system, single error convention | No benchmark evidence; qualitative judgment shared by both agents |
| C# wins 2.1 sub-dimension A (type-system depth) over Go | [U] | Structural reasoning: sealed types, exhaustiveness, Roslyn | No language-specific AI-agent error-rate benchmark exists; this is the main confidence gap |
| Spring Boot AOP implicit behavior is a 2.1 penalty for Java | [U] | Structural reasoning: proxy-bypass (self-invocation) is a real AI-agent trap | Both agents agreed; Java 2.1 = Adequate-Strong (not Strong) |
| Go 2.3 ecosystem = Adequate (not Strong) | [V] + [U] | pdfcpu Alpha self-label (source 6); UniPDF commercial license; thin background-job orchestration | Both agents agreed; context note: gap narrows for MIME/file-size-only intake |
| Kotlin JVM deployments can use Java OTel SDK at Stable maturity | [U] | Structural JVM fact (Kotlin compiles to JVM bytecode); corroborated by JetBrains OTel tutorial (source 22) | Mitigates Kotlin-specific OTel Development SDK concern |
| Java #3 above Kotlin #4 | [V] + [U] | Kotlin Tier 3 audit evidence (source 3); Java Tier 2 MCP SDK (source 7); convention-space reasoning | Both agents converged; Kotlin's stronger type system acknowledged but MCP margin is decisive |
| Rust ranks above Python (#6 vs #7) | [U] | 2.1 highest-weight: Rust Adequate (capped) > Python Weak | Consistent with agreed Tier 2 weighting; no benchmark evidence |
| Python ranks last on 2.1 | [U] | Optional typing, unenforced at runtime; dynamic dispatch, magic methods | Structural language design fact; specific survey statistics removed as unverified |
| JVM cold-start 2–5 seconds for Spring Boot without optimization | [U] | Industry knowledge; standard JVM startup characteristic | No Azure-specific measurement this run; conditional penalty depends on min-replica setting |
| .NET Native AOT addresses C# cold-start concern | [U] | .NET documentation; available since .NET 8 | Feasibility depends on DVS dependency graph; unverified for this specific stack |
| Go goroutines map naturally to SKIP LOCKED worker pattern | [U] | Structural concurrency model reasoning | Both agents agreed; Go 2.2 = Strong |
| TypeScript full-stack alignment is Tier 3, not Tier 2 | [U] | Explicit brief guidance + agreed interpretation | Both agents agreed; does not override 2.1 analysis |
| Decision confidence: MEDIUM-HIGH | [U] | Framework criteria adequately differentiated candidates; C# edge over Go is narrow on 2.1 sub-B | Single missing evidence: AI-agent pilot on representative DVS slice |
