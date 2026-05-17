## Summary

I accept openai's clarification on the v1 MCP write boundary: P1-only for `submit_document`/`submit_attestation`, no P3 external-agent writes in v1, tenant-admin MCP writes deferred. This resolves the sole remaining blocking disagreement (D-4). I have no new open questions. I am ready to agree, endorse openai's drafter concession to claude, and adopt the AGREED_PLAN block I proposed in round 3 verbatim. The plan is now stable and I emit `STATUS: AGREED`.

---

## Answers to openai's open questions

**Q1 (Exact v1 MCP boundary: P1-only `submit_document`/`submit_attestation`, no P3, tenant-admin writes deferred):**

Yes, accepted. The exact v1 MCP write boundary is: `submit_document` and `submit_attestation` available under P1/ARC UI/known Trimble-ID actor context only; no P3 external-customer-agent write access in v1; `create_ruleset`, `grant_visibility`, `revoke_visibility`, and MCP-triggered `start_vetting_run` deferred to Phase 2 pending MCP security model completion. All partner submission writes in v1 gated by: UI confirmation, malware/MIME scan at Upload Endpoint, idempotency keys, Evidence Extraction Gateway processing, adversarial document fixtures in the eval suite, and no automatic terminal approval from the MCP path. This fully resolves D-4.

---

## What I researched since the last round**Corroboration: D-2 central RLS claim (openai's round 3 position)**

- Claim: "transaction-scoped `SET LOCAL` on tenant paths rather than a universal mandate for one pool mode"
- Tag from other agent: [U]
- Independent search: Searched PostgreSQL FORCE ROW LEVEL SECURITY SET LOCAL connection pooling PgBouncer transaction mode 2025
- Signal: CORROBORATED
- Sources found: [2-1,2-2,2-17,2-18] (rivestack.io, 3 weeks ago) — "always use `SET LOCAL` to set tenant context, never `SET`... `SET` persists for the lifetime of the session... In transaction mode, a session is shared across many clients." [4-4,4-5,4-6] (mvpfactory.io, March 2026) — "PgBouncer in transaction mode reuses connections across different clients. If you set `app.current_tenant` at the session level... the next request on that connection inherits the previous tenant's context. That's a data breach waiting to happen." [7-1,7-2] (planetscale.com, 4 weeks ago) — authoritative code example showing `BEGIN; SET LOCAL app.current_tenant = '1'; -- SET LOCAL ensures the setting is scoped to this transaction -- which is important when using connection pooling. SELECT * FROM orders; COMMIT;` [3-14] (dev.to, 3 weeks ago) — explicitly names both failure modes: "Not using `FORCE ROW LEVEL SECURITY` when the app connects as the table owner · Using `SET` instead of `SET LOCAL` with PgBouncer in transaction mode (tenant context leaks between clients)"
- My take: Fully corroborated from multiple independent, recently-published authoritative sources. The seven RLS invariants in the AGREED_PLAN are correct and concrete. The additional FK-referential-integrity bypass point from [5-3,5-4,5-7,5-8] (bytebase.com) — INSERT into child tables fails FK checks because RLS blocks SELECT on parent rows — is a seventh footgun the plan should retain.

---

## Open questions for openai

*(none)*

---

## Plan as I currently propose it

*(unchanged from round 3 — see AGREED_PLAN block below)*

---

## Substantive disagreements I'm holding

- **D-4 (v1 MCP write-tool scope):** `resolved` — OpenAI accepted P1-only `submit_document`/`submit_attestation` in v1 with UI confirmation, content scanning, idempotency, Evidence Extraction Gateway processing, adversarial fixtures, and no auto-terminal approval; no P3 external-agent writes; tenant-admin writes deferred. Converged in round 4.

- **D-1 (oracle quality framing):** `resolved` — Conceded to OpenAI in round 3; oracle quality leads, concrete infrastructure failures are instances.

- **D-2 (RLS controls):** `resolved` — Both agents agree on seven mandatory invariants including `SET LOCAL`, `FORCE ROW LEVEL SECURITY`, no `BYPASSRLS`, pool-reuse negative tests. Confirmed by independent sources this round and rounds 1–2.

- **D-3 (Fernet vs AES-GCM):** `resolved` — AES-GCM as architecture default; Fernet permitted only with Trimble internal standard citation. Agreed by both agents since round 2.

- **D-5 (MCP-only public programmatic surface):** `non_blocking_limitation` — Real difference, not material enough to block; no public REST in v1/v2 is per the brief; internal HTTP remains clean enough to publish later.

- **D-6 (specification review governance):** `resolved` — Both agents agree "no human code inspection" does not prohibit human review of specs, policies, eval sets, threat models, and release evidence.

- **D-7 (prompt injection architecture-level risk):** `resolved` — Both agents agree; Document AI Quarantine Layer is required architecture component.

- **D-8 (critical core / generated shell split):** `accepted` — Adopted from OpenAI in round 1; stable since.

- **D-9 (consent cache invalidation race):** `resolved` — Both agents agree synchronous Redis cache invalidation on revocation is architecture-level invariant.

- **D-10 (evidence quality for MCP/security claims):** `resolved` — Load-bearing claims rely on official MCP documentation, OWASP, and primary sources only.

---

## Final-surfaced disagreements

*(none)*

---

## Resolved or non-blocking differences

1. **D-1 (oracle quality framing):** `resolved` — Conceded to OpenAI in round 3; framing confirmed stable.
2. **D-2 (RLS controls):** `resolved` — Seven mandatory invariants confirmed by multiple independent authoritative sources across rounds 1–4.
3. **D-3 (Fernet vs AES-GCM):** `resolved` — OWASP first-preference confirmed; agreed since round 2.
4. **D-4 (v1 MCP write-tool scope):** `resolved` — Converged on P1-only partner writes; tenant-admin writes deferred; no P3 writes in v1.
5. **D-5 (MCP-only public programmatic surface):** `non_blocking_limitation` — Real preference difference; does not affect any v1 recommendation.
6. **D-6 (specification review governance):** `resolved` — Both agents aligned since round 2.
7. **D-7 (prompt injection architecture-level):** `resolved` — Document AI Quarantine Layer accepted by both agents; confirmed by dual-LLM research.
8. **D-8 (critical core / generated shell):** `accepted` — Stable since round 1.
9. **D-9 (consent cache invalidation):** `resolved` — Both agents aligned since round 2.
10. **D-10 (evidence quality):** `resolved` — Stable since round 2.

---

## Agreement check

`ENDORSEMENT:` The agreed plan is better than my initial Phase 1 proposal because it adds the independent verifier pipeline and oracle-quality framing (from OpenAI) as the organizing principle, alongside my specific technical constraints (SET LOCAL + FORCE RLS, Document AI Quarantine Layer, consent cache synchronous invalidation, adversarial eval fixture requirements), producing a document that is both architecturally coherent and operationally specific.

`MIND_CHANGED:` Mutation testing for critical core modules was the most important point I changed — absent from my Phase 1 entirely, confirmed by independent research as the essential quality gate distinguishing AI-generated code quality from branch-coverage theater.

`REMAINING_UNCERTAINTY:` Whether Trimble's internal cryptographic standard mandates Fernet specifically (versus AES-GCM) cannot be resolved from available documentation and must be named as open question R7 in the final document's Risks section.

`STRONGEST_REMAINING_OBJECTION:` The P1-only MCP write restriction for partner-initiated submissions may prevent ARC (Mario) from submitting documents on a carrier's behalf in a carrier-initiated chat session, since carrier-initiated ARC sessions could plausibly arrive via P2 rather than P1 depending on how Trimble ID token issuance works for the carrier-facing portal.

`WHY_NON_BLOCKING:` The P1 constraint is the correct conservative v1 posture for the reasons the MCP specification itself states; the P2/P1 ambiguity for carrier-initiated ARC sessions is a design-doc concern that does not require an architecture-level change, and Phase 2 can relax the constraint once capability scoping is proven.

---

## AGREED_PLAN

```
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

---

## Drafter recommendation

`DRAFTER: claude` — The final document requires surgical amendment of the existing detailed architecture proposal with its ADRs and C4 structure; the accumulated primary-source research depth (RLS GUC lifecycle, Document AI Quarantine Layer, consent cache race, MCP official specification) suits the amendment approach over a structural rewrite.

`DOMAIN_FIT_SELF: 4`
`DOMAIN_FIT_OTHER: 4`

---

## Status

`STATUS: AGREED`
`OPEN_QUESTIONS: 0`
`BLOCKING_DISAGREEMENTS: 0`
`FINAL_SURFACED_DISAGREEMENTS: 0`