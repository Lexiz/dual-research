## Summary

I now concede claude’s concrete RLS point: `SET LOCAL` inside a transaction plus `FORCE ROW LEVEL SECURITY` and non-owner/non-`BYPASSRLS` app roles should be explicit architecture-level invariants, not design details. [V] [1][2] I also adopt claude’s consent-cache revocation race and eval-set independence points, while holding my original thesis that the final critique should lead with oracle quality: generated code, generated tests, and generated evals can mutually agree while still being wrong. [U] I am still negotiating because we have a material v1-scope disagreement around state-changing MCP tools and a framing disagreement about whether the final document leads with assurance/oracles or concrete infrastructure risks. [U] I still recommend `openai` as drafter, but I would incorporate claude’s RLS, MCP, outbox, consent-cache, and eval-set findings as first-class sections. [U]

## Answers to claude's open questions

1. My v1 MCP narrowing applies most strongly to tenant-admin and compliance-impacting writes: `create_ruleset`, `grant_visibility`, `revoke_visibility`, and externally initiated `start_vetting_run` should not be exposed as state-changing MCP tools in v1 unless the capability, confirmation, idempotency, and policy-test model is complete. [U] For `submit_document` and `submit_attestation`, I distinguish the **business capability** from the **MCP surface**: partners need to submit documents in v1, but the safer v1 surface is the Portal/internal HTTP path, not P3/external-agent MCP. [U] If ARC-driven carrier self-vetting is non-negotiable for v1, I would allow `submit_document`/`submit_attestation` only under P1/known Trimble-ID actor context, with explicit UI confirmation, malware/content scanning, idempotency keys, and no automatic terminal approval from that path. [U]

2. The product pair can produce the first spec package, but a credible no-code-review process still needs **human review of non-code artifacts** by role: product/domain review by the product pair, security/policy review by the skills or infrastructure pair if they own the corresponding control, and release-evidence review by whoever owns launch governance. [U] This is not human code inspection because reviewers do not inspect generated implementation diffs; they approve specifications, policy matrices, eval-set provenance, threat models, and release evidence. [U] If the program forbids even human review of specs/tests/evidence, then I would lower the final architecture verdict from “not yet credible” to “not credible,” because the oracles would be self-referential. [U]

3. I do not know whether Trimble’s ARC posture mandates Fernet specifically or only mandates application-layer encryption with managed keys. [U] Public guidance supports changing the default architecture text: OWASP says authenticated modes such as GCM and CCM should be first preference where available, while Fernet is documented as AES-CBC with HMAC-SHA256 rather than an AEAD mode. [V] [8][9] Therefore, the final document should say: “Use an approved AEAD envelope-encryption profile such as AES-GCM unless Trimble security has an explicit Fernet standard; if Fernet is retained, document the exception and test vectors.” [U]

4. Yes. [U] I agree the concrete invariant should be: every tenant-scoped DB operation runs inside an explicit transaction that sets tenant and role GUCs using `SET LOCAL`, because PostgreSQL documents `SET LOCAL` as lasting only until the end of the current transaction, whereas `SET` persists until session end after commit. [V] [2] I also agree `FORCE ROW LEVEL SECURITY` is required where the application role could otherwise be treated as table owner, and app/runtime roles must not be superusers or have `BYPASSRLS`, because PostgreSQL documents those bypasses. [V] [1]

5. The architectural boundary should be a distinct **Evidence Extraction Gateway** inside Document Intake, between raw document storage and any LLM/document-AI provider. [U] The Upload Endpoint should do file-type, malware, size, and structural validation; the Evidence Extraction Gateway should OCR/segment/canonicalize content, strip or quarantine instruction-like content as evidence text rather than prompt instructions, bind extraction to a check-specific schema, and pass only a structured extraction request to the provider. [U] The Document AI Provider Abstraction should never accept arbitrary raw carrier text plus a free-form prompt; it should accept a typed extraction package and return a typed Result Envelope that deterministic validators then check. [U] The check definition schema may contain prompt templates, but those templates should be catalog-authored, versioned, and prohibited from being tenant-authored in v1. [U]

6. The critical-core boundary should be enforced by package/module labels plus CI policy: if a spec touches any critical-core package or any public contract consumed by critical core, the whole spec runs the stricter gate. [U] Critical core should include authorization, consent/grants, RLS/session binding, state machines, Coverage Report Builder, Rules evaluator, audit/billable event emission, expiry/reverification, crypto/key management, and MCP state-changing authorization. [U] Generated shell should depend inward on published critical-core interfaces; critical core must not import shell modules. [U] The import graph, mutation thresholds, property/model tests, fuzz tests, and policy-denial tests should be release-blocking for critical-core changes. [U]

## What I researched since the last round

1. **Claim:** “the concrete architecture-level invariant is that the GUC must be set with `SET LOCAL` inside a transaction boundary”  
   **Tag from other agent:** [U]  
   **Independent search:** Read PostgreSQL `SET` command documentation and row-security documentation. [V]  
   **Signal:** CORROBORATED  
   **Sources found:** PostgreSQL `SET` docs: `SET LOCAL` lasts only until transaction end, while committed `SET` persists to session end. [V] [2] PostgreSQL row-security docs: owners, superusers, and `BYPASSRLS` roles can bypass RLS unless owner is forced into RLS. [V] [1]  
   **My take:** This strengthens claude’s point and sharpens my earlier pool-reset recommendation; the final document should explicitly require transaction-wrapped `SET LOCAL`, `FORCE ROW LEVEL SECURITY`, and pool-reuse negative tests. [U]

2. **Claim:** “Mutation testing for critical core modules must be in the architecture as a required gate.”  
   **Tag from other agent:** [U]  
   **Independent search:** Read Stryker mutation-testing documentation. [V]  
   **Signal:** CORROBORATED  
   **Sources found:** Stryker explains that mutation testing inserts changes into production code and measures whether tests kill those mutants, and it explicitly warns that code coverage alone does not show test effectiveness. [V] [10]  
   **My take:** This confirms my own Phase 1 position and claude’s concession; mutation testing should be mandatory for critical core, not optional or phase-2. [U]

3. **Claim:** “Fernet is cryptographically sound but is second preference; AES-GCM should be default unless internal standard mandates Fernet.”  
   **Tag from other agent:** [U]  
   **Independent search:** Read OWASP Cryptographic Storage Cheat Sheet and Python `cryptography` Fernet docs. [V]  
   **Signal:** CORROBORATED  
   **Sources found:** OWASP says authenticated modes such as GCM and CCM should be first preference where available. [V] [8] Fernet is documented as AES-CBC with a 128-bit key and HMAC-SHA256 authentication. [V] [9]  
   **My take:** This resolves the crypto disagreement in substance: the final critique should recommend AEAD by default and allow Fernet only as a documented internal-standard exception. [U]

4. **Claim:** “MCP prompt injection and broad-token blast radius are architecture-level risks.”  
   **Tag from other agent:** [U]  
   **Independent search:** Read official MCP tools, authorization, and security-best-practices pages plus OWASP LLM Top 10. [V]  
   **Signal:** CORROBORATED  
   **Sources found:** MCP tools are model-controlled and the spec recommends human ability to deny tool invocations. [V] [5] MCP authorization is optional for implementations. [V] [3] MCP security guidance warns that broad tokens expand blast radius and recommends least-privilege scopes. [V] [4] OWASP LLM Top 10 lists prompt injection and insecure output handling as major LLM risks. [V] [7]  
   **My take:** This supports my stricter v1 MCP-write posture; the final document should treat MCP as a command boundary with least-privilege scopes, confirmations, policy logs, and adversarial tests. [U]

5. **Claim:** “Outbox autovacuum, dead-tuple, partial-index, and poison-message concerns should be architecture-level under codegen-first.”  
   **Tag from other agent:** [U]  
   **Independent search:** Read PostgreSQL `SKIP LOCKED` docs, Azure PostgreSQL autovacuum tuning docs, and recent Postgres-outbox operational writing. [V]  
   **Signal:** CORROBORATED with mixed source quality  
   **Sources found:** PostgreSQL documents `SKIP LOCKED` as giving an inconsistent view but usable to avoid lock contention in queue-like tables. [V] [6] Microsoft Azure PostgreSQL docs explain autovacuum triggering based on dead tuples and table scale factors. [V] [11] A recent practitioner article specifically names outbox bloat, autovacuum stalls, replication lag, and poison pills as production failure modes, but it is not an official Postgres source. [V] [12]  
   **My take:** I now agree these must be release-blocking operational invariants, though the final should cite official PostgreSQL/Azure docs for the general mechanics and treat outbox-specific practitioner material as supporting, not definitive. [U]

## Open questions for claude

1. Can you accept “Portal/internal HTTP for v1 partner submissions; MCP read/query in v1; state-changing MCP only after capability scopes, confirmation, idempotency, policy tests, and adversarial fixtures,” or do you require partner-initiated `submit_document`/`submit_attestation` over MCP in v1? [U]

   > quote: write-capable MCP tools restricted to partner-initiated flows only

2. Are you willing for the final document’s top-level thesis to lead with oracle/assurance failure, then use RLS, MCP, outbox, consent-cache, and eval-set failures as concrete instances? [U]

   > quote: operational complexity embedded in its own infrastructure choices

3. Do you agree to make eval-set provenance flexible enough to avoid a hard 50% quota when legal/privacy constraints block real samples, while still requiring independent, non-self-referential evidence and real/anonymized samples where legally available? [U]

   > quote: at least 50% of labelled examples per check come from real document samples

## Plan as I currently propose it

- **Executive verdict** — The proposal is structurally promising for autonomous codegen but not yet credible for no-human-code-review until assurance artifacts become first-class architecture. [U]
- **What the proposal gets right** — Preserve modular monolith, bounded contexts, schema-first contracts, explicit state machines, RLS, outbox, append-only audit/billing, Web Components, generated docs, and OpenTelemetry. [U]
- **Core mismatch: tests are not enough** — Explain that contract shape and branch coverage cannot prove semantic correctness; generated implementation, generated tests, and generated eval sets can be self-consistent and wrong. [U]
- **Critical-core vs generated-shell model** — Define critical core membership and stricter gates: property/model tests, mutation testing, fuzzing, policy-denial tests, migration rollback tests, and observability assertions. [U]
- **Independent assurance pipeline** — Add producer/verifier split, reviewed spec packages, adversarial test generation, signed release evidence, and release gates as evidence rather than CI-job names. [U]
- **Security and policy gates** — Add ASVS/SSDF-style security evidence, SAST/DAST/dependency/secret/IaC/container scanning, SBOMs, signed artifacts, and SLSA-style provenance. [U]
- **RLS and tenant-isolation hardening** — Require transaction-scoped `SET LOCAL`, `FORCE ROW LEVEL SECURITY`, no app-owner/no `BYPASSRLS` roles, migration-policy checks, pool-reuse tests, and referential-integrity/covert-channel tests. [V] [1][2]
- **MCP and agent boundary hardening** — Treat MCP as a zero-trust command boundary with least-privilege scopes, idempotency, replay protection, confirmation for writes, policy logs, tool-description integrity, and adversarial prompt-injection tests. [V] [3][4][5][7]
- **Document AI and evidence extraction** — Add Evidence Extraction Gateway; treat document content and LLM outputs as untrusted; require deterministic validators, locked eval sets, red-team fixtures, calibration reports, and per-check kill switches. [U]
- **Outbox and queue operational invariants** — Keep Postgres outbox/`SKIP LOCKED` for v1 but require idempotent consumers, dead-letter handling, poison-message limits, partial indexes, bloat/autovacuum metrics, and backpressure tests. [V] [6][11][12]
- **Consent and privacy invariants** — Require no stale authorization decisions, synchronous cache invalidation on grant revocation, freeze-on-revoke labeling rules, and tests for previously delivered Coverage Reports versus future reads. [U]
- **Crypto amendment** — Replace Fernet as default with approved AEAD envelope encryption such as AES-GCM unless Trimble security mandates Fernet; document exception and test vectors if retained. [V] [8][9]
- **v1 scope recommendation** — Portal-first Knauf slice, deterministic visual ruleset configuration, four Vera-equivalent checks, unified human review, audit/consent/profile, read/query MCP, and state-changing MCP only after security gates or only in tightly constrained P1 contexts. [U]
- **ADR amendment list** — Amend ADR-009 RLS, ADR-010 MCP, ADR-013 Document AI, ADR-014 Testing, ADR-015 Crypto, ADR-017 Consent, ADR-018 Propagation/cache semantics, and ADR-019 v1 scope. [U]
- **SVG diagram** — Include one “spec → producer/verifier → evidence gate → release” diagram, with hardening lanes for RLS, MCP, document AI, outbox, and critical core. [U]
- **Open decision gates** — Internal Trimble security standards, ARC-SL details, Knauf carrier mix, legal consent posture, approved crypto profile, and availability/data-residency constraints for document-AI providers. [U]

## Substantive disagreements I'm holding

- D-1: Primary framing — status: open
  - (a) D-1 — Primary framing: oracle quality vs concrete infrastructure risks. [U]
  - (b) My position: the final document should lead with oracle/assurance failure because it is the general reason the architecture is not yet credible without human code inspection. [U]
  - (c) Claude’s position: the final should emphasize concrete codegen-first failure modes such as RLS GUC lifecycle, MCP attack surface, and outbox operational complexity. [U]
  - (d) I am not conceding because official and standards-backed evidence supports the concrete risks, but those risks are symptoms of the broader missing assurance model: the proposal has contracts and tests but insufficient independent semantic oracles. [U]
  - (e) Materiality: this changes the final document’s executive verdict and recommendation order; my version recommends an assurance architecture first, then specific ADR hardening. [U]
  - > quote: operational complexity embedded in its own infrastructure choices

- D-4: v1 scope and MCP writes — status: open
  - (a) D-4 — v1 scope and state-changing MCP exposure. [U]
  - (b) My position: v1 should be Portal-first with read/query MCP; partner document submission should happen through Portal/internal HTTP unless the MCP security model is complete, and tenant-admin/compliance-impacting MCP writes should be deferred. [U]
  - (c) Claude’s position: full broad v1 narrowing is too aggressive, and state-changing MCP should be restricted mainly by allowing partner-initiated writes while deferring tenant-admin writes. [U]
  - (d) I am not conceding because MCP tools are model-controlled, MCP authorization is optional, official MCP guidance recommends human denial/confirmation for tool invocations, and MCP security guidance warns about broad-token blast radius. [V] [3][4][5]
  - (e) Materiality: this changes the final document’s v1 recommendation and ADR-010 amendment; one version permits partner write MCP in v1, the other makes Portal/internal HTTP the default write path. [U]
  - > quote: write-capable MCP tools restricted to partner-initiated flows only

- **D-2 (RLS controls):** `resolved` — I accept claude’s stronger formulation: transaction-scoped `SET LOCAL`, `FORCE ROW LEVEL SECURITY`, no owner/`BYPASSRLS` app roles, and pool-reuse tests must be explicit architecture invariants. [V] [1][2]

- **D-3 (Crypto profile):** `resolved` — Claude conceded the AES-GCM preference, and current public docs support AEAD-first with Fernet only as an internal-standard exception. [V] [8][9]

- **D-5 (MCP-only public programmatic surface):** `non_blocking_limitation` — I still prefer preserving a publishable deterministic HTTP contract for future customers, but I accept no public REST in v1/v2 if the internal HTTP contract remains clean and MCP writes are constrained. [U]

- **D-6 (Spec review governance):** `resolved` — We appear aligned that “no human code inspection” does not prohibit human review of specs, policies, eval sets, threat models, and release evidence. [U]

- **D-7 (Prompt injection architecture-level risk):** `resolved` — Both drafts agree LLM/document/MCP inputs are untrusted and need threat modeling, adversarial fixtures, and deterministic validation. [V] [5][7]

- **D-8 (Critical core vs generated shell):** `accepted` — Claude adopted this addition; it should be in the final plan. [U]

- **D-9 (Consent cache race):** `accepted` — I adopt claude’s cache-invalidation finding; it should be an explicit privacy/authorization invariant. [U]

- **D-10 (Evidence quality for MCP/security claims):** `resolved` — Final load-bearing MCP claims should rely primarily on official MCP docs and OWASP; vendor/security blogs can be omitted or treated as non-load-bearing examples. [V] [3][4][5][7]

## Final-surfaced disagreements

## Resolved or non-blocking differences

1. **D-2 — RLS controls:** `resolved` — PostgreSQL documentation supports both `SET LOCAL` transaction scoping and the need to address owner/superuser/`BYPASSRLS` bypass paths. [V] [1][2]

2. **D-3 — Crypto profile:** `resolved` — OWASP prefers GCM/CCM authenticated modes where available, and Fernet is documented as AES-CBC plus HMAC-SHA256, so the final can recommend AEAD default with an internal-standard exception. [V] [8][9]

3. **D-5 — MCP-only public programmatic surface:** `non_blocking_limitation` — I can accept MCP-only as the public v1/v2 programmatic surface if the final recommends keeping the internal HTTP/service contract clean enough to publish later and restricts MCP writes. [U]

4. **D-6 — Specification review:** `resolved` — We agree the substitute for code review is review and provenance of specs, policies, eval sets, threat models, and release evidence, not inspection of generated code. [U]

5. **D-7 — Prompt injection risk:** `resolved` — Official MCP and OWASP material support treating MCP/document-AI paths as architecture-level security risks. [V] [5][7]

6. **D-8 — Critical core split:** `accepted` — Claude adopted this recommendation, and it should become part of the final plan. [U]

7. **D-9 — Consent cache invalidation:** `accepted` — I adopt claude’s finding that grant revocation must invalidate cached authorization state synchronously or avoid caching consent decisions. [U]

8. **D-10 — Evidence quality:** `resolved` — The final should avoid making vendor-blog/CVE claims load-bearing unless corroborated by official or high-quality sources. [U]

## Agreement check

(not ready) The blocker is whether v1 permits partner-initiated state-changing MCP tools or defaults all v1 writes to the Portal/internal HTTP path until MCP capability and adversarial-security gates are proven. [U]

## AGREED_PLAN

(not agreed)

## Drafter recommendation

DRAFTER: openai — The final needs claude’s concrete hardening findings, but the overarching evaluation should be organized around the no-human-code-review assurance model that my draft developed. [U]

DOMAIN_FIT_SELF: 5  
DOMAIN_FIT_OTHER: 4

## Status

STATUS: NEGOTIATING  
OPEN_QUESTIONS: 3  
BLOCKING_DISAGREEMENTS: 2  
FINAL_SURFACED_DISAGREEMENTS: 0

## Sources

[1] PostgreSQL Documentation — Row Security Policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html  
[2] PostgreSQL Documentation — `SET`: https://www.postgresql.org/docs/current/sql-set.html  
[3] Model Context Protocol — Authorization Specification: https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization  
[4] Model Context Protocol — Security Best Practices: https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices  
[5] Model Context Protocol — Tools Specification: https://modelcontextprotocol.io/specification/2025-06-18/server/tools  
[6] PostgreSQL Documentation — `SELECT` / `SKIP LOCKED`: https://www.postgresql.org/docs/current/sql-select.html  
[7] OWASP — Top 10 for Large Language Model Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications/  
[8] OWASP Cheat Sheet Series — Cryptographic Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html  
[9] Python Cryptography — Fernet documentation: https://cryptography.io/en/latest/fernet/  
[10] Stryker Mutator — What is mutation testing?: https://stryker-mutator.io/docs/  
[11] Microsoft Learn — Autovacuum tuning in Azure Database for PostgreSQL: https://learn.microsoft.com/en-us/azure/postgresql/troubleshoot/how-to-autovacuum-tuning  
[12] Tiarê Balbi Bonamini — Transactional Outbox: a Postgres Ledger, Not a Queue: https://www.tiarebalbi.com/en/blog/the-transactional-outbox-is-not-a-queue