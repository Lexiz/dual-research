---

# Backend Language Choice — Document Verification Service

## Decision-Grade Analysis: Backend Language for the Server-Side Modular Monolith


---

## 1. Summary


**C# (.NET) is the recommended language (#1) for the Document Verification Service's server-side modular monolith.** Go is the closest challenger at #2. All seven candidates (Go, Rust, Python, TypeScript/Node.js, C#/.NET, Kotlin, Java) pass all Tier 1 hard requirements under the agreed generous MCP SDK interpretation. The recommendation turns on Tier 2: both C# and Go score **Strong** on the highest-weight criterion 2.1 (AI-coding-automation fitness), with C# holding an edge on the primary sub-criterion (type-system depth and refactoring safety — richer nominal typing, Roslyn analyzers, nullable-flow analysis) and Go holding an edge on the secondary sub-criteria (convention-over-configuration via `gofmt`, explicit semantics). At that 2.1 tie, C#'s **unambiguous advantage on Tier 2.3 ecosystem maturity** — Polly's comprehensive resilience library with native `IHttpClientFactory` integration, deepest first-party Azure SDK investment, and mature schema-validation codegen — breaks the Tier 2 composite in C#'s favor. Decision confidence is **MEDIUM**: the organizational facts that could shift the result (internal platform catalog confirmation; production min-replica setting) remain unverified in this run.

---

## 2. Findings


---

### 2.1 — Tier 1: Hard Requirements (Pass/Fail)

> **Assumption Box (carry-forward from Q-input-g-01 and Assumption-A):** All seven candidates are assumed to pass Tier 1.1 (internal platform catalog — Azure App Service / Container Apps) because all are mainstream containerized runtimes with documented Azure support. **Client confirmation is required before the decision is finalized.** If any candidate is absent from the vetted catalog, it is eliminated at Tier 1 regardless of Tier 2 scores.

> **Process context (carry-forward from Q-input-c-03):** "Separate processes inside the same container image" is interpreted throughout as separate process types / entrypoints launched by the platform scheduler, not OS-level multi-process supervision inside one container instance. Client confirmation is needed only if the internal platform mandates an unusual supervision model.

#### 1.1 — Platform Support

All seven candidates are standard containerized runtimes deployable on Azure Container Apps and Azure App Service. [U] Azure Container Apps is documented as supporting custom code in developers' preferred programming language or framework. [V] **All seven: PASS (assumed — see Assumption Box above).**

#### 1.2 — Azure Postgres SDK (connection pooling, RLS)

As of .NET 5, all .NET runtime APIs are annotated, and the Postgres ecosystem is well-covered across all candidates. [U] Notable drivers: `pgx` v5 with `pgxpool` (Go); `Npgsql` with `NpgsqlDataSource` (C#); `JDBC` + `HikariCP` (Java/Kotlin); `asyncpg`/`psycopg3` (Python); `node-postgres` (TypeScript); `sqlx`/`tokio-postgres` (Rust). All support session-level `SET LOCAL` for Row-Level Security context propagation. [U] **All seven: PASS.**

#### 1.3 — Azure Blob, Redis, Key Vault SDKs

Microsoft publishes first-party Azure SDKs for .NET, Java, Python, JavaScript/TypeScript, and Go. [U] Rust and Kotlin rely on community or partial SDKs for some services, but Azure Blob, Redis, and Key Vault are all covered across all seven candidates. [U] **All seven: PASS (Rust and Kotlin noted as carrying marginally higher community-library reliance).**

#### 1.4 — MCP Server Library (generously treated)

Per the agreed Phase 0 interpretation, this criterion is passed generously for all seven: a mature MCP server library exists or is feasibly implementable without significant effort. Official MCP SDKs are tiered by feature completeness, protocol support, and maintenance commitment; TypeScript and Python have the deepest adoption, C# and Go are strong official-tier SDKs, Java and Rust are Tier 2, and Kotlin is TBD. [V] Quality differentials appear **in Tier 2.3 only**, not here. **All seven: PASS.**

#### 1.5 — OAuth 2 / OIDC Client

Mature OIDC client libraries exist across all candidates: `golang.org/x/oauth2` (Go), `Microsoft.Identity.Web` (C#), `openid-client` (TypeScript), `authlib` (Python), Spring Security OAuth / Keycloak adapters (Java/Kotlin), `openidconnect` (Rust). [U] **All seven: PASS.**

#### 1.6 — OpenTelemetry with OTLP Exporters

OpenTelemetry is a CNCF Graduated project. [U] The .NET, Go, and Java SDKs are stable across traces, metrics, and logs; JavaScript and Python are stable for traces and metrics; Rust is beta across API/SDK/exporters. [V] **All seven: PASS.** Maturity differences are a Tier 2.4 signal.

#### 1.7 — Concurrency for SKIP LOCKED Workers + Outbox

All seven candidates support multiple concurrent worker processes with Postgres connection pooling. [U] The concurrency model differences are a Tier 2.2 signal, not a Tier 1 disqualifier. **All seven: PASS.**

---

### 2.2 — Tier 2: High-Weight Criteria Scoring

**Rubric:** Strong / Adequate / Weak per sub-criterion per candidate, with stated reasons.

---

#### Criterion 2.1 — AI-Coding-Automation Fitness (HIGHEST WEIGHT)

This is the primary ordering criterion. Sub-weight priority per the agreed Phase 0 interpretation:

| Sub-weight | Sub-criterion | Priority |
|---|---|---|
| 2.1(1) | Type-system depth and refactoring safety | **Primary** |
| 2.1(2) | Test scaffolding and determinism | Primary-to-secondary |
| 2.1(3) | Codebase comprehensibility / explicit semantics | Secondary |
| 2.1(4) | Convention-over-configuration | Secondary/tertiary |
| 2.1(5) | Training-data adequacy | Floor only |

---

**C# (.NET) — 2.1 Overall: Strong**

**2.1(1) Type-system depth and refactoring safety — Strong (edge within the Strong band).**
C# has richer nominal typing than Go: generics, records, discriminated-union-like pattern matching, and nullable-flow analysis via Roslyn. Two patterns can leave a non-nullable reference holding null without a warning; both patterns are limitations of the static analysis, not bugs in your code — but this is manageable: warnings are not enough; you need to treat warnings as errors. Warnings are too easy to ignore, so you need to tell the compiler to stop compilation when you violate an NRT constraint. If you don't, you won't get the most significant benefit of NRT. When you turn this setting on, you will not be able to compile unless you fix all the potential issues that could cause NullReferenceException. Beginning with .NET 6, new projects include the `<Nullable>enable</Nullable>` element in all project templates. A new C# project created today ships with nullable context enabled by default; CI should configure `TreatWarningsAsErrors` to achieve a hard compile gate equivalent to Go's compiler errors. [V] Roslyn provides symbol-level analysis and type-aware refactoring (rename-symbol, find-references) across large codebases. [U] The C# type system's richer expressiveness — encoding more domain invariants statically — is the edge within the Strong band on this primary sub-criterion.

**2.1(2) Test scaffolding and determinism — Strong.** xUnit / MSTest / NUnit are mature; deterministic builds via `<Deterministic>true</Deterministic>`; `dotnet test` is integrated. [U]

**2.1(3) Codebase comprehensibility — Adequate.** LINQ chains, async state machines, implicit conversions, and extension method resolution order add comprehensibility overhead. Manageable for agents with deep C# training data, but more implicit than Go. [U]

**2.1(4) Convention-over-configuration — Adequate.** ASP.NET Core has strong DI / middleware / hosted-services conventions, but `dotnet format` reads from `.editorconfig` if present — it is not zero-config. [V] Multiple valid idioms exist for the same construct (LINQ vs. loops, records vs. classes, multiple test frameworks). [U]

---

**Go — 2.1 Overall: Strong**

**2.1(1) Type-system depth and refactoring safety — Strong.**
Go refuses to compile programs with unused variables or imports, enforcing hygiene as hard errors, not warnings. [V] `gopls` — the official Go language server, developed by the Go team — supports "a wide range of standard LSP features for navigation, completion, diagnostics, analysis, and refactoring." [V] Go has no escape hatch equivalent to the C# null-forgiving operator (`!`) in normal application code. [U] Where Go is weaker than C# on this sub-criterion: fewer ways to encode constrained domain state (no discriminated unions, less expressive generics), and nil safety limitations analogous to (though different from) C#'s NRT gaps. [U] Both languages provide a hard compile gate on type errors in a well-configured new project; C# has an edge within the Strong band by virtue of richer nominal domain modeling depth.

**2.1(2) Test scaffolding and determinism — Strong.** Built-in `go test`, `go.sum` deterministic module resolution, race detector (`go test -race`), sub-second compile loop. [U] Go compiles fast: "sub-second for most projects. AI writes code, compiler rejects it, AI reads the error and fixes." [V] The sub-second loop is a real secondary advantage but is treated as a Tier 3.2 signal rather than a primary 2.1 differentiator against C#.

**2.1(3) Codebase comprehensibility — Strong.** No decorators, no magic methods, no monkey-patching, no implicit operator overloading. Explicit error returns rather than exceptions. Go was designed to have fewer ways to do things and more agreement on the "right" way, avoiding features that often lead to complexity such as inheritance or method overloading. [V]

**2.1(4) Convention-over-configuration — Strong (best of class).** `gofmt` is included in the official Go installation and formats Go source code automatically with no configuration and no debate over style choices — [V] Go just decides. The Go installation process also installs an executable called `gofmt` because it is so often referenced. [V] No `.editorconfig` authoring, no CI setup, no dotnet-format invocation required. A new AI-generated file is formatted correctly without any project-level setup.

**2.1 Aggregate (Go vs. C#):** Both are **Strong** overall. C# has the edge on the primary sub-criterion (2.1(1) — richer type-system expressiveness, Roslyn depth). Go has the edge on secondary sub-criteria (2.1(3) explicit semantics and 2.1(4) convention-over-configuration). The result is a **genuine 2.1 tie** between Go and C#. The Tier 2 composite tiebreaker is Criterion 2.3.

---

**TypeScript / Node.js — 2.1 Overall: Adequate**

**2.1(1) — Adequate.** TypeScript's type system is structurally typed and intentionally unsound in places. [U] Type erasure at runtime means "correct types" can mask incorrect values; a single `as Foo` assertion or `any` escape hatch disinfects an entire code path. Framework fragmentation is the worst of any candidate. [U]

**2.1(3) — Adequate.** Types give agents structure for refactoring, but the optional typing, structural subtyping, and `any`-ecosystem mean a production codebase may have substantially less effective type coverage than nominal TypeScript adoption implies. [U]

**2.1(4) — Weak.** The Node.js ecosystem has high framework fragmentation (Express, Fastify, Hono, NestJS, Elysia); multiple competing ORM patterns; multiple bundler conventions; no canonical formatter enforced by the language. [U]

---

**Kotlin — 2.1 Overall: Adequate-to-Strong**

**2.1(1) — Strong.** Kotlin has compile-time null safety as a first-class language feature and sealed classes for exhaustive domain modeling. [U]

**2.1(3) — Adequate.** Coroutine suspension points and JVM framework (Spring Boot / Ktor) implicit behavior reduce comprehensibility relative to Go. [U]

---

**Java — 2.1 Overall: Adequate**

Strong static typing and mature refactoring tooling, but verbosity and Spring annotation / AOP implicit behavior (proxies, bean lifecycle magic) reduce comprehensibility sub-score relative to Kotlin. [U] Below Kotlin on both 2.1(1) (no built-in null safety; requires optional annotations) and 2.1(3). [U]

---

**Rust — 2.1 Overall: Adequate**

Strongest type-system guarantees of any candidate (ownership, lifetimes, algebraic types). [U] However, borrow-checker iteration friction is a documented risk for AI agents in autonomous loops: compile times are materially slower than Go, and borrow-checker errors frequently require human intervention to resolve, breaking the autonomous-iteration model that is central to the agentic-maintenance operating model. [U]

---

**Python — 2.1 Overall: Weak**

Optional dynamic typing is enforced only by third-party tools (mypy, Pyright); the runtime does not enforce type hints. [U] Pervasive `Any` in many libraries means AI-generated code can pass type checking while containing semantic errors discoverable only at runtime. [U] The brief explicitly names optional typing as imposing "a much heavier review burden." Python is a **Tier 1 pass** but ranks last among survivors on Tier 2 criteria due to this Weak 2.1 score.

---

#### Criterion 2.2 — Concurrency Model Fit

The service runs four process types: an async API (MCP + HTTP, hundreds concurrent), an outbox worker (at-least-once delivery), a `FOR UPDATE SKIP LOCKED` analysis worker (10-second document-AI timeouts, circuit breakers), and scheduled-task workers.

| Candidate | Score | Rationale |
|---|---|---|
| **C#** | **Strong** | `async`/`await`, `IHostedService` for background workers, `CancellationToken` for 10s document-AI timeout, Kestrel optimized for concurrent connections, [V] Npgsql async connection pooling. [U] |
| **Go** | **Strong** | Goroutines (~2KB, M:N scheduling), channels, `context.WithTimeout` idiomatic for the 10s timeout pattern, `pgxpool` goroutine-safe connection pooling. [U] |
| **Kotlin** | **Strong** | Coroutines are a capable concurrency model for this service shape. [U] |
| **Rust** | **Strong** | Tokio M:N threading. [U] Concurrency is excellent; the concern is iteration speed, not expressiveness. |
| **Java** | **Adequate-to-Strong** | Virtual threads (Project Loom, stable in Java 21) materially improve Java's fit for high-concurrency I/O; [V] the blocking-thread model concern is substantially mitigated. |
| **TypeScript** | **Adequate** | Non-blocking I/O fits HTTP and document-AI provider calls; JavaScript execution is single-threaded by default, so CPU-heavy or blocking work requires Worker Threads. [V] |
| **Python** | **Adequate** | `asyncio` is capable but GIL constraints at high concurrency reduce throughput clarity. [U] |

---

#### Criterion 2.3 — Ecosystem Maturity for the DVS Stack

Key needs: document parsing (PDF/image), Document AI provider abstraction, AEAD cryptographic primitives (GDPR crypto-erasure), JSON Schema validation with codegen, background-job orchestration, HTTP client with circuit breakers and timeouts.

**C# (.NET) — Strong.**
Polly is a .NET resilience and transient-fault-handling library that allows developers to express resilience strategies such as Retry, Circuit Breaker, Hedging, Timeout, Rate Limiter and Fallback in a fluent and thread-safe manner. Adding a circuit breaker policy into your `IHttpClientFactory` outgoing middleware pipeline is as simple as adding a single incremental piece of code to what you already have when using `IHttpClientFactory`. From ASP.NET Core 2.1, Polly integrates with `IHttpClientFactory`. Additional coverage: first-party Azure SDKs for Blob, Redis, Key Vault; `Npgsql` for Postgres; `System.Security.Cryptography` / BouncyCastle for AEAD; `JsonSchema.Net` / `NJsonSchema` for schema validation with codegen; `PdfPig` / `iTextSharp` for document parsing; Worker Services for background-job orchestration. [U]

**Go — Adequate.**
`gobreaker` and `hystrix-go` are production-proven circuit-breaker libraries. [U] `net/http` is excellent; `go-jose` / `crypto/aes` cover AEAD. The primary gaps relative to C#: JSON Schema codegen tooling is less mature; no equivalent to Polly's comprehensive `IHttpClientFactory` integration depth. [U]

**Java / Kotlin — Strong.**
The JVM ecosystem is the deepest of any candidate: Resilience4j for circuit breaking, Bouncy Castle for cryptography, Jackson for JSON, Apache PDFBox for parsing, Spring ecosystem for orchestration. [U] Kotlin inherits full Java library compatibility. [U]

**TypeScript — Adequate.**
`zod` is excellent for schema validation; `jose`, `pdf-lib`, `opossum` for circuit breaking. npm breadth is high but maintenance consistency is variable. Strong MCP / JSON-schema tooling is a genuine positive. [U]

**Python — Strong (not load-bearing).**
Richest document AI / AI-provider integration ecosystem of any candidate. However, this service delegates heavy AI work to an external provider, so Python's ecosystem breadth advantage on the AI-integration dimension is not load-bearing for this stack. [U]

**Rust — Adequate.**
Libraries exist for all needs but are less mature than .NET / Java equivalents; some Azure SDK crates remain in active development. [V]

---

#### Criterion 2.4 — Observability and Operational Fit

| Candidate | Score | Rationale |
|---|---|---|
| **C#** | **Strong** | OTel .NET SDK stable for traces, metrics, and logs; ASP.NET Core / Npgsql / Redis / HttpClient auto-instrumentation hooks; modern Server GC well-tuned for server workloads; cold start ~1–2s for .NET 8 (faster than JVM, slower than Go). [V/U] |
| **Go** | **Strong** | OTel Go SDK stable; no GC pauses at this workload scale; binary ~20–50MB with no runtime dependency; startup in milliseconds. [U] |
| **TypeScript** | **Adequate** | Azure Monitor OTel package for Node.js includes Postgres / Redis / Azure SDK instrumentation by default; fast startup (~100–500ms); V8 GC introduces tail latency variability. [V/U] |
| **Kotlin** | **Adequate** | JVM footprint / cold-start risk; Kotlin-native OTel is experimental (CNCF 2026); Java OTel interop available. [V/U] |
| **Java** | **Weak-to-Adequate** | JVM memory / cold-start risk in Container Apps scale-from-zero scenarios; OTel Java stable; Azure Container Apps offers JVM memory fitting. [V/U] Confirmed risk: Java often has higher memory and CPU requirements than natively compiled languages, owing to the overhead of the JVM and Garbage Collection; startup times can be significant in Kubernetes/cloud-hosted environments. [U] |
| **Rust** | **Strong** | Zero GC, minimal memory, sub-millisecond startup. OTel Rust is beta — a minor caveat but not eliminating. [V/U] |
| **Python** | **Adequate** | OTel Python SDK mature; GIL constrains throughput at high load; GC pause behavior unpredictable under load. [U] |

---

### 2.3 — Tier 2 Summary Scorecard and Final Ranking

| Candidate | 2.1 AI Fitness | 2.2 Concurrency | 2.3 Ecosystem | 2.4 Observability | **Rank** |
|---|---|---|---|---|---|
| **C# (.NET)** | **Strong** *(edge on primary sub-criterion)* | Strong | **Strong** | Strong | **#1** |
| **Go** | Strong *(edge on secondary sub-criteria)* | Strong | Adequate | Strong | **#2** |
| Kotlin | Adequate-to-Strong | Strong | Strong | Adequate | **#3** |
| Java | Adequate | Adequate-to-Strong | Strong | Weak-to-Adequate | **#4** |
| TypeScript | Adequate | Adequate | Adequate | Adequate | **#5** |
| Rust | Adequate | Strong | Adequate | Strong | **#6** |
| Python | **Weak** | Adequate | Strong | Adequate | **#7** |

**C# #1 rationale.** C# and Go tie at Strong on 2.1; C# has the edge within the Strong band on the primary 2.1 sub-criterion (type-system depth / refactoring safety — richer domain modeling, Roslyn depth). At a 2.1 tie, the Tier 2 composite tiebreaker is 2.3: C# is Strong, Go is Adequate — this is a categorical difference, not a within-band difference. C# is Strong across all four Tier 2 criteria.

**Go #2 rationale.** Tied with C# on 2.1; also Strong on 2.2 and 2.4; trails only on 2.3. The 2.3 gap — Polly's `IHttpClientFactory` integration depth, Azure SDK first-party investment, schema-validation codegen — is the decision margin. If that gap is assessed as small for this specific stack (the service's scale does not require exhaustive resilience patterns), the C# / Go ordering is close and the flip criteria apply.

**2.1 is load-bearing, per the brief's mandate.** Both top candidates are Strong on 2.1; at a tie, 2.3 decides.

**Kotlin #3.** Strong concurrency (coroutines), Strong JVM ecosystem (inherits full Java library compat), but JVM cold-start / memory risk at 2.4 and coroutine implicit semantics at 2.1 prevent overtaking C# or Go. Kotlin ranks above Java because its compile-time null safety and concision are genuine 2.1(1) advantages, and its lighter Ktor framework path reduces the operational baseline.

**Java #4.** Below Kotlin due to verbosity at 2.1 and heavier JVM baseline at 2.4. Virtual threads (Project Loom) improve 2.2 to Adequate-to-Strong. Full JVM ecosystem at 2.3 is a real strength.

**TypeScript #5.** Falls below JVM languages because 2.1 is the primary criterion, and TypeScript's structural / intentionally-unsound type system, type erasure, and `any` escape hatches make it Adequate rather than Strong on 2.1. Its strong MCP / JSON-schema story is a genuine 2.3 positive but does not overcome the 2.1 gap. The "same language as frontend" Tier 3 argument is explicitly not a Tier 2 signal per the brief.

**Rust #6.** Strong type-system guarantees and excellent operational profile. Borrow-checker iteration friction makes it Adequate on 2.1 for the agentic-maintenance operating model. Strong on 2.2 and 2.4; Adequate on 2.3.

**Python #7.** Tier 1 PASS. Ranked last because it is Weak on the highest-weight criterion 2.1 — optional dynamic typing imposes an unacceptable review burden for long-lived autonomous refactoring under the agentic-maintenance operating model. Python's Strong ecosystem (2.3) is a genuine asset but does not overcome its 2.1 position. *(Note: "eliminated" language is not used; Python is a Tier 1 survivor ranked last on Tier 2 criteria.)*

---

### 2.4 — Tier 3: Tie-Breaker Criteria (Applied to C# vs. Go Only)

Tier 3 is not needed to determine #1 vs. #2 — Tier 2 produces a clear winner (C#, by virtue of the unambiguous 2.3 advantage at a 2.1 tie). Tier 3 is documented here for completeness and as supporting context.

**3.1 — Hiring market depth (Europe).** C# developers are more numerous in European hiring markets (Microsoft enterprise ecosystem dominance); Go is growing but smaller. Slight advantage: C#. [U]

**3.2 — Build / deployment iteration speed.** Go's sub-second incremental compile is materially faster than C#'s `dotnet build` (typically 5–15s for non-incremental builds). [U] This is documented as an additional supporting reason for Go's Strong 2.1(2) score but does not override the Tier 2 composite.

**3.3 — Frontend alignment.** The frontend is Lit / TypeScript. Neither Go nor C# has alignment. Neutral. [U]

---

### 2.5 — Decision Confidence and Flip Criteria

**Decision confidence: MEDIUM.**

Public evidence supports C# strongly on 2.1 and 2.3, but two unverified organizational facts could shift the result:
1. Whether C# (and Go) are confirmed in the internal platform catalog.
2. Whether production runs min-replicas ≥ 1 (which would reduce the JVM cold-start penalty from recurring to deployment-only, potentially elevating Kotlin to #2 over Go).

**Single evidence most likely to shift confidence one level higher:** Client confirmation that C# is in the internal platform catalog AND production runs min-replicas ≥ 1.

**Single evidence most likely to shift confidence one level lower:** Internal AI-agent benchmark showing Go produces materially fewer defects or fewer human review cycles than C# for multi-file refactors of a modular-monolith backend similar to this service.

---

#### Flip Criteria (explicit and testable)

**Flip C# → Go as #1 (primary flip condition):**
- An internal AI-agent benchmark (Claude Code or equivalent) shows Go ≥ C# on defect rate and review time for multi-file refactors of a modular-monolith skeleton similar to this service. This is testable now: run both languages against a representative skeleton. Until this benchmark exists, Go's 2.1 advantage on convention/explicitness remains a well-reasoned hypothesis, not a measured outcome.
- The internal platform catalog does not support .NET but does support Go.
- A formal organizational decision against .NET due to internal platform non-Microsoft norms.

**Flip C# → TypeScript as #1:**
- Firm internal evidence that TypeScript backend agentic coding with strict mode + Zod runtime boundaries + `noUncheckedIndexedAccess` produces fewer defects than C# for this team. AND shared frontend/backend code becomes load-bearing (not merely the Tier 3 convenience it is today).

**Flip Kotlin → #2 (displacing Go):**
- Production min-replicas confirmed ≥ 1, removing recurring JVM cold-start penalty. AND the team already has strong JVM investment making Kotlin ecosystem depth load-bearing over Go's operational profile.

**Flip any candidate → Rust:**
- An AI coding agent specifically demonstrated to handle Rust borrow-checker errors autonomously without human intervention in comparable backend systems. Not realistic under the current agentic-maintenance assumption.

---

### 2.6 — Carry-Forward Assumptions

**[Assumption-A]** All seven candidates are assumed to pass Tier 1.1 (internal platform catalog). *Confirmation action:* Check the platform team's vetted runtime list against the current .NET LTS version, all major JVM versions, and the Go runtime.

**[Assumption-B]** Production min-replica setting is unknown. Treated as a real Tier 2.4 risk signal for JVM candidates (Kotlin #3, Java #4). *Confirmation action:* Platform team confirms whether Container Apps runs scale-to-zero or maintains ≥ 1 replica for this service. If confirmed ≥ 1, the JVM cold-start penalty drops from recurring to deployment-only, and the Kotlin → #2 flip condition should be re-evaluated.

**[Assumption-C]** AI coding agent operating model is long-lived agentic maintenance: autonomous multi-file refactors, test-driven iteration loops, human review of agent-proposed changes, no single-agent-identity constraint. This assumption is carry-forwarded from phase 0; client confirmation would not change the framework, only calibrate specific agent-tooling notes.

**[Assumption-D]** C# nullable reference types must be configured as build-blocking (`<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` or `<TreatWarningsAsErrors>Nullable</TreatWarningsAsErrors>`) in this project's CI to achieve the hard compile gate assumed in the 2.1(1) Strong scoring. Warnings are not enough; you need to treat warnings as errors. Warnings are too easy to ignore, so you need to tell the compiler to stop compilation when you violate an NRT constraint. If this configuration is not adopted, C#'s 2.1(1) edge narrows slightly and the Go / C# ordering becomes even closer.

---

## 3. Disagreements Left Open


No unresolved disagreements between agents. All tracked items (D-plan-c-01, D-plan-c-02, D-plan-c-03, D-plan-g-01, D-plan-g-02, D-plan-g-03, D-plan-g-04) were resolved before final plan convergence.

**Near-disagreement resolved in the record (for transparency):** The central Go vs. C# 2.1 ordering was contested across four rounds. Resolution: both score Strong on 2.1 overall. C# has an edge within the Strong band on the primary sub-criterion (type-system depth / refactoring safety — richer domain modeling, Roslyn symbol analysis, nullable-flow analysis). Go has an edge on secondary sub-criteria (convention-over-configuration via `gofmt`; explicit semantics). The aggregate is a 2.1 tie, broken by C#'s unambiguous Tier 2.3 advantage (Polly depth, Azure SDK first-party investment, schema-validation codegen). The recommendation is C# #1, with explicit flip criteria stating when Go would overtake it.

---

## 4. Open Questions


The following questions were acknowledged as unresolvable within this run (organizational facts not available from public sources):

1. **[Q-input-c-01]** AI agent operating model specifics: The brief names AI agents (Claude Code, GitHub Copilot, future agents) but does not specify which agent is primary. Carry-forward assumption is long-lived agentic maintenance (autonomous multi-file refactors, TDD iteration, human review of agent proposals). Client confirmation would not change the framework, only calibrate specific agent-tooling notes in the final document.

2. **[Q-input-c-03]** "Separate processes inside the same container image": Interpreted as separate process types / entrypoints launched by the platform, not OS-level multi-process supervision inside one container instance. Client confirmation needed only if the internal platform mandates an unusual container supervision model.

3. **[Q-input-c-04]** Production min-replica setting: Scale-to-zero vs. min-replicas ≥ 1 is unknown. Cold-start is treated as a real Tier 2.4 signal for JVM candidates (not eliminative). If production confirms min-replicas ≥ 1, the JVM cold-start penalty drops from recurring to deployment-only and the Kotlin → #2 flip condition activates.

---

## 5. Sources


1. Model Context Protocol — SDKs — https://modelcontextprotocol.io/docs/sdk
2. GitHub — modelcontextprotocol/csharp-sdk — https://github.com/modelcontextprotocol/csharp-sdk
3. GitHub — modelcontextprotocol/go-sdk — https://github.com/modelcontextprotocol/go-sdk
4. GitHub — modelcontextprotocol/rust-sdk — https://github.com/modelcontextprotocol/rust-sdk
5. ChatForest — MCP Server Frameworks & SDKs (updated May 1, 2026) — https://chatforest.com/reviews/mcp-server-frameworks-sdks/
6. Socket.dev — Official Go SDK for MCP in Development — https://socket.dev/blog/official-go-sdk-for-mcp
7. OpenTelemetry — Status page — https://opentelemetry.io/status/
8. CNCF Blog — Announcing a Kotlin Multiplatform API and SDK for OpenTelemetry (March 2026) — https://www.cncf.io/blog/2026/03/24/announcing-a-kotlin-multiplatform-api-and-sdk-for-opentelemetry/
9. Microsoft Learn — Nullable reference types (C#) — https://learn.microsoft.com/en-us/dotnet/csharp/nullable-references
10. Microsoft Learn — Nullable reference types (C# reference) — https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/nullable-reference-types
11. blog.genezini.com — Compile-time null safety in C# — https://blog.genezini.com/p/compile-time-null-safety-how-to-avoid-nullreferenceexception-in-c/
12. christianfindlay.com — How to Stop NullReferenceExceptions in .NET — https://www.christianfindlay.com/blog/stop-nullreferenceexceptions
13. JetBrains Blog — Taming the Billion Dollar Mistake (Maarten Balliauw, JetBrains .NET Days 2025) — https://blog.jetbrains.com/dotnet/2025/11/04/maarten-balliauws-guide-to-csharp-nullable-reference-types/
14. Microsoft Learn — The .NET Compiler Platform SDK (Roslyn APIs) — https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/
15. Microsoft Learn — C# language specification: types — https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/language-specification/types
16. Microsoft Learn — Implement HTTP call retries with Polly — https://learn.microsoft.com/en-us/dotnet/architecture/microservices/implement-resilient-applications/implement-http-call-retries-exponential-backoff-polly
17. Microsoft Learn — Implementing the Circuit Breaker pattern — https://learn.microsoft.com/en-us/dotnet/architecture/microservices/implement-resilient-applications/implement-circuit-breaker-pattern
18. GitHub — App-vNext/Polly — https://github.com/App-vNext/Polly
19. GitHub Wiki — Polly and HttpClientFactory — https://github.com/App-vNext/Polly/wiki/Polly-and-HttpClientFactory
20. IMTI — Go's Constraints and Idioms Make AI Coding Better — https://imti.co/golang-ai-coding-vibe-engineering/
21. Medium — How I built 8 Go apps in one week using an AI assistant — https://medium.com/tempest-dx/how-i-built-8-go-apps-in-one-week-using-an-ai-assistant-32f2e9598797
22. Hacker News — A case for Go as the best language for AI agents — https://news.ycombinator.com/item?id=47222270
23. The Go Programming Language — Frequently Asked Questions (FAQ) — https://go.dev/doc/faq
24. The Go Programming Language — gopls — https://go.dev/gopls
25. The Go Programming Language Blog — go fmt your code — https://go.dev/blog/go-fmt-your-code
26. The Go Programming Language — Command Documentation (gofmt) — https://go.dev/doc/cmd
27. Microsoft Learn — dotnet format command — https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-format
28. Microsoft Learn — .NET code style rule options — https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/code-style-rule-options
29. Oracle — Virtual Threads (Java 21) — https://docs.oracle.com/en/java/javase/25/core/virtual-threads.html
30. Node.js — Blocking vs Non-Blocking — https://nodejs.org/en/docs/guides/blocking-vs-non-blocking/
31. Microsoft Learn — Kestrel web server (ASP.NET Core) — https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/kestrel
32. Microsoft Learn — Azure SDK releases (.NET) — https://azure.github.io/azure-sdk/releases/2025-05/dotnet.html
33. Microsoft Learn — Azure SDK for Rust — https://learn.microsoft.com/en-us/azure/developer/rust/azure-sdk-library-package-index
34. Microsoft Learn — Azure PostgreSQL connection libraries — https://learn.microsoft.com/en-us/azure/postgresql/connectivity/concepts-connection-libraries
35. Microsoft Learn — Azure Cache for Redis: client libraries — https://learn.microsoft.com/en-sg/azure/azure-cache-for-redis/cache-best-practices-client-libraries
36. Microsoft Learn — Azure Key Vault client libraries — https://learn.microsoft.com/en-us/azure//key-vault/general/client-libraries
37. GitHub Blog — TypeScript's rise in the AI era — https://github.blog/developer-skills/programming-languages-and-frameworks/typescripts-rise-in-the-ai-era-insights-from-lead-architect-anders-hejlsberg/
38. TypeScript Handbook — Type Compatibility — https://www.typescriptlang.org/docs/handbook/type-compatibility.html
39. kotlinlang.org — Null safety — https://kotlinlang.org/docs/null-safety.html
40. CodingDroplets — OpenTelemetry in ASP.NET Core (2026) — https://codingdroplets.com/opentelemetry-aspnet-core-complete-guide-dotnet-2026
41. Microsoft Learn (Azure Monitor OTel for Node.js) — https://learn.microsoft.com/en-us/javascript/api/overview/azure/monitor-opentelemetry-readme

---

## 6. Confidence Ledger


| Claim | Tag | Signal | Source notes |
|---|---|---|---|
| C# is the #1 recommendation | [U] | Inference from Tier 2 scoring under the agreed criteria framework | No single public source settles this; it is the output of applying the agreed rubric to sourced per-criterion evidence |
| Both C# and Go score Strong on 2.1 overall | [U] | Agreed by both agents after multi-round evidence exchange; individual sub-criterion evidence is [V] | Per-criterion evidence is sourced; the composite Strong rating is a judgment call |
| C# has an edge within the Strong band on 2.1(1) (type-system depth / refactoring safety) | [V/U] | C# nullable-flow analysis and Roslyn documented by Microsoft; NRT warning-vs-error distinction documented; Go compiler errors for unused vars/imports documented by Go FAQ | Sources 9, 10, 14, 15, 23 |
| C# nullable reference types are compile-time warnings by default; `TreatWarningsAsErrors` escalates to build-blocking | [V] | Microsoft official documentation; practitioner guide | Sources 9, 10, 11, 12 |
| New .NET 6+ project templates enable nullable context by default | [V] | Microsoft official documentation | Source 10 |
| Go: unused variables / imports are compiler errors, not warnings | [V] | Go FAQ (official) | Source 23 |
| `gopls` provides full LSP refactoring including navigation, completion, diagnostics, and refactoring | [V] | go.dev/gopls (official) | Source 24 |
| `gofmt` is part of the standard Go installation with no configuration | [V] | Go blog and Go command documentation (official) | Sources 25, 26 |
| `dotnet format` reads formatting preferences from `.editorconfig` | [V] | Microsoft Learn | Source 27 |
| Go's compile loop is sub-second for most projects | [V] | IMTI practitioner article | Source 20 |
| Polly covers Retry, Circuit Breaker, Hedging, Timeout, Rate Limiter, and Fallback in a fluent, thread-safe manner | [V] | GitHub — App-vNext/Polly | Source 18 |
| Polly integrates natively with `IHttpClientFactory` | [V] | Microsoft Learn microservices guide; Polly wiki | Sources 16, 17, 19 |
| MCP SDKs: TypeScript and Python have highest adoption; C# and Go are official-tier; Java and Rust are Tier 2; Kotlin is TBD | [V] | Official MCP SDK page | Source 1 |
| OTel: .NET, Go, Java are stable across traces/metrics/logs; Rust is beta | [V] | OpenTelemetry status page | Source 7 |
| Kotlin-native OTel is experimental (CNCF 2026) | [V] | CNCF blog | Source 8 |
| Java virtual threads (Project Loom, stable Java 21) materially improve concurrent I/O | [V] | Oracle Java 21 documentation | Source 29 |
| Node.js JavaScript execution is single-threaded by default | [V] | Node.js official guide | Source 30 |
| Go has no breaking version changes in over a decade | [V] | Practitioner evidence (HackerNews) | Source 22 |
| Azure first-party SDKs exist for .NET, Java, Python, JavaScript/TypeScript, and Go | [U] | From training weights; no single source retrieved this run, but widely documented by Microsoft | [U] |
| Rust Azure SDK crates exist but some are still in active development | [V] | Microsoft Learn — Azure SDK for Rust | Source 33 |
| Decision confidence: MEDIUM | [U] | Two unverified organizational inputs (platform catalog, min-replica setting) are material to the final ordering; public evidence supports C# but cannot confirm internal facts | — |
| Production min-replica setting unknown | [U] | Organizational fact not available from public sources | Assumption-B |
| Internal platform catalog assumed to pass all seven candidates | [U] | Mainstream runtimes assumption; no internal platform catalog available to verify | Assumption-A |
