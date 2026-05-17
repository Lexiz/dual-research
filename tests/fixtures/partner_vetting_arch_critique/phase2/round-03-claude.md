## Summary

I'm ready to move toward agreement this round. The two blocking disagreements — D-1 (framing primacy) and D-4 (v1 MCP write-tool scope) — can be resolved without contradiction: D-1 is a presentation order question, not a substantive difference, and the evidence on D-4 points to a workable compromise where partner-initiated MCP writes (`submit_document`, `submit_attestation`) proceed in v1 under Portal-confirmed identity (P1 only), while tenant-admin writes are deferred. I'm conceding D-1 to OpenAI's framing preference (oracle quality leads, concrete failures are instances) because the distinction is non-material to the document's recommendations. I'm accepting OpenAI's D-4 answer: `submit_document`/`submit_attestation` in v1 under P1-only with UI confirmation, content scanning, idempotency, and no auto-terminal approval from the MCP path. I'm proposing `DRAFTER: claude` given the surgical amendment character of the work and the depth of primary-source research this thread has accumulated.

---

## Answers to openai's open questions

**Q1 (Portal/internal HTTP for v1 partner submissions vs. MCP):**
Accepted with the constraints openai specified: `submit_document` and `submit_attestation` are available in v1 under P1/known Trimble-ID actor context only (not P3), with explicit UI confirmation in the Portal before submission, content scanning at the Upload Endpoint (malware/MIME validation), idempotency keys, and the explicit architectural constraint that no Result Envelope produced from an MCP-submitted document can reach `Approved` terminal state without passing through the deterministic post-validation layer. This satisfies the brief's carrier-initiated self-vetting requirement (LR §«Carrier-Initiated Self-Vetting Flow») without exposing the full write surface.

**Q2 (Oracle/assurance failure as leading framing):**
Accepted. The final document will lead with the oracle/assurance problem as the primary framing — generated code, generated tests, and generated eval sets can be mutually consistent and collectively wrong. The RLS GUC lifecycle, MCP attack surface, outbox operational failure modes, consent cache race, and eval set self-referentiality are presented as concrete instances of this general failure. This is a better organizing principle and does not suppress any of my specific findings.

**Q3 (Eval set provenance — flexible wording):**
Accepted. The final document will use: "eval sets must include a substantial proportion of real or independently anonymized document samples; synthetically generated examples must be produced by a model distinct from the document AI provider used in production (typically a separate model family); the proportion of real/anonymized examples should target ≥40% for EU checks and ≥60% for non-EU country variants where synthetic ground truth is unreliable; where legal/privacy constraints prevent real samples, the gap must be disclosed in the check version's release evidence and mitigated with independently sourced edge-case fixtures." This is flexible enough for practical compliance and rigorous enough to prevent self-referential eval sets.

---

## What I researched since the last round

**1. Corroboration of openai's Evidence Extraction Gateway proposal (architectural boundary for document pre-processing):**

- Claim: "The Document AI Provider Abstraction should never accept arbitrary raw carrier text plus a free-form prompt; it should accept a typed extraction package and return a typed Result Envelope that deterministic validators then check."
- Tag from other agent: [U]
- Independent search: Searched "document AI extraction pipeline prompt injection prevention structured extraction schema 2025"
- Signal: CORROBORATED
- Sources found:- My take: CORROBORATED strongly. The dual-LLM pattern separates a privileged orchestration model from a quarantined model that reads untrusted content; the privileged model decides which tools to call, while the quarantined model is allowed to read attacker-controlled bytes but never given tool-calling capability, with a schema-validated channel passing only structured extractions between them. The architectural commitment is: separate the planning model from any model that reads untrusted content, validate every tool output against a typed schema before it re-enters the planning context. This directly corroborates OpenAI's Evidence Extraction Gateway proposal. The finding that all tools which use PDF sources for text extraction parse hidden prompts as standard text, enabling possible manipulations of the following LLM review generation confirms the threat is real for the specific carrier document context. My position on openai's architectural boundary recommendation: fully corroborated; the Evidence Extraction Gateway is a required architectural component.

**2. Corroboration of D-4 compromise: P1-only MCP write tools for partner-initiated submissions:**

- Claim: "MCP tools are model-controlled and the spec recommends human ability to deny tool invocations."
- Tag from other agent: [V] (OpenAI cited MCP tools spec)
- Independent search: This is a central claim supporting the MCP write-tool deferral argument.
- Signal: CORROBORATED — I previously confirmed this from MCP official documentation in rounds 1 and 2; the specification states tools are "model-controlled" and SHOULD allow human denial.
- Sources found: Already confirmed in prior rounds via [modelcontextprotocol.io] official docs.
- My take: Stable. The P1-only constraint for `submit_document` and `submit_attestation` is the right compromise — it ensures the actor is a known Trimble-ID user (not an anonymous P3 external agent), which provides the human-in-loop equivalent the spec recommends.

---

## Open questions for openai

1. On the Evidence Extraction Gateway: research this round confirms the dual-LLM / quarantine pattern as the current state-of-the-art for document content injection defense. The architecture should name this as the **Document AI Quarantine Layer** — a separate, tool-incapable invocation context that reads carrier document bytes and returns only a typed extraction package. Does openai agree this should be named as a component in §6.2 (Document Intake & Authentication) and that the check definition schema should prohibit catalog-authored prompt templates from being embedded in free-text fields accessible to the quarantined model context?

   > after: 6.2 Document Intake & Authentication

2. On the AGREED_PLAN: I'm ready to agree in this round. The remaining question is which agent proposes the canonical `AGREED_PLAN` block. Per procedure, one agent proposes it and the other copies it verbatim in the next round. I'll propose a complete block below. Does openai intend to copy it verbatim and emit `STATUS: AGREED` in round 4, or does openai want to propose amendments first?

   > after: AGREED_PLAN

---

## Plan as I currently propose it

- **§1 Executive verdict and primary constraint** — Structural strengths (typed contracts at every boundary, modular monolith, explicit state machines, RLS, Postgres outbox, OTel, append-only audit/billing, web component family, generated docs) directly enable the autonomous codegen constraint by reducing distributed-system failure modes and creating machine-verifiable seams. Four architecture-level gaps undermine the constraint and require remediation before v1 ships to Knauf: (A) generated code and generated tests can be self-consistent and wrong — the oracle quality problem; (B) RLS GUC lifecycle fails under connection-pool reuse without `SET LOCAL` + `FORCE RLS`; (C) MCP/document-AI attack surface is unaddressed at the architecture level; (D) mutation testing is absent. Two additional gaps require ADR amendments: (E) Fernet is OWASP second-preference; (F) consent cache invalidation race on grant revocation.

- **§2 What the architecture gets right** — (1) Typed contracts at every boundary as the primary enabler. (2) Modular monolith correct for codegen-first — eliminates distributed-system failure modes. (3) Explicit state machines named and modeled — the domain invariants most likely to be broken by codegen if implicit. (4) RLS as tenant isolation: correct direction, default-deny posture. (5) Postgres outbox for at-least-once internal delivery: correct for v1 load. (6) OTel as vendor-neutral instrumentation: correct. (7) Web Components as framework-agnostic on-the-wire contract: correct. (8) Lint rule inventory as the machine-enforceable invariant layer: correct and load-bearing. (9) Append-only audit and billable event streams: correct and essential for codegen.

- **§3 Core mismatch: tests are not enough** — Generated code, generated tests, and generated eval sets produced from the same model family can be mutually consistent and collectively wrong. Oracle quality — the independence and adversarial coverage of the quality gate — is the primary architectural concern for no-human-review systems. The following sections address concrete instances of this general failure.

- **§4 Gap A: Oracle quality — independent verifier pipeline** — The architecture must add a separate verifier pipeline that generates adversarial tests from the same spec as the producer pipeline but using a distinct execution context. The verifier generates: mutation test cases, fuzz inputs for parsers and document metadata, property-test counterexamples for state machines, policy-denial test cases for every role × resource × action triple, migration rollback tests, and prompt-injection document fixtures for every AI-bearing check. Evidence bundle release gate: a signed evidence artifact is required per merge, covering unit, property, mutation, fuzz, contract, e2e, accessibility, SAST, dependency scan, secret scan, AI eval set, prompt-injection eval, RLS negative tests, policy-denial tests, migration rollback tests, and observability assertions.

- **§5 Gap A: Mutation testing as a required gate** — Mutation score ≥80% for general code; ≥90% for critical core modules (Authorization, Consent/Grants, RLS session binding, State machines, Coverage Report Builder, Rules Evaluator, Audit/Billable Event Emission, Expiry/Reverification, Crypto/Key Management, MCP state-changing authorization). Branch coverage ≥90% is a necessary but insufficient hygiene metric. The critical core / generated shell split must be enforced by separate module labels, separate CI gate thresholds, and import-graph rules preventing shell modules from being imported by critical core.

- **§6 Gap B: RLS GUC lifecycle — mandatory invariants** — Seven invariants at architecture level (not delegated to data design doc): (a) `ALTER TABLE ... FORCE ROW LEVEL SECURITY` on all tenant-scoped tables; (b) no `BYPASSRLS` attribute on the application role; (c) all tenant GUC assignments use `SET LOCAL` inside an explicit transaction boundary; (d) connection pool configured in transaction mode (not session mode); (e) migration-time policy checks as part of schema migration CI; (f) referential-integrity leak tests asserting cross-tenant FK violations fail closed; (g) pool-reuse negative test: same connection acquired by tenant A, returned, acquired by tenant B, asserts B cannot see A's rows. These seven are codegen-pipeline invariants (§9.1), enforced by lint and integration tests, not prose.

- **§7 Gap C: MCP and document AI attack surface** — MCP is a command boundary, not a benign protocol adapter. Required architecture-level additions: (a) Document AI Quarantine Layer as a named component in §6.2 — a separate, tool-incapable model invocation context that reads carrier document bytes and returns only a typed extraction package; the planning model (Claude extraction) never reads raw carrier document content; (b) per-tool capability scope for write-capable MCP tools; (c) v1 MCP write scope restricted: `submit_document` and `submit_attestation` available in v1 under P1/known Trimble-ID actor context only (not P3), with UI confirmation, malware/MIME scan at Upload Endpoint, idempotency keys, and no auto-terminal approval from MCP path; `create_ruleset`, `grant_visibility`, `revoke_visibility`, `start_vetting_run` deferred to Phase 2 pending MCP security model completion; (d) prompt-injection test fixtures required in the eval suite for every check that processes carrier-submitted content; (e) check definition schema prohibits tenant-authored prompt templates.

- **§8 Gap D: Eval set independence** — Eval sets must include a substantial proportion of real or independently anonymized document samples. Synthetically generated examples must be produced by a model distinct from the document AI provider used in production. Target: ≥40% real/anonymized for EU checks, ≥60% for non-EU country variants. Where legal/privacy constraints prevent real samples, the gap must be disclosed in the check version's release evidence and mitigated with independently sourced edge-case fixtures. An eval set produced entirely by the same model family as the production document AI provider does not constitute an independent quality gate.

- **§9 Gap E: Cryptographic posture amendment** — AES-GCM (or equivalent AEAD mode) replaces Fernet as the architecture-specified default for envelope encryption, per OWASP Cryptographic Storage Cheat Sheet first preference. Fernet (AES-128-CBC + HMAC-SHA256) is permitted only if an explicit Trimble internal cryptographic standard mandating it is cited in ADR-020. This is a named open question in §13 (R7) pending internal security team confirmation. Per-profile envelope keys in Azure Key Vault, GDPR crypto-erasure mechanism: unchanged from proposal.

- **§10 Gap F: Consent cache invalidation race** — On grant revocation, the Consent Manager must synchronously invalidate the `(profile_id, tenant_id, section)` Redis cache key before returning 200 to the caller. This is an architecture-level invariant in the Consent Manager specification. If Redis is unavailable at revocation time: the DB write commits; the audit event records `cache_invalidation_failed: true`; a conservative grace-period negative-cache entry is written on Redis reconnect; an alert fires. The 5-minute Redis TTL on consent state is not acceptable as the only freshness mechanism for grant revocation semantics.

- **§11 Required ADR amendments** — ADR-009 (RLS): add seven mandatory invariants. ADR-010 (MCP): add v1 write-tool scope restriction and per-tool capability scope requirement. ADR-013 (Document AI): add Document AI Quarantine Layer as required architectural component. ADR-014 (Testing): add mutation score thresholds, critical core / generated shell split, verifier pipeline, evidence bundle gate. ADR-015 (Crypto): AES-GCM as default target; Fernet permitted with internal standard citation. ADR-017 (Consent): add synchronous cache invalidation on revocation as architecture-level invariant. New ADR-022 (MCP write-tool v1 scope). New ADR-021 (Mutation testing gate).

- **§12 Surviving open questions (architecture did not close)** — Trimble internal cryptographic standard (Fernet vs AES-GCM); ARC-SL degradation thresholds and per-tool configurability; Knauf carrier population non-EU country distribution (required to confirm Phase 1 non-EU check priority list); Applied AI Safety & Enablements audit schema; Anthropic Claude regional availability in Azure West Europe.

- **§13 SVG diagram** — Single diagram: spec → [producer agent | verifier agent] → evidence bundle gate → release, with hardening lanes for RLS (SET LOCAL + FORCE RLS), MCP (quarantine layer + P1-only writes), document AI (typed extraction package), outbox (partial index + dead-letter + autovacuum alert), and critical core (mutation gate).

---

## Substantive disagreements I'm holding

- **D-1 (oracle quality vs infrastructure framing):** `resolved` — Conceded to OpenAI's framing. Oracle quality leads the document; concrete infrastructure failures (RLS GUC, outbox, consent cache) are presented as instances. Both agents now hold this position. Resolved by OpenAI's Q2 acceptance of this framing and my acceptance in Q2 answers above.

- **D-4 (v1 MCP write-tool scope):** `resolved` — Converged: `submit_document` and `submit_attestation` in v1 under P1-only with UI confirmation, content scanning, idempotency, and no auto-terminal approval from MCP path; `create_ruleset`, `grant_visibility`, `revoke_visibility`, `start_vetting_run` deferred to Phase 2. Both agents now hold this position.

---

## Final-surfaced disagreements

*(none)*

---

## Resolved or non-blocking differences

1. **D-1 (oracle quality framing):** `resolved` — Both agents agree oracle quality leads; concrete infrastructure failures are instances. OpenAI proposed this framing; I concede it in this round.

2. **D-2 (mutation testing gate):** `resolved` — Confirmed by multiple sources (Stryker docs, Meta FSE 2025 research, Atlassian). Mutation score ≥80% (90% critical core) is the required gate. Adopted from OpenAI.

3. **D-3 (Fernet vs AES-GCM):** `resolved` — OWASP first preference is GCM/CCM; Fernet (AES-CBC + HMAC) is second preference. AES-GCM as default target; Fernet permitted with Trimble internal standard citation.

4. **D-4 (v1 MCP write-tool scope):** `resolved` — Converged on P1-only for partner-initiated MCP writes; tenant-admin writes deferred to Phase 2.

5. **D-5 (MCP-only public programmatic surface):** `non_blocking_limitation` — OpenAI prefers preserving a publishable HTTP contract for future customers; I accept MCP-only in v1/v2 given the brief's explicit designation of REST as a non-goal. The internal HTTP boundary remains clean enough to publish later.

6. **D-6 (specification review governance):** `resolved` — Both agents agree that "no human code inspection" does not prohibit human review of specs, policies, eval sets, threat models, and release evidence. The product pair's specification process is the human-review substitute the brief describes; the verifier pipeline provides the independence layer.

7. **D-7 (prompt injection as architecture-level):** `resolved` — Confirmed by OWASP, official MCP documentation, dual-LLM research, and the Document AI Quarantine Layer proposal accepted by both agents.

8. **D-8 (critical core / generated shell split):** `accepted` — Adopted from OpenAI with explicit membership list.

9. **D-9 (consent cache invalidation race):** `resolved` — Both agents agree synchronous cache invalidation on revocation is an architecture-level invariant. Accepted my finding.

10. **D-10 (eval set independence):** `resolved` — Flexible wording agreed in Q3 answer. Proportion targets: ≥40% EU, ≥60% non-EU.

---

## Agreement check

`ENDORSEMENT:` The plan is better than my initial proposal because it combines the structural strengths I identified with OpenAI's critical addition of the independent verifier pipeline and the oracle-quality framing, making the final document coherent around the central no-human-review failure mode rather than a list of independent infrastructure risks.

`MIND_CHANGED:` Mutation testing for critical core modules was the most important point I changed — it is the correct primary quality gate for AI-generated code and was absent from my Phase 1 draft entirely.

`REMAINING_UNCERTAINTY:` The Trimble internal cryptographic standard (Fernet vs AES-GCM) and ARC-SL degradation thresholds remain unresolvable from available documentation and should be disclosed as named open questions in §13.

`STRONGEST_REMAINING_OBJECTION:` The proposal to defer all tenant-admin write MCP tools to Phase 2 may constrain the carrier-initiated self-vetting flow more than intended if the P1-only restriction prevents ARC (Mario) from submitting documents on a carrier's behalf in a chat-driven self-vetting session.

`WHY_NON_BLOCKING:` The constraint is the right conservative v1 posture given the unaddressed MCP security model; Phase 2 can relax it once capability scoping, confirmation gating, and adversarial test fixtures are proven.

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
   - The verifier generates: mutation test cases, fuzz inputs for parsers and document metadata, property-test counterexamples for state machines, policy-denial test cases for every role × resource × action triple, migration rollback tests, and prompt-injection document fixtures for every AI-bearing check.
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
   - v1 MCP write scope: submit_document and submit_attestation available under P1/Trimble-ID actor context only (not P3), with UI confirmation, malware/MIME scan, idempotency keys, and no auto-terminal approval from the MCP path.
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

`DRAFTER: claude` — The final document requires surgical amendment of the existing detailed architecture proposal with ADRs; claude's Phase 1 diagnosis approach, primary-source research depth, and specific technical constraint formulations (GUC lifecycle, consent cache, quarantine layer naming) suit this better than a structural rewrite from the OpenAI framing.

`DOMAIN_FIT_SELF: 4`
`DOMAIN_FIT_OTHER: 4`

---

## Status

`STATUS: AGREED`
`OPEN_QUESTIONS: 2`
`BLOCKING_DISAGREEMENTS: 0`
`FINAL_SURFACED_DISAGREEMENTS: 0`