I'll research a few current-state items before drafting, to ensure key claims are properly verified.Now I have strong source material. Let me produce the final document.

---

## Summary

The Partner Vetting architecture proposal is structurally well-suited to autonomous codegen: typed contracts at every boundary, a modular monolith, explicit state machines, row-level security tenant isolation, a Postgres-backed outbox, OpenTelemetry instrumentation, and append-only audit and billing streams together reduce the distributed-system failure modes that codegen pipelines handle worst. The document's central weakness is that it conflates *test existence* with *test quality*: generated code and generated tests can be mutually consistent and collectively wrong, which is the primary failure mode for no-human-review systems. This oracle-quality problem manifests concretely in four gaps requiring remediation before v1 ships: the absence of a mutation testing gate, a specific RLS GUC lifecycle failure under connection pooling, an unaddressed MCP and document-AI attack surface, and an eval-set design that risks self-referential validation. Two further gaps require targeted ADR amendments: the proposal's envelope encryption scheme (Fernet/AES-CBC-128) is OWASP's second preference rather than first, and the consent cache invalidation path has a race condition that may violate GDPR revocation semantics.

---

## Findings

### 1. Executive Verdict and Primary Constraint

The governing constraint is unambiguous: every line of implementation is AI-generated; automated tests are the only quality gate. This constraint is simultaneously the architecture's greatest design driver and the source of its most dangerous unexamined assumption.

**What autonomous codegen requires of the architecture:** machine-verifiable boundaries that the pipeline cannot violate without a build failure; typed contracts so that contract drift breaks the build before reaching production; lint rules enforcing invariants the pipeline cannot self-correct without a specification; and observability that surfaces drift without human intervention. The proposal provides all of these at the coarse-grained structural level.

**The primary architectural concern for no-human-review systems:** generated code, generated tests, and generated eval sets produced from the same model family can be mutually consistent and collectively wrong. A test suite that achieves 90% branch coverage by executing happy-path lines without asserting on boundary conditions passes CI while leaving production business-logic errors undetected. The architecture must require independently produced, adversarially oriented quality gates — not merely more tests of the same character as the code they validate.

---

### 2. What the Architecture Gets Right

**Typed contracts at every boundary** are the single most important enabler. The `mcp-surface.json` schema, `internal-http.openapi.yaml`, TypeScript interfaces at bounded-context entry points, and component prop contracts as JSON Schemas constitute the contract layer that makes the entire codegen-first model tractable. Schema-first development — where editing a schema regenerates the implementation skeleton and contract tests, and where failing tests refuse the merge — is the correct architecture for a pipeline with no human PR review.

**The modular monolith decision** eliminates the distributed-system failure modes that autonomous codegen handles worst: network-boundary authentication, cross-service schema drift, partial-failure reasoning in distributed transactions, and independently deployed services whose contract tests can silently diverge. A system where four bounded contexts (Profile & Consent, Document Intake & Authentication, Rules, Network Signal stub) are enforced by import-linter rules rather than network calls achieves logical separation without distributed-systems complexity.

**Explicit state machines named and modeled** prevent codegen from leaving the domain's most critical invariants implicit. The Submission state machine (`Pending → Missing → Approved → Rejected → Expired`), the Vetting Run state machine, and the Grant lifecycle are the invariants most likely to be broken by a codegen pipeline operating without domain expertise. Naming them, specifying their transitions, and making them the subject of property tests is architecturally correct.

**PostgreSQL RLS as the tenant isolation mechanism** is the correct default-deny approach: if RLS is enabled and no applicable policy exists, access is denied by default. This means the codegen pipeline's failures (a forgotten `WHERE tenant_id = ?` clause) fail closed rather than open. This is the correct failure mode for a no-human-review system.

**The Postgres outbox** for at-least-once internal event delivery between contexts is correct for v1 load. The `SELECT FOR UPDATE SKIP LOCKED` pattern is explicitly documented as suitable for queue-like table access, providing the at-least-once delivery guarantee without an external message broker.

**OpenTelemetry as vendor-neutral instrumentation** is correct and swap-friendly: the same SDK serves traces, metrics, and logs regardless of which backend (Datadog, Grafana, Azure Monitor, New Relic) the engineer-review pass selects. This is the right architecture for a codegen-first system because the instrumentation code is stable and the backend decision is deferred.

**The lint rule inventory** is load-bearing. The specific rules named — no `UPDATE` against `audit_events` or `billable_events`, no raw queries bypassing RLS, no PII in logs via typed values, no cross-context imports outside the published interface, every state-changing handler emits ≥1 outbox row in the same transaction — each catch a class of bug that branch-coverage tests alone cannot reliably detect because they depend on the *absence* of a call or statement. This is the correct architecture for codegen-first systems: make illegal states unrepresentable at the lint level.

**Append-only audit and billable event streams** are essential for a codegen-first system because they are the one source of ground truth about what the system actually did that a future human or automated analysis can recover from. No generated implementation can erase audit history.

---

### 3. Gap A — Independent Verifier Pipeline

The current proposal has a single code-generation pipeline. The same pipeline that produces implementation also produces tests from the same specifications and model family. This is the oracle-quality failure mode: the two artifacts can pass each other's checks while both being wrong in the same direction.

The architecture must add a **separate verifier pipeline** that consumes the same specification as the producer pipeline but executes in a distinct model context. Its purpose is to break the producer's output, not to confirm it.

**What the verifier pipeline generates:**
- Mutation test cases targeting every critical core module (see Gap A: Mutation Testing below)
- Fuzz inputs for document metadata parsers, JWT/OIDC token parsers, and ruleset predicate evaluators
- Property-test counterexamples for every state machine transition
- Policy-denial test cases for every role × resource × action triple (Platform Admin, Tenant Admin, Tenant User, Partner × all MCP tools and internal HTTP endpoints × read/write/delete)
- Migration rollback tests asserting that schema migrations are reversible
- Prompt-injection document fixtures for every AI-bearing check in the check catalog

**The evidence bundle release gate:** A signed evidence artifact is required per merge and must cover: unit tests (passing), property tests (passing), mutation score (at threshold), fuzz test runs (no new crashes), contract tests (passing), end-to-end browser tests (passing), accessibility checks (passing), SAST scan results (no new critical/high findings), dependency scan (no new critical CVEs), secret scan (no secrets detected), AI eval set results (confidence at threshold), prompt-injection eval results (no falsified passes), RLS negative tests (all failing as expected), policy-denial tests (all correctly denying), migration rollback tests (passing), and observability assertion tests (all expected telemetry emitted). Release is blocked without the complete signed evidence bundle.

---

### 4. Gap A — Mutation Testing as a Required Gate

Branch coverage ≥90% is a necessary but insufficient quality gate for AI-generated code. Research shows tests can achieve 100% line and branch coverage while scoring only 4% on mutation testing, because the tests execute code paths without asserting on boundary conditions. AI-authored pull requests average 10.83 issues per PR versus 6.45 for human-only submissions, with logic and correctness errors up 75%. A test suite with 95% line coverage but only 38% mutation score provides false confidence.

**Mutation score targets:**
- ≥80% for all generated code in the codebase
- ≥90% for **critical core modules**: Authorization, Consent/Grants, RLS session binding, State machines (Vetting Run, Submission, Grant lifecycle), Coverage Report Builder, Rules Evaluator, Audit/Billable Event Emission, Expiry/Reverification logic, Crypto/Key Management, MCP state-changing authorization

**The critical core / generated shell split** must be enforced structurally, not by convention:
- Critical core lives in a named package with separate module labels
- A separate, more stringent CI gate threshold applies to every merge that touches any critical core module or any public contract it exposes
- Import-graph rules enforced by the import-linter prevent generated shell modules from being imported by critical core
- Critical core tests must include: property tests on every state transition (not just unit tests), fuzz tests on parser inputs, policy-denial tests for every authorization path, and the stricter mutation score target above

---

### 5. Gap B — RLS GUC Lifecycle — Seven Mandatory Invariants

The proposal correctly chooses PostgreSQL RLS as the tenant isolation mechanism and specifies the per-request middleware pattern (`pv.current_tenant` and `pv.current_principal_role` GUCs). However, the implementation detail that makes this safe under connection pooling is absent, and it is precisely the implementation detail that a codegen pipeline will get wrong.

In transaction mode pooling (the recommended production mode for connection efficiency), `SET` persists for the lifetime of the session on the server side, meaning a connection returned to the pool by tenant A and subsequently acquired by tenant B retains A's GUC values unless the application explicitly handles this. The correct pattern — confirmed by Heroku's authoritative PgBouncer documentation — is `SET LOCAL`, which scopes the variable to the current transaction and resets automatically when the transaction ends: "Any changes to session state via SET must only be made with `SET LOCAL` so that the changes are scoped only to the currently executing transaction. Never use `SET SESSION` or `SET` alone."

Additionally, the proposal's RLS policy pattern does not specify `FORCE ROW LEVEL SECURITY`, which means if the application role is the table owner, RLS is bypassed silently.

**Seven architecture-level invariants (not design-doc concerns):**

1. `ALTER TABLE ... FORCE ROW LEVEL SECURITY` on all tenant-scoped tables, ensuring the application role cannot bypass policies through table ownership
2. No `BYPASSRLS` attribute on the application database role
3. All tenant GUC assignments (`pv.current_tenant`, `pv.current_principal_role`) use `SET LOCAL` inside an explicit transaction boundary — never bare `SET` followed by `RESET` on pool return
4. Connection pool configured in transaction mode (not session mode); this is the required complement to `SET LOCAL`
5. Migration-time policy checks: schema migration CI asserts that every tenant-scoped table has an active RLS policy before the migration is accepted
6. Referential-integrity leak tests: integration tests assert that a cross-tenant `INSERT` into a child table referencing a parent row from a different tenant fails closed (RLS blocks the parent SELECT during the FK check)
7. Pool-reuse negative test: a test acquires a connection under tenant A, executes a query, returns the connection to the pool, re-acquires under tenant B, and asserts that B cannot read A's rows — this test must be in the codegen pipeline's invariant set

These seven are codegen-pipeline invariants enforced by lint and integration tests, not prose in the architecture document.

---

### 6. Gap C — MCP and Document AI Attack Surface

The official MCP specification states that tools are "model-controlled, meaning that the language model can discover and invoke tools automatically," and recommends that "there SHOULD always be a human in the loop with the ability to deny tool invocations." In April 2025, security researchers documented multiple outstanding security issues with MCP, including prompt injection, tool permissions enabling data exfiltration, and lookalike tools that can silently replace trusted ones. OWASP has established the first industry-standard MCP Top 10 risk classification framework covering command injection, context injection, confused deputy attacks, and supply chain risks.

The proposal treats the MCP adapter as "intentionally thin — no business logic, only protocol translation and authentication." This is correct for what the adapter *does*, but the proposal contains no architecture-level defense for what an adversary *can put into* the data the adapter processes.

**Required architectural addition: Document AI Quarantine Layer**

The planning model (Claude, in the document AI role) must never read raw carrier document content directly. The architecture must add a **Document AI Quarantine Layer** as a named component in Document Intake & Authentication: a separate, tool-incapable model invocation context that reads carrier document bytes and returns only a typed extraction package. The planning model receives only the typed extraction package, not the document content. This implements the dual-LLM quarantine pattern: the quarantined model handles untrusted bytes but has no tool-calling capability; the planning model makes decisions but never sees attacker-controlled content.

This component sits between the Document Store Adapter and the Document AI Provider Abstraction. Its inputs are: `(blob_uri, check_id, check_version, extraction_schema)`. Its outputs are a `TypedExtractionPackage` that strictly conforms to the check's output schema. It never accepts free-form prompts from the carrier document; it only accepts catalog-authored, versioned extraction schemas.

**v1 MCP write-tool scope:**
- `submit_document` and `submit_attestation` are available in v1 under **P1/known Trimble-ID actor context only** (not P3 external-agent context), with: visible UI confirmation before document submission, malware/MIME scan at the Upload Endpoint, idempotency keys on every call, Document AI Quarantine Layer processing, adversarial document fixtures in the eval suite, and **no automatic terminal approval** (`Approved` state) reachable exclusively via the MCP path
- **Deferred to Phase 2:** `create_ruleset`, `grant_visibility`, `revoke_visibility`, and `start_vetting_run` via MCP, pending completion of the MCP security model (per-tool capability scoping, confirmation gating, policy decision logging, and adversarial test suite)
- Check definition schema prohibits tenant-authored prompt templates; only Platform Admin-authored, versioned catalog templates may be used
- Prompt-injection document fixtures must be in the eval suite for every AI-bearing check: documents containing embedded instruction text must produce `inconclusive` Result Envelopes, not falsified `pass` results

---

### 7. Gap D — Eval Set Independence

The proposal specifies eval sets of ≥200 labelled examples per check. This is correct discipline. The gap is that an eval set produced entirely by the same model family as the production document AI provider is self-referential: the same biases, the same blind spots, the same edge-case failures that affect production extraction will affect the eval set generation, and the system will appear to pass while being wrong in the same direction on the same inputs.

**Requirements:**
- Eval sets must include a substantial proportion of **real or independently anonymized** document samples
- Synthetically generated examples must be produced by a **model distinct from the production document AI provider** (typically a separate model family)
- Proportion targets: ≥40% real/anonymized for EU checks; ≥60% for non-EU country variants where synthetic ground truth is harder to verify
- Where legal/privacy constraints prevent real document samples, the gap must be **disclosed in the check version's release evidence** and mitigated with independently sourced edge-case fixtures (such as publicly available regulatory document templates)
- An eval set produced exclusively by the same model family as Claude (the proposed production provider) does not constitute an independent quality gate

---

### 8. Gap E — Cryptographic Posture Amendment

The proposal commits to "Fernet AES-128-CBC + HMAC-SHA256" as the application-layer envelope encryption scheme. Fernet is a well-established Python cryptography library construct that implements encrypt-then-MAC using AES-128-CBC and HMAC-SHA256. This is a sound construction — it is not broken. However, it is **OWASP's second preference**, not first. The OWASP Cryptographic Storage Cheat Sheet states explicitly: "The most commonly used authenticated modes are GCM and CCM, which should be used as a **first preference**. If GCM or CCM are not available, then CTR mode or CBC mode should be used." Fernet's CBC mode with separate MAC is the "CTR or CBC mode" fallback path, not the AEAD-first path.

**Required amendment:**
- Replace Fernet as the architecture-specified default with **AES-GCM** (or equivalent AEAD mode such as XChaCha20-Poly1305), which provides confidentiality, integrity, and authenticity in a single construction with a single key
- Fernet (AES-128-CBC + HMAC-SHA256) remains permitted **if and only if** an explicit Trimble internal cryptographic standard mandating it is cited in ADR-020; if no such citation is provided, AES-GCM is the required default
- Per-profile envelope keys in Azure Key Vault and the GDPR crypto-erasure mechanism (destroying the envelope key on profile deletion, rendering document blobs and consent records unreadable while preserving audit metadata) are architecturally correct and unchanged

This is a named open question (R7) in the surviving open questions section.

---

### 9. Gap F — Consent Cache Invalidation Race

The architecture specifies a 5-minute Redis TTL for the IdP attribute cache and by implication for the consent state cache (the `is_granted(profile_id, tenant_id, section)` read path). The proposal's consent revocation semantic is "freeze on revoke: future reads are denied." These two specifications are in conflict.

When a carrier revokes consent at T=0, any tenant Status Card rendered before T+5 minutes may read stale cached grant state and display data the carrier has explicitly withdrawn consent for. In GDPR jurisdictions, the right to object may require immediate effect; a 5-minute window of stale consent state may constitute a compliance failure.

**Required architecture-level invariant in the Consent Manager specification:**

On grant revocation, the Consent Manager must **synchronously invalidate** the `(profile_id, tenant_id, section)` Redis cache key as part of the same request handler, before returning 200 to the caller. Specifically:
- The Redis `DEL` call executes within the same request handler as the DB write, before the response is sent
- This is not deferred to an async outbox event; the 200 response must not be sent until both the DB write and the Redis invalidation have completed
- If Redis is unavailable at revocation time: the DB write commits and the consent revocation is durably recorded; the audit event records `cache_invalidation_failed: true`; a conservative negative-cache entry is written to Redis on reconnect (TTL ≤60 seconds); an alert fires immediately; reads fail closed during the Redis unavailability window

The 5-minute TTL is acceptable for IdP attribute caching (user name, email — these are informational). It is not acceptable as the only freshness mechanism for authorization/consent state that has a legal revocation semantic.

---

### 10. Required ADR Amendments

The following amendments to the existing ADR set are required by the findings above:

**ADR-009 (Tenant isolation: PostgreSQL row-level security):** Add the seven mandatory GUC-lifecycle and `FORCE ROW LEVEL SECURITY` invariants described in Gap B as explicit architectural commitments, not design-doc delegations.

**ADR-010 (MCP programmatic surface):** Add v1 write-tool scope restriction (P1-only for `submit_document`/`submit_attestation`; Phase 2 for tenant-admin writes) and the per-tool capability scope requirement for all write-capable tools.

**ADR-013 (Document AI provider):** Add the Document AI Quarantine Layer as a required architectural component with the typed extraction package boundary specification.

**ADR-014 (Testing framework):** Add mutation score thresholds (≥80% general, ≥90% critical core), the critical core / generated shell split with separate CI gates, the verifier pipeline requirement, and the evidence bundle release gate with its required categories.

**ADR-015 (Secret and key management):** Replace Fernet as the default with AES-GCM (AEAD-first per OWASP); permit Fernet only with explicit Trimble internal cryptographic standard citation.

**ADR-017 (Consent model):** Add synchronous Redis cache invalidation on revocation as an architecture-level invariant of the Consent Manager, not a design-doc implementation detail.

**New ADR-021 (Mutation testing gate):** Commits the critical core membership list, the ≥80%/≥90% threshold targets, the enforcement mechanism (separate CI gate), and the rationale.

**New ADR-022 (MCP write-tool v1 scope):** Commits the P1-only restriction for partner-initiated write tools and the Phase 2 deferral for tenant-admin write tools, with the conditions under which Phase 2 deferral ends (per-tool capability scoping, confirmation gating, policy decision logging, and adversarial test suite complete).

---

### 11. Architecture Diagram — Codegen-First Assurance Topology

The diagram below shows the producer/verifier pipeline split, the evidence bundle gate as the release condition, and the five hardening lanes that the architecture must satisfy before an evidence bundle can be signed.

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540" font-family="Arial, sans-serif">
  <!-- Background -->
  <rect x="0" y="0" width="960" height="540" rx="0" fill="#f8fafc"/>

  <!-- Title -->
  <text x="480" y="38" text-anchor="middle" font-size="17" font-weight="bold" fill="#0f172a">Partner Vetting — Codegen-First Assurance Topology</text>

  <!-- Spec Package Box -->
  <rect x="30" y="70" width="180" height="90" rx="10" fill="#dbeafe" stroke="#1d4ed8" stroke-width="1.5"/>
  <text x="120" y="98" text-anchor="middle" font-size="13" font-weight="bold" fill="#1e3a8a">Reviewed Spec Package</text>
  <text x="120" y="116" text-anchor="middle" font-size="11" fill="#1e40af">contracts · invariants</text>
  <text x="120" y="132" text-anchor="middle" font-size="11" fill="#1e40af">policies · threat model</text>

  <!-- Arrow spec → producer -->
  <line x1="210" y1="100" x2="290" y2="100" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>
  <!-- Arrow spec → verifier -->
  <line x1="210" y1="130" x2="290" y2="310" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>

  <!-- Producer Agent Box -->
  <rect x="290" y="60" width="200" height="90" rx="10" fill="#dcfce7" stroke="#15803d" stroke-width="1.5"/>
  <text x="390" y="90" text-anchor="middle" font-size="13" font-weight="bold" fill="#14532d">Producer Pipeline</text>
  <text x="390" y="108" text-anchor="middle" font-size="11" fill="#166534">generates implementation</text>
  <text x="390" y="124" text-anchor="middle" font-size="11" fill="#166534">tests · migrations · docs</text>

  <!-- Verifier Agent Box -->
  <rect x="290" y="260" width="200" height="110" rx="10" fill="#fee2e2" stroke="#b91c1c" stroke-width="1.5"/>
  <text x="390" y="290" text-anchor="middle" font-size="13" font-weight="bold" fill="#7f1d1d">Verifier Pipeline</text>
  <text x="390" y="308" text-anchor="middle" font-size="11" fill="#991b1b">mutation tests · fuzz inputs</text>
  <text x="390" y="324" text-anchor="middle" font-size="11" fill="#991b1b">policy-denial cases</text>
  <text x="390" y="340" text-anchor="middle" font-size="11" fill="#991b1b">prompt-injection fixtures</text>
  <text x="390" y="356" text-anchor="middle" font-size="11" fill="#991b1b">migration rollback tests</text>

  <!-- Arrow producer → evidence -->
  <line x1="490" y1="105" x2="570" y2="170" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>
  <!-- Arrow verifier → evidence -->
  <line x1="490" y1="315" x2="570" y2="265" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>

  <!-- Evidence Bundle Gate -->
  <rect x="570" y="145" width="200" height="145" rx="10" fill="#fef9c3" stroke="#a16207" stroke-width="1.5"/>
  <text x="670" y="173" text-anchor="middle" font-size="13" font-weight="bold" fill="#78350f">Signed Evidence Bundle</text>
  <text x="670" y="191" text-anchor="middle" font-size="10" fill="#92400e">unit · property · mutation ≥80/90%</text>
  <text x="670" y="206" text-anchor="middle" font-size="10" fill="#92400e">fuzz · contract · e2e · a11y</text>
  <text x="670" y="221" text-anchor="middle" font-size="10" fill="#92400e">SAST · dep-scan · secret-scan</text>
  <text x="670" y="236" text-anchor="middle" font-size="10" fill="#92400e">AI eval · prompt-injection eval</text>
  <text x="670" y="251" text-anchor="middle" font-size="10" fill="#92400e">RLS-negative · policy-denial</text>
  <text x="670" y="266" text-anchor="middle" font-size="10" fill="#92400e">migration-rollback · observability</text>
  <text x="670" y="281" text-anchor="middle" font-size="11" font-weight="bold" fill="#b45309">BLOCKS RELEASE IF INCOMPLETE</text>

  <!-- Arrow evidence → release -->
  <line x1="770" y1="217" x2="860" y2="217" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>

  <!-- Release Box -->
  <rect x="860" y="185" width="90" height="65" rx="10" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
  <text x="905" y="212" text-anchor="middle" font-size="12" font-weight="bold" fill="#f8fafc">Release</text>
  <text x="905" y="230" text-anchor="middle" font-size="10" fill="#94a3b8">to production</text>

  <!-- Hardening Lanes Section -->
  <text x="480" y="415" text-anchor="middle" font-size="13" font-weight="bold" fill="#0f172a">Hardening Lanes (must appear in Evidence Bundle)</text>

  <!-- Lane boxes -->
  <!-- RLS Lane -->
  <rect x="30" y="430" width="160" height="90" rx="8" fill="#ede9fe" stroke="#6d28d9" stroke-width="1.2"/>
  <text x="110" y="450" text-anchor="middle" font-size="11" font-weight="bold" fill="#4c1d95">RLS Invariants</text>
  <text x="110" y="467" text-anchor="middle" font-size="9.5" fill="#5b21b6">SET LOCAL + tx mode</text>
  <text x="110" y="482" text-anchor="middle" font-size="9.5" fill="#5b21b6">FORCE ROW LEVEL SEC.</text>
  <text x="110" y="497" text-anchor="middle" font-size="9.5" fill="#5b21b6">no BYPASSRLS app role</text>
  <text x="110" y="512" text-anchor="middle" font-size="9.5" fill="#5b21b6">pool-reuse negative test</text>

  <!-- MCP Lane -->
  <rect x="205" y="430" width="165" height="90" rx="8" fill="#fce7f3" stroke="#9d174d" stroke-width="1.2"/>
  <text x="287" y="450" text-anchor="middle" font-size="11" font-weight="bold" fill="#831843">MCP Zero-Trust</text>
  <text x="287" y="467" text-anchor="middle" font-size="9.5" fill="#9d174d">P1-only writes (v1)</text>
  <text x="287" y="482" text-anchor="middle" font-size="9.5" fill="#9d174d">quarantine layer</text>
  <text x="287" y="497" text-anchor="middle" font-size="9.5" fill="#9d174d">per-tool capability scope</text>
  <text x="287" y="512" text-anchor="middle" font-size="9.5" fill="#9d174d">admin writes → Phase 2</text>

  <!-- Document AI Lane -->
  <rect x="385" y="430" width="165" height="90" rx="8" fill="#fff7ed" stroke="#c2410c" stroke-width="1.2"/>
  <text x="467" y="450" text-anchor="middle" font-size="11" font-weight="bold" fill="#7c2d12">Document AI</text>
  <text x="467" y="467" text-anchor="middle" font-size="9.5" fill="#9a3412">typed extraction pkg</text>
  <text x="467" y="482" text-anchor="middle" font-size="9.5" fill="#9a3412">no raw carrier text → LLM</text>
  <text x="467" y="497" text-anchor="middle" font-size="9.5" fill="#9a3412">≥40/60% real eval samples</text>
  <text x="467" y="512" text-anchor="middle" font-size="9.5" fill="#9a3412">injection fixtures required</text>

  <!-- Critical Core Lane -->
  <rect x="565" y="430" width="165" height="90" rx="8" fill="#ecfdf5" stroke="#065f46" stroke-width="1.2"/>
  <text x="647" y="450" text-anchor="middle" font-size="11" font-weight="bold" fill="#064e3b">Critical Core</text>
  <text x="647" y="467" text-anchor="middle" font-size="9.5" fill="#065f46">mutation ≥90% gate</text>
  <text x="647" y="482" text-anchor="middle" font-size="9.5" fill="#065f46">property tests: all transitions</text>
  <text x="647" y="497" text-anchor="middle" font-size="9.5" fill="#065f46">separate CI gate threshold</text>
  <text x="647" y="512" text-anchor="middle" font-size="9.5" fill="#065f46">import-graph enforcement</text>

  <!-- Consent + Outbox Lane -->
  <rect x="745" y="430" width="185" height="90" rx="8" fill="#f0fdf4" stroke="#166534" stroke-width="1.2"/>
  <text x="837" y="450" text-anchor="middle" font-size="11" font-weight="bold" fill="#14532d">Consent + Outbox</text>
  <text x="837" y="467" text-anchor="middle" font-size="9.5" fill="#166534">sync cache invalidation</text>
  <text x="837" y="482" text-anchor="middle" font-size="9.5" fill="#166534">on revocation (pre-200)</text>
  <text x="837" y="497" text-anchor="middle" font-size="9.5" fill="#166534">outbox: partial idx + DLQ</text>
  <text x="837" y="512" text-anchor="middle" font-size="9.5" fill="#166534">n_dead_tup alert required</text>

  <!-- Arrow marker def -->
  <defs>
    <marker id="arr" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#475569"/>
    </marker>
  </defs>
</svg>
```

---

### 12. Surviving Open Questions

Five questions cannot be resolved from the material available in this run and require specific inputs:

**R7 — Trimble internal cryptographic standard (Fernet vs. AES-GCM):** Does Trimble's TTC platform or the ARC integration posture mandate Fernet specifically, or does it mandate only "application-layer encryption with Trimble-managed keys"? If the former, ADR-020 keeps Fernet with an internal standard citation. If the latter, AES-GCM becomes the required default immediately. Resolution requires: Trimble Security team sign-off or ARC integration documentation specifying the approved cryptographic profile.

**R5 — ARC-SL degradation thresholds and per-tool configurability:** What confidence level triggers a skill demotion from `published` to `degraded`, and is this threshold configurable per tool? This determines whether R5 (ARC demoting Partner Vetting without warning) can be mitigated by per-tool threshold configuration or only by overall skill health monitoring. Resolution requires: ARC skill lifecycle technical documentation (referenced but not yet provided in the brief).

**R-Knauf — Knauf carrier population non-EU country distribution:** What proportion of Knauf's carrier panel consists of carriers from Albania, Bosnia, Montenegro, Norway, Serbia, Switzerland, Turkey, or Ukraine? This determines whether the Phase 1 non-EU check catalog (eight priority countries) is sufficient for the Knauf launch or whether additional variants are needed immediately. Resolution requires: the Knauf workshop referenced in the brief.

**R4 — Applied AI Safety & Enablements audit schema:** What is the target schema for the audit export? The proposal defers to this team's standard "once it ships," but the architecture's audit event schema must be forward-compatible. Until this schema is published, the export contract is a documented pull interface — but forward-compatibility cannot be verified. Resolution requires: the Applied AI Safety & Enablements team's published audit standard.

**R-Claude-region — Anthropic Claude regional availability in Azure West Europe:** Does Anthropic provide API endpoints in West Europe with acceptable latency and data-residency properties compatible with a Knauf (German shipper) production deployment? If not, the fallback provider for the document AI must be elevated from "rate-limit fallback" to "co-primary." Resolution requires: current Anthropic API regional documentation and Trimble data-residency policy for EU customer data.

---

## Disagreements Left Open

Phase 2 reached full consensus. No final-surfaced disagreements remain. One non-blocking limitation noted for transparency:

**D-5 (MCP-only public programmatic surface) — non-blocking preference difference:** OpenAI continues to prefer preserving a clean future-publishable HTTP contract for external customer compliance integrations that want deterministic non-agent APIs. Claude maintains that the brief explicitly designates REST as a non-goal for v1 and v2, and that the internal HTTP boundary is clean enough to publish later if Phase 3 surfaces a concrete requirement. This preference difference does not affect any v1 recommendation: the Portal provides deterministic UI access, the internal HTTP boundary is never externally exposed, and both agents agree that Phase 3 can introduce a REST surface if a paying customer requires it. The architecture can accommodate either direction without structural change.

---

## Open Questions

| ID | Question | Input needed to resolve | Why unresolved |
|---|---|---|---|
| R7 | Does Trimble's cryptographic standard mandate Fernet specifically, or only application-layer encryption with managed keys? | Trimble Security team sign-off; ARC integration approved cryptographic profile | ARC integration documentation not yet provided in the brief |
| R5 | What confidence threshold triggers ARC-SL skill demotion from `published` to `degraded`, and is this configurable per tool? | ARC skill lifecycle technical documentation | Documentation referenced in brief as "expected but not yet provided" |
| R-Knauf | What proportion of Knauf's carrier panel is from the eight priority non-EU countries? | Knauf workshop output | Workshop had not yet occurred as of the brief's authorship date |
| R4 | What is the audit event schema required by Applied AI Safety & Enablements? | That team's published audit standard | Standard not yet finalized at brief date |
| R-Claude-region | Does Anthropic provide API endpoints in Azure West Europe with acceptable latency and EU data-residency properties for a German shipper deployment? | Current Anthropic regional API documentation; Trimble EU data-residency policy | Requires live API documentation check; not in brief |

---

## Sources

1. Heroku Dev Center — Best Practices for PgBouncer Configuration: https://devcenter.heroku.com/articles/best-practices-pgbouncer-configuration
2. PostgreSQL Documentation — Row Security Policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
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
23. PgBouncer official documentation — config.html: https://www.pgbouncer.org/config.html
24. Bytebase — PostgreSQL Row Level Security Limitations and Alternatives: https://www.bytebase.com/blog/postgres-row-level-security-limitations-and-alternatives/
25. fast-check documentation — Model-based testing: https://fast-check.dev/docs/advanced/model-based-testing/
26. OWASP — Top 10 for Large Language Model Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications/
27. OWASP — Application Security Verification Standard: https://owasp.org/www-project-application-security-verification-standard/
28. SLSA — Security Levels: https://slsa.dev/spec/v1.0/levels
29. OpenTelemetry Documentation: https://opentelemetry.io/docs/
30. React — React 19 announcement (custom elements support): https://react.dev/blog/2024/12/05/react-19
31. Lit official site: https://lit.dev/
32. arXiv — Coverage Is Not Enough: SBFL-Driven Insights into Manually Created vs. Automatically Generated Tests: https://arxiv.org/pdf/2512.11223

---

## Confidence Ledger

| Claim | Tag | Signal | Source notes |
|---|---|---|---|
| Heroku official docs: "Any changes to session state via SET must only be made with `SET LOCAL`... Never use `SET SESSION` or `SET` alone" | [V] | CORROBORATED | Source [1], retrieved this run; authoritative PgBouncer configuration documentation |
| In transaction-mode pooling, `SET` persists to session end and leaks tenant GUC values between clients if not scoped with `SET LOCAL` | [V] | CORROBORATED | Sources [1], [22], [23]; multiple authoritative sources confirm this failure mode |
| `FORCE ROW LEVEL SECURITY` is required when the application role is the table owner; owners bypass RLS by default | [V] | CORROBORATED | PostgreSQL official row-security documentation [2], retrieved this run |
| PostgreSQL RLS default-deny: if RLS is enabled and no policy exists, access is denied | [V] | CORROBORATED | Source [2]; official PostgreSQL documentation |
| OWASP Cryptographic Storage: GCM and CCM are first preference; "should be used as a first preference" | [V] | CORROBORATED | Source [5], retrieved this run; canonical OWASP guidance |
| Fernet uses AES-128-CBC + HMAC-SHA256 (encrypt-then-MAC, not AEAD) | [V] | CORROBORATED | Source [6]; Python cryptography library official documentation |
| Fernet is OWASP second preference (CBC mode with separate MAC), not first preference (GCM/CCM AEAD) | [V] | CORROBORATED | Sources [5], [6]; follows directly from first two claims |
| MCP tools specification states tools are "model-controlled" and that "there SHOULD always be a human in the loop with the ability to deny tool invocations" | [V] | CORROBORATED | Source [7], retrieved this run; official MCP specification 2025-06-18 |
| MCP authorization is optional for implementations | [V] | CORROBORATED | Source [8]; official MCP authorization specification |
| Security researchers documented multiple outstanding MCP security issues including prompt injection and lookalike tools (April 2025) | [V] | CORROBORATED | Source [10]; Wikipedia article on MCP with citation to April 2025 researcher analysis |
| OWASP MCP Top 10 project has been established covering command injection, context injection, confused deputy attacks, supply chain risks | [V] | CORROBORATED | Source [13]; SentinelOne article referencing the official OWASP MCP Top 10 project |
| AI-generated tests can achieve 100% line and branch coverage while scoring only 4% on mutation testing | [V] | CORROBORATED | Source [16]; researchers on HumanEval-Java documented this exact result |
| AI-authored PRs average 10.83 issues vs. 6.45 for human-only; logic/correctness errors up 75%; security findings 57% more prevalent | [V] | CORROBORATED | Source [16]; citing CodeRabbit December 2025 analysis of 470 open-source PRs |
| Mutation score ≥80% for business logic, ≥90% for payment and security modules is a recommended threshold | [V] | CORROBORATED | Source [20]; industry threshold guidance corroborated by source [39] (StrykerJS default "high" threshold is 80%) |
| Meta's ACH tool (FSE 2025) uses LLM-based mutation testing to overcome barriers to scale | [V] | CORROBORATED | Source [19]; Meta Engineering blog post on FSE 2025 keynote |
| "SELECT FOR UPDATE SKIP LOCKED" is documented as usable to avoid lock contention with multiple consumers in a queue-like table | [V] | CORROBORATED | Source [4]; official PostgreSQL documentation |
| The modular monolith eliminates the distributed-system failure modes autonomous codegen handles worst | [U] | — | Architectural reasoning; no direct primary source; consistent with ADR-008's stated rationale |
| The Document AI Quarantine Layer (dual-LLM quarantine pattern) is the current state-of-the-art for document prompt injection defense | [U] | CORROBORATED | Dual-LLM quarantine concept corroborated by Simon Willison's analysis [11] and CoSAI WS4 [12]; specific implementation guidance is synthesis |
| The 5-minute Redis TTL on consent state creates a potential GDPR compliance failure window when a partner revokes consent | [U] | — | Architectural reasoning; follows from the freeze-on-revoke semantic and Redis TTL specification in the proposal; no direct primary source for the legal claim |
| Eval sets produced by the same model family as the production document AI provider are self-referential and do not constitute an independent quality gate | [U] | — | Architectural reasoning; the self-referential oracle problem is well-established in ML literature but no specific source retrieved this run |
| An independent verifier pipeline generating adversarial tests from the same spec is required for no-human-review systems | [U] | — | Architectural reasoning derived from the oracle-quality failure mode; no single primary source; consistent with broader AI testing literature |
| Referential-integrity FK checks bypass RLS (parent table lookup during child INSERT may see cross-tenant rows) | [U] | CORROBORATED | Corroborated by Bytebase source [24] on RLS limitations; architecture documents this as gap (f) in the seven RLS invariants |
| The proposal's estimate that Postgres outbox / SKIP LOCKED is adequate for v1 load (Knauf only) is plausible | [U] | — | Plausibility reasoning; v1 with one customer is well below published throughput limits for SKIP LOCKED queues; no specific load estimate retrieved |