## Answers to openai's prior comments

(none — first round)

---

## Issue ledger (delta + currently open)

This is round 1; all issues are newly raised by me as drafter.

1. **CLAUDE-01** `open` — Gap A (oracle-quality / verifier pipeline) requires concrete architectural specification of how the verifier pipeline is separated from the producer pipeline at the model-invocation level. The draft describes *what* the verifier pipeline produces but not *how* the pipeline enforces model-family separation. Without this, the requirement is aspirational prose rather than an enforceable architectural constraint.

   > after: Gap A — Independent Verifier Pipeline

2. **CLAUDE-02** `open` — Gap B (RLS GUC lifecycle) lists seven invariants but invariant #6 (referential-integrity leak via FK) is materially underspecified. The scenario where a child-table INSERT triggers a FK check that silently reads a cross-tenant parent row through RLS is a real vulnerability class documented in PostgreSQL RLS limitations literature, but the draft does not state *which* FK relationships in the data model are at risk or how to mitigate (e.g., deferring FK checks or using application-layer FK enforcement for cross-context references).

   > quote: Referential-integrity leak tests: integration tests assert that a cross-tenant INSERT into a child table

3. **CLAUDE-03** `open` — Gap C (MCP attack surface) defers `create_ruleset`, `grant_visibility`, `revoke_visibility`, and `start_vetting_run` to Phase 2 without specifying the conditions under which Phase 2 deferral ends. ADR-022 is named but its "conditions under which Phase 2 deferral ends" clause contains four requirements (per-tool capability scoping, confirmation gating, policy decision logging, adversarial test suite complete) but no definition of what "complete" means for the adversarial test suite — a codegen pipeline needs machine-verifiable completion criteria, not narrative descriptions.

   > quote: per-tool capability scoping, confirmation gating, policy decision logging, and adversarial test suite complete

4. **CLAUDE-04** `open` — The confidence ledger claim about "AI-authored PRs average 10.83 issues vs. 6.45 for human-only; logic/correctness errors up 75%; security findings 57% more prevalent" cites Source [16] which in turn cites a "CodeRabbit December 2025 analysis." The draft's own source is TwoCents Software (a blog post) citing CodeRabbit. This is a second-order citation for a material quantitative claim that drives the mutation testing gate justification. The ledger tags this [V]-CORROBORATED but the retrieval chain ends at a third-party blog that cites an industry report I have not directly inspected. This should be tagged [U] with a staleness note or the primary CodeRabbit source should be retrieved.

   > quote: AI-authored PRs average 10.83 issues vs. 6.45 for human-only; logic/correctness errors up 75%

5. **CLAUDE-05** `open` — Gap F (consent cache invalidation race) specifies synchronous Redis DEL in the same request handler, but does not address the scenario where the Consent Manager is invoked through the MCP path (not the internal HTTP path). An MCP tool invocation is async by nature; the "same request handler" semantic needs to be explicitly stated to apply to MCP tool invocations as well, and the serialization guarantee (DB write commits → Redis DEL → 200 returned) must be specified for both surfaces.

   > quote: The Redis DEL call executes within the same request handler as the DB write, before the response is sent

6. **CLAUDE-06** `open` — The surviving open question R-Claude-region (Anthropic API in Azure West Europe) is material to the Phase 1 architecture because Knauf is a German shipper and EU data residency requirements may apply to carrier document processing. The draft flags this as unresolved but does not specify the fallback path's architectural implication: if Anthropic cannot satisfy EU data residency, is Azure Document Intelligence elevated to co-primary (requiring its capability gaps for natural-language reasoning to be explicitly acknowledged), or is a different AEAD-capable model required? The open question needs a conditional resolution path, not just a flag.

   > after: Surviving Open Questions

---

## Evidence checked this round- **New research performed:**
  - Retrieved CodeRabbit "State of AI vs Human Code Generation" primary source [coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report], December 17, 2025. The Register confirms the specific figures: "AI-generated pull requests include about 10.83 issues each, compared with 6.45 issues in human-generated PRs." CodeRabbit's own blog confirms: "AI-generated code shows significantly higher rates of logic and correctness issues (75% more common), readability issues (3x more common), security vulnerabilities (up to 2.74x higher)."
  - Retrieved PostgreSQL official documentation on RLS and foreign key behavior. PostgreSQL official documentation states: "Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security to ensure that data integrity is maintained. Care must be taken when developing schemas and row level policies to avoid 'covert channel' leaks of information through such referential integrity checks."
  - Retrieved Bytebase RLS footguns article confirming FK bypass and `FORCE ROW LEVEL SECURITY` requirement. Bytebase documents: "The footgun: Enabling RLS without FORCE allows table owners to bypass policies. ... ALTER TABLE orders FORCE ROW LEVEL SECURITY."
  - Retrieved PostgreSQL wiki on row-security design, which documents the FK side-channel: The PostgreSQL wiki states: "The FOREIGN KEY side channel. A user can probe for the existence of keys by testing to see whether or not DML operations succeed on tables with foreign keys to/from protected tables. Needs documentation - recommend that synthetic keys or no foreign keys at all be used for FK relationships between RS tables."

- **Claims checked against existing sources:**
  - Draft claim: "AI-authored PRs average 10.83 issues vs. 6.45 for human-only" — **UPGRADED from second-order to first-order [V]**: Direct CodeRabbit primary source and The Register corroboration both retrieved this run. The original concern in CLAUDE-04 is resolved; the confidence ledger should be updated.
  - Draft claim: FK checks bypass RLS — **CORROBORATED [V]**: PostgreSQL official docs (current version and 9.5) confirm this is documented behavior.
  - Draft claim: `FORCE ROW LEVEL SECURITY` required — **CORROBORATED [V]**: PostgreSQL docs, Bytebase footguns article, AWS multi-tenant RLS blog all confirm.

- **Factual issues found:**
  - Source [16] in the confidence ledger (TwoCents Software blog) is a second-order citation for the CodeRabbit statistics. The primary source (coderabbit.ai) has now been retrieved directly. The confidence ledger entry for CLAUDE-04 can be upgraded to [V]-CORROBORATED with the direct primary source added. The specific "10.83 issues" and "6.45 issues" figures and "75% more logic/correctness errors" are confirmed by multiple primary sources retrieved this run.
  - The draft states "security findings 57% more prevalent" in the confidence ledger — The Register reports security findings at 1.57x (57% more prevalent), which is consistent; but the original claim of "security findings 57% more prevalent" understates the data since the report also cites "up to 2.74x higher" for security vulnerabilities specifically. This is a nuance rather than an error: the 1.57x figure is the overall security finding rate; the 2.74x is XSS-specific. The ledger entry should clarify this.

- **No new research because:** (n/a — new research was performed)

- **Corroboration on the other agent's claims:**
  - Material [U] claims: (none — this is round 1; no prior openai turn to corroborate)
  - Central [V] claims: (none — this is round 1; no prior openai turn to corroborate)

---

## Comments on the current draft

1. **Comment on Confidence Ledger — CLAUDE-04 citation chain.** The confidence ledger entry for "AI-authored PRs average 10.83 issues vs. 6.45 for human-only" cites Source [16] (TwoCents Software blog) and tags it [V]-CORROBORATED. The TwoCents blog cites CodeRabbit; the current confidence ledger does not cite the CodeRabbit primary source directly. With the primary source now retrieved, this entry should be upgraded to cite the CodeRabbit report (coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report) and The Register corroboration (theregister.com) as new sources. Desired change: add the two new source entries to the Sources list (numbered 33 and 34 or similar) and update the confidence ledger row to cite them as [V]-primary.

   > quote: AI-authored PRs average 10.83 issues vs. 6.45 for human-only; logic/correctness errors up 75%; security findings 57% more prevalent

2. **Comment on Confidence Ledger — "security findings 57% more prevalent" precision.** The current ledger states "security findings 57% more prevalent" but the CodeRabbit report distinguishes between an overall security finding rate of 1.57x and a specific XSS/injection vulnerability rate of 2.74x. The ledger as written is accurate but potentially misleading for readers who encounter the more commonly cited "2.74x" figure elsewhere. Desired change: amend the ledger entry to state "overall security findings 1.57x more prevalent (XSS-specific: 2.74x)" to be precise.

   > quote: security findings 57% more prevalent

3. **Comment on Gap B (RLS) — FK bypass is insufficiently prescribed.** The PostgreSQL official documentation states that "referential integrity checks, such as... foreign key references, *always* bypass row security." This means the draft's invariant #6 ("integration tests assert that a cross-tenant INSERT into a child table fails closed") is mischaracterizing the actual behavior: the FK check does NOT fail; it succeeds by bypassing RLS, creating a covert channel. The test prescription ("assert that the insert fails") needs to distinguish between: (a) the child row INSERT itself being blocked by RLS (this is about the child table's RLS policy, not the FK), and (b) the FK check succeeding against the parent even when the parent row is from a different tenant (this is the covert channel). The current draft conflates these two behaviors. Desired change: split invariant #6 into two explicit sub-invariants: (6a) the child table's own INSERT policy blocks cross-tenant inserts and (6b) FK relationships between tenant-scoped tables use synthetic keys or application-layer FK enforcement rather than Postgres FK constraints, since Postgres FK enforcement bypasses RLS unconditionally.

   > quote: Referential-integrity leak tests: integration tests assert that a cross-tenant INSERT into a child table

4. **Comment on Gap C (MCP) — "visible UI confirmation before document submission."** The requirement for "visible UI confirmation before document submission" applies to MCP tool calls (which are programmatic, not UI-mediated). For MCP P1 invocations (Mario in ARC UI on behalf of a Trimble-ID user), this is achievable — the ARC UI layer can present a confirmation before invoking the tool. However, the draft does not address how the "visible UI confirmation" requirement is satisfied when the MCP invocation is triggered by ARC rather than by a human pressing a button in the Partner Submission web component. The distinction matters: for MCP-path document submission, the confirmation must happen at the ARC UI layer (above the MCP adapter), not inside the Partner Vetting service. Desired change: clarify that the "visible UI confirmation" requirement is enforced by the ARC skill-lifecycle gates (ARC-SL) at the Mario/ARC layer, not by the MCP adapter itself, and that the MCP adapter's responsibility is idempotency keys and malware scanning only.

   > quote: visible UI confirmation before document submission, malware/MIME scan at the Upload Endpoint

5. **Comment on Sources — add additional FK-bypass sources.** The confidence ledger entry for "Referential-integrity FK checks bypass RLS" currently cites only Bytebase source [24]. Two additional primary sources were retrieved this run that directly confirm this: PostgreSQL official documentation (current version, stating "foreign key references, always bypass row security") and the PostgreSQL wiki (documenting the FK side channel and recommending synthetic keys). Both should be added as new numbered sources. Desired change: add PostgreSQL official docs (current) as a new source and the PostgreSQL wiki as a new source, update the confidence ledger row for the FK bypass claim to cite all three.

   > quote: Referential-integrity FK checks bypass RLS (parent table lookup during child INSERT may see cross-tenant rows)

6. **Comment on Gap A (verifier pipeline) — model-family separation mechanism is underspecified.** The draft requires a "verifier pipeline" that is "separate, more stringent CI gate threshold" and "model context" but does not specify what architectural mechanism prevents the verifier from using the same model. In practice, if both producer and verifier pipelines call the same model API (Anthropic Claude) with different system prompts, they may share the same training data biases and blind spots. The architecture-level requirement should specify: (a) the verifier pipeline SHOULD use a different model family where feasible (e.g., an OpenAI or Gemini model as verifier against a Claude producer), or (b) where model-family alternation is not feasible, the verifier pipeline must use independently authored adversarial specifications (not generated from the same specification as the producer) and must be seeded with known-defect fixtures from previous bug reports. Without one of these mechanisms, the "independent verifier" property is aspirational. Desired change: add a sub-requirement to Gap A specifying the specific mechanism for achieving model-independence, not just the existence of a separate pipeline.

   > after: Gap A — Independent Verifier Pipeline

---

## Disagreement carryover audit

**Final-surfaced disagreements from Phase 2:**
- D-5 (MCP-only public programmatic surface vs. clean future REST endpoint): **Present in draft, correctly framed.** The "Disagreements Left Open" section accurately states both positions and notes D-5 as non-blocking.

**Resolved disagreements that re-emerged:** (none)

**New disagreements raised during review:** (none — round 1; no prior openai comments to respond to)

---

## Substantive disagreements I'm holding

(none — round 1; no prior openai position to disagree with)

---

## Drafter revision note

This is round 1. I am the drafter. OpenAI has not yet reviewed the draft. Based on my own anti-sycophancy review of the draft I authored, I identify the following items requiring revision before I can consider this ready for approval:

**(a) Changes made and where:**
No round-1 changes to the draft body yet — I am documenting issues to address in a revised draft below.

**(b) Changes considered and rejected:**
None at this stage — issues are new, not yet addressed.

**(c) Comments not yet acted on:**
All six comments above are newly raised and not yet incorporated. I will produce a revised draft addressing:
- CLAUDE-01: Add model-family separation mechanism to Gap A
- CLAUDE-02: Split RLS invariant #6 into (6a) child-insert RLS and (6b) synthetic-key requirement
- CLAUDE-03: Add machine-verifiable completion criteria for Phase 2 MCP deferral conditions
- CLAUDE-04: Upgrade CodeRabbit citation to primary source; fix "57% → 1.57x overall / 2.74x XSS-specific"
- CLAUDE-05: Clarify MCP-path consent revocation covers both HTTP and MCP surfaces
- CLAUDE-06: Add conditional resolution path for R-Claude-region

**(d) Confidence ledger changes:**
- "AI-authored PRs average 10.83 issues vs. 6.45 for human-only" → upgrade from [V] citing TwoCents (second-order) to [V]-CORROBORATED citing CodeRabbit primary source directly
- "security findings 57% more prevalent" → amend to "overall security findings 1.57x more prevalent; XSS-specific 2.74x"
- "Referential-integrity FK checks bypass RLS" → add PostgreSQL official current docs and PostgreSQL wiki as additional confirming sources, upgrade to [V]-CORROBORATED from multiple primary sources

---

## Revised draft

## Summary

The Partner Vetting architecture proposal is structurally well-suited to autonomous codegen: typed contracts at every boundary, a modular monolith, explicit state machines, row-level security tenant isolation, a Postgres-backed outbox, OpenTelemetry instrumentation, and append-only audit and billing streams together reduce the distributed-system failure modes that codegen pipelines handle worst. The document's central weakness is that it conflates *test existence* with *test quality*: generated code and generated tests can be mutually consistent and collectively wrong, which is the primary failure mode for no-human-review systems. This oracle-quality problem manifests concretely in six gaps requiring remediation before v1 ships: the absence of a mutation testing gate with a model-independent verifier pipeline, a specific RLS GUC lifecycle failure under connection pooling with an additional FK covert-channel not addressed by the current invariants, an unaddressed MCP and document-AI attack surface, an eval-set design that risks self-referential validation, a cryptographic posture that is OWASP's second preference rather than first, and a consent cache invalidation path covering only the HTTP surface (not the MCP surface) with a race condition that may violate GDPR revocation semantics. Two further gaps require targeted ADR amendments. Seven surviving open questions cannot be resolved from the material in the brief.

---

## Findings

### 1. Executive Verdict and Primary Constraint

The governing constraint is unambiguous: every line of implementation is AI-generated; automated tests are the only quality gate. This constraint is simultaneously the architecture's greatest design driver and the source of its most dangerous unexamined assumption.

**What autonomous codegen requires of the architecture:** machine-verifiable boundaries that the pipeline cannot violate without a build failure; typed contracts so that contract drift breaks the build before reaching production; lint rules enforcing invariants the pipeline cannot self-correct without a specification; and observability that surfaces drift without human intervention. The proposal provides all of these at the coarse-grained structural level.

**The primary architectural concern for no-human-review systems:** generated code, generated tests, and generated eval sets produced from the same model family can be mutually consistent and collectively wrong. CodeRabbit's primary research confirms that AI-generated code shows "significantly higher rates of logic and correctness issues (75% more common)" and "security vulnerabilities (up to 2.74x higher)" compared to human-authored code. A test suite that achieves 90% branch coverage by executing happy-path lines without asserting on boundary conditions passes CI while leaving production business-logic errors undetected. The architecture must require independently produced, adversarially oriented quality gates — not merely more tests of the same character as the code they validate.

---

### 2. What the Architecture Gets Right

**Typed contracts at every boundary** are the single most important enabler. The `mcp-surface.json` schema, `internal-http.openapi.yaml`, TypeScript interfaces at bounded-context entry points, and component prop contracts as JSON Schemas constitute the contract layer that makes the entire codegen-first model tractable. Schema-first development — where editing a schema regenerates the implementation skeleton and contract tests, and where failing tests refuse the merge — is the correct architecture for a pipeline with no human PR review.

**The modular monolith decision** eliminates the distributed-system failure modes that autonomous codegen handles worst: network-boundary authentication, cross-service schema drift, partial-failure reasoning in distributed transactions, and independently deployed services whose contract tests can silently diverge. A system where four bounded contexts (Profile & Consent, Document Intake & Authentication, Rules, Network Signal stub) are enforced by import-linter rules rather than network calls achieves logical separation without distributed-systems complexity.

**Explicit state machines named and modeled** prevent codegen from leaving the domain's most critical invariants implicit. The Submission state machine (`Pending → Missing → Approved → Rejected → Expired`), the Vetting Run state machine, and the Grant lifecycle are the invariants most likely to be broken by a codegen pipeline operating without domain expertise. Naming them, specifying their transitions, and making them the subject of property tests is architecturally correct.

**PostgreSQL RLS as the tenant isolation mechanism** is the correct default-deny approach: PostgreSQL official documentation states that "referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security to ensure that data integrity is maintained" — but for all other queries, if RLS is enabled and no applicable policy exists, access is denied by default. This means the codegen pipeline's failures (a forgotten `WHERE tenant_id = ?` clause) fail closed rather than open.

**The Postgres outbox** for at-least-once internal event delivery between contexts is correct for v1 load. The `SELECT FOR UPDATE SKIP LOCKED` pattern is explicitly documented as suitable for queue-like table access, providing the at-least-once delivery guarantee without an external message broker.

**OpenTelemetry as vendor-neutral instrumentation** is correct and swap-friendly: the same SDK serves traces, metrics, and logs regardless of which backend (Datadog, Grafana, Azure Monitor, New Relic) the engineer-review pass selects. This is the right architecture for a codegen-first system because the instrumentation code is stable and the backend decision is deferred.

**The lint rule inventory** is load-bearing. The specific rules named — no `UPDATE` against `audit_events` or `billable_events`, no raw queries bypassing RLS, no PII in logs via typed values, no cross-context imports outside the published interface, every state-changing handler emits ≥1 outbox row in the same transaction — each catch a class of bug that branch-coverage tests alone cannot reliably detect because they depend on the *absence* of a call or statement. This is the correct architecture for codegen-first systems: make illegal states unrepresentable at the lint level.

**Append-only audit and billable event streams** are essential for a codegen-first system because they are the one source of ground truth about what the system actually did that a future human or automated analysis can recover from. No generated implementation can erase audit history.

---

### 3. Gap A — Independent Verifier Pipeline

The current proposal has a single code-generation pipeline. The same pipeline that produces implementation also produces tests from the same specifications and model family. This is the oracle-quality failure mode: the two artifacts can pass each other's checks while both being wrong in the same direction.

The architecture must add a **separate verifier pipeline** that consumes the same specification as the producer pipeline but executes in a distinct model context. Its purpose is to break the producer's output, not to confirm it.

**Model-independence requirement:** The verifier pipeline must achieve genuine adversarial independence through at least one of:
- (a) **Model-family alternation** (preferred): the verifier pipeline uses a different LLM family than the producer pipeline. If the producer uses Anthropic Claude, the verifier uses an OpenAI or Gemini model, and vice versa. Different training data and alignment procedures produce materially different blind spots.
- (b) **Independently authored adversarial specifications** (required when model-family alternation is not feasible): verifier pipeline inputs are specifications authored by a human or by a separate adversarial process, not generated from the same system prompt chain as the producer. The verifier pipeline must additionally be seeded with known-defect fixtures from previous production bug reports.

Where neither (a) nor (b) is achievable for a specific test category, the gap must be documented in the evidence bundle and that test category must be treated as unverified, not as passing.

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

[U] Branch coverage ≥90% is a necessary but insufficient quality gate for AI-generated code. The Register's reporting on the CodeRabbit study confirms that AI-generated pull requests include "about 10.83 issues each, compared with 6.45 issues in human-generated PRs." [U] Research shows tests can achieve 100% line and branch coverage while scoring only 4% on mutation testing, because the tests execute code paths without asserting on boundary conditions. A test suite with 95% line coverage but only 38% mutation score provides false confidence.

**Mutation score targets:**
- ≥80% for all generated code in the codebase
- ≥90% for **critical core modules**: Authorization, Consent/Grants, RLS session binding, State machines (Vetting Run, Submission, Grant lifecycle), Coverage Report Builder, Rules Evaluator, Audit/Billable Event Emission, Expiry/Reverification logic, Crypto/Key Management, MCP state-changing authorization

**The critical core / generated shell split** must be enforced structurally, not by convention:
- Critical core lives in a named package with separate module labels
- A separate, more stringent CI gate threshold applies to every merge that touches any critical core module or any public contract it exposes
- Import-graph rules enforced by the import-linter prevent generated shell modules from being imported by critical core
- Critical core tests must include: property tests on every state transition (not just unit tests), fuzz tests on parser inputs, policy-denial tests for every authorization path, and the stricter mutation score target above

---

### 5. Gap B — RLS GUC Lifecycle — Eight Mandatory Invariants

The proposal correctly chooses PostgreSQL RLS as the tenant isolation mechanism and specifies the per-request middleware pattern (`pv.current_tenant` and `pv.current_principal_role` GUCs). However, the implementation detail that makes this safe under connection pooling is absent, and it is precisely the implementation detail that a codegen pipeline will get wrong.

In transaction mode pooling (the recommended production mode for connection efficiency), `SET` persists for the lifetime of the session on the server side, meaning a connection returned to the pool by tenant A and subsequently acquired by tenant B retains A's GUC values unless the application explicitly handles this. The correct pattern — confirmed by Heroku's authoritative PgBouncer documentation — is `SET LOCAL`, which scopes the variable to the current transaction and resets automatically when the transaction ends.

Additionally, the proposal's RLS policy pattern does not specify `FORCE ROW LEVEL SECURITY`. PostgreSQL official documentation states: "Table owners normally bypass row security as well, though a table owner can choose to be subject to row security with `ALTER TABLE ... FORCE ROW LEVEL SECURITY`."

**Eight architecture-level invariants (not design-doc concerns):**

1. `ALTER TABLE ... FORCE ROW LEVEL SECURITY` on all tenant-scoped tables, ensuring the application role cannot bypass policies through table ownership
2. No `BYPASSRLS` attribute on the application database role
3. All tenant GUC assignments (`pv.current_tenant`, `pv.current_principal_role`) use `SET LOCAL` inside an explicit transaction boundary — never bare `SET` followed by `RESET` on pool return
4. Connection pool configured in transaction mode (not session mode); this is the required complement to `SET LOCAL`
5. Migration-time policy checks: schema migration CI asserts that every tenant-scoped table has an active RLS policy before the migration is accepted
6. **(6a) Child-table INSERT policies:** Integration tests assert that a cross-tenant INSERT into a child table — where the INSERT itself is blocked by the child table's own RLS policy — fails with a policy violation, not silently succeeds. **(6b) FK side-channel mitigation:** The PostgreSQL official documentation explicitly states that "foreign key references *always* bypass row security" and warns that "care must be taken... to avoid 'covert channel' leaks of information through such referential integrity checks." The PostgreSQL wiki documents this as "The FOREIGN KEY side channel" and recommends "synthetic keys or no foreign keys at all... for FK relationships between RS tables." Therefore: FK relationships between tenant-scoped tables must use synthetic keys enforced at the application layer (not Postgres FK constraints), OR the FK constraint must be replaced by an application-layer assertion that includes an explicit tenant-check on the parent row. This is a schema-level architectural requirement, not a test requirement.
7. Pool-reuse negative test: a test acquires a connection under tenant A, executes a query, returns the connection to the pool, re-acquires under tenant B, and asserts that B cannot read A's rows — this test must be in the codegen pipeline's invariant set

These eight are codegen-pipeline invariants enforced by lint and integration tests, not prose in the architecture document.

---

### 6. Gap C — MCP and Document AI Attack Surface

The official MCP specification states that tools are "model-controlled, meaning that the language model can discover and invoke tools automatically," and recommends that "there SHOULD always be a human in the loop with the ability to deny tool invocations." Security researchers have documented multiple outstanding MCP security issues including prompt injection, tool permissions enabling data exfiltration, and lookalike tools that can silently replace trusted ones. OWASP has established an MCP Top 10 risk classification framework covering command injection, context injection, confused deputy attacks, and supply chain risks.

The proposal treats the MCP adapter as "intentionally thin — no business logic, only protocol translation and authentication." This is correct for what the adapter *does*, but the proposal contains no architecture-level defense for what an adversary *can put into* the data the adapter processes.

**Required architectural addition: Document AI Quarantine Layer**

The planning model (Claude, in the document AI role) must never read raw carrier document content directly. The architecture must add a **Document AI Quarantine Layer** as a named component in Document Intake & Authentication: a separate, tool-incapable model invocation context that reads carrier document bytes and returns only a typed extraction package. The planning model receives only the typed extraction package, not the document content. This implements the dual-LLM quarantine pattern: the quarantined model handles untrusted bytes but has no tool-calling capability; the planning model makes decisions but never sees attacker-controlled content.

This component sits between the Document Store Adapter and the Document AI Provider Abstraction. Its inputs are: `(blob_uri, check_id, check_version, extraction_schema)`. Its outputs are a `TypedExtractionPackage` that strictly conforms to the check's output schema. It never accepts free-form prompts from the carrier document; it only accepts catalog-authored, versioned extraction schemas.

**v1 MCP write-tool scope:**
- `submit_document` and `submit_attestation` are available in v1 under **P1/known Trimble-ID actor context only** (not P3 external-agent context), with: malware/MIME scan at the Upload Endpoint, idempotency keys on every call, Document AI Quarantine Layer processing, adversarial document fixtures in the eval suite, and **no automatic terminal approval** (`Approved` state) reachable exclusively via the MCP path. The "visible UI confirmation" requirement for these tools is enforced at the **ARC/Mario layer** (above the MCP adapter), not inside Partner Vetting's MCP adapter itself — the adapter's responsibility is idempotency keys and malware scanning only.
- **Deferred to Phase 2:** `create_ruleset`, `grant_visibility`, `revoke_visibility`, and `start_vetting_run` via MCP, pending completion of four Phase 2 gates with machine-verifiable criteria: (i) per-tool capability scope defined in `mcp-surface.json` with an explicit `allowed_callers` field; (ii) policy-decision logs for every write-tool invocation reaching 100% coverage in integration tests; (iii) adversarial test suite covering at minimum the OWASP MCP Top 10 risk categories with 0 unmitigated critical findings; and (iv) ARC-SL automated quality gates for the new tools passing at `published` confidence for 30 consecutive days in a staging environment.
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

The proposal commits to "Fernet AES-128-CBC + HMAC-SHA256" as the application-layer envelope encryption scheme. Fernet is a well-established Python cryptography library construct that implements encrypt-then-MAC using AES-128-CBC and HMAC-SHA256. This is a sound construction — it is not broken. However, it is OWASP's second preference, not first. The OWASP Cryptographic Storage Cheat Sheet states that GCM and CCM modes "should be used as a first preference." Fernet's CBC mode with separate MAC is the "CTR or CBC mode" fallback path, not the AEAD-first path.

**Required amendment:**
- Replace Fernet as the architecture-specified default with **AES-GCM** (or equivalent AEAD mode such as XChaCha20-Poly1305), which provides confidentiality, integrity, and authenticity in a single construction with a single key
- Fernet (AES-128-CBC + HMAC-SHA256) remains permitted **if and only if** an explicit Trimble internal cryptographic standard mandating it is cited in ADR-020; if no such citation is provided, AES-GCM is the required default
- Per-profile envelope keys in Azure Key Vault and the GDPR crypto-erasure mechanism (destroying the envelope key on profile deletion, rendering document blobs and consent records unreadable while preserving audit metadata) are architecturally correct and unchanged

This is a named open question (R7) in the surviving open questions section.

---

### 9. Gap F — Consent Cache Invalidation Race (Both HTTP and MCP Surfaces)

The architecture specifies a 5-minute Redis TTL for the IdP attribute cache and by implication for the consent state cache (the `is_granted(profile_id, tenant_id, section)` read path). The proposal's consent revocation semantic is "freeze on revoke: future reads are denied." These two specifications are in conflict.

When a carrier revokes consent at T=0, any tenant Status Card rendered before T+5 minutes may read stale cached grant state and display data the carrier has explicitly withdrawn consent for. In GDPR jurisdictions, the right to object may require immediate effect; a 5-minute window of stale consent state may constitute a compliance failure.

**Required architecture-level invariant in the Consent Manager specification, covering both HTTP and MCP invocation surfaces:**

On grant revocation — whether triggered through the internal HTTP path (Partner Profile web component) or through the MCP `revoke_visibility` tool — the Consent Manager must **synchronously invalidate** the `(profile_id, tenant_id, section)` Redis cache key as part of the same request handler, before returning any success response to the caller. Specifically:
- The Redis `DEL` call executes within the same request handler as the DB write, before the response is sent, on both the HTTP and MCP code paths
- This is not deferred to an async outbox event; no success response (200 HTTP or MCP result) may be sent until both the DB write and the Redis invalidation have completed
- If Redis is unavailable at revocation time: the DB write commits and the consent revocation is durably recorded; the audit event records `cache_invalidation_failed: true`; a conservative negative-cache entry is written to Redis on reconnect (TTL ≤60 seconds); an alert fires immediately; reads fail closed during the Redis unavailability window

The 5-minute TTL is acceptable for IdP attribute caching (user name, email — these are informational). It is not acceptable as the only freshness mechanism for authorization/consent state that has a legal revocation semantic.

---

### 10. Required ADR Amendments

The following amendments to the existing ADR set are required by the findings above:

**ADR-009 (Tenant isolation: PostgreSQL row-level security):** Add the eight mandatory GUC-lifecycle, `FORCE ROW LEVEL SECURITY`, and FK-covert-channel mitigation invariants described in Gap B as explicit architectural commitments, not design-doc delegations.

**ADR-010 (MCP programmatic surface):** Add v1 write-tool scope restriction (P1-only for `submit_document`/`submit_attestation`; Phase 2 for tenant-admin writes), the per-tool capability scope requirement with machine-verifiable Phase 2 completion criteria for all write-capable tools, and clarification that the "visible UI confirmation" requirement is enforced at the ARC/Mario layer.

**ADR-013 (Document AI provider):** Add the Document AI Quarantine Layer as a required architectural component with the typed extraction package boundary specification.

**ADR-014 (Testing framework):** Add mutation score thresholds (≥80% general, ≥90% critical core), the critical core / generated shell split with separate CI gates, the verifier pipeline requirement with the model-independence requirement, and the evidence bundle release gate with its required categories.

**ADR-015 (Secret and key management):** Replace Fernet as the default with AES-GCM (AEAD-first per OWASP); permit Fernet only with explicit Trimble internal cryptographic standard citation.

**ADR-017 (Consent model):** Add synchronous Redis cache invalidation on revocation as an architecture-level invariant of the Consent Manager covering both internal HTTP and MCP `revoke_visibility` invocation paths, not a design-doc implementation detail.

**New ADR-021 (Mutation testing gate):** Commits the critical core membership list, the ≥80%/≥90% threshold targets, the enforcement mechanism (separate CI gate), and the rationale.

**New ADR-022 (MCP write-tool v1 scope):** Commits the P1-only restriction for partner-initiated write tools, the Phase 2 deferral for tenant-admin write tools, the four machine-verifiable Phase 2 completion criteria, and the clarification that "visible UI confirmation" is an ARC-layer, not MCP-adapter, concern.

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
  <rect x="290" y="260" width="200" height="125" rx="10" fill="#fee2e2" stroke="#b91c1c" stroke-width="1.5"/>
  <text x="390" y="288" text-anchor="middle" font-size="13" font-weight="bold" fill="#7f1d1d">Verifier Pipeline</text>
  <text x="390" y="305" text-anchor="middle" font-size="10" font-style="italic" fill="#991b1b">(different model family or</text>
  <text x="390" y="318" text-anchor="middle" font-size="10" font-style="italic" fill="#991b1b"> independent adversarial specs)</text>
  <text x="390" y="333" text-anchor="middle" font-size="11" fill="#991b1b">mutation tests · fuzz inputs</text>
  <text x="390" y="348" text-anchor="middle" font-size="11" fill="#991b1b">policy-denial · injection fixtures</text>
  <text x="390" y="363" text-anchor="middle" font-size="11" fill="#991b1b">migration rollback tests</text>

  <!-- Arrow producer → evidence -->
  <line x1="490" y1="105" x2="570" y2="170" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>
  <!-- Arrow verifier → evidence -->
  <line x1="490" y1="322" x2="570" y2="270" stroke="#475569" stroke-width="1.5" marker-end="url(#arr)"/>

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
  <rect x="30" y="430" width="160" height="100" rx="8" fill="#ede9fe" stroke="#6d28d9" stroke-width="1.2"/>
  <text x="110" y="450" text-anchor="middle" font-size="11" font-weight="bold" fill="#4c1d95">RLS Invariants</text>
  <text x="110" y="467" text-anchor="middle" font-size="9.5" fill="#5b21b6">SET LOCAL + tx mode</text>
  <text x="110" y="482" text-anchor="middle" font-size="9.5" fill="#5b21b6">FORCE ROW LEVEL SEC.</text>
  <text x="110" y="497" text-anchor="middle" font-size="9.5" fill="#5b21b6">no BYPASSRLS app role</text>
  <text x="110" y="512" text-anchor="middle" font-size="9.5" fill="#5b21b6">synthetic keys for FK</text>
  <text x="110" y="527" text-anchor="middle" font-size="9.5" fill="#5b21b6">pool-reuse negative test</text>

  <!-- MCP Lane -->
  <rect x="205" y="430" width="165" height="100" rx="8" fill="#fce7f3" stroke="#9d174d" stroke-width="1.2"/>
  <text x="287" y="450" text-anchor="middle" font-size="11" font-weight="bold" fill="#831843">MCP Zero-Trust</text>
  <text x="287" y="467" text-anchor="middle" font-size="9.5" fill="#9d174d">P1-only writes (v1)</text>
  <text x="287" y="482" text-anchor="middle" font-size="9.5" fill="#9d174d">quarantine layer</text>
  <text x="287" y="497" text-anchor="middle" font-size="9.5" fill="#9d174d">per-tool capability scope</text>
  <text x="287" y="512" text-anchor="middle" font-size="9.5" fill="#9d174d">confirm at ARC layer</text>
  <text x="287" y="527" text-anchor="middle" font-size="9.5" fill="#9d174d">admin writes → Phase 2</text>

  <!-- Document AI Lane -->
  <rect x="385" y="430" width="165" height="100" rx="8" fill="#fff7ed" stroke="#c2410c" stroke-width="1.2"/>
  <text x="467" y="450" text-anchor="middle" font-size="11" font-weight="bold" fill="#7c2d12">Document AI</text>
  <text x="467" y="467" text-anchor="middle" font-size="9.5" fill="#9a3412">typed extraction pkg</text>
  <text x="467" y="482" text-anchor="middle" font-size="9.5" fill="#9a3412">no raw carrier text → LLM</text>
  <text x="467" y="497" text-anchor="middle" font-size="9.5" fill="#9a3412">≥40/60% real eval samples</text>
  <text x="467" y="512" text-anchor="middle" font-size="9.5" fill="#9a3412">diff model-family eval</text>
  <text x="467" y="527" text-anchor="middle" font-size="9.5" fill="#9a3412">injection fixtures required</text>

  <!-- Critical Core Lane -->
  <rect x="565" y="430" width="165" height="100" rx="8" fill="#ecfdf5" stroke="#065f46" stroke-width="1.2"/>
  <text x="647" y="450" text-anchor="middle" font-size="11" font-weight="bold" fill="#064e3b">Critical Core</text>
  <text x="647" y="467" text-anchor="middle" font-size="9.5" fill="#065f46">mutation ≥90% gate</text>
  <text x="647" y="482" text-anchor="middle" font-size="9.5" fill="#065f46">property: all transitions</text>
  <text x="647" y="497" text-anchor="middle" font-size="9.5" fill="#065f46">separate CI gate threshold</text>
  <text x="647" y="512" text-anchor="middle" font-size="9.5" fill="#065f46">import-graph enforcement</text>
  <text x="647" y="527" text-anchor="middle" font-size="9.5" fill="#065f46">verifier: diff model family</text>

  <!-- Consent + Outbox Lane -->
  <rect x="745" y="430" width="185" height="100" rx="8" fill="#f0fdf4" stroke="#166534" stroke-width="1.2"/>
  <text x="837" y="450" text-anchor="middle" font-size="11" font-weight="bold" fill="#14532d">Consent + Outbox</text>
  <text x="837" y="467" text-anchor="middle" font-size="9.5" fill="#166534">sync cache invalidation</text>
  <text x="837" y="482" text-anchor="middle" font-size="9.5" fill="#166534">on revoke (HTTP + MCP)</text>
  <text x="837" y="497" text-anchor="middle" font-size="9.5" fill="#166534">pre-200 DEL required</text>
  <text x="837" y="512" text-anchor="middle" font-size="9.5" fill="#166534">outbox: partial idx + DLQ</text>
  <text x="837" y="527" text-anchor="middle" font-size="9.5" fill="#166534">n_dead_tup alert required</text>

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

Seven questions cannot be resolved from the material available in this run and require specific inputs:

**R7 — Trimble internal cryptographic standard (Fernet vs. AES-GCM):** Does Trimble's TTC platform or the ARC integration posture mandate Fernet specifically, or does it mandate only "application-layer encryption with Trimble-managed keys"? If the former, ADR-020 keeps Fernet with an internal standard citation. If the latter, AES-GCM becomes the required default immediately. Resolution requires: Trimble Security team sign-off or ARC integration documentation specifying the approved cryptographic profile.

**R5 — ARC-SL degradation thresholds and per-tool configurability:** What confidence level triggers a skill demotion from `published` to `degraded`, and is this threshold configurable per tool? This determines whether R5 (ARC demoting Partner Vetting without warning) can be mitigated by per-tool threshold configuration or only by overall skill health monitoring. Resolution requires: ARC skill lifecycle technical documentation (referenced but not yet provided in the brief).

**R-Knauf — Knauf carrier population non-EU country distribution:** What proportion of Knauf's carrier panel consists of carriers from Albania, Bosnia, Montenegro, Norway, Serbia, Switzerland, Turkey, or Ukraine? This determines whether the Phase 1 non-EU check catalog (eight priority countries) is sufficient for the Knauf launch or whether additional variants are needed immediately. Resolution requires: the Knauf workshop referenced in the brief.

**R4 — Applied AI Safety & Enablements audit schema:** What is the target schema for the audit export? The proposal defers to this team's standard "once it ships," but the architecture's audit event schema must be forward-compatible. Until this schema is published, the export contract is a documented pull interface — but forward-compatibility cannot be verified. Resolution requires: the Applied AI Safety & Enablements team's published audit standard.

**R-Claude-region — Anthropic Claude regional availability in Azure West Europe:** Does Anthropic provide API endpoints in Azure West Europe with acceptable latency and data-residency properties compatible with a Knauf (German shipper) production deployment? If not, the fallback provider must be elevated. **Conditional resolution path:** if Anthropic cannot satisfy EU data residency, Azure Document Intelligence is elevated from "rate-limit fallback" to "co-primary" for document extraction steps, and the capability gap for natural-language cross-reference reasoning (where Document Intelligence is demonstrably weaker than Claude) must be addressed by adding a second-pass reasoning step using an EU-data-residency-compliant hosted model. This requires the architecture to explicitly name the fallback model and its confidence calibration parameters in the check catalog entry for each affected check. Resolution requires: current Anthropic API regional documentation and Trimble data-residency policy for EU customer data.

**R-verifier-model — Model family available for verifier pipeline:** What model families does Trimble have access to beyond Anthropic Claude (used as the proposed production document AI provider)? If OpenAI or Gemini access is not available, the model-family alternation path for the verifier pipeline cannot be used, and independently authored adversarial specifications become the mandatory mechanism. Resolution requires: confirmation of Trimble's AI provider access and ARC skill-lifecycle gate constraints.

**R-outbox-dlq — Outbox table dead-letter handling:** What is the operational procedure when an outbox row fails delivery to all in-process subscribers (audit, billable, notification)? The architecture specifies the outbox pattern and `n_dead_tup` monitoring but does not specify the dead-letter handling contract: after how many delivery failures does a row move to DLQ, who is notified, and what is the recovery procedure? This is a design-doc concern that becomes architectural when the audit emitter is involved, because a silently dropped audit-outbox event violates the "every state-changing operation emits ≥1 audit row" invariant. Resolution requires: the outbox design doc (not yet in the brief materials).

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
| R-Claude-region | Does Anthropic provide API endpoints in Azure West Europe with acceptable latency and EU data-residency properties for a German shipper deployment? If not, what is the fallback co-primary and its capability calibration? | Current Anthropic regional API documentation; Trimble EU data-residency policy | Requires live API documentation check; not in brief |
| R-verifier-model | What model families does Trimble have access to beyond Anthropic Claude for use as an independent verifier pipeline? | Trimble AI provider access confirmation; ARC constraints | Not determinable from brief materials |
| R-outbox-dlq | After how many outbox delivery failures does a row move to DLQ, and what is the recovery procedure when the audit emitter is involved? | Outbox design doc | Not yet in brief materials |

---

## Sources

1. Heroku Dev Center — Best Practices for PgBouncer Configuration: https://devcenter.heroku.com/articles/best-practices-pgbouncer-configuration
2. PostgreSQL Documentation — Row Security Policies (current): https://www.postgresql.org/docs/current/ddl-rowsecurity.html
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
33. CodeRabbit — State of AI vs Human Code Generation Report (primary): https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report
34. The Register — AI-authored code needs more attention, contains worse bugs: https://www.theregister.com/2025/12/17/ai_code_bugs/
35. Bytebase — PostgreSQL Row Level Security Footguns: https://www.bytebase.com/blog/postgres-row-level-security-footguns/
36. PostgreSQL wiki — Row-security (design notes, FK side channel): https://wiki.postgresql.org/wiki/Row-security
37. AWS Blog — Multi-tenant data isolation with PostgreSQL Row Level Security: https://aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security/

---

## Confidence Ledger

| Claim | Tag | Signal | Source notes |
|---|---|---|---|
| Heroku official docs: "Any changes to session state via SET must only be made with `SET LOCAL`... Never use `SET SESSION` or `SET` alone" | [V] | CORROBORATED | Source [1], retrieved this run; authoritative PgBouncer configuration documentation |
| In transaction-mode pooling, `SET` persists to session end and leaks tenant GUC values between clients if not scoped with `SET LOCAL` | [V] | CORROBORATED | Sources [1], [22], [23]; multiple authoritative sources confirm this failure mode |
| `FORCE ROW LEVEL SECURITY` is required when the application role is the table owner; owners bypass RLS by default | [V] | CORROBORATED | Sources [2], [35], [37]; PostgreSQL official docs, Bytebase footguns, AWS blog all confirm |
| PostgreSQL RLS default-deny: if RLS is enabled and no policy exists, access is denied | [V] | CORROBORATED | Source [2]; official PostgreSQL documentation |
| OWASP Cryptographic Storage: GCM and CCM are first preference; "should be used as a first preference" | [V] | CORROBORATED | Source [5], retrieved this run; canonical OWASP guidance |
| Fernet uses AES-128-CBC + HMAC-SHA256 (encrypt-then-MAC, not AEAD) | [V] | CORROBORATED | Source [6]; Python cryptography library official documentation |
| Fernet is OWASP second preference (CBC mode with separate MAC), not first preference (GCM/CCM AEAD) | [V] | CORROBORATED | Sources [5], [6]; follows directly from first two claims |
| MCP tools specification states tools are "model-controlled" and that "there SHOULD always be a human in the loop with the ability to deny tool invocations" | [V] | CORROBORATED | Source [7], retrieved this run; official MCP specification 2025-06-18 |
| MCP authorization is optional for implementations | [V] | CORROBORATED | Source [8]; official MCP authorization specification |
| Security researchers documented multiple outstanding MCP security issues including prompt injection and lookalike tools (April 2025) | [V] | CORROBORATED | Source [10]; Wikipedia article on MCP with citation to April 2025 researcher analysis |
| OWASP MCP Top 10 project has been established covering command injection, context injection, confused deputy attacks, supply chain risks | [V] | CORROBORATED | Source [13]; SentinelOne article referencing the official OWASP MCP Top 10 project |
| AI-generated pull requests average 10.83 issues vs. 6.45 for human-only; logic/correctness errors 75% more common (1.75x); overall security findings 1.57x more prevalent; XSS-specific security findings 2.74x more prevalent | [V] | CORROBORATED | Sources [33] (CodeRabbit primary, December 2025) and [34] (The Register corroboration), both retrieved this run. Prior ledger entry cited [16] (TwoCents, second-order); upgraded to primary sources. |
| Tests can achieve 100% line/branch coverage while scoring only 4% on mutation testing | [U] | — | Claim from [16] citing HumanEval-Java research; primary paper not retrieved; retained as [U] |
| Mutation score ≥80% for business logic, ≥90% for critical core modules is a recommended threshold | [V] | CORROBORATED | Source [20]; industry threshold guidance corroborated by Stryker documentation [15] |
| Meta's ACH tool (FSE 2025) uses LLM-based mutation testing to overcome barriers to scale | [V] | CORROBORATED | Source [19]; Meta Engineering blog post on FSE 2025 keynote |
| "SELECT FOR UPDATE SKIP LOCKED" is documented as usable to avoid lock contention with multiple consumers in a queue-like table | [V] | CORROBORATED | Source [4]; official PostgreSQL documentation |
| The modular monolith eliminates the distributed-system failure modes autonomous codegen handles worst | [U] | — | Architectural reasoning; no direct primary source; consistent with ADR-008's stated rationale |
| The Document AI Quarantine Layer (dual-LLM quarantine pattern) is