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
