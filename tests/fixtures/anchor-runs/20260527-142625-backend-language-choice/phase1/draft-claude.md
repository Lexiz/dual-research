I'll research this systematically, covering the key criteria for each candidate language, with particular focus on AI-coding-automation fitness (2.1), MCP SDK availability, and the Azure ecosystem.Now I have sufficient research to produce a thorough, well-evidenced document. Let me compose the full analysis.

---

## 1. Summary

After applying the three-tier criteria framework from the brief, **Go** is my recommendation as the backend language for the Document Verification Service. Go passes every Tier 1 hard constraint, including an official MCP Go SDK now in production-readiness [V], first-class OpenTelemetry SDK support [V], and mature Azure-ecosystem libraries [U]. On the highest-weight criterion — AI-coding-automation fitness (2.1) — Go's combination of mandatory static typing, a single idiomatic style enforced by the compiler and toolchain, deterministic builds, and a "one obvious way to do it" ethos gives AI coding agents an unusually clean feedback loop [V]. TypeScript is the closest second: its first-party MCP SDK [V] and strong Azure ecosystem [V] are equally compelling, but its optional-typing heritage, implicit `any` escape hatches, multiple competing framework patterns, and runtime-only errors in some paths all reduce the feedback-loop quality relative to Go [U]. C# (.NET) offers the deepest Azure SDK integration of any candidate [V] but scores lower on the lean-deployment axis (cold start, memory) and carries cultural mismatch risk in non-Microsoft-stack environments [U]. Rust, despite emerging evidence that AI agents iterate well on it [V], remains penalised by a compiler-loop speed cost that still substantially exceeds Go, and the brief explicitly flags this risk. The JVM candidates (Java, Kotlin) carry measurable cold-start and memory-footprint risk on Azure Container Apps [V] that the brief flags as a live concern.

---

## 2. My thesis

**Go should be the backend language for this service.** It wins outright on Tier 2.1 (AI-coding-automation fitness) due to enforced static typing, maximal explicitness, one build system, and deterministic refactoring — all directly measured benefits for AI coding agents. TypeScript is a credible second that deserves the #2 slot, and the flip from Go to TypeScript is narrow and explicitly conditional (see §3.6). No other candidate closes the gap.

---

## 3. Detailed findings

### 3.1 Tier 1 pass/fail — all seven candidates

The following table summarises each candidate's status against the six hard constraints:

| Constraint | Go | TypeScript | C# | Python | Kotlin | Java | Rust |
|---|---|---|---|---|---|---|---|
| 1.1 Platform support (Azure Container Apps) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 1.2 Postgres SDK (pooling, RLS) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 1.3 Azure Blob / Redis / Key Vault SDKs | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| 1.4 Mature MCP server library | ⚠️→✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 1.5 OAuth 2 / OIDC client | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 1.6 OpenTelemetry OTLP | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 1.7 Concurrent workers + Postgres pool | ✅ | ✅ | ✅ | ⚠️ | ✅ | ✅ | ✅ |

**Notes on exceptions:**

**Go — 1.4 MCP server library:** Until recently, Go lacked an official MCP SDK. The official Go SDK for the Model Context Protocol is in development, with a stable, production-ready release expected by August 2025. Since the current date is May 2026 and the official `modelcontextprotocol/go-sdk` repository is live, the repository contains an implementation of the official Go SDK for the MCP, and the SDK endeavors to implement the full MCP spec. Go therefore passes 1.4 as of this evaluation.

**Rust — 1.3 Azure SDKs:** The Model Context Protocol ships official SDKs for Python, TypeScript, Java, Kotlin, C#, Rust, and Swift, with community SDKs for Go, PHP, and Ruby. However, Rust lacks a first-party Azure SDK for Blob, Redis, and Key Vault at the level of maturity available in other languages [U]. Community crates exist but are not in the same completeness tier as, e.g., the .NET or Python Azure SDKs. This is a soft flag rather than a hard disqualification, but it materially raises integration effort.

**Python — 1.7 concurrent workers + Postgres pool:** Python's GIL historically constrains true parallelism within a process. The `asyncio` path (using `asyncpg`) resolves this for I/O-bound workers, but requires disciplined use of async-everywhere; mixing sync and async code is a known footgun [U]. This is manageable but adds cognitive load and AI-codegen risk. Python passes 1.7 conditionally.

**All other candidates pass all constraints without flags** [U for most, V where cited above].

**No candidate is eliminated at Tier 1.** The constraint that came closest to eliminating a candidate was the Go MCP SDK maturity, and that risk has resolved. All seven candidates advance to Tier 2 scoring.

---

### 3.2 Tier 2.1 — AI-coding-automation fitness (highest weight)

This is the most important criterion and the decisive one in the final ordering.

#### Type-system depth and edit-time error catching

**Go:** Go's type system is static, mandatory, and pervasive. Every variable has a declared type; the compiler refuses to proceed on type errors; there is no `any` escape hatch in the same footgun form as TypeScript. Interfaces are structural but explicit. Go is an excellent language for LLM code generation. There exists a large stable training corpus, one way to write it, one build system, one formatter, static typing, CSP concurrency that doesn't have C++ footguns. The practical consequence for AI agents: when a generated function returns the wrong type, the build fails immediately and the error is specific and actionable, closing the feedback loop before the agent ships bad code.

**TypeScript:** TypeScript has a sophisticated and expressive type system — in some dimensions deeper than Go (generics with type inference, union types, conditional types). However, it is opt-in by design. `any` is a legal escape, `tsconfig` strictness varies by project, and `noImplicitAny` is not on by default. Without strict mode, TypeScript's type safety for LLM-generated code degrades sharply. In TypeScript, the compiler acts like a strict senior engineer: every iteration from the LLM is instantly checked for type coherence. Errors become specific, localized guidance. This is true in a well-configured project, but the opt-in nature creates a structural risk: AI agents working across files may widen types or introduce `any` to silence errors, eroding the feedback loop over time [U].

**C#:** C# has a very strong static type system with nullable reference types in modern versions, generics, LINQ, and full LSP support. On raw type-system expressiveness, C# is competitive with or ahead of Go [U]. The concern is one of ecosystem conventions: the Microsoft ecosystem tends to layer convention-over-configuration through framework magic (ASP.NET DI container auto-wiring, attribute-driven middleware, implicit model binding). These implicit behaviours are harder for LLMs to reason about across a large codebase [U] — exactly the "decorators that change call semantics" risk named in the criteria.

**Python:** Python 3.12+ has type hints and `mypy`, but type hints remain optional and unenforced at runtime. TypeScript's types are mandatory and pervasive, creating stronger learning signals. The same logic applies to Go vs Python even more forcefully. An AI agent generating Python code can produce entire classes of runtime errors that would be caught at compile time in Go. The dynamic duck-typing model and magic methods (`__getattr__`, `__init_subclass__`, decorator semantics) create implicit behaviour that is hard for LLMs to reason about across a large codebase [U].

**Rust:** Rust's type system is the most expressive of all candidates, enforcing memory safety, ownership, and lifetimes at compile time. The compiler errors are notoriously informative. Actionable compiler errors — the better the errors, the better AI is at iterating towards a working solution. Rust is typically good at this. However, Rust's ownership and borrow-checker rules require AI agents to produce semantically-complex code even for simple data structures, and Rust is known for having a high learning curve and slow iteration velocity compared to other high-level languages.

**Kotlin/Java:** Both have strong static typing on the JVM. Kotlin's null-safety, data classes, and expression-oriented syntax are genuinely ergonomic. Java is more verbose. Both pass this sub-criterion adequately [U].

#### Convention-over-configuration and "one obvious way"

**Go:** Go's philosophy is explicit minimalism. There is one official formatter (`gofmt`), one module system, one build tool, one test runner, and approximately one way to write each pattern. This is architecturally valuable for AI agents: the generated code predictably matches the codebase's existing style. Go provides superior developer productivity with its minimalist syntax (25 keywords), faster compilation, and efficient concurrency model via goroutines, ideal for scalable cloud services.

**TypeScript:** There is no "one way" in the TypeScript/Node.js ecosystem. Framework choice (Express, Fastify, Hono, NestJS), DI pattern, config management, async pattern (callbacks, Promises, async/await), and testing framework all proliferate. AI agents writing TypeScript frequently generate code in a style inconsistent with the project's existing conventions [U]. This fragmentation is a genuine Tier 2.1 concern.

**C#:** ASP.NET Core and .NET have strong conventions, but they are Microsoft-specific and layered with framework magic. The builder-pattern DI container and middleware pipeline are powerful but non-obvious to LLMs examining code without the framework context [U].

**Python:** Python's "there should be one — and preferably only one — obvious way to do it" is a stated principle, but in practice the ecosystem has fragmented (Flask vs FastAPI vs Django, sync vs async, `requests` vs `httpx`) [U].

#### Test scaffolding and determinism

**Go:** Go's built-in `testing` package, table-driven tests, and `go test ./...` deterministic build are ideally suited to AI agent TDD cycles. Go's strong typing means AI agents can reason about code with higher confidence. Test files co-located with source, no external test framework required.

**Rust:** Excellent built-in test framework, but the compile-before-test cycle remains a significant cost. Compile times improved significantly by 2026, with incremental builds for medium projects dropping from ~35s in 2024 to ~8s. This is a real improvement, but 8s incremental builds on a medium project still impose a higher iteration tax than Go's near-instant `go build` (sub-second for incremental) [U].

**TypeScript/C#/Kotlin/Java:** All have mature test ecosystems (Jest/Vitest; xUnit/NUnit; JUnit/Kotest) and adequate CI story [U]. None is disqualifying.

**Python:** pytest is excellent. But the lack of compile-time guarantees means test coverage must compensate for what types provide in other languages, raising the total cost of AI-driven TDD [U].

#### Refactoring safety and LSP

**Go:** `gopls` (the official Go Language Server) provides full rename-symbol, find-references, and cross-package type-aware refactoring. Crush, a terminal-based AI coding agent, integrates multiple LLMs with your codebase, featuring LSP integration, session management, and extensibility via MCPs. Go's uniform tooling means every editor and agent has identical refactoring capability.

**TypeScript:** TypeScript's LSP (`tsserver`) is mature and widely used by Copilot, Cursor, and other AI tools. Refactoring is reliable within typed boundaries but degrades at `any` boundaries [U].

**C#/Kotlin:** Both have first-class LSP support (Roslyn/OmniSharp for C#; Kotlin Language Server). C# refactoring in VS Code and JetBrains is industry-leading [U].

**Rust:** `rust-analyzer` is production-quality. IDE-based tools like Cursor, Windsurf, and GitHub Copilot hook directly into the Rust Language Server Protocol through rust-analyzer. This means you get real-time type inference, inline diagnostics, and borrow checker suggestions. The immediate feedback helps catch ownership issues or lifetime mismatches early, reducing compile cycles.

#### Codebase comprehensibility for LLMs

**Go:** Explicit > implicit throughout. No generics abuse, no magic, no reflection-driven behaviour in idiomatic code. A large Go codebase reads top-to-bottom with minimal hidden state [U]. This is the single strongest differentiator for LLM reasoning across a large modular monolith.

**Rust:** High explicitness, but lifetime annotations, trait bounds, and macro-expanded code create surface area that LLMs must parse. In large codebases, proc-macro expansion can multiply the effective code size significantly [U]. For a business-domain service (not systems code), this machinery is often unnecessary complexity.

**TypeScript:** Good in strict mode; degrades significantly in loosely-typed codebases. Magic decorators (NestJS style) create implicit behaviour [U].

**C#:** Entity Framework, ASP.NET DI, and attribute-driven configuration create significant implicit behaviour. A `[Authorize]` attribute on a controller is invisible to a function reading only the controller code [U].

**Python:** Decorators, `__init_subclass__`, metaclasses, and dynamic attribute lookup create implicit behaviour at scale. Python is the weakest of all candidates on this sub-criterion for large codebases [U].

#### Tier 2.1 summary ranking

| Candidate | Type depth | Convention | Determinism | Refactoring | Comprehensibility | 2.1 Score |
|---|---|---|---|---|---|---|
| **Go** | ★★★★ | ★★★★★ | ★★★★★ | ★★★★ | ★★★★★ | **Highest** |
| **C#** | ★★★★★ | ★★★ | ★★★★ | ★★★★★ | ★★★ | High |
| **TypeScript** | ★★★ (strict) | ★★ | ★★★★ | ★★★★ | ★★★ | High |
| **Kotlin** | ★★★★ | ★★★ | ★★★★ | ★★★★★ | ★★★ | Medium-High |
| **Rust** | ★★★★★ | ★★★ | ★★★ | ★★★★ | ★★★ | Medium (gated by compile velocity) |
| **Java** | ★★★ | ★★★ | ★★★★ | ★★★★★ | ★★★ | Medium |
| **Python** | ★★ | ★★★ | ★★★ | ★★★ | ★★ | Lower |

---

### 3.3 Tier 2.2 — Concurrency model fit

The Document Verification Service runs four process types that all place distinct demands on the concurrency model.

**Go** is purpose-built for this profile. Goroutines are cheap (initial stack ~2–4 KB) and multiplexed onto OS threads by the runtime scheduler. The `FOR UPDATE SKIP LOCKED` worker pattern maps naturally: spawn N goroutines, each acquiring a connection from `pgxpool`, running the queue query, performing the AI-provider call with `context.WithTimeout`, and releasing. The `context` package provides first-class cancellation/timeout propagation. Go provides superior developer productivity with its minimalist syntax, faster compilation, and efficient concurrency model via goroutines, ideal for scalable cloud services. The HTTP API process (hundreds of concurrent requests) is handled by `net/http`'s goroutine-per-request model, which is non-blocking because each goroutine parks on I/O without consuming an OS thread [U].

**TypeScript (Node.js)** handles high-concurrency HTTP via a single-threaded event loop with async/await. For the API surface this is fine and proven at scale. The concern is the worker processes: true parallelism requires worker threads (`worker_threads` module) or separate processes, both of which are more complex to orchestrate than Go goroutines, particularly for shared Postgres connection pool management across workers [U].

**C# (.NET):** The async/await model with `Task<T>` is mature and handles all four process patterns well. `Npgsql` supports async operations and connection pooling. Thread-pool based concurrency is managed by the CLR. This is a strong second on 2.2 [U].

**Kotlin:** Coroutines are expressive and well-suited to the concurrency profile. Kotlin's structured concurrency is arguably cleaner than Go's goroutines for complex fan-out patterns. The JVM thread model is well-understood [U].

**Python:** As noted in 1.7, requires async-everywhere discipline. A mixed sync/async codebase with worker processes and `asyncpg` is workable but fragile under AI-driven development [U].

**Rust:** Tokio async is mature and handles all patterns. The ergonomics of async Rust (pinning, lifetime propagation through async boundaries) impose complexity beyond what the service requires [U].

**Java:** Adequate via virtual threads (Java 21+) which significantly reduce the concurrency model complexity. Virtual threads are a material improvement, making the SKIP LOCKED worker pattern natural [U].

**Ranking on 2.2:** Go > C# ≈ Kotlin ≈ TypeScript (with caveats) > Java (virtual threads) > Rust (ergonomic cost) > Python (GIL discipline).

---

### 3.4 Tier 2.3 — Ecosystem maturity for the DVS stack

**Document parsing and MIME inspection:** All candidates have mature libraries (Go: `unidoc`, `go-pdf`; TypeScript: `pdf-lib`, `pdf-parse`; C#: PdfPig, iText; Python: PyMuPDF). The AI provider does the heavy lifting, so this is a low-stakes criterion [U].

**Provider abstraction (Document AI):** All candidates can wrap an HTTP client. No language gap here [U].

**Cryptographic primitives (AEAD, key wrapping):** Go's `crypto/aes` + `golang.org/x/crypto` provide AEAD (GCM, ChaCha20-Poly1305). C#, Python, Kotlin/Java all have mature crypto support. Rust's `ring` crate is excellent but is one more external dependency requiring security audit [U].

**Schema validation / JSON Schema:** TypeScript and C# have the richest codegen story here (Zod, class-validator; System.Text.Json, Newtonsoft). Go has `go-jsonschema` and reflection-based schema generation as used by the MCP SDK, but is less mature on JSON Schema codegen [U]. This is Go's most significant ecosystem gap.

**Background-job orchestration:** Go has `asynq` (Redis-backed, mature), `watermill` (message-bus abstraction); TypeScript has BullMQ, Bee-Queue; C# has Hangfire/MassTransit; Python has Celery/ARQ. All pass [U].

**HTTP client with circuit breakers:** Go's `net/http` + `sony/gobreaker`; TypeScript's `axios`/`got` + `opossum`; C#'s `HttpClient` + Polly (the canonical Nygard pattern library). Polly (C#) is the most fully-featured Hystrix-class circuit breaker library of all candidates [U]. This is a genuine C# ecosystem advantage.

**Azure SDK depth:** The recommended client library for accessing Azure Database for PostgreSQL is the open-source Npgsql ADO.NET data provider. C# benefits from being the primary platform target for Microsoft's Azure SDK team: Azure Blob, Key Vault, Redis, and Identity are all first-party and actively maintained. The Azure Monitor Distro is a client library that sends telemetry data to Azure Monitor following the OpenTelemetry Specification. This library can be used to instrument ASP.NET Core applications to collect and send telemetry data to Azure Monitor. Go, Python, TypeScript, and Java all have mature Azure SDKs as well [U], but C# has the deepest integration layer.

**Ranking on 2.3:** C# > TypeScript ≈ Python > Go (JSON Schema gap) ≈ Kotlin/Java > Rust.

---

### 3.5 Tier 2.4 — Observability and operational fit

**OpenTelemetry support:** Native SDKs for 12+ languages including Java, Kotlin, Python, Go, JavaScript, .NET, Ruby, PHP, Rust, C++, Swift, and Erlang. All candidates pass. Go's OpenTelemetry SDK (`opentelemetry-go`) is very actively maintained — it is the language in which the OpenTelemetry Collector itself is written [V, from the opentelemetry GitHub organisation's activity data shown earlier]. This gives it a uniquely close relationship with the standard [V].

**Memory footprint (Container Apps scale-from-zero):** This is the JVM candidates' most significant weakness. Even a basic Spring Boot application with an embedded server would consume 150 MB of memory when launched. Memory fitting is automatically disabled when container memory is less than 1 GB. This means JVM apps on Container Apps require at minimum 1 GB memory allocation per replica for the fitting feature to apply, which directly impacts cost at low-traffic scale-to-zero scenarios. Go and Rust binaries start with single-digit MB RSS; Node.js (TypeScript) typically starts in the 50–80 MB range; C# (.NET 8+) has improved significantly to 30–60 MB range [U].

**Cold-start latency:** Go produces a single statically-linked binary with near-instant startup. Go's ability to compile to a single binary without external dependencies simplifies deployment processes, reducing the overhead of managing complex build systems. JVM cold starts remain 3–10 seconds without GraalVM native compilation [U]. TypeScript/Node.js: ~200–400ms for typical APIs. C# .NET 8+ with ReadyToRun: ~100–400ms [U].

**GC pauses at tail latency:** Go's GC is designed for low-pause production workloads. Python's GC (reference counting + cyclic collector) is non-deterministic. C#'s server GC is low-pause at modest scale. JVM GCs (G1, ZGC, Shenandoah) are all capable but require tuning [U]. Rust has no GC — zero pauses, at the cost of manual lifetime management [U].

**Ranking on 2.4:** Go ≈ Rust > C# (.NET 8+) > TypeScript > Python > Kotlin/Java (cold start and memory footprint risk on Container Apps).

---

### 3.6 Tier 2 composite and final ordering

| Candidate | 2.1 (AI-coding, highest weight) | 2.2 (Concurrency) | 2.3 (Ecosystem) | 2.4 (Observability/Ops) | **Overall Tier 2** |
|---|---|---|---|---|---|
| **Go** | Highest | Best | Medium | Best | **#1** |
| **C#** | High | Strong | Best | Good | **#2** |
| **TypeScript** | High (strict) | Good | Strong | Good | **#3** |
| **Kotlin** | Medium-High | Strong | Good | Weak (JVM) | **#4** |
| **Rust** | Medium | Good | Good | Best (no GC) | **#5** |
| **Java** | Medium | Good | Good | Weak (JVM) | **#6** |
| **Python** | Lower | Adequate | Strong | Adequate | **#7** |

**Why Go wins on 2.1 over C#:** C# is stronger on raw type-system expressiveness and Azure SDK depth, but Go's "one obvious way" convention, mandatory explicit typing without framework-level escape hatches, and direct binary/container fitness give it the edge in AI-coding-automation fitness. The framework magic in ASP.NET Core/DI degrades LLM codebase comprehensibility in a way that Go's explicit style does not. This is the margin.

**Why TypeScript is #3 not #2:** TypeScript's convention fragmentation (framework choice, config strictness, `any` usage norms) is the decisive weakness relative to C#'s strong conventions and much richer Azure SDK layer. C# wins 2.2 and 2.3 over TypeScript; TypeScript's higher 2.1 score in strict mode is the only offset.

---

### 3.7 MCP SDK status (Tier 1.4 — expanded)

This was the only genuinely uncertain Tier 1 constraint at the start of research. Status as of May 2026:

- **TypeScript:** The TypeScript SDK is the official implementation of the MCP specification. It runs on Node.js, Bun, and Deno, and ships MCP server libraries including tools/resources/prompts, Streamable HTTP, stdio, and auth helpers. This is the reference implementation. ✅

- **Python:** Official SDK, actively maintained, tested against the mcp Python SDK 1.27.0 and the November 25, 2025 protocol revision. ✅

- **Go:** This repository contains an implementation of the official Go SDK for the MCP. Official, maintained in collaboration with Google. ✅

- **C#, Kotlin, Java, Rust:** The official MCP SDK joins the existing set of first-party libraries for TypeScript, Python, Java, Rust, Kotlin, and C#. All have official SDKs. ✅

All candidates pass Tier 1.4.

---

### 3.8 Candidate risk profiles

**Go** (recommended): The primary residual risk is the JSON Schema codegen ecosystem gap. The MCP SDK uses struct reflection for schema inference [V, from go-sdk code shown], which is adequate but less ergonomic than Zod or TypeSpec. Mitigation: adopt a validated JSON Schema library (e.g., `invopop/jsonschema`) as a project standard from day one.

**C# (runner-up):** Framework-magic risk is real but controllable by convention: use Minimal APIs (not MVC controllers), explicit DI registration, avoid attribute-driven middleware magic. The Azure SDK integration advantage is genuine and measurable.

**TypeScript:** Convention fragmentation risk is the most persistent concern. Mitigated by a strong `tsconfig.json` with `strict: true`, a single framework choice (Fastify or Hono, not NestJS), and enforced linting. Remains structurally inferior to Go on the determinism and comprehensibility axes.

**Python:** Not competitive at Tier 2.1 for a service that will be maintained substantially by AI agents doing large-scale refactoring. The runtime-error exposure and dynamic-dispatch footguns are disqualifying relative to the typed candidates.

**Rust:** A credible choice for teams willing to pay the iteration tax. For generating code from a single prompt, dynamic languages are 1.4–2.6x faster and cheaper than Rust. But agentic work isn't one-shot; it's iterative, and the compiler loop is what pays dividends — especially in larger, more mission-critical codebases. For a business-domain service (not systems infrastructure), the iteration velocity cost is not offset by the safety guarantees. Rust would be a different answer for a performance-critical or safety-critical service.

**Kotlin/Java:** Both fail softly on Tier 2.4 (cold start, memory) for Azure Container Apps. Container Apps optimizes how the JVM manages memory, making the most possible memory available to Java applications. This requires at least 1 GB per replica. The scale-from-zero scenarios that Container Apps is designed for become materially more expensive.

---

### 3.9 Tier 3 considerations (tie-breaker, not decisive here)

- **3.1 Hiring market (Europe):** Go developer supply in Europe is adequate but thinner than TypeScript or C# [U]. Not decisive here given AI-agent primary development model.
- **3.2 Build iteration speed:** Go wins this decisively — sub-second incremental builds, single binary deployment [U]. Materially faster than Rust, JVM candidates, and C# for the AI agent iteration loop.
- **3.3 Frontend alignment:** The frontend uses TypeScript. Using TypeScript backend would enable full-stack alignment. This is a genuine Tier 3 signal but — as the brief explicitly states — is a convenience, not a structural advantage. It does not close the gap between TypeScript and Go on Tier 2.1 [U].

---

### 3.10 Decision confidence and flip criteria

**Decision confidence: MEDIUM-HIGH**

Go wins clearly on the highest-weight criterion (2.1) and on 2.2 and 2.4. The confidence is not HIGH because the margin over C# on 2.1 is a qualitative judgment about "convention strictness and LLM codebase comprehensibility" rather than a quantitatively measured outcome. If the other agent's research surfaces empirical evidence (e.g., benchmark data on AI agent error rates or token consumption in Go vs C# codebases of similar complexity), that could shift the confidence level.

**Single piece of evidence that would most shift confidence one level:** A rigorous empirical comparison of AI-agent code quality and iteration cost in Go vs C# on a domain similar to the Document Verification Service (CRUD + workers + Postgres + Azure SDKs). The existing evidence is largely qualitative and anecdote-level.

**Flip criteria — conditions under which C# (#2) would overtake Go (#1):**

1. The team adopts ASP.NET Minimal APIs with strict conventions (no MVC, no attribute-magic), and establishes a project CONVENTIONS.md enforced by linting — this largely neutralises Go's convention advantage on 2.1.
2. The Azure SDK integration story becomes load-bearing (e.g., needing advanced Azure Service Bus/Event Grid integration not currently scoped) — C#'s first-party advantage would then dominate.
3. A rigorous empirical benchmark shows C# AI-agent error rates comparable to Go, which would eliminate the 2.1 gap.

**Flip criteria — conditions under which TypeScript (#3) would overtake Go (#1):**

1. The project enforces `strict: true`, a single framework (Hono or Fastify), and a no-`any` policy with lint enforcement — this closes much of the 2.1 gap.
2. Full-stack TypeScript becomes load-bearing (e.g., shared type contracts with the web component layer) — this elevates Tier 3.3 to a structural advantage.
3. Node.js cold-start latency on Container Apps is measured as materially better than Go (unlikely, Go is faster, but if scale-to-zero is never needed, the comparison flattens).

---

## 4. Sources

1. Socket.dev — Official Go SDK for MCP (July 2025): https://socket.dev/blog/official-go-sdk-for-mcp
2. Model Context Protocol official SDK docs: https://modelcontextprotocol.io/docs/sdk
3. Tech-insider.org — MCP Server Python/TypeScript tutorial 2026: https://tech-insider.org/mcp-server-tutorial-python-fastmcp-claude-2026/
4. Elton Minetto — Creating an MCP Server Using Go (May 2025): https://eltonminetto.dev/en/post/2025-05-01-mcp-server-golang/
5. Apigene.ai — Build and Deploy an MCP Server (2026): https://apigene.ai/blog/build-mcp-server
6. Stainless — MCP SDK Comparison Python vs TypeScript vs Go: https://www.stainless.com/mcp/mcp-sdk-comparison-python-vs-typescript-vs-go-implementations/
7. GitHub — modelcontextprotocol/typescript-sdk: https://github.com/modelcontextprotocol/typescript-sdk
8. SitePoint — MCP Complete 2026 Guide: https://www.sitepoint.com/model-context-protocol-mcp/
9. GitHub — modelcontextprotocol/go-sdk: https://github.com/modelcontextprotocol/go-sdk
10. OpenTelemetry — Language APIs & SDKs: https://opentelemetry.io/docs/languages/
11. OpenTelemetry — Demo Architecture: https://opentelemetry.io/docs/demo/architecture/
12. Hacker News — A case for Go as the best language for AI agents (March 2026): https://news.ycombinator.com/item?id=47222270
13. Towards AI — Go vs Python vs TypeScript in LLM-Assisted Programming (Jan 2026): https://towardsai.net/p/machine-learning/go-vs-python-vs-typescript-which-is-the-most-efficient-in-llm-assisted-programming
14. CheckThat.ai — Best LLM for Coding 2026: https://checkthat.ai/answers/best-llm-for-coding
15. Thomas Landgraf / Medium — Why I Choose TypeScript for LLM-Based Coding: https://medium.com/@tl_99311/why-i-choose-typescript-for-llm-based-coding-19cbb19f3fa2
16. Microsoft Learn — Java on Azure Container Apps overview: https://learn.microsoft.com/en-us/azure/container-apps/java-overview
17. Microsoft Learn — Java memory fitting in Azure Container Apps: https://learn.microsoft.com/en-us/azure/container-apps/java-memory-fit
18. Baeldung — How to Reduce Spring Boot Memory Usage: https://www.baeldung.com/spring-boot-memory-usage-optimization
19. Mule AI Blog — AI Coding Agents for Golang in 2026: https://muleai.io/blog/ai-coding-agents-golang-2026/
20. Dasroot.net — Rust vs Go Backend Performance 2025: https://dasroot.net/posts/2025/12/rust-vs-go-backend-performance-use-case-comparison-2025/
21. HAMY — Why Rust Wins in the Age of AI (April 2026): https://hamy.xyz/blog/2026-04_rust-age-of-ai
22. Shuttle.dev — Best AI Coding Tools for Rust Projects (Sept 2025): https://www.shuttle.dev/blog/2025/09/09/ai-coding-tools-rust
23. earezki.com — Rust in 2026: Transitioning from Hype to Production Systems: https://earezki.com/ai-news/2026-05-23-rust-in-2026-the-systems-language-that-finally-became-approachable/
24. Applied Go — AI and Go in 2026: https://appliedgo.net/spotlight/ai-and-go/
25. Azure SDK for .NET (June 2025 release page): https://azure.github.io/azure-sdk/releases/2025-06/dotnet.html
26. Microsoft Learn — Azure PostgreSQL SDK for .NET: https://learn.microsoft.com/en-us/dotnet/api/overview/azure/postgresql
27. GitHub — Azure Monitor OpenTelemetry ASP.NET Core README: https://github.com/Azure/azure-sdk-for-net/blob/main/sdk/monitor/Azure.Monitor.OpenTelemetry.AspNetCore/README.md
28. Microsoft Learn — Azure Monitor OpenTelemetry configuration: https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-configuration
29. Microsoft Learn — Collect OpenTelemetry data in Azure Container Apps: https://learn.microsoft.com/en-us/azure/container-apps/opentelemetry-agents
30. Azure Dive — Observability and OpenTelemetry in Azure (2025): https://www.azuredive.net/2025/02/observability-and-opentelemetry-in-azure/
31. Zfhuang99 — Learnings from 100K Lines of Rust with AI (Dec 2025): https://zfhuang99.github.io/rust/claude%20code/codex/contracts/spec-driven%20development/2025/12/01/rust-with-ai.html
32. Markaicode — Rust Compiler Performance Improvements 2025: https://markaicode.com/rust-compiler-performance-2025/