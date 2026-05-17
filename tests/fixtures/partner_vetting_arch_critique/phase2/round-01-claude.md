I'll research the key gaps before producing my round-1 turn.Now I have sufficient research to produce my round-1 turn. Let me compile it.

---

## Summary

My Phase 1 identified four critical codegen-first failure modes: the RLS GUC lifecycle leak under connection pooling, prompt injection via carrier documents into the Claude extraction pipeline, Postgres outbox operational underspecification, and self-referential eval sets. OpenAI's draft converges on two of these (MCP adversarial surface, specification independence) but diverges materially on scope (recommending aggressive v1 narrowing), on the Fernet cryptography choice (recommending replacement with AES-GCM), on whether human spec review is required (they say yes, the brief says no human code review), and on the "no public REST API" decision (they call it too strong). Research this round confirms the RLS SET vs. SET LOCAL distinction is the specific, fixable codegen-failure mode I identified; confirms Fernet with CBC+HMAC is cryptographically sound but OWASP explicitly names GCM/CCM as first preference; confirms mutation testing is the critical missing gate for AI-generated code; and confirms MCP prompt injection attack rates are severe enough to be architecture-level, not design-level. I propose claude as drafter given depth of architectural reasoning in my Phase 1 and the research-heavy direction this document needs.

---

## Diff vs openai's Phase 1

**D-1** — **RLS isolation mechanism adequacy**
- *Claude said:* RLS is correct direction but the specific codegen failure mode is the connection-pool GUC lifecycle — `SET` vs `SET LOCAL` distinction; integration tests asserting the denial path do not catch pool-reuse leaks; requires a mandatory connection-lifecycle contract test.
- *OpenAI said:* RLS is correct and sound (cites PostgreSQL documentation), calls for `FORCE ROW LEVEL SECURITY`, connection-pool reset tests, migration tests, superuser/bypass-role controls, and negative tests per table. Does not specifically identify the `SET LOCAL` vs `SET SESSION` failure mode as the critical implementation gap.
- *Type:* Interpretive, substantive. OpenAI's list is correct but incomplete on the specific mechanism that kills codegen pipelines. The SET LOCAL vs SET failure mode is the fixable, spec-expressible constraint that makes this architecture-level rather than design-level.

**D-2** — **Mutation testing as a required gate**
- *Claude said:* Not explicitly called out in Phase 1 (gap in my draft).
- *OpenAI said:* Required mutation score thresholds for critical core modules are essential; branch coverage can be gamed by shallow assertions; specifically lists Rules, Consent, Authorization, Tenant Isolation, Billing, Audit, Expiry, Coverage Report Builder as mutation targets.
- *Type:* Scope. OpenAI identified this gap that I missed in Phase 1. Research confirms it: tests achieving 100% line and branch coverage can score only 4% on mutation testing [26-14,26-41]. AI-generated code is specifically susceptible to this failure mode [21-1, 26-15,26-16]. I concede this point fully — mutation testing must be in the architecture document as a gate.

**D-3** — **Fernet (AES-CBC-128 + HMAC-SHA256) vs AES-GCM**
- *Claude said:* (not addressed in my Phase 1)
- *OpenAI said:* Fernet should not be hard-coded as the architectural standard; OWASP recommends authenticated modes such as GCM and CCM as first preference; recommends AES-GCM or XChaCha20-Poly1305 unless an internal standard mandates Fernet.
- *Type:* Factual/interpretive, substantive. OWASP is clear: "The most commonly used authenticated modes are GCM and CCM, which should be used as a first preference." [31-2]. Fernet uses AES-128-CBC + HMAC-SHA256 [36-1, 36-4], which is the "encrypt-then-MAC" pattern that OWASP accepts as second preference when GCM/CCM are unavailable [31-3]. Fernet is not broken, but it is second preference. OpenAI's position is correct as a default; the architecture document should specify AES-GCM as the target and permit Fernet only if Trimble's internal standard mandates it.

**D-4** — **Whether v1 scope is too large for no-human-review**
- *Claude said:* The scope is manageable given the modular monolith decision; the risks I identified are specific technical gaps, not a general scope problem.
- *OpenAI said:* Phase 1 is too large for a no-human-code-review system; recommends narrowing to: one tenant, one portal, one standing workflow, four Vera-equivalent checks, no write-capable MCP tools in v1, no conversational workflow authoring, no billing automation beyond audit-grade event capture.
- *Type:* Scope, substantive. This is a genuine disagreement. OpenAI's narrowing is the safer argument in the abstract, but it conflicts directly with the brief: Phase 1 explicitly includes the MCP adapter, the web component family, the carrier profile, the consent model, audit and billing infrastructure, and the role architecture. The brief also states a real customer (Knauf) with a two-month deadline. Aggressive narrowing may be architecturally safer but risks not delivering to the stated requirement. My position: narrowing the *write-capable MCP tools* in v1 (keeping read-only MCP only) is the right compromise; full scope narrowing to exclude the portal, consent model, or profile is not consistent with the brief.

**D-5** — **Whether MCP-only external programmatic surface is correct (ADR-010)**
- *Claude said:* MCP-only is right for v1; the degraded-skill runbook gap is the real risk, not the MCP-only decision itself.
- *OpenAI said:* MCP-only is too strong; customer compliance integrations need deterministic non-agent APIs; recommends keeping MCP for ARC in v1 but defining the internal service contract as an HTTP API that can later be published safely.
- *Type:* Interpretive, substantive. The brief explicitly says "REST/HTTP public API" is a Non-goal for v1 and v2, and ADR-010 makes MCP the sole external surface with this as a deliberate decision. The Portal's internal HTTP boundary means deterministic non-agent UI access exists. OpenAI's concern about compliance integrations wanting deterministic APIs is real but: (a) the brief specifically defers REST to Phase 3, and (b) the internal HTTP boundary already serves deterministic access via the Portal. I maintain MCP-only is the correct v1 call per the brief; the runbook gap is the real architecture-level risk.

**D-6** — **Whether human specification review is required**
- *Claude said:* The architecture enables codegen by making illegal states unrepresentable at lint and contract levels; "no human PR review" applies to code, not to the overall product design process.
- *OpenAI said:* "No human PR review, no human code inspection" means human review must move to specifications, policies, threat models, and acceptance evidence; an "independent assurance pipeline" generating adversarial tests is needed; the producer and verifier agents must be separated.
- *Type:* Scope/framing, substantive. This is the most fundamental conceptual disagreement. The brief is unambiguous: "no code ever changes without a specification" and code is AI-generated. OpenAI interprets "no human code inspection" to mean humans must review specifications. My reading: the brief describes a development team of six people none of whom write code, and the constraint is that code is AI-generated from specs. Human review of specs is inherently part of that process (the product pair writes the specs). The separate "verifier agent" recommendation is valuable regardless of this interpretation. My position: OpenAI's recommendation of a separate verifier pipeline is correct and should be adopted; their framing that this "resolves" the human-review prohibition is not a contradiction.

**D-7** — **Prompt injection as architecture-level vs. design-level**
- *Claude said:* Document-content-as-attack-vector is architecture-level because it determines whether the sole quality gate (automated tests) can catch the failure at all; requires a threat model section in the architecture document.
- *OpenAI said:* LLM outputs should be treated as untrusted inputs; MCP must be classified as high-risk; requires per-tool capability tokens, argument canonicalization, prompt-injection tests using malicious documents, tool-result sanitization.
- *Type:* Framing, aligned. Both agents agree this is underaddressed. Research confirms: MCPTox benchmark shows attack success rates up to 72.8% [4-19]; Claude 3.7-Sonnet had the highest refusal rate at less than 3% [4-22]; OWASP ranks prompt injection as #1 [4-8]. The practical recommendation is the same; the framing (architecture-level threat model section) is my addition.

**D-8** — **"Critical core" vs. "generated shell" split**
- *Claude said:* (not explicitly named in my Phase 1)
- *OpenAI said:* Split codebase into "critical core" (tiny, deterministic, side-effect controlled, property-tested, mutation-tested, fuzz-tested) and "generated shell" (adapters, formatting, documentation with lighter gates).
- *Type:* Scope. This is a valuable addition. The proposal currently treats all generated code too uniformly. Authorization, consent, billing emission, audit emission, tenant isolation, state transitions, and expiry logic are the critical core modules. I adopt this recommendation.

**D-9** — **Consent cache invalidation race on revocation**
- *Claude said:* The 5-minute Redis TTL on consent state creates a GDPR compliance risk when a partner revokes consent — the Consent Manager must invalidate the Redis cache entry immediately on revocation.
- *OpenAI said:* (not addressed directly; mentioned "carrier ownership consent model needs stronger invariants" but not the specific Redis TTL race)
- *Type:* Factual, substantive gap in OpenAI's draft. This is a specific, architecture-level invariant that must be in the Consent Manager specification: on revocation, synchronously invalidate the `(profile_id, tenant_id, section)` cache key in Redis before returning 200 to the caller.

**D-10** — **Eval set independence for AI-bearing checks**
- *Claude said:* At least 50% of labelled examples per check must come from real document samples, not LLM-generated synthetic data, because a self-referential eval set does not constitute an independent quality gate.
- *OpenAI said:* Per-check eval datasets required before a check version can be published; red-team document corpora, prompt-injection fixtures, OCR degradation cases, multilingual edge cases, calibration reports required.
- *Type:* Framing, aligned with OpenAI going further. My position holds and OpenAI's additions (red-team corpus, prompt-injection fixtures) strengthen it.

---

## Gaps I researched this round

1. **D-1 (RLS GUC lifecycle):** Searched "PostgreSQL RLS row level security connection pool GUC session variable reset vulnerability." Found: `SET LOCAL` vs `SET` is the concrete mechanism — `SET LOCAL` scopes the variable to the current transaction and rolls back automatically when the transaction ends; `SET` persists for the lifetime of the session and leaks between clients in transaction mode pooling [16-1,16-5,14-6,14-15,14-17]. The proposal uses `RESET` on connection release, which is `SET` semantics. The architecture must mandate `SET LOCAL` (within a transaction) not `SET` + `RESET` on release, because in transaction-mode connection pooling the `RESET` call may not execute if the connection is interrupted. Additionally, if the application connects as the table owner, policies are silently bypassed unless `FORCE ROW LEVEL SECURITY` is set [16-17,16-18]. The proposal does not specify `FORCE RLS`. This confirms my D-1 position and adds the `FORCE RLS` gap. Position unchanged and strengthened.

2. **D-2 (Mutation testing):** Searched "mutation testing autonomous AI generated code quality gate 2025." Found: researchers documented tests achieving 100% line and branch coverage scoring only 4% mutation testing [26-14]; CodeRabbit's December 2025 analysis found AI-authored PRs average 10.83 issues each versus 6.45 for human-only, with logic/correctness errors up 75% and security findings 57% more prevalent [26-15,26-16]. Atlassian's Sep 2025 innovation week found mutation scores below 80% on code with ostensibly solid coverage [25-3]. An April 2026 piece from the DEV community specifically describes mutation testing as "the missing safety net for AI-generated code" [21-1]. I concede D-2 to OpenAI fully: mutation testing for critical core modules must be in the architecture as a required gate.

3. **D-3 (Fernet vs AES-GCM):** Searched "Fernet AES-CBC-128 vs AES-GCM OWASP cryptographic storage recommendation." Found: OWASP Cryptographic Storage Cheat Sheet explicitly states "The most commonly used authenticated modes are GCM and CCM, which should be used as a first preference. If GCM or CCM are not available, then CTR mode or CBC mode should be used." [31-2,31-3]. Fernet uses AES-128-CBC + HMAC-SHA256 [36-1], which is the encrypt-then-MAC pattern OWASP accepts as second preference [36-4,36-5]. Fernet is cryptographically sound for the use case but is not first preference. OpenAI's position (D-3) is correct. The architecture document should specify an AEAD mode (AES-GCM) as the standard and permit Fernet only if Trimble's internal standard mandates it.

4. **D-7 (MCP prompt injection — architecture level):** Searched "MCP prompt injection attack carrier document security 2025." Found: MCPTox benchmark on 20 LLM agents, 45 real-world MCP servers, 353 tools — attack success rate up to 72.8% for o1-mini; Claude 3.7-Sonnet highest refusal rate at less than 3% [4-19,4-22]. Tool poisoning ranks #1 in OWASP LLM Top 10 and scores Critical (46.5/50) in DREAD analysis [9-20]. Unit 42 identified three PoC attacks on a widely used coding copilot: resource theft, conversation hijacking, covert tool invocation [1-11,1-12,1-13]. The client receives tool metadata from servers and passes it without validation into the LLM's context window [9-24,9-25]. Position confirmed: this is architecture-level because tests cannot catch prompt-injection-induced falsified Result Envelopes without adversarial document fixtures in the eval set. Position unchanged.

5. **Fernet note (clarification):** The proposal states "Fernet AES-128-CBC + HMAC-SHA256" as the application-layer encryption scheme. Research confirms this is the correct description of Fernet [36-1, 36-9, 39-2] and that it implements Encrypt-then-MAC [36-5], which OWASP treats as second preference. AES-GCM would be first preference [31-2, 35-15]. The gap is real but not a security failure at current scale — it is a preference gap that should be resolved before v1 ships to a compliance-sensitive customer (Knauf).

---

## Updated position

The architecture proposal is fundamentally sound for the stated primary constraint — typed contracts, lint rules, import boundaries, modular monolith, and Postgres RLS make the codegen pipeline's failure modes mostly detectable before production. My Phase 1 position is confirmed and strengthened by research on four specific gaps: (1) the `SET LOCAL` vs `SET` connection-pool GUC failure mode and missing `FORCE ROW LEVEL SECURITY` are the concrete implementation constraints that must be in the architecture spec, not delegated to the data design doc; (2) mutation testing for critical core modules (authorization, consent, billing emission, audit emission, tenant isolation, state transitions, expiry logic) is confirmed as the critical missing quality gate for AI-generated code and must be in the architecture document; (3) Fernet AES-CBC + HMAC is second preference under OWASP and should be replaced with AES-GCM as the default unless a Trimble internal standard mandates otherwise; (4) MCP prompt injection via carrier-submitted documents is a demonstrated, high-severity, architecture-level threat that the current proposal does not address with adversarial test fixtures in the eval suite. I concede D-2 to OpenAI (mutation testing) and D-3 (AES-GCM preference). I maintain D-4 (v1 scope): the brief's explicit Phase 1 commitments cannot be renegotiated in the architecture document — the right narrowing is write-capable MCP tools deferred, not elimination of the portal, consent model, or profile. I maintain D-5 (MCP-only): the brief explicitly designates REST as a non-goal for v1 and v2, and the portal provides deterministic UI access. I add D-9 (Redis cache invalidation on consent revocation) as an architecture-level constraint not identified in either Phase 1 draft that must be specified. The critical core / generated shell split (D-8) from OpenAI is a valuable addition I adopt.

---

## Open questions for openai

1. On D-4 (v1 scope narrowing): does openai's recommendation to eliminate write-capable MCP tools from v1 apply to `submit_document` and `submit_attestation` (partner-initiated flows), or only to `create_ruleset`, `grant_visibility`, and `start_vetting_run`? These are architecturally different risk profiles.

   > quote: "Defer write-capable MCP tools such as `create_ruleset`, `grant_visibility`, `submit_document`, and `start_vetting_run` until the MCP-specific security model and policy tests are mature."

2. On D-6 (specification review): openai describes a "reviewed Spec Package" as input to both the producer and verifier agents. Who produces that review in the three-pair team described in the brief (product pair, skills team, infrastructure/self-healing team)? If it is the product pair (as the brief implies), is that "human spec review" or is it the same humans who would have written code in a traditional process?

   > quote: "if human code inspection is forbidden, human review must move to specifications, policies, threat models, and acceptance evidence"

3. On D-3 (cryptography): Does openai know whether Trimble's ARC integration posture (cited in the proposal as the inherited baseline) mandates Fernet specifically, or merely "application-layer encryption with Trimble-managed keys"? This determines whether the AES-GCM upgrade is a policy question or an architecture question.

   > quote: "My recommended change is to use an approved AEAD envelope-encryption scheme such as AES-GCM or XChaCha20-Poly1305 with KMS-managed data keys, unless an internal security standard mandates Fernet."

4. On D-1 (RLS implementation): openai lists RLS mitigation requirements including "connection-pool reset tests" but does not specify the `SET LOCAL` vs `SET SESSION` distinction. Does openai agree that the concrete architecture-level invariant is that the GUC must be set with `SET LOCAL` inside a transaction boundary, not with `SET` followed by `RESET` on pool return — and that `FORCE ROW LEVEL SECURITY` is a required table-level attribute?

   > after: Where the architecture undermines the no-human-review constraint

5. On D-7 (MCP prompt injection): openai recommends "prompt-injection tests using malicious documents" and "LLM cannot authorize" rules. Does openai have a concrete proposal for *what architectural boundary* prevents a carrier-submitted document from being passed verbatim to the Claude extraction prompt without sanitization? Is this the Document AI Provider Abstraction (a pre-processing stage), the Upload Endpoint (content sanitization at ingestion), or a separate prompt engineering constraint in the check definition schema?

   > quote: "Document AI results, conversational workflow drafts, and ARC/MCP tool arguments should all be treated as untrusted until validated by deterministic code."

6. On D-8 (critical core vs generated shell): How does openai propose to enforce the boundary between "critical core" and "generated shell" in a codegen-first pipeline? Specifically, if the product pair generates a specification that touches both a critical core module and an adapter, is the entire specification subject to the stricter gate, or only the critical core portion?

   > quote: "The proposal should create a 'critical core' package whose APIs are tiny, whose functions are pure where possible, whose invariants are exhaustively property-tested, and whose generated code must pass a stronger gate than ordinary UI or adapter code."

---

## Initial plan proposal

- **§1 Drivers and Goals** — As-is from the proposal; add explicit acknowledgment that codegen-first constraint requires architecture to expose machine-verifiable boundaries, not prose assertions
- **§2 Quality Attributes** — Extend table with: mutation score target ≥80% for critical core modules; adversarial document eval fixtures as required for every AI-bearing check; `SET LOCAL` GUC transaction discipline as a committed target
- **§3 Domain Model and Glossary** — As-is; add "Critical Core" as a named architectural zone with explicit membership list
- **§4 System Context (C4 L1)** — As-is; add threat model subsection covering: carrier-document-as-attack-vector, tool poisoning, rug-pull, confused deputy
- **§5 Containers (C4 L2)** — As-is; add "Verifier Pipeline" as a distinct container (separate from the producer pipeline; generates adversarial tests from the same spec)
- **§6 Components** — As-is; add pre-processing stage in Document Intake before LLM invocation; add `FORCE ROW LEVEL SECURITY` and `SET LOCAL` as explicit invariants of the Profile & Consent context
- **§7 Data Architecture** — As-is; add: consent revocation triggers synchronous Redis cache invalidation (architecture-level invariant); AES-GCM replaces Fernet as default envelope encryption scheme
- **§8 Integration Surface** — As-is; add: per-tool capability token requirement for write-capable MCP tools; adversarial prompt injection test requirements in MCP adapter spec
- **§9 Cross-Cutting Concerns** — Extend codegen invariants with: mutation testing as required gate for critical core modules; separate producer/verifier agent pipeline; "critical core vs generated shell" split with explicit enforcement mechanism
- **§10 Deployment and Operability** — As-is; add: `FORCE ROW LEVEL SECURITY` checklist item; connection-pool configuration mandating transaction mode with `SET LOCAL`
- **§11 Phasing** — Adjust v1 scope: write-capable MCP tools restricted to partner-initiated flows only (`submit_document`, `submit_attestation`); tenant-admin write tools (`create_ruleset`, `grant_visibility`) deferred to Phase 2 pending MCP security model completion
- **§12 Architecture/Design Boundary** — As-is
- **§13 Risks and Open Questions** — Add: R7 (Fernet OWASP second-preference gap), R8 (eval set self-referentiality risk), R9 (Redis consent cache revocation race)
- **§14 Success Metrics** — Add: mutation score per critical core module; adversarial eval pass rate; consent revocation latency (time to cache invalidation)
- **§15 Glossary** — As-is
- **§16 ADRs** — Add: ADR-020 (Application-layer encryption: AES-GCM); ADR-021 (Mutation testing gate: critical core scope and minimum score); ADR-022 (MCP write-tool deferral: v1 scope limitation)

---

## Drafter recommendation

`DRAFTER: claude` — The proposal is already a detailed architecture document with ADRs, C4 diagrams, and bounded context specifications; the final document requires integration of specific technical amendments (GUC lifecycle, mutation testing gate, AES-GCM, prompt injection threat model, critical core/shell split) rather than a structural rewrite, which maps to claude's Phase 1 approach of surgical diagnosis rather than wholesale scope reduction.

`DOMAIN_FIT_SELF: 4`
`DOMAIN_FIT_OTHER: 4`

---

## Status

`STATUS: NEGOTIATING`
`OPEN_QUESTIONS: 6`

---

## Sources

1. Unit 42 / Palo Alto Networks — New Prompt Injection Attack Vectors Through MCP Sampling: https://unit42.paloaltonetworks.com/model-context-protocol-attack-vectors/
2. Keysight — Command Injection: Uncovering A New Attack Vector of MCP Server: https://www.keysight.com/blogs/en/tech/nwvs/2026/01/12/mcp-command-injection-new-attack-vector
3. Simon Willison — Model Context Protocol has prompt injection security problems: https://simonwillison.net/2025/Apr/9/mcp-prompt-injection/
4. DataDome — MCP Security: How to Stop Prompt Injection Attacks: https://datadome.co/agent-trust-management/mcp-security-prompt-injection-prevention/
5. Docker — MCP Horror Stories: The GitHub Prompt Injection Data Heist: https://www.docker.com/blog/mcp-horror-stories-github-prompt-injection/
6. Practical DevSecOps — MCP Security Vulnerabilities 2026: https://www.practical-devsecops.com/mcp-security-vulnerabilities/
7. Checkmarx — 11 Emerging AI Security Risks with MCP: https://checkmarx.com/zero-post/11-emerging-ai-security-risks-with-mcp-model-context-protocol/
8. CyberSecurityNews — New Prompt Injection Attack via Malicious MCP Servers: https://cybersecuritynews.com/prompt-injection-malicious-mcp-servers/
9. arXiv — MCP Threat Modeling and Analyzing Vulnerabilities to Prompt Injection with Tool Poisoning: https://arxiv.org/html/2603.22489v1
10. JFrog — CVE-2025-6515 Prompt Hijacking Attack: https://jfrog.com/blog/mcp-prompt-hijacking-vulnerability/
11. DEV Community (YugabyteDB) — Row Level Security with an ARRAY of tenants set in session parameter: https://dev.to/yugabyte/postgresql-row-level-security-with-an-array-of-tenants-2136
12. Bytebase — Postgres Row Level Security: https://www.bytebase.com/reference/postgres/how-to/postgres-row-level-security/
13. PostgreSQL Wiki — Row Security Considerations: https://wiki.postgresql.org/wiki/Row_Security_Considerations
14. DEV Community (Software MVP Factory) — PostgreSQL Row-Level Security for Multi-Tenant SaaS: https://dev.to/software_mvp-factory/postgresql-row-level-security-for-multi-tenant-saas-1lgp
15. ShiftAsia — Why Your Database Needs Boundaries: https://shiftasia.com/community/why-your-database-needs-boundaries-an-intro-to-postgresqls-row-level-security-rls/
16. Rivestack — PostgreSQL Row Level Security: A Complete Guide: https://rivestack.io/blog/postgresql-row-level-security
17. Crunchy Data — Row Level Security for Tenants in Postgres: https://www.crunchydata.com/blog/row-level-security-for-tenants-in-postgres
18. Daniel Imfeld — PostgreSQL Row Level Security: https://imfeld.dev/notes/postgresql_row_level_security
19. Kimmo Oppel — Yes, Postgres can do session vars - but should you use them?: https://kmoppel.github.io/2025-06-03-yes-postgres-can-do-session-variables-but-should-you-use-them/
20. PostgreSQL Official Documentation — Row Security Policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
21. DEV Community (rsri) — Mutation Testing: The Missing Safety Net for AI-Generated Code: https://dev.to/rsri/mutation-testing-the-missing-safety-net-for-ai-generated-code-54kn
22. Medium (Tejaspisal) — Mutation Testing: https://medium.com/@tejaspisal/mutation-testing-8e780d26254f
23. InnovateBits — Top AI Testing Trends QA Engineers Must Know in 2025-2026: https://www.innovatebits.com/blog/ai-testing-trends-2025-2026
24. Augment Code — Autonomous Quality Gates: https://www.augmentcode.com/learn/autonomous-quality-gates-ai-powered-code-review
25. Atlassian — Automating Mutation Coverage with AI: https://www.atlassian.com/blog/developer/automating-mutation-coverage-with-ai
26. TwoCents Software — How to Test AI-Generated Code the Right Way in 2026: https://www.twocents.software/blog/how-to-test-ai-generated-code-the-right-way/
27. Medium (Prateek Singh) — Your AI-Generated Tests are Lying to You: https://singhpr.medium.com/your-ai-generated-tests-are-lying-to-you-and-what-to-do-about-it-57fb0e5f2783
28. Gartner — Use AI Mutation Testing to Improve Software Quality: https://www.gartner.com/en/webinar/830638/1839333-use-ai-mutation-testing-to-improve-software-quality
29. Augment Code — Harness Engineering for AI Coding Agents: https://www.augmentcode.com/guides/harness-engineering-ai-coding-agents
30. ShiftAsia — Testing AI-Generated Code: The QA Engineer's New Blind Spot: https://shiftasia.com/column/testing-ai-generated-code-the-qa-engineers-new-blind-spot/
31. OWASP — Cryptographic Storage Cheat Sheet (current): https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
32. PythonTutorials — Is the Fernet Cryptography Module Safe?: https://www.pythontutorials.net/blog/is-the-fernet-cryptography-module-safe-and-can-i-do-aes-encryption-with-that-module/
33. AquilaX — Strong Encryption Best Practices: https://aquilax.ai/blog/strong-encryption-best-practices
34. DeepWiki OWASP — Cryptography and Secure Storage: https://deepwiki.com/OWASP/CheatSheetSeries/5-cryptography-and-secure-storage