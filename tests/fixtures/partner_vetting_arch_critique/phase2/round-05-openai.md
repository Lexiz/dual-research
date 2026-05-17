## Summary

I accept claude’s round-4 clarification and the full canonical plan; my prior round accidentally emitted an empty `AGREED_PLAN`, so this is a repair turn. [U] I hold no remaining substantive disagreements and no open questions. [U] I agree that the final document should lead with oracle/assurance failure, incorporate claude’s concrete RLS/MCP/consent-cache findings, and use claude as drafter. [U]

## Answers to claude's open questions

(none)

## What I researched since the last round

Nothing new researched since the last round. [U]

## Open questions for claude

None.

## Plan as I currently propose it

- Use the canonical `AGREED_PLAN` block below as the final plan. [U]
- Keep `DRAFTER: claude`. [U]
- Surface no final disagreements. [U]

## Substantive disagreements I'm holding

(none)

## Resolved or non-blocking differences

1. **D-1 — Oracle quality framing:** `resolved` — Both agents agree the final critique should lead with oracle/assurance failure and treat RLS, MCP, outbox, consent-cache, crypto, and eval-set issues as concrete instances. [U]

2. **D-2 — RLS controls:** `resolved` — Both agents agree transaction-scoped `SET LOCAL`, `FORCE ROW LEVEL SECURITY`, no `BYPASSRLS` application roles, and pool-reuse negative tests should be architecture-level invariants. [U]

3. **D-3 — Crypto profile:** `resolved` — Both agents agree AES-GCM or equivalent AEAD should be the default target, with Fernet allowed only as a documented internal-standard exception. [U]

4. **D-4 — v1 MCP write-tool scope:** `resolved` — Both agents agree on P1-only partner `submit_document`/`submit_attestation` in v1, no P3 external-agent writes, and tenant-admin MCP writes deferred. [U]

5. **D-5 — MCP-only public programmatic surface:** `non_blocking_limitation` — I still prefer preserving a clean future-publishable HTTP contract, but this does not block agreement because public REST remains out of v1/v2 and MCP writes are constrained. [U]

6. **D-6 — Specification review governance:** `resolved` — Both agents agree no human code inspection can be paired with human review of specifications, policy matrices, eval provenance, threat models, and release evidence. [U]

7. **D-7 — Prompt injection architecture-level risk:** `resolved` — Both agents agree the Document AI Quarantine Layer and adversarial fixtures belong in the architecture, not just prompt-engineering design. [U]

8. **D-8 — Critical core / generated shell split:** `accepted` — Both agents agree stricter gates should apply to critical core modules and lighter gates can apply to shell/adapters. [U]

9. **D-9 — Consent cache invalidation:** `resolved` — Both agents agree grant revocation requires synchronous cache invalidation or equivalent no-stale-consent behavior. [U]

10. **D-10 — Evidence quality:** `resolved` — Both agents agree final load-bearing claims should rely on official MCP documentation, OWASP, PostgreSQL documentation, and other primary/high-quality sources rather than uncorroborated vendor-blog claims. [U]

## Agreement check

ENDORSEMENT: The agreed plan is better than my initial plan because it combines my assurance/oracle-quality framing with claude’s more precise architecture-level hardening requirements. [U]

MIND_CHANGED: The most important refinement was accepting claude’s P1-only partner-write MCP compromise instead of deferring all state-changing MCP submission paths. [U]

REMAINING_UNCERTAINTY: The final document should disclose unresolved internal dependencies, especially Trimble’s crypto standard, ARC-SL thresholds, Knauf carrier distribution, and Applied AI audit schema. [U]

STRONGEST_REMAINING_OBJECTION: The P1-only MCP write boundary may still be too permissive if ARC-mediated carrier sessions cannot provide a reliably human-confirmed Trimble-ID actor context. [U]

WHY_NON_BLOCKING: The plan makes that risk manageable by requiring UI confirmation, no P3 writes, no automatic terminal approval, and Phase-2 deferral for higher-risk MCP write tools. [U]

## AGREED_PLAN

```markdown
## Agreed Plan — Partner Vetting Architecture Critique

1. Title: Executive Verdict and Primary Constraint
   Key claims:
   - The architecture's typed contracts, modular monolith, explicit state machines, RLS, Postgres outbox, OTel, append-only audit/billing streams, web component family, and generated-documentation pipeline directly enable the autonomous codegen constraint by eliminating distributed-system failure modes and creating machine-verifiable boundaries.
   - Four architecture-level gaps undermine the constraint and require remediation before v1 ships: (A) oracle quality — generated code and tests can be self-consistent and wrong; (B) RLS GUC lifecycle fails under connection-pool reuse without SET LOCAL + FORCE RLS; (C) MCP and document-AI attack surface is unaddressed at the architecture level; (D) mutation testing is absent as a quality gate.
   - Two additional gaps require ADR amendments: (E) Fernet is OWASP second-preference; (F) consent cache invalidation race on grant revocation.

2. Title: What the Architecture Gets Right
   Key claims:
   - Typed contracts at every boundary (MCP tool schemas, internal OpenAPI, TypeScript interfaces, component prop schemas, provider interfaces) are the primary enabler for codegen-first development.
   - The modular monolith eliminates distributed-system failure modes that autonomous codegen cannot reliably handle.
   - Explicit state machines named and modeled prevent codegen from leaving domain invariants implicit.
   - RLS with default-deny posture is correct for tenant isolation.
   - Postgres outbox for at-least-once internal delivery is correct for v1 load.
   - OTel as vendor-neutral instrumentation is correct and swap-friendly.
   - Web Components as framework-agnostic on-the-wire contract are correct.
   - Lint rule inventory (no UPDATE on audit_events, no raw queries bypassing RLS, no PII in logs, no cross-context imports, every state-changing handler emits outbox row) is load-bearing.
   - Append-only audit and billable event streams are essential for codegen.

3. Title: Core Mismatch — Tests Are Not Enough (Oracle Quality)
   Key claims:
   - Generated code, generated tests, and generated eval sets produced from the same model family can be mutually consistent and collectively wrong; this is the primary architectural concern for no-human-review systems.
   - Shape contracts and branch coverage do not prove semantic correctness.
   - The architecture requires independently produced, adversarially oriented quality gates — not merely more of the same kind of tests the producer pipeline generates.

4. Title: Gap A — Independent Verifier Pipeline
   Key claims:
   - A separate verifier pipeline must generate adversarial tests from the same spec as the producer pipeline using a distinct execution context.
   - The verifier generates: mutation test cases, fuzz inputs for parsers and document metadata, property-test counterexamples for state machines, policy-denial test cases for every role x resource x action triple, migration rollback tests, and prompt-injection document fixtures for every AI-bearing check.
   - A signed evidence bundle is required per merge: unit, property, mutation, fuzz, contract, e2e, accessibility, SAST, dependency scan, secret scan, AI eval set, prompt-injection eval, RLS negative tests, policy-denial tests, migration rollback tests, and observability assertions.
   - Release is blocked without the complete signed evidence bundle.

5. Title: Gap A — Mutation Testing as a Required Gate
   Key claims:
   - Mutation score >= 80% required for general code; >= 90% for critical core modules.
   - Critical core membership: Authorization, Consent/Grants, RLS session binding, State machines, Coverage Report Builder, Rules Evaluator, Audit/Billable Event Emission, Expiry/Reverification, Crypto/Key Management, MCP state-changing authorization.
   - Branch coverage >= 90% is a necessary but insufficient hygiene metric.
   - The critical core / generated shell split is enforced by separate module labels, separate CI gate thresholds, and import-graph rules.

6. Title: Gap B — RLS GUC Lifecycle Mandatory Invariants
   Key claims:
   - Seven architecture-level invariants (not design-doc concerns): (a) FORCE ROW LEVEL SECURITY on all tenant-scoped tables; (b) no BYPASSRLS on the application role; (c) SET LOCAL for all GUC assignments inside explicit transaction boundaries; (d) connection pool in transaction mode, not session mode; (e) migration-time policy checks in schema migration CI; (f) referential-integrity leak tests asserting cross-tenant FK violations fail closed; (g) pool-reuse negative test asserting tenant B cannot see tenant A's rows after connection return.
   - These are codegen-pipeline invariants enforced by lint and integration tests, not prose assertions.

7. Title: Gap C — MCP and Document AI Attack Surface
   Key claims:
   - MCP is a command boundary, not a benign protocol adapter; official MCP specification states tools are model-controlled and recommends human ability to deny invocations.
   - A Document AI Quarantine Layer is required as a named component in Document Intake and Authentication: a separate tool-incapable model invocation context that reads carrier document bytes and returns only a typed extraction package; the planning model never reads raw carrier document content.
   - v1 MCP write scope: submit_document and submit_attestation available under P1/Trimble-ID actor context only (not P3), with UI confirmation, malware/MIME scan, idempotency keys, Evidence Extraction Gateway processing, adversarial document fixtures in the eval suite, and no automatic terminal approval from the MCP path.
   - Deferred to Phase 2: create_ruleset, grant_visibility, revoke_visibility, start_vetting_run via MCP, pending MCP security model completion.
   - Prompt-injection test fixtures required in the eval suite for every AI-bearing check.
   - Check definition schema prohibits tenant-authored prompt templates.

8. Title: Gap D — Eval Set Independence
   Key claims:
   - Eval sets must include a substantial proportion of real or independently anonymized document samples.
   - Synthetic examples must be produced by a model distinct from the production document AI provider.
   - Proportion targets: >= 40% real/anonymized for EU checks; >= 60% for non-EU country variants.
   - Where legal/privacy constraints prevent real samples, the gap must be disclosed in the check version release evidence and mitigated with independently sourced edge-case fixtures.

9. Title: Gap E — Cryptographic Posture Amendment
   Key claims:
   - AES-GCM or equivalent AEAD mode replaces Fernet as the architecture-specified default for envelope encryption, per OWASP Cryptographic Storage Cheat Sheet first preference (GCM/CCM preferred where available).
   - Fernet (AES-128-CBC + HMAC-SHA256) permitted only if an explicit Trimble internal cryptographic standard mandating it is cited in ADR-020.
   - Named open question R7 in Risks and Open Questions.
   - Per-profile envelope keys in Azure Key Vault and GDPR crypto-erasure mechanism are unchanged.

10. Title: Gap F — Consent Cache Invalidation Race
    Key claims:
    - On grant revocation, the Consent Manager must synchronously invalidate the (profile_id, tenant_id, section) Redis cache key before returning 200.
    - If Redis is unavailable at revocation time: DB write commits; audit event records cache_invalidation_failed: true; conservative negative-cache entry written on reconnect; alert fires.
    - The 5-minute Redis TTL is not acceptable as the sole freshness mechanism for grant revocation semantics.
    - This is an architecture-level invariant in the Consent Manager specification.

11. Title: Required ADR Amendments
    Key claims:
    - ADR-009 (RLS): add seven mandatory GUC-lifecycle and FORCE RLS invariants.
    - ADR-010 (MCP): add v1 write-tool scope restriction and per-tool capability scope requirement.
    - ADR-013 (Document AI): add Document AI Quarantine Layer as required architectural component.
    - ADR-014 (Testing): add mutation score thresholds, critical core / generated shell split, verifier pipeline requirement, evidence bundle release gate.
    - ADR-015 (Crypto): AES-GCM as default target; Fernet permitted with internal standard citation only.
    - ADR-017 (Consent): add synchronous cache invalidation on revocation as architecture-level invariant.
    - New ADR-021 (Mutation testing gate: critical core scope and minimum scores).
    - New ADR-022 (MCP write-tool v1 scope: partner-initiated P1-only; tenant-admin writes deferred to Phase 2).

12. Title: Surviving Open Questions
    Key claims:
    - Trimble internal cryptographic standard (Fernet vs AES-GCM): R7, pending internal security team confirmation.
    - ARC-SL degradation thresholds and per-tool configurability: R5, pending ARC integration documentation.
    - Knauf carrier population non-EU country distribution: R-Knauf, requires Knauf workshop.
    - Applied AI Safety and Enablements audit schema: R4, pending that team's standard publication.
    - Anthropic Claude regional availability in Azure West Europe: R-Claude-region, requires current API documentation.

13. Title: SVG Architecture Diagram
    Key claims:
    - Single diagram showing: spec feeds both producer agent and verifier agent; both feed evidence bundle gate; evidence bundle gate is release condition.
    - Hardening lanes annotated: RLS (SET LOCAL + FORCE RLS), MCP (quarantine layer + P1-only writes), document AI (typed extraction package), outbox (partial index + dead-letter + autovacuum alert), critical core (mutation gate threshold).

## Final-surfaced disagreements (canonical)

(none)
```

## Drafter recommendation

DRAFTER: claude (claude should draft because the agreed plan is an ADR-level amendment of an existing detailed architecture proposal, and claude’s formulation best preserves that structure.) [U]

DOMAIN_FIT_SELF: 5  
DOMAIN_FIT_OTHER: 5

## Status

STATUS: AGREED  
OPEN_QUESTIONS: 0  
BLOCKING_DISAGREEMENTS: 0  
FINAL_SURFACED_DISAGREEMENTS: 0