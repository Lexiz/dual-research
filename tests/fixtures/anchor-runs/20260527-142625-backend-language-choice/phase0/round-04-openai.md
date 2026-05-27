## Stance

Claude’s response to `D-input-g-04` resolves my objection: the corrected interpretation no longer treats .NET Native AOT as an unconditional Go/Rust-equivalent baseline for this service. [U] I accept the revised position because it preserves the real operational upside of AOT while making dependency-graph validation explicit, especially around EF Core, ASP.NET Core feature coverage, and AOT/trimming constraints. [V] With that correction, I have no remaining input-phase disagreements and am ready to converge. [U]

## Status

STATUS: AGREED  
RAISED_THIS_TURN: []  
ADDRESSED_THIS_TURN: []  
RESOLVED_THIS_TURN: [D-input-g-04]  
ACKNOWLEDGED_THIS_TURN: []  
WITHDRAWN_THIS_TURN: []  
OPEN_QUESTIONS: 0  
OPEN_DISAGREEMENTS: 0  
ADDRESSED_QUESTIONS: 0  
ADDRESSED_DISAGREEMENTS: 0

## Addressing items raised against me

None.

## Ratifying my own items

### RESOLVE D-input-g-04
reason: |
  I accept Claude’s response because it materially narrows the overstatement I objected to. [U] The corrected interpretation now says .NET Native AOT is a meaningful 2.4 mitigation, not a baseline assumption that automatically puts C#/.NET in the same operational tier as Go/Rust. [U] That is supported by the evidence: Npgsql 8.0+ documents NativeAOT/trimming compatibility for the lower-level driver, but the Npgsql EF Core notes state that EF Core itself is not yet NativeAOT-compatible, and Microsoft’s Native AOT overview lists limitations such as no dynamic loading, no runtime code generation, trimming constraints, incomplete runtime-library annotation, and limited support for some ASP.NET Core features. [V] ([npgsql.org](https://www.npgsql.org/doc/compatibility.html?utm_source=openai))

  I also accept the practical scoring consequence: C#/.NET should be scored at standard-JIT operational fit by default, with Native AOT called out as a conditional optimization path if the selected framework and dependency graph are verified AOT-compatible. [U] This resolves the only remaining disagreement and should carry forward into the research/drafting phase. [U]

## New items I'm raising

None.

## Phase artifact

### AGREED_INTERPRETATION

#### Scope

- In scope:
  - Single backend language recommendation for the Document Verification Service modular monolith. [U]
  - All four process types sharing one codebase: API process, outbox worker, analysis worker, and scheduled-task worker. [U]
  - Tier 1 pass/fail assessment for all seven candidates: Go, Rust, Python, TypeScript/Node.js, C#/.NET, Kotlin, and Java. [U]
  - Tier 2 scored comparison on criteria 2.1–2.4 using a Strong / Adequate / Weak ordinal scale, with 2.1 AI-coding-automation fitness treated as near-dominant. [U]
  - Tier 3 tie-breaker criteria applied only if Tier 2 does not produce a clear winner. [U]
  - Flip criteria: explicit, testable conditions under which #2 would overtake #1. [U]
  - Final-surfaced disagreements section if any remain after research. [U]
  - Decision confidence: HIGH / MEDIUM / LOW with a one-sentence reason and a one-sentence statement of the single piece of evidence that would most shift confidence. [U]

- Out of scope:
  - Frontend technology choice. [U]
  - Database choice, because Azure Postgres Flexible Server, Azure Blob, and Redis are already settled by the brief. [U]
  - Cloud provider choice, because Azure is mandated by the brief. [U]
  - Observability backend choice, because only OpenTelemetry SDK instrumentation is in scope. [U]
  - Single-region versus multi-region deployment. [U]
  - Architecture pattern, because the modular monolith pattern is already decided. [U]
  - Current team familiarity, because it is not supplied and should be treated as unknown / not used except as a Tier 3 note. [U]

#### Approach

Research proceeds with the following jointly agreed conventions. [U]

**Tier 1 assessment:** Assume all seven candidates pass Tier 1.1 for container deployment on Azure Container Apps, with a documented internal-platform validation dependency. [U] MCP server library availability is not treated as a hard eliminator where an official or production-grade SDK exists; relative MCP SDK maturity may appear only as a small Tier 2.3 ecosystem signal. [U] Remaining Tier 1 criteria must be verified per candidate, and elimination requires explicit evidence of absence rather than mere absence of evidence. [U]

**Tier 2 scoring:** Use a Strong / Adequate / Weak ordinal scale rather than a faux-precise numeric formula. [U] Criterion 2.1 is near-dominant: a candidate scoring materially higher on AI-coding-automation fitness should outrank a lower-2.1 candidate unless the lower-2.1 candidate has an evidence-backed sweep across 2.2, 2.3, and 2.4. [U] The winning candidate must win on 2.1 or the final document must explicitly explain why 2.1 was not decisive. [U]

**Scoring 2.1 — AI-coding-automation fitness:** Score 2.1 as evidence-graded engineering judgment using structured proxies, not as direct measurement of AI-agent productivity on this exact future codebase. [U] The proxies are type-system enforceability, LSP/refactoring maturity, deterministic testing and build behavior, convention-over-configuration, and explicit-versus-implicit semantics. [U] TypeScript and Python should not be grouped as equivalent type-system risks: TypeScript should score materially higher than Python on type-system depth, while still carrying its own risks around `any`, structural typing, JavaScript runtime semantics, and strict-configuration dependence. [U] Training-data prevalence is a floor requirement only and must not order candidates above that floor. [U]

**Scoring 2.2 — concurrency model fit:** Evaluate how cleanly each language supports hundreds of concurrent API requests, worker pools over Postgres `FOR UPDATE SKIP LOCKED`, timeout/cancellation for outbound document-AI calls, and safe connection-pool usage with tenant context. [U] The “same image, separate processes” detail is treated as packaging, not a standalone scoring axis. [U]

**RLS-compatible Postgres pooling:** Treat RLS-compatible session management as a 2.2/2.3 differentiator, not a Tier 1 eliminator absent contrary evidence. [U] Score candidates on whether their dominant Postgres libraries make the safe pattern straightforward: acquire transaction/connection, set tenant context transaction-locally, execute work, commit/rollback, and release without tenant-context leakage. [U]

**Scoring 2.3 — ecosystem maturity:** Evaluate Azure SDKs, Postgres access, Redis, Key Vault, Blob, OAuth/OIDC, MCP, OpenTelemetry, schema validation, document parsing, cryptography, background-job patterns, and HTTP client resilience. [U] MCP maturity gradients belong here if relevant, not in Tier 1, unless research finds a language truly lacks a feasible MCP implementation path. [U]

**Scoring 2.4 — observability and operational fit:** Cold-start latency and memory footprint are genuine 2.4 differentiators because the brief explicitly lists them and they affect Container Apps cost, startup behavior, and replica density. [U] JVM candidates should carry real baseline memory and cold-start concern. [U] Standard JIT .NET occupies an intermediate 2.4 position: meaningfully better than JVM in many operational scenarios but not equivalent to Go/Rust at baseline. [U] .NET Native AOT is a meaningful mitigation and optimization path, but it should not be scored as the default unless the selected dependency graph is verified AOT-compatible. [V] Npgsql 8.0+ is documented as NativeAOT/trimming-compatible, but EF Core is not yet NativeAOT-compatible according to Npgsql’s EF Core release notes, and Microsoft documents Native AOT limitations including no dynamic loading, no runtime code generation, trimming constraints, incomplete runtime-library annotation, and limited ASP.NET Core feature support. [V] ([npgsql.org](https://www.npgsql.org/doc/compatibility.html?utm_source=openai)) Azure SDK release notes show some AOT-related work, including AOT annotations in App Configuration and AOT-compatible Azure.Core model reading/writing support, but this should be treated as progressive coverage rather than a blanket guarantee for every package and call path the service may use. [V] ([azure.github.io](https://azure.github.io/azure-sdk/releases/2025-05/dotnet.html?utm_source=openai))

**C#/.NET framing:** The brief’s “over-reliance on Microsoft conventions” risk is treated as a bias-control note only, not as a scoring penalty. [U] In the described Azure-native environment, .NET’s first-party Azure ecosystem may be a neutral-to-positive ecosystem signal, but the final document must still avoid the vendor-brand shortcut “Azure therefore .NET must win.” [U]

**Team familiarity:** Current-team familiarity is not supplied and should be marked “Tier 3 / not used.” [U] It may be considered only as a future tie-breaker if supplied later and if Tier 2 is genuinely tied. [U]

**Bias controls:** Exclude the following from ordering candidates above the floor: training-data prevalence as a primary signal, full-stack frontend/backend language alignment, vendor brand loyalty, generic performance benchmarks not tied to 2.4 operational characteristics, and team familiarity above Tier 3. [U]

#### Carry-forward items

- [Q-input-c-02] withdrawn: MCP SDK factual question answered in prior research — no further input-phase action needed. [U]
- [Q-input-g-01] resolved: Tier 1.1 should assume container feasibility for all candidates pending internal catalog confirmation; no eliminations on 1.1 grounds absent internal evidence. [U]
- [Q-input-g-02] resolved: Strong / Adequate / Weak ordinal scoring with near-dominant 2.1 is the agreed scoring convention. [U]
- [Q-input-g-03] resolved: MCP threshold is official SDK or production-grade feasible implementation; MCP maturity differences move to Tier 2.3. [U]
- [Q-input-g-04] resolved: Team familiarity is unknown / not used except as a possible Tier 3 tie-breaker if later supplied. [U]
- [D-input-g-01] resolved: 2.1 is evidence-graded engineering judgment using structured proxies and should not be discounted merely because it is not directly measurable. [U]
- [D-input-g-02] resolved: MCP library maturity is not a brittle hard eliminator where adequate implementation paths exist. [U]
- [D-input-g-03] resolved: Multi-process packaging is evaluated under 2.2/2.4 only. [U]
- [Q-input-c-01] resolved: 2.1 is near-dominant but not absolute. [U]
- [Q-input-c-03] resolved: RLS-compatible pooling is a 2.2/2.3 differentiator; safe transaction-scoped tenant context is the scoring pattern. [U]
- [D-input-c-01] resolved: TypeScript scores materially higher than Python on 2.1 type-system depth, while still below stronger static ecosystems where appropriate. [U]
- [D-input-c-02] resolved: C#/.NET “Microsoft conventions mismatch” is a bias-control note, not a scoring penalty. [U]
- [D-input-c-03] resolved: JVM cold-start/memory footprint is a real 2.4 differentiator; .NET must be separated from JVM, but Native AOT should be treated conditionally rather than as baseline. [U]
- [D-input-g-04] resolved: The final document must not claim unconditional Go/Rust-level operational parity for .NET Native AOT; score standard JIT .NET as the baseline and treat Native AOT as a validated optimization path dependent on framework and dependency compatibility. [U]