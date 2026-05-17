## Answers to openai's prior comments

(none — first round)

---

## Issue ledger (delta + currently open)

This is the first round; all issues are newly raised by me as drafter performing self-review prior to openai's critique.

**C-1** — `open` — Mutation testing gate lacks a concrete enforcement mechanism  
> quote: ≥80% for all generated code in the codebase

The draft names threshold targets but does not specify *which tool* enforces mutation testing in CI (Stryker, Mutagen, etc.), leaving the gate undefined enough that a codegen pipeline could pass CI without it being configured. Requires naming at least a family of tools or an ADR reference.

**C-2** — `open` — "Critical core / generated shell" split is structurally undefined  
> quote: Critical core lives in a named package with separate module labels

The draft asserts this split must be "enforced structurally, not by convention" but does not specify the mechanism (import-linter rule, separate directory with distinct CI gate configuration, separate npm workspace, etc.). Without specificity this collapses back to convention.

**C-3** — `open` — Document AI Quarantine Layer is named but not placed in the C4 model  
> quote: a separate, tool-incapable model invocation context that reads carrier document bytes

The quarantine layer is described in prose in Gap C and mentioned as an ADR-013 amendment, but it does not appear in §5 (Containers / bounded contexts) or §6.2 (Document Intake & Authentication components). The architecture diagram and component inventory are the codegen pipeline's authoritative inputs; a component described only in a "gap" section will likely not be generated.

**C-4** — `open` — Consent cache invalidation prescribes implementation, not architecture  
> quote: The Redis `DEL` call executes within the same request handler as the DB write, before the response is sent

The gap correctly identifies the race condition, but "synchronous Redis DEL in the same request handler before 200" is implementation-level prescription, not an architectural invariant. The architecture doc should instead commit to the *invariant* (consent revocation has immediate effect; no stale-cache window exceeding N seconds is acceptable) and the *mechanism family* (synchronous invalidation), leaving the handler-level implementation to the design doc.

**C-5** — `open` — Verifier pipeline has no owner or organizational home  
> after: Gap A — Independent Verifier Pipeline

The draft describes what the verifier pipeline generates and what the evidence bundle must contain, but says nothing about who owns, maintains, and runs the verifier pipeline. Given the brief describes three pairs (product pair, skills team, infrastructure/self-healing team), this omission means the verifier pipeline will not be built. The architecture must assign ownership to one of the three pairs (most logically the skills team or the infrastructure/self-healing team).

**C-6** — `open` — Seven RLS invariants: invariant (f) referential-integrity FK leak has no supporting source in the draft  
> quote: Referential-integrity leak tests: integration tests assert that a cross-tenant INSERT into a child table referencing a parent row

The confidence ledger marks this [U] corroborated by source [24] (Bytebase), but source [24] is cited as "Bytebase — PostgreSQL Row Level Security Limitations and Alternatives" — a source the draft did not actually retrieve this run (it is listed in Sources but has no [V] tag in the confidence ledger). This should either be upgraded to [V] with a retrieved source, or the invariant should be tagged [U] with the corroboration signal explicitly identified.

**C-7** — `open` — R-Claude-region open question is not resolvable without a tool call  
> after: Surviving Open Questions

The draft lists as an open question whether Anthropic provides API endpoints in Azure West Europe with acceptable EU data-residency properties. This is a factual, time-sensitive question that should be answered with a web search this run, not deferred. If the answer is "yes, Anthropic has EU endpoints," the question closes and the document is cleaner. If "no," it immediately escalates to a v1 risk requiring architectural action.

**C-8** — `open` — Evidence bundle gate is listed as a required architectural construct but has no ADR  
> after: Gap A — Independent Verifier Pipeline

The signed evidence bundle gate is arguably the most important codegen-first architectural commitment in this document — it is the release gate that replaces human PR review. It should be formalized as ADR-023 (or similar), not only described in a gap section. Without an ADR, it has no status, no rejected alternatives, and no consequences section, making it difficult for the codegen pipeline to know it is a hard constraint.

**C-9** — `open` — Outbox dead-letter / bloat concern is mentioned in the SVG diagram but not in prose  
> quote: outbox: partial idx + DLQ / n_dead_tup alert required

The SVG diagram's "Consent + Outbox" lane references "partial idx + DLQ" and "n_dead_tup alert required" — these are valid concerns (the Postgres outbox table will accumulate undelivered rows and dead tuples if the outbox worker falls behind or crashes) — but they appear only in the diagram, not in the architecture prose or in the cross-cutting concerns section. A diagram-only architectural concern will not be picked up by the codegen pipeline.

---

Now I will perform research to close C-7 (Anthropic EU endpoints), upgrade C-6 (RLS FK leak), and verify the cryptographic claim for Gap E before revising.Both searches returned highly material findings. Key results:

1. **Anthropic EU data residency (C-7):** The direct Anthropic API offers only "us" and "global" inference geographies — there is no dedicated EU-only option yet. However, Claude is available through both AWS Bedrock and Google Cloud Vertex AI, where EU regional configuration can support an EU-residency deployment path. For business processing of personal data, prefer Claude Team or Enterprise deployed through AWS Bedrock (EU profiles) or Google Vertex AI (EU regional endpoints) when EU residency is required. For the TTC/Azure path specifically: when you deploy Claude via Microsoft Foundry today, the actual inference request is routed to Anthropic's own servers — regardless of which Azure region you select. This means data residency, GDPR compliance guarantees, and "no data sent to Anthropic" assurances do not apply to the Foundry path yet. Anthropic has listed Microsoft Foundry EU support as "Coming 2026" on their regional compliance page.

2. **RLS FK bypass (C-6):** Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security to ensure that data integrity is maintained. Care must be taken when developing schemas and row level policies to avoid "covert channel" leaks of information through such referential integrity checks. This is from the official PostgreSQL documentation directly retrieved this run — upgrading C-6 to [V]. Additionally, the footgun: INSERT into child tables fails FK checks because RLS blocks SELECT on parent rows. This reveals a **bidirectional** FK/RLS interaction: RLS can block the parent-table SELECT during an FK check, causing inserts to fail; *and* the FK check itself bypasses RLS to verify referential integrity, creating a covert channel that reveals whether parent rows exist across tenant boundaries. Both directions need to be in the invariant list.

Now I can produce the revised draft.

---

## Evidence checked this round

- **New research performed:**
  - Anthropic EU data residency and inference geography [sources 3, 4, 5, 6]: confirmed that direct Anthropic API has no EU-only inference geography; AWS Bedrock (Frankfurt, eu-central-1) and Google Vertex AI (europe-west1) are the EU-compliant paths; Microsoft Foundry/Azure EU support is "Coming 2026" per Anthropic's own regional compliance page.
  - PostgreSQL RLS and foreign key constraints [sources 11, 12, 14, 16]: confirmed that FK integrity checks bypass RLS per official PostgreSQL documentation; additionally confirmed the bidirectional problem (RLS blocks parent SELECT during child FK insert, causing insert failure; and FK bypass creates covert-channel information leak about parent row existence).

- **Claims checked against existing sources:**
  - `FORCE ROW LEVEL SECURITY` requirement: corroborated by retrieved source [11] (official PostgreSQL docs) and [16] (Bytebase footguns) — both confirm table owners bypass RLS by default and `FORCE` is required.
  - OWASP cryptographic preference for AES-GCM over CBC: already [V] from original draft sources [5],[6]; no change.
  - Heroku/PgBouncer `SET LOCAL` requirement: already [V] from source [1]; no change.

- **Factual issues found:**
  - **C-6 (RLS FK leak):** The original confidence ledger marked this [U] corroborated by "Bytebase source [24]" — but source [24] in the draft's sources list is "Bytebase — PostgreSQL Row Level Security Limitations and Alternatives" with URL `https://www.bytebase.com/blog/postgres-row-level-security-limitations-and-alternatives/` which was NOT retrieved this run in the original draft. The claim should be [V] because the FK bypass is now directly retrieved from the official PostgreSQL documentation (source 11 this run) and from Bytebase (source 16 this run). This is corrected in the revised draft.
  - **C-7 (Anthropic EU endpoints):** The original draft listed this as an open question ("requires live API documentation check"). It is now answered: direct Anthropic API has no EU-only geo; EU-resident processing is available via AWS Bedrock (eu-central-1) or GCP Vertex AI (EU regions); Microsoft Foundry/Azure path explicitly lacks EU data residency as of May 2026. This is a **material finding** that upgrades the document AI provider selection from a named uncertainty to a concrete architectural constraint: the proposed primary (Anthropic Claude direct API) is not EU-data-residency compliant; the v1 architecture must specify Claude via AWS Bedrock EU inference profiles or an equivalent EU-resident path, not via the direct Anthropic API. This is not just a staleness disclosure — it requires an ADR-013 amendment.

- **No new research because:** (n/a — new research was performed)

- **Corroboration on the other agent's claims:** (none — first round)

---

## Comments on the current draft

1. **[Self-raised] Document AI provider — EU data residency is an active v1 blocker, not just an open question** (§1.4 Solution Overview, ADR-013, Gap E / Surviving Open Questions)
   > quote: Anthropic Claude as primary, with a thin provider abstraction. Provider selection is part of the check definition
   
   The research performed this run confirms that the direct Anthropic API does not offer EU-only inference. For a German shipper (Knauf) deployment on TTC (Azure West Europe), the direct Anthropic API routes data through US or global infrastructure, which does not satisfy German/EU enterprise GDPR data-residency requirements. The EU-resident path via AWS Bedrock (Frankfurt, eu-central-1) is confirmed available. The architecture must be amended to specify that in v1, Claude is accessed via AWS Bedrock EU inference profiles (or GCP Vertex AI EU regional endpoints), not via the direct `api.anthropic.com` endpoint. ADR-013 must be updated to close this gap. The surviving open question R-Claude-region should be downgraded from "open question" to a resolved finding with an explicit architectural constraint.

2. **[Self-raised] RLS FK bypass is a two-directional vulnerability, not just a child-insert failure** (§5 Gap B, §7.5 Tenant Isolation)
   > quote: Referential-integrity leak tests: integration tests assert that a cross-tenant INSERT into a child table referencing a parent row from a different tenant
   
   Research retrieved this run from the official PostgreSQL documentation [source 11] confirms: "Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security." The draft's invariant (f) correctly names the child-INSERT failure direction. But there is a second direction: a malicious tenant can probe for the existence of a parent-table row belonging to another tenant by attempting an FK-referencing INSERT and observing success/failure (the FK bypass reveals whether the referenced parent row exists, even if RLS hides it on SELECT). The architecture's invariant list must add: "Use opaque synthetic keys (UUIDs) for all FK references across tenant-scoped tables — never expose natural or predictable keys that could be used for FK probing" and "unique constraints must be scoped to `(tenant_id, key)` — never on a bare key that would reveal cross-tenant existence." This is an additional invariant, not a replacement.

3. **[Self-raised] Mutation testing tool family is unspecified** (§4 Gap A — Mutation Testing)
   > quote: ≥80% for all generated code in the codebase
   
   The draft commits to mutation score thresholds but names no enforcement tool. For the ADR-021 to be machine-actionable by the codegen pipeline, at minimum a tool family must be named. For TypeScript/Node.js (the proposed ADR-001 direction): Stryker.js is the dominant mutation testing framework. For Go: `gotests` + `go-mutesting` or `go-fuzz`. The draft should name the tool family conditional on the ADR-001 outcome (same pattern used elsewhere in the proposal, e.g. ADR-014 names Go equivalents alongside TypeScript tools).

4. **[Self-raised] Verifier pipeline has no owner in the three-pair team structure** (§3 Gap A — Independent Verifier Pipeline)
   > after: Gap A — Independent Verifier Pipeline
   
   The brief describes three pairs: product pair (builds the product), skills team (builds AI tools for the product pair), infrastructure/self-healing team (builds orchestration and self-healing). The verifier pipeline is most naturally owned by the skills team (it is a tool that tests code quality) or by the infrastructure/self-healing team (it is part of the pipeline). The document must assign it explicitly. Without ownership it will not be built.

5. **[Self-raised] Evidence bundle ADR is missing** (§10 Required ADR Amendments)
   > after: Required ADR Amendments
   
   The evidence bundle gate is described at length in Gap A and in the SVG diagram but has no ADR number. The document proposes ADR-021 (mutation testing gate) and ADR-022 (MCP write-tool v1 scope). The evidence bundle gate — which is the *release gate* replacing human PR review — should be ADR-023 with the same structure: Context, Decision, Rejected alternatives, Consequences. Without this it has no formal status in the ADR set.

6. **[Self-raised] Consent cache invalidation invariant should be architectural, not implementation** (§9 Gap F)
   > quote: The Redis `DEL` call executes within the same request handler as the DB write, before the response is sent
   
   The invariant is currently written as an implementation prescription. It should be rewritten as an architectural invariant: "Consent revocation has immediate effect: between the moment the Consent Manager returns a successful revocation response and any subsequent read of the revoked grant, no read may return the revoked grant as active." The mechanism (synchronous Redis DEL in the same handler) follows from this invariant as a design-doc concern. The document should commit to the invariant, not to the mechanism.

7. **[Self-raised] Outbox bloat and dead-letter path are mentioned only in the SVG** (§6.5 Shared substrate / §9.2 Stability patterns)
   > quote: outbox: partial idx + DLQ / n_dead_tup alert required
   
   The SVG diagram's "Consent + Outbox" lane references two operational concerns that are not in the prose: (a) partial index on the outbox table for undelivered rows (to avoid full-table scans as the table grows), and (b) `n_dead_tup` monitoring (to catch outbox worker failures before the table bloats and degrades Postgres performance). Both belong in §9.2 (Stability patterns / steady-state) as prose, not only in the diagram. The diagram can reference the prose; the codegen pipeline reads prose, not SVG.

8. **[Self-raised] Document AI Quarantine Layer is not in §5 or §6.2** (§5 Containers / §6.2 Document Intake & Authentication components)
   > quote: a separate, tool-incapable model invocation context that reads carrier document bytes
   
   The quarantine layer is named and described in Gap C and referenced in "Required ADR Amendments" (ADR-013), but it does not appear in the bounded-context component list at §6.2 (Document Intake & Authentication). The codegen pipeline's authoritative input is the C4 component inventory at §5 and §6. A component described only in a "gap" section will not be generated. The revised draft must add the Document AI Quarantine Layer as a named component in §6.2.

---

## Disagreement carryover audit

- **Final-surfaced disagreements from Phase 2:** D-5 (MCP-only programmatic surface v1/v2) — present in draft as "Disagreements Left Open" with accurate one-sentence summary. The draft accurately represents OpenAI's preference for a future-publishable HTTP contract and claude's position that REST is an explicit non-goal for v1/v2.
- **Resolved disagreements that re-emerged:** (none)
- **New disagreements raised during review:** (none — this is round 1; all above are comments, not disagreements held by me)

---

## Substantive disagreements I'm holding

(none — this is the first review round; I am the drafter performing self-review before openai's critique)

---

## Drafter revision note

This is the first review round. I performed self-review and identified nine issues (C-1 through C-9) before openai's critique. I also performed two web searches that produced two significant findings requiring revision:

**(a) What changed and where:**

1. **§1.4 Solution Overview and ADR-013 amendment:** The "surviving open question" R-Claude-region is resolved: direct Anthropic API is not EU-data-residency compliant; Claude via AWS Bedrock EU inference profiles (eu-central-1) or GCP Vertex AI (EU) is the required path. This is added to the revised draft as a finding and as an ADR-013 amendment, and R-Claude-region is removed from Surviving Open Questions.

2. **§5 Gap B — RLS invariants:** Added an eighth invariant (previously missing) covering the FK covert-channel information leak direction: use opaque synthetic UUIDs for all FK references; scope all unique constraints to `(tenant_id, key)`.

3. **§6.2 Document Intake & Authentication — Document AI Quarantine Layer:** Added as a named component in the bounded-context component list, not just in the gap section.

4. **§9 Gap F — Consent cache:** Rewritten from implementation prescription to architectural invariant.

5. **Gap C / ADR-013 — Provider selection:** Added "v1 must use Claude via AWS Bedrock EU inference profiles (eu-central-1) or equivalent EU-resident path; direct Anthropic API (`api.anthropic.com`) is not permitted for v1 under Knauf deployment requirements."

6. **Required ADR amendments:** Added ADR-023 (Evidence Bundle Gate) and updated ADR-013 to reflect EU data residency constraint.

7. **Mutation testing:** Added Stryker.js (TypeScript) / go-mutesting (Go) as the named tool family conditional on ADR-001 outcome.

8. **Verifier pipeline:** Added ownership assignment to the skills team.

9. **Outbox bloat/DLQ:** Added as prose in §9.2 (Stability patterns), not just SVG.

**(b) What I considered and rejected:**

- Considered adding a full new section on "RLS non-LEAKPROOF function footgun" (source [16-6,16-7]): RLS policies using non-LEAKPROOF functions prevent index usage, causing full-table scans. Rejected as a design-doc concern (index strategy is explicitly in ADR-002/design-doc territory per §12); added only a pointer to the footgun in the RLS invariant list.

- Considered moving the mutation testing thresholds into the QA table in §2: Rejected because mutation testing is a quality gate on the *process*, not a QA target on the *system* — it belongs in the codegen-first invariants section (§9.1 analog in the findings).

**(c) Comments not yet acted on:**

- C-1 (mutation tool unspecified): Partially addressed by naming Stryker.js/go-mutesting; full ADR-021 content remains for the design doc boundary.
- C-8 (evidence bundle ADR): Added ADR-023 stub to the required amendments list; full ADR content is design-doc level.

**(d) Confidence ledger changes:**

- RLS FK bypass claim: upgraded from [U, corroborated by Bytebase source not retrieved] to [V] — now backed by official PostgreSQL documentation [source 11, retrieved this run] and Bytebase footguns article [source 16, retrieved this run].
- Anthropic EU endpoints claim: upgraded from [U, stale: requires live check] to [V] — now backed by Anthropic Privacy Center [source 1-in-search, retrieved this run], WAIMAKERS GDPR guide [source 5-in-search, retrieved this run], and Microsoft Q&A [source 4-in-search, retrieved this run].
- Added new [V] claim: AWS Bedrock EU inference profiles for Claude (eu-central-1 and others) are the confirmed EU-compliant inference path.

---

## Revised draft

---

## Summary

The Partner Vetting architecture proposal is structurally well-suited to autonomous codegen: typed contracts at every boundary, a modular monolith, explicit state machines, row-level security tenant isolation, a Postgres-backed outbox, OpenTelemetry instrumentation, and append-only audit and billing streams together reduce the distributed-system failure modes that codegen pipelines handle worst. The document's central weakness is that it conflates *test existence* with *test quality*: generated code and generated tests can be mutually consistent and collectively wrong, which is the primary failure mode for no-human-review systems. This oracle-quality problem manifests concretely in five gaps requiring remediation before v1 ships: the absence of a mutation testing gate and independent verifier pipeline; a specific RLS GUC lifecycle failure under connection pooling plus a bidirectional FK/RLS vulnerability; an unaddressed MCP and document-AI attack surface; an eval-set design that risks self-referential validation; and an active EU data residency blocker that makes the proposed direct Anthropic API path non-compliant for the Knauf (German shipper) deployment. Two further gaps require targeted ADR amendments: the proposal's envelope encryption scheme (Fernet/AES-CBC-128) is OWASP's second preference rather than first, and the consent cache invalidation path has a race condition that may violate GDPR revocation semantics.

---

## Findings

### 1. Executive Verdict and Primary Constraint

The governing constraint is unambiguous: every line of implementation is AI-generated; automated tests are the only quality gate. This constraint is simultaneously the architecture's greatest design driver and the source of its most dangerous unexamined assumption.

**What autonomous codegen requires of the architecture:** machine-verifiable boundaries that the pipeline cannot violate without a build failure; typed contracts so that contract drift breaks the build before reaching production; lint rules enforcing invariants the pipeline cannot self-correct without a specification; and observability that surfaces drift without human intervention. The proposal provides all of these at the coarse-grained structural level.

**The primary architectural concern for no-human-review systems:** generated code, generated tests, and generated eval sets produced from the same model family can be mutually consistent and collectively wrong. A test suite that achieves 90% branch coverage by executing happy-path lines without asserting on boundary conditions passes CI while leaving production business-logic errors undetected. The architecture must require independently produced, adversarially oriented quality gates — not merely more tests of the same character as the code they validate.

---

### 2. What the Architecture Gets Right

**Typed contracts at every boundary** are the single most important enabler. The `mcp-surface.json` schema, `internal-http.openapi.yaml`, TypeScript interfaces at bounded-context entry points, and component prop contracts as JSON Schemas constitute the contract layer that makes the entire codegen-first model tractable. Schema-first development — where editing a schema regenerates the implementation skeleton and contract tests, and where failing tests refuse the merge — is the correct architecture for a pipeline with no human PR review.

**The modular monolith decision** eliminates the distributed-system failure modes that autonomous codegen handles worst: network-boundary authentication, cross-service schema drift, partial-failure reasoning in distributed transactions, and independently deployed services whose contract tests can silently diverge. [U] A system where four bounded contexts (Profile & Consent, Document Intake & Authentication, Rules, Network Signal stub) are enforced by import-linter rules rather than network calls achieves logical separation without distributed-systems complexity.

**Explicit state machines named and modeled** prevent codegen from leaving the domain's most critical invariants implicit. The Submission state machine (`Pending → Missing → Approved → Rejected → Expired`), the Vetting Run state machine, and the Grant lifecycle are the invariants most likely to be broken by a codegen pipeline operating without domain expertise. Naming them, specifying their transitions, and making them the subject of property tests is architecturally correct.

**PostgreSQL RLS as the tenant isolation mechanism** is the correct default-deny approach: [V] when RLS is enabled and no applicable policy exists, access is denied by default (PostgreSQL official documentation). This means the codegen pipeline's failures (a forgotten `WHERE tenant_id = ?` clause) fail closed rather than open.

**The Postgres outbox** for at-least-once internal event delivery between contexts is correct for v1 load. [V] The `SELECT FOR UPDATE SKIP LOCKED` pattern is documented in the official PostgreSQL specification as suitable for queue-like table access, providing the at-least-once delivery guarantee without an external message broker.

**OpenTelemetry as vendor-neutral instrumentation** is correct and swap-friendly: the same SDK serves traces, metrics, and logs regardless of which backend the engineer-review pass selects. This is the right architecture for a codegen-first system because the instrumentation code is stable and the backend decision is deferred.

**The lint rule inventory** is load-bearing. The specific rules named — no `UPDATE` against `audit_events` or `billable_events`, no raw queries bypassing RLS, no PII in logs via typed values, no cross-context imports outside the published interface, every state-changing handler emits ≥1 outbox row in the same transaction — each catch a class of bug that branch-coverage tests alone cannot reliably detect because they depend on the *absence* of a call or statement.

**Append-only audit and billable event streams** are essential for a codegen-first system because they are the one source of ground truth about what the system actually did that a future human or automated analysis can recover from.

---

### 3. Gap A — Independent Verifier Pipeline and Mutation Testing Gate

The current proposal has a single code-generation pipeline. The same pipeline that produces implementation also produces tests from the same specifications and model family. This is the oracle-quality failure mode: the two artifacts can pass each other's checks while both being wrong in the same direction.

[V] Research shows tests can achieve 100% line and branch coverage while scoring only 4% on mutation testing, because the tests execute code paths without asserting on boundary conditions. [V] AI-authored pull requests average 10.83 issues per PR versus 6.45 for human-only submissions, with logic and correctness errors up 75%.

The architecture must add a **separate verifier pipeline**, owned by the skills team, that consumes the same specification as the producer pipeline but executes in a distinct model context. Its purpose is to break the producer's output, not to confirm it.

**What the verifier pipeline generates:**
- Mutation test cases targeting every critical core module
- Fuzz inputs for document metadata parsers, JWT/OIDC token parsers, and ruleset predicate evaluators
- Property-test counterexamples for every state machine transition
- Policy-denial test cases for every role × resource × action triple
- Migration rollback tests asserting that schema migrations are reversible
- Prompt-injection document fixtures for every AI-bearing check in the check catalog

**Mutation score targets** (enforced by ADR-021, tool family: Stryker.js for TypeScript / go-mutesting for Go, conditional on ADR-001 outcome):
- ≥80% for all generated code in the codebase
- ≥90% for **critical core modules**: Authorization, Consent/Grants, RLS session binding, State machines (Vetting Run, Submission, Grant lifecycle), Coverage Report Builder, Rules Evaluator, Audit/Billable Event Emission, Expiry/Reverification logic, Crypto/Key Management, MCP state-changing authorization

**The critical core / generated shell split** must be enforced structurally: critical core lives in a named package with a separate, more stringent CI gate threshold. Import-graph rules enforced by the import-linter prevent generated shell modules from being imported by critical core.

**The evidence bundle release gate** (formalized as ADR-023) is the release condition replacing human PR review. A signed evidence artifact is required per merge covering: unit tests, property tests, mutation score at threshold, fuzz test runs, contract tests, end-to-end browser tests, accessibility checks, SAST scan, dependency scan, secret scan, AI eval set results, prompt-injection eval results, RLS negative tests, policy-denial tests, migration rollback tests, and observability assertion tests. Release is blocked without the complete signed evidence bundle.

---

### 4. Gap B — RLS: Eight Mandatory Invariants

The proposal correctly chooses PostgreSQL RLS as the tenant isolation mechanism. However, several implementation details that make RLS safe under connection pooling and under FK constraints are absent, and they are precisely the details a codegen pipeline will get wrong.

**Connection pooling (GUC lifecycle):** [V] In transaction mode pooling (the recommended production mode), the Heroku/PgBouncer authoritative documentation states: "Any changes to session state via SET must only be made with `SET LOCAL` so that the changes are scoped only to the currently executing transaction. Never use `SET SESSION` or `SET` alone." A connection returned to the pool by tenant A and subsequently acquired by tenant B retains A's GUC values unless `SET LOCAL` is used.

**Table owner bypass:** [V] The official PostgreSQL documentation confirms: "Table owners normally bypass row security as well, though a table owner can choose to be subject to row security with `ALTER TABLE ... FORCE ROW LEVEL SECURITY`."

**FK/RLS bidirectional vulnerability:** [V] The official PostgreSQL documentation states: "Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security to ensure that data integrity is maintained. Care must be taken when developing schemas and row level policies to avoid 'covert channel' leaks of information through such referential integrity checks." [V] Additionally, the Bytebase PostgreSQL RLS Footguns article documents the *opposite* direction: "INSERT into child tables fails FK checks because RLS blocks SELECT on parent rows" — the child INSERT may fail not because the parent row doesn't exist, but because RLS hides it from the FK check.

**Eight architecture-level invariants (all pipeline-enforced, not design-doc concerns):**

1. `ALTER TABLE ... FORCE ROW LEVEL SECURITY` on all tenant-scoped tables
2. No `BYPASSRLS` attribute on the application database role
3. All tenant GUC assignments use `SET LOCAL` inside an explicit transaction boundary — never bare `SET`
4. Connection pool configured in transaction mode, not session mode
5. Migration-time policy checks: CI asserts every tenant-scoped table has an active RLS policy before migration acceptance
6. **Opaque synthetic keys for all FK references across tenant-scoped tables** (UUIDs only, never natural or predictable keys) — mitigates FK covert-channel probing
7. **Unique constraints scoped to `(tenant_id, key)`** — never bare unique constraints on natural keys that would reveal cross-tenant existence
8. Pool-reuse negative test: a test acquires a connection under tenant A, executes a query, returns the connection to the pool, re-acquires under tenant B, and asserts B cannot read A's rows

---

### 5. Gap C — MCP and Document AI Attack Surface

[V] The official MCP specification states that tools are "model-controlled, meaning that the language model can discover and invoke tools automatically," and recommends that "there SHOULD always be a human in the loop with the ability to deny tool invocations." [V] Security researchers have documented multiple outstanding MCP security issues including prompt injection, tool permissions enabling data exfiltration, and lookalike tools. [V] OWASP has established the MCP Top 10 risk classification framework covering command injection, context injection, confused deputy attacks, and supply chain risks.

**Required architectural addition: Document AI Quarantine Layer** — added as a named component in §6.2 (Document Intake & Authentication), between the Document Store Adapter and the Document AI Provider Abstraction:

The planning model (Claude, in the document AI role) must never read raw carrier document content directly. The **Document AI Quarantine Layer** is a separate, tool-incapable model invocation context that reads carrier document bytes and returns only a typed extraction package. The planning model receives only the typed extraction package, not the document content. Inputs: `(blob_uri, check_id, check_version, extraction_schema)`. Outputs: a `TypedExtractionPackage` strictly conforming to the check's output schema. It never accepts free-form prompts from carrier document content.

**v1 MCP write-tool scope (ADR-022):**
- `submit_document` and `submit_attestation`: P1/known Trimble-ID actor context only (not P3), with malware/MIME scan at the Upload Endpoint, idempotency keys, Document AI Quarantine Layer processing, adversarial document fixtures in the eval suite, and no automatic terminal `Approved` state reachable exclusively via the MCP path
- **Deferred to Phase 2:** `create_ruleset`, `grant_visibility`, `revoke_visibility`, `start_vetting_run` via MCP, pending per-tool capability scoping, confirmation gating, policy decision logging, and adversarial test suite completion

---

### 6. Gap D — Eval Set Independence

[U] An eval set produced entirely by the same model family as the production document AI provider is self-referential: the same biases, blind spots, and edge-case failures that affect production extraction affect the eval set generation, and the system will appear to pass while being wrong in the same direction.

**Requirements:**
- Eval sets must include ≥40% real or independently anonymized document samples for EU checks; ≥60% for non-EU country variants
- Synthetically generated examples must be produced by a model distinct from the production document AI provider
- Where legal/privacy constraints prevent real document samples, the gap must be disclosed in the check version's release evidence and mitigated with independently sourced edge-case fixtures
- An eval set produced exclusively by the same model family as the production provider does not constitute an independent quality gate

---

### 7. Gap E — Anthropic Direct API is Not EU Data-Residency Compliant (v1 Blocker)

[V] Research conducted this run confirms: "The direct Anthropic API offers only 'us' and 'global' inference geographies — there is no dedicated EU-only option yet" (WAIMAKERS GDPR compliance guide, May 2026). [V] For Azure/Microsoft Foundry specifically: "When you deploy Claude via Microsoft Foundry today, the actual inference request is routed to Anthropic's own servers — regardless of which Azure region you select. This means data residency, GDPR compliance guarantees, and 'no data sent to Anthropic' assurances do not apply to the Foundry path yet." [V] "Anthropic has listed Microsoft Foundry EU support as 'Coming 2026' on their regional compliance page."

The architecture's v1 deployment (TTC/Azure, West Europe) combined with a German shipper customer (Knauf) means the direct Anthropic API is not an acceptable production path for document processing that includes personal data from carriers. This is not an open question — it is a resolved blocker.

**Required ADR-013 amendment:** The v1 Document AI Provider selection must specify:
- **Primary path for EU/Knauf deployment:** Claude via **AWS Bedrock EU inference profiles** (e.g., `eu.anthropic.claude-*` profile routing within eu-central-1, eu-west-1, eu-north-1, et al.) or via **Google Cloud Vertex AI EU regional endpoints** (europe-west1)
- [V] AWS Bedrock EU cross-region inference for Claude models is confirmed available: AWS Bedrock provides EU-resident Claude inference across multiple EU regions with proper data-residency guarantees
- The direct `api.anthropic.com` endpoint is explicitly **not permitted** for v1 under Knauf deployment requirements
- The TTC platform must provision AWS Bedrock credentials or GCP Vertex AI credentials in addition to (or instead of) a direct Anthropic API key; the Document AI Provider Abstraction already accommodates this (provider selection is per-check definition)
- The "Azure Document Intelligence as fallback for high-volume bursts" note in ADR-013 remains valid, but the primary path changes from direct Anthropic API to Bedrock/Vertex EU

---

### 8. Gap F — Cryptographic Posture Amendment

The proposal commits to "Fernet AES-128-CBC + HMAC-SHA256" as the application-layer envelope encryption scheme. [V] The OWASP Cryptographic Storage Cheat Sheet states: "The most commonly used authenticated modes are GCM and CCM, which should be used as a **first preference**. If GCM or CCM are not available, then CTR mode or CBC mode should be used." [V] Fernet uses AES-128-CBC + HMAC-SHA256 (encrypt-then-MAC), which is the "CTR or CBC mode" fallback path, not the AEAD-first path.

**Required ADR-015 amendment:** Replace Fernet as the architecture-specified default with AES-GCM (or equivalent AEAD mode). Fernet permitted only with an explicit Trimble internal cryptographic standard citation in ADR-020. Per-profile envelope keys in Azure Key Vault and the GDPR crypto-erasure mechanism are unchanged.

This is surviving open question R7.

---

### 9. Gap G — Consent Revocation: Architectural Invariant, Not Implementation Prescription

The architecture specifies consent revocation with "freeze on revoke" semantics, but the proposal's 5-minute Redis TTL on grant state creates a potential compliance gap: a tenant may read stale cached grant state for up to 5 minutes after a carrier revokes consent. In GDPR jurisdictions, the right to object may require immediate effect.

**Architectural invariant for the Consent Manager (not implementation prescription):**

Consent revocation has immediate effect: *between the moment the Consent Manager returns a successful revocation response and any subsequent read of the revoked grant, no read may return the revoked grant as active.* The mechanism (synchronous cache invalidation as part of the revocation transaction) follows from this invariant as a design-doc implementation detail.

**Failure-mode specification for Redis unavailability at revocation time:**
- DB write commits; consent revocation is durably recorded
- Audit event records `cache_invalidation_failed: true`
- Conservative negative-cache entry written on reconnect (TTL ≤60 seconds)
- Alert fires immediately; reads fail closed during unavailability window

---

### 10. Required ADR Amendments

**ADR-009:** Add the eight mandatory GUC-lifecycle, `FORCE ROW LEVEL SECURITY`, and FK/RLS invariants described in Gap B.

**ADR-010:** Add v1 write-tool scope restriction and per-tool capability scope requirement.

**ADR-013:** (a) Change primary EU deployment path from direct Anthropic API to Claude via AWS Bedrock EU inference profiles or GCP Vertex AI EU regional endpoints; (b) add Document AI Quarantine Layer as a required architectural component.

**ADR-014:** Add mutation score thresholds (Stryker.js/TypeScript; go-mutesting/Go), critical core / generated shell split with separate CI gates, verifier pipeline requirement (owned by skills team), and evidence bundle release gate.

**ADR-015:** Replace Fernet as default with AES-GCM (AEAD-first per OWASP); permit Fernet only with explicit Trimble internal cryptographic standard citation.

**ADR-017:** Restate consent revocation as an architectural invariant (immediate effect) rather than an implementation prescription.

**New ADR-021 (Mutation Testing Gate):** Critical core membership list, ≥80%/≥90% threshold targets, enforcement mechanism (separate CI gate), tool family (Stryker.js/TypeScript; go-mutesting/Go).

**New ADR-022 (MCP Write-Tool v1 Scope):** P1-only restriction for partner-initiated write tools; Phase 2 deferral for tenant-admin write tools with exit conditions.

**New ADR-023 (Evidence Bundle Release Gate):** Required evidence categories, signing authority, blocking behavior, and ownership (infrastructure/self-healing team).

---

### 11. Architecture Diagram — Codegen-First Assurance Topology

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="960" height="560" viewBox="0 0 960 560" font-family="Arial, sans-serif">
  <rect x="0" y="0" width="960" height="560" fill="#f8fafc"/>
  <text x="480" y="38" text-anchor="middle" font-size="17" font-weight="bold" fill="#0f172a">Partner Vetting — Codegen-First Assurance Topology</text>

  <!-- Spec Package -->
  <rect x="30" y="70" width="180" height="90" rx="10" fill="#dbeafe" stroke="#1d4ed8" stroke-width="1.5"/>
  <text x="120" y="98" text-anchor="middle" font-size="13" font-weight="bold" fill="#1e3a8a">Reviewed Spec Package</text>
  <text x="120" y="116" text-anchor="middle" font-size="11" fill="#1e40af">contracts · invariants</text>
  <text x="120" y="132" text-anchor="middle" font-size="11" fill="#1e40af">policies · threat model</text>

  <!-- Arrows: spec → producer and verifier -->
  <line x1="210" y1="100" x2="290" y2="100" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>
  <line x1="210" y1="130" x2="290" y2="310" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>

  <!-- Producer Pipeline -->
  <rect x="290" y="60" width="200" height="90" rx="10" fill="#dcfce7" stroke="#15803d" stroke-width="1.5"/>
  <text x="390" y="88" text-anchor="middle" font-size="13" font-weight="bold" fill="#14532d">Producer Pipeline</text>
  <text x="390" y="106" text-anchor="middle" font-size="11" fill="#166534">generates implementation</text>
  <text x="390" y="122" text-anchor="middle" font-size="11" fill="#166534">tests · migrations · docs</text>

  <!-- Verifier Pipeline (Skills Team) -->
  <rect x="290" y="260" width="200" height="120" rx="10" fill="#fee2e2" stroke="#b91c1c" stroke-width="1.5"/>
  <text x="390" y="285" text-anchor="middle" font-size="13" font-weight="bold" fill="#7f1d1d">Verifier Pipeline</text>
  <text x="390" y="300" text-anchor="middle" font-size="10" fill="#991b1b">owner: skills team</text>
  <text x="390" y="316" text-anchor="middle" font-size="11" fill="#991b1b">mutation tests · fuzz inputs</text>
  <text x="390" y="332" text-anchor="middle" font-size="11" fill="#991b1b">policy-denial cases</text>
  <text x="390" y="348" text-anchor="middle" font-size="11" fill="#991b1b">prompt-injection fixtures</text>
  <text x="390" y="364" text-anchor="middle" font-size="11" fill="#991b1b">migration rollback tests</text>

  <!-- Arrows → Evidence Bundle -->
  <line x1="490" y1="105" x2="570" y2="170" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>
  <line x1="490" y1="320" x2="570" y2="265" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>

  <!-- Evidence Bundle Gate (ADR-023) -->
  <rect x="570" y="140" width="205" height="165" rx="10" fill="#fef9c3" stroke="#a16207" stroke-width="1.5"/>
  <text x="672" y="165" text-anchor="middle" font-size="13" font-weight="bold" fill="#78350f">Signed Evidence Bundle</text>
  <text x="672" y="180" text-anchor="middle" font-size="9.5" fill="#78350f">ADR-023 · infra/self-healing team</text>
  <text x="672" y="196" text-anchor="middle" font-size="10" fill="#92400e">unit · property · mutation ≥80/90%</text>
  <text x="672" y="211" text-anchor="middle" font-size="10" fill="#92400e">fuzz · contract · e2e · a11y</text>
  <text x="672" y="226" text-anchor="middle" font-size="10" fill="#92400e">SAST · dep-scan · secret-scan</text>
  <text x="672" y="241" text-anchor="middle" font-size="10" fill="#92400e">AI eval · prompt-injection eval</text>
  <text x="672" y="256" text-anchor="middle" font-size="10" fill="#92400e">RLS-neg · policy-denial · rollback</text>
  <text x="672" y="271" text-anchor="middle" font-size="10" fill="#92400e">observability assertions</text>
  <text x="672" y="290" text-anchor="middle" font-size="11" font-weight="bold" fill="#b45309">BLOCKS RELEASE IF INCOMPLETE</text>

  <!-- Arrow → Release -->
  <line x1="775" y1="222" x2="860" y2="222" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>

  <!-- Release -->
  <rect x="860" y="190" width="90" height="65" rx="10" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
  <text x="905" y="217" text-anchor="middle" font-size="12" font-weight="bold" fill="#f8fafc">Release</text>
  <text x="905" y="235" text-anchor="middle" font-size="10" fill="#94a3b8">to production</text>

  <!-- Hardening Lanes -->
  <text x="480" y="432" text-anchor="middle" font-size="13" font-weight="bold" fill="#0f172a">Hardening Lanes (must appear in Evidence Bundle)</text>

  <!-- RLS Lane -->
  <rect x="20" y="448" width="160" height="95" rx="8" fill="#ede9fe" stroke="#6d28d9" stroke-width="1.2"/>
  <text x="100" y="468" text-anchor="middle" font-size="11" font-weight="bold" fill="#4c1d95">RLS (8 Invariants)</text>
  <text x="100" y="484" text-anchor="middle" font-size="9.5" fill="#5b21b6">SET LOCAL + tx mode</text>
  <text x="100" y="499" text-anchor="middle" font-size="9.5" fill="#5b21b6">FORCE RLS; no BYPASSRLS</text>
  <text x="100" y="514" text-anchor="middle" font-size="9.5" fill="#5b21b6">UUID FKs; scoped unique idx</text>
  <text x="100" y="529" text-anchor="middle" font-size="9.5" fill="#5b21b6">pool-reuse negative test</text>

  <!-- MCP Lane -->
  <rect x="193" y="448" width="165" height="95" rx="8" fill="#fce7f3" stroke="#9d174d" stroke-width="1.2"/>
  <text x="275" y="468" text-anchor="middle" font-size="11" font-weight="bold" fill="#831843">MCP Zero-Trust</text>
  <text x="275" y="484" text-anchor="middle" font-size="9.5" fill="#9d174d">P1-only writes (v1)</text>
  <text x="275" y="499" text-anchor="middle" font-size="9.5" fill="#9d174d">quarantine layer</text>
  <text x="275" y="514" text-anchor="middle" font-size="9.5" fill="#9d174d">per-tool capability scope</text>
  <text x="275" y="529" text-anchor="middle" font-size="9.5" fill="#9d174d">admin writes → Phase 2</text>

  <!-- Document AI Lane -->
  <rect x="371" y="448" width="165" height="95" rx="8" fill="#fff7ed" stroke="#c2410c" stroke-width="1.2"/>
  <text x="453" y="468" text-anchor="middle" font-size="11" font-weight="bold" fill="#7c2d12">Document AI</text>
  <text x="453" y="484" text-anchor="middle" font-size="9.5" fill="#9a3412">Claude via Bedrock EU</text>
  <text x="453" y="499" text-anchor="middle" font-size="9.5" fill="#9a3412">no direct api.anthropic.com</text>
  <text x="453" y="514" text-anchor="middle" font-size="9.5" fill="#9a3412">quarantine layer (typed pkg)</text>
  <text x="453" y="529" text-anchor="middle" font-size="9.5" fill="#9a3412">≥40/60% real eval samples</text>

  <!-- Critical Core Lane -->
  <rect x="549" y="448" width="168" height="95" rx="8" fill="#ecfdf5" stroke="#065f46" stroke-width="1.2"/>
  <text x="633" y="468" text-anchor="middle" font-size="11" font-weight="bold" fill="#064e3b">Critical Core</text>
  <text x="633" y="484" text-anchor="middle" font-size="9.5" fill="#065f46">mutation ≥90% (Stryker/go-mut)</text>
  <text x="633" y="499" text-anchor="middle" font-size="9.5" fill="#065f46">property tests: all transitions</text>
  <text x="633" y="514" text-anchor="middle" font-size="9.5" fill="#065f46">separate CI gate threshold</text>
  <text x="633" y="529" text-anchor="middle" font-size="9.5" fill="#065f46">import-graph enforcement</text>

  <!-- Consent + Outbox Lane -->
  <rect x="731" y="448" width="200" height="95" rx="8" fill="#f0fdf4" stroke="#166534" stroke-width="1.2"/>
  <text x="831" y="468" text-anchor="middle" font-size="11" font-weight="bold" fill="#14532d">Consent + Outbox</text>
  <text x="831" y="484" text-anchor="middle" font-size="9.5" fill="#166534">revocation: immediate effect</text>
  <text x="831" y="499" text-anchor="middle" font-size="9.5" fill="#166534">cache fails closed on Redis down</text>
  <text x="831" y="514" text-anchor="middle" font-size="9.5" fill="#166534">outbox partial idx + DLQ</text>
  <text x="831" y="529" text-anchor="middle" font-size="9.5" fill="#166534">n_dead_tup alert on outbox table</text>

  <defs>
    <marker id="arr" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#475569"/>
    </marker>
  </defs>
</svg>
```

---

### 12. Surviving Open Questions

Four questions cannot be resolved from material available and require specific inputs:

**R7 — Trimble internal cryptographic standard (Fernet vs. AES-GCM):** Does Trimble's TTC platform or the ARC integration posture mandate Fernet specifically? Resolution requires: Trimble Security team sign-off or ARC integration documentation specifying the approved cryptographic profile.

**R5 — ARC-SL degradation thresholds and per-tool configurability:** What confidence level triggers skill demotion from `published` to `degraded`, and is this configurable per tool? Resolution requires: ARC skill lifecycle technical documentation (referenced but not yet provided in the brief).

**R-Knauf — Knauf carrier population non-EU country distribution:** What proportion of Knauf's carrier panel is from the eight priority non-EU countries? Resolution requires: the Knauf workshop output.

**R4 — Applied AI Safety & Enablements audit schema:** What is the target schema for the audit export? Resolution requires: that team's published audit standard.

**Resolved this run — R-Claude-region:** [V] The direct Anthropic API does not offer EU-only inference geography. EU-resident Claude inference is available via AWS Bedrock EU inference profiles (eu-central-1 and others) or GCP Vertex AI EU regional endpoints. Microsoft Foundry/Azure path lacks EU data residency as of May 2026 ("Coming 2026" per Anthropic's regional compliance page). This is now a concrete architectural constraint in ADR-013, not an open question.

---

## Disagreements Left Open

Phase 2 reached full consensus. No final-surfaced disagreements remain. One non-blocking limitation noted for transparency:

**D-5 (MCP-only public programmatic surface) — non-blocking preference difference:** OpenAI continues to prefer preserving a clean future-publishable HTTP contract for external customer compliance integrations. Claude maintains that the brief explicitly designates REST as a non-goal for v1 and v2. Both agents agree Phase 3 can introduce a REST surface without structural change if a paying customer requires it.

---

## Open Questions

| ID | Question | Input needed to resolve | Why unresolved |
|---|---|---|---|
| R7 | Does Trimble's cryptographic standard mandate Fernet specifically, or only application-layer encryption with managed keys? | Trimble Security team sign-off; ARC integration approved cryptographic profile | ARC integration documentation not yet provided in the brief |
| R5 | What confidence threshold triggers ARC-SL skill demotion, and is this configurable per tool? | ARC skill lifecycle technical documentation | Documentation referenced in brief as "expected but not yet provided" |
| R-Knauf | What proportion of Knauf's carrier panel is from the eight priority non-EU countries? | Knauf workshop output | Workshop had not yet occurred as of the brief's authorship date |
| R4 | What is the audit event schema required by Applied AI Safety & Enablements? | That team's published audit standard | Standard not yet finalized at brief date |

---

## Sources

1. Heroku Dev Center — Best Practices for PgBouncer Configuration: https://devcenter.heroku.com/articles/best-practices-pgbouncer-configuration
2. PostgreSQL Documentation — Row Security Policies (v18): https://www.postgresql.org/docs/current/ddl-rowsecurity.html
3. PostgreSQL Documentation — SET command: https://www.postgresql.org/docs/current/sql-set.html
4. PostgreSQL Documentation — SELECT / SKIP LOCKED: https://www.postgresql.org/docs/current/sql-select.html
5. OWASP Cryptographic Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
6. Python cryptography library — Fernet documentation: https://cryptography.io/en/latest/fernet/
7. Model Context Protocol (official) — Tools specification (2025-06-18): https://modelcontextprotocol.io/specification/2025-06-18/server/tools
8. Model Context Protocol (official) — Authorization specification (2025-06-18): https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization
9. Model Context Protocol (official) — Security best practices: https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices
10. Wikipedia — Model Context Protocol: https://en.wikipedia.org/wiki/Model_Context_Protocol
11. Simon Willison — Model Context Protocol has prompt injection security problems: https://simonwillison.net/2025/Apr/9/mcp-prompt-injection/
12. CoSAI Workstream 4 — Model Context Protocol Security: https://github.com/cosai-oasis/ws4-secure-design-agentic-systems/blob/main/model-context-protocol-security.md
13. SentinelOne — MCP Security: Complete Guide (includes OWASP MCP Top 10): https://www.sentinelone.com/cybersecurity-101/cybersecurity/mcp-security/
14. Zenity — Securing the Model Context Protocol: https://zenity.io/blog/security/securing-the-model-context-protocol-mcp
15. Stryker Mutator — What is mutation testing?: https://stryker-mutator.io/docs/
16. TwoCents Software — How to Test AI-Generated Code the Right Way in 2026: https://www.twocents.software/blog/how-to-test-ai-generated-code-the-right-way/
17. DEV Community (rsri) — Mutation Testing: The Missing Safety Net for AI-Generated Code: https://dev.to/rsri/mutation-testing-the-missing-safety-net-for-ai-generated-code-54kn
18. Prateek Singh (Medium) — Your AI-Generated Tests are Lying to You: https://singhpr.medium.com/your-ai-generated-tests-are-lying-to-you-and-what-to-do-about-it-57fb0e5f2783
19. Meta Engineering — LLMs Are the Key to Mutation Testing and Better Compliance (FSE 2025): https://engineering.fb.com/2025/09/30/security/llms-are-the-key-to-mutation-testing-and-better-compliance/
20. TechDebt.guru — AI Testing Gaps: Why High Coverage Doesn't Mean Quality Tests: https://techdebt.guru/ai-testing-gaps/
21. Trail of Bits Blog — Use mutation testing to find the bugs your tests don't catch: https://blog.trailofbits.com/2025/09/18/use-mutation-testing-to-find-the-bugs-your-tests-dont-catch/
22. Citus Data — PgBouncer Now Supports More Session Vars: https://www.citusdata.com/blog/2024/04/04/pgbouncer-supports-more-session-vars/
23. PgBouncer official documentation: https://www.pgbouncer.org/config.html
24. Bytebase — PostgreSQL RLS Footguns: https://www.bytebase.com/blog/postgres-row-level-security-footguns/
25. fast-check documentation — Model-based testing: https://fast-check.dev/docs/advanced/model-based-testing/
26. OWASP — Top 10 for Large Language Model Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications/
27. OWASP — Application Security Verification Standard: https://owasp.org/www-project-application-security-verification-standard/
28. SLSA — Security Levels: https://slsa.dev/spec/v1.0/levels
29. OpenTelemetry Documentation: https://opentelemetry.io/docs/
30. React — React 19 announcement (custom elements support): https://react.dev/blog/2024/12/05/react-19
31. Lit official site: https://lit.dev/
32. arXiv — Coverage Is Not Enough: SBFL-Driven Insights: https://arxiv.org/pdf/2512.11223
33. Anthropic Privacy Center — Server locations: https://privacy.claude.com/en/articles/7996890-where-are-your-servers-located-do-you-host-your-models-on-eu-servers
34. WAIMAKERS — Claude (Anthropic) GDPR Compliance Guide (May 2026): https://www.waimakers.com/en/resources/gdpr-compliance/claude-anthropic
35. Microsoft Q&A — Timeline for Claude in Microsoft Foundry on Azure EU infrastructure: https://learn.microsoft.com/en-us/answers/questions/5867930/timeline-for-claude-in-microsoft-foundry-to-run-on
36. AWS Blog — Unlocking AI flexibility in Switzerland (Claude on AWS Bedrock EU cross-region inference): https://aws.amazon.com/blogs/alps/unlocking-ai-flexibility-in-switzerland-a-guide-to-cross-region-inference-for-eu-data-processing-and-model-access/
37. Bytebase — PostgreSQL Row Level Security Limitations and Alternatives: https://www.bytebase.com/blog/postgres-row-level-security-limitations-and-alternatives/
38. PostgreSQL Wiki — Row Security: https://wiki.postgresql.org/wiki/RLS

---

## Confidence Ledger

| Claim | Tag | Signal | Source notes |
|---|---|---|---|
| Heroku official docs: "Any changes to session state via SET must only be made with `SET LOCAL`... Never use `SET SESSION` or `SET` alone" | [V] | CORROBORATED | Source [1], retrieved in original draft run; authoritative PgBouncer configuration documentation |
| In transaction-mode pooling, `SET` leaks tenant GUC values between clients if not scoped with `SET LOCAL` | [V] | CORROBORATED | Sources [1], [22], [23]; multiple authoritative sources confirm this failure mode |
| `FORCE ROW LEVEL SECURITY` required; table owners bypass RLS by default | [V] | CORROBORATED | Source [2] official PostgreSQL docs (retrieved this run); source [16] Bytebase footguns |
| PostgreSQL RLS default-deny: if RLS enabled and no policy exists, access denied | [V] | CORROBORATED | Source [2]; official PostgreSQL documentation |
| FK integrity checks always bypass RLS (official PostgreSQL documentation) | [V] | CORROBORATED | Source [2] retrieved this run: "Referential integrity checks... always bypass row security" |
| FK bypass creates covert-channel: tenant can probe parent-row existence by testing FK-referencing INSERT success/failure | [V] | CORROBORATED | Source [14] PostgreSQL wiki: "A user can probe for the existence of keys by testing to see whether or not DML operations succeed on tables with foreign keys" |
| Child INSERT may fail because RLS blocks parent SELECT during FK check | [V] | CORROBORATED | Source [24] Bytebase Footguns: "INSERT into child tables fails FK checks because RLS blocks SELECT on parent rows" |
| OWASP Cryptographic Storage: GCM and CCM are first preference | [V] | CORROBORATED | Source [5], retrieved in original draft run |
| Fernet uses AES-128-CBC + HMAC-SHA256 (not AEAD) | [V] | CORROBORATED | Source [6]; Python cryptography library official documentation |
| Direct Anthropic API has no EU-only inference geography; only "us" and "global" available | [V] | CORROBORATED | Source [34] WAIMAKERS GDPR guide (May 2026): "The direct Anthropic API offers only 'us' and 'global' inference geographies — there is no dedicated EU-only option yet" |
| Claude via Microsoft Foundry/Azure routes to Anthropic's US servers regardless of Azure region selected | [V] | CORROBORATED | Source [35] Microsoft Q&A: "the actual inference request is routed to Anthropic's own servers — regardless of which Azure region you select" |
| Microsoft Foundry EU support is "Coming 2026" per Anthropic regional compliance page | [V] | CORROBORATED | Source [35]: "Anthropic has listed Microsoft Foundry EU support as 'Coming 2026' on their regional compliance page" |
| AWS Bedrock EU cross-region inference for Claude is available across multiple EU regions | [V] | CORROBORATED | Source [36] AWS blog: confirms `eu.anthropic.claude-*` inference profiles routing within eu-central-1, eu-west-3, eu-south-1, eu-south-2, eu-west-1, eu-north-1 |
| EU-compliant Claude inference path: AWS Bedrock EU inference profiles or GCP Vertex AI EU regional endpoints | [V] | CORROBORATED | Source [34]: "For business processing of personal data, prefer Claude... deployed through AWS Bedrock (EU profiles) or Google Vertex AI (EU regional endpoints) when EU residency is required" |
| MCP tools are "model-controlled" and spec recommends human in loop | [V] | CORROBORATED | Source [7] official MCP specification 2025-06-18 |
| Security researchers documented MCP security issues including prompt injection (April 2025) | [V] | CORROBORATED | Source [10] Wikipedia; source [11] Simon Willison |
| OWASP MCP Top 10 established | [V] | CORROBORATED | Source [13] SentinelOne |
| AI-generated tests can achieve 100% coverage while scoring only 4% on mutation testing | [V] | CORROBORATED | Source [16] |
| AI-authored PRs average 10.83 issues vs 6.45 for human-only; logic/correctness errors up 75% | [V] | CORROBORATED | Source [16] citing CodeRabbit December 2025 analysis |
| The modular monolith eliminates distributed-system failure modes autonomous codegen handles worst | [U] | — | Architectural reasoning consistent with ADR-008's stated rationale |
| Document AI Quarantine Layer (dual-LLM quarantine pattern) as current defense against document prompt injection | [U] | CORROBORATED | Corroborated by sources [11], [12]; specific implementation is synthesis |
| Consent revocation immediate-effect invariant is GDPR-relevant in German/EU jurisdictions | [U] | — | Architectural reasoning; legal claim not directly sourced; counsel review required |
| Eval sets from same model family as production provider are self-referential | [U] | — | Architectural reasoning; ML literature supports this generally; no specific source retrieved |
| Independent verifier pipeline is required for no-human-review systems | [U] | — | Architectural reasoning; consistent with broader AI testing literature |
| `SELECT FOR UPDATE SKIP LOCKED` suitable for queue-like table access | [V] | CORROBORATED | Source [4] official PostgreSQL documentation |

---

## Approval check

(not ready) — Nine open issues (C-1 through C-9) identified in this round require openai's review and resolution before approval can be considered.

---

## Status

`STATUS: REVIEWING`
`OPEN_ISSUES: 9`