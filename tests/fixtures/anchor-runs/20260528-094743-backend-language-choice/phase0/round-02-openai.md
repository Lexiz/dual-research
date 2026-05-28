## Stance
We are converging on an input interpretation: the supplied criteria framework should remain authoritative, but unresolved organization-specific facts must be carried as explicit assumptions or flip criteria rather than silently invented. [U] I agree with Claude that Tier 2 should use ordinal scoring and that 2.1 must be load-bearing; I also think the MCP question is now resolvable without eliminating any candidate, though the current official SDK tiering differs in a few details from Claude’s summary. [V] ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/sdk)) I am not ready to emit `AGREED` until Claude ratifies the assumptions I propose below for his open items. [U]

## Status
STATUS: IN_PROGRESS  
RAISED_THIS_TURN: []  
ADDRESSED_THIS_TURN: [Q-input-c-01, Q-input-c-02, Q-input-c-03, Q-input-c-04, D-input-c-01, D-input-c-02]  
RESOLVED_THIS_TURN: [Q-input-g-01, Q-input-g-02, Q-input-g-03, D-input-g-01, D-input-g-02]  
ACKNOWLEDGED_THIS_TURN: []  
WITHDRAWN_THIS_TURN: []  
OPEN_QUESTIONS: 0  
OPEN_DISAGREEMENTS: 0  
ADDRESSED_QUESTIONS: 4  
ADDRESSED_DISAGREEMENTS: 2  

## Addressing items raised against me

### ADDRESS Q-input-c-01
response: |
  I do not think we can identify a primary AI coding agent from the brief alone. [U] The brief names Claude Code, GitHub Copilot, and future agents, which I read as intentionally agent-agnostic rather than as a hidden preference for one vendor or workflow. [U]

  My proposed carry-forward assumption is: score 2.1 against long-lived, human-reviewed agentic maintenance rather than greenfield-only generation or inline autocomplete. [U] That means autonomous multi-file edits, test-driven repair loops, and reviewer comprehension all matter. [U] If the client later says the dominant workflow is, for example, Claude Code terminal-agent automation or Copilot inline completion only, the 2.1 scoring should be revisited as a sensitivity check. [U]

  I propose this item be treated as unresolvable within Phase 0 because the missing fact is client-specific, but with the above assumption carried into the research plan. [U]
proposes_status: acknowledged_proposed

### ADDRESS Q-input-c-02
response: |
  I agree that MCP SDK maturity must be handled carefully because it can affect Tier 1 eliminations versus Tier 2 derating. [U] Current official MCP documentation lists official SDKs and classifies TypeScript, Python, C#, and Go as Tier 1; Java and Rust as Tier 2; and Kotlin as TBD. [V] The same official page says SDKs support building MCP servers and clients, local and remote transports, and protocol compliance with type safety. [V] ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/sdk))

  My proposed interpretation: no candidate should be eliminated solely on MCP grounds at Tier 1.4. [U] TypeScript, Python, C#, and Go get a clear Tier 1.4 pass based on official Tier 1 SDK status. [V] Java and Rust pass because official Tier 2 SDKs exist, but they should carry a maturity note under 2.3. [V] Kotlin should be marked as conditional pass rather than clear pass: the official SDK page lists Kotlin but with tier “TBD,” so Kotlin’s Tier 1.4 pass depends on either the Kotlin SDK being acceptable despite TBD status or using JVM/Java interop without material friction. [V] ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/sdk))

  This differs slightly from Claude’s prior summary: I would not describe Kotlin as a settled official mature pass unless later research confirms that status from an official source. [V] This does not change the likely final recommendation unless Kotlin is otherwise near #1; it changes the exact Tier 1.4 row and the Tier 2 ecosystem-risk note. [U]
proposes_status: addressed

### ADDRESS Q-input-c-03
response: |
  We do not have the internal platform’s preferred runtime pattern for “same image, separate processes.” [U] I agree the phrase is ambiguous: it could mean one container image with different entrypoints deployed as separate app/worker processes, or it could mean multiple OS processes supervised inside a single running container. [U]

  My proposed carry-forward assumption is the former: one codebase and one container image, with API, outbox worker, analysis worker, and scheduler launched as separate process types or commands by the platform/deployment definition, not four long-lived processes supervised inside one container instance. [U] That assumption keeps the language comparison focused on codebase/process ergonomics, worker concurrency, and connection-pool safety rather than on container-supervisor mechanics. [U]

  If the internal platform actually mandates multiple long-lived processes inside one container, the final document should add an operational-risk note, but I do not think that would eliminate any candidate by itself. [U] It would mostly penalize stacks whose worker/process packaging is awkward or convention-poor. [U]
proposes_status: acknowledged_proposed

### ADDRESS Q-input-c-04
response: |
  We cannot determine from the brief whether production will run with scale-to-zero or minimum replicas. [U] Because criterion 2.4 explicitly mentions cold start for Container Apps scale-from-zero or low-min scenarios, I think the safe interpretation is to score cold-start and memory footprint as real Tier 2.4 signals, but not as eliminative constraints. [U]

  My proposed carry-forward assumption: production may use low-min or scale-to-zero-like behavior for non-API workers and possibly the API in lower environments, so cold start remains relevant. [U] If production API min replicas are guaranteed to be at least one, JVM cold-start risk should be downgraded from recurring operational concern to deployment/incident-recovery concern. [U] That would improve Java/Kotlin slightly under 2.4 but would not erase memory-footprint and container-density considerations. [U]
proposes_status: acknowledged_proposed

### ADDRESS D-input-c-01
response: |
  I agree with the core disagreement: the analysis must declare a priority ordering within 2.1 rather than pretending the sub-factors are self-weighting. [U] My proposed priority is:

  1. Type-system depth and refactoring safety are primary because the brief explicitly emphasizes edit-time error detection and large-scale AI refactors. [U]
  2. Test scaffolding and determinism are also primary-to-secondary because the assumed workflow is test-loop-driven maintenance, not one-shot generation. [U]
  3. Codebase comprehensibility and explicit semantics are secondary but still important because reviewers and agents must reason across bounded contexts. [U]
  4. Convention-over-configuration is secondary: it helps agents produce idiomatic code, but it should not override materially weaker type/refactor safety. [U]
  5. Training-data adequacy remains a floor, as the brief instructs, not a ranking factor above the floor. [U]

  This means I would not let Go win 2.1 solely because it is highly conventional if C# or Kotlin materially outperform it on type depth and refactoring safety. [U] Conversely, I would not let TypeScript win 2.1 solely because it has abundant backend examples or frontend alignment if framework fragmentation and weaker runtime guarantees create review risk. [U]

  Final-document effect: the Tier 2 table should show sub-ratings for 2.1, then an overall 2.1 rating, and the recommendation must explain why the winner either wins 2.1 or justifiably overrides it. [U]
proposes_status: addressed

### ADDRESS D-input-c-02
response: |
  I partially agree that the Rust risk framing should be updated, but I do not think the update is strong enough to make Rust a default top contender for this service. [U] Secondary reports describe an Anthropic/Claude-agent experiment in which 16 Claude agents produced a roughly 100,000-line Rust C compiler that compiled Linux 6.9 and reportedly passed about 99% of GCC torture tests. [V] ([linux-magazin.de](https://www.linux-magazin.de/news/team-aus-claude-opus-4-6-agenten-schreibt-autonom-c-compiler-in-rust/?utm_source=openai)) That is meaningful evidence that modern agentic workflows can operate in a large Rust codebase under a highly scaffolded, test-oracle-heavy setup. [U]

  However, I would not treat that as direct evidence that Rust is equally efficient for a B2B document-verification modular monolith. [U] The experiment appears to be a specialized systems-programming benchmark with unusually strong automated validation, while this service is business logic, integrations, OAuth/OIDC, database sessions, worker orchestration, document workflows, and operational maintenance. [U] Those tasks stress library ergonomics, build iteration, hiring/reviewer fluency, and ecosystem fit differently from compiler construction. [U]

  My proposed final treatment: revise the brief’s Rust risk from “AI agents struggle with Rust” to “Rust is increasingly viable for agentic coding, but still carries iteration-speed, reviewer-fluency, and ecosystem-ergonomics risk for this business-service context.” [U] That would improve Rust’s narrative relative to a stale pessimistic prior, but I would still expect Rust to need unusually strong evidence on 2.1 and 2.3 to overtake Go, C#, TypeScript, or a JVM option. [U]
proposes_status: addressed

## Ratifying my own items

### RESOLVE Q-input-g-01
reason: |
  I accept Claude’s answer because it preserves Tier 1.1 as a required row while making the missing internal catalog explicit as an assumption rather than pretending we verified a private company list. [U] The final document should say mainstream Azure/container support is not identical to internal catalog approval. [U]

### RESOLVE Q-input-g-02
reason: |
  I accept the proposed ordinal rubric because Strong/Adequate/Weak avoids false numerical precision while still satisfying the brief’s requirement for Tier 2 scoring. [U] I also accept the added requirement that 2.1 sub-factors be scored visibly and that 2.1 remain load-bearing in the final ordering. [U]

### RESOLVE Q-input-g-03
reason: |
  I accept Claude’s operating-model assumption because it matches the brief’s wording better than either greenfield-only generation or autocomplete-only use. [U] The final document should explicitly state the assumption: long-lived agentic maintenance, test-driven loops, multi-file refactors, and human review. [U]

### RESOLVE D-input-g-01
reason: |
  I accept Claude’s resolution because it respects the brief’s explicit instruction not to elevate team familiarity above Tier 3 while still preserving my concern as a flip criterion. [U] That is the right compromise: familiarity should not rewrite the scoring framework, but severe reviewer-fluency mismatch can change the risk-adjusted recommendation. [U]

### RESOLVE D-input-g-02
reason: |
  I accept the core resolution: MCP library support should not eliminate any candidate at Tier 1 unless follow-up research finds a candidate cannot implement the required server surface without significant friction. [U] Current official MCP SDK documentation supports a differentiated treatment rather than a hard elimination: TypeScript, Python, C#, and Go are Tier 1; Java and Rust are Tier 2; Kotlin is listed but TBD. [V] ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/sdk)) The final document should therefore mark MCP as pass/conditional-pass and carry maturity differences into 2.3. [U]

## New items I'm raising

(none)