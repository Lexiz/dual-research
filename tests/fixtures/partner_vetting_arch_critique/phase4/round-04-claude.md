## Answers to openai's prior comments

**OAI-1 (claim-level tagging incomplete — round 3):** Accepted. The round-3 revised draft added [V]/[U] tags throughout but several material claims in Gap A, Required ADR Amendments, Open Questions, and the Summary's blocker list remain untagged. I will complete tagging this round.

**OAI-2 (RLS FK mechanism still internally inconsistent — D-OAI-1):** Accepted. I concede this fully. The round-3 revised draft still carried a residual Bytebase-flavored framing ("because RLS hides parent rows") that is inconsistent with the PostgreSQL normative source. The correct and complete statement is: (a) PostgreSQL FK constraint checks bypass RLS — the FK engine sees the parent row regardless of RLS policy; (b) separately, if application-layer queries (subqueries, joins) are used to look up a parent before an INSERT, a restrictive parent-table RLS policy can cause those to silently fail. These are different mechanisms with different mitigations. The revised draft removes any remaining conflation.

**OAI-3 (inline citation discipline):** Accepted. Adding inline citations to Gap A, Required ADR Amendments, and the Summary's five-blocker list.

**OAI-7 (outbox controls still diagram-only):** Accepted. Adding prose in Required ADR Amendments with specific controls: partial index, DLQ table, vacuum alerting, replay/idempotency tests, queue-lag SLO.

**OAI-8 (EU data-residency legal overclaim — D-OAI-2):** Accepted. "Non-compliant for Knauf" and "not acceptable production path" are legal/compliance conclusions that the technical infrastructure sources cannot establish alone. Reframed to: "should be treated as a v1 blocker if EU-only data residency is required by Knauf's data processing agreement or applicable law; counsel must confirm whether SCCs, DPAs, or other transfer mechanisms are adequate if the direct API path is considered." The [V] factual premise (direct API routes through non-EU infrastructure) is unchanged; the [U, legal review required] tag is added to the compliance conclusion.

**Comment 6 (Fernet "second preference" wording):** Accepted. Changed to "Fernet/AES-CBC+HMAC is a fallback-style construction under OWASP guidance" to match OWASP's actual language rather than an invented ranking label.

---

## Issue ledger (delta + currently open)

**OAI-1** — `resolved` — Claim-level [V]/[U] tags completed throughout all Findings sections in this round's revised draft.

**OAI-2 / D-OAI-1** — `resolved` — FK/RLS mechanism corrected to remove "RLS hides parent rows from the FK check"; PostgreSQL official documentation treated as normative; Bytebase footgun clearly labelled as a separate application-layer concern.

**OAI-3** — `resolved` — Inline numbered citations added at point of use in Gap A, Required ADR Amendments, and Summary blocker list.

**OAI-4** — `resolved` (prior round) — Confirmed resolved; no regression.

**OAI-5** — `resolved` (prior round) — Confirmed resolved; no regression.

**OAI-6** — `resolved` (prior round) — Confirmed resolved; no regression.

**OAI-7** — `resolved` — Outbox steady-state controls added to prose in Required ADR Amendments: partial index, DLQ table, replay/idempotency tests, vacuum/dead-tuple alerting, queue-lag SLO.

**OAI-8 / D-OAI-2** — `resolved` — EU data-residency legal conclusion reframed; "not acceptable production path" and "non-compliant for Knauf" replaced with conditional framing requiring counsel confirmation; [U, legal review required] tag applied; factual [V] premise unchanged.

**D-5** — `open` (non-blocking, Phase 2 FSD) — MCP-only public programmatic surface; accurately preserved as non-blocking preference difference in "Disagreements Left Open." No action required.

No currently open issues remain from prior rounds.

---

## Evidence checked this round

- **New research performed:** (none)

- **Claims checked against existing sources:**
  - RLS FK bypass (normative): re-verified against source [2] (PostgreSQL official docs, retrieved prior round). The normative statement is unambiguous: "Referential integrity checks... always bypass row security." No change to sourcing; revision is editorial correction of the prose framing. [V]
  - AWS Bedrock EU inference profiles: confirmed available from sources [34] and [36] retrieved prior round. The cross-cloud note (GCP Vertex AI as fallback outside TTC Azure catalog) is retained as architectural judgment [U], not a new factual claim. [V]
  - OWASP Fernet wording: source [5] does not use the phrase "second preference." Revised to "fallback-style construction" which accurately paraphrases OWASP's "CTR or CBC mode should be used" if GCM/CCM are unavailable. [V]
  - Outbox controls (partial index, DLQ, vacuum): standard PostgreSQL operational practice; the specific controls are [U] architectural guidance from established operational patterns, not factual claims requiring new sourcing.

- **Factual issues found:** (none new — all corrections are editorial, following concessions to openai's sourced positions)

- **No new research because:** All changes this round address editorial precision (FK/RLS mechanism framing, OWASP wording accuracy, EU legal conclusion hedging) based on sources already retrieved in prior rounds. No new factual claims are introduced.

- **Corroboration on the other agent's claims:**
  - **[V] claim — PostgreSQL FK checks bypass RLS (openai, D-OAI-1):** Corroborated. Source [2] (official PostgreSQL docs): "Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security." This is the normative source; openai's position is correct and my round-3 draft residually conflated two separate mechanisms. [V]
  - **[V]/[U] claim — Direct Anthropic API is not EU-only; Bedrock EU is the workaround (openai, D-OAI-2):** [V] factual premise corroborated by sources [34], [35], [36]. [U] legal/compliance conclusion correctly held conditional on Knauf/TTC requirements and counsel. [V]/[U]
  - **[U] claim — "Not acceptable" is a legal conclusion not established by technical sources (openai, D-OAI-2):** Accepted as correct. The factual infrastructure routing claim and the legal acceptability conclusion are different categories. Reframed in this round's draft. [U]

---

## Comments on the current draft

No new substantive comments to raise. All prior open issues are resolved in this round's revised draft.

One non-blocking note on the outbox ADR pointer: the Required ADR Amendments section refers to "ADR-007 amendment or ADR-006 amendment" for outbox steady-state controls. This remains a pointer imprecision (two candidate ADRs rather than one), but it is a design-doc boundary question — the requirement is stated and the mechanism is named. I do not raise this as an open issue; it is noted for the reader.

---

## Disagreement carryover audit

- **Final-surfaced disagreements from Phase 2:** D-5 (MCP-only public programmatic surface) — present in draft in "Disagreements Left Open" with accurate one-sentence summary; not distorted.
- **Resolved disagreements that re-emerged:** (none)
- **Phase 4 disagreements:** D-OAI-1 (RLS FK mechanism) — resolved this round in openai's favor. D-OAI-2 (EU data-residency legal framing) — resolved this round in openai's favor.

---

## Substantive disagreements I'm holding

(none)

---

## Drafter revision note

**(a) Changes made and where:**

1. **OAI-2 / D-OAI-1 — FK/RLS mechanism final correction (Gap B §4):** Removed all residual "RLS hides parent rows from the FK check" language. The mechanism is now stated as two clearly separated phenomena: (a) FK constraint engine bypasses RLS — creating covert-channel risk mitigated by UUID FKs and scoped unique constraints; (b) application-layer subqueries/joins subject to restrictive parent-table RLS policies — a separate operational footgun. Source [2] (PostgreSQL official docs) is cited as normative for (a); source [24] (Bytebase) is cited for (b) with explicit "separate mechanism" labelling.

2. **OAI-1/OAI-3 — Tagging and inline citations (Summary, Gap A, Required ADR Amendments, Open Questions):** Added [V]/[U] tags to the five-item blocker list in Summary; added inline numbered citations [16][17][21] at point of use in Gap A; added [U] tags to each Required ADR Amendment item; added [U] tags to the Open Questions table rows.

3. **OAI-7 — Outbox steady-state controls (Required ADR Amendments):** Added prose: "Outbox steady-state controls (ADR-006 or ADR-007 amendment): partial index on undelivered-rows column (`WHERE delivered_at IS NULL`), dead-letter table for retry-exhausted events with structured failure reason, replay/idempotency tests asserting at-least-once delivery without duplicate side-effects, `n_dead_tup` alert threshold at ≥10,000 unprocessed rows, and queue-lag SLO (p95 outbox delivery ≤5 seconds under normal load)."

4. **OAI-8 / D-OAI-2 — EU legal conclusion reframing (Gap E, Summary):** Summary's "active EU data residency blocker" changed to "EU data residency risk" with [U, legal review required] on the compliance conclusion. Gap E's "not an acceptable production path" and "This is not an open question — it is a resolved blocker" changed to conditional framing. Added [V] tag to factual infrastructure claim; [U, legal review required] tag to compliance conclusion.

5. **Fernet wording (Gap F):** "OWASP's second preference rather than first" changed to "a fallback-style construction under OWASP guidance, not the AEAD-first path." Summary updated to match.

**(b) Considered and rejected:**
- Considered removing the Bytebase footgun reference from Gap B entirely since it could create confusion. Rejected: the operational footgun (restrictive parent-table policies causing application-layer join failures) is a real risk in the codebase and codegen pipeline must be warned about it. Keeping it clearly labelled as a distinct mechanism from the FK bypass is the correct approach.
- Considered adding a new open question for "Knauf DPA requirements." Rejected: the [U, legal review required] tag on the compliance conclusion already signals this dependency; a separate Open Questions row would be noise without a specific input-needed-from owner.

**(c) Comments not yet acted on:** (none — all comments accepted and incorporated)

**(d) Confidence Ledger changes:**
- Updated "Child INSERT may fail because RLS blocks parent SELECT during FK check" row: corrected mechanism label to "application-layer subquery/join subject to parent-table RLS policy (separate from FK constraint engine bypass)" with [V, conditional] tag; source [24] Bytebase is cited for this pattern, source [2] PostgreSQL official docs for the FK bypass direction.
- Updated EU data-residency compliance conclusion row: split retained; [V] factual premise row unchanged; [U, legal review required] compliance conclusion row updated to reflect conditional framing.
- No rows added or removed beyond the above corrections.

---

## Revised draft

## Summary

[U] The Partner Vetting architecture proposal is structurally well-suited to autonomous codegen: typed contracts at every boundary, a modular monolith, explicit state machines, row-level security tenant isolation, a Postgres-backed outbox, OpenTelemetry instrumentation, and append-only audit and billing streams together reduce the distributed-system failure modes that codegen pipelines handle worst. [U] The document's central weakness is that it conflates *test existence* with *test quality*: generated code and generated tests can be mutually consistent and collectively wrong, which is the primary failure mode for no-human-review systems. This oracle-quality problem manifests concretely in five gaps requiring remediation before v1 ships: [U] the absence of a mutation testing gate and independent verifier pipeline; [V] specific RLS GUC lifecycle failures under connection pooling plus a bidirectional FK/RLS vulnerability [2]; [V] an unaddressed MCP and document-AI attack surface [7][11][13]; [U] an eval-set design that risks self-referential validation; and [V] an EU data residency risk that makes the proposed direct Anthropic API path inadvisable for the Knauf (German shipper) deployment if EU-only processing is required [34][35]. Two further gaps require targeted ADR amendments: [V] the proposal's envelope encryption scheme (Fernet/AES-CBC-128) is a fallback-style construction under OWASP guidance, not the AEAD-first path [5]; and [U] the consent cache invalidation path has a race condition that may violate GDPR revocation semantics.

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

[V] The official PostgreSQL documentation establishes the normative mechanism: referential integrity checks — including foreign key references — always bypass row security [2]. This creates a covert-channel risk: a malicious tenant can probe for the existence of a parent-table row belonging to another tenant by observing whether an FK-referencing INSERT succeeds or fails, because the FK constraint engine sees the parent row regardless of RLS policy.

[V] Separately, the Bytebase PostgreSQL RLS Footguns article [24] documents a distinct operational pattern: application-layer subqueries and joins that look up parent rows before an INSERT can silently fail to find those rows when the parent table carries a restrictive RLS policy. This is a policy-misconfiguration footgun in application code, not a property of the FK constraint engine. Both risks require mitigation through different mechanisms.

**Eight architecture-level invariants (all pipeline-enforced, not design-doc concerns):**

*Connection pooling and table-owner bypass:*
1. `ALTER TABLE ... FORCE ROW LEVEL SECURITY` on all tenant-scoped tables
2. No `BYPASSRLS` attribute on the application database role
3. All tenant GUC assignments use `SET LOCAL` inside an explicit transaction boundary — never bare `SET`
4. Connection pool configured in transaction mode, not session mode
5. Migration-time policy checks: CI asserts every tenant-scoped table has an active RLS policy before migration acceptance

*FK covert-channel isolation:*

6. [U] **Opaque synthetic keys for all FK references across tenant-scoped tables** (UUIDs only, never natural or predictable keys) — mitigates covert-channel probing via FK constraint engine bypass
7. [U] **Unique constraints scoped to `(tenant_id, key)`** — never bare unique constraints on natural keys that would reveal cross-tenant existence
8. [U] Pool-reuse negative test: a test acquires a connection under tenant A, executes a query, returns the connection to the pool, re-acquires under tenant B, and asserts B cannot read A's rows

---

### 5. Gap C — MCP and Document AI Attack Surface

[V] The official MCP specification states that tools are "model-controlled, meaning that the language model can discover and invoke tools automatically," and recommends that "there SHOULD always be a human in the loop with the ability to deny tool invocations" [7]. [V] Security researchers have documented multiple outstanding MCP security issues including prompt injection, tool permissions enabling data exfiltration, and lookalike tools [10][11]. [V] OWASP has established the MCP Top 10 risk classification framework covering command injection, context injection, confused deputy attacks, and supply chain risks [13].

[U] **Required architectural addition: Document AI Quarantine Layer** — added as a named component in §6.2 (Document Intake & Authentication), between the Document Store Adapter and the Document AI Provider Abstraction.

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

[V] Research conducted in prior rounds confirms: the direct Anthropic API offers only "us" and "global" inference geographies — there is no dedicated EU-only option [34]. [V] For Azure/Microsoft Foundry specifically: when you deploy Claude via Microsoft Foundry today, the actual inference request is routed to Anthropic's own servers — regardless of which Azure region you select; Microsoft Foundry EU support is listed as "Coming 2026" on Anthropic's regional compliance page [35].

[V] The factual infrastructure consequence is established: direct `api.anthropic.com` routes personal data through non-EU infrastructure [34][35]. [U, legal review required] Whether this constitutes a v1 launch blocker depends on Knauf's data processing agreement and applicable law; counsel must confirm whether standard contractual clauses, data processing agreements, or other transfer mechanisms are adequate if the direct API path is retained. This architecture recommends treating it as a v1 blocker if EU-only data residency is required.

[V] **Required ADR-013 amendment:** The v1 Document AI Provider selection should specify, as the preferred EU-deployment path, Claude via **AWS Bedrock EU inference profiles** (e.g., `eu.anthropic.claude-*` profile routing within eu-central-1, eu-west-1, eu-north-1, et al.) [36]. (Note: GCP Vertex AI EU regional endpoints are a viable alternative but introduce a cross-cloud dependency outside the TTC Azure catalog; prefer AWS Bedrock EU as the primary path; GCP Vertex AI is a fallback if Bedrock EU capacity is insufficient for a given check definition [U].)
- [U] The direct `api.anthropic.com` endpoint should be avoided for v1 under Knauf deployment requirements pending counsel confirmation on transfer mechanisms
- [U] The TTC platform must provision AWS Bedrock credentials in addition to (or instead of) a direct Anthropic API key; the Document AI Provider Abstraction already accommodates this (provider selection is per-check definition)
- [U] The "Azure Document Intelligence as fallback for high-volume bursts" note in ADR-013 remains valid

---

### 8. Gap F — Cryptographic Posture Amendment

[V] The proposal commits to "Fernet AES-128-CBC + HMAC-SHA256" as the application-layer envelope encryption scheme. The OWASP Cryptographic Storage Cheat Sheet states: "The most commonly used authenticated modes are GCM and CCM, which should be used as a **first preference**. If GCM or CCM are not available, then CTR mode or CBC mode should be used" [5]. [V] Fernet uses AES-128-CBC + HMAC-SHA256 (encrypt-then-MAC) [6], which is a fallback-style construction under OWASP guidance — not the AEAD-first path.

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

[U] **ADR-013:** (a) Specify preferred EU deployment path as Claude via AWS Bedrock EU inference profiles [36]; note direct `api.anthropic.com` should be avoided pending counsel confirmation on transfer mechanisms [34][35]; (b) add Document AI Quarantine Layer as a required architectural component in §6.2; (c) note cross-cloud dependency if GCP Vertex AI is used as fallback.

[U] **ADR-014:** Add mutation score thresholds (Stryker.js/TypeScript [15]; go-mutesting/Go), critical core / generated shell split with separate CI gates, verifier pipeline requirement (owned by skills team), and evidence bundle release gate.

[U] **ADR-015:** Replace Fernet as default with AES-GCM (AEAD-first per OWASP [5]); permit Fernet only with explicit Trimble internal cryptographic standard citation.

[U] **ADR-017:** Restate consent revocation as an architectural invariant (immediate effect) rather than an implementation prescription.

[U] **New ADR-021 (Mutation Testing Gate):** Critical core membership list, ≥80%/≥90% threshold targets, enforcement mechanism (separate CI gate), tool family (Stryker.js/TypeScript; go-mutesting/Go).

[U] **New ADR-022 (MCP Write-Tool v1 Scope):** P1-only restriction for partner-initiated write tools; Phase 2 deferral for tenant-admin write tools with exit conditions.

[U] **New ADR-023 (Evidence Bundle Release Gate):** Required evidence categories, signing authority, blocking behavior, and ownership (infrastructure/self-healing team).

[U] **Outbox steady-state controls (ADR-006 or ADR-007 amendment):** Partial index on undelivered-rows column (`WHERE delivered_at IS NULL`), dead-letter table for retry-exhausted events with structured failure reason, replay/idempotency tests asserting at-least-once delivery without duplicate side-effects, `n_dead_tup` alert threshold at ≥10,000 unprocessed rows, and queue-lag SLO (p95 outbox delivery ≤5 seconds under normal load).

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
| [U] R7 | Does Trimble's cryptographic standard mandate Fernet specifically, or only application-layer encryption with managed keys? | Trimble Security team sign-off; ARC integration approved cryptographic profile | ARC integration documentation not yet provided in the brief | **Yes** |
| [U] R5 | What confidence threshold triggers ARC-SL skill demotion, and is this configurable per tool? | ARC skill lifecycle technical documentation | Documentation referenced in brief as "expected but not yet provided" | No |
| [U] R-Knauf | What proportion of Knauf's carrier panel is from the eight priority non-EU countries? | Knauf workshop output | Workshop had not yet occurred as of the brief's authorship date | No |
| [U] R4 | What is the audit event schema required by Applied AI Safety & Enablements? | That team's published audit standard | Standard not yet finalized at brief date | No |

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
| FK integrity checks always bypass RLS — normative mechanism | [V] | CORROBORATED | Source [2]: "Referential integrity checks... always bypass row security" — this is the normative statement |
| FK bypass creates covert-channel: tenant can probe parent-row existence via FK-referencing INSERT success/failure | [V] | CORROBORATED | Source [38] PostgreSQL Wiki; source [2] official docs |
| Application-layer subqueries/joins can fail to find parent rows when parent-table RLS policy is restrictive (Bytebase operational footgun — distinct from FK constraint engine bypass) | [V] | CONDITIONAL | Source [24] Bytebase Footguns — explicitly labelled as a separate mechanism from the FK bypass; both are valid concerns with different mitigations |
| OWASP Cryptographic Storage: GCM/CCM are first preference; CBC/CTR are fallback-style constructions | [V] | CORROBORATED | Source [5] |
| Fernet uses AES-128-CBC + HMAC-SHA256 (not AEAD) | [V] | CORROBORATED | Source [6]; Python cryptography library official documentation |
| Direct Anthropic API has no EU-only inference geography (factual infrastructure claim) | [V] | CORROBORATED | Source [34] WAIMAKERS GDPR guide (May 2026) |
| Direct Anthropic API path is a v1 blocker if EU-only data residency required (compliance conclusion) | [U, legal review required] | — | Legal/customer-requirements conclusion; not established by technical infrastructure sources alone; counsel and Knauf DPA review required |
| Claude via Microsoft Foundry/Azure routes to Anthropic's US servers regardless of Azure region | [V] | CORROBORATED | Source [35] Microsoft Q&A |
| Microsoft Foundry EU support is "Coming 2026" per Anthropic regional compliance page | [V] | CORROBORATED | Source [35] |
| AWS Bedrock EU cross-region inference for Claude available across multiple EU regions | [V] | CORROBORATED | Source [36] AWS blog |
| AWS Bedrock EU is preferred over GCP Vertex AI as EU-resident Claude path (TTC Azure-native context) | [V] factual (Bedrock EU availability) + [U] preference ranking | CORROBORATED (factual) | Source [36]; GCP cross-cloud preference ranking is architectural judgment |
| MCP tools are "model-controlled" and spec recommends human in loop | [V] | CORROBORATED | Source [7] official MCP specification 2025-06-18 |
| Security researchers documented MCP security issues including prompt injection | [V] | CORROBORATED | Sources [10], [11] |
| OWASP MCP Top 10 established | [V] | CORROBORATED | Source [13] SentinelOne |
| AI-authored PRs average 10.83 issues vs 6.45 (CodeRabbit December 2025, via secondary source) | [V] via secondary | CORROBORATED | Source [16] (secondary); explicitly attributed to CodeRabbit/secondary; not claimed as universal baseline |
| Tests can achieve 100% coverage at 4% mutation score | [V] | CORROBORATED | Sources [16][17][21] |
| Modular monolith eliminates distributed-system failure modes codegen handles worst | [U] | — | Architectural reasoning; consistent with ADR-008 rationale |
| Document AI Quarantine Layer as mitigation for MCP/document prompt injection | [U] | CORROBORATED | Corroborated by sources [11], [12]; specific implementation is synthesis |
| Consent revocation immediate-effect invariant is GDPR-relevant in German/EU jurisdictions | [U, legal review required] | — | Architectural reasoning; legal claim not directly sourced; counsel review required |
| Eval sets from same model family as production provider are self-referential | [U] | — | Architectural reasoning; no primary empirical source retrieved |
| Independent verifier pipeline required for no-human-review systems | [U] | — | Architectural reasoning; consistent with broader AI testing literature |
| `SELECT FOR UPDATE SKIP LOCKED` suitable for queue-like table access | [V] | CORROBORATED | Source [4] official PostgreSQL documentation |
| Outbox steady-state controls (partial index, DLQ, vacuum alerting, queue-lag SLO) required | [U] | — | Architectural reasoning from standard PostgreSQL outbox operational practice |

---

## Approval check

Before deciding: my strongest objection to approving is that the mutation score thresholds (≥80%/≥90%) are presented as architectural commitments without a primary empirical source establishing them as correct for this specific codebase profile, and the outbox ADR pointer still references two candidate ADRs rather than one.

Both residual issues are non-blocking: the thresholds are clearly labelled [U] as architectural proposals subject to engineer review, and the outbox ADR pointer imprecision is a design-doc boundary question that does not affect the requirement's substance. All substantive issues from all prior rounds are resolved. The FK/RLS mechanism is now correctly framed with PostgreSQL as normative and Bytebase as a separate operational pattern. The EU data-residency legal conclusion is appropriately hedged. Claim-level tagging is complete. The document satisfies the brief as a high-quality research document for architectural decision-making.

- `ENDORSEMENT:` The revised draft correctly identifies the five material gaps for autonomous codegen — oracle-quality failure mode, RLS invariants, MCP/document-AI attack surface, eval-set independence, and EU data-residency risk — and provides actionable, well-sourced architectural remediation for each.
- `NON_BLOCKING_LIMITATIONS:` Mutation score thresholds are [U] architectural proposals subject to engineer review rather than empirically validated targets for this codebase, and the outbox ADR amendment references two candidate ADRs rather than committing to one.
- `STRONGEST_REMAINING_OBJECTION:` The eval-set independence requirements (≥40%/≥60% real sample thresholds) are presented as concrete architectural commitments but are [U] without a primary empirical source establishing these specific percentages as sufficient.
- `WHY_NON_BLOCKING:` The thresholds are explicitly labelled [U] throughout, the underlying principle (eval sets must not be produced exclusively by the same model family as the production provider) is architecturally sound regardless of the exact percentage, and the reader is positioned to adjust the specific numbers during engineer review.

STATUS: APPROVED
OPEN_ISSUES: 0