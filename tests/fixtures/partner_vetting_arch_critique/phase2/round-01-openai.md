## Summary

My updated position is closer to claude’s on MCP and RLS risk, but I still think their draft underweights the core assurance problem: independently trustworthy specifications, tests, policies, and eval sets are the substitute for human code review. [U] The material diffs are MCP write-surface scope, RLS severity, outbox operational invariants, v1 narrowing, crypto posture, consent cache semantics, and whether infrastructure risks or oracle-quality risks should lead the final critique. [U] My proposed plan is a final document organized around “what enables codegen,” “what breaks no-review assurance,” and “required architectural changes,” with an explicit release-evidence model. [U] I recommend `openai` as drafter because my Phase 1 already covers the broader assurance framework, while claude’s strongest additions should be incorporated as hardening subsections. [U]

## Diff vs claude's Phase 1

1. **D-1 — Primary failure mode: oracle quality vs operational/adversarial infrastructure.** I said the fatal weakness is that generated code can pass generated tests while implementing the wrong behavior, so the architecture needs independent spec/test/policy/eval oracles. [U] Claude said the main mismatches are RLS, MCP attack surface, and Postgres outbox operational failure modes. [U] **Type:** framing. **Materiality:** substantive.

2. **D-2 — RLS risk severity and remedy.** I said PostgreSQL RLS is directionally correct but incomplete, requiring `FORCE ROW LEVEL SECURITY`, pool-reset tests, bypass-role controls, and negative tests. [U] Claude said RLS as the sole tenant isolation mechanism is the critical unaddressed failure mode, especially around session GUC lifecycle under connection pooling. [U] **Type:** interpretive. **Materiality:** substantive.

3. **D-3 — MCP v1 posture.** I recommended deferring write-capable MCP tools in v1 and keeping MCP as a zero-trust command boundary. [U] Claude argued MCP-only is right for v1 because ARC is unavoidable and the Portal provides deterministic access, while adding threat modeling and degraded-skill runbooks. [U] **Type:** scope / architecture. **Materiality:** substantive.

4. **D-4 — Outbox and `SKIP LOCKED` emphasis.** I treated Postgres outbox / queueing as acceptable for v1 if idempotency and duplicate-delivery properties are mandatory. [U] Claude emphasized autovacuum, table bloat, poison messages, lock pressure, and partial indexing as architecture-level requirements under no human operations review. [U] **Type:** scope. **Materiality:** substantive.

5. **D-5 — v1 scope reduction.** I recommended a narrower v1: portal-only, Knauf-only, four Vera-equivalent checks, deterministic ruleset configuration, and read-only or heavily constrained MCP. [U] Claude did not propose a comparably aggressive v1 cut; they accepted the standalone Portal and most core surfaces while adding hardening. [U] **Type:** scope. **Materiality:** substantive.

6. **D-6 — Cryptography posture.** I said the Fernet commitment is questionable and should be replaced by an approved AEAD envelope-encryption profile unless an internal standard mandates Fernet. [U] Claude did not materially address the Fernet/AES-CBC vs AEAD issue. [U] **Type:** missing content. **Materiality:** substantive.

7. **D-7 — Frontend framework importance.** I said Lit vs React is secondary to component contracts, accessibility tests, role-visibility tests, and embedding tests. [U] Claude said Lit is technically sound but React may win if team familiarity and React-heavy hosts dominate. [U] **Type:** interpretive. **Materiality:** minor.

8. **D-8 — Eval-set independence.** I said eval sets and test oracles must be independent of the implementation generator. [U] Claude added a concrete rule that at least 50% of labelled examples per check should come from real or anonymized documents rather than LLM-generated synthetic examples. [U] **Type:** scope. **Materiality:** already compatible; substantive as an addition.

9. **D-9 — Consent revocation cache race.** I did not call out Redis/cache invalidation on consent revocation. [U] Claude identified a race where stale cached grant state could remain visible after revocation. [U] **Type:** missing content. **Materiality:** substantive.

10. **D-10 — Source quality / unsupported specifics.** My Phase 1 leaned on official or standards sources for security and platform claims. [U] Claude cited several vendor blogs, Medium posts, and future/security-news claims for MCP CVEs and AI-code vulnerability percentages, some of which should not become final-document load-bearing evidence unless replaced by primary or higher-quality sources. [U] **Type:** factual / evidence quality. **Materiality:** substantive.

## Gaps I researched this round

1. **RLS mechanics for D-2.** I read PostgreSQL’s current row-security documentation and confirmed that superusers and roles with `BYPASSRLS` bypass RLS, table owners normally bypass RLS unless `ALTER TABLE ... FORCE ROW LEVEL SECURITY` is used, and referential-integrity checks bypass row security. [V] This strengthens my position that RLS is acceptable only with explicit owner/bypass-role constraints, forced RLS where applicable, migration checks, and connection-pool GUC reset tests. [U] [1] ([postgresql.org](https://www.postgresql.org/docs/current/ddl-rowsecurity.html?utm_source=openai))

2. **`SKIP LOCKED` / queue semantics for D-4.** PostgreSQL documents that `SKIP LOCKED` provides an inconsistent view and is unsuitable for general-purpose querying, but can be used to avoid lock contention with multiple consumers accessing a queue-like table. [V] This keeps my v1 acceptance of Postgres-backed queues, but moves me toward claude that queue/outbox operational invariants must be architecture-level under no human code inspection. [U] [2] ([postgresql.org](https://www.postgresql.org/docs/11/sql-select.html?utm_source=openai))

3. **MCP authorization and security posture for D-3.** The MCP authorization spec says authorization is optional for implementations and defines transport-level authorization for HTTP-based transports. [V] MCP’s own security best-practices documentation frames security considerations as complementary to authorization and warns about expanded blast radius from broad tokens. [V] This reinforces my view that MCP cannot be treated as a benign protocol adapter and that write-capable v1 tools need either deferral or a much stronger capability/security model. [U] [3][4] ([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization?utm_source=openai))

4. **LLM / agentic threat evidence for D-3 and D-8.** OWASP’s LLM Top 10 project identifies LLM-specific risks including prompt injection, insecure output handling, and excessive agency. [V] This supports both drafts’ concern that documents, tool outputs, and conversational workflow authoring must be treated as untrusted inputs. [U] [5] ([owasp.org](https://owasp.org/www-project-top-10-for-large-language-model-applications?utm_source=openai))

5. **Security verification standards for D-1 and D-10.** OWASP ASVS provides a basis for testing web application technical security controls and secure-development requirements. [V] NIST SSDF is a set of high-level secure software development practices intended to reduce vulnerabilities and mitigate exploitation impact. [V] This strengthens my recommendation that no-human-code-review releases need explicit ASVS/SSDF-derived evidence gates, not just ordinary CI. [U] [6][7] ([owasp.org](https://owasp.org/www-project-application-security-verification-standard/?utm_source=openai))

6. **Supply-chain provenance for D-1.** SLSA’s build track defines increasing levels of trustworthiness and completeness in package-artifact provenance. [V] This supports making provenance, signed artifacts, SBOMs, and dependency controls part of the release evidence bundle for AI-generated code. [U] [8] ([slsa.dev](https://slsa.dev/spec/v1.0/levels?utm_source=openai))

7. **Mutation and model-based/property testing for D-1.** Stryker’s documentation describes mutation testing as introducing changes to code and running tests to see whether the tests detect the changes. [V] fast-check documents model-based testing as defining potential actions against a system and checking whether model state permits those actions. [V] This reinforces my claim that branch coverage is insufficient and that mutation/property/model-based tests should be mandatory for critical core modules. [U] [9][10] ([stryker-mutator.io](https://stryker-mutator.io/docs/?utm_source=openai))

8. **Crypto posture for D-6.** OWASP’s Cryptographic Storage Cheat Sheet says AES with secure modes should be preferred and that authenticated modes such as GCM and CCM should be used as first preference where available. [V] The Python `cryptography` Fernet documentation states Fernet uses AES-CBC with a 128-bit key plus HMAC-SHA256 authentication. [V] This leaves my Phase 1 recommendation unchanged: do not hard-code Fernet unless Trimble security has mandated it; specify an approved AEAD envelope-encryption profile or cite the internal exception. [U] [11][12] ([cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html?utm_source=openai))

9. **Observability foundation for D-1.** OpenTelemetry documents itself as a vendor-neutral open-source observability framework for telemetry such as traces, metrics, and logs. [V] This supports both drafts’ view that OTel is a good instrumentation abstraction, but it also supports my addition that observability assertions should be tested as release evidence. [U] [13] ([opentelemetry.io](https://opentelemetry.io/docs/?utm_source=openai))

10. **Frontend framework for D-7.** React’s official React 19 announcement says React 19 adds full support for custom elements and passes all Custom Elements Everywhere tests. [V] Lit’s official site describes Lit as a simple library for building fast, lightweight web components. [V] This confirms D-7 is not central: either frontend can satisfy the architectural boundary if Custom Elements remain the external contract. [U] [14][15] ([react.dev](https://react.dev/blog/2024/12/05/react-19?utm_source=openai))

## Updated position

The final critique should keep the proposal’s modular monolith, schema-first contracts, explicit state machines, RLS, outbox, append-only audit, Web Components, and OpenTelemetry direction. [U] The final critique should say these choices enable autonomous codegen by reducing distributed-system ambiguity and creating machine-checkable seams. [U] The final critique should then state that these seams are not enough because the decisive risk is oracle quality: generated implementation, generated tests, and generated evals can agree with each other while being wrong. [U] Claude’s RLS GUC-lifecycle and consent-cache race findings are strong and should be adopted as concrete failure modes. [U] My research strengthened claude’s MCP concern because MCP authorization is optional in the spec and MCP’s own security guidance calls out broad-token blast-radius risks. [V] [3][4] ([modelcontextprotocol.io](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization?utm_source=openai)) I still disagree with claude that MCP-only is the right v1 posture if write-capable tools are exposed; I would allow MCP read/query tools first and require capability-scoped, idempotent, policy-logged, confirmation-gated write tools later. [U] I also retain the crypto objection because OWASP prefers authenticated modes such as GCM/CCM where available, while Fernet is AES-CBC plus HMAC rather than a modern AEAD construction. [V] [11][12] ([cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html?utm_source=openai)) The final recommendations should be framed as architecture changes, not generic process advice: executable domain models, policy-as-code, independent verifier pipeline, mutation/fuzz/security/supply-chain evidence gates, per-check kill switches, cache invalidation on consent revocation, and a narrower v1. [U]

## Open questions for claude

1. Can you distinguish which of your MCP claims are supported by official MCP documentation versus vendor/security-blog reporting, and which ones you want to keep as final-document load-bearing? [U]  
   > quote: The two CVEs that put this category on the map

2. Are you willing to converge on “MCP read/query tools in v1; write-capable MCP only behind capability scopes, idempotency, confirmation, and policy tests,” or do you still want all proposed v1 MCP tools available? [U]  
   > quote: MCP-only is the right call for v1

3. Should the final document lead with oracle/spec independence as the primary no-human-review failure mode, with RLS/MCP/outbox as concrete instances, or should it lead with the concrete infrastructure risks? [U]  
   > quote: fails it for adversarial-input hardening and for the operational complexity

4. What exact RLS controls do you think are mandatory beyond pool lifecycle tests: `FORCE ROW LEVEL SECURITY`, no `BYPASSRLS` app roles, migration-time policy checks, referential-integrity leak tests, or schema-per-tenant fallback triggers? [U]  
   > quote: the gap is not in the policy itself but in the connection-pool GUC lifecycle

5. Do you agree that the Fernet commitment should be changed or explicitly conditioned on an internal Trimble crypto standard? [U]  
   > after: 3.2 Where the architecture undermines autonomous codegen

6. Should outbox autovacuum/bloat/dead-letter/partial-index requirements be in the architecture document itself or in a referenced operational-invariants appendix that architecture makes release-blocking? [U]  
   > quote: These are not design-doc concerns — they are architecture-level operational invariants

7. Can you support an explicit v1 scope cut, and if not, which controls would make the full v1 scope acceptable without human code inspection? [U]  
   > quote: v1 (Knauf only, vetting not a real-time path)

8. Should we make “at least 50% real/anonymized labelled examples per check” a firm recommendation, or soften it to “eval sets must be independently sourced and include real/anonymized examples where legally available”? [U]  
   > quote: at least 50% of labelled examples per check come from real document samples

9. For the consent cache race, do you want to recommend strict no-cache for authorization/consent decisions, event-driven cache invalidation, or both? [U]  
   > quote: The Consent Manager must also invalidate the Redis cache entry

## Initial plan proposal

- **Executive verdict** — The architecture is structurally promising but not yet credible for no-human-code-review until assurance artifacts become first-class architecture. [U]
- **What enables autonomous codegen** — Modular monolith, schema-first contracts, explicit state machines, RLS, outbox, generated docs, and OTel reduce ambiguity and integration drift. [U]
- **Core mismatch: tests are not enough** — Shape contracts and branch coverage do not prove semantic correctness; independent spec/test/policy/eval oracles are required. [U]
- **Critical risk register** — RLS/GUC lifecycle, MCP command surface, document-AI prompt injection, outbox operational degradation, consent revocation caching, crypto profile, supply chain, and eval-set self-reference. [U]
- **Required architectural changes** — Independent verifier pipeline, executable domain models, policy-as-code, evidence bundle release gates, mutation/fuzz/security scans, SLSA/SSDF/ASVS mapping, and tested observability assertions. [U]
- **v1 scope recommendation** — Narrow v1 to portal-first, deterministic workflow configuration, four Vera checks, human-review fallback, strict audit/consent, and read-only or tightly gated MCP writes. [U]
- **Specific ADR amendments** — Amend ADR-009 RLS, ADR-010 MCP, ADR-013 Document AI, ADR-014 Testing, ADR-015 Crypto, ADR-017 Consent, ADR-019 v1 Portal scope. [U]
- **Operating model without code review** — Human review moves to specs, threat models, eval sets, policy matrices, evidence bundles, and release exceptions, not generated code diffs. [U]
- **SVG diagram** — Include a single “producer/verifier/evidence gate” diagram derived from my Phase 1, updated with claude’s RLS/MCP/outbox hardening lanes. [U]
- **Open questions / decision gates** — Internal Trimble security standards, ARC-SL details, Knauf carrier mix, legal consent posture, and approved cryptographic profile. [U]

## Drafter recommendation

- `DRAFTER: openai` — My draft already provides the broader no-human-review assurance architecture, and claude’s strongest findings can be incorporated as concrete risk cases and ADR amendments. [U]
- `DOMAIN_FIT_SELF: 5`
- `DOMAIN_FIT_OTHER: 4`

## Status

STATUS: NEGOTIATING  
OPEN_QUESTIONS: 9

## Sources

1. PostgreSQL Documentation — Row Security Policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
2. PostgreSQL Documentation — SELECT / `SKIP LOCKED`: https://www.postgresql.org/docs/11/sql-select.html
3. Model Context Protocol — Authorization Specification: https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization
4. Model Context Protocol — Security Best Practices: https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices
5. OWASP — Top 10 for Large Language Model Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications
6. OWASP — Application Security Verification Standard: https://owasp.org/www-project-application-security-verification-standard/
7. NIST — SP 800-218 Secure Software Development Framework: https://csrc.nist.gov/pubs/sp/800/218/final
8. SLSA — Security Levels: https://slsa.dev/spec/v1.0/levels
9. Stryker Mutator — What is mutation testing?: https://stryker-mutator.io/docs/
10. fast-check — Model-based testing: https://fast-check.dev/docs/advanced/model-based-testing/
11. OWASP Cheat Sheet Series — Cryptographic Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
12. Python Cryptography — Fernet documentation: https://cryptography.io/en/41.0.5/fernet/
13. OpenTelemetry Documentation: https://opentelemetry.io/docs/
14. React — React 19 announcement: https://react.dev/blog/2024/12/05/react-19
15. Lit official site: https://lit.dev/