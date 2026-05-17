## Summary

I now accept claude’s narrower v1 compromise if it is stated as **P1/ARC UI only for partner document/attestation submission**, with P3 external-agent write access deferred and tenant-admin MCP writes deferred. [U] I am no longer holding the framing dispute as blocking: the final can lead with oracle/assurance failure and then make RLS, MCP, outbox, consent-cache, crypto, and eval-set failures the concrete proof points. [U] I concede `DRAFTER: claude` because claude’s latest plan incorporates the assurance architecture I wanted while preserving the proposal-amendment structure needed for this architecture review. [U] I am still negotiating only to confirm the exact MCP v1 write boundary. [U]

## Answers to claude's open questions

1. Yes on `SET LOCAL`, `FORCE ROW LEVEL SECURITY`, and non-`BYPASSRLS` application roles as architecture-level invariants. [V] [1][2] I would slightly reword “transaction-mode connection pooling” as: every tenant-scoped database operation must run inside an explicit transaction that sets tenant/role GUCs using `SET LOCAL`; statement pooling is prohibited for these paths; session pooling is allowed only if the same `SET LOCAL` transaction invariant and pool-reuse negative tests hold. [U] PostgreSQL documents that `SET LOCAL` lasts only to transaction end, while `SET` persists to session end after commit. [V] [1] PostgreSQL also documents table-owner, superuser, and `BYPASSRLS` bypass behavior, with `FORCE ROW LEVEL SECURITY` available to subject owners to policies. [V] [2]

2. I accept claude’s distinction between partner-initiated submission writes and tenant-admin/compliance-configuration writes, but only with a tighter v1 boundary: `submit_document` and `submit_attestation` may be available in v1 only under P1 / ARC UI / known Trimble-ID actor context, with human-visible confirmation, idempotency keys, malware/content scanning, Evidence Extraction Gateway processing, adversarial document fixtures, and no automatic terminal approval from that path. [U] I do **not** accept P3 external-customer-agent `submit_document`/`submit_attestation` in v1. [U] I agree `create_ruleset`, `grant_visibility`, `revoke_visibility`, and MCP-triggered tenant-admin `start_vetting_run` should be deferred until the MCP capability, confirmation, policy-test, and adversarial-security model is complete. [U]

3. I do not require a fourth party, but I do require a named non-code review path for the artifacts that replace code review: specs, policy matrices, threat models, eval-set provenance, migration plans, and release evidence. [U] The product pair can own product/domain review; the skills and infrastructure/self-healing pairs can own assurance, security, and operability review where they are accountable for those controls. [U] If the same person/agent can write the spec, generate the tests, approve the evidence, and release without independent artifact review, the final should call that self-referential and not credible under the no-code-inspection constraint. [U]

4. The verifier should be a separate logical pipeline with separate artifacts, policy, and release gate authority. [U] It may execute inside the same CI platform for practicality, but it must not be just a stage that the producer pipeline can rewrite or mark optional. [U] The release artifact should include a signed evidence bundle from both producer and verifier paths. [U]

5. Yes. [V] [7][8] The final should specify AES-GCM or another approved AEAD envelope-encryption profile as the target, and permit Fernet only if an explicit Trimble internal cryptographic standard mandates it. [U] OWASP says authenticated modes such as GCM and CCM should be first preference where available. [V] [7] Fernet is documented as AES-CBC with a 128-bit key plus HMAC-SHA256 authentication. [V] [8] The unresolved item is not whether Fernet is broken; it is whether Trimble has an internal standard that intentionally chooses it despite AEAD-first public guidance. [U]

## What I researched since the last round

1. **Claim:** “`SET LOCAL` inside a transaction boundary is the correct pattern.”  
   **Tag from other agent:** [V]  
   **Independent search:** Read PostgreSQL `SET` documentation and row-security documentation. [V]  
   **Signal:** CORROBORATED  
   **Sources found:** PostgreSQL `SET` docs — authoritative; distinguishes `SET` session persistence from `SET LOCAL` transaction scoping. [V] [1] PostgreSQL row-security docs — authoritative; documents owner/superuser/`BYPASSRLS` bypass and `FORCE ROW LEVEL SECURITY`. [V] [2]  
   **My take:** This fully resolves the RLS implementation disagreement in claude’s favor, with my wording nuance that the invariant is transaction-scoped `SET LOCAL` on tenant paths rather than a universal mandate for one pool mode. [U]

2. **Claim:** “`submit_document` and `submit_attestation` available in v1.”  
   **Tag from other agent:** [U]  
   **Independent search:** Read official MCP tools, authorization, and security-best-practices documentation. [V]  
   **Signal:** PARTIALLY CORROBORATED  
   **Sources found:** MCP tools are model-controlled and the spec recommends human ability to deny tool invocations. [V] [3] MCP authorization is optional. [V] [4] MCP security guidance recommends progressive, least-privilege scopes and warns about broad-token blast radius. [V] [5]  
   **My take:** The sources support allowing only tightly constrained write tools, not unconstrained write-capable MCP. [U] I can accept P1 partner submission writes with confirmation and least privilege, but not P3 external-agent document submission in v1. [U]

3. **Claim:** “Mutation testing requirements are now confirmed.”  
   **Tag from other agent:** [V]  
   **Independent search:** Read Stryker mutation-testing documentation. [V]  
   **Signal:** CORROBORATED  
   **Sources found:** Stryker docs — tool documentation, not an academic standard, but directly explains why code coverage alone is insufficient and how mutation testing detects weak tests. [V] [9]  
   **My take:** This remains a core release-gate recommendation: branch coverage is hygiene; mutation score is evidence that tests catch plausible wrong behavior. [U]

4. **Claim:** “Prompt injection as architecture-level risk.”  
   **Tag from other agent:** [V]  
   **Independent search:** Read OWASP LLM Top 10 plus official MCP tools/security pages. [V]  
   **Signal:** CORROBORATED  
   **Sources found:** OWASP LLM Top 10 — recognized security project; prompt injection can cause unauthorized access and compromised decision-making. [V] [6] MCP tools page — official spec; model-controlled tools and human denial recommendation. [V] [3]  
   **My take:** This supports an architecture-level Evidence Extraction Gateway and MCP zero-trust boundary; it should not be relegated to prompt engineering in a design doc. [U]

5. **Claim:** “AES-GCM as target, Fernet only if internal standard.”  
   **Tag from other agent:** [V]  
   **Independent search:** Read OWASP Cryptographic Storage Cheat Sheet and Python `cryptography` Fernet docs. [V]  
   **Signal:** CORROBORATED  
   **Sources found:** OWASP Cryptographic Storage — recognized application-security guidance; GCM/CCM first preference. [V] [7] Python `cryptography` Fernet docs — primary implementation documentation; Fernet uses AES-CBC plus HMAC-SHA256. [V] [8]  
   **My take:** The final should recommend AEAD default and make Fernet a documented internal-standard exception, not the default architectural commitment. [U]

## Open questions for claude

1. Can you accept the exact v1 MCP boundary: P1-only `submit_document`/`submit_attestation`; no P3 external-agent write tools; tenant-admin MCP writes deferred; all partner submission writes gated by confirmation, idempotency, scanning, Evidence Extraction Gateway processing, and no automatic terminal approval? [U]

   > quote: `submit_document` and `submit_attestation` available in v1

## Plan as I currently propose it

- **Executive verdict** — The proposal is structurally strong for autonomous codegen but not yet credible for no-human-code-review until assurance artifacts become first-class architecture. [U]
- **What the proposal gets right** — Preserve modular monolith, bounded contexts, schema-first contracts, explicit state machines, RLS, outbox, append-only audit/billing, Web Components, generated docs, and OpenTelemetry. [U]
- **Core mismatch: tests are not enough** — Explain that generated implementation, generated tests, and generated eval sets can be self-consistent and wrong; independent semantic oracles are required. [U]
- **Critical-core vs generated-shell model** — Define critical core membership: authorization, consent/grants, RLS/session binding, state machines, rules evaluation, Coverage Report Builder, audit/billable event emission, expiry/reverification, crypto/key management, and MCP state-changing authorization. [U]
- **Independent assurance pipeline** — Add producer/verifier split, reviewed spec packages, adversarial test generation, signed evidence bundles, and release gates as evidence rather than CI job names. [U]
- **Security and supply-chain gates** — Add ASVS/SSDF-style evidence, SAST, DAST, dependency scanning, secret scanning, IaC scanning, container scanning, SBOMs, signed artifacts, and SLSA-style provenance. [U]
- **RLS and tenant-isolation hardening** — Require transaction-scoped `SET LOCAL`, `FORCE ROW LEVEL SECURITY`, no owner/`BYPASSRLS` app roles, migration-policy checks, pool-reuse tests, referential-integrity tests, and covert-channel review. [V] [1][2]
- **MCP and agent boundary hardening** — Treat MCP as a zero-trust command boundary with least-privilege scopes, idempotency, replay protection, confirmation for writes, policy logs, tool-description integrity, and adversarial prompt-injection tests. [V] [3][4][5][6]
- **Document AI and evidence extraction** — Add an Evidence Extraction Gateway; treat carrier documents and LLM outputs as untrusted; require deterministic validators, locked eval sets, real/anonymized examples where legally available, red-team fixtures, calibration reports, and per-check kill switches. [U]
- **Outbox and queue operational invariants** — Keep Postgres outbox/`SKIP LOCKED` for v1 but require idempotent consumers, dead-letter handling, poison-message limits, partial indexes, bloat/autovacuum metrics, and backpressure tests. [U]
- **Consent and privacy invariants** — Require no stale authorization decisions, synchronous cache invalidation on grant revocation or no caching for grant decisions, freeze-on-revoke labeling rules, and tests separating prior Coverage Reports from future reads. [U]
- **Crypto amendment** — Replace Fernet default with approved AEAD envelope encryption such as AES-GCM unless Trimble security mandates Fernet; if retained, document the exception and test vectors. [V] [7][8]
- **v1 scope recommendation** — Portal-first Knauf slice; deterministic visual ruleset configuration; four Vera-equivalent checks; unified human review; audit, consent, profile, roles, and billable event capture; MCP read/query tools; P1-only partner submission writes if gated; no P3 write tools; tenant-admin MCP writes deferred. [U]
- **ADR amendment list** — Amend ADR-009 RLS, ADR-010 MCP, ADR-013 Document AI, ADR-014 Testing, ADR-015 Crypto, ADR-017 Consent, ADR-018 Propagation/cache semantics, and ADR-019 v1 scope; add ADRs for verifier pipeline, critical core, and mutation gates. [U]
- **SVG diagram** — Include one “spec package → producer pipeline + verifier pipeline → signed evidence gate → release” diagram with lanes for critical core, RLS, MCP, document AI, outbox, and consent. [U]
- **Open decision gates** — Internal Trimble security standards, ARC-SL details, Knauf carrier mix, legal consent posture, approved crypto profile, and document-AI provider availability/data-residency constraints. [U]

## Substantive disagreements I'm holding

- D-4: v1 MCP write boundary — status: open
  - (a) D-4 — v1 scope and state-changing MCP exposure. [U]
  - (b) My position: v1 can include P1-only partner `submit_document`/`submit_attestation` over MCP if gated as above, but P3 external-agent writes and tenant-admin/compliance-impacting MCP writes should be deferred. [U]
  - (c) Claude’s position: partner-initiated `submit_document` and `submit_attestation` should be available in v1, while tenant-admin write tools should be deferred; claude has not yet explicitly distinguished P1 from P3 for those partner writes. [U]
  - (d) I am not yet conceding P3 partner writes because MCP tools are model-controlled, MCP authorization is optional, the MCP tools spec recommends human ability to deny tool invocations, and MCP security guidance recommends least-privilege scopes due to broad-token blast-radius risks. [V] [3][4][5]
  - (e) Materiality: this changes the final v1 recommendation and ADR-010 amendment by determining whether external customer agents can mutate profile/document state in v1. [U]
  - > quote: `submit_document` and `submit_attestation` available in v1

- **D-1 (oracle quality vs infrastructure framing):** `resolved` — The final should lead with oracle/assurance failure and then use RLS, MCP, outbox, consent-cache, crypto, and eval-set findings as concrete failure modes. [U]

- **D-2 (RLS controls):** `resolved` — PostgreSQL documentation supports `SET LOCAL` transaction scoping and the need to handle owner/superuser/`BYPASSRLS` bypass paths. [V] [1][2]

- **D-3 (Crypto profile):** `resolved` — OWASP’s AEAD-first guidance and Fernet’s documented AES-CBC+HMAC construction support AEAD default with a documented internal-standard exception. [V] [7][8]

- **D-5 (MCP-only public programmatic surface):** `non_blocking_limitation` — I still prefer preserving a clean future-publishable HTTP contract, but this does not block if public REST remains out of v1/v2 and MCP writes are tightly constrained. [U]

- **D-6 (Specification review governance):** `resolved` — We agree no human code inspection can be paired with human review of specs, policy, threat models, eval provenance, and release evidence. [U]

- **D-7 (Prompt injection architecture-level risk):** `resolved` — OWASP and official MCP material support treating MCP/document-AI paths as architecture-level security risks. [V] [3][6]

- **D-8 (Critical core / generated shell split):** `accepted` — Claude adopted the split, and the plan now includes stricter gates for critical core modules. [U]

- **D-9 (Consent cache invalidation):** `accepted` — I adopt claude’s finding; the final should require synchronous invalidation or no caching for authorization/consent decisions. [U]

- **D-10 (Evidence quality for MCP/security claims):** `resolved` — Final load-bearing MCP claims should rely primarily on official MCP docs and OWASP, not uncorroborated vendor-blog CVE claims. [V] [3][4][5][6]

## Resolved or non-blocking differences

1. **D-1 — Primary framing:** `resolved` — The final can lead with oracle/assurance failure while still treating claude’s RLS/MCP/outbox findings as the concrete architecture-level proof points. [U]

2. **D-2 — RLS controls:** `resolved` — `SET LOCAL`, forced RLS, and role-bypass constraints are supported by PostgreSQL documentation and should be architecture-level invariants. [V] [1][2]

3. **D-3 — Crypto profile:** `resolved` — AEAD should be the default; Fernet can remain only as a documented internal-standard exception. [V] [7][8]

4. **D-5 — MCP-only public programmatic surface:** `non_blocking_limitation` — No public REST in v1/v2 is acceptable if MCP writes are constrained and the internal service contract remains clean enough to publish later if Phase 3 requires it. [U]

5. **D-6 — Specification review governance:** `resolved` — Human review moves to non-code artifacts and release evidence, not generated diffs. [U]

6. **D-7 — Prompt injection:** `resolved` — Official MCP and OWASP sources support architecture-level controls for model-controlled tools and untrusted LLM inputs. [V] [3][6]

7. **D-8 — Critical core split:** `accepted` — The plan includes critical-core membership and stronger gates. [U]

8. **D-9 — Consent cache invalidation:** `accepted` — The plan includes synchronous revocation invalidation or no caching for consent decisions. [U]

9. **D-10 — Evidence quality:** `resolved` — Vendor-blog and unconfirmed CVE material will not be load-bearing in the final. [U]

## Agreement check

(not ready) The only blocker is whether claude accepts the exact v1 MCP boundary: P1-only partner submission writes, no P3 external-agent writes, and tenant-admin MCP writes deferred. [U]

## AGREED_PLAN

(not agreed)

## Drafter recommendation

DRAFTER: claude — Claude’s latest plan has incorporated the broader assurance framework while retaining the proposal-amendment structure and detailed ADR-level fit needed for the final critique. [U]

DOMAIN_FIT_SELF: 5  
DOMAIN_FIT_OTHER: 5

## Status

STATUS: NEGOTIATING  
OPEN_QUESTIONS: 1  
BLOCKING_DISAGREEMENTS: 1  
FINAL_SURFACED_DISAGREEMENTS: 0

## Sources

[1] PostgreSQL Documentation — `SET`. ([postgresql.org](https://www.postgresql.org/docs/current/sql-set.html))  
[2] PostgreSQL Documentation — Row Security Policies. ([postgresql.org](https://www.postgresql.org/docs/current/ddl-rowsecurity.html))  
[3] Model Context Protocol — Tools Specification. ([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-06-18/server/tools))  
[4] Model Context Protocol — Authorization Specification. ([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization))  
[5] Model Context Protocol — Security Best Practices. ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices))  
[6] OWASP — Top 10 for Large Language Model Applications. ([owasp.org](https://owasp.org/www-project-top-10-for-large-language-model-applications/))  
[7] OWASP Cheat Sheet Series — Cryptographic Storage Cheat Sheet. ([cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html))  
[8] Python `cryptography` — Fernet documentation. ([cryptography.io](https://cryptography.io/en/latest/fernet/))  
[9] Stryker Mutator — What is mutation testing? ([stryker-mutator.io](https://stryker-mutator.io/docs/))