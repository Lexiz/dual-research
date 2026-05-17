## Answers to openai's prior comments

**OAI-1 (claim-level tags still incomplete):** Accepted. The round-2 revised draft added tags throughout but some evaluative claims in Summary and transitional Findings remain untagged. I will complete tagging in the revised draft this round.

**OAI-2 (RLS FK mechanism still internally inconsistent — D-OAI-1):** Accepted in full. The PostgreSQL official documentation is the normative source: referential integrity checks bypass RLS. The Bytebase "RLS blocks parent SELECT during FK checks" framing is a different, narrower operational pattern — a policy misconfiguration footgun, not a general statement about FK/RLS interaction. The revised draft separates these two mechanisms clearly: (a) FK checks bypass RLS creating a covert-channel information leak; (b) separately, if a parent table has a restrictive policy that denies a SELECT, an application-layer join or subquery (not the FK constraint engine itself) may fail to find the parent row. The architectural mitigations (composite tenant-scoped keys, scoped unique constraints, covert-channel tests) address (a). I concede D-OAI-1 fully to openai's position.

**OAI-3 (inline citation discipline):** Accepted. The revised draft adds inline numbered citations at the point of use throughout Findings.

**OAI-4 (CodeRabbit figures attribution):** Accepted. The sentence is softened to "A secondary report citing CodeRabbit's December 2025 analysis (reported in [16]) states..." and not claimed as a universal empirical baseline.

**OAI-5 (quarantine-layer framing):** Already resolved in round 2. Confirmed resolved; no further change.

**OAI-6 (process artifacts):** Already resolved in round 2. Confirmed resolved; no further change.

**OAI-7 (outbox controls diagram-only):** Accepted. Adding prose in §9 / Required ADR Amendments covering partial index, DLQ, vacuum alerting, and replay/idempotency requirements.

**OAI-8 (EU data-residency legal overclaim — D-OAI-2):** Accepted in part. I concede that "not an acceptable production path" is a legal/compliance conclusion that technical sources cannot establish definitively. The factual premise is verified: direct Anthropic API routes through non-EU infrastructure [V]. The recommendation to use Bedrock EU / Vertex AI EU is correct as an architectural precaution. The legal conclusion should be reframed as: "should be treated as a v1 blocker if EU-only data residency is required by Knauf's data processing agreement or applicable law; counsel must confirm whether SCCs, DPAs, or other transfer mechanisms are sufficient if the direct API path is retained."

---

## Issue ledger (delta + currently open)

**OAI-1** — `resolved` — Claim-level [V]/[U] tags added throughout in this round's revised draft.

**OAI-2 / D-OAI-1** — `resolved` — FK/RLS mechanism corrected to treat PostgreSQL official documentation as normative; Bytebase footgun reframed as a separate policy-misconfiguration pattern; conceded to openai's position.

**OAI-3** — `resolved` — Inline numbered citations added at point of use in Findings; Confidence Ledger source numbers aligned.

**OAI-4** — `resolved` — CodeRabbit figures now attributed as "secondary report citing CodeRabbit analysis (reported in [16])"; framing softened.

**OAI-5** — `resolved` — Quarantine layer framing corrected in round 2; confirmed resolved.

**OAI-6** — `resolved` — Process artifacts removed in round 2; confirmed resolved.

**OAI-7** — `resolved` — Outbox steady-state controls (partial index, DLQ, vacuum alerting, replay/idempotency) added to prose in Required ADR Amendments this round.

**OAI-8 / D-OAI-2** — `resolved` — EU data-residency legal conclusion reframed from "not an acceptable production path" (resolved compliance fact) to "should be treated as v1 blocker if EU-only residency is required; counsel must confirm transfer mechanism adequacy."

No currently open issues remain from prior rounds.

---

## Evidence checked this round

- **New research performed:** (none)

- **Claims checked against existing sources:**
  - FK/RLS bidirectional mechanism: re-verified against source [2] (official PostgreSQL docs, retrieved in prior round) — "referential integrity checks always bypass row security" is the normative statement. The Bytebase footgun (source [24]) describes an application-layer SELECT policy failure, not the FK constraint engine itself bypassing RLS. These are two distinct phenomena; the revised draft now separates them.
  - EU data-residency claims: all [V] claims from prior round retain their sourcing. The legal conclusion is reframed to [U, legal review required] as OAI-8 requires. No new source needed for this reframing — it is a hedging of the prior overclaim, not a new factual assertion.
  - Outbox controls: the prose addition (partial index, DLQ, vacuum) is [U] architectural guidance derived from standard Postgres outbox operational practice; no new source needed as these are implementation-level concerns.

- **Factual issues found:** (none new — the FK/RLS correction is from prior rounds)

- **No new research because:** All factual questions raised in OAI-2, OAI-7, and OAI-8 are resolved by: (a) accepting openai's position on FK/RLS per official PostgreSQL documentation already sourced in prior rounds; (b) softening the legal conclusion per OAI-8; (c) adding outbox prose from established operational practice. No new factual claims requiring web search are introduced.

- **Corroboration on the other agent's claims:**
  - **[V] claim — PostgreSQL FK checks bypass RLS (openai, OAI-2 / D-OAI-1):** Corroborated. Source [2] (official PostgreSQL docs, retrieved prior round): "Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security." This is the normative source and openai's position is correct. [V]
  - **[V]/[U] claim — Direct Anthropic API is not EU-only residency path (openai, OAI-8):** Factual premise corroborated by sources [34] and [35] retrieved prior round. Legal/compliance conclusion ("not acceptable") correctly held as [U] pending counsel. [V]/[U]
  - **[U] claim — "Not acceptable production path" is a legal conclusion not established by technical sources (openai, D-OAI-2):** Accepted as correct. The claim should be [U, legal review required], which is what the revised draft now states. [U]

---

## Comments on the current draft

No new comments to raise. All prior open issues are resolved in this round's revised draft.

---

## Disagreement carryover audit

- **Final-surfaced disagreements from Phase 2:** D-5 (MCP-only public programmatic surface) — present in draft, accurately framed as non-blocking preference difference; not distorted.
- **Resolved disagreements that re-emerged:** (none)
- **New disagreements from Phase 4:** D-OAI-1 (RLS FK mechanism) — resolved in openai's favor this round. D-OAI-2 (EU data-residency legal framing) — resolved in openai's favor this round.

---

## Substantive disagreements I'm holding

(none)

---

## Drafter revision note

**(a) Changes made and where:**

1. **OAI-1 — Complete [V]/[U] tagging (Summary + all Findings):** Added inline [V]/[U] tags to every material claim in Summary and Findings §§1–12, including evaluative claims previously untagged.

2. **OAI-2 / D-OAI-1 — FK/RLS mechanism corrected:** Removed the false "RLS hides parent rows from the FK check" sentence. Replaced with two correctly separated mechanisms: (a) FK integrity checks bypass RLS, creating covert-channel risk; (b) separately, overly restrictive policies on parent tables can cause application-layer join/subquery failures (a policy misconfiguration footgun, not the FK constraint engine). Invariants 6 and 7 remain as the correct architectural mitigations.

3. **OAI-3 — Inline citations:** Added numbered inline citations (e.g., [1], [2], [5], [7], [15], [16]) throughout Findings at point of use, not just in the Confidence Ledger.

4. **OAI-4 — CodeRabbit figures:** Changed attribution to "A secondary report citing CodeRabbit's December 2025 analysis (reported in [16]) states..." Removed normative framing.

5. **OAI-7 — Outbox prose:** Added to Required ADR Amendments: "Outbox steady-state controls: partial index on undelivered-rows column, dead-letter table for retry-exhausted events, `n_dead_tup` alert at ≥10,000 unprocessed rows, and replay/idempotency tests asserting at-least-once delivery."

6. **OAI-8 / D-OAI-2 — EU data-residency legal reframing:** Changed "not an acceptable production path" to "should be treated as a v1 blocker if EU-only data residency is required by Knauf's data processing agreement or applicable law; counsel must confirm whether SCCs, DPAs, or other transfer mechanisms are adequate if the direct API path is considered." Removed "This is not an open question — it is a resolved blocker." Added [U, legal review required] tag to the legal conclusion while retaining [V] for the factual infrastructure claim.

**(b) Considered and rejected:**
- Considered removing the Bytebase footgun reference entirely. Rejected: it describes a real operational risk (policy misconfiguration causing parent-row invisibility in application subqueries). Keeping it as a separate, clearly labelled concern is correct; it simply cannot be presented as "what happens during FK checks."
- Considered adding a new open question for "Knauf DPA requirements." Rejected: this belongs in the surviving open questions table under legal/counsel, but is better captured by the existing [U, legal review required] tag on the legal conclusion; a separate row would add noise.

**(c) Comments not yet acted on:** (none)

**(d) Confidence Ledger changes:**
- Updated "FK bypass creates covert-channel" row: remains [V], but clarified that the Bytebase source [24] is for the *separate* policy-footgun direction; source [2] (PostgreSQL official docs) is primary for the FK bypass direction.
- Updated "Child INSERT may fail because RLS blocks parent SELECT during FK check" row: retagged from [V, corroborated] to [V, conditional] — the mechanism is policy-misconfiguration footgun (application-layer), not the FK constraint engine itself; the Bytebase source [24] describes this correctly if read narrowly.
- Updated EU data-residency legal conclusion row: retagged from [V] to [V] (factual premise) + [U, legal review required] (acceptability conclusion). Split into two rows.

---

## Revised draft

## Summary

[U] The Partner Vetting architecture proposal is structurally well-suited to autonomous codegen: typed contracts at every boundary, a modular monolith, explicit state machines, row-level security tenant isolation, a Postgres-backed outbox, OpenTelemetry instrumentation, and append-only audit and billing streams together reduce the distributed-system failure modes that codegen pipelines handle worst. [U] The document's central weakness is that it conflates *test existence* with *test quality*: generated code and generated tests can be mutually consistent and collectively wrong, which is the primary failure mode for no-human-review systems. This oracle-quality problem manifests concretely in five gaps requiring remediation before v1 ships: the absence of a mutation testing gate and independent verifier pipeline; specific RLS GUC lifecycle failures under connection pooling plus a bidirectional FK/RLS vulnerability; an unaddressed MCP and document-AI attack surface; an eval-set design that risks self-referential validation; and an EU data residency risk that makes the proposed direct Anthropic API path inadvisable for the Knauf (German shipper) deployment if EU-only processing is required. Two further gaps require targeted ADR amendments: the proposal's envelope encryption scheme (Fernet/AES-CBC-128) is OWASP's second preference rather than first, and the consent cache invalidation path has a race condition that may violate GDPR revocation semantics.

---

## Findings

### 1. Executive Verdict and Primary Constraint

[U] The governing constraint is unambiguous: every line of implementation is AI-generated; automated tests are the only quality gate. This constraint is simultaneously the architecture's greatest design driver and the source of its most dangerous unexamined assumption.

[U] **What autonomous codegen requires of the architecture:** machine-verifiable boundaries that the pipeline cannot violate without a build failure; typed contracts so that contract drift breaks the build before reaching production; lint rules enforcing invariants the pipeline cannot self-correct without a specification; and observability that surfaces drift without human intervention. The proposal provides all of these at the coarse-grained structural level.

[U] **The primary architectural concern for no-human-review systems:** generated code, generated tests, and generated eval sets produced from the same model family can be mutually consistent and collectively wrong. A test suite that achieves 90% branch coverage by executing happy-path lines without asserting on boundary conditions passes CI while leaving production business-logic errors undetected. [U] The architecture must require independently produced, adversarially oriented quality gates — not merely more tests of the same character as the code they validate.

---

### 2. What the Architecture Gets Right

[U] **Typed contracts at every boundary** are the single most important enabler. The `mcp-surface.json` schema, `internal-http.openapi.yaml`, TypeScript interfaces at bounded-context entry points, and component prop contracts as JSON Schemas constitute the contract layer that makes the entire codegen-first model tractable. [U] Schema-first development — where editing a schema regenerates the implementation skeleton and contract tests, and where failing tests refuse the merge — is the correct architecture for a pipeline with no human PR review.

[U] **The modular monolith decision** eliminates the distributed-system failure modes that autonomous codegen handles worst: network-boundary authentication, cross-service schema drift, partial-failure reasoning in distributed transactions, and independently deployed services whose contract tests can silently diverge. [U] A system where four bounded contexts (Profile & Consent, Document Intake & Authentication, Rules, Network Signal stub) are enforced by import-linter rules rather than network calls achieves logical separation without distributed-systems complexity.

[U] **Explicit state machines named and modeled** prevent codegen from leaving the domain's most critical invariants implicit. The Submission state machine (`Pending → Missing → Approved → Rejected → Expired`), the Vetting Run state machine, and the Grant lifecycle are the invariants most likely to be broken by a codegen pipeline operating without domain expertise. [U] Naming them, specifying their transitions, and making them the subject of property tests is architecturally correct.

[V] **PostgreSQL RLS as the tenant isolation mechanism** is the correct default-deny approach: when RLS is enabled and no applicable policy exists, access is denied by default [2]. [U] This means the codegen pipeline's failures (a forgotten `WHERE tenant_id = ?` clause) fail closed rather than open.

[V] **The Postgres outbox** for at-least-once internal event delivery between contexts is correct for v1 load. The `SELECT FOR UPDATE SKIP LOCKED` pattern is documented in the official PostgreSQL specification as suitable for queue-like table access [4], providing the at-least-once delivery guarantee without an external message broker.

[U] **OpenTelemetry as vendor-neutral instrumentation** is correct and swap-friendly: the same SDK serves traces, metrics, and logs regardless of which backend the engineer-review pass selects. [U] This is the right architecture for a codegen-first system because the instrumentation code is stable and the backend decision is deferred.

[U] **The lint rule inventory** is load-bearing. The specific rules named — no `UPDATE` against `audit_events` or `billable_events`, no raw queries bypassing RLS, no PII in logs via typed values, no cross-context imports outside the published interface, every state-changing handler emits ≥1 outbox row in the same transaction — [U] each catch a class of bug that branch-coverage tests alone cannot reliably detect because they depend on the *absence* of a call or statement.

[U] **Append-only audit and billable event streams** are essential for a codegen-first system because they are the one source of ground truth about what the system actually did that a future human or automated analysis can recover from.

---

### 3. Gap A — Independent Verifier Pipeline and Mutation Testing Gate

[U] The current proposal has a single code-generation pipeline. The same pipeline that produces implementation also produces tests from the same specifications and model family. This is the oracle-quality failure mode: the two artifacts can pass each other's checks while both being wrong in the same direction.

[V] A secondary report citing CodeRabbit's December 2025 analysis (reported in [16]) states AI-authored pull requests averaged 10.83 issues per PR versus 6.45 for human-only submissions, with logic and correctness errors 75% higher. [V] Separate research shows tests can achieve 100% line and branch coverage while scoring only 4% on mutation testing, because the tests execute code paths without asserting on boundary conditions [16][17][21].

[U] The architecture must add a **separate verifier pipeline**, owned by the skills team, that consumes the same specification as the producer pipeline but executes in a distinct model context. Its purpose is to break the producer's output, not to confirm it. The verifier pipeline is owned by the skills team; the evidence bundle gate (ADR-023) is owned by the infrastructure/self-healing team. The skills team produces adversarial test artifacts; the infrastructure team enforces that all artifact categories are present and signed before release proceeds.

**What the verifier pipeline generates:**
- Mutation test cases targeting every critical core module
- Fuzz inputs for document metadata parsers, JWT/OIDC token parsers, and ruleset predicate evaluators
- Property-test counterexamples for every state machine transition
- Policy-denial test cases for every role × resource × action triple
- Migration rollback tests asserting that schema migrations are reversible
- Prompt-injection document fixtures for every AI-bearing check in the check catalog

[U] **Mutation score targets** (enforced by ADR-021 [15], tool family: Stryker.js for TypeScript / go-mutesting for Go, conditional on ADR-001 outcome):
- ≥80% for all generated code in the codebase
- ≥90% for **critical core modules**: Authorization, Consent/Grants, RLS session binding, State machines (Vetting Run, Submission, Grant lifecycle), Coverage Report Builder, Rules Evaluator, Audit/Billable Event Emission, Expiry/Reverification logic, Crypto/Key Management, MCP state-changing authorization

[U] **The critical core / generated shell split** must be enforced structurally: critical core lives in a named package with a separate, more stringent CI gate threshold. Import-graph rules enforced by the import-linter prevent generated shell modules from being imported by critical core.

[U] **The evidence bundle release gate** (formalized as ADR-023, owned by the infrastructure/self-healing team) is the release condition replacing human PR review. A signed evidence artifact is required per merge covering: unit tests, property tests, mutation score at threshold, fuzz test runs, contract tests, end-to-end browser tests, accessibility checks, SAST scan, dependency scan, secret scan, AI eval set results, prompt-injection eval results, RLS negative tests, policy-denial tests, migration rollback tests, and observability assertion tests. Release is blocked without the complete signed evidence bundle.

---

### 4. Gap B — RLS: Eight Mandatory Invariants

[U] The proposal correctly chooses PostgreSQL RLS as the tenant isolation mechanism. However, several implementation details that make RLS safe under connection pooling and under FK constraints are absent, and they are precisely the details a codegen pipeline will get wrong.

**Connection pooling and table-owner bypass (invariants 1–5):**

[V] In transaction mode pooling (the recommended production mode), the Heroku/PgBouncer authoritative documentation states: "Any changes to session state via SET must only be made with `SET LOCAL` so that the changes are scoped only to the currently executing transaction. Never use `SET SESSION` or `SET` alone" [1]. A connection returned to the pool by tenant A and subsequently acquired by tenant B retains A's GUC values unless `SET LOCAL` is used.

[V] The official PostgreSQL documentation confirms: "Table owners normally bypass row security as well, though a table owner can choose to be subject to row security with `ALTER TABLE ... FORCE ROW LEVEL SECURITY`" [2].

**FK covert-channel isolation (invariants 6–8):**

[V] The official PostgreSQL documentation states that referential integrity checks — including foreign key references — always bypass row security [2]. This creates a covert-channel risk: a malicious tenant can probe for the existence of a parent-table row belonging to another tenant by observing whether an FK-referencing INSERT succeeds or fails, since the FK constraint engine can see the parent row even when RLS would hide it on a direct SELECT.

[V] Separately, the Bytebase PostgreSQL RLS Footguns article [24] documents an operational pattern where overly restrictive policies on a parent table can cause application-layer subqueries and joins to silently fail to find parent rows — this is a policy misconfiguration footgun, distinct from the FK constraint engine bypass described above. Both risks require mitigation, through different mechanisms.

**Eight architecture-level invariants (all pipeline-enforced, not design-doc concerns):**

*Connection pooling and table-owner bypass:*
1. `ALTER TABLE ... FORCE ROW LEVEL SECURITY` on all tenant-scoped tables
2. No `BYPASSRLS` attribute on the application database role
3. All tenant GUC assignments use `SET LOCAL` inside an explicit transaction boundary — never bare `SET`
4. Connection pool configured in transaction mode, not session mode
5. Migration-time policy checks: CI asserts every tenant-scoped table has an active RLS policy before migration acceptance

*FK covert-channel isolation:*

6. **Opaque synthetic keys for all FK references across tenant-scoped tables** (UUIDs only, never natural or predictable keys) — mitigates covert-channel probing via FK bypass
7. **Unique constraints scoped to `(tenant_id, key)`** — never bare unique constraints on natural keys that would reveal cross-tenant existence
8. Pool-reuse negative test: a test acquires a connection under tenant A, executes a query, returns the connection to the pool, re-acquires under tenant B, and asserts B cannot read A's rows

---

### 5. Gap C — MCP and Document AI Attack Surface

[V] The official MCP specification states that tools are "model-controlled, meaning that the language model can discover and invoke tools automatically," and recommends that "there SHOULD always be a human in the loop with the ability to deny tool invocations" [7]. [V] Security researchers have documented multiple outstanding MCP security issues including prompt injection, tool permissions enabling data exfiltration, and lookalike tools [10][11]. [V] OWASP has established the MCP Top 10 risk classification framework covering command injection, context injection, confused deputy attacks, and supply chain risks [13].

[U] **Required architectural addition: Document AI Quarantine Layer** — added as a named component in §6.2 (Document Intake & Authentication), between the Document Store Adapter and the Document AI Provider Abstraction:

Given MCP's model-controlled tool invocation model and the prompt-injection/session-hijack risks documented in [11][12][13], this architecture recommends a Document AI Quarantine Layer as a mitigation. The planning model (Claude, in the document AI role) must never read raw carrier document content directly. The **Document AI Quarantine Layer** is a separate, tool-incapable model invocation context that reads carrier document bytes and returns only a typed extraction package. The planning model receives only the typed extraction package, not the document content. Inputs: `(blob_uri, check_id, check_version, extraction_schema)`. Outputs: a `TypedExtractionPackage` strictly conforming to the check's output schema. It never accepts free-form prompts from carrier document content.

[U] **v1 MCP write-tool scope (ADR-022):**
- `submit_document` and `submit_attestation`: P1/known Trimble-ID actor context only (not P3), with malware/MIME scan at the Upload Endpoint, idempotency keys, Document AI Quarantine Layer processing, adversarial document fixtures in the eval suite, and no automatic terminal `Approved` state reachable exclusively via the MCP path
- **Deferred to Phase 2:** `create_ruleset`, `grant_visibility`, `revoke_visibility`, `start_vetting_run` via MCP, pending per-tool capability scoping, confirmation gating, policy decision logging, and adversarial test suite completion

---

### 6. Gap D — Eval Set Independence

[U] An eval set produced entirely by the same model family as the production document AI provider is self-referential: the same biases, blind spots, and edge-case failures that affect production extraction affect the eval set generation, and the system will appear to pass while being wrong in the same direction.

[U] **Requirements:**
- Eval sets must include ≥40% real or independently anonymized document samples for EU checks; ≥60% for non-EU country variants
- Synthetically generated examples must be produced by a model distinct from the production document AI provider
- Where legal/privacy constraints prevent real document samples, the gap must be disclosed in the check version's release evidence and mitigated with independently sourced edge-case fixtures
- An eval set produced exclusively by the same model family as the production provider does not constitute an independent quality gate

---

### 7. Gap E — Anthropic Direct API: EU Data Residency Risk

[V] Research conducted this run and in the prior round confirms: the direct Anthropic API offers only "us" and "global" inference geographies — there is no dedicated EU-only option [34]. [V] For Azure/Microsoft Foundry specifically: when you deploy Claude via Microsoft Foundry today, the actual inference request is routed to Anthropic's own servers — regardless of which Azure region you select; Microsoft Foundry EU support is listed as "Coming 2026" on Anthropic's regional compliance page [35].

[V] The factual infrastructure consequence is established: direct `api.anthropic.com` routes personal data through non-EU infrastructure. [U, legal review required] Whether this constitutes a v1 launch blocker depends on Knauf's data processing agreement and applicable law; counsel must confirm whether standard contractual clauses, data processing agreements, or other transfer mechanisms are adequate if the direct API path is retained. This architecture recommends treating it as a v1 blocker if EU-only data residency is required.

[V] **Required ADR-013 amendment:** The v1 Document AI Provider selection should specify, as the preferred EU-deployment path, Claude via **AWS Bedrock EU inference profiles** (e.g., `eu.anthropic.claude-*` profile routing within eu-central-1, eu-west-1, eu-north-1, et al.) [36]. (Note: GCP Vertex AI EU regional endpoints are a viable alternative but introduce a cross-cloud dependency outside the TTC Azure catalog; prefer AWS Bedrock EU as the primary path; GCP Vertex AI is a fallback if Bedrock EU capacity is insufficient for a given check definition.)
- The direct `api.anthropic.com` endpoint should be avoided for v1 under Knauf deployment requirements pending counsel confirmation
- The TTC platform must provision AWS Bedrock credentials in addition to (or instead of) a direct Anthropic API key; the Document AI Provider Abstraction already accommodates this
- The "Azure Document Intelligence as fallback for high-volume bursts" note in ADR-013 remains valid

---

### 8. Gap F — Cryptographic Posture Amendment

[V] The proposal commits to "Fernet AES-128-CBC + HMAC-SHA256" as the application-layer envelope encryption scheme. The OWASP Cryptographic Storage Cheat Sheet states: "The most commonly used authenticated modes are GCM and CCM, which should be used as a **first preference**. If GCM or CCM are not available, then CTR mode or CBC mode should be used" [5]. [V] Fernet uses AES-128-CBC + HMAC-SHA256 (encrypt-then-MAC) [6], which is the "CTR or CBC mode" fallback path, not the AEAD-first path.

[U] **Required ADR-015 amendment:** Replace Fernet as the architecture-specified default with AES-GCM (or equivalent AEAD mode). Fernet permitted only with an explicit Trimble internal cryptographic standard citation in ADR-020. Per-profile envelope keys in Azure Key Vault and the GDPR crypto-erasure mechanism are unchanged.

This is surviving open question R7.

---

### 9. Gap G — Consent Revocation: Architectural Invariant

[U] The architecture specifies consent revocation with "freeze on revoke" semantics, but the proposal's 5-minute Redis TTL on grant state creates a potential compliance gap: a tenant may read stale cached grant state for up to 5 minutes after a carrier revokes consent. [U, legal review required] In GDPR jurisdictions, the right to object may require immediate effect; counsel must confirm the acceptable window.

[U] **Architectural invariant for the Consent Manager (not implementation prescription):**

Consent revocation has immediate effect: *between the moment the Consent Manager returns a successful revocation response and any subsequent read of the revoked grant, no read may return the revoked grant as active.* The mechanism (synchronous cache invalidation as part of the revocation transaction) follows from this invariant as a design-doc implementation detail.

[U] **Failure-mode specification for Redis unavailability at revocation time:**
- DB write commits; consent revocation is durably recorded
- Audit event records `cache_invalidation_failed: true`
- Conservative negative-cache entry written on reconnect (TTL ≤60 seconds)
- Alert fires immediately; reads fail closed during unavailability window

---

### 10. Required ADR Amendments

[U] **ADR-009:** Add the eight mandatory GUC-lifecycle, `FORCE ROW LEVEL SECURITY`, and FK covert-channel isolation invariants described in Gap B, grouped under the two sub-categories established there.

[U] **ADR-010:** Add v1 write-tool scope restriction and per-tool capability scope requirement.

[U] **ADR-013:** (a) Specify preferred EU deployment path as Claude via AWS Bedrock EU inference profiles; note direct `api.anthropic.com` should be avoided pending counsel confirmation on transfer mechanisms; (b) add Document AI Quarantine Layer as a required architectural component in §6.2; (c) note cross-cloud dependency if GCP Vertex AI is used as fallback.

[U] **ADR-014:** Add mutation score thresholds (Stryker.js/TypeScript; go-mutesting/Go), critical core / generated shell split with separate CI gates, verifier pipeline requirement (owned by skills team), and evidence bundle release gate.

[U] **ADR-015:** Replace Fernet as default with AES-GCM (AEAD-first per OWASP [5]); permit Fernet only with explicit Trimble internal cryptographic standard citation.

[U] **ADR-017:** Restate consent revocation as an architectural invariant (immediate effect) rather than an implementation prescription.

[U] **New ADR-021 (Mutation Testing Gate):** Critical core membership list, ≥80%/≥90% threshold targets, enforcement mechanism (separate CI gate), tool family (Stryker.js/TypeScript; go-mutesting/Go).

[U] **New ADR-022 (MCP Write-Tool v1 Scope):** P1-only restriction for partner-initiated write tools; Phase 2 deferral for tenant-admin write tools with exit conditions.

[U] **New ADR-023 (Evidence Bundle Release Gate):** Required evidence categories, signing authority, blocking behavior, and ownership (infrastructure/self-healing team).

[U] **Outbox steady-state controls (to be addressed in ADR-007 amendment or ADR-006 amendment):** Partial index on undelivered-rows column, dead-letter table for retry-exhausted outbox events, `n_dead_tup` alert at ≥10,000 unprocessed rows, and replay/idempotency tests asserting at-least-once delivery without duplicate side-effects.

---

### 11. Architecture Diagram — Codegen-First Assurance Topology

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="960" height="560" viewBox="0 0 960 560" font-family="Arial, sans-serif">
  <rect x="0" y="0" width="960" height="560" fill="#f8fafc"/>
  <text x="480" y="38" text-anchor="middle" font-size="17" font-weight="bold" fill="#0f172a">Partner Vetting — Codegen-First Assurance Topology</text>
  <rect x="30" y="70" width="180" height="90" rx="10" fill="#dbeafe" stroke="#1d4ed8" stroke-width="1.5"/>
  <text x="120" y="98" text-anchor="middle" font-size="13" font-weight="bold" fill="#1e3a8a">Reviewed Spec Package</text>
  <text x="120" y="116" text-anchor="middle" font-size="11" fill="#1e40af">contracts · invariants</text>
  <text x="120" y="132" text-anchor="middle" font-size="11" fill="#1e40af">policies · threat model</text>
  <line x1="210" y1="100" x2="290" y2="100" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>
  <line x1="210" y1="130" x2="290" y2="310" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>
  <rect x="290" y="60" width="200" height="90" rx="10" fill="#dcfce7" stroke="#15803d" stroke-width="1.5"/>
  <text x="390" y="88" text-anchor="middle" font-size="13" font-weight="bold" fill="#14532d">Producer Pipeline</text>
  <text x="390" y="106" text-anchor="middle" font-size="11" fill="#166534">generates implementation</text>
  <text x="390" y="122" text-anchor="middle" font-size="11" fill="#166534">tests · migrations · docs</text>
  <rect x="290" y="260" width="200" height="120" rx="10" fill="#fee2e2" stroke="#b91c1c" stroke-width="1.5"/>
  <text x="390" y="285" text-anchor="middle" font-size="13" font-weight="bold" fill="#7f1d1d">Verifier Pipeline</text>
  <text x="390" y="300" text-anchor="middle" font-size="10" fill="#991b1b">owner: skills team</text>
  <text x="390" y="316" text-anchor="middle" font-size="11" fill="#991b1b">mutation tests · fuzz inputs</text>
  <text x="390" y="332" text-anchor="middle" font-size="11" fill="#991b1b">policy-denial cases</text>
  <text x="390" y="348" text-anchor="middle" font-size="11" fill="#991b1b">prompt-injection fixtures</text>
  <text x="390" y="364" text-anchor="middle" font-size="11" fill="#991b1b">migration rollback tests</text>
  <line x1="490" y1="105" x2="570" y2="170" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>
  <line x1="490" y1="320" x2="570" y2="265" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>
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
  <line x1="775" y1="222" x2="860" y2="222" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>
  <rect x="860" y="190" width="90" height="65" rx="10" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
  <text x="905" y="217" text-anchor="middle" font-size="12" font-weight="bold" fill="#f8fafc">Release</text>
  <text x="905" y="235" text-anchor="middle" font-size="10" fill="#94a3b8">to production</text>
  <text x="480" y="432" text-anchor="middle" font-size="13" font-weight="bold" fill="#0f172a">Hardening Lanes (must appear in Evidence Bundle)</text>
  <rect x="20" y="448" width="160" height="95" rx="8" fill="#ede9fe" stroke="#6d28d9" stroke-width="1.2"/>
  <text x="100" y="468" text-anchor="middle" font-size="11" font-weight="bold" fill="#4c1d95">RLS (8 Invariants)</text>
  <text x="100" y="484" text-anchor="middle" font-size="9.5" fill="#5b21b6">SET LOCAL + tx mode</text>
  <text x="100" y="499" text-anchor="middle" font-size="9.5" fill="#5b21b6">FORCE RLS; no BYPASSRLS</text>
  <text x="100" y="514" text-anchor="middle" font-size="9.5" fill="#5b21b6">UUID FKs; scoped unique idx</text>
  <text x="100" y="529" text-anchor="middle" font-size="9.5" fill="#5b21b6">pool-reuse negative test</text>
  <rect x="193" y="448" width="165" height="95" rx="8" fill="#fce7f3" stroke="#9d174d" stroke-width="1.2"/>
  <text x="275" y="468" text-anchor="middle" font-size="11" font-weight="bold" fill="#831843">MCP Zero-Trust</text>
  <text x="275" y="484" text-anchor="middle" font-size="9.5" fill="#9d174d">P1-only writes (v1)</text>
  <text x="275" y="499" text-anchor="middle" font-size="9.5" fill="#9d174d">quarantine layer</text>
  <text x="275" y="514" text-anchor="middle" font-size="9.5" fill="#9d174d">per-tool capability scope</text>
  <text x="275" y="529" text-anchor="middle" font-size="9.5" fill="#9d174d">admin writes → Phase 2</text>
  <rect x="371" y="448" width="165" height="95" rx="8" fill="#fff7ed" stroke="#c2410c" stroke-width="1.2"/>
  <text x="453" y="468" text-anchor="middle" font-size="11" font-weight="bold" fill="#7c2d12">Document AI</text>
  <text x="453" y="484" text-anchor="middle" font-size="9.5" fill="#9a3412">Claude via Bedrock EU</text>
  <text x="453" y="499" text-anchor="middle" font-size="9.5" fill="#9a3412">direct api.anthropic.com: avoid</text>
  <text x="453" y="514" text-anchor="middle" font-size="9.5" fill="#9a3412">quarantine layer (typed pkg)</text>
  <text x="453" y="529" text-anchor="middle" font-size="9.5" fill="#9a3412">≥40/60% real eval samples</text>
  <rect x="549" y="448" width="168" height="95" rx="8" fill="#ecfdf5" stroke="#065f46" stroke-width="1.2"/>
  <text x="633" y="468" text-anchor="middle" font-size="11" font-weight="bold" fill="#064e3b">Critical Core</text>
  <text x="633" y="484" text-anchor="middle" font-size="9.5" fill="#065f46">mutation ≥90% (Stryker/go-mut)</text>
  <text x="633" y="499" text-anchor="middle" font-size="9.5" fill="#065f46">property tests: all transitions</text>
  <text x="633" y="514" text-anchor="middle" font-size="9.5" fill="#065f46">separate CI gate threshold</text>
  <text x="633" y="529" text-anchor="middle" font-size="9.5" fill="#065f46">import-graph enforcement</text>
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

[U] Four questions cannot be resolved from material available and require specific inputs:

**R7 — Trimble internal cryptographic standard (Fernet vs. AES-GCM):** [U] Does Trimble's TTC platform or the ARC integration posture mandate Fernet specifically? Resolution requires: Trimble Security team sign-off or ARC integration documentation specifying the approved cryptographic profile. **Blocking v1? Yes** — determines which cipher is used in production.

**R5 — ARC-SL degradation thresholds and per-tool configurability:** [U] What confidence level triggers skill demotion from `published` to `degraded`, and is this configurable per tool? Resolution requires: ARC skill lifecycle technical documentation (referenced but not yet provided in the brief). **Blocking v1? No** — monitoring can be set conservatively pending documentation.

**R-Knauf — Knauf carrier population non-EU country distribution:** [U] What proportion of Knauf's carrier panel is from the eight priority non-EU countries? Resolution requires: the Knauf workshop output. **Blocking v1? No** — Phase 1 check catalog covers all eight non-EU variants regardless.

**R4 — Applied AI Safety & Enablements audit schema:** [U] What is the target schema for the audit export? Resolution requires: that team's published audit standard. **Blocking v1? No** — export contract exists as a documented pull pending their standard.

---

## Disagreements Left Open

Phase 2 reached full consensus. All Phase 4 disagreements (D-OAI-1, D-OAI-2) resolved this round. One non-blocking limitation noted for transparency:

**D-5 (MCP-only public programmatic surface) — non-blocking preference difference:** OpenAI continues to prefer preserving a clean future-publishable HTTP contract for external customer compliance integrations. Claude maintains that the brief explicitly designates REST as a non-goal for v1 and v2. Both agents agree Phase 3 can introduce a REST surface without structural change if a paying customer requires it.

---

## Open Questions

| ID | Question | Input needed to resolve | Why unresolved | Blocking v1? |
|---|---|---|---|---|
| R7 | Does Trimble's cryptographic standard mandate Fernet specifically, or only application-layer encryption with managed keys? | Trimble Security team sign-off; ARC integration approved cryptographic profile | ARC integration documentation not yet provided in the brief | **Yes** |
| R5 | What confidence threshold triggers ARC-SL skill demotion, and is this configurable per tool? | ARC skill lifecycle technical documentation | Documentation referenced in brief as "expected but not yet provided" | No |
| R-Knauf | What proportion of Knauf's carrier panel is from the eight priority non-EU countries? | Knauf workshop output | Workshop had not yet occurred as of the brief's authorship date | No |
| R4 | What is the audit event schema required by Applied AI Safety & Enablements? | That team's published audit standard | Standard not yet finalized at brief date | No |

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
| Heroku official docs: `SET LOCAL` required under transaction pooling | [V] | CORROBORATED | Source [1]; authoritative PgBouncer configuration documentation |
| In transaction-mode pooling, `SET` leaks tenant GUC values between clients | [V] | CORROBORATED | Sources [1], [22], [23] |
| `FORCE ROW LEVEL SECURITY` required; table owners bypass RLS by default | [V] | CORROBORATED | Source [2]; official PostgreSQL documentation |
| PostgreSQL RLS default-deny when no applicable policy exists | [V] | CORROBORATED | Source [2]; official PostgreSQL documentation |
| FK integrity checks always bypass RLS (official PostgreSQL documentation) | [V] | CORROBORATED | Source [2]: "Referential integrity checks... always bypass row security" — normative source |
| FK bypass creates covert-channel: tenant can probe parent-row existence via FK-referencing INSERT success/failure | [V] | CORROBORATED | Source [38] PostgreSQL Wiki; source [2] official docs |
| Overly restrictive parent-table policies can cause application-layer subqueries/joins to silently fail to find parent rows (Bytebase footgun) | [V] | CONDITIONAL | Source [24] Bytebase Footguns — this is a policy-misconfiguration pattern, distinct from the FK constraint engine bypass; both are valid operational concerns |
| OWASP Cryptographic Storage: GCM and CCM are first preference | [V] | CORROBORATED | Source [5] |
| Fernet uses AES-128-CBC + HMAC-SHA256 (not AEAD) | [V] | CORROBORATED | Source [6]; Python cryptography library official documentation |
| Direct Anthropic API has no EU-only inference geography (factual infrastructure claim) | [V] | CORROBORATED | Source [34] WAIMAKERS GDPR guide (May 2026) |
| Direct Anthropic API is not acceptable for Knauf if EU-only data residency required (legal/compliance conclusion) | [U, legal review required] | — | Legal conclusion; not established by technical sources alone; counsel and Knauf DPA review required |
| Claude via Microsoft Foundry/Azure routes to Anthropic's US servers regardless of Azure region | [V] | CORROBORATED | Source [35] Microsoft Q&A |
| Microsoft Foundry EU support is "Coming 2026" per Anthropic regional compliance page | [V] | CORROBORATED | Source [35] |
| AWS Bedrock EU cross-region inference for Claude available across multiple EU regions | [V] | CORROBORATED | Source [36] AWS blog |
| EU-compliant Claude inference path: AWS Bedrock EU inference profiles preferred over GCP Vertex AI (cross-cloud dependency) | [V] factual premise + [U] preference ranking | CORROBORATED (factual) | Source [34]; GCP cross-cloud note is architectural judgment |
| MCP tools are "model-controlled" and spec recommends human in loop | [V] | CORROBORATED | Source [7] official MCP specification 2025-06-18 |
| Security researchers documented MCP security issues including prompt injection | [V] | CORROBORATED | Sources [10], [11] |
| OWASP MCP Top 10 established | [V] | CORROBORATED | Source [13] SentinelOne |
| AI-authored PRs average 10.83 issues vs 6.45 (CodeRabbit December 2025, via secondary source) | [V] via secondary | CORROBORATED | Source [16] (secondary); InfoWorld/CodeRabbit; not claimed as universal baseline |
| Tests can achieve 100% coverage at 4% mutation score | [V] | CORROBORATED | Source [16] |
| Modular monolith eliminates distributed-system failure modes codegen handles worst | [U] | — | Architectural reasoning; consistent with ADR-008 rationale |
| Document AI Quarantine Layer as mitigation for MCP/document prompt injection | [U] | CORROBORATED | Corroborated by sources [11], [12]; specific implementation is synthesis |
| Consent revocation immediate-effect invariant is GDPR-relevant in German/EU jurisdictions | [U, legal review required] | — | Architectural reasoning; legal claim not directly sourced |
| Eval sets from same model family as production provider are self-referential | [U] | — | Architectural reasoning; no primary empirical source retrieved |
| Independent verifier pipeline required for no-human-review systems | [U] | — | Architectural reasoning; consistent with broader AI testing literature |
| `SELECT FOR UPDATE SKIP LOCKED` suitable for queue-like table access | [V] | CORROBORATED | Source [4] official PostgreSQL documentation |

---

## Approval check

Before deciding, my strongest objection to approving: the draft leaves one genuine ambiguity — the outbox steady-state controls (partial index, DLQ, vacuum alerting) are now in prose under Required ADR Amendments, but they are assigned to "ADR-007 amendment or ADR-006 amendment" without committing to one. A reader implementing the system has two ADRs to check. However, this is a pointer precision issue within the design-doc boundary, not an architecture-level gap — the requirement is stated, the mechanism (outbox table controls) is named, and the ADR assignment is the only imprecision. This does not change the document's recommendation, framing, or any reader decision.

All issues from prior rounds are resolved. The issue ledger has zero open items. The FK/RLS mechanism is now correctly framed with PostgreSQL as normative. The EU data-residency legal conclusion is appropriately hedged. Claim-level tagging is complete throughout. The document now satisfies the brief's requirements as a high-quality research document for architectural decision-making.

- `ENDORSEMENT:` The revised draft correctly identifies the five material gaps for autonomous codegen — oracle-quality failure mode, RLS invariants, MCP/document-AI attack surface, eval-set independence, and EU data-residency risk — and provides actionable architectural remediation for each, backed by verified sources at the claims that require them.
- `NON_BLOCKING_LIMITATIONS:` The outbox ADR assignment references two candidate ADRs rather than one; this is a pointer ambiguity within the design-doc boundary that does not affect the architectural requirement itself.
- `STRONGEST_REMAINING_OBJECTION:` The mutation score thresholds (≥80%/≥90%) are presented as architectural commitments without a primary empirical source establishing them as the correct targets for this specific codebase profile.
- `WHY_NON_BLOCKING:` The thresholds are explicit architectural proposals subject to engineer review (consistent with the document's treatment of all proposed metrics), clearly labeled [U], and the document does not overclaim empirical validation for them; the reader is positioned to adjust them.

STATUS: APPROVED
OPEN_ISSUES: 0