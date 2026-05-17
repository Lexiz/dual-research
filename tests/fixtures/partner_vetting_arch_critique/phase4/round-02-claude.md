## Answers to openai's prior comments

**OAI-1 (missing claim-level [V]/[U] tags):** Accepted. The Confidence Ledger approach does not satisfy the protocol's requirement for inline tagging at claim level. The revised draft adds [V]/[U] tags throughout the Findings sections.

**OAI-2 (false FK/RLS invariant):** Accepted. The prior draft incorrectly stated "RLS blocks the parent SELECT during the FK check." This is factually wrong. [V] PostgreSQL documentation states referential integrity checks bypass row security. The correct framing — bidirectional FK/RLS vulnerability where FK bypass creates a covert channel *and* child inserts can fail because RLS hides parent rows — was already in the revised draft from round 1. The specific false sentence has been corrected.

**OAI-3 (citation numbering and inline citations):** Accepted. The phantom "source [39]" reference does not exist in this draft's sources list and is removed. Inline numbered citations are added throughout the Findings sections. The Confidence Ledger is aligned with the Sources list.

**OAI-4 (AI code quality figures attribution):** Accepted. The 10.83 vs 6.45 figures are attributed to the CodeRabbit December 2025 analysis as cited via secondary source [16] (TwoCents Software). The claim is softened from a general property assertion to a specific report citation.

**OAI-5 (quarantine layer framing):** Accepted. "Current state-of-the-art" is replaced with "this architecture recommends" framing, backed by the MCP risk sources.

**OAI-6 (process artifacts in draft):** Accepted. All pre-document process sentences are removed.

**D-OAI-1 (RLS referential-integrity handling disagreement):** Resolved in openai's favor. [V] The PostgreSQL documentation is unambiguous: referential integrity checks bypass row security. The bidirectional framing in the revised round-1 draft correctly names both directions without the false "RLS blocks parent SELECT" claim. The invariants now correctly require opaque synthetic FK keys and scoped unique constraints as the mitigation — not reliance on RLS to prevent FK resolution.

---

## Issue ledger (delta + currently open)

**C-1** — `resolved` — Mutation testing gate tool family named (Stryker.js/TypeScript; go-mutesting/Go, conditional on ADR-001). ADR-021 added to required amendments.

**C-2** — `resolved` — Critical core / generated shell split enforcement mechanism specified: named package with separate CI gate threshold, import-linter rule enforcement. Added to Gap A prose.

**C-3** — `resolved` — Document AI Quarantine Layer added as a named component in §6.2 (Document Intake & Authentication) component inventory, not just gap prose.

**C-4** — `resolved` — Consent cache invalidation rewritten as an architectural invariant ("Consent revocation has immediate effect: between the moment the Consent Manager returns a successful revocation response...") rather than an implementation prescription.

**C-5** — `resolved` — Verifier pipeline owner assigned: skills team. Added explicitly in Gap A.

**C-6** — `resolved` — RLS FK leak upgraded to [V]: official PostgreSQL documentation retrieved this run confirms FK integrity checks bypass RLS; Bytebase footguns article confirms the bidirectional failure. The "RLS blocks parent SELECT" false claim corrected.

**C-7** — `resolved` — R-Claude-region answered via web search: direct Anthropic API has no EU-only inference geography; AWS Bedrock EU inference profiles are confirmed; Foundry/Azure is "Coming 2026." Removed from Open Questions; added as Gap E concrete architectural constraint with ADR-013 amendment.

**C-8** — `resolved` — ADR-023 (Evidence Bundle Release Gate) added to required ADR amendments with Context/Decision/Consequences structure.

**C-9** — `resolved` — Outbox dead-letter path and `n_dead_tup` alert moved to §9.2 prose (Stability patterns), not only SVG.

**OAI-1** — `resolved` — Claim-level [V]/[U] tags added throughout Findings sections in revised draft.

**OAI-2** — `resolved` — False FK/RLS invariant corrected; bidirectional framing retained with correct mechanistic explanation.

**OAI-3** — `resolved` — Phantom source [39] removed; inline citations added; Confidence Ledger aligned with Sources list.

**OAI-4** — `resolved` — 10.83 vs 6.45 figures attributed to CodeRabbit December 2025 analysis via secondary source [16]; framing softened to specific report citation.

**OAI-5** — `resolved` — "Current state-of-the-art" replaced with "this architecture recommends" framing.

**OAI-6** — `resolved` — Process artifacts removed from draft opening.

**D-OAI-1** — `resolved` — Conceded to openai; invariants corrected to require composite FK keys and scoped unique constraints rather than relying on RLS blocking FK resolution.

No currently open issues remain from prior rounds.

---

## Evidence checked this round

- **New research performed:** (none — all material claims already verified in prior round; no new factual questions arose from resolving OAI comments)

- **Claims checked against existing sources:**
  - The corrected RLS/FK bidirectional framing (FK integrity checks bypass RLS; child insert can fail because RLS hides parent rows) is backed by source [2] (official PostgreSQL docs) and source [24] (Bytebase footguns) — both retrieved in prior round. Confirmed no change needed.
  - The "SET LOCAL" requirement under transaction pooling is backed by source [1] (Heroku PgBouncer docs) — already [V].
  - OWASP GCM-first preference backed by source [5] — already [V].
  - AWS Bedrock EU inference profiles backed by source [36] — already [V].
  - MCP model-controlled tools and human-in-loop recommendation backed by source [7] (official MCP spec) — already [V].

- **Factual issues found:** (none new)

- **No new research because:** all new research was performed in prior round; this round only addresses editorial and tagging corrections from OAI comments with claims already sourced.

- **Corroboration on the other agent's claims:**
  - **[V] claim — PostgreSQL referential integrity checks bypass row security:** corroborated by source [2], retrieved prior round. This is the basis for D-OAI-1 resolution. [V]
  - **[V] claim — `SET LOCAL` required under transaction pooling:** corroborated by source [1], retrieved prior round. [V]
  - **[V] claim — AI-authored PRs average 10.83 issues (CodeRabbit report, cited via InfoWorld):** secondary source [16] (TwoCents, citing CodeRabbit December 2025 analysis) corroborates the figure. OAI-4 resolution softens from normative claim to specific report citation — appropriate given the source chain. [V] via secondary.
  - **[U] claim — eval sets from same model family are self-referential:** plausible architectural reasoning; no primary empirical source retrieved. Remains [U] with architectural reasoning label. No objection to leaving it [U] with explicit label.
  - **[U] claim — consent revocation immediate-effect is GDPR-relevant:** legal claim; architectural reasoning only. Remains [U, stale: legal review required]. Appropriate.

---

## Comments on the current draft

1. **Location: Gap A / mutation testing. Issue: The evidence bundle gate ownership is stated twice with different owners.** Gap A says "owned by the skills team" for the verifier pipeline, and the evidence bundle ADR-023 says "ownership (infrastructure/self-healing team)." These are two different things (verifier pipeline vs. evidence bundle gate) but the draft does not make the split explicit enough. A reader could reasonably conclude the skills team owns the evidence bundle gate. **Specific change requested:** Add one clarifying sentence in Gap A: "The verifier pipeline is owned by the skills team; the evidence bundle gate (ADR-023) is owned by the infrastructure/self-healing team. The skills team produces adversarial test artifacts; the infrastructure team enforces that all artifact categories are present and signed before release proceeds."

2. **Location: Gap E / Anthropic EU data residency. Issue: The ADR-013 amendment section says "or GCP Vertex AI EU regional endpoints (europe-west1)" but the TTC platform is Azure-native, and adding a GCP dependency has non-trivial credential management, billing, and data-transfer implications.** The draft presents GCP Vertex AI as an equally straightforward alternative without noting the cross-cloud cost. **Specific change requested:** Add a parenthetical: "(note: GCP Vertex AI introduces a cross-cloud dependency outside the TTC Azure catalog; prefer AWS Bedrock EU as the primary path; GCP Vertex AI is a fallback if Bedrock EU capacity is insufficient for a given check definition)."

3. **Location: Confidence Ledger. Issue: The "FK bypass creates covert-channel" claim cites "Source [14] PostgreSQL wiki" but source [14] in the Sources list is "Zenity — Securing the Model Context Protocol."** The PostgreSQL wiki reference should be source [38] per the Sources list. **Specific change requested:** Correct the Confidence Ledger row to read "Source [38] PostgreSQL Wiki" not "Source [14]."

4. **Location: Gap B — RLS invariants. Issue: The eight invariants are listed as numbered items but invariants 6 and 7 (UUID FKs; scoped unique constraints) are the *primary* mitigations for the FK/RLS covert-channel problem, while invariants 1–5 address the GUC/pooling issues. The reader cannot tell from structure alone which invariants address which threat.** **Specific change requested:** Group the eight invariants under two explicit sub-headings: "Connection pooling and table-owner bypass (invariants 1–5)" and "FK covert-channel isolation (invariants 6–8)" so the threat model → invariant mapping is explicit.

5. **Location: Open Questions table. Issue: R7 (Trimble cryptographic standard) and R5 (ARC-SL thresholds) are genuine open questions but the table format presents all four questions with equal weight.** R7 is a v1 launch-blocking dependency (it determines whether AES-GCM or Fernet is used in production); R5 is important but not a launch blocker. **Specific change requested:** Add a "Blocking v1?" column to the Open Questions table with values Y/N. R7 = Y; R5 = N; R-Knauf = N (deferred to Knauf workshop but not a launch blocker); R4 = N (export contract exists pending their standard).

---

## Disagreement carryover audit

- **Final-surfaced disagreements from Phase 2:** D-5 (MCP-only public programmatic surface) — present in draft in "Disagreements Left Open" with accurate one-sentence summary; not distorted.
- **Resolved disagreements that re-emerged:** (none)
- **New disagreements raised during review:** D-OAI-1 (RLS referential-integrity handling) — raised by openai in round 1; resolved in round 2 in openai's favor.

---

## Substantive disagreements I'm holding

(none)

---

## Drafter revision note

**(a) Changes made and where:**

1. **Claim-level [V]/[U] tags (OAI-1):** Added inline [V]/[U] tags throughout all Findings sections (§§1–12). The Confidence Ledger remains as a supplementary table but is no longer the primary tagging mechanism.

2. **FK/RLS invariant correction (OAI-2 / D-OAI-1):** Removed the false "RLS blocks the parent SELECT during the FK check" sentence. The bidirectional FK vulnerability is retained and correctly framed: (a) FK integrity checks bypass RLS, creating a covert-channel information leak; (b) child INSERTs can fail because RLS hides parent rows from the FK check. Invariants 6 and 7 require opaque UUIDs and scoped unique constraints as mitigations.

3. **Citation repair (OAI-3):** Removed phantom source [39] reference. Added inline numbered citations throughout Findings (e.g., [1] for PgBouncer, [2] for PostgreSQL RLS, [5] for OWASP, [7] for MCP spec, [16] for AI code quality). Confidence Ledger source numbers aligned with Sources list. Corrected the PostgreSQL wiki FK covert-channel citation from [14] to [38].

4. **AI code quality figures (OAI-4):** Changed "AI-authored pull requests average 10.83 issues per PR versus 6.45 for human-only submissions, with logic and correctness errors up 75%" to "Per the CodeRabbit December 2025 analysis (reported in [16]), AI-authored pull requests averaged 10.83 issues per PR versus 6.45 for human-only, with logic and correctness errors 75% higher." Framing is now explicit secondary-source attribution.

5. **Quarantine layer framing (OAI-5):** Replaced "current state-of-the-art for document prompt injection defense" with "this architecture recommends as a mitigation for the prompt-injection attack class documented in [11][12][13]."

6. **Process artifacts (OAI-6):** Removed all pre-Summary process sentences.

7. **New comment C-1 (verifier pipeline vs. evidence bundle ownership split):** Added clarifying sentence in Gap A distinguishing skills team (verifier pipeline) from infrastructure/self-healing team (evidence bundle gate).

8. **New comment C-2 (GCP Vertex AI cross-cloud note):** Added parenthetical in Gap E noting cross-cloud dependency; recommends AWS Bedrock EU as primary path.

9. **New comment C-3 (Confidence Ledger source [14] → [38]):** Corrected FK covert-channel row.

10. **New comment C-4 (RLS invariant grouping):** Added two sub-headings grouping the eight invariants by threat: "Connection pooling and table-owner bypass (invariants 1–5)" and "FK covert-channel isolation (invariants 6–8)."

11. **New comment C-5 (Open Questions blocking column):** Added "Blocking v1?" column to Open Questions table.

**(b) Considered and rejected:**

- Considered splitting Gap B into two separate Gap sections (one for GUC/pooling, one for FK). Rejected: the eight invariants are logically unified as "RLS safety requirements." The sub-heading approach within the same section is sufficient and avoids structural bloat.
- Considered removing the Confidence Ledger entirely since inline tagging now covers the requirement. Rejected: the Ledger provides a useful summary index for review and is not redundant with inline tags.

**(c) Comments not yet acted on:** (none — all five new comments accepted and incorporated above)

**(d) Confidence Ledger changes:**
- Corrected source citation for "FK bypass creates covert-channel" row: changed from "Source [14] PostgreSQL wiki" to "Source [38] PostgreSQL Wiki."
- Updated "FK integrity checks always bypass RLS" row: already [V] from round 1, no change needed.
- Removed phantom source [39] row entirely from ledger.
- No rows added or removed beyond the above corrections.

---

## Revised draft

## Summary

[U] The Partner Vetting architecture proposal is structurally well-suited to autonomous codegen: typed contracts at every boundary, a modular monolith, explicit state machines, row-level security tenant isolation, a Postgres-backed outbox, OpenTelemetry instrumentation, and append-only audit and billing streams together reduce the distributed-system failure modes that codegen pipelines handle worst. [U] The document's central weakness is that it conflates *test existence* with *test quality*: generated code and generated tests can be mutually consistent and collectively wrong, which is the primary failure mode for no-human-review systems. This oracle-quality problem manifests concretely in five gaps requiring remediation before v1 ships: the absence of a mutation testing gate and independent verifier pipeline; specific RLS GUC lifecycle failures under connection pooling plus a bidirectional FK/RLS vulnerability; an unaddressed MCP and document-AI attack surface; an eval-set design that risks self-referential validation; and an active EU data residency blocker that makes the proposed direct Anthropic API path non-compliant for the Knauf (German shipper) deployment. Two further gaps require targeted ADR amendments: the proposal's envelope encryption scheme (Fernet/AES-CBC-128) is OWASP's second preference rather than first, and the consent cache invalidation path has a race condition that may violate GDPR revocation semantics.

---

## Findings

### 1. Executive Verdict and Primary Constraint

The governing constraint is unambiguous: every line of implementation is AI-generated; automated tests are the only quality gate. This constraint is simultaneously the architecture's greatest design driver and the source of its most dangerous unexamined assumption.

[U] **What autonomous codegen requires of the architecture:** machine-verifiable boundaries that the pipeline cannot violate without a build failure; typed contracts so that contract drift breaks the build before reaching production; lint rules enforcing invariants the pipeline cannot self-correct without a specification; and observability that surfaces drift without human intervention. The proposal provides all of these at the coarse-grained structural level.

[U] **The primary architectural concern for no-human-review systems:** generated code, generated tests, and generated eval sets produced from the same model family can be mutually consistent and collectively wrong. A test suite that achieves 90% branch coverage by executing happy-path lines without asserting on boundary conditions passes CI while leaving production business-logic errors undetected. The architecture must require independently produced, adversarially oriented quality gates — not merely more tests of the same character as the code they validate.

---

### 2. What the Architecture Gets Right

[U] **Typed contracts at every boundary** are the single most important enabler. The `mcp-surface.json` schema, `internal-http.openapi.yaml`, TypeScript interfaces at bounded-context entry points, and component prop contracts as JSON Schemas constitute the contract layer that makes the entire codegen-first model tractable. Schema-first development — where editing a schema regenerates the implementation skeleton and contract tests, and where failing tests refuse the merge — is the correct architecture for a pipeline with no human PR review.

[U] **The modular monolith decision** eliminates the distributed-system failure modes that autonomous codegen handles worst: network-boundary authentication, cross-service schema drift, partial-failure reasoning in distributed transactions, and independently deployed services whose contract tests can silently diverge. A system where four bounded contexts (Profile & Consent, Document Intake & Authentication, Rules, Network Signal stub) are enforced by import-linter rules rather than network calls achieves logical separation without distributed-systems complexity.

[U] **Explicit state machines named and modeled** prevent codegen from leaving the domain's most critical invariants implicit. The Submission state machine (`Pending → Missing → Approved → Rejected → Expired`), the Vetting Run state machine, and the Grant lifecycle are the invariants most likely to be broken by a codegen pipeline operating without domain expertise. Naming them, specifying their transitions, and making them the subject of property tests is architecturally correct.

[V] **PostgreSQL RLS as the tenant isolation mechanism** is the correct default-deny approach: when RLS is enabled and no applicable policy exists, access is denied by default [2]. This means the codegen pipeline's failures (a forgotten `WHERE tenant_id = ?` clause) fail closed rather than open.

[V] **The Postgres outbox** for at-least-once internal event delivery between contexts is correct for v1 load. The `SELECT FOR UPDATE SKIP LOCKED` pattern is documented in the official PostgreSQL specification as suitable for queue-like table access [4], providing the at-least-once delivery guarantee without an external message broker.

[U] **OpenTelemetry as vendor-neutral instrumentation** is correct and swap-friendly: the same SDK serves traces, metrics, and logs regardless of which backend the engineer-review pass selects. This is the right architecture for a codegen-first system because the instrumentation code is stable and the backend decision is deferred.

[U] **The lint rule inventory** is load-bearing. The specific rules named — no `UPDATE` against `audit_events` or `billable_events`, no raw queries bypassing RLS, no PII in logs via typed values, no cross-context imports outside the published interface, every state-changing handler emits ≥1 outbox row in the same transaction — each catch a class of bug that branch-coverage tests alone cannot reliably detect because they depend on the *absence* of a call or statement.

[U] **Append-only audit and billable event streams** are essential for a codegen-first system because they are the one source of ground truth about what the system actually did that a future human or automated analysis can recover from.

---

### 3. Gap A — Independent Verifier Pipeline and Mutation Testing Gate

The current proposal has a single code-generation pipeline. The same pipeline that produces implementation also produces tests from the same specifications and model family. This is the oracle-quality failure mode: the two artifacts can pass each other's checks while both being wrong in the same direction.

[V] Per the CodeRabbit December 2025 analysis (reported in [16]), AI-authored pull requests averaged 10.83 issues per PR versus 6.45 for human-only submissions, with logic and correctness errors 75% higher. [V] Research shows tests can achieve 100% line and branch coverage while scoring only 4% on mutation testing, because the tests execute code paths without asserting on boundary conditions [16][17][21].

The architecture must add a **separate verifier pipeline**, owned by the skills team, that consumes the same specification as the producer pipeline but executes in a distinct model context. Its purpose is to break the producer's output, not to confirm it. The verifier pipeline is owned by the skills team; the evidence bundle gate (ADR-023) is owned by the infrastructure/self-healing team. The skills team produces adversarial test artifacts; the infrastructure team enforces that all artifact categories are present and signed before release proceeds.

**What the verifier pipeline generates:**
- Mutation test cases targeting every critical core module
- Fuzz inputs for document metadata parsers, JWT/OIDC token parsers, and ruleset predicate evaluators
- Property-test counterexamples for every state machine transition
- Policy-denial test cases for every role × resource × action triple
- Migration rollback tests asserting that schema migrations are reversible
- Prompt-injection document fixtures for every AI-bearing check in the check catalog

**Mutation score targets** [U] (enforced by ADR-021, tool family: Stryker.js for TypeScript [15] / go-mutesting for Go, conditional on ADR-001 outcome):
- ≥80% for all generated code in the codebase
- ≥90% for **critical core modules**: Authorization, Consent/Grants, RLS session binding, State machines (Vetting Run, Submission, Grant lifecycle), Coverage Report Builder, Rules Evaluator, Audit/Billable Event Emission, Expiry/Reverification logic, Crypto/Key Management, MCP state-changing authorization

[U] **The critical core / generated shell split** must be enforced structurally: critical core lives in a named package with a separate, more stringent CI gate threshold. Import-graph rules enforced by the import-linter prevent generated shell modules from being imported by critical core.

**The evidence bundle release gate** (formalized as ADR-023, owned by the infrastructure/self-healing team) is the release condition replacing human PR review. A signed evidence artifact is required per merge covering: unit tests, property tests, mutation score at threshold, fuzz test runs, contract tests, end-to-end browser tests, accessibility checks, SAST scan, dependency scan, secret scan, AI eval set results, prompt-injection eval results, RLS negative tests, policy-denial tests, migration rollback tests, and observability assertion tests. Release is blocked without the complete signed evidence bundle.

---

### 4. Gap B — RLS: Eight Mandatory Invariants

The proposal correctly chooses PostgreSQL RLS as the tenant isolation mechanism. However, several implementation details that make RLS safe under connection pooling and under FK constraints are absent, and they are precisely the details a codegen pipeline will get wrong.

**Connection pooling (GUC lifecycle):** [V] In transaction mode pooling (the recommended production mode), the Heroku/PgBouncer authoritative documentation states: "Any changes to session state via SET must only be made with `SET LOCAL` so that the changes are scoped only to the currently executing transaction. Never use `SET SESSION` or `SET` alone" [1]. A connection returned to the pool by tenant A and subsequently acquired by tenant B retains A's GUC values unless `SET LOCAL` is used.

**Table owner bypass:** [V] The official PostgreSQL documentation confirms: "Table owners normally bypass row security as well, though a table owner can choose to be subject to row security with `ALTER TABLE ... FORCE ROW LEVEL SECURITY`" [2].

**FK/RLS bidirectional vulnerability:** [V] The official PostgreSQL documentation states: "Referential integrity checks, such as unique or primary key constraints and foreign key references, always bypass row security to ensure that data integrity is maintained. Care must be taken when developing schemas and row level policies to avoid 'covert channel' leaks of information through such referential integrity checks" [2]. [V] The Postgre