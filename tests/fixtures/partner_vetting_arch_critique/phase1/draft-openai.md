1. **Summary**

The proposal is directionally strong for autonomous codegen because it chooses a modular monolith, schema-first boundaries, explicit state machines, RLS tenant isolation, outbox-driven side effects, and generated documentation from typed contracts. [U] Its fatal weakness is that it treats “automated tests are the only quality gate” as mostly a CI concern, when the real problem is oracle quality: if the same autonomous pipeline writes the specs, code, and tests, the system can pass CI while faithfully implementing the wrong behavior. [U] The architecture must be tightened around independently reviewed specifications, executable domain models, mutation/fuzz/property testing, policy-as-code authorization, security verification gates, and runtime kill-switches before it is credible without human code inspection. [U] I would keep the modular monolith and contract-first posture, but cut v1 surface area, remove “magic lint” claims unless implemented by real analyzers, make all AI-bearing outputs non-authoritative until independently verified, and treat MCP as a high-risk executable-tool boundary rather than just another API adapter. [U]

2. **My thesis**

This architecture enables autonomous codegen at the coarse-grained structural level but undermines it at the assurance level: it specifies many good seams, but not enough independent, adversarial, machine-checkable oracles to trust generated implementation with no human PR review. [U] The most important change is to make the specification, tests, policies, and eval sets independent artifacts with their own review and provenance, because generated code cannot be safer than the tests and contracts that define “correct.” [U]

3. **Detailed findings**

### A. What the architecture gets right for autonomous codegen

1. **The modular monolith is the right default for no-human-review codegen.** [U] A single deployable with bounded-context import rules gives the generator fewer distributed failure modes than microservices, and it avoids requiring autonomous codegen to reason correctly about partial failure, network retries, cross-service authorization, and eventual consistency across many deployables. [U] This is especially appropriate because the proposal’s core entities—Profile, Document, Result Envelope, Vetting Run, Coverage Report, Grant, Audit Event—are referentially dense and transactionally related. [U]

2. **Typed contracts at every boundary are necessary and should remain non-negotiable.** [U] The proposal’s MCP schemas, internal OpenAPI schema, TypeScript interfaces, component prop schemas, and provider interfaces are exactly the kind of narrow, machine-checkable surfaces that autonomous codegen needs. [U] MCP tools are executable functions exposed by servers to clients, so treating each tool schema as a contract and test target is the right posture. [V] [7]

3. **PostgreSQL is a defensible v1 persistence choice.** [U] PostgreSQL row-level security can restrict which rows are visible or modifiable, and PostgreSQL assumes default deny if RLS is enabled but no applicable policy exists. [V] [1] PostgreSQL `FOR UPDATE SKIP LOCKED` is explicitly documented as usable for queue-like table access, though it gives an inconsistent view and is not suitable for general-purpose querying. [V] [2] That makes Postgres acceptable for v1’s job queue and outbox if the design explicitly accepts at-least-once delivery, idempotent consumers, and queue starvation tests. [U]

4. **The explicit state-machine framing is one of the strongest parts of the proposal.** [U] Submission state, Vetting Run state, Grant lifecycle, document immutability, result append-only semantics, expiry transitions, and re-verification loops are the domain invariants most likely to be broken by generated code if they remain implicit. [U] These state machines should be specified in executable form before implementation, not merely described in prose. [U]

5. **The RLS tenant-isolation decision is directionally correct, but incomplete.** [U] Database-enforced isolation is safer than relying only on generated application queries to remember `tenant_id` filters. [U] PostgreSQL RLS supports policy-based row visibility and modification rules, so the proposal’s decision to push tenant isolation into the database is sound. [V] [1] However, the current proposal must add `FORCE ROW LEVEL SECURITY`, connection-pool reset tests, migration tests, superuser/bypass-role controls, referential-integrity leak tests, and negative tests for every table, because RLS failures are catastrophic in a multi-tenant compliance system. [U]

6. **Outbox-driven audit, billing, and notification is a good match for codegen if idempotency is mandatory.** [U] The architecture correctly avoids having generated handlers update domain state and then separately attempt audit/billing side effects without a transactional bridge. [U] The missing requirement is that every outbox consumer must have a deterministic idempotency key and property tests proving duplicate delivery does not duplicate billable events, user notifications, or state transitions. [U]

7. **OpenTelemetry is the right instrumentation abstraction.** [U] OpenTelemetry is documented as vendor-neutral and supports telemetry such as traces, metrics, and logs. [V] [3] This fits the proposal’s need to decouple instrumentation from the final backend and to feed drift detection, skill health, queue depth, and dependency behavior into automated operations. [U]

8. **Web Components are a reasonable host-product integration boundary, but not the most important codegen boundary.** [U] Lit’s official site describes Lit as a small web-component library of about 5 KB minified and compressed. [V] [9] React 19 officially added full support for custom elements. [V] [8] Therefore, the architecture is right that Custom Elements can be the on-the-wire UI contract regardless of whether Lit or React wins internally. [U] The critical decision is not Lit versus React; the critical decision is whether component contracts, accessibility tests, role-visibility tests, and host-embedding tests are complete enough to substitute for human inspection. [U]

### B. Where the architecture undermines the no-human-review constraint

1. **It confuses contract existence with contract adequacy.** [U] A JSON Schema proves shape, not business correctness. [U] A tool schema can ensure that `coverage_amount` is numeric, but it cannot by itself prove currency normalization, per-shipper threshold semantics, country-specific license equivalence, consent scope, expiry math, or audit provenance correctness. [U] The proposal needs semantic contracts: examples, counterexamples, invariants, metamorphic properties, and forbidden states for every contract. [U]

2. **It allows the same generator to create code and likely create its own tests.** [U] That is the central assurance failure. [U] If autonomous codegen produces both the implementation and the tests from the same ambiguous specification, passing tests only demonstrates internal consistency with the generator’s interpretation. [U] The architecture must require independently authored or independently generated test oracles, mutation testing, seeded bug tests, and golden domain scenarios that the implementation generator cannot rewrite. [U]

3. **The proposal overstates “lint rules” as if they can enforce architectural intent without specifying the analyzer.** [U] Claims like “lint fails if every state-changing handler does not emit an outbox row” are not credible unless the handler taxonomy, transaction wrapper, AST pattern, data-access layer, and allowed escape hatches are formally constrained. [U] This should be replaced with generated code templates that make illegal states unrepresentable, database triggers or constraints where possible, and integration tests that observe audit rows after real state changes. [U]

4. **The architecture lacks a formal authorization model.** [U] The four roles are useful, but RBAC prose is not enough for autonomous codegen. [U] The system needs a policy matrix or policy-as-code model covering subject, tenant, profile, grant, ruleset, check, document section, action, trigger mode, and provenance. [U] Every MCP tool and internal HTTP endpoint should have generated allow/deny tests for each role and consent state. [U]

5. **MCP is treated too benignly.** [U] MCP tools expose executable functionality to model clients. [V] [7] OWASP identifies prompt injection, insecure output handling, sensitive information disclosure, and excessive agency as major LLM application risks. [V] [6] Therefore, Partner Vetting’s MCP adapter must be classified as a high-risk command surface, not merely a protocol translation layer. [U] The current proposal must add per-tool capability tokens, tool-call confirmation policies, argument canonicalization, prompt-injection tests using malicious documents, tool-result sanitization, and “LLM cannot authorize” rules. [U]

6. **The document-AI path is under-specified for no-human-review operations.** [U] The proposal says document AI emits Result Envelopes with confidence, but confidence is not ground truth. [U] AI output should never directly create a terminal compliance-relevant status without deterministic post-validation against schemas, extracted-field constraints, known-source checks, and adversarial eval suites. [U] NIST’s AI RMF is intended to improve trustworthy design, development, use, and evaluation of AI systems, and its generative-AI profile reinforces the need for AI-specific risk treatment. [V] [13] The proposal should require per-check eval datasets, red-team document corpora, prompt-injection fixtures, OCR degradation cases, multilingual edge cases, and calibration reports before a check version can be published. [U]

7. **The proposal’s “80% automation” target is operationally useful but architecturally dangerous.** [U] Optimizing for automation rate can incentivize over-approval unless paired with false-positive limits, false-negative limits, manual-review sampling, and holdout labels. [U] The right quality gate is not “≥80% automated”; it is “automation may only increase when measured error rates on a locked eval set and production sampling stay within threshold.” [U]

8. **The architecture underplays security verification.** [U] OWASP ASVS provides a basis for testing web application technical security controls and requirements for secure development. [V] [4] NIST SSDF includes practices for reviewing design/architecture and using code analysis and vulnerability testing to find security issues. [V] [5] The proposal mentions tests and linting but does not commit to ASVS level, SAST, DAST, dependency scanning, IaC scanning, SBOMs, secret scanning, container scanning, threat-model tests, or release-blocking vulnerability thresholds. [U] Without human code review, those gates must be explicit release criteria, not design-doc afterthoughts. [U]

9. **The crypto proposal is questionable.** [U] Fernet uses AES-CBC with a 128-bit key plus HMAC-SHA256 authentication. [V] [11] OWASP’s cryptographic-storage guidance says authenticated modes such as GCM and CCM should be preferred where available. [V] [10] Therefore, the proposal should not hard-code Fernet as the architectural standard unless Trimble has an inherited, approved cryptographic profile requiring it. [U] My recommended change is to use an approved AEAD envelope-encryption scheme such as AES-GCM or XChaCha20-Poly1305 with KMS-managed data keys, unless an internal security standard mandates Fernet. [U]

10. **The proposal defers too many “engineer review” decisions while claiming no human PR review.** [U] Engineer review of ADRs is not the same as code review, but the proposal does not define which human reviews remain allowed and mandatory: architecture review, security review, specification review, test-oracle review, eval-set review, release review, and incident review. [U] If human code inspection is forbidden, human review must move to specifications, policies, threat models, and acceptance evidence. [U]

11. **The proposal keeps too much v1 scope for a no-human-code-review system.** [U] Phase 1 includes MCP, a portal, five web components, workflow configuration, document intake, profile/consent, RLS multi-tenancy, audit, billing, notifications, AI validation, external registries, human review, crypto-erasure, and role architecture. [U] That is too large for a first release where no one reads generated code. [U] The correct v1 should be a narrow vertical slice: one tenant, one portal, one standing workflow, four Vera-equivalent checks, no external-customer MCP exposure, no conversational workflow authoring, no dynamic check authoring, no billing automation beyond audit-grade event capture, and no cross-product embedding. [U]

12. **The “MCP-only public programmatic surface” decision is too strong.** [U] MCP is appropriate for ARC and agentic callers, but customer-owned compliance integrations often need deterministic non-agent APIs with conventional authentication, idempotency keys, pagination, and audit semantics. [U] My best judgment is to keep MCP for ARC in v1 but define the internal service contract as an HTTP API that can later be safely published; do not make MCP the only durable external contract. [U] The condition under which MCP-only is acceptable is narrow: all v1 and v2 programmatic consumers are mediated through ARC-style agents and no customer system needs direct deterministic integration. [U]

13. **The test strategy lacks mutation testing and fuzzing, which are essential without code review.** [U] Branch coverage can be gamed by shallow assertions. [U] The architecture should require mutation score thresholds for business logic, fuzzing for parsers and document metadata, property tests for lifecycle transitions, contract tests for every boundary, and golden end-to-end scenarios for each workflow variant. [U] Coverage should be treated as a minimum hygiene metric, not a correctness metric. [U]

14. **The proposal does not separate safety-critical generated code from generated glue.** [U] Generated UI layout and generated adapters are lower risk than generated authorization, consent, billing, crypto, tenant isolation, and state transitions. [U] The architecture should create a “critical core” package whose APIs are tiny, whose functions are pure where possible, whose invariants are exhaustively property-tested, and whose generated code must pass a stronger gate than ordinary UI or adapter code. [U]

15. **The “carrier ownership” consent model needs stronger invariants.** [U] Freeze-on-revoke is plausible, but the architecture needs machine-checkable rules for what remains visible after revocation, what becomes hidden, what appears in previously delivered Coverage Reports, and how downstream products must label stale or revoked consent. [U] Without those rules, generated components and MCP tools will likely diverge in edge cases. [U]

16. **The proposal’s runtime safety mechanisms are good but need stronger blast-radius controls.** [U] Auto-approval toggles, circuit breakers, timeouts, and human-review queues are the right ideas. [U] They should be extended into per-check kill switches, per-source kill switches, per-tenant rollout flags, shadow-mode execution for new check versions, canary rulesets, and automatic demotion to human review on drift. [U]

17. **The architecture should prefer deterministic workflow authoring over conversational authoring in v1.** [U] A conversational helper can draft a ruleset, but a deterministic visual editor should be the canonical authoring surface because rulesets are compliance artifacts. [U] OWASP’s LLM risk taxonomy includes prompt injection and excessive agency risks, which are directly relevant when an LLM creates executable business rules. [V] [6] My recommendation is: conversational drafting allowed, but only a normalized, visual, diffable ruleset AST can be saved, versioned, tested, and activated. [U]

18. **The “no aggregate verified boolean” decision is excellent and should be enforced at schema and UI levels.** [U] This avoids hidden provenance loss and reduces the chance that generated UI creates misleading trust signals. [U] It should be backed by schema constraints, component snapshot tests, and forbidden-string tests that fail if labels such as “Verified Carrier” appear without ruleset provenance. [U]

19. **The proposal should add supply-chain provenance as a first-class requirement.** [U] SLSA defines levels that provide increasing supply-chain security guarantees for builds. [V] [12] In a system where no human inspects code, provenance, hermetic builds, dependency pinning, SBOMs, signed artifacts, and reproducible build evidence become part of the quality gate. [U]

20. **The proposal should make “specification review” the governance substitute for code review.** [U] The hard rule “no code changes without a specification” is powerful only if specifications are reviewed, versioned, tested, and traceable to generated code, tests, migrations, and docs. [U] Every production change should require a spec package containing: intent, affected contracts, invariants, policy matrix diff, migration plan, tests to add, rollback behavior, telemetry expectations, and acceptance evidence. [U]

### C. Recommended architecture changes

#### C1. Introduce an independent assurance pipeline

Add a second pipeline that never writes production code and exists only to break generated output. [U] It should generate adversarial tests, mutation tests, fuzz inputs, security scans, policy-denial cases, migration rollback tests, and prompt-injection fixtures from the same spec. [U]

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="920" height="360" viewBox="0 0 920 360">
  <rect x="20" y="20" width="880" height="320" rx="16" fill="#f8fafc" stroke="#334155"/>
  <text x="460" y="50" text-anchor="middle" font-size="20" font-family="Arial" fill="#0f172a">Required no-human-code-review assurance topology</text>

  <rect x="60" y="90" width="180" height="70" rx="10" fill="#dbeafe" stroke="#1d4ed8"/>
  <text x="150" y="120" text-anchor="middle" font-size="14" font-family="Arial">Reviewed Spec Package</text>
  <text x="150" y="140" text-anchor="middle" font-size="12" font-family="Arial">contracts · invariants · policies</text>

  <rect x="310" y="80" width="190" height="90" rx="10" fill="#dcfce7" stroke="#15803d"/>
  <text x="405" y="110" text-anchor="middle" font-size="14" font-family="Arial">Producer Agent</text>
  <text x="405" y="130" text-anchor="middle" font-size="12" font-family="Arial">generates implementation</text>
  <text x="405" y="148" text-anchor="middle" font-size="12" font-family="Arial">and migrations</text>

  <rect x="310" y="215" width="190" height="90" rx="10" fill="#fee2e2" stroke="#b91c1c"/>
  <text x="405" y="245" text-anchor="middle" font-size="14" font-family="Arial">Verifier Agent</text>
  <text x="405" y="265" text-anchor="middle" font-size="12" font-family="Arial">generates adversarial tests</text>
  <text x="405" y="283" text-anchor="middle" font-size="12" font-family="Arial">and negative cases</text>

  <rect x="590" y="120" width="260" height="120" rx="10" fill="#fef9c3" stroke="#a16207"/>
  <text x="720" y="150" text-anchor="middle" font-size="14" font-family="Arial">Gated Evidence Bundle</text>
  <text x="720" y="172" text-anchor="middle" font-size="12" font-family="Arial">unit · property · mutation · fuzz</text>
  <text x="720" y="192" text-anchor="middle" font-size="12" font-family="Arial">SAST · DAST · SBOM · eval sets</text>
  <text x="720" y="212" text-anchor="middle" font-size="12" font-family="Arial">policy denial · migration rollback</text>

  <line x1="240" y1="125" x2="310" y2="125" stroke="#334155" marker-end="url(#arrow)"/>
  <line x1="240" y1="125" x2="310" y2="260" stroke="#334155" marker-end="url(#arrow)"/>
  <line x1="500" y1="125" x2="590" y2="160" stroke="#334155" marker-end="url(#arrow)"/>
  <line x1="500" y1="260" x2="590" y2="205" stroke="#334155" marker-end="url(#arrow)"/>

  <text x="460" y="325" text-anchor="middle" font-size="13" font-family="Arial" fill="#334155">Release only if implementation and independent verifier evidence agree.</text>

  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#334155"/>
    </marker>
  </defs>
</svg>
```

#### C2. Define release gates as evidence, not as CI steps

The release gate should require signed evidence for each category: type-check, unit, integration, property, mutation, fuzz, contract, e2e, accessibility, SAST, DAST, dependency scan, secret scan, IaC scan, container scan, SBOM, provenance, AI eval, prompt-injection eval, RLS negative tests, policy-denial tests, migration rollback tests, and observability assertions. [U] A build that lacks evidence should fail even if the code compiles and ordinary tests pass. [U]

#### C3. Replace prose RBAC with policy-as-code

Create a canonical authorization matrix and generate both enforcement and tests from it. [U] Example axes: role, tenant, profile ownership, grant section, ruleset ownership, check catalog permission, trigger mode, actor type, agent principal, and terminal state. [U] Every tool must have positive and negative tests generated from the matrix. [U]

#### C4. Treat AI outputs as untrusted inputs

Document AI results, conversational workflow drafts, and ARC/MCP tool arguments should all be treated as untrusted until validated by deterministic code. [U] OWASP’s LLM risks include prompt injection, insecure output handling, sensitive information disclosure, and excessive agency, so these are directly relevant to documents, prompts, tools, and autonomous actions in this product. [V] [6]

#### C5. Narrow v1

Ship v1 as: portal-only UI, Knauf-only tenant, four Vera-equivalent checks, deterministic ruleset configuration, Partner Submission, Partner Profile, unified human-review queue, audit events, consent grants, and read-only MCP for status/profile queries. [U] Defer write-capable MCP tools such as `create_ruleset`, `grant_visibility`, `submit_document`, and `start_vetting_run` until the MCP-specific security model and policy tests are mature. [U] My best guess is that this narrower v1 is the highest-probability path to a safe launch under no human code review. [U]

#### C6. Reframe MCP as a zero-trust command boundary

Every MCP tool should require: explicit capability scope, idempotency key for state-changing calls, rate limit, replay protection, structured actor identity, tenant binding, policy decision log, prompt-injection test cases, and tool-result sanitization. [U] MCP should not be allowed to create or activate compliance-impacting rulesets without deterministic preview, diff, validation, and explicit human business approval in the UI. [U]

#### C7. Make domain invariants executable

Each state machine should be encoded once in a machine-readable model and used to generate implementation scaffolds, property tests, migration constraints, documentation, and telemetry expectations. [U] Forbidden transitions should be represented explicitly, not left to handler logic. [U]

#### C8. Add mutation testing as a required gate

Require a high mutation score for critical core modules: Rules, Consent, Authorization, Tenant Isolation, Billing Event Emission, Audit Emission, Expiry, and Coverage Report Builder. [U] This is more important than increasing branch coverage from 90% to 95%, because mutation tests expose weak assertions. [U]

#### C9. Split the codebase into “critical core” and “generated shell”

Critical core modules should be tiny, deterministic, side-effect controlled, property-tested, mutation-tested, and fuzz-tested. [U] Generated shell modules—UI composition, adapters, formatting, documentation—can have lighter gates. [U] The proposal currently treats all generated code too uniformly. [U]

#### C10. Fix the cryptographic posture

Use Key Vault or equivalent KMS for key custody, but do not hard-code Fernet unless it is an internal standard. [U] Fernet’s documented construction is AES-CBC-128 plus HMAC-SHA256. [V] [11] OWASP recommends authenticated modes such as GCM or CCM as first preference where available. [V] [10] The architecture should specify an approved AEAD envelope-encryption profile, key hierarchy, associated data, rotation, crypto-erasure semantics, and test vectors. [U]

#### C11. Add supply-chain controls

Require pinned dependencies, lockfile integrity, dependency review, SBOM generation, vulnerability thresholds, signed artifacts, build provenance, and isolated build runners. [U] SLSA is organized into levels that provide increasing supply-chain security guarantees, making it a useful framework for this release gate. [V] [12]

#### C12. Make observability assertions testable

For every state-changing operation, tests should assert not only final state but also audit event, metric emission, trace span tags, outbox event, and log redaction. [U] OpenTelemetry’s vendor-neutral model supports this instrumentation strategy across backend choices. [V] [3]

### D. Bottom-line architectural verdict

Keep: modular monolith, Postgres, RLS, outbox, append-only audit/billing, explicit state machines, contract-first MCP/internal HTTP/component boundaries, generated docs, runtime toggles, and web-component distribution. [U]

Change immediately: shrink v1, make specs independently reviewed, separate producer and verifier agents, require policy-as-code, add mutation/fuzz/security/supply-chain gates, treat MCP and LLM outputs as high-risk untrusted boundaries, replace prose invariants with executable models, and define evidence bundles as the release artifact. [U]

Reject or defer: write-capable external MCP in v1, conversational ruleset activation in v1, dynamic UI generation, customer self-service check authoring, live cross-product embedding, and any AI-generated check version without locked eval sets and human-approved acceptance criteria. [U]

4. **Claims I expect the other agent might dispute**

1. **I expect dispute on my recommendation to narrow v1 aggressively.** [U] It matters because the proposal’s commercial goal favors broad Phase 1 capability, but no-human-code-review safety favors a smaller release; evidence that would resolve it is a two-week generated-code spike measuring defect escape rate across the full proposed v1 scope versus a narrowed vertical slice. [U]

2. **I expect dispute on treating MCP as too risky for write-capable v1 operations.** [U] It matters because ARC integration is central to the product vision; evidence that would resolve it is a complete MCP threat model, adversarial tool-call test suite, and demonstrated policy enforcement for state-changing tools. [U]

3. **I expect dispute on whether TypeScript is acceptable for the backend under autonomous codegen.** [U] It matters because single-language development helps codegen, while Go may provide a smaller runtime surface and stronger concurrency defaults; evidence that would resolve it is a controlled implementation spike of the same state machine, RLS access layer, outbox, and MCP adapter in both stacks. [U]

4. **I expect dispute on my crypto recommendation away from Fernet.** [U] It matters because inherited ARC standards may mandate Fernet, while OWASP guidance prefers authenticated modes such as GCM/CCM where available. [V] [10] Evidence that would resolve it is Trimble’s internal cryptographic standard and counsel/security approval for the envelope-encryption design. [U]

5. **I expect dispute on whether human spec/test review violates the “autonomous codegen” premise.** [U] It matters because I believe no human code inspection is only credible if humans inspect specifications, policies, and acceptance evidence instead; evidence that would resolve it is the project’s governance rule defining whether humans may review non-code artifacts. [U]

6. **I expect dispute on whether generated tests can be trusted if they come from a separate verifier agent.** [U] It matters because independent verifier generation is better than self-testing but still not equivalent to expert assurance; evidence that would resolve it is mutation score, seeded-defect detection rate, and historical escape rate across generated changes. [U]

5. **Open questions**

1. **Specific question:** What exactly is forbidden by “no human PR review, no human code inspection,” and are humans allowed to review specifications, tests, generated diffs at a semantic level, eval sets, and release evidence? [U] **Evidence needed:** Written governance policy for the codegen pipeline. [U] **Why unresolved:** The brief states the code constraint but does not define allowed review of non-code artifacts. [U]

2. **Specific question:** What security standards does Trimble/TTC mandate for web applications, AI systems, cryptography, supply chain, and cloud deployment? [U] **Evidence needed:** Internal Trimble security standards, TTC platform requirements, approved cryptographic profiles, and deployment control checklists. [U] **Why unresolved:** Those internal documents were not included in the prompt and are not public sources I could inspect. [U]

3. **Specific question:** Does ARC’s MCP skill lifecycle provide enforceable security gates or mainly quality/confidence gates? [U] **Evidence needed:** ARC-SL technical documentation, gate definitions, failure thresholds, and examples of demotion behavior. [U] **Why unresolved:** The prompt says ARC documentation was expected but