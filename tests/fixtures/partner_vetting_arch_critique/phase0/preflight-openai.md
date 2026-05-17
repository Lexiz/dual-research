## Brief clarity

The brief is clear enough to answer: it provides the product context, legacy constraints, proposed architecture, ADRs, and the evaluation lens. [U] The main internal ambiguity is that the proposal says “**no human PRs, no human review**” while several ADRs say “**subject to engineer review**” or “**final commitments land with the review pass**,” which creates uncertainty about whether human review is forbidden only for generated implementation code or also for architecture, ADRs, schemas, tests, prompts, and CI rules. [U]

## Missing inputs

1. The actual autonomous codegen pipeline design: spec format, generation steps, allowed tools, merge mechanics, rollback process, and who/what writes or approves specs. [U]
2. The CI/CD quality-gate definitions: exact lint rules, coverage measurement rules, mutation-test policy if any, flaky-test handling, eval-set acceptance thresholds, and release-blocking criteria. [U]
3. ARC integration documentation, especially ARC-SL gates, MCP auth/token semantics, and degradation/demotion behavior. [U]
4. Applied AI Safety & Enablements audit standard, because the proposal references it as a future migration target but does not define its required schema or controls. [U]
5. Threat model and compliance requirements for a no-human-inspection system handling personal data, commercial credentials, consent, and regulatory evidence. [U]
6. Expected v1 volume/capacity assumptions: Knauf carrier count, document volume, concurrent users, AI calls per vetting run, and human-review backlog assumptions. [U]
7. Representative document corpus and labelled eval datasets for the 25+ language requirement. [U]
8. Clarification of whether humans may inspect generated tests, schemas, prompts, specifications, infra definitions, and observability rules, even if they may not inspect generated product code. [U]

## Framing concerns

1. The brief risks treating “automated tests are the only quality gate” as equivalent to “system quality is adequately controlled,” but test generation, oracle correctness, and coverage meaningfulness are themselves unsolved governance problems. [U]
2. The proposal assumes autonomous codegen is safer with a modular monolith, typed contracts, and linting, but does not yet prove that those controls catch semantic, security, privacy, or regulatory failures. [U]
3. The “no human PR review” constraint conflicts with repeated references to engineer review, counsel review, and platform review unless the boundary between implementation review and design/governance review is made explicit. [U]
4. The architecture emphasizes test coverage percentages, but high branch coverage can still miss authorization, tenant-isolation, consent, prompt-injection, data-leakage, and AI-evaluation oracle failures. [U]
5. The framing asks whether the architecture “enables or undermines” autonomous codegen, but the deeper issue may be whether some components should be excluded from autonomous-only implementation entirely, such as auth, crypto, RLS policies, audit, billing, and AI-eval harnesses. [U]

## Proposed scope

I intend to evaluate the proposal as an architecture-for-codegen document, not as a general Partner Vetting solution review. [U] I will focus on whether its boundaries, contracts, test strategy, data isolation, AI-eval approach, observability, security controls, operational rollback, and ADRs are sufficient when no human inspects generated implementation code. [U] I will not independently validate market claims, competitor claims, regulation dates, cargo-theft statistics, or vendor product capabilities unless Phase 1 explicitly asks for external verification, because the requested critique is primarily architectural and process-oriented. [U]

## Status

STATUS: BRIEF_OK

BRIEF_ISSUES: 13