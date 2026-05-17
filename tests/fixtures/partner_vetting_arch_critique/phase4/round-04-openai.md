## Answers to claude's prior comments

1. **No-new-comments assertion:** I do not agree that the draft is fully resolved. [U] The FK/RLS and EU-residency legal-framing issues are resolved in the current draft, but two draft-internal issues remain: incomplete claim-level tagging in the Summary / recommendation bullets, and the Summary’s lingering “OWASP’s second preference” wording. [U]

2. **D-OAI-1 / RLS FK mechanism:** Resolved. [V] The current draft now treats PostgreSQL’s official statement that referential-integrity checks bypass RLS as normative and separates that from parent-table policy footguns. [2]

3. **D-OAI-2 / EU data-residency legal framing:** Resolved. [U] The current draft appropriately separates the verified infrastructure claim from the legal/customer-requirements conclusion by using “if EU-only processing is required” and “legal review required” framing. [U]

4. **OAI-7 / Outbox prose:** Resolved. [U] The current draft now includes prose requiring partial indexes, DLQ/retry-exhaustion handling, replay/idempotency tests, and dead-tuple alerting under Required ADR Amendments. [U]

## Issue ledger (delta + currently open)

1. **OAI-1 — open — Claim-level [V]/[U] tagging remains incomplete in the draft body.** The current draft improved materially, but material claims in the Summary and some recommendation bullets still lack immediate claim-level tags; the protocol requires tagging at claim level, not section/paragraph level. [U]

   > quote: This oracle-quality problem manifests concretely in five gaps requiring remediation before v1 ships

2. **OAI-2 / D-OAI-1 — resolved — RLS referential-integrity mechanism is now correctly framed.** The draft now states that PostgreSQL FK checks bypass RLS and treats the Bytebase-style parent-visibility issue as a separate policy footgun. [V] [2][24]

3. **OAI-3 — resolved — Inline citation discipline is now sufficient except where folded into OAI-1 tagging.** Central [V] claims in the Findings now generally carry inline numbered citations; remaining issue is tagging completeness, not citation numbering. [U]

4. **OAI-4 — resolved — AI-code-quality figures are now sufficiently softened.** The draft now attributes the 10.83 vs. 6.45 figures to a secondary report citing CodeRabbit rather than treating them as a universal baseline. [U]

5. **OAI-7 — resolved — Outbox/DLQ controls are now in prose.** The current draft includes prose requirements for partial index, DLQ/retry-exhaustion table, replay/idempotency tests, and dead-tuple alerting. [U]

6. **OAI-8 / D-OAI-2 — resolved — EU data-residency legal conclusion is now appropriately conditional.** The draft now distinguishes the verified infrastructure routing issue from the legal/customer acceptability question. [U]

7. **OAI-9 — open — Summary still uses the “OWASP’s second preference” wording that prior review asked to replace.** The body’s Gap F wording is now acceptable, but the Summary still says “OWASP’s second preference rather than first,” which is less precise than the sourced OWASP framing. [V]/[U] [5]

   > quote: is OWASP's second preference rather than first

## Evidence checked this round

- New research performed: (none)
- Claims checked against existing sources:
  - PostgreSQL FK/RLS framing in the current draft matches the official PostgreSQL source already cited in the draft: referential-integrity checks bypass row security. [V] [2]
  - The current draft’s EU-residency wording now matches the evidentiary boundary established in prior rounds: technical routing is sourced, legal/customer acceptability remains conditional. [U]
  - The OWASP cryptographic wording issue is tied to existing source [5], which says GCM/CCM authenticated modes should be first preference and CBC/CTR are alternatives when authenticated modes are unavailable. [V] [5]
- Factual issues found:
  - The Summary still contains an over-compressed crypto claim (“OWASP’s second preference”) that is not OWASP’s exact framing. [V]/[U] [5]
- No new research because: Remaining blockers are draft-internal tagging and wording issues tied to sources already retrieved and cited in prior rounds. [U]
- Corroboration on the other agent's claims:
  - Material [U] claims:
    - **Claim:** The current draft resolves all prior open issues. **Assessment:** Not fully; RLS, EU-residency, outbox, and attribution issues are resolved, but claim-level tagging and the crypto Summary wording remain unresolved. [U]
    - **Claim:** Mutation thresholds are acceptable as architectural proposals despite limited empirical basis. **Assessment:** Acceptable if tagged [U] and treated as proposed gates subject to engineer review; no objection remains. [U]
  - Central [V] claims:
    - **Claim:** PostgreSQL referential-integrity checks bypass RLS. **Assessment:** Corroborated by PostgreSQL official documentation and now correctly reflected in the draft. [V] [2]
    - **Claim:** OWASP prefers authenticated modes such as GCM/CCM where available. **Assessment:** Corroborated by OWASP Cryptographic Storage guidance; Summary wording should use “fallback-style construction” rather than “second preference.” [V] [5]

## Comments on the current draft

1. **Location: Summary / Findings. Issue: claim-level tagging remains incomplete. Specific change requested:** Add [U] or [V] tags to the untagged Summary sentences and material recommendation bullets, especially the “oracle-quality problem manifests…” sentence and the “Two further gaps…” sentence. [U]

   > quote: This oracle-quality problem manifests concretely in five gaps requiring remediation before v1 ships

2. **Location: Summary / crypto gap. Issue: crypto wording still overstates OWASP’s ranking. Specific change requested:** Replace “OWASP’s second preference rather than first” with “a fallback-style construction under OWASP guidance; AEAD modes such as GCM/CCM are first preference where available.” [V] [5]

   > quote: is OWASP's second preference rather than first

## Disagreement carryover audit

- Final-surfaced disagreements from Phase 2: **D-5 / MCP-only public programmatic surface** is present in the draft and accurately framed as a non-blocking preference difference. [U]
- Resolved disagreements that re-emerged: (none). [U]
- New disagreements raised during review: **D-OAI-1 / RLS referential-integrity handling** is resolved in OpenAI’s favor; **D-OAI-2 / EU data-residency legal framing** is resolved in OpenAI’s favor. [U]

## Substantive disagreements I'm holding

(none)

## Drafter revision note

(reviewer — no draft edits)

## Approval check

(not ready) The blockers are incomplete claim-level [V]/[U] tagging in the draft body and the lingering imprecise OWASP “second preference” wording in the Summary. [U]

## Status

STATUS: REVIEWING

OPEN_ISSUES: 2