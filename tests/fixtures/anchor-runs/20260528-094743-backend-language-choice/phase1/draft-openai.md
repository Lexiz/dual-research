## 1. Summary

My provisional recommendation is **C# / .NET as #1**, with **Go as the closest challenger** and **Java/Kotlin as credible but operationally heavier JVM alternatives**. [U] C# best matches the brief’s highest-weight criterion, AI-coding-automation fitness, because it combines rich static typing, nullable-reference analysis, strong IDE/LSP refactoring, deterministic test/build tooling, and a comparatively direct async/concurrency model. [V] Microsoft documents nullable-reference static analysis in C#, including compiler warnings for maybe-null flows into non-nullable references. ([learn.microsoft.com](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/nullable-reference-types?utm_source=openai)) Go is the best alternative if the organization weights operational simplicity, low memory footprint, and worker concurrency above type-system depth. [U] Python and TypeScript should remain Tier 1 survivors but should not win under this criteria framework because their weaker runtime/type-safety boundary increases review burden for long-lived AI-agent maintenance. [U]

## 2. My thesis

The decision should be framed as **“C# beats Go on 2.1; Go beats C# only if operational minimalism or internal non-.NET norms are proven to matter more than the stated AI-coding criterion.”** [U] All seven candidates appear to pass Tier 1 if the agreed interpretation’s generous MCP rule and internal-platform assumption are retained, but the Tier 2 ordering should make 2.1 load-bearing rather than letting “same language as frontend” or “Azure implies Microsoft stack” dominate. [U]

## 3. Detailed findings

### Research plan for the final document

The final document should first verify the Tier 1 gates with current evidence: Azure/container runtime support, Azure SDK coverage, Postgres/Redis/Key Vault access, MCP SDK maturity, OAuth/OIDC library maturity, OpenTelemetry maturity, and worker-concurrency feasibility. [U] Azure Container Apps are custom-container oriented and Microsoft’s product page says developers can write code using their preferred programming language or framework, so the platform/runtime gate is unlikely to eliminate any candidate unless the internal catalog is narrower than Azure itself. [V] ([azure-int.microsoft.com](https://azure-int.microsoft.com/en-us/products/container-apps/?utm_source=openai))

The final document should then score Tier 2 with **2.1 as the ordering anchor**, not as a decorative row. [U] I would treat 2.1’s sub-factors in the agreed priority order: type-system depth and refactoring safety first; test determinism second; explicit semantics and conventions next; training-data prevalence only as a floor. [U]

The final document should separately record **flip criteria** because #1 vs #2 is sensitive to organization-specific inputs that cannot be verified from public sources. [U] The most important flip test is: if the internal platform/team has a strong anti-.NET norm or if measured agent productivity in the team’s actual codebase is better in Go than C#, Go could overtake C#. [U]

### Tier 1 evidence baseline

**Platform/runtime:** no public Azure evidence suggests that any candidate language is impossible in Azure Container Apps if packaged as a Linux container. [V] Azure Container Apps advertises custom code in a preferred language/framework and scale behavior based on events or HTTP traffic. [V] ([azure-int.microsoft.com](https://azure-int.microsoft.com/en-us/products/container-apps/?utm_source=openai)) The internal platform catalog remains an organization-specific assumption, so the final document should include an assumption box that all seven are catalog-approved. [U]

**Azure SDKs and storage/security services:** .NET, Java, JavaScript/TypeScript, Python, and Go have first-party Azure SDK surfaces documented by Microsoft/Azure release pages. [V] ([azure.github.io](https://azure.github.io/azure-sdk/?utm_source=openai)) Rust also now has Microsoft-documented Azure SDK crates, including Identity, Key Vault, and Storage Blob entries, though the Rust SDK has had active-development/breaking-change caveats and should be scored cautiously in ecosystem maturity rather than eliminated. [V] ([learn.microsoft.com](https://learn.microsoft.com/en-us/azure/developer/rust/azure-sdk-library-package-index?utm_source=openai))

**Postgres:** Azure Database for PostgreSQL documentation lists mature client libraries for Python, Node.js, Java, and .NET, including psycopg, `pg`, JDBC, and Npgsql. [V] ([learn.microsoft.com](https://learn.microsoft.com/en-us/azure/postgresql/connectivity/concepts-connection-libraries?utm_source=openai)) Go and Rust have mature community Postgres drivers such as pgx and sqlx in the broader ecosystem, but I have not verified their exact Azure Flexible Server guidance in this run. [U]

**Redis:** Azure Cache for Redis documentation says applications can use any client library compatible with open-source Redis, and Microsoft’s best-practices page explicitly notes that Microsoft and the Azure Redis team do not own most client libraries. [V] ([learn.microsoft.com](https://learn.microsoft.com/en-sg/azure/azure-cache-for-redis/cache-best-practices-client-libraries?utm_source=openai)) This means Redis should not eliminate any of the seven candidates, but it does slightly favor ecosystems with heavily used clients and good connection-management patterns. [U]

**Key Vault:** Microsoft documents Key Vault client libraries across .NET, Python, Java, JavaScript, and Spring, and the Azure SDK pages cover Go and Rust Key Vault packages as well. [V] ([learn.microsoft.com](https://learn.microsoft.com/en-us/azure//key-vault/general/client-libraries?utm_source=openai)) This favors .NET/Java/TypeScript/Python/Go as low-risk and makes Rust acceptable but somewhat newer. [U]

**MCP:** The official MCP SDK page lists TypeScript and Python as Tier 1 SDKs, Go as Tier 1, Java and Rust as Tier 2, and Kotlin as TBD. [V] ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/sdk?utm_source=openai)) The official C# SDK repository states that it is the official C# SDK for MCP servers and clients and is maintained in collaboration with Microsoft. [V] ([github.com](https://github.com/modelcontextprotocol/csharp-sdk?utm_source=openai)) Under the agreed interpretation, MCP is a Tier 1 pass for all seven, but the SDK tier/status should still affect Tier 2.3. [U]

**OpenTelemetry:** OpenTelemetry’s status page reports stable API/SDK/exporter maturity for .NET, Go, and Java; JavaScript and Python have stable tracing/metrics but development-status logs; Rust is beta across API/SDK/exporters. [V] ([opentelemetry.io](https://opentelemetry.io/status/?utm_source=openai)) Kotlin/JVM applications can rely on Java OpenTelemetry interoperability today, while CNCF’s 2026 Kotlin Multiplatform OTel announcement describes the Kotlin API/SDK as experimental and notes historical reliance on the Java SDK. [V] ([cncf.io](https://www.cncf.io/blog/2026/03/24/announcing-a-kotlin-multiplatform-api-and-sdk-for-opentelemetry/?utm_source=openai))

**Concurrency:** Go has first-class goroutines and context-based cancellation idioms suitable for queue workers and bounded concurrent I/O. [U] Node.js provides non-blocking I/O through its event loop, but JavaScript execution is single-threaded by default, so CPU-heavy or blocking work must be controlled carefully. [V] ([nodejs.org](https://nodejs.org/en/docs/guides/blocking-vs-non-blocking/?utm_source=openai)) Java’s virtual threads are documented as lightweight threads intended to reduce the effort of high-throughput concurrent applications, which materially improves Java’s fit for worker-heavy services compared with older blocking-thread models. [V] ([docs.oracle.com](https://docs.oracle.com/en/java/javase/25/core/virtual-threads.html?utm_source=openai)) ASP.NET Core’s Kestrel is documented as optimized for efficiently handling many concurrent connections. [V] ([learn.microsoft.com](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/kestrel?view=aspnetcore-3.1&utm_source=openai))

### Preliminary Tier 1 pass/fail

| Candidate | Preliminary Tier 1 result | Rationale |
|---|---:|---|
| C# / .NET | Pass | Strong Azure, Postgres/Npgsql, Redis, Key Vault, OAuth/OIDC, OTel, concurrency, and official MCP story. [V/U] |
| Go | Pass | Strong Azure SDK coverage, strong concurrency, mature Postgres/Redis ecosystem, and official Tier 1 MCP SDK. [V/U] |
| Java | Pass | Strong Azure/JDBC/Redis/OIDC/OTel story and official MCP SDK, with JVM operational caveats deferred to Tier 2. [V/U] |
| Kotlin | Pass | JVM ecosystem covers most service needs; MCP Kotlin SDK exists but official page marks status TBD, so this is a pass under the agreed generous rule. [V/U] |
| TypeScript / Node.js | Pass | Strong MCP, JSON-schema, Azure SDK, Postgres, Redis, and OAuth/OIDC ecosystem; type/runtime concerns are Tier 2. [V/U] |
| Rust | Pass | Rust has official MCP and Microsoft-documented Azure SDK crates, but Azure SDK and OTel maturity should be scored below .NET/Go/Java. [V/U] |
| Python | Pass | Strong Azure, MCP, Postgres, Redis, document-processing, and AI-provider ecosystem; dynamic typing is Tier 2.1, not Tier 1. [U] |

### Preliminary Tier 2 scoring

| Candidate | 2.1 AI-coding fitness | 2.2 concurrency fit | 2.3 ecosystem fit | 2.4 observability/ops fit | Provisional rank |
|---|---|---|---|---|---:|
| **C# / .NET** | **Strong** — rich static typing, nullable-reference analysis, excellent refactoring/tooling, deterministic test/build loop, and less lifetime complexity than Rust. [V/U] | **Strong** — async/await, Kestrel, background services, cancellation tokens, and mature connection pooling fit the API/worker mix. [V/U] | **Strong** — Azure SDKs, Npgsql, Redis, Key Vault, OAuth/OIDC, JSON/schema tooling, crypto, and official MCP are strong. [V/U] | **Strong** — OTel is stable for .NET and memory/cold-start are acceptable for a modular monolith even if not as lean as Go/Rust. [V/U] | **1** |
| **Go** | **Adequate** — excellent explicitness and simple conventions, but less type-system depth and less expressive domain modeling than C#/Java/Kotlin/Rust. [U] | **Strong** — goroutines, channels, contexts, and small worker processes fit SKIP LOCKED/outbox patterns well. [U] | **Adequate** — cloud, Postgres, Redis, HTTP, crypto are strong; schema/codegen and MCP are improving, with MCP now officially Tier 1. [V/U] | **Strong** — small binaries, fast startup, low memory, and stable OTel make it operationally excellent. [V/U] | **2** |
| **Java** | **Strong** — static typing, mature refactoring, deterministic builds, and widely standardized enterprise patterns are strong; null-safety and verbosity are weaker than C#/Kotlin. [U] | **Strong** — virtual threads materially improve Java’s fit for high-concurrency I/O workloads. [V] | **Strong** — JDBC, Azure SDK, Redis, OAuth/OIDC, crypto, validation, and job-processing ecosystems are deep. [V/U] | **Adequate** — OTel is stable, but JVM memory and cold-start risk matter in Azure Container Apps. [V/U] | **3** |
| **Kotlin** | **Strong** — strong null-safety and expressive types are good for AI refactoring, but implicit DSL/coroutine/framework patterns can reduce comprehensibility. [V/U] | **Strong** — JVM + coroutines are capable, though coroutine misuse is a review risk. [U] | **Strong** — inherits Java ecosystem depth, but MCP status is less mature than C#/Go/TypeScript/Python. [V/U] | **Adequate** — JVM footprint/cold-start issues remain; Kotlin-native OTel is experimental, though Java OTel interop is available. [V/U] | **4** |
| **TypeScript / Node.js** | **Adequate** — TypeScript has excellent editor tooling and type annotations, but the type/runtime boundary, `any`, and structural typing make large AI-driven refactors less safe than C#/Java/Kotlin. [U] | **Adequate** — non-blocking I/O fits HTTP and provider calls, but blocking CPU or synchronous code can harm the event loop. [V/U] | **Strong** — MCP, JSON schema, AI-provider SDKs, web tooling, and Azure JS SDKs are strong. [V/U] | **Adequate** — good startup and ecosystem, but Node’s event-loop discipline and OTel log maturity are concerns. [V/U] | **5** |
| **Rust** | **Adequate** — the type system is excellent, but borrow/lifetime complexity and compile-time friction are likely to slow autonomous AI-agent iteration. [U] | **Strong** — async Rust and Tokio-style runtimes are highly capable for bounded concurrent workers. [U] | **Adequate** — improving Azure SDK and official MCP exist, but ecosystem maturity for this Azure-heavy business app is not as low-risk as .NET/Java/Go/TypeScript/Python. [V/U] | **Strong** — low memory and startup are excellent, but OTel Rust is beta. [V] | **6** |
| **Python** | **Weak** — optional typing and runtime dynamism create too much review burden for long-lived autonomous refactors under the stated 2.1 priority. [U] | **Adequate** — async I/O and worker processes are feasible, but concurrency is less clean for this service shape than Go/.NET/Java/Rust. [U] | **Strong** — document parsing, AI-provider, Azure, Postgres, Redis, and MCP ecosystems are strong. [U] | **Adequate** — startup is good, but runtime performance, typing, and OTel log maturity are not differentiators. [V/U] | **7** |

### Why C# is my current #1

C# is the best fit if the brief’s highest-weight criterion is taken literally: AI coding agents benefit from strong compile-time feedback, safe refactoring, good IDE/LSP support, and deterministic build/test loops, and C# supplies those without Rust’s steep ownership/lifetime iteration cost. [U] C# nullable-reference types are not perfect because they are warnings and can be bypassed, but they are still a meaningful static-analysis advantage over TypeScript/Python for a data-sensitive backend with tenant boundaries and compliance workflows. [V/U] ([learn.microsoft.com](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/nullable-reference-types?utm_source=openai))

C# also has an unusually clean Tier 1 and Tier 2.3 story for this exact stack: Azure SDKs, Key Vault, Npgsql/Postgres, Redis, OAuth/OIDC, OpenTelemetry, background workers, and official MCP all have credible paths. [V/U] ([azure.github.io](https://azure.github.io/azure-sdk/?utm_source=openai)) This is not an “Azure means Microsoft language” argument; it is a lower-risk integration argument combined with the 2.1 argument. [U]

### Why Go is the main challenger

Go is the strongest challenger because its concurrency model, fast startup, low memory footprint, simple deployment, and explicit code style fit the API + outbox + analysis-worker + scheduled-worker shape extremely well. [U] Its MCP position has improved materially because the official MCP SDK page lists Go as Tier 1, reducing what would otherwise have been a serious ecosystem-gap concern. [V] ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/sdk?utm_source=openai))

Go does not overtake C# for me because the agreed 2.1 sub-weighting makes **type-system depth and refactoring safety primary**, and Go’s type system is deliberately simpler than C#’s. [U] If the future codebase is mostly straightforward CRUD, queues, HTTP, and provider calls, that simplicity may be enough; if the codebase accumulates complex rules, tenant invariants, consent states, document-authentication state machines, and provider abstractions, C#’s richer modeling becomes more valuable. [U]

### Why Java/Kotlin do not beat C#

Java and Kotlin are credible because the JVM ecosystem is deep, Java’s virtual threads improve high-concurrency I/O ergonomics, and both have strong tooling. [V/U] ([docs.oracle.com](https://docs.oracle.com/en/java/javase/25/core/virtual-threads.html?utm_source=openai)) They do not beat C# because their advantages are not clearly higher on 2.1 or 2.3, while they carry more Container Apps cold-start and memory-footprint risk under the brief’s operational criteria. [U]

Kotlin’s null-safety is genuinely attractive for 2.1 because Kotlin documents compile-time handling of potential null-related issues. [V] ([kotlinlang.org](https://kotlinlang.org/docs/null-safety.html?utm_source=openai)) However, Kotlin’s server-side ecosystem often layers Kotlin idioms over Java frameworks, and that mixed implicitness can make AI-agent maintenance less predictable than a disciplined C#/.NET codebase. [U]

### Why TypeScript and Python should not win

TypeScript has a strong MCP and JSON-schema story and would align with the Lit frontend language, but same-language frontend/backend alignment is explicitly Tier 3 in the brief. [U] Node’s non-blocking I/O model is a real strength for HTTP/provider calls, but the event-loop model requires discipline around blocking and CPU-heavy work. [V/U] ([nodejs.org](https://nodejs.org/en/docs/guides/blocking-vs-non-blocking/?utm_source=openai)) The decisive weakness is 2.1: TypeScript improves JavaScript but does not provide the same compile-time/runtime integrity as C# or Java for autonomous multi-file backend refactors. [U]

Python has the best general AI/document-processing ecosystem, but this service delegates heavy document AI to providers and needs durable backend invariants more than notebook-style experimentation. [U] Under the stated criteria, Python’s dynamic nature is the clearest mismatch with high-weight AI-coding-automation fitness. [U]

### Why Rust should not win despite technical strength

Rust has excellent type and memory safety, low runtime overhead, and strong operational properties. [U] Microsoft now documents Azure SDK for Rust crates and OpenTelemetry lists Rust as beta across API/SDK/exporters, so Rust should pass Tier 1 but take a Tier 2.3/2.4 maturity penalty. [V] ([learn.microsoft.com](https://learn.microsoft.com/en-us/azure/developer/rust/azure-sdk-library-package-index?utm_source=openai))

The main reason Rust should not win is AI-agent iteration speed: ownership, lifetimes, compile times, and async trait/generic complexity can turn routine backend changes into longer edit-compile-debug loops. [U] Rust would become more attractive if the service had hard memory-safety constraints, high-throughput CPU-bound parsing, or security-critical native components; the brief describes a Postgres/document-AI-dominated business service instead. [U]

### Provisional decision confidence and flip criteria

My decision confidence is **MEDIUM**: the public ecosystem evidence supports C# strongly, but the most decision-shifting inputs are organization-specific and unavailable in this phase. [U] The single piece of evidence most likely to shift confidence upward or downward would be a small benchmark of the company’s actual AI coding agents performing equivalent multi-file refactors in C#, Go, and TypeScript against a representative modular-monolith skeleton. [U]

**Go overtakes C#** if three conditions are all true: the internal platform strongly prefers non-.NET Linux containers, the production setting uses scale-to-zero or very tight memory budgets where .NET cold start/memory materially affects cost/SLOs, and the representative agent-refactor benchmark shows Go equal or better than C# in defect rate and review time. [U]

**Java overtakes C#** if the company is already a JVM-heavy engineering organization, production runs min-replicas ≥ 1 so cold start is mostly deployment-only, and Java virtual-thread/Spring or Quarkus conventions are already standardized internally. [U]

**TypeScript overtakes C#** only if full-stack staffing constraints dominate the formal criteria and the team accepts stricter runtime validation, linting, codegen, and architectural guardrails to compensate for weaker backend type/runtime safety. [U]

## 4. Sources

1. https://modelcontextprotocol.io/docs/sdk  
2. https://github.com/modelcontextprotocol/csharp-sdk  
3. https://go.sdk.modelcontextprotocol.io/  
4. https://github.com/modelcontextprotocol/rust-sdk  
5. https://github.com/modelcontextprotocol/kotlin-sdk  
6. https://opentelemetry.io/status/  
7. https://opentelemetry.io/api/  
8. https://www.cncf.io/blog/2026/03/24/announcing-a-kotlin-multiplatform-api-and-sdk-for-opentelemetry/  
9. https://azure.microsoft.com/en-us/products/container-apps/  
10. https://learn.microsoft.com/en-us/azure/developer/go/  
11. https://azure.github.io/azure-sdk/  
12. https://github.com/Azure/azure-sdk  
13. https://learn.microsoft.com/en-us/azure/postgresql/connectivity/concepts-connection-libraries  
14. https://learn.microsoft.com/en-sg/azure/azure-cache-for-redis/cache-best-practices-client-libraries  
15. https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/cache-dotnet-core-quickstart  
16. https://learn.microsoft.com/en-us/azure/key-vault/general/client-libraries  
17. https://learn.microsoft.com/en-us/azure/key-vault/general/developers-guide  
18. https://learn.microsoft.com/en-us/azure/developer/rust/azure-sdk-library-package-index  
19. https://learn.microsoft.com/en-us/azure/developer/rust/sdk/overview  
20. https://github.com/Azure/azure-sdk-for-rust  
21. https://nodejs.org/en/docs/guides/blocking-vs-non-blocking/  
22. https://nodejs.org/fr/docs/guides/event-loop-timers-and-nexttick/  
23. https://nodejs.org/en/learn/asynchronous-work/dont-block-the-event-loop  
24. https://docs.oracle.com/en/java/javase/25/core/virtual-threads.html  
25. https://learn.microsoft.com/en-us/aspnet/core/fundamentals/servers/kestrel  
26. https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/nullable-reference-types  
27. https://kotlinlang.org/docs/null-safety.html