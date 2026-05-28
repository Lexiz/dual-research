## Stance

Round 3 of Phase 0. I need to ratify or counter openai's addresses on my six open items (Q-input-c-01 through Q-input-c-04, D-input-c-01, D-input-c-02). My private strongest objection to my own current position: openai's address on Q-input-c-02 raises a genuine discrepancy — the official MCP SDK page tiers Kotlin as "TBD" rather than a settled pass, which differs from my Round 2 summary that called Kotlin "recently stabilised." I need to verify this before I can RESOLVE or push back. Additionally, on D-input-c-02 (Rust velocity), openai's partial agreement is reasonable but I should check whether their evidence citation from linux-magazin.de is actually the same C-compiler proof point I found, and whether we are genuinely aligned or just using different sources for the same claim.

My assessment of the state: all substantive disagreements have been addressed with reasonable positions. The main remaining question is whether I can ratify the addresses or need to push back on specifics. After ratifying, we should be at AGREED with a clean shared interpretation for Phase 1.Now I have what I need. Let me assess the two key verification questions before writing my turn:

**On Kotlin MCP SDK status**: The search results show a `modelcontextprotocol/kotlin-sdk` repository that is officially maintained "in collaboration with JetBrains" — this is a full official SDK, not a "TBD" tier. The SDK supports JVM, Native, JS, and Wasm targets, and includes client+server APIs, multiple transports (stdio, SSE, Streamable HTTP, WebSocket), and is published on Maven Central. The official modelcontextprotocol.io/docs/sdk page doesn't show specific tier assignments in the snippets returned, but the existence of a `modelcontextprotocol/kotlin-sdk` repo maintained by JetBrains establishes Kotlin as having an official SDK. OpenAI's claim that Kotlin is "TBD" tier appears inconsistent with this evidence — there are now two Kotlin SDK repositories (modelcontextprotocol/kotlin-sdk and JetBrains/mcp-kotlin-sdk). I need to push back on openai's Kotlin characterisation.

**On the C compiler / Rust proof point**: The primary source is `anthropic.com/engineering/building-c-compiler`. Key nuances: (1) Rust code quality described as "reasonable, but... nowhere near the quality of what an expert Rust programmer might produce" [V]; (2) the compiler has real limitations (no 16-bit x86, no own assembler/linker); (3) required ~$20K API costs and nearly 2,000 sessions. This supports my round 2 claim that the proof point doesn't directly address business-logic iteration speed. OpenAI's characterisation in their D-input-c-02 address is substantively aligned with mine — I can RESOLVE this.

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: [Q-input-c-01, Q-input-c-03, Q-input-c-04, D-input-c-01, D-input-c-02]
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 0
OPEN_DISAGREEMENTS: 0
ADDRESSED_QUESTIONS: 6
ADDRESSED_DISAGREEMENTS: 4

---

## Addressing items raised against me

*(None this round — all items pointed at me were addressed by openai in round 2.)*

---

## Ratifying my own items

### RESOLVE Q-input-c-01
reason: |
  OpenAI's proposed assumption is substantively identical to mine: score 2.1 against long-lived, human-reviewed agentic maintenance — autonomous multi-file edits, test-driven repair loops, multi-bounded-context refactors, and human review. The brief's language ("Claude Code, GitHub Copilot, future agents") is intentionally agent-agnostic, and the correct response is the stated assumption rather than a specific agent answer. This item cannot be answered with client-specific data within this run, but the carry-forward assumption is agreed. [U]

---

### RESOLVE Q-input-c-02
reason: |
  This is substantially resolved by my own ADDRESS of D-input-g-02 (round 2) and openai's ADDRESS of Q-input-c-02. However, I must note a discrepancy that I am now resolving with fresh evidence: openai's address characterised Kotlin's MCP SDK tier as "TBD" on the official modelcontextprotocol.io page. My research this turn finds that `modelcontextprotocol/kotlin-sdk` exists as an official repository "maintained in collaboration with JetBrains," [V] supports JVM, Native, JS, and Wasm targets, [V] and includes full client+server APIs with multiple transports including stdio, SSE, Streamable HTTP, and WebSocket. [V] The JetBrains Kotlin documentation also actively promotes the "MCP Kotlin SDK" as a Kotlin Multiplatform implementation. [V] On this evidence, I do not accept that Kotlin is "TBD" tier — it has an official SDK. The final document should mark Kotlin as a clear Tier 1.4 pass, not a conditional pass. This does not change the recommendation directionally (no candidate is eliminated) but it removes an unwarranted maturity caveat for Kotlin in the Tier 2.3 ecosystem section. [V]

---

### RESOLVE Q-input-c-03
reason: |
  OpenAI's proposed assumption is correct and workable: interpret "separate processes inside the same container image" as one codebase/image with separate process types launched by the platform/deployment definition (separate commands/entrypoints), not four long-lived OS processes inside a single container instance. This interpretation does not disadvantage any candidate and reflects the most natural Container Apps deployment pattern. Carrying forward as an explicit assumption in the final document. [U]

---

### RESOLVE Q-input-c-04
reason: |
  OpenAI's proposed assumption is reasonable: treat cold-start and memory footprint as real Tier 2.4 signals because the brief explicitly names them and production min-replica count is unknown. If production guarantees min-replicas ≥ 1, JVM cold-start risk would be downgraded from recurring to deployment-only concern — this is exactly the right flip condition to carry into the final document. The assumption is: cold-start remains a relevant scoring signal for JVM candidates under 2.4, but is not eliminative. [U]

---

### RESOLVE D-input-c-01
reason: |
  OpenAI's proposed sub-weight ordering within 2.1 matches my own position from round 2 closely: (1) type-system depth and refactoring safety primary, (2) test scaffolding secondary-primary, (3) codebase comprehensibility and explicit semantics secondary, (4) convention-over-configuration tertiary within 2.1, (5) training-data adequacy a floor. I accept this ordering. The final-document implication is also agreed: Tier 2 table must show sub-ratings for 2.1, then an overall 2.1 rating, and the recommendation must explain if the winner does not have the highest overall 2.1. [U]

---

### RESOLVE D-input-c-02
reason: |
  OpenAI's position is well-calibrated and I accept it. The Anthropic C-compiler experiment (16 Claude agents, 100K lines of Rust, $20K API cost, ~2,000 sessions) [V] is a valid proof point that modern agents can navigate large Rust codebases, but several important caveats apply: the Rust code quality was characterised by the experiment author as "reasonable but nowhere near the quality of what an expert Rust programmer might produce," [V] the experiment required specialised harness infrastructure and significant API investment, and the task was systems programming under automated oracle validation — not the business-logic, integration-heavy, operational maintenance context of the Document Verification Service. [V] The correct updated framing for the final document is: Rust AI-coding velocity is meaningfully better than a stale 2023-era prior would suggest, but Rust still carries reviewer-fluency and ecosystem-ergonomics risk for this specific business-service context. Not "AI agents can't do Rust" — rather "Rust imposes higher iteration overhead and reviewer burden in a business-logic context than Go, C#, or TypeScript." [U]

---

## New items I'm raising

*(None. All substantive interpretive issues are now resolved. The ledger is clean.)*

---

## Phase artifact

### AGREED_INTERPRETATION

#### Scope
- In scope:
  - Selecting one backend language for the Document Verification Service's server-side modular monolith (API process, outbox worker, analysis worker, scheduled-task worker — all sharing one codebase, one container image, deployed as separate process types).
  - Tier 1 pass/fail assessment for all seven candidates: Go, Rust, Python, TypeScript/Node.js, C#/.NET, Kotlin, Java.
  - Tier 2 ordinal scoring (Strong / Adequate / Weak per sub-criterion) for all Tier 1 survivors, with criterion 2.1 (AI-coding-automation fitness) load-bearing in the final ordering.
  - Tier 3 tie-breaker application if and only if Tier 2 does not produce a clear winner.
  - Single ranked recommendation (#1 through #N or explicit Tier 1 eliminations), decision confidence (HIGH/MEDIUM/LOW), flip criteria, and any final-surfaced disagreements.
  - Explicit carry-forward assumptions for all organisation-specific facts that cannot be verified within this run.
- Out of scope:
  - Frontend technology (Lit web components / React — already decided).
  - Database, cloud provider, observability backend (already decided).
  - Architecture pattern (modular monolith — already decided).
  - Multi-region deployment, Phase 2 features.
  - Any language not in the seven named candidates.

#### Approach
Research will be conducted by both agents using web search and reasoning. The criteria framework in the brief is authoritative — neither agent will override it without sourced evidence that a stated criterion is factually wrong. Tier 2 scoring uses an ordinal rubric (Strong / Adequate / Weak) per sub-criterion per candidate, with each rating requiring a stated reason. Criterion 2.1 (AI-coding-automation fitness) must be load-bearing: if the #1 candidate does not have the highest overall 2.1 rating, the document must explicitly justify the override. Within 2.1, the agreed sub-weight priority is: (1) type-system depth and refactoring safety — primary; (2) test scaffolding and determinism — primary-to-secondary; (3) codebase comprehensibility and explicit semantics — secondary; (4) convention-over-configuration — secondary/tertiary; (5) training-data adequacy — floor only. Tier 1.4 (MCP library) is treated generously: all seven candidates pass because all have either official SDKs or mature community libraries; quality differentials appear as Tier 2.3 nuances, not Tier 1 eliminations. The AI-agent operating model assumption is: long-lived agentic maintenance — autonomous multi-file refactors, test-driven iteration loops, human review of agent-proposed changes. Team familiarity is Tier 3, not Tier 2, per the brief's explicit instruction; it appears as an explicit flip condition, not a scoring factor. Cold-start and memory footprint are real Tier 2.4 signals but not eliminative. All unresolvable organisation-specific inputs (internal platform catalog, min-replica production setting, primary AI agent identity) are carried as explicit assumptions with confirmation steps noted in the final document.

#### Carry-forward items
- [Q-input-c-01] acknowledged: AI agent operating model is agent-agnostic per brief; carry-forward assumption is long-lived agentic maintenance (autonomous multi-file refactors, test-driven loops, human review) — client confirmation would not change the framework, only calibrate specific agent-tooling notes.
- [Q-input-c-03] acknowledged: "separate processes inside the same container image" interpreted as separate process types/entrypoints launched by the platform, not OS-level multi-process supervision inside one container instance — client confirmation needed only if the internal platform mandates something unusual.
- [Q-input-c-04] acknowledged: scale-to-zero vs. min-replica production setting unknown; cold-start treated as a real Tier 2.4 signal; flip condition stated if production confirms min-replicas ≥ 1, which would reduce the JVM cold-start penalty from recurring to deployment-only.
- [Q-input-g-01] resolved: Tier 1.1 (internal platform catalog) assumed pass for all seven candidates — mainstream Azure/Container Apps runtimes — with an explicit assumption box in the final document requiring client confirmation.

---

## STATUS: AGREED