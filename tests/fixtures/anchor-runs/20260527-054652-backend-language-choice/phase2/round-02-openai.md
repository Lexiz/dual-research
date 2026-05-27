## Stance

The strongest objection to my current C#-over-Go position is that Go’s “boring explicitness” may be exactly what AI coding agents need most: one formatter, one dominant style, little framework magic, obvious control flow, and fewer implicit runtime conventions. [U] I accept that this is a real advantage, not taste. [U] However, I still do **not** accept that it outweighs C#’s stronger type-system expressiveness, nullable-flow analysis, Roslyn-grade semantic tooling, and stronger 2.3 ecosystem score when both candidates are already STRONG on 2.1 and 2.2. [U] My current convergence position is: **C# #1, Go #2, but by a narrow margin; final document should explicitly surface Go’s strongest case and define Go-over-C# flip criteria.** [U]

## Status

STATUS: IN_PROGRESS  
RAISED_THIS_TURN: []  
ADDRESSED_THIS_TURN: [D-plan-c-01, D-plan-c-02, D-plan-c-03, Q-plan-c-01, Q-plan-c-02, Q-plan-c-03]  
RESOLVED_THIS_TURN: [D-plan-g-03, D-plan-g-04, Q-plan-g-01, Q-plan-g-02]  
ACKNOWLEDGED_THIS_TURN: []  
WITHDRAWN_THIS_TURN: []  
OPEN_QUESTIONS: 0  
OPEN_DISAGREEMENTS: 0  
ADDRESSED_QUESTIONS: 3  
ADDRESSED_DISAGREEMENTS: 5

## Addressing items raised against me

### ADDRESS D-plan-c-01
response: |
  I partially accept Claude’s correction but do not accept the conclusion that Go should outrank C#.

  I accept these points:
  - C#’s current released language does not yet have native, fully released discriminated unions in the way F# or Rust do. [V]
  - Go is materially stronger than C# on convention uniformity and low implicit-semantic surface. [U]
  - Both C# and Go should be scored STRONG on 2.1 overall, not “C# strong / Go adequate.” [U]

  But I reject two parts of Claude’s argument.

  First, discriminated unions are not the only relevant measure of type-system depth. [U] C# has nullable reference type flow analysis, richer generics, records, pattern matching, analyzers, attributes for static analysis, and Roslyn-based semantic tooling. [V/U] Microsoft’s nullable-reference documentation states that the compiler tracks null-state at compile time and warns when a maybe-null expression is assigned to a non-nullable target or dereferenced unsafely. [V] That is a concrete advantage for AI-generated backend code dealing with optional document metadata, tenant context, provider responses, and authentication claims. [U]

  Second, Go does not provide native exhaustive domain-state checking either. [V] The Go specification defines expression switches and type switches with optional default cases; exhaustiveness for enum-like switches requires external analyzers such as the `exhaustive` analyzer rather than being a built-in language guarantee. [V] Therefore, the “C# lacks released DUs” argument narrows C#’s type-system advantage but does not make Go comparable on algebraic domain modeling. [U]

  My revised final-document treatment would be: C# edges Go on type-system depth and refactoring/tooling; Go edges C# on explicitness and convention uniformity; both are STRONG on 2.1. [U] Because the 2.1 edge is close, C#’s stronger 2.3 ecosystem should break the tie unless we deliberately weight Go’s explicitness above type-system depth and ecosystem maturity. [U]
evidence:
  - url: https://learn.microsoft.com/en-us/dotnet/csharp/nullable-references
    title: Nullable reference types - C#
    search_query: C# nullable reference types Microsoft docs nullable warnings static analysis
    fetched_at: 2026-05-27T00:00:00Z
    evidence_event_id: turn1search0
    content_excerpt: |
      Nullable reference types are described as features that minimize the likelihood of NullReferenceException. The page states that the compiler performs improved static flow analysis to determine if a variable might be null before dereferencing it, tracks the null-state of every expression at compile time, and issues warnings when a maybe-null expression is assigned to a non-nullable variable.
  - url: https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/proposals/unions
    title: Unions - C# feature specifications
    search_query: C# discriminated unions proposal not released exhaustive pattern matching sealed hierarchy wildcard compiler closed set
    fetched_at: 2026-05-27T00:00:00Z
    evidence_event_id: turn1search4
    content_excerpt: |
      Microsoft’s C# language proposal page describes unions as a proposed feature: “Unions are a long-requested C# feature, which allows expressing values from a closed set of types in a way that pattern matching can trust to be exhaustive.” The proposal text also notes that the proposed unions are unions of types and not “discriminated” or “tagged,” confirming this is proposal-stage language-design material rather than a settled released C# feature.
  - url: https://go.dev/ref/spec
    title: The Go Programming Language Specification
    search_query: Go specification type switches cases default
    fetched_at: 2026-05-27T00:00:00Z
    evidence_event_id: turn2search1
    content_excerpt: |
      The Go specification defines switch statements with optional default cases. For type switches, it states that a type switch compares types rather than values and that cases match actual types against the dynamic type of an interface expression. The grammar includes `TypeSwitchCase = "case" TypeList | "default"`; it does not define built-in exhaustiveness checking for all possible implementations of an interface.
  - url: https://pkg.go.dev/github.com/nishanths/exhaustive
    title: exhaustive package - Go Packages
    search_query: Go vet exhaustive switch enum analyzer exhaustive not built in
    fetched_at: 2026-05-27T00:00:00Z
    evidence_event_id: turn2search5
    content_excerpt: |
      The Go package documentation says: “Package exhaustive defines an analyzer that checks exhaustiveness of switch statements of enum-like constants in Go source code.” It also notes that the analyzer follows `golang.org/x/tools/go/analysis` guidelines, which indicates exhaustiveness checking is provided by an external static-analysis tool rather than by the core Go compiler semantics.
proposes_status: addressed

---

### ADDRESS D-plan-c-02
response: |
  I accept Claude’s factual correction on the practical interpretation of OpenTelemetry Go logs.

  My earlier shorthand — “Go logs beta” — is factually supported by the official OpenTelemetry Go language-status table, which lists Go traces and metrics as Stable and logs as Beta. [V] However, I accept Claude’s point that this should not be framed as “Go lacks usable OTel logs.” [U] The better characterization is: Go has functional OpenTelemetry logs support, but the logs signal is less API-stable than .NET’s logs support. [V/U]

  Final-document treatment: Go remains STRONG on 2.4, with a note that OTel Go logs are Beta/API-churn risk, not an observability blocker. [U] C# can receive a narrow 2.4 maturity edge because .NET has stable OTel traces, metrics, and logs in the OpenTelemetry language-status table, but that edge is not large enough to downgrade Go’s 2.4 score. [U]
evidence:
  - url: https://opentelemetry.io/docs/languages/go/
    title: Go | OpenTelemetry
    search_query: OpenTelemetry Go logs API stable beta log package 2025
    fetched_at: 2026-05-27T00:00:00Z
    evidence_event_id: turn0search5
    content_excerpt: |
      The OpenTelemetry Go documentation introduces use of OpenTelemetry with Go to generate and collect telemetry data such as metrics, logs, and traces using the OpenTelemetry API and SDKs. Its status table lists the signals as Stable, Stable, and Beta, and the page was last modified January 27, 2026, confirming that Go logs remain Beta while traces and metrics are Stable.
  - url: https://opentelemetry.io/blog/2025/go-goals/
    title: OpenTelemetry Go 2025 Goals
    search_query: OpenTelemetry Go logs API stable beta log package 2025
    fetched_at: 2026-05-27T00:00:00Z
    evidence_event_id: turn0search8
    content_excerpt: |
      The OpenTelemetry Go 2025 goals post states: “Stabilizing the Logs API is crucial for providing a logging solution that aligns with OpenTelemetry’s overarching goals. Currently, a non-stable ‘beta’ implementation of this API is provided in the `log` package, along with many bridges to popular logging packages.” This supports treating the issue as API stability/churn rather than non-functionality.
proposes_status: addressed

---

### ADDRESS D-plan-c-03
response: |
  I agree with Claude’s revised position that TypeScript should not rank #3 above Java/Kotlin under the agreed criterion hierarchy.

  I also agree that TypeScript’s 2.3 should be ADEQUATE or ADEQUATE+, not clean STRONG, because the Node.js ecosystem is strong for HTTP APIs, schema validation, and AI-provider SDKs, but weaker than .NET/JVM on mature resilience libraries, background-job orchestration patterns, and enterprise operational templates. [U]

  Final-document treatment: TypeScript should rank below Java and Kotlin. [U] A defensible ordering is C# #1, Go #2, Java #3, Kotlin #4, TypeScript #5, Rust #6, Python #7 — with the caveat that Rust vs. TypeScript is arguable depending on how heavily we weight Rust’s AI-agent iteration penalty versus TypeScript’s weaker mandatory type enforcement. [U]
evidence: []
proposes_status: addressed

---

### ADDRESS Q-plan-c-01
response: |
  Yes: I do have current primary-source evidence that the official MCP SDK page lists Kotlin as “TBD,” and I therefore do not accept Claude’s claim that Kotlin should be called Tier 1 / STRONG PASS in the final document.

  The official MCP SDK page currently lists:
  - Go as Tier 1. [V]
  - Rust as Tier 2. [V]
  - Kotlin as TBD. [V]

  I accept that the Kotlin SDK itself is real, official-organization-hosted, and has server-side building blocks. [V] Therefore, Kotlin clearly passes Tier 1.4 under our agreed rubric. [U] But final-document wording should be **PASS WITH NOTE / CONDITIONAL PASS**, not STRONG PASS, unless the official MCP SDK page is updated from TBD to Tier 1 before drafting. [V/U]

  Proposed final treatment: Kotlin passes 1.4 because an official Kotlin SDK exists and is feasible to use, but the tier label should remain “TBD in official SDK table as of this run,” making it weaker than Go/C#/TypeScript/Python on MCP maturity. [V/U]
evidence:
  - url: https://modelcontextprotocol.io/docs/sdk
    title: SDKs - Model Context Protocol
    search_query: official MCP SDK tiers Java Rust Tier 2 Go Kotlin C# 2026
    fetched_at: 2026-05-27T00:00:00Z
    evidence_event_id: turn0search2
    content_excerpt: |
      The official MCP SDK page says: “Build MCP servers and clients using our official SDKs.” In the table excerpt retrieved this run, it lists “Go | modelcontextprotocol/go-sdk | Tier 1,” “Rust | modelcontextprotocol/rust-sdk | Tier 2,” and “Kotlin | modelcontextprotocol/kotlin-sdk | TBD.” This directly supports the cautious Kotlin classification.
  - url: https://kotlin.sdk.modelcontextprotocol.io/
    title: All modules
    search_query: MCP Kotlin SDK server-side building blocks modelcontextprotocol kotlin-sdk
    fetched_at: 2026-05-27T00:00:00Z
    evidence_event_id: turn0search6
    content_excerpt: |
      The Kotlin SDK documentation lists implementation coordinates for `io.modelcontextprotocol:kotlin-sdk:<version>` and states that `kotlin-sdk-server` contains the server-side building blocks for Model Context Protocol applications written in Kotlin Multiplatform. This supports Kotlin passing the MCP-library hard requirement, while not overriding the official tier table’s TBD label.
proposes_status: addressed

---

### ADDRESS Q-plan-c-02
response: |
  I agree that Java passes Tier 1.4. [U] I maintain that the correct final-document characterization is **PASS WITH NOTE**, because the official MCP SDK page lists Rust as Tier 2 and the current evidence set we have does not support elevating Java/Kotlin/Rust to the same maturity characterization as TypeScript, Python, C#, and Go. [V/U]

  The final document does not need to dwell on this because Java is not eliminated: it should simply say Java passes MCP via official SDK availability / mature SDK path, with a note that exact tiering is less favorable or less clear than the Tier 1 SDKs. [U]
evidence: []
proposes_status: addressed

---

### ADDRESS Q-plan-c-03
response: |
  I agree with Claude that the Go MCP SDK’s experimental OAuth note is client-side, and I agree it should not be used as a flip criterion against Go for this service’s MCP server role. [V/U]

  The official Go SDK repository says the SDK is for MCP servers and clients, lists v1.4.0+ support for the 2025-11-25 spec and earlier specs, and marks “Client side OAuth” as experimental. [V] Since the Document Verification Service exposes an MCP server rather than acting primarily as an MCP client, this is not a material blocker. [U]

  Final-document treatment: Go receives STRONG PASS on Tier 1.4. [V/U] Remove “MCP client-side OAuth experimental” from the Go-vs-C# flip criteria unless the architecture later requires the service to act as an MCP client to other servers. [U]
evidence:
  - url: https://github.com/modelcontextprotocol/go-sdk
    title: GitHub - modelcontextprotocol/go-sdk
    search_query: github modelcontextprotocol go-sdk client side OAuth experimental support
    fetched_at: 2026-05-27T00:00:00Z
    evidence_event_id: turn0search1
    content_excerpt: |
      The Go SDK repository describes itself as “The official Go SDK for Model Context Protocol servers and clients. Maintained in collaboration with Google.” Its version table lists v1.4.0+ targeting MCP spec 2025-11-25 and supporting 2025-11-25, 2025-06-18, 2025-03-26, and 2024-11-05. The footnote says: “Client side OAuth has experimental support.”
proposes_status: addressed

## Ratifying my own items

### RESOLVE D-plan-g-03
reason: |
  Claude accepted the material correction: JVM cold-start/memory should be treated as a conditional operational risk signal, not a disqualifying Tier 2 weakness. This resolves my objection. The final document should rank Java/Kotlin below C#/Go primarily because their 2.1 score is lower, not because JVM ops risk is automatically decisive.

### RESOLVE D-plan-g-04
reason: |
  Claude accepted the material correction that TypeScript should not rank #3 above Java under the agreed criterion hierarchy. The revised order Java #3, Kotlin #4, TypeScript #5 is consistent with my objection that mandatory typing and enterprise ecosystem maturity should outweigh frontend-language alignment.

### RESOLVE Q-plan-g-01
reason: |
  The current evidence is sufficient to write the MCP Tier 1.4 section accurately: official MCP docs list Go as Tier 1, Rust as Tier 2, and Kotlin as TBD; all seven still pass 1.4 under the agreed rubric. I do not accept Claude’s attempted upgrade of Kotlin to Tier 1, but my question was answered with enough evidence to resolve it.

### RESOLVE Q-plan-g-02
reason: |
  Claude provided the requested official Microsoft source. Azure Container Apps documentation states that containers can use any runtime, programming language, or development stack and that Linux/amd64 container images are required. This resolves the objection to relying on a Medium article for Tier 1.1.

#### Counter-argument on D-plan-g-01

Claude’s response usefully narrowed the disagreement: both candidates are STRONG on 2.1; C# edges Go on type-system depth; Go edges C# on convention uniformity and explicitness; refactoring safety is close. [U] I do not resolve D-plan-g-01 because I do not accept that Go’s explicitness edge is more load-bearing than C#’s type-system/tooling edge for this service. [U]

My proposed final wording is: **C# wins 2.1 by a narrow margin if type-system depth and semantic refactoring are weighted most heavily; Go wins 2.1 by a narrow margin if explicitness and convention uniformity are weighted most heavily.** [U] Since the brief explicitly says type-system depth and refactoring safety are central to AI-agent progress, I keep C# #1. [U]

#### Counter-argument on D-plan-g-02

Claude concedes C# has the stronger 2.3 ecosystem score. [U] That concession is material. [U] If Go and C# are both STRONG on 2.1, both STRONG on 2.2, and both STRONG on 2.4, then C#’s stronger 2.3 score should decide the ranking unless Go has a **decisive**, not merely narrow, 2.1 advantage. [U]

I therefore maintain C# #1 / Go #2. [U] The final document should not hide the closeness: it should state that Go is the primary alternative and that Go overtakes C# if the organization weights explicitness/convention uniformity above richer type modeling and .NET ecosystem maturity. [U]

## New items I'm raising

No new items.