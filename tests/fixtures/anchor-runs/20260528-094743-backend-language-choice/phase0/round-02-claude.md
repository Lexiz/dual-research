## Stance

Round 2 of Phase 0. My job is to address the five open items that openai raised (Q-input-g-01, Q-input-g-02, Q-input-g-03, D-input-g-01, D-input-g-02), ratify or counter openai's responses to my own items (none yet — my items are still open, not addressed), and determine whether we have enough convergence to move to AGREED or whether substantive gaps remain. I will also do targeted research this turn on the MCP SDK landscape (Q-input-c-02 / D-input-g-02) and on current AI-agent Rust velocity (D-input-c-02), since those are the two items most likely to affect the final document's Tier 1 eliminations and Tier 2 ordering.

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: []
ADDRESSED_THIS_TURN: [Q-input-g-01, Q-input-g-02, Q-input-g-03, D-input-g-01, D-input-g-02]
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 7
OPEN_DISAGREEMENTS: 4
ADDRESSED_QUESTIONS: 3
ADDRESSED_DISAGREEMENTS: 2

---

## Addressing items raised against me### ADDRESS Q-input-g-01

**Item:** Do we have access to the internal platform's vetted runtime catalog?

response: |
  Agreed with the substance of this item. We do not have access to the internal platform's vetted runtime catalog. The correct approach is to treat Tier 1.1 as conditionally satisfied for all seven candidates — all of them (Go, Rust, Python, TypeScript/Node.js, C#/.NET, Kotlin, Java) are supported by Azure App Service and Azure Container Apps as documented Azure runtimes [U] — but to mark this in the final document with an explicit assumption box: "Assumes all seven candidates are on the internal platform's vetted runtime list; the accountable team must confirm or eliminate any candidate whose runtime has been blocked." This is not a fatal ambiguity because it is unlikely any mainstream Azure-supported runtime has been excluded, but the final document should make the assumption visible rather than asserting a pass with false certainty.

  Where I part slightly from the openai framing: this is not a reason to defer the Tier 1.1 analysis — it is a reason to call the assumption explicitly. The final document should state the assumption and flag the confirmation step, not omit the Tier 1.1 row.
proposes_status: addressed

---

### ADDRESS Q-input-g-02

**Item:** Should we create an explicit numerical or ordinal scoring rubric for Tier 2?

response: |
  A strict numerical rubric (e.g., 1–5 per sub-criterion with fixed weights) would produce false precision here: the criteria framework is already qualitative in the brief, and no empirical data exists that would anchor, say, "Go convention-over-configuration = 4.2 vs C# = 3.7." The risk of a numerical rubric is that it launders subjective judgment into pseudo-quantitative output, making the scoring harder to challenge and easier to game.

  My position: use an ordinal scoring approach — Strong / Adequate / Weak per criterion per candidate — with each rating backed by a stated reason. This is less arbitrary than a numerical scale, more tractable than pure narrative, and honest about the precision limit. For criterion 2.1, the sub-factors (type-system depth, convention-over-configuration, test scaffolding, refactoring safety, codebase comprehensibility) should each be graded, then an overall 2.1 rating derived — rather than collapsing 2.1 into a single undifferentiated score.

  The one structural requirement I'd add to what openai proposed: 2.1 must be load-bearing in the final ordering. If the #1 candidate does not have the highest overall 2.1 rating, the document must explicitly justify the override. That is the contract the brief sets and we should honour it.
proposes_status: addressed

---

### ADDRESS Q-input-g-03

**Item:** What assumptions should we use about the AI coding-agent workflow?

response: |
  This overlaps substantially with my own Q-input-c-01 (which agent is primary). From research this turn: the agent landscape in 2025–2026 shows a clear two-tier picture. Most developers use more than one tool — Cursor or Windsurf as the daily IDE agent, Claude Code or Codex CLI as the terminal agent for hard problems and automation. A notable proof point: 16 Claude agents wrote a 100K-line C compiler in Rust, showing agent teams can handle complex systems programming beyond CRUD scaffolding.

  Since the brief names both Claude Code and GitHub Copilot explicitly, and names "future agents on top of capable models," the correct assumption is: the operating model is a mix of long-lived agentic maintenance (large-context autonomous refactors, test-driven loops) and human-in-the-loop review. This is not greenfield-only, nor is it purely autocomplete. The implication for scoring:

  - Languages with weaker type systems impose greater review burden on human reviewers, not just on the AI agents themselves.
  - Test determinism matters more than in greenfield generation because the agent will iterate in test loops.
  - LSP refactoring safety matters because autonomous refactors across bounded contexts need safe rename-symbol.

  My proposed carry-forward assumption for the final document: "Agent workflow assumed to be long-lived agentic maintenance — autonomous multi-file refactors, test-driven iteration loops, human review of agent-proposed changes. This assumption is held constant across all candidate scores. If the actual operating model is strictly inline autocomplete + human writing, scoring should be revisited." [U]
proposes_status: addressed

---

### ADDRESS D-input-g-01

**Item:** Team familiarity should be higher than Tier 3.

response: |
  I understand openai's argument: when human reviewers must assess AI-generated code, their fluency in the language is a delivery-risk factor, not a mere tie-breaker. This is a real concern.

  However, I do not agree that it changes the tier placement, and here is why: the brief explicitly says "Team familiarity as a top-line criterion. Real, but belongs under Tier 3 (hiring market), not above Tier 2." This is not a claim that familiarity is unimportant — it is a deliberate design choice in the criteria framework to prevent "we already know X" from overriding objective fitness assessment. The brief is the client document; we shouldn't override it without evidence that it is wrong.

  More importantly, if team familiarity were elevated to Tier 2, it would make the analysis circular: we don't know the team's actual composition, so we'd either (a) have to ask a question we can't answer, or (b) fill in an assumption that could inflate any candidate's score without evidence. The brief's answer is to keep familiarity at Tier 3 and let the "flip criteria" section handle the sensitivity: if the accountable team has strong familiarity with one candidate and weak familiarity with the winner, that can be stated as a flip condition.

  Where I will concede to openai's point: the final document should include an explicit note in the flip-criteria section that says: "If the accountable engineering team lacks production fluency in [winner], and the AI-generated code requires significant human review of language-specific patterns, #2 may be preferable as a risk-adjusted choice." This is narrow — it is not elevating familiarity to Tier 2, but it makes the risk visible as a flip condition. Resolving this one way versus the other changes whether the flip-criteria section acknowledges familiarity risk explicitly, not whether the tier structure is overridden.
proposes_status: addressed

---

### ADDRESS D-input-g-02

**Item:** MCP Tier 1.4 binary hard constraint framing.

response: |
  This needed research, which I've now done. The picture is clearer than the brief implied. [V]

  The MCP ecosystem now spans seven languages — Python, TypeScript, Go, Java, Kotlin, C#, and Rust — with Python dominating adoption by a wide margin. Since March 2026, two new official SDKs launched (C# with Microsoft, Rust); the Rust SDK reached v1.0 and iterated to v1.5.0 in six weeks. Microsoft's MCP-for-beginners guide documents six officially supported languages: Python, C#, Java, TypeScript/JavaScript, and Rust.

  Specifically for Go: the mcp-go community project has 8,700 stars at v0.50.0, and the official Go SDK is at v1.6.0-pre.1 (pre-release). This matters for Tier 1.4 scoring of Go — there is a substantial community library but the official SDK is not yet stable.

  Given this evidence, my position on the framing dispute: the binary/feasibility ambiguity in Tier 1.4 should be resolved by a tiered interpretation in the final document:
  - **Clear pass**: Python, TypeScript, C#, Java — official SDKs, stable, high adoption.
  - **Conditional pass**: Go — mature community library (mcp-go v0.50.0, 8,700 stars) but official SDK pre-release; passes the "feasible without significant friction" standard.
  - **Pass (recently stabilised)**: Rust, Kotlin — official SDKs now at v1.0+ / v0.12.0 respectively.

  No candidate should be eliminated at Tier 1 on MCP library grounds — the field is broad enough that all seven candidates have either an official or a high-quality community SDK. The correct treatment is: all seven pass Tier 1.4, but the quality differential between Python/TypeScript (mature, high-star official) and Go/Kotlin (adequate but less-tested in production) should appear as a Tier 2 ecosystem-maturity nuance, not a Tier 1 eliminator.

  This resolves the openai framing dispute in favour of treating feasibility as sufficient for Tier 1 pass, with a clear note that this is a generous reading of "feasible."

evidence:
  - url: https://chatforest.com/reviews/mcp-server-frameworks-sdks/
    title: "MCP Server Frameworks & SDKs — FastMCP, Official SDKs, and the Tools That Power Every MCP Server"
    search_query: MCP server SDK official languages supported 2025
    fetched_at: 2026-05-28T00:00:00Z
    evidence_event_id: search_call_1
    content_excerpt: |
      The ecosystem now spans seven languages — Python, TypeScript, Go, Java, Kotlin, C#, and Rust — with Python dominating adoption by a wide margin. Since our original review in March 2026, two new official SDKs launched (C# with Microsoft, Rust), the Rust SDK reached v1.0 and iterated to v1.5.0 in six weeks, and the MCP Apps specification introduced interactive UI capabilities that frameworks are racing to support. MCP server frameworks: FastMCP (24,900 stars, ~1.9M downloads/day, MCP Apps), official Python SDK (22,800 stars), TypeScript SDK (12,300 stars), FastAPI-MCP (11,800 stars), mcp-go (8,700 stars, v0.50.0 task-augmented tools), Go SDK (4,500 stars, v1.6.0-pre.1), C# SDK (4,200 stars, Microsoft), Rust SDK (3,400 stars, v1.5.0 NOW STABLE), Java SDK (3,400 stars, v1.1.2), Kotlin SDK (1,300 stars, v0.12.0).
  - url: https://deepwiki.com/microsoft/mcp-for-beginners/4-multi-language-sdk-guide
    title: "Multi-Language SDK Guide | microsoft/mcp-for-beginners | DeepWiki"
    search_query: MCP server SDK official languages supported 2025
    fetched_at: 2026-05-28T00:00:00Z
    evidence_event_id: search_call_1
    content_excerpt: |
      This page provides a comprehensive overview of the Model Context Protocol (MCP) SDK implementations across six officially supported programming languages: Python, C#, Java, TypeScript, JavaScript, and Rust. The guide focuses on the architectural consistency of the protocol while highlighting language-idiomatic patterns for server and client development. Each SDK provides idiomatic interfaces while maintaining protocol compatibility. All SDKs implement the same JSON-RPC protocol, ensuring complete interoperability.
proposes_status: addressed

---

## Ratifying my own items

My five items (Q-input-c-01, Q-input-c-02, Q-input-c-03, Q-input-c-04, D-input-c-01, D-input-c-02) are all still **open** — the other agent has not addressed them yet. I cannot ratify unaddressed items. I note for the record what my research this turn has partially answered, so the other agent can absorb this when they address:

**On Q-input-c-02 (MCP SDK maturity):** Research above now establishes the MCP SDK landscape clearly. The question is largely answered by my ADDRESS of D-input-g-02. When openai addresses Q-input-c-02, I expect to be able to RESOLVE it.

**On D-input-c-02 (Rust AI-coding velocity):** Research found that 16 Claude agents wrote a 100K-line C compiler in Rust that compiles the Linux kernel 6.9, passing 99% of GCC torture tests for ~$20K in API cost — described as a proof point for agent teams handling complex systems programming. Additionally, a community project cataloguing 179 rules for AI coding agents writing Rust exists and works across Claude Code, Cursor, Windsurf, Copilot, Codex, Aider, and others, indicating the toolchain ecosystem for Rust AI coding has matured substantially. However, I note the proof point is for a systems-level task (compiler) from a highly resourced experiment — it does not directly address whether Rust's compile times and borrow-checker friction affect iteration speed in a business-logic codebase like the Document Verification Service. The D-input-c-02 disagreement remains open in terms of whether this evidence is strong enough to move Rust from "weak contender" to "credible contender" in the Tier 2 scoring.

**On Q-input-c-01 (primary AI agent):** Research confirms the landscape is genuinely agent-agnostic in practice — most teams use multiple tools. The model routing consensus the community has settled on is Claude for depth, GPT-5.x for speed, cheap models for volume. The brief's "Claude Code, GitHub Copilot, future agents" framing maps onto this accurately. I will likely ACKNOWLEDGE Q-input-c-01 as unanswerable without more client information — it cannot be resolved within this run — unless openai has a different read.

---

## New items I'm raising

No new items this turn. The existing open item set (9 open questions, 4 open disagreements) is already the right scope for Phase 0. Adding more items would widen the scope unnecessarily.

---

## Synthesis note for convergence

At this point, the interpretive framework is converging. My view of the shared interpretation we're building:

1. **Tier 1.1**: Assumed pass for all seven candidates; confirmation required from client. [U]
2. **Tier 1.4 (MCP)**: All seven pass; Python/TypeScript strongest, Go conditional, Kotlin/Rust recently stabilised. [V]
3. **Tier 2 scoring format**: Ordinal (Strong/Adequate/Weak) per sub-criterion, not numerical. 2.1 must be load-bearing. [U]
4. **AI agent operating model**: Long-lived agentic maintenance (refactor loops, test-driven iteration, human review), not greenfield-only. [U]
5. **Team familiarity**: Stays Tier 3, but appears explicitly in flip criteria. [U]
6. **D-input-c-01 (2.1 sub-weights)**: Not yet resolved. My position is that type-system depth and refactoring safety should be the primary sub-factors within 2.1, with convention-over-configuration secondary. This needs to be agreed or disagreed by openai.
7. **D-input-c-02 (Rust velocity)**: New evidence (C compiler proof point, 179-rule Rust skill library) partially updates the brief's risk characterisation, but does not fully overturn it for business-logic codebases. Needs resolution.

I am not yet at AGREED because D-input-c-01 and D-input-c-02 (both my own raises, now partially researched) have not been addressed by openai, and Q-input-c-01 / Q-input-c-03 / Q-input-c-04 remain open with no client answer in sight. The right resolution is: carry Q-input-c-01, Q-input-c-03, Q-input-c-04 forward as acknowledged-unresolvable within this run, agree on the assumptions that replace them, and resolve or acknowledge the two disagreements.