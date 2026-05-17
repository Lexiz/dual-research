## Summary

This is round 5. OpenAI's round 4 was a repair turn acknowledging a formatting failure — their AGREED_PLAN block was empty, which is a parse error. I supplied the canonical AGREED_PLAN in my round 4 and emitted `STATUS: AGREED`. OpenAI emitted `STATUS: AGREED` but with an empty AGREED_PLAN block, which the orchestrator correctly flagged as a mismatch. The fix is straightforward: I repeat the canonical AGREED_PLAN block verbatim this round, emit `STATUS: AGREED`, and openai must do the same in their round 5 turn. No substantive position has changed; no new research is needed; no open questions remain. Proposing `DRAFTER: claude`.

## Answers to openai's open questions

(none)

## What I researched since the last round

Nothing new researched this round. The round 4 repair turn by OpenAI contained no new [U] claims requiring corroboration — it was a procedural acknowledgment only. All material claims were corroborated in prior rounds.

## Open questions for openai

(none)

## Plan as I currently propose it

Unchanged from round 3/4. See AGREED_PLAN block below.

## Substantive disagreements I'm holding

- **D-5 (MCP-only public programmatic surface):** `non_blocking_limitation` — Real preference difference; does not affect any v1 recommendation. OpenAI prefers preserving a clean future-publishable HTTP contract; the brief explicitly designates REST as a non-goal for v1/v2; the internal HTTP boundary remains clean enough to publish later if Phase 3 requires it.

All other D-N entries resolved in prior rounds.

## Final-surfaced disagreements

(none)

## Resolved or non-blocking differences

1. **D-1 (oracle quality framing):** `resolved` — Both agents agreed oracle quality leads the document with concrete infrastructure failures as instances. Resolved round 3.
2. **D-2 (mutation testing gate):** `resolved` — Confirmed by Stryker documentation, Meta FSE 2025 research, and independent practitioner sources. Mutation score ≥80% (90% critical core) adopted from OpenAI. Resolved round 1.
3. **D-3 (Fernet vs AES-GCM):** `resolved` — OWASP Cryptographic Storage Cheat Sheet confirms GCM/CCM first preference; Fernet (AES-128-CBC + HMAC-SHA256) is second preference. AES-GCM as default target; Fernet permitted with Trimble internal standard citation. Resolved round 2.
4. **D-4 (v1 MCP write-tool scope):** `resolved` — Converged on P1-only for partner-initiated MCP writes (`submit_document`, `submit_attestation`); no P3 external-agent writes in v1; tenant-admin writes (`create_ruleset`, `grant_visibility`, `revoke_visibility`, `start_vetting_run` via MCP) deferred to Phase 2. Resolved round 4.
5. **D-5 (MCP-only public programmatic surface):** `non_blocking_limitation` — Real preference difference; not material enough to block given brief explicitly designates REST as non-goal for v1/v2.
6. **D-6 (specification review governance):** `resolved` — Both agents agree "no human code inspection" does not prohibit human review of specs, policies, eval sets, threat models, and release evidence. Resolved round 2.
7. **D-7 (prompt injection architecture-level risk):** `resolved` — OWASP, official MCP documentation, and dual-LLM research all confirm Document AI Quarantine Layer is required architecture component. Resolved round 3.
8. **D-8 (critical core / generated shell split):** `accepted` — Adopted from OpenAI round 1; stable since.
9. **D-9 (consent cache invalidation race):** `resolved` — Both agents agree synchronous Redis cache invalidation on revocation is architecture-level invariant. Resolved round 2.
10. **D-10 (evidence quality for MCP/security claims):** `resolved` — Load-bearing claims rely on official MCP documentation, OWASP, and primary sources only. Resolved round 2.

## Agreement check

`ENDORSEMENT:` The agreed plan is better than my initial Phase 1 proposal because it combines the structural strengths I identified with OpenAI's critical addition of the independent verifier pipeline and the oracle-quality framing, making the final document coherent around the central no-human-review failure mode rather than a list of independent infrastructure risks.

`MIND_CHANGED:` Mutation testing for critical core modules was the most important point I changed — it was absent from my Phase 1 draft entirely, and research confirmed it as the essential quality gate distinguishing AI-generated code quality from branch-coverage theater.

`REMAINING_UNCERTAINTY:` Whether Trimble's internal cryptographic standard mandates Fernet specifically (versus AES-GCM) cannot be resolved from available documentation and must be named as open question R7 in the final document's Risks section.

`STRONGEST_REMAINING_OBJECTION:` The P1-only MCP write restriction for partner-initiated submissions may prevent ARC (Mario) from submitting documents on a carrier's behalf in a carrier-initiated chat session if those sessions arrive via P2 rather than P1 depending on Trimble ID token issuance for the carrier-facing portal.

`WHY_NON_BLOCKING:` The P1 constraint is the correct conservative v1 posture for the reasons the MCP specification itself states; the P2/P1 ambiguity for carrier-initiated ARC sessions is a design-doc concern that does not require an architecture-level change, and Phase 2 can relax the constraint once capability scoping is proven.

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

## Drafter recommendation

`DRAFTER: claude` — The final document requires surgical amendment of the existing detailed architecture proposal with its ADRs and C4 structure; the accumulated primary-source research depth (RLS GUC lifecycle, Document AI Quarantine Layer, consent cache race, MCP official specification) suits the amendment approach over a structural rewrite.

`DOMAIN_FIT_SELF: 4`
`DOMAIN_FIT_OTHER: 4`

## Status

`STATUS: AGREED`
`OPEN_QUESTIONS: 0`
`BLOCKING_DISAGREEMENTS: 0`
`FINAL_SURFACED_DISAGREEMENTS: 0`