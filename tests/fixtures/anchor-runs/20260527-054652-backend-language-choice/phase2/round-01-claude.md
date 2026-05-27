## Stance

OpenAI and I agree on the overall research framework, all seven candidates passing Tier 1, Python ranking last, the JVM cold-start risk, and the MEDIUM-HIGH confidence level. The central substantive disagreement is the #1/#2 ordering: I recommend **Go #1, C# #2** while OpenAI recommends **C# #1, Go #2** — a difference that turns on whether Go or C# scores higher on 2.1 AI-coding-automation fitness, specifically on the type-system-depth and refactoring-safety sub-dimensions where OpenAI claims C# leads. There are also narrower disagreements on MCP SDK tier classifications (OpenAI uses a different tier mapping than I found), on OpenTelemetry logs maturity for Go (OpenAI claims "logs beta" while I found stable support), and on whether C#'s DI/framework implicit behavior should depress its 2.1 score enough to matter. The biggest open questions are: (1) the factual state of OpenTelemetry Go logs maturity, and (2) whether Go's type system is genuinely less expressive than C# for the domain-modeling patterns this service needs, or whether C#'s added expressiveness is outweighed by its implicit-semantic surface area.

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: [D-plan-c-01, D-plan-c-02, D-plan-c-03, Q-plan-c-01, Q-plan-c-02, Q-plan-c-03]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 3
OPEN_DISAGREEMENTS: 3
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0

## Addressing items raised against me
*(none — first round)*

## Ratifying my own items
*(none — first round)*

## New items I'm raisingNow I have evidence for the key factual claims. Let me search for one more critical item before writing my raises.I now have sufficient evidence for all three raises. Let me compose them.

---

### RAISE
kind: disagreement
body: |
  OpenAI ranks C# as #1 and Go as #2, primarily arguing that C# has greater type-system depth and domain-model expressiveness than Go, making it superior on 2.1 (the highest-weight criterion). I rank Go as #1 and C# as #2.

  The core of openai's argument is: "Go is weaker than C# on type-system depth and domain-model expressiveness, which matters because Tier 2.1 is explicitly highest-weighted." [U]

  My counter-position: C#'s claimed type-system advantage over Go on 2.1 is overstated for this specific service and use-case, and is outweighed by Go's advantages on the sub-dimensions most predictive of AI-agent failure modes: convention uniformity, codebase explicitness, and absence of implicit-semantic surface. Specifically:

  1. **Discriminated unions (the primary expressiveness gap openai appears to invoke)**: C# does not have native discriminated unions in any currently *released* version. C# 14 discriminated unions are still in proposal stage as of Nov 2025 [V] (source: medium.com/@yathavarajan article: "they are still in the proposal stage and are not available in any released or public preview version of C#"). Current C# simulates DUs via sealed class hierarchies + pattern matching, which lacks compiler-enforced exhaustiveness without a wildcard catch-all [V] (source: ijrussell.github.io: "switch expression requires a wildcard as the compiler has no concept of what a closed set is"). Go achieves comparable exhaustive matching via typed interface switches + iota-style enums. Neither language has first-class DUs available today; C#'s future DU roadmap is not a present-tense advantage.

  2. **Implicit semantic surface (the AI-agent failure mode criterion)**: C#'s ASP.NET Core DI, attribute-driven behavior (`[Authorize]`, `[FromBody]`, `[Transactional]`), and convention-based model binding introduce implicit behavior that AI agents must correctly infer. Go's idiomatic patterns — explicit error returns, no DI framework magic, no decorator-changed semantics — produce code where what the code does is visible in the code. This directly serves the "codebase comprehensibility for LLMs" sub-dimension.

  3. **Convention uniformity**: Go has one formatter, one build system, one dominant error-handling idiom, and one concurrency model. C# has multiple competing logging frameworks, multiple DI lifetimes with footguns, multiple async-context patterns (ConfigureAwait(false) vs. not). This variation creates more surface area for AI-agent errors.

  **How resolving this changes the final document**: The #1 and #2 positions swap, which changes the primary recommendation, the flip criteria, and the decision rationale's framing of what makes the winner win on 2.1.
anchor_type: quote
anchor_text: "Go is weaker than C# on type-system depth and domain-model expressiveness"
evidence_required: true

> quote: "Go is weaker than C# on type-system depth and domain-model expressiveness"

---

### RAISE
kind: disagreement
body: |
  OpenAI characterizes the OpenTelemetry Go logs status as "beta" and uses this to argue that C# has a stronger 2.4 observability posture ("OpenTelemetry's .NET implementation is listed stable across traces, metrics, and logs, which is stronger than the current status for Go logs"). [V] The OTel Go 2025 goals blog confirms the Logs API was still non-stable beta as of January 2025 [V] (source: opentelemetry.io/blog/2025/go-goals: "Currently, a non-stable 'beta' implementation of this API is provided in the log package"). The GitHub tracking issue for 2025 goals lists "Logs API stable" as a goal [V] (source: github.com/open-telemetry/opentelemetry-go/issues/6175).

  However, the practical impact of this "beta" status on Tier 2.4 scoring is minimal and should not alter the 2.4 scoring for Go in the final document, for the following reasons:

  1. The OTel Go Logs Bridge API being "beta" means the *API surface* may change; it does not mean OTLP log export is non-functional. Production Go services already use the OTel logs SDK via bridge packages to popular loggers (slog, zap, logrus). The service needs OTLP log export to work — it does — not API stability guarantees.

  2. The CHANGELOG shows active maintenance of the logs SDK, including fixes to `sdk/log` in very recent releases [V] (source: github.com/open-telemetry/opentelemetry-go releases CHANGELOG: references to `go.opentelemetry.io/otel/sdk/log` and `exporters/otlp/otlplog/otlploggrpc`). The trajectory is toward stability, not abandonment.

  3. Go's standard library `slog` (stable since Go 1.21) provides structured logging without needing the OTel Logs Bridge API at all. A production Go service can use `slog` for structured logs and OTel for traces + metrics, with logs correlating via trace context injection into log fields. This is a common and fully functional pattern.

  The disagreement matters because: if openai's plan scores Go as ADEQUATE on 2.4 (due to logs-beta), while I score it STRONG, this difference could shift the Tier 2 synthesis marginally. But more importantly, if the final document incorrectly characterizes the OTel Go logs situation as a meaningful 2.4 weakness, it gives the reader a false signal. The correct characterization is: OTel Go logs API is pre-stable, not non-functional; the operational risk is API churn risk, not observability gap.
anchor_type: quote
anchor_text: "current status for Go logs, JavaScript logs, Python logs, Kotlin, or Rust"
evidence_required: true

> quote: "current status for Go logs, JavaScript logs, Python logs, Kotlin, or Rust"

---

### RAISE
kind: question
body: |
  OpenAI assigns Kotlin a "CONDITIONAL PASS" (or "PASS WITH NOTE / CONDITIONAL") on Tier 1.4 (MCP SDK), citing that Kotlin's SDK tier is listed as "TBD" on modelcontextprotocol.io/docs/sdk. I assigned Kotlin a STRONG PASS, citing the official Kotlin SDK maintained in collaboration with JetBrains with full feature support.

  The current evidence I found this run shows:
  - The official Kotlin SDK (`io.modelcontextprotocol:kotlin-sdk`) is maintained in the modelcontextprotocol GitHub org, in active development, with coroutines-native APIs, Ktor integration, and support for tools, resources, prompts, completions, and logging [V] (source: github.com/modelcontextprotocol/kotlin-sdk and modelcontextprotocol.github.io/kotlin-sdk).
  - The Kotlin SDK has full server-side implementation including StdioServerTransport, Ktor-based HTTP hosting, WebSocket transport [V] (source: modelcontextprotocol.github.io/kotlin-sdk).

  My question: Does openai have a specific source showing that modelcontextprotocol.io/docs/sdk currently classifies the Kotlin SDK as "TBD" tier (vs. a Tier 1 or equivalent classification)? The MCP docs landing page I retrieved this run doesn't show individual tier assignments in the snippet — it just says "SDKs are classified into tiers" [V] (source: modelcontextprotocol.io/docs/sdk). Given what I found at the Kotlin SDK repo, a "CONDITIONAL PASS" seems too conservative.

  **How resolving this changes the final document**: If Kotlin's 1.4 passes fully (not conditionally), it strengthens Kotlin's Tier 1 posture, potentially removing a factor that depresses its ranking relative to other JVM candidates. This is modest but could affect the relative Java/Kotlin ordering.
anchor_type: quote
anchor_text: "Kotlin receives CONDITIONAL PASS because it is listed but tiered 'TBD'"
evidence_required: true

> quote: "Kotlin receives CONDITIONAL PASS because it is listed but tiered 'TBD'"

---

### RAISE
kind: question
body: |
  OpenAI's plan treats Java's MCP SDK as "Tier 2" and assigns it PASS WITH NOTE. My research found the Java SDK reached 1.0.0 GA, is maintained in collaboration with Spring AI, and is compliant with the 2025-06-18 MCP specification [V] (source: github.com/modelcontextprotocol/java-sdk/releases: "We are pleased to announce the 1.0.0 GA release of the MCP Java SDK"). 
  
  The classification of the Java SDK as "Tier 2" (vs Tier 1) is potentially material because: if the MCP SDK tier page specifically designates Java as Tier 2 even post-GA-release, this is a meaningful factual claim that should be sourced in the final document. If both our findings agree that Java passes 1.4 regardless of which tier label applies, then the tier label is a documentation detail and not material. But if the tier affects how we characterize risk, we should align.
  
  **How resolving this changes the final document**: Unlikely to change Java's position (it passes 1.4 either way), but clarifies the accuracy of the MCP tier footnotes in the Tier 1 table, which a future reader could check.
anchor_type: quote
anchor_text: "Java receive PASS WITH NOTE because they are Tier 2"
evidence_required: false

> quote: "Java receive PASS WITH NOTE because they are Tier 2"

---

### RAISE
kind: disagreement
body: |
  OpenAI scores TypeScript 2.3 (Ecosystem maturity) as STRONG while I score it ADEQUATE-to-STRONG. The final document should align on this because if TypeScript is STRONG on 2.3 and ADEQUATE on 2.1, 2.2, and 2.4, the question arises whether a 2.3 STRONG could pull TypeScript above the JVM candidates (Kotlin/Java) which score STRONG on 2.3 but ADEQUATE on 2.4. This affects the #3 through #5 ranking.

  My position: TypeScript's 2.3 score is ADEQUATE, not STRONG, specifically because:
  - Circuit breaker libraries for Node.js (`opossum`) are less mature and less enterprise-tested than Polly (.NET), Resilience4j (JVM), or even Go's `gobreaker`. The Hystrix-class stability pattern requirement in 2.3 is explicitly named in the criteria.
  - Background-job orchestration in Node.js lacks a native Postgres-queue-backed pattern equivalent to Spring Batch or Hangfire. The Postgres `FOR UPDATE SKIP LOCKED` pattern requires more hand-rolled code in TypeScript than in the JVM or .NET ecosystem.
  - Document parsing libraries for Node.js are thinner than Python's (PyMuPDF, pdfplumber) though this is reduced by the AI-provider doing heavy lifting.

  **How resolving this changes the final document**: If TypeScript 2.3 = STRONG (openai's view), TypeScript's rank could plausibly be #3 ahead of Kotlin/Java. If TypeScript 2.3 = ADEQUATE (my view), Kotlin and Java hold #3/#4 due to STRONG 2.3 scores despite their 2.4 ADEQUATE (cold-start) penalty.
anchor_type: quote
anchor_text: "TypeScript / Node.js... 2.3 Ecosystem maturity... STRONG"
evidence_required: false

> quote: "TypeScript / Node.js... 2.3 Ecosystem maturity... STRONG"

---

### RAISE
kind: question
body: |
  OpenAI's plan suggests the Go MCP SDK's OAuth status might be a concern without specifying exactly what aspects apply server-side vs client-side. My research confirms: [V] the official Go MCP SDK (v1.4.0+) notes "client side OAuth has experimental support" but server-side MCP path is fully compliant with 2025-11-25 spec (source: github.com/modelcontextprotocol/go-sdk version table). The Document Verification Service acts as an MCP *server* (it exposes document-verification skills to AI agent callers), not as an MCP *client* consuming other MCP servers.
  
  Does openai agree that the Go MCP SDK's experimental OAuth status applies only to the client-side path, and that the server-side MCP use case relevant to this brief is fully supported? If yes, this concern should be dropped from the flip criteria in the final document. If no, openai should provide evidence that server-side OAuth flows in the Go MCP SDK are also experimentally flagged.
  
  **How resolving this changes the final document**: If we agree the experimental OAuth is client-only and server-side is fine, this condition is removed from the Go flip criteria, marginally strengthening Go's position. If openai can show server-side OAuth is also affected, it stays.
anchor_type: quote
anchor_text: "MCP lists Go as Tier 1"
evidence_required: true

> quote: "MCP lists Go as Tier 1"

---

**EVIDENCE for D-plan-c-01 (C# vs Go #1/#2 ordering)**

The key factual anchor for D-plan-c-01 is C# discriminated unions not being available in released versions:
Discriminated Unions were described as "finally coming to C# in version 14" but "as of now, they are still in the proposal stage and are not available in any released or public preview version of C#."

Current C# simulates discriminated unions via sealed hierarchies, but "none of the examples is perfect" and "the switch expression requires a wildcard as the compiler has no concept of what a closed set is" — meaning exhaustiveness enforcement is not compiler-guaranteed in current C#.

**EVIDENCE for D-plan-c-02 (OTel Go logs beta status)**

The OpenTelemetry Go 2025 goals blog states: "Stabilizing the Logs API is crucial for providing a logging solution that aligns with OpenTelemetry's overarching goals. Currently, a non-stable 'beta' implementation of this API is provided in the log package, along with many bridges to popular logging packages."

The GitHub 2025 tracking issue lists "Logs API stable" as an explicit 2025 goal alongside runtime metrics stabilization, confirming it was not yet stable at the start of 2025.

However, the most recent release CHANGELOG shows active maintenance of `go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploggrpc` and `go.opentelemetry.io/otel/sdk/log`, indicating functional development is progressing regardless of API stability designation.

**EVIDENCE for Q-plan-c-01 (Kotlin MCP tier)**

The MCP SDK docs state "SDKs are classified into tiers based on feature completeness, protocol support, and maintenance commitment" — the page confirms a tiering system exists but my search result didn't resolve individual tier assignments.

The official Kotlin MCP SDK provides: "Handle MCP protocol messages and lifecycle events with coroutine-friendly APIs · io.modelcontextprotocol:kotlin-sdk – umbrella SDK (client + server APIs)" with full Ktor Streamable HTTP support.

**EVIDENCE for Q-plan-c-03 (Go MCP server-side OAuth)**

The Go SDK version table states: "v1.4.0+ 2025-11-25* ... * Client side OAuth has experimental support" — the asterisk and footnote specifically identify the limitation as client-side only.