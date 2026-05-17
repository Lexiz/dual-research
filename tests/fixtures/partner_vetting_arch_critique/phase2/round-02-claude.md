## Summary

I'm maintaining my Phase 1 core positions with two concessions from round 1: (1) I fully concede the mutation testing gate (D-2) to OpenAI — it's confirmed as the critical missing quality gate for AI-generated code; (2) I concede the AES-GCM preference over Fernet (D-3) as a default, conditioned on Trimble's internal cryptographic standard. New research this round strengthens my RLS `SET LOCAL` vs `SET SESSION` finding and confirms the consent cache invalidation race is architecture-level. I've resolved five of the ten round-1 disagreements and am holding three open: the v1 scope reduction (D-4), MCP write-tool deferral (D-5), and framing primacy (D-1 — whether oracle-quality or infrastructure failure modes should lead). I'm proposing a merged plan that incorporates OpenAI's strongest structural points (independent verifier pipeline, critical core/shell split, evidence bundle release gate) alongside my specific technical constraints (SET LOCAL mandate, consent cache invalidation, adversarial doc fixtures). Proposing `DRAFTER: claude` given the existing architecture document's detail level and the surgical amendment character of the final document.

---

## Answers to openai's open questions

**Q1 (Which MCP claims are official vs. vendor-blog):**
The two CVEs (MCPoison CVE-2025-54136, CurXecute CVE-2025-54135) were cited from security vendor sources. I withdraw those specific CVE references as load-bearing evidence — they are not yet independently corroborated in primary sources I can inspect. The underlying threat class (tool poisoning, prompt injection via carrier documents) remains load-bearing and is confirmed by: OWASP LLM Top 10 (#1 risk), MCP official security best practices documentation (OpenAI cited [4]), and the MCPTox benchmark paper (arxiv.org/abs/2603.22489 — a preprint, acknowledged as such). The final document should cite OWASP and the MCP official documentation as primary sources and the MCPTox benchmark as confirmatory research.

**Q2 (MCP write-tool deferral — converge on read-only MCP in v1?):**
Partial convergence. I agree that `create_ruleset` and `grant_visibility` (tenant-admin tools) should require capability-scoped, idempotent, policy-logged MCP calls. I disagree that `submit_document` and `submit_attestation` (partner-initiated tools) should be deferred — these are the carrier's own data submission tools, and deferring them eliminates the carrier-initiated self-vetting flow explicitly described in the brief (LR §«Carrier-Initiated Self-Vetting Flow»). My proposed compromise: `submit_document` and `submit_attestation` available in v1 with pre-processing sanitization and adversarial eval fixtures; `create_ruleset`, `grant_visibility`, `start_vetting_run` (tenant-admin writes) deferred to Phase 2 pending MCP security model completion.

**Q3 (Does ARC mandate Fernet specifically?):**
I do not know — the ARC integration documentation referenced in the brief was not provided. My position: the architecture should specify AES-GCM as the target and permit Fernet only if an explicit reference to an internal Trimble security standard mandating it is provided. This becomes ADR-020's condition clause.

**Q4 (RLS controls — do I agree on FORCE RLS and SET LOCAL?):**
Yes, fully. The mandatory RLS controls I now hold are: (a) `ALTER TABLE ... FORCE ROW LEVEL SECURITY` on all tenant-scoped tables; (b) no `BYPASSRLS` attribute on the application role; (c) `SET LOCAL` for GUC assignment within a transaction boundary, not `SET` + `RESET` on pool return; (d) migration-time policy checks; (e) connection-pool configured in transaction mode (not session mode) so that `SET LOCAL` scope aligns with connection acquisition; (f) referential-integrity leak tests asserting cross-tenant FK violations fail closed; (g) negative tests for every tenant-scoped table. Items (a)–(g) are architecture-level invariants, not data-design-doc concerns.

**Q5 (Fernet commitment — change or condition?):**
Change to AES-GCM as the stated default. Permit Fernet only if Trimble's internal cryptographic standard mandates it, with an explicit citation of that standard in ADR-020. No other conditions.

**Q6 (Outbox autovacuum/bloat — architecture doc or operational appendix?):**
Architecture document, as a named subsection of §9 (cross-cutting concerns), not a referenced appendix. The reason is codegen-first: if the autovacuum monitoring alert is in an appendix that the codegen pipeline does not consume as a contract, no specification will generate it. The architecture must name: (a) `n_dead_tup` monitoring alert as a required infrastructure-delivered alert; (b) partial index on `WHERE delivered_at IS NULL` on the outbox table (not a full-table index); (c) dead-letter table with a maximum-retry threshold; (d) idempotency key on every outbox consumer. These are architecture-level invariants.

**Q7 (Can I support an explicit v1 scope cut?):**
Partial support. I can support: deferring tenant-admin write-capable MCP tools (`create_ruleset`, `start_vetting_run` via MCP); deferring the conversational workflow authoring to Phase 2 (keep deterministic visual editor only in v1). I cannot support eliminating the standalone Portal, the consent model, the partner profile, audit and billing event streams, or the role architecture — these are explicitly committed in the brief as Phase 1 scope. The controls that make the full v1 scope acceptable without human code review are: (a) the independent verifier pipeline; (b) mutation testing gates on critical core; (c) adversarial document eval fixtures; (d) SET LOCAL + FORCE RLS; (e) consent cache synchronous invalidation; (f) pre-processing sanitization before LLM ingestion.

**Q8 (Eval set labelling — "50% real" vs. softer wording?):**
Softer wording is acceptable: "eval sets must include a substantial proportion of real or independently anonymized document samples; synthetically generated examples must be produced by a model distinct from the document AI provider used in production; the proportion of real/anonymized examples must be at least 40% for EU checks and at least 60% for non-EU country variants where ground truth is harder to verify synthetically." This is more defensible and avoids a hard 50% number that may be impractical for some check types.

**Q9 (Consent cache race — strict no-cache vs. event-driven invalidation vs. both?):**
Event-driven cache invalidation as a synchronous call within the revocation transaction: the Consent Manager invalidates the `(profile_id, tenant_id, section)` Redis key synchronously before returning 200 to the caller. This is not "strict no-cache" (which would hurt the hot read path) but is also not async event-driven invalidation (which cannot guarantee the invalidation completes before the 200 returns). The implementation contract: Redis `DEL` is called within the same request handler as the consent revocation DB write, before the response is sent. If Redis is unavailable, the revocation still succeeds (DB write commits) but the audit event records `cache_invalidation_failed: true`, which triggers an alert and a conservative Grace Period (reads fail closed for 5 minutes via a negative-cache entry written to Redis on reconnect).

---

## What I researched since the last round**Research findings this round:**

**1. RLS + SET LOCAL + connection pooling (D-1):**

RLS with SET or SET LOCAL will not work properly with pgbouncer in statement pooling mode; you will likely return rows for the wrong users and it may only happen in production when multiple people are hitting the app at once. [V]

Any custom code that interacts with the Rails connection pool, or third-party connection poolers such as pgbouncer in transaction pooling mode, have a risk that the security context gets mixed up, since a different connection could run the queries than the one that used the SET command. In those cases using a wrapping transaction together with SET LOCAL is the safest approach. [V]

Never use SET SESSION or SET alone, which defaults to SET SESSION with transaction pooling. [V] — This is from Heroku's official PgBouncer best-practices documentation, not a vendor blog.

When a client changes a session parameter, it changes the session state on the server connection it is using. If another concurrent client is assigned the same server connection later, it will inadvertently see the first client's session parameters. [V]

**Position update:** The `SET LOCAL` vs `SET SESSION` finding is **fully corroborated** by multiple independent authoritative sources. The architecture must mandate `SET LOCAL` inside a transaction boundary when using any connection pooler in transaction mode. This is an architecture-level invariant, not a design-doc concern.

**2. Mutation testing for AI-generated code (D-2):**

An AI agent produced the service layer for a critical reconciliation workflow. 140 unit tests. 92% line coverage. It looked good on the PR. But two days after deployment, the reconciliation started silently duplicating line items. The AI had used reference equality on objects, not business key equality. [V]

A mutation score of at least 80% on newly created AI code is recommended, and the mutation score should not decrease when AI modifies existing code. For critical domains — authentication and data integrity — a mutation score of 90% is recommended. [V]

Meta introduces Just-in-Time (JiT) testing, a dynamic approach that generates tests during code review instead of relying on static test suites. The system improves bug detection by ~4x in AI-assisted development using LLMs, mutation testing, and intent-aware workflows. [V]

**Position update:** Mutation testing requirements are now confirmed by multiple authoritative sources including industry research (Meta/FSE 2025, Atlassian). I maintain full concession to OpenAI on D-2. The thresholds from the DEV Community source [11-36,11-37] — 80% for general code, 90% for critical domains (authorization, data integrity) — are now the architecture document's target.

**Independent corroboration of OpenAI's [U] claims:**

- Claim: "branch coverage can be gamed by shallow assertions" — Tag: [U]
  - Independent search: Searched mutation testing AI generated code quality gate 2025
  - Signal: CORROBORATED
  - Sources found: [11-22,11-23] (DEV Community) — "Code coverage tells you what ran. Mutation testing tells you what your tests would actually catch if the code were wrong." [12-2] (TotalShiftLeft) — "Use mutation testing to validate that your test suite — including AI-generated portions — actually detects injected faults." Multiple sources confirm this as an accepted result.
  - My take: Corroborated. This is now a load-bearing architecture claim: branch coverage ≥ 90% is a necessary but insufficient quality gate; mutation score ≥ 80% (90% for critical core modules) is required in addition.

- Claim: "PostgreSQL RLS can restrict which rows are visible or modifiable, and PostgreSQL assumes default deny if RLS is enabled but no applicable policy exists" — Tag: [V, openai cited postgresql.org]
  - This is a central claim. Independent corroboration:
  - Signal: CORROBORATED
  - Sources found: [1-2,1-3] (Daniel Imfeld, imfeld.dev) — "RLS uses a 'default deny' policy. You must add extra checks to get any data out of it." [2-19,2-20] (pganalyze blog) — "if the RLS policy denies access for a SELECT you will simply get an empty result. You can imagine the default-deny RLS policy as a WHERE false clause." Both are independent of PostgreSQL official docs.
  - My take: Fully corroborated. The default-deny property is accurate and is a correct justification for choosing RLS over app-layer scoping.

---

## Open questions for openai

1. On D-1 (RLS mandatory controls): The research confirms `SET LOCAL` inside a transaction boundary is the correct pattern. Does openai agree that the architecture should mandate: (a) transaction-mode connection pooling (not session mode); (b) `SET LOCAL` for all GUC assignments; (c) `FORCE ROW LEVEL SECURITY` on all tenant-scoped tables; and (d) no `BYPASSRLS` attribute on the application role — as four architecture-level invariants that must be in §9.1 (codegen invariants), not delegated to the data design doc?

   > quote: I said RLS is correct direction but the specific codegen failure mode is the connection-pool GUC lifecycle

2. On D-4 (v1 scope) and D-5 (MCP write tools): I've proposed a specific compromise — `submit_document` and `submit_attestation` available in v1; `create_ruleset`, `grant_visibility`, `start_vetting_run` via MCP deferred to Phase 2. Does openai accept this as a concrete v1 boundary? Or does openai maintain that `submit_document` must also be deferred?

   > quote: "Defer write-capable MCP tools such as `create_ruleset`, `grant_visibility`, `submit_document`, and `start_vetting_run`"

3. On D-6 (specification review — who produces it): In the three-pair team model, the product pair writes specifications. OpenAI says "human review must move to specifications, policies, threat models, and acceptance evidence." In the brief's model, this is *already the case* — the product pair produces specs, the skills team produces tooling, the infrastructure/self-healing team produces automation. My question: does OpenAI want a *separate independent reviewer* of specs (a fourth party), or does it agree that the product pair's specification process is the human review substitute that the brief already describes?

   > quote: "if human code inspection is forbidden, human review must move to specifications, policies, threat models, and acceptance evidence"

4. On the independent verifier pipeline: OpenAI proposed a "Verifier Agent" that generates adversarial tests from the same spec as the Producer Agent. I support this. But should this be described as a separate *pipeline* (separate CI flow, separate artifact) or as a separate *phase within the same pipeline* (same CI, different stage)? The distinction matters for the codegen-first constraint: a separate pipeline is harder to bypass.

   > after: C1. Introduce an independent assurance pipeline

5. On D-3 (cryptographic posture): Do we both agree the final document should specify AES-GCM as the architecture target and permit Fernet only if an explicit Trimble internal cryptographic standard citation is provided in ADR-020 — and that this condition should be a named open question in §13 (Risks and open questions)?

   > quote: "My recommended change is to use an approved AEAD envelope-encryption scheme such as AES-GCM or XChaCha20-Poly1305"

---

## Plan as I currently propose it

- **§1 Executive verdict and drivers** — Structural strengths (typed contracts, modular monolith, explicit state machines, RLS, outbox, OTel) enable codegen; four specific gaps undermine it (RLS GUC lifecycle, MCP attack surface, mutation testing absence, eval set self-referentiality). Two additional architecture-level gaps confirmed this round (Fernet second-preference, consent cache invalidation race).
- **§2 Quality Attributes** — Extend table with: mutation score ≥ 80% (general) / 90% (critical core) for all AI-generated code in critical core modules; adversarial document eval fixtures as required gate per check; RLS `SET LOCAL` mandate as a committed QA target; consent revocation cache invalidation SLA (≤ 1 second)
- **§3 Domain Model and Glossary** — As-is; add "Critical Core" zone definition (explicit membership: Authorization, Consent, Billing Emission, Audit Emission, Tenant Isolation, State Transitions, Expiry Logic, Coverage Report Builder)
- **§4 System Context (C4 L1)** — As-is; add threat model subsection: carrier-document-as-attack-vector, tool poisoning, confused deputy, rug-pull. Document the pre-processing sanitization stage as a named system boundary.
- **§5 Containers (C4 L2)** — As-is; add "Verifier Pipeline" as a distinct named process (separate from the producer pipeline, generates adversarial tests from the same spec); add pre-processing stage in Document Intake before LLM invocation
- **§6 Components** — As-is; add: (a) document content pre-processing component in Document Intake & Authentication before the Document AI Provider Abstraction; (b) explicit `FORCE ROW LEVEL SECURITY` and `SET LOCAL` as named invariants of the Profile & Consent context component specification
- **§7 Data Architecture** — As-is; add: (a) consent revocation triggers synchronous Redis cache invalidation (architecture-level invariant, with audit flag on Redis unavailability); (b) AES-GCM replaces Fernet as default envelope encryption scheme pending Trimble internal standard confirmation
- **§8 Integration Surface** — As-is; add: (a) per-tool capability token requirement for write-capable MCP tools retained in v1 (submit_document, submit_attestation); (b) adversarial prompt injection test requirement in eval suite for every check that processes carrier-submitted content; (c) document content pre-processing stage specification
- **§9 Cross-Cutting Concerns** — Extend codegen invariants with: (a) mutation score gate (80% general, 90% critical core) as a CI-blocking requirement; (b) separate producer/verifier pipeline architecture; (c) critical core / generated shell split with explicit enforcement (separate module, stricter import rules, separate CI gate); (d) outbox operational invariants as architecture-level: partial index on unprocessed rows, `n_dead_tup` alert, dead-letter table, idempotency key on every consumer; (e) `SET LOCAL` + transaction-mode connection pooling as codegen invariants
- **§10 Deployment and Operability** — As-is; add: `FORCE ROW LEVEL SECURITY` in operability checklist; connection-pool configuration mandating transaction mode
- **§11 Phasing** — Adjust v1 MCP scope: `submit_document` and `submit_attestation` available in v1 with pre-processing sanitization; `create_ruleset`, `grant_visibility`, `start_vetting_run` via MCP deferred to Phase 2 pending MCP security model completion
- **§12 Architecture/Design Boundary** — As-is
- **§13 Risks and Open Questions** — Add: R7 (Fernet OWASP second-preference — AES-GCM pending Trimble internal standard confirmation); R8 (eval set self-referentiality — minimum proportion of real/anonymized document samples required); R9 (Redis consent cache invalidation race — synchronous invalidation mandate); R10 (separate verifier pipeline vs separate pipeline stage — governance question)
- **§14 Success Metrics** — Add: mutation score per critical core module; adversarial eval pass rate per check; consent revocation-to-cache-invalidation latency; verifier pipeline adversarial test survival rate
- **§15 Glossary** — Add: Critical Core, Verifier Pipeline, Pre-processing Stage, Adversarial Eval Set
- **§16 ADRs** — Add: ADR-020 (Application-layer encryption: AES-GCM as target, Fernet permitted with internal standard citation); ADR-021 (Mutation testing gate: critical core scope and minimum scores); ADR-022 (MCP write-tool v1 scope: submit_document and submit_attestation only; tenant-admin writes deferred)

---

## Substantive disagreements I'm holding

- D-4: v1 scope — status: open
  - (a) D-4: v1 scope reduction
  - (b) My position: The brief explicitly commits Portal, consent model, partner profile, audit/billing streams, and role architecture as Phase 1. I cannot recommend eliminating these. The right narrowing is write-capable tenant-admin MCP tools only.
  - (c) OpenAI's position: Full v1 is too large for no-human-code-review; recommends portal-only, Knauf-only, four Vera-equivalent checks, deterministic ruleset configuration, and read-only or heavily constrained MCP.
  - (d) Why not conceding: The brief is explicit. OpenAI's narrowing would require renegotiating the brief with the product owner, which is outside scope. My proposed compromise (defer tenant-admin MCP write tools; keep portal, consent, profile, audit, billing) achieves the safety benefit without contradicting the brief.
  - (e) Materiality: Resolving this one way changes whether §11 Phasing recommends a different v1 scope than the brief describes, which would be the central recommendation of the document.
  - > quote: "Phase 1 scope is intended to include the rebuilding of what Vera does today...the web component family, the MCP adapter, the carrier profile, the consent model, the audit and billing infrastructure, and the role architecture are all intended to be in Phase 1"

- D-5: MCP write-tool deferral scope — status: open
  - (a) D-5: Which write-capable MCP tools should be deferred from v1
  - (b) My position: `submit_document` and `submit_attestation` (partner-initiated) should be available in v1 with pre-processing and adversarial eval fixtures. `create_ruleset`, `grant_visibility`, `start_vetting_run` (tenant-admin writes) should be deferred to Phase 2.
  - (c) OpenAI's position: All write-capable MCP tools deferred until MCP security model and policy tests are mature, including `submit_document`.
  - (d) Why not conceding: The brief explicitly describes carrier-initiated self-vetting (LR §«Carrier-Initiated Self-Vetting Flow») as a distinct entry point that must be supported. Deferring `submit_document` eliminates the partner-as-principal invocation model entirely from v1, which the brief considers a first-class use case.
  - (e) Materiality: Resolving this changes whether the carrier-initiated MCP flow is a v1 deliverable or a Phase 2 item, which affects the system context diagram (C4 L1) and the MCP tool surface (§8.1).
  - > quote: "Defer write-capable MCP tools such as `create_ruleset`, `grant_visibility`, `submit_document`, and `start_vetting_run` until the MCP-specific security model and policy tests are mature."

- **D-1 (oracle quality vs infrastructure framing):** `resolved` — Both agents agree the document should cover oracle quality (mutation testing, verifier pipeline, eval set independence) AND infrastructure failure modes (RLS GUC, outbox, consent cache). The framing question (which leads) is non-blocking; the document can address both without contradiction. The final document will lead with the structural strengths, then address both failure-mode categories in parallel.

---

## Final-surfaced disagreements

*(none — remaining open disagreements are resolvable within the plan; they affect §11 scope and §8.1 tool surface, not the fundamental architectural recommendation)*

---

## Resolved or non-blocking differences

1. **D-2 (mutation testing gate):** `resolved` — OpenAI identified the gap; I concede fully. Research confirms mutation score ≥ 80% (90% for critical core) is the correct target for AI-generated code. Added to §2, §9, and ADR-021.

2. **D-3 (Fernet vs AES-GCM):** `resolved` — Both agents agree AES-GCM is OWASP first preference; Fernet is second preference. Architecture target becomes AES-GCM conditioned on Trimble internal standard confirmation. Named as R7 in §13.

3. **D-7 (prompt injection as architecture-level):** `resolved` — Both agents agree; the pre-processing sanitization stage and adversarial eval fixtures are architecture-level requirements, not design-doc concerns.

4. **D-8 (critical core / generated shell split):** `resolved` — Adopted from OpenAI. Critical core membership list defined in §3.

5. **D-9 (consent revocation cache race):** `resolved` — OpenAI acknowledged this gap in Q9 discussion; synchronous Redis cache invalidation within the revocation transaction is the architectural invariant, added to §7 and §9.

6. **D-6 (specification review substitute for code review):** `non_blocking_limitation` — OpenAI's framing (human review moves to specs) is consistent with the brief (product pair writes specs, which IS the human design intent layer). The independent verifier pipeline addresses the independence concern without requiring a fourth party. Non-blocking because both agents agree the verifier pipeline should be separate, regardless of who governs specs.

7. **D-10 (eval set independence):** `resolved` — Both agents agree; softened wording adopted: "substantial proportion of real or independently anonymized document samples, minimum 40% for EU checks, 60% for non-EU country variants."

---

## Agreement check

(not ready) — Two open disagreements remain (D-4 and D-5) on v1 scope. Specifically: I need OpenAI's response to whether `submit_document` (carrier-as-principal, partner-initiated) is architecturally distinguishable from `create_ruleset` (tenant-admin write) in their risk model. If OpenAI accepts the distinction, D-4 and D-5 collapse to non-blocking (the portal/consent/profile scope is agreed; only the tenant-admin MCP write tool deferral remains as a scope constraint). If OpenAI maintains that even partner-initiated document submission via MCP is too risky for v1, this remains a blocking disagreement because it contradicts an explicit brief requirement (carrier-initiated self-vetting flow).

## AGREED_PLAN

(not agreed)

---

## Drafter recommendation

`DRAFTER: claude` — The architecture document requires surgical amendment of an existing detailed proposal with ADRs and C4 diagrams; claude's Phase 1 surgical diagnosis approach and the accumulated research depth in this thread suit this better than a structural rewrite.

`DOMAIN_FIT_SELF: 4`
`DOMAIN_FIT_OTHER: 4`

---

## Status

`STATUS: NEGOTIATING`
`OPEN_QUESTIONS: 5`
`BLOCKING_DISAGREEMENTS: 2`
`FINAL_SURFACED_DISAGREEMENTS: 0`