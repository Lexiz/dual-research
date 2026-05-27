# Research brief

_Compiled from 2 Notion page(s) rooted at `36699f3e-507f-81e8-b6a4-ee77f6232fef`._
_Max depth reached: 1. Complete tree fetched._


---

## Source: Backend Language Choice — Briefing for Dual Research (Generic)

https://www.notion.so/Backend-Language-Choice-Briefing-for-Dual-Research-Generic-36699f3e507f81e8b6a4ee77f6232fef

## Purpose

This document briefs a single technical decision: **which backend language should the Document Verification Service use for its server-side modular monolith?**

The candidates are listed without commentary. The criteria that should distinguish them live in the child page **Decision Criteria & Quality Attributes**, which the Notion ingest pulls in automatically.

## Product context — Document Verification Service

The Document Verification Service is a B2B product that vets business partners (typically carriers in transport and logistics) for use across a multi-product portfolio. Partners submit identity, operating authority, insurance, and country-specific compliance documentation. The service authenticates the documents, runs them through configurable rule sets, and exposes the resulting trust signals to consuming products (commerce marketplace, fleet management platform, freight procurement, shipment visibility).

**Primary users:**

- Partners: submit profile + documentation through a web-component-driven portal.

- Tenant operators (consuming products and their customers): configure vetting rule sets and consume coverage reports.

- Platform admins: maintain the check catalog and shared rules.

- AI agents: invoke the Document Verification Service as an MCP skill on behalf of users.

**Architectural shape:**

- Modular monolith deployed as a single service on the internal platform (Azure, West Europe v1).

- Four bounded contexts: Profile & Consent, Document Intake & Authentication, Rules, Network Signal (phase-2 stub).

- External programmatic surface: MCP server.

- Embedded UI surface: 5 Web Components + a standalone Verification Portal (v1 primary UI).

- Persistence: Azure Postgres (Flexible Server, OLTP, RLS as tenant boundary), Azure Blob, Azure Cache for Redis, Azure Key Vault.

- Edge: Azure API Management.

- Observability: OpenTelemetry SDK (backend choice deferred to engineer review).

This briefing focuses only on the language-choice decision; broader architectural context is summarised here.

## The decision in scope

Choose **one** backend language for the Document Verification Service's server-side modular monolith. The choice covers:

- API process (MCP adapter + internal HTTP boundary for Web Components).

- Outbox worker (at-least-once domain event emission).

- Analysis worker (Postgres `FOR UPDATE SKIP LOCKED` queue, document AI provider abstraction).

- Scheduled-task worker (expiry, daily exports).

All four processes share one codebase (the modular monolith) and run as separate processes inside the same container image.

## Out of scope

The following decisions are already settled:

- Frontend technology (Lit web components, possibly React framing — separate decision).

- Database choice (Azure Postgres Flexible Server, OLTP primary; Azure Blob for documents; Redis for cache).

- Cloud provider (the internal platform runs on Azure — mandated by platform standardisation).

- Observability instrumentation choice (OpenTelemetry SDK; backend choice deferred to engineer review).

- Single-region deployment (West Europe active; multi-region passive deferred to Phase 2).

- Architecture pattern (modular monolith, not microservices).

## Hard constraints

The chosen language must satisfy all of the following:

1. **Internal platform support.** The language and its runtime must be supported by the internal platform's vetted catalog (Azure App Service / Container Apps).

2. **Azure SDK availability.** First-party or mature community SDKs for: Postgres (connection pooling, RLS-aware sessions), Azure Blob, Azure Cache for Redis, Azure Key Vault.

3. **MCP server library.** Mature MCP server SDK available (or feasible to implement without significant friction).

4. **OAuth 2 / OIDC client.** The company's IdP is the primary auth provider; tokens must be validated and propagated through internal HTTP.

5. **OpenTelemetry instrumentation.** OTLP exporters for traces, metrics, logs.

6. **Concurrency primitives sufficient for SKIP LOCKED workers + outbox** — multiple worker processes concurrently with safe Postgres connection management.

## Candidate languages

Candidates under consideration, listed in arbitrary order. No commentary or characterisation here.

- **Go**

- **Rust**

- **Python**

- **TypeScript (Node.js LTS)**

- **C# (.NET)**

- **Kotlin (JVM)**

- **Java (JVM)**

## Known biases in this topic area

When this question is discussed informally, two arguments tend to dominate even when the formal criteria don't support them. Naming them here as part of the topic context, not as instructions:

- **"TypeScript on both sides."** Because the frontend uses TypeScript (Lit), a TypeScript backend feels like a natural fit. This is convenience; many successful systems run different languages frontend and backend. On AI-coding-automation fitness (the highest-weight criterion in the child page), the frontend language has no bearing.

- **"More training data."** TypeScript backend code has very high prevalence in modern LLM training data, so it can feel like a safer AI-coding bet. This clears a floor — every mainstream language clears it — but it doesn't order candidates above the floor. The criteria framework is what does the ordering.

The criteria framework is intentionally written so that whichever language genuinely fits best wins on its own merits — including TypeScript, if it does.

## Where the criteria live

The criteria are in the child page **Decision Criteria & Quality Attributes for the Backend Language Choice**. Dual-research's Notion ingest pulls child pages recursively, so the criteria are part of the input automatically.

_[→ child page: Decision Criteria & Quality Attributes for the Backend Language Choice]_

## Expected output shape

The final document is decision-grade if and only if it contains, in this order:

- **Single ranked recommendation.** One language picked as #1. Other candidates ranked 2 through N, or explicitly eliminated at Tier 1 with the constraint that disqualified them.

- **Decision confidence.** HIGH / MEDIUM / LOW, with a one-sentence reason and a one-sentence statement of the single piece of evidence that would most shift confidence one level.

- **Tier 1 pass/fail per candidate.** Every Tier 1 hard constraint addressed for every candidate. Eliminations explicit.

- **Tier 2 scoring per candidate.** Per-candidate scoring on 2.1, 2.2, 2.3, 2.4 — with **2.1 (AI-coding-automation fitness)** load-bearing in the final ordering, not merely listed. The winning candidate must win on 2.1 or the doc must explain why 2.1 was not decisive here.

- **Flip criteria.** Conditions under which #2 would overtake #1. Explicit and testable — a future reader can check whether the conditions have changed.

- **Final-surfaced disagreements** (if any). Per FSD: both positions, exact final-document treatment, whether it affects the recommendation.

This is the contract for "decision-grade" in this brief. The dual-research assessment skill (`/dr-run-assess`) grades the output against these six bullets as its headline axis.


---

## Source: Decision Criteria & Quality Attributes for the Backend Language Choice

https://www.notion.so/Decision-Criteria-Quality-Attributes-for-the-Backend-Language-Choice-36699f3e507f814ea303c6b04ee77cee

## Why this page exists

This page is the criteria framework for the backend language choice. The parent briefing lists candidates and hard constraints; this page defines the criteria that distinguish the candidates beyond those constraints.

The criteria are split into three tiers:

- **Tier 1 — hard requirements.** Binary pass/fail. A candidate that fails any of these is out of consideration.

- **Tier 2 — high-weight criteria.** The dominant signal for ordering candidates that pass Tier 1.

- **Tier 3 — tie-breaker criteria.** Used when Tier 2 doesn't produce a clear winner.

## Tier 1 — hard requirements (binary pass / fail)

Duplicates the parent briefing's hard constraints, restated here for completeness. Failure on any of these eliminates the candidate from further consideration.

- **1.1** Supported by the internal platform's catalog runtime list (Azure App Service / Container Apps).

- **1.2** First-party or mature SDK for Azure Postgres (connection pooling, RLS-compatible session management).

- **1.3** First-party or mature SDK for Azure Blob, Azure Cache for Redis, Azure Key Vault.

- **1.4** Mature MCP server library available (or feasible to implement without significant effort).

- **1.5** Mature OAuth 2 / OIDC client library.

- **1.6** OpenTelemetry instrumentation with OTLP exporters for traces, metrics, logs.

- **1.7** Can run multiple worker processes (or goroutines / async tasks) concurrently with safe Postgres connection pooling.

## Tier 2 — high-weight criteria

These are the criteria that should drive the final ordering. A candidate wins primarily by being strong on Tier 2.

### 2.1 — AI-coding-automation fitness (HIGHEST WEIGHT)

The Document Verification Service will be developed and maintained substantially by AI coding agents (Claude Code, GitHub Copilot, future agents on top of capable models). The chosen language must be amenable to AI codegen. Specifically:

- **Type-system depth.** Rich, expressive static typing that catches errors at edit-time, not at runtime. AI agents make more progress when the type system catches their mistakes before they ship. Weak or optional typing imposes a much heavier review burden.

- **Convention-over-configuration.** Idiomatic patterns that are widely shared across the ecosystem, so AI agents write code that matches the project's existing style without bespoke conventions. "There is one obvious way to do it" languages score higher.

- **Test scaffolding and determinism.** Built-in or de-facto test framework. Deterministic builds. AI agents iterate via test-driven cycles; a language with flaky builds, non-deterministic test ordering, or hidden state slows the iteration loop substantially.

- **Refactoring safety.** Rename-symbol, find-references, type-aware refactoring across the codebase. LSP support of professional quality. AI agents do large-scale refactors; without safe refactoring tooling, large changes become unsafe.

- **Codebase comprehensibility for LLMs.** Ratio of explicit-to-implicit semantics. Languages with heavy implicit behavior (decorators that change call semantics, monkey-patching, dynamic dispatch by name, magic methods) are harder for LLMs to reason about across a large codebase.

- **Training-data adequacy.** A floor requirement — every mainstream language clears it. It must not become a "more training data = better choice" argument; that's the bias the parent briefing names.

### 2.2 — Concurrency model fit

The Document Verification Service runs four kinds of process inside one container image:

- An **API process** serving sync requests (MCP + internal HTTP), hundreds concurrent.

- An **outbox worker** with at-least-once delivery semantics emitting domain events.

- An **analysis worker** pulling from a Postgres `FOR UPDATE SKIP LOCKED` queue, calling document AI providers with 10s timeouts and circuit breakers.

- **Scheduled-task workers** for document expiry and daily exports.

The language's concurrency model should:

- Express N workers consuming a queue without contention or lock thrashing.

- Handle hundreds of concurrent in-flight HTTP requests with bounded resource use.

- Provide first-class timeout / cancellation primitives for outbound document-AI calls.

- Integrate cleanly with Postgres connection pools that respect RLS session context.

- Avoid blocking-thread-per-request models when serving concurrent HTTP.

### 2.3 — Ecosystem maturity for the Document Verification Service stack

Beyond the Tier 1 hard requirements, mature libraries are needed for:

- **Document parsing** (PDF, image handling, MIME inspection — though the AI provider does the heavy lifting).

- **Provider abstraction patterns** for the Document AI layer (wrapping Anthropic Claude with options to switch or run consensus).

- **Cryptographic primitives** for per-profile envelope keys (GDPR crypto-erasure mechanism). AEAD, key wrapping.

- **Schema validation** for MCP tool schemas (JSON Schema or equivalent, with codegen ideally).

- **Background-job orchestration** patterns (durable queues with idempotency keys, retry/backoff, dead-letter handling).

- **HTTP client with circuit breakers and timeouts** (Hystrix-class stability patterns; per Release-It / Nygard).

### 2.4 — Observability and operational fit

The language should enable:

- OpenTelemetry traces with full request-context propagation through worker boundaries.

- Structured logging with low overhead.

- Metrics emission at production rates without garbage-collection pauses dominating tail latency.

- Memory footprint compatible with Azure Container Apps scaling (small min-replica memory).

- Acceptable cold-start latency for the API process (Container Apps scale-from-zero or low-min scenarios).

## Tier 3 — tie-breaker criteria

Used only when Tier 2 doesn't produce a clear winner.

### 3.1 — Hiring market depth in the company's recruitment markets

Long-term sustainability requires being able to hire engineers. Each candidate has different depth in the geographies where the company recruits (primarily Europe). Every mainstream candidate is hireable, so this rarely tips the decision.

### 3.2 — Build / deployment iteration speed

Faster build cycles improve developer iteration. Languages with slow compile, type-check, or container-build times add friction. AI agents particularly benefit from sub-second feedback loops.

### 3.3 — Same language as frontend ("full-stack alignment")

The frontend uses Lit web components (and potentially React framing). If the backend used the same language, developers could cross-cut between frontend and backend without context-switching.

This is a small convenience, not a structural advantage. Many successful systems use different languages for frontend and backend. The bias notes in the parent briefing apply here — same-language alignment is a Tier 3 tie-breaker, not a Tier 2 signal.

## Arguments that should not order candidates above the floor

Some arguments are observed informally but are not part of the criteria framework. Listed here so the analysis can recognise them as topic-area noise:

- **Training-data prevalence as a primary signal.** "There are more TypeScript backend examples in training data" clears the Tier 2.1 floor; it does not order candidates above the floor.

- **Personal preference.** Not a criterion.

- **Performance benchmarks unless load-bearing.** The Document Verification Service is not a hot-path latency-sensitive system. Document AI calls and Postgres roundtrips dominate latency. Modest performance differences between mainstream languages are not load-bearing here.

- **Generic "modernity" or "what's popular in 2026".** Popularity is a weak proxy for fitness.

- **Team familiarity as a top-line criterion.** Real, but belongs under Tier 3 (hiring market), not above Tier 2.

- **Vendor brand loyalty.** "Azure is a Microsoft service, so .NET is the natural fit" is not a criterion. Azure SDKs for non-Microsoft languages are first-party and mature.

## Risk shapes by candidate

Each candidate has a different shape of risk if it ends up the winner. These are context, not a prescription for what the analysis must do:

- A **JVM language** (Java / Kotlin) carries Container Apps cold-start latency and memory footprint risk.

- **Go** carries ecosystem-gap risk for MCP server libraries and schema-validation codegen.

- **Rust** carries development-velocity-vs-iteration-speed risk for AI agents (compile times, lifetime errors).

- **Python** or **TypeScript** carries type-system-depth risk under heavy AI-driven refactoring.

- **C# / .NET** carries over-reliance-on-Microsoft-conventions risk that may not match the internal platform's broader Azure-on-non-Microsoft-stack norms.
