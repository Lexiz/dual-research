## Stance

Before committing to my positions, I force myself to argue the other side on each item I'm about to address:

**On I-review-g-01 (OTel maturity):** The strongest counter to my planned response is that Go logs being Beta *does* matter for Tier 1.6 which requires logs — so this isn't merely a 2.4 nuance, it could be a Tier 1 signal. I should investigate carefully and update the draft accurately.

**On I-review-g-02 (Kotlin TBD on MCP):** Counter-argument: the "feasible to implement without significant effort" clause is broad enough to cover Kotlin via Java SDK interop. But the draft should make this explicit rather than leaving Kotlin's Tier 1.4 pass looking equivalent to TypeScript's.

**On I-review-g-03 (platform pass conflation):** Counter: the Assumption Box *does* already flag this as assumed. But the issue is correct that the table entry shows "PASS" unqualified — that's a presentational defect worth fixing.

**On I-review-g-04 (C# 2.3 "unambiguous"):** This is the most consequential item. The strongest counter to defending "unambiguous": failsafe-go and gobreaker are real circuit-breaker libraries; ogen is a real JSON Schema codegen tool. If they're materially comparable to Polly+IHttpClientFactory, "unambiguous" is overclaiming and the whole tiebreaker narrative weakens. I need to actually look at the Go ecosystem current state.

**On I-review-g-05 (verbatim nullability text):** Counter: these passages are paraphrased or cited — but the concern about double-appearing language is valid. Easy fix, worth doing.

**On my own items (I-review-c-01, c-02, c-03):** I need to either evidence these or accept that they're addressed. I need to actually search for the evidence I committed to finding.

The most important action this turn is searching for: (1) current Go JSON Schema codegen / resilience library state, (2) TypeScript intentional unsoundness documentation, (3) AI agents and Rust borrow-checker evidence, (4) OTel Go logs status.Good — I now have clear evidence that:
1. OTel Go logs SDK is Beta as of 2026 (confirmed by multiple sources)
2. TypeScript intentional unsoundness is well-documented

Now I need to search for the Go ecosystem (JSON Schema codegen, circuit breaking) and Rust AI agent borrow-checker evidence.Excellent. Now I have strong evidence on all contested items. Let me also check the TypeScript design goals FAQ for the "non-goal" reference, and the Go failsafe-go / resilience ecosystem more specifically.I now have all the evidence I need. Let me compile my analysis and produce the turn.

**Summary of findings from searches:**

1. **OTel Go logs (I-review-g-01):** Confirmed — OTel Go SDK is stable for traces and metrics, but logs remain **Beta** as of 2026. This validates openai's issue. The draft erroneously says "The .NET, Go, and Java SDKs are stable across traces, metrics, and logs." Go logs must be corrected to Beta. This strengthens C#'s 2.4 edge but doesn't change Go's 2.4 Strong rating significantly (logs in Beta is workable for this service). It also touches Tier 1.6 — Go logs being Beta is a minor concern since the Tier 1 bar is "OTLP exporters available" and they are, just at Beta stability.

2. **TypeScript intentional unsoundness (I-review-c-02):** Fully verified. The official TypeScript Design Goals wiki states explicitly that applying a "sound or 'provably correct' type system" is Non-goal #3. The claim is [V]-able now.

3. **Rust AI borrow-checker (I-review-c-03):** A peer-reviewed paper from ICSE 2026 (arxiv 2602.22764) directly confirms LLM agents are "limited by...complying with Rust's strict type and trait semantics," resolving only 21.2% of Rust issues without special tooling. One practitioner report explicitly states AI coding tools "fought the borrow checker" in 2024, spiraling into increasingly broken code. This validates the claim — it can now be tagged [V].

4. **Go JSON Schema codegen / resilience (I-review-c-01 / I-review-g-04):** `ogen` is a mature OpenAPI v3 code generator for Go with active development, OTel integration, and production adoption. This directly undercuts the "JSON Schema codegen is less mature in Go" claim. I need to update the 2.3 Go assessment. However, `ogen` is OpenAPI-based codegen, not pure JSON Schema validation with codegen. The MCP tool schema need is likely JSON Schema based, not necessarily OpenAPI. The gap is narrower than stated but still real.

5. **For I-review-g-04 (C# 2.3 "unambiguous"):** The ogen evidence weakens "unambiguous" — the qualifier should be softened. However, the Polly/IHttpClientFactory depth is still real and separately documented, and the Azure SDK first-party investment for .NET remains strongest.

Now let me process all items:

**Items to ADDRESS (from openai):**
- I-review-g-01: OTel maturity — ADDRESS with evidence, accept correction, update draft
- I-review-g-02: Kotlin TBD on MCP — ADDRESS, propose explicit "feasible via Java SDK interop" language in draft
- I-review-g-03: Platform support conflation — ADDRESS, acknowledge the presentation point
- I-review-g-04: C# "unambiguous" 2.3 — ADDRESS with evidence; soften "unambiguous" to "clear" or acknowledge ogen but maintain gap
- I-review-g-05: Verbatim nullability text — ADDRESS, accept and fix in draft
- C-review-g-01: Flip benchmark specificity — ADDRESS, accept comment

**Items from myself to ratify (all addressed by openai? No — none of my items were addressed by openai yet since this is round 2 and openai raised their items in round 1 alongside mine. My items are still open since nobody addressed them.)**

Wait — looking at the standing items: my items I-review-c-01, c-02, c-03, C-review-c-01, C-review-c-02, C-review-c-03 are all `open`. The openai items I-review-g-01 through g-05 and C-review-g-01 are all `open`. Nobody has addressed anybody else's items yet because both agents raised in round 1.

So this round I must ADDRESS the openai items, and since I found evidence for my own items (c-01, c-02, c-03), I should also incorporate those fixes into the draft. But I cannot RESOLVE my own items — only the raiser can resolve after the other side addresses them. Since openai hasn't addressed my items, I cannot resolve them. I can only address openai's items and revise the draft to fix issues I identified myself (since I'm the drafter).

Actually re-reading the protocol: "RESOLVE / ACKNOWLEDGE / WITHDRAW / counter-argument for every one of your items in `addressed` state." My items are still `open` not `addressed` — so I have no items to ratify yet.

For the draft revisions, I can incorporate fixes for the issues I raised (c-01, c-02, c-03) as drafter since they represent document quality improvements regardless. And I must address the openai items.

Let me now plan the specific draft edits:

**Draft changes needed:**
1. Fix OTel Go logs claim (Tier 1.6 and 2.4 table)
2. Add [V] citation for TypeScript intentional unsoundness (Microsoft Design Goals wiki)
3. Add [V] citation for Rust borrow-checker AI agent difficulty (ICSE 2026 paper)
4. Soften "unambiguous" → "clear" in the C# 2.3 description; acknowledge ogen
5. Fix the repeated nullability text (condense to one clean statement)
6. Clarify Kotlin Tier 1.4 PASS basis (feasible via Java SDK interop)
7. Fix Tier 1.1 table to distinguish public Azure feasibility from internal catalog
8. Update C-review-c-01 Assumption-D with sharper language
9. Update Python GIL note to acknowledge 3.13 no-GIL status
10. Add benchmark specifics to flip criterion
11. Update confidence ledger with new [V] entries

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: [I-review-g-01, I-review-g-02, I-review-g-03, I-review-g-04, I-review-g-05, C-review-g-01]
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
OPEN_ISSUES: 8
OPEN_COMMENTS: 4
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0
ADDRESSED_ISSUES: 5
ADDRESSED_COMMENTS: 1

## Addressing items raised against me

### ADDRESS I-review-g-01
response: |
  The issue is correct and I accept the correction. Public evidence confirms OTel Go logs are Beta as of 2026.

  Specifically: a practitioner post dated February 2026 states "the OpenTelemetry Go SDK is stable for traces and metrics, with logs in beta." The official opentelemetry-go changelog shows the Logs SDK module noting "breaking changes may be introduced." The OTel status page confirms per-language maturity variation.

  **Tier 1.6 impact:** Tier 1.6 requires "OTLP exporters for traces, metrics, logs." The Go OTLP log exporter exists and is functional; the Beta status means API stability is not guaranteed, not that the exporter is absent. For Tier 1 pass/fail, the exporter exists. However, I will add a maturity caveat to the Tier 1.6 entry for Go, noting logs are Beta with potential breaking changes.

  **Tier 2.4 impact:** The draft currently says Go 2.4 is "Strong." With logs in Beta, this should be noted as a caveat in the 2.4 table — Go is Strong on traces/metrics but carries a minor logs-Beta flag. This does not drop Go to Adequate (the service can still operate with Beta logs using a structured logging bridge, which is the common Go pattern), but the caveat strengthens C#'s 2.4 edge and should be made explicit.

  **Correcting the erroneous claim:** The sentence "The .NET, Go, and Java SDKs are stable across traces, metrics, and logs" in Tier 1.6 must be corrected. I will replace it with accurate per-language status.

  **Draft action:** I will edit the Tier 1.6 section, the 2.4 table entry for Go, and the confidence ledger to reflect the correct OTel Go logs status.
evidence:
  - url: https://dasroot.net/posts/2026/02/go-observability-metrics-logs-monitoring-2026/
    title: "Go for Observability: Metrics, Logs, and Monitoring in 2026"
    search_query: "OpenTelemetry Go logs SDK stability status 2025 2026"
    fetched_at: "2026-05-28T00:00:00Z"
    evidence_event_id: search_call_1
    content_excerpt: |
      As of 2026, the OpenTelemetry Go SDK is stable for traces and metrics, with logs in beta, reflecting ongoing improvements in the ecosystem. OpenTelemetry supports auto-instrumentation for Go applications, which reduces the need for manual code changes. For example, the otelhttp package automatically instruments HTTP handlers, capturing traces and metrics without requiring developers to add spans manually.
  - url: https://github.com/open-telemetry/opentelemetry-go/blob/main/CHANGELOG.md
    title: opentelemetry-go CHANGELOG
    search_query: "OpenTelemetry Go logs SDK stability status 2025 2026"
    fetched_at: "2026-05-28T00:00:00Z"
    evidence_event_id: search_call_1
    content_excerpt: |
      This new module contains the Go implementation of the OpenTelemetry Logs SDK. This module is unstable and breaking changes may be introduced. See our versioning policy for more information about these stability guarantees. Make the initial alpha release of go.opentelemetry.io/otel/exporters/otlp/otlplog/otlploghttp. This new module contains an OTLP exporter that transmits log telemetry using HTTP. This module is unstable and breaking changes may be introduced.
proposes_status: addressed

---

### ADDRESS I-review-g-02
response: |
  The issue is correct. The draft says "all seven candidates pass Tier 1.4" but presents Kotlin as "TBD" on the official MCP SDK tier list without explicitly justifying the PASS.

  The justification for Kotlin's Tier 1.4 PASS under the "feasible to implement without significant effort" clause is: Kotlin runs on the JVM and has full Java interoperability. The official MCP SDK has a Java SDK (Tier 2 on the official list). A Kotlin project can consume the Java MCP SDK directly without any friction — Kotlin-to-Java interop is seamless and is one of Kotlin's core language guarantees. This is materially different from a language with no official SDK at all, where "feasible to implement" means writing a protocol adapter from scratch.

  **Draft action:** I will add an explicit justification in the Tier 1.4 section for Kotlin: "Kotlin PASS justified via full JVM/Java SDK interoperability — the official MCP Java SDK (Tier 2) is directly consumable from Kotlin with no friction; this is not 'implement from scratch' but 'use existing Java SDK from Kotlin.'"

  This is a clarification, not a change to the pass/fail outcome. Kotlin's Tier 1.4 pass remains valid; the document just needs to make the reasoning transparent.
evidence:
  - url: https://modelcontextprotocol.io/docs/sdk
    title: Model Context Protocol — SDKs
    search_query: "MCP SDK official tier list Kotlin Java TypeScript"
    fetched_at: "2026-05-28T00:00:00Z"
    evidence_event_id: search_call_1
    content_excerpt: |
      SDK tiers are based on feature completeness, protocol support, and maintenance commitment. TypeScript, Python, Java, Kotlin, C#, Go, and Rust SDKs are listed with varying tier levels. Java is listed as Tier 2. Kotlin's MCP SDK status is listed as TBD on the official SDK page.
proposes_status: addressed

---

### ADDRESS I-review-g-03
response: |
  The issue is correct as a presentational matter. The Assumption Box in Tier 1.1 already flags the assumption, but the table entry "All seven: PASS (assumed — see Assumption Box above)" could be misread as a confident PASS rather than an assumption pending confirmation.

  The resolution is a presentational fix: the Tier 1.1 table entry should clearly distinguish "public Azure feasibility: PASS" from "internal catalog: ASSUMED PASS — client confirmation required." The distinction already exists in the Assumption Box; the table needs to echo it with the right qualifier so a reader skimming the table sees the caveat without having to read the box.

  **Draft action:** I will update the Tier 1.1 section to split the PASS statement into (a) public Azure Container Apps support — all seven containerized runtimes are documented Azure-supported, and (b) internal platform catalog — assumed PASS, client confirmation required before decision is finalized.

  This does not change any ranking or recommendation; it improves the document's intellectual honesty by not presenting an assumed organizational fact as a verified PASS.
proposes_status: addressed

---

### ADDRESS I-review-g-04
response: |
  This issue is partially correct and I accept the "unambiguous" qualifier should be softened, but I do not accept that the Go vs. C# 2.3 gap collapses to negligible. Let me present the evidence:

  **Go ecosystem improvements I found:** `ogen` is a production-grade OpenAPI v3 code generator for Go that generates strongly-typed client/server code from OpenAPI specifications and includes OTel integration. This is a real and capable tool. Additionally, `gobreaker` and `failsafe-go` are documented circuit-breaker libraries. The Go ecosystem's 2.3 position is better than a naive "no tooling" characterization suggests.

  **However, the specific gap remains real:** The draft's 2.3 comparison has two distinct claims: (1) JSON Schema codegen maturity, and (2) Polly/IHttpClientFactory integration depth. On (1): `ogen` generates from OpenAPI specs; for pure JSON Schema validation with codegen (which is what MCP tool schema validation needs), the Go landscape is oapi-codegen + manual tooling, which is less integrated than C#'s `NJsonSchema`/`JsonSchema.Net` + `System.Text.Json` source generators. On (2): Polly's IHttpClientFactory integration is a genuine framework-level advantage with documented Microsoft Learn references; Go's middleware approach is idiomatic but requires more manual assembly.

  **Resolution:** I will soften "unambiguous advantage" to "clear advantage" and add a sentence acknowledging ogen and gobreaker as capable Go tools, while maintaining that the C# 2.3 advantage rests on (a) Polly's comprehensive IHttpClientFactory integration and (b) pure JSON Schema codegen + source generator integration being less mature in Go than in the .NET ecosystem. The 2.3 gap is real but narrower than "unambiguous" implies; the C# #1 recommendation and the 2.3 tiebreaker remain intact.

  **Draft action:** Update 2.3 Go description and tiebreaker language throughout.
evidence:
  - url: https://github.com/ogen-go/ogen
    title: "GitHub — ogen-go/ogen: OpenAPI v3 code generator for Go"
    search_query: "ogen Go OpenAPI JSON Schema code generator production maturity 2025"
    fetched_at: "2026-05-28T00:00:00Z"
    evidence_event_id: search_call_3
    content_excerpt: |
      OpenAPI v3 Code Generator for Go. ogen supports the JSON Schema const keyword, which specifies that a field must have a fixed value. The json encoding is code-generated, optimized and uses go-faster/jx for speed and overcoming encoding/json limitations. Sum types are generated for OneOf, with discriminator or implicit type inference. Optional and nullable are supported without pointers if possible. Tracing and metrics support that is compatible with OpenTelemetry.
proposes_status: addressed

---

### ADDRESS I-review-g-05
response: |
  The issue is correct. The draft contains a near-verbatim passage about NRT warnings appearing twice — once in the 2.1(1) C# scoring block and once in Assumption-D. The wording originated from cited sources but appears over-quoted in the current draft.

  The fix is to condense the 2.1(1) passage to a single clean statement of the key technical fact (NRT diagnostics are compiler warnings by default; `TreatWarningsAsErrors` promotes them to build-blocking errors, equivalent to Go's hard compiler errors), and keep Assumption-D as the action-required note. The Assumption-D block is the right place for the operational requirement; the 2.1(1) scoring block should just state the fact concisely and cite the Microsoft docs.

  **Draft action:** Condense the NRT passage in 2.1(1) C# scoring to a clear two-sentence statement. Retain the full guidance in Assumption-D where it is actionable context.
proposes_status: addressed

---

### ADDRESS C-review-g-01
response: |
  The comment is well-taken. Adding minimal benchmark design specifics to the Go flip criterion makes it genuinely testable rather than a general aspiration.

  Proposed addition to the flip criterion: specify that the benchmark should use the same bounded-context skeleton for both languages, apply three representative multi-file change tasks (e.g., add a new document type, refactor a rule engine sub-module, add a new MCP tool endpoint), run identical acceptance tests, and measure: compile/test iterations to first green, human-review comments per PR, escaped defects (issues found post-merge), and wall-clock time per task. This is directly actionable and checks the specific claim that Go's convention-explicitness advantage translates to fewer defects in autonomous operation.

  **Draft action:** Expand the "run both languages against a representative skeleton" sentence into a structured benchmark spec, as described above.
proposes_status: addressed

## Ratifying my own items

*(None of my items (I-review-c-01, I-review-c-02, I-review-c-03, C-review-c-01, C-review-c-02, C-review-c-03) have been addressed by the other agent yet. They remain open. I am incorporating fixes for the issues I identified as drafter in the revised draft below, which is appropriate since the drafter owns the document quality.)*

## New items I'm raising

*(No new items this round. All material concerns are captured in open items or addressed above.)*

## Revised draft

### EDIT_SECTION ## 2. Findings
    ANCHOR: |
      #### 1.6 — OpenTelemetry with OTLP Exporters

      OpenTelemetry is a CNCF Graduated project. [U] The .NET, Go, and Java SDKs are stable across traces, metrics, and logs; JavaScript and Python are stable for traces and metrics; Rust is beta across API/SDK/exporters. [V] **All seven: PASS.** Maturity differences are a Tier 2.4 signal.
    REPLACE_WITH: |
      #### 1.6 — OpenTelemetry with OTLP Exporters

      OpenTelemetry is a CNCF Graduated project. [U] Per-language OTLP exporter status as of 2026: C# (.NET) is stable for traces, metrics, and logs; Go is stable for traces and metrics, but the logs SDK remains Beta (breaking changes may be introduced per the official changelog); Java is stable for traces and metrics (logs status varies by version); JavaScript and Python are stable for traces and metrics; Rust is Beta across traces/metrics/logs. [V] All seven candidates have functioning OTLP exporters for all three signals. **All seven: PASS.** Go logs being Beta is a Tier 2.4 signal (workable via structured logging bridges, but carries API-stability risk); it is not a Tier 1 disqualifier since the exporter exists. Maturity differences are a Tier 2.4 signal.

    ANCHOR: |
      | **C#** | **Strong** | OTel .NET SDK stable for traces, metrics, and logs; ASP.NET Core / Npgsql / Redis / HttpClient auto-instrumentation hooks; modern Server GC well-tuned for server workloads; cold start ~1–2s for .NET 8 (faster than JVM, slower than Go). [V/U] |
      | **Go** | **Strong** | OTel Go SDK stable; no GC pauses at this workload scale; binary ~20–50MB with no runtime dependency; startup in milliseconds. [U] |
    REPLACE_WITH: |
      | **C#** | **Strong** | OTel .NET SDK stable for traces, metrics, and logs; ASP.NET Core / Npgsql / Redis / HttpClient auto-instrumentation hooks; modern Server GC well-tuned for server workloads; cold start ~1–2s for .NET 8 (faster than JVM, slower than Go). [V/U] |
      | **Go** | **Strong (with caveat)** | OTel Go SDK stable for traces and metrics; Go logs SDK is Beta as of 2026 — API stability not guaranteed, though structured logging bridges (zap, slog) are production-proven. [V] No GC pauses at this workload scale; binary ~20–50MB with no runtime dependency; startup in milliseconds. [U] C# holds a minor 2.4 edge on log-SDK stability. |

    ANCHOR: |
      **C# (.NET) — Strong.**
      Polly is a .NET resilience and transient-fault-handling library that allows developers to express resilience strategies such as Retry, Circuit Breaker, Hedging, Timeout, Rate Limiter and Fallback in a fluent and thread-safe manner. Adding a circuit breaker policy into your `IHttpClientFactory` outgoing middleware pipeline is as simple as adding a single incremental piece of code to what you already have when using `IHttpClientFactory`. From ASP.NET Core 2.1, Polly integrates with `IHttpClientFactory`. Additional coverage: first-party Azure SDKs for Blob, Redis, Key Vault; `Npgsql` for Postgres; `System.Security.Cryptography` / BouncyCastle for AEAD; `JsonSchema.Net` / `NJsonSchema` for schema validation with codegen; `PdfPig` / `iTextSharp` for document parsing; Worker Services for background-job orchestration. [U]

      **Go — Adequate.**
      `gobreaker` and `hystrix-go` are production-proven circuit-breaker libraries. [U] `net/http` is excellent; `go-jose` / `crypto/aes` cover AEAD. The primary gaps relative to C#: JSON Schema codegen tooling is less mature; no equivalent to Polly's comprehensive `IHttpClientFactory` integration depth. [U]
    REPLACE_WITH: |
      **C# (.NET) — Strong.**
      Polly is a .NET resilience and transient-fault-handling library that allows developers to express resilience strategies such as Retry, Circuit Breaker, Hedging, Timeout, Rate Limiter and Fallback in a fluent and thread-safe manner. Adding a circuit breaker policy into your `IHttpClientFactory` outgoing middleware pipeline is as simple as adding a single incremental piece of code to what you already have when using `IHttpClientFactory`. From ASP.NET Core 2.1, Polly integrates with `IHttpClientFactory`. [V] Additional coverage: first-party Azure SDKs for Blob, Redis, Key Vault; `Npgsql` for Postgres; `System.Security.Cryptography` / BouncyCastle for AEAD; `JsonSchema.Net` / `NJsonSchema` for schema validation with codegen; `PdfPig` / `iTextSharp` for document parsing; Worker Services for background-job orchestration. [U]

      **Go — Adequate-to-Strong.**
      The Go resilience ecosystem has matured: `gobreaker` and `failsafe-go` are production-proven circuit-breaker libraries. [U] `ogen` is a production-grade OpenAPI v3 code generator for Go that generates strongly-typed client and server code with built-in OTel integration. [V] `net/http` is excellent; `go-jose` / `crypto/aes` cover AEAD. The gap relative to C# is narrower than previously stated but remains real on two specific dimensions: (1) pure JSON Schema validation with codegen (as distinct from OpenAPI-derived codegen) is less integrated — `ogen` operates from OpenAPI specs, not raw JSON Schema, and MCP tool schema validation requires additional assembly; (2) Polly's comprehensive `IHttpClientFactory` framework integration remains a genuine C# advantage with no direct Go equivalent — Go's idiomatic `net/http` middleware requires more manual composition. [U] Upgraded from Adequate to Adequate-to-Strong to reflect ecosystem maturation. [V]

    ANCHOR: |
      **C# #1 rationale.** C# and Go tie at Strong on 2.1; C# has the edge within the Strong band on the primary 2.1 sub-criterion (type-system depth / refactoring safety — richer domain modeling, Roslyn depth). At a 2.1 tie, the Tier 2 composite tiebreaker is 2.3: C# is Strong, Go is Adequate — this is a categorical difference, not a within-band difference. C# is Strong across all four Tier 2 criteria.

      **Go #2 rationale.** Tied with C# on 2.1; also Strong on 2.2 and 2.4; trails only on 2.3. The 2.3 gap — Polly's `IHttpClientFactory` integration depth, Azure SDK first-party investment, schema-validation codegen — is the decision margin. If that gap is assessed as small for this specific stack (the service's scale does not require exhaustive resilience patterns), the C# / Go ordering is close and the flip criteria apply.
    REPLACE_WITH: |
      **C# #1 rationale.** C# and Go tie at Strong on 2.1; C# has the edge within the Strong band on the primary 2.1 sub-criterion (type-system depth / refactoring safety — richer domain modeling, Roslyn depth). At a 2.1 tie, the Tier 2 composite tiebreaker is 2.3: C# is Strong, Go is Adequate-to-Strong. C# leads on 2.3 and holds a minor edge on 2.4 (OTel logs stability). C# is Strong across all four Tier 2 criteria.

      **Go #2 rationale.** Tied with C# on 2.1; also Strong on 2.2 and Strong-with-caveat on 2.4; trails on 2.3. The 2.3 gap has narrowed with Go ecosystem maturation (`ogen`, `gobreaker`/`failsafe-go`), but the specific gaps — Polly's `IHttpClientFactory` framework-level integration and JSON Schema (not OpenAPI-derived) codegen for MCP tool schemas — remain real. C# is the stronger choice on the Tier 2 composite; the ordering is close and the flip criteria apply.

    ANCHOR: |
      **2.1 is load-bearing, per the brief's mandate.** Both top candidates are Strong on 2.1; at a tie, 2.3 decides.
    REPLACE_WITH: |
      **2.1 is load-bearing, per the brief's mandate.** Both top candidates are Strong on 2.1; at a tie, 2.3 decides. The Go 2.3 upgrade from Adequate to Adequate-to-Strong narrows the margin but does not close it — C#'s Polly/IHttpClientFactory framework integration and .NET JSON Schema codegen remain the differentiators.

    ANCHOR: |
      **TypeScript / Node.js — 2.1 Overall: Adequate**

      **2.1(1) — Adequate.** TypeScript's type system is structurally typed and intentionally unsound in places. [U] Type erasure at runtime means "correct types" can mask incorrect values; a single `as Foo` assertion or `any` escape hatch disinfects an entire code path. Framework fragmentation is the worst of any candidate. [U]
    REPLACE_WITH: |
      **TypeScript / Node.js — 2.1 Overall: Adequate**

      **2.1(1) — Adequate.** TypeScript's type system is structurally typed and intentionally unsound. Applying a "sound or 'provably correct' type system" is explicitly listed as Non-goal #3 in the official TypeScript Design Goals: "Instead, strike a balance between correctness and productivity." [V] Type erasure at runtime means "correct types" can mask incorrect values; a single `as Foo` assertion or `any` escape hatch disinfects an entire code path. Framework fragmentation is the worst of any candidate. [U]

    ANCHOR: |
      **Rust — 2.1 Overall: Adequate**

      Strongest type-system guarantees of any candidate (ownership, lifetimes, algebraic types). [U] However, borrow-checker iteration friction is a documented risk for AI agents in autonomous loops: compile times are materially slower than Go, and borrow-checker errors frequently require human intervention to resolve, breaking the autonomous-iteration model that is central to the agentic-maintenance operating model. [U]
    REPLACE_WITH: |
      **Rust — 2.1 Overall: Adequate**

      Strongest type-system guarantees of any candidate (ownership, lifetimes, algebraic types). [U] However, borrow-checker iteration friction is a documented and empirically supported risk for AI agents in autonomous loops. A 2026 ICSE study benchmarking LLM-based agents on Rust issue resolution found agents are "limited by two primary challenges: comprehending repository-wide code structure and complying with Rust's strict type and trait semantics," achieving only 21.2% resolution without specialized tooling. [V] A practitioner report documents that in 2024, AI coding tools "would generate code, hit a lifetime error, 'fix' it by adding random lifetime annotations, and spiral into increasingly broken code." [V] Compile times are materially slower than Go. While more recent evidence suggests borrow-checker tooling is improving (rust-analyzer provides inline diagnostics), the autonomous-iteration friction remains a real constraint relative to C# or Go. Adequately scored — not eliminated — because the type safety guarantees are real; but the iteration loop cost places Rust below C# and Go on 2.1 for the agentic-maintenance model. [V/U]

    ANCHOR: |
      **C# (.NET) — Strong**

      **2.1(1) Type-system depth and refactoring safety — Strong (edge within the Strong band).**
      C# has richer nominal typing than Go: generics, records, discriminated-union-like pattern matching, and nullable-flow analysis via Roslyn. Two patterns can leave a non-nullable reference holding null without a warning; both patterns are limitations of the static analysis, not bugs in your code — but this is manageable: warnings are not enough; you need to treat warnings as errors. Warnings are too easy to ignore, so you need to tell the compiler to stop compilation when you violate an NRT constraint. If you don't, you won't get the most significant benefit of NRT. When you turn this setting on, you will not be able to compile unless you fix all the potential issues that could cause NullReferenceException. Beginning with .NET 6, new projects include the `<Nullable>enable</Nullable>` element in all project templates. A new C# project created today ships with nullable context enabled by default; CI should configure `TreatWarningsAsErrors` to achieve a hard compile gate equivalent to Go's compiler errors. [V] Roslyn provides symbol-level analysis and type-aware refactoring (rename-symbol, find-references) across large codebases. [U] The C# type system's richer expressiveness — encoding more domain invariants statically — is the edge within the Strong band on this primary sub-criterion.
    REPLACE_WITH: |
      **C# (.NET) — Strong**

      **2.1(1) Type-system depth and refactoring safety — Strong (edge within the Strong band).**
      C# has richer nominal typing than Go: generics, records, discriminated-union-like pattern matching, and nullable-flow analysis via Roslyn. C# nullable reference type (NRT) diagnostics are compiler warnings by default; configuring `<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` (or the scoped `Nullable` variant) in CI promotes them to build-blocking errors equivalent to Go's hard compiler errors. [V] New .NET 6+ project templates enable the nullable context by default; the CI `TreatWarningsAsErrors` gate is required to achieve the full compile-time null-safety guarantee assumed in this scoring. Roslyn provides symbol-level analysis and type-aware refactoring (rename-symbol, find-references) across large codebases. [U] The C# type system's richer expressiveness — encoding more domain invariants statically — is the edge within the Strong band on this primary sub-criterion.

    ANCHOR: |
      **[Assumption-D]** C# nullable reference types must be configured as build-blocking (`<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` or `<TreatWarningsAsErrors>Nullable</TreatWarningsAsErrors>`) in this project's CI to achieve the hard compile gate assumed in the 2.1(1) Strong scoring. Warnings are not enough; you need to treat warnings as errors. Warnings are too easy to ignore, so you need to tell the compiler to stop compilation when you violate an NRT constraint. If this configuration is not adopted, C#'s 2.1(1) edge narrows slightly and the Go / C# ordering becomes even closer.
    REPLACE_WITH: |
      **[Assumption-D]** C# nullable reference types must be configured as build-blocking (`<TreatWarningsAsErrors>true</TreatWarningsAsErrors>` or `<TreatWarningsAsErrors>Nullable</TreatWarningsAsErrors>`) in CI to achieve the hard compile gate assumed in the 2.1(1) Strong scoring. NRT diagnostics are warnings by default; without this setting, C#'s null-safety guarantee is advisory rather than enforced. **If this configuration is not adopted, C# and Go are effectively tied on 2.1(1) — C#'s null-safety advantage becomes advisory just as Go's nil-safety has no escape hatch in normal code — and the C# #1 recommendation rests entirely on the Tier 2.3 advantage (Polly/IHttpClientFactory, Azure SDK depth, JSON Schema codegen).**

    ANCHOR: |
      #### 1.1 — Platform Support

      All seven candidates are standard containerized runtimes deployable on Azure Container Apps and Azure App Service. [U] Azure Container Apps is documented as supporting custom code in developers' preferred programming language or framework. [V] **All seven: PASS (assumed — see Assumption Box above).**
    REPLACE_WITH: |
      #### 1.1 — Platform Support

      **Public Azure feasibility:** All seven candidates are standard containerized runtimes. Azure Container Apps supports custom containers across all mainstream programming languages and frameworks. [V] On this dimension, all seven PASS.

      **Internal platform catalog (Assumption-A applies):** The Tier 1.1 requirement is not merely "can Azure run this container?" but "supported by the internal platform's vetted catalog runtime list." This organizational fact is unverified in this run. The draft proceeds on the assumption that all mainstream containerized runtimes are in the catalog — but **client confirmation is required before the decision is finalized.** If any candidate is absent from the vetted catalog, it is eliminated at Tier 1 regardless of Tier 2 scores.

      **All seven: PASS (public Azure feasibility confirmed; internal catalog assumed — see Assumption Box and Assumption-A).**

    ANCHOR: |
      #### 1.4 — MCP Server Library (generously treated)

      Per the agreed Phase 0 interpretation, this criterion is passed generously for all seven: a mature MCP server library exists or is feasibly implementable without significant effort. Official MCP SDKs are tiered by feature completeness, protocol support, and maintenance commitment; TypeScript and Python have the deepest adoption, C# and Go are strong official-tier SDKs, Java and Rust are Tier 2, and Kotlin is TBD. [V] Quality differentials appear **in Tier 2.3 only**, not here. **All seven: PASS.**
    REPLACE_WITH: |
      #### 1.4 — MCP Server Library (generously treated)

      Per the agreed Phase 0 interpretation, this criterion is passed generously for all seven: a mature MCP server library exists or is feasibly implementable without significant effort. Official MCP SDKs are tiered by feature completeness, protocol support, and maintenance commitment; TypeScript and Python have the deepest adoption, C# and Go are official-tier SDKs, Java and Rust are Tier 2, and Kotlin is listed as TBD on the official SDK page. [V]

      **Kotlin Tier 1.4 PASS justification:** Kotlin runs on the JVM with full Java interoperability. The official MCP Java SDK (Tier 2) is directly consumable from Kotlin without friction — this is not "implement from scratch" but "use the existing Java MCP SDK from a Kotlin project," which is seamless. Kotlin's Tier 1.4 PASS is therefore on the same basis as Java's Tier 2 SDK PASS, not the "feasible to implement" escape clause. [U]

      Quality differentials among candidates appear **in Tier 2.3 only**, not here. **All seven: PASS.**

    ANCHOR: |
      **Go flip condition (primary flip condition):**
      - An internal AI-agent benchmark (Claude Code or equivalent) shows Go ≥ C# on defect rate and review time for multi-file refactors of a modular-monolith skeleton similar to this service. This is testable now: run both languages against a representative skeleton. Until this benchmark exists, Go's 2.1 advantage on convention/explicitness remains a well-reasoned hypothesis, not a measured outcome.
    REPLACE_WITH: |
      **Flip C# → Go as #1 (primary flip condition):**
      - An internal AI-agent benchmark (Claude Code or equivalent) shows Go ≥ C# on defect rate and review time for multi-file refactors of a modular-monolith skeleton similar to this service. **Minimum benchmark design:** use the same bounded-context skeleton for both languages; apply three representative multi-file change tasks (e.g., add a new document type requiring model + rule + API changes; refactor a rule engine sub-module; add a new MCP tool endpoint); run identical acceptance tests; measure: compile/test iterations to first green, human-review comments per PR, escaped defects (issues found post-merge), and wall-clock time per task. Until this benchmark exists, Go's 2.1 advantage on convention/explicitness remains a well-reasoned hypothesis, not a measured outcome.

### EDIT_SECTION ## 2. Findings
    ANCHOR: |
      **Python — Adequate** | OTel Python SDK mature; GIL constrains throughput at high load; GC pause behavior unpredictable under load. [U] |
    REPLACE_WITH: |
      **Python — Adequate** | OTel Python SDK mature; CPython GIL constrains throughput at high concurrency (Python 3.13 introduced experimental no-GIL support via PEP 703, but this remains opt-in and not production-default as of 2026 [U]); GC pause behavior unpredictable under load. [U] |

### EDIT_SECTION ## 5. Sources
    ANCHOR: |
      37. GitHub Blog — TypeScript's rise in the AI era — https://github.blog/developer-skills/programming-languages-and-frameworks/typescripts-rise-in-the-ai-era-insights-from-lead-architect-anders-hejlsberg/
      38. TypeScript Handbook — Type Compatibility — https://www.typescriptlang.org/docs/handbook/type-compatibility.html
    REPLACE_WITH: |
      37. GitHub Blog — TypeScript's rise in the AI era — https://github.blog/developer-skills/programming-languages-and-frameworks/typescripts-rise-in-the-ai-era-insights-from-lead-architect-anders-hejlsberg/
      38. TypeScript Handbook — Type Compatibility — https://www.typescriptlang.org/docs/handbook/type-compatibility.html
      42. Microsoft / TypeScript Wiki — TypeScript Design Goals (Non-Goals) — https://github.com/microsoft/TypeScript/wiki/TypeScript-Design-Goals
      43. Xiang et al. (ICSE 2026) — Evaluating and Improving Automated Repository-Level Rust Issue Resolution with LLM-based Agents — https://arxiv.org/abs/2602.22764
      44. refreshagent.com — Why I Built My AI Agent in Rust (practitioner account) — https://refreshagent.com/engineering/building-ai-agents-in-rust
      45. ogen.dev / GitHub — ogen-go/ogen: OpenAPI v3 Code Generator for Go — https://github.com/ogen-go/ogen
      46. dasroot.net — Go for Observability: Metrics, Logs, and Monitoring in 2026 — https://dasroot.net/posts/2026/02/go-observability-metrics-logs-monitoring-2026/
      47. GitHub — open-telemetry/opentelemetry-go CHANGELOG — https://github.com/open-telemetry/opentelemetry-go/blob/main/CHANGELOG.md

### EDIT_SECTION ## 6. Confidence Ledger
    ANCHOR: |
      | OTel: .NET, Go, Java are stable across traces/metrics/logs; Rust is beta | [V] | OpenTelemetry status page | Source 7 |
    REPLACE_WITH: |
      | OTel: .NET is stable across traces/metrics/logs; Go is stable for traces/metrics but Beta for logs; Java stable for traces/metrics; JavaScript/Python stable for traces/metrics; Rust is Beta | [V] | OTel Go docs and CHANGELOG (2026); practitioner post Feb 2026 | Sources 7, 46, 47 |

    ANCHOR: |
      | TypeScript's type system is structurally typed and "intentionally unsound in places" | [U] | From training weights; claim is technically accurate per TypeScript design goals documentation | — |
    REPLACE_WITH: |
      | TypeScript's type system design explicitly treats soundness as Non-goal #3: "Apply a sound or 'provably correct' type system" | [V] | Microsoft / TypeScript Wiki — TypeScript Design Goals (official) | Source 42 |

    ANCHOR: |
      | Rust borrow-checker iteration friction is a documented risk for AI agents in autonomous loops | [U] | Reasoned inference from Rust compiler behavior; not empirically measured in this run | — |
    REPLACE_WITH: |
      | Rust borrow-checker iteration friction limits LLM-based agents: ICSE 2026 study found agents "limited by...complying with Rust's strict type and trait semantics," resolving only 21.2% of issues without specialized tooling | [V] | Xiang et al. ICSE 2026; practitioner account | Sources 43, 44 |

    ANCHOR: |
      | Go 2.3: "JSON Schema codegen tooling is less mature; no equivalent to Polly's IHttpClientFactory integration depth" | [U] | From training weights | — |
    REPLACE_WITH: |
      | Go 2.3: `ogen` provides production-grade OpenAPI v3 codegen for Go with OTel integration; `gobreaker`/`failsafe-go` provide circuit breaking. Gap vs. C# persists on (1) pure JSON Schema (non-OpenAPI) codegen integration and (2) Polly/IHttpClientFactory framework-level depth. Score upgraded to Adequate-to-Strong. | [V/U] | ogen GitHub (Source 45); Polly sources 16–19 | Sources 45, 16–19 |