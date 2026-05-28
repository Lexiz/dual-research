## Stance

This brief asks for a decision-grade recommendation on which backend language to use for the Document Verification Service's server-side modular monolith, from a field of seven candidates (Go, Rust, Python, TypeScript/Node.js, C#/.NET, Kotlin, Java). The task is to apply a three-tier criteria framework rigorously, with AI-coding-automation fitness (2.1) carrying the highest weight in Tier 2. My posture is to treat the criteria framework as authoritative while probing its assumptions — particularly around AI-coding fitness, where the framing has real empirical content that deserves scrutiny — and to flag any under-specified inputs that could change the outcome before we begin research.

## Status

STATUS: IN_PROGRESS
RAISED_THIS_TURN: [Q-input-c-01, Q-input-c-02, Q-input-c-03, Q-input-c-04, D-input-g-01, D-input-g-02]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 4
OPEN_DISAGREEMENTS: 2
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0

---

## Addressing items raised against me

*(None — first round.)*

---

## Ratifying my own items

*(None — first round.)*

---

## New items I'm raising

### RAISE
kind: question
body: |
  The brief says the service will be "developed and maintained substantially by AI coding agents
  (Claude Code, GitHub Copilot, future agents on top of capable models)." It does not specify
  the *primary* agent(s) — whether the dominant agent is Claude Code (Anthropic), Copilot
  (OpenAI/GitHub), Cursor, or a mix. This matters for criterion 2.1 because different agents
  have different language-specific strengths in their context-window tooling, LSP integration,
  and test-loop fidelity. If Claude Code is the dominant agent, its tool-use loop with strongly-
  typed languages may differ from Copilot's inline completion model. Does the brief or the
  team have a known primary agent, or is this genuinely agent-agnostic?
anchor_type: quote
anchor_text: "developed and maintained substantially by AI coding agents (Claude Code, GitHub Copilot, future agents on top of capable models)"
evidence_required: false
> quote: "developed and maintained substantially by AI coding agents (Claude Code, GitHub Copilot, future agents on top of capable models)"

### RAISE
kind: question
body: |
  The brief states the external programmatic surface is an "MCP server" and that AI agents
  invoke the service as an "MCP skill." Criterion 1.4 requires a "Mature MCP server library
  available (or feasible to implement without significant effort)." The MCP protocol is very
  new (late 2024 / early 2025). Before we can grade candidates on 1.4, we need to know:
  which languages currently have official or well-maintained community MCP server SDKs, and
  what the brief's team considers "mature" versus "feasible to implement without significant
  friction." Should we treat languages without an official SDK but with a thin HTTP+SSE
  implementation path as a pass or a conditional pass? This affects whether any candidates
  are eliminated at Tier 1 versus derated at Tier 2.
anchor_type: quote
anchor_text: "Mature MCP server library available (or feasible to implement without significant effort)"
evidence_required: false
> quote: "Mature MCP server library available (or feasible to implement without significant effort)"

### RAISE
kind: question
body: |
  The brief says "four bounded contexts" with "one codebase (the modular monolith)" running
  "as separate processes inside the same container image." This is an unusual runtime topology:
  single image, multiple processes. The choice of language affects how cleanly this is expressed.
  Does the internal platform (Azure Container Apps) have any constraint on multi-process
  container images — e.g., does it mandate a single entrypoint, use a process supervisor
  (s6, supervisord), or have a preferred pattern? This matters for criterion 2.2 (concurrency
  model fit) because some languages make multi-process-from-one-codebase trivially clean
  (Go, .NET with Worker Services), while others (Python) require extra scaffolding.
anchor_type: quote
anchor_text: "run as separate processes inside the same container image"
evidence_required: false
> quote: "run as separate processes inside the same container image"

### RAISE
kind: question
body: |
  Criterion 2.4 mentions "cold-start latency for the API process (Container Apps scale-from-zero
  or low-min scenarios)" as a concern, specifically flagging JVM languages. The brief does not
  specify whether the service will routinely scale to zero or whether a minimum of 1 replica is
  always maintained. If min-replicas ≥ 1, the cold-start penalty for JVM languages is a one-time
  deployment concern, not a recurring operational concern, which would significantly change the
  JVM penalty in the scoring. Is scale-to-zero expected in production, or is a minimum replica
  count already decided?
anchor_type: quote
anchor_text: "cold-start latency for the API process (Container Apps scale-from-zero or low-min scenarios)"
evidence_required: false
> quote: "cold-start latency for the API process (Container Apps scale-from-zero or low-min scenarios)"

### RAISE
kind: disagreement
body: |
  The brief frames criterion 2.1 (AI-coding-automation fitness) as "HIGHEST WEIGHT" and lists
  five sub-factors, but does not supply relative weights among those sub-factors. "Convention-
  over-configuration" and "type-system depth" are both listed, but they can pull in opposite
  directions: Python has moderate typing (optional, typed via mypy/pyright) and moderate
  convention; Go has very strong convention ("one obvious way") but a shallower type system
  than C# or Kotlin; TypeScript has rich types but multiple viable frameworks (Express, Fastify,
  Hono, NestJS) creating convention fragmentation. Without sub-weights or a stated priority
  ordering among the five sub-factors, two analysts evaluating 2.1 can rank Go above TypeScript
  or TypeScript above Go with equal fidelity to the criteria. The brief should either supply
  sub-weights, or the analysis should declare and defend a priority ordering before scoring.

  How this would change the final document: if "type-system depth" is primary within 2.1,
  C# and Kotlin score highest; if "convention-over-configuration" is primary, Go scores highest;
  if both matter equally, the ranking tightens between Go, C#, and Kotlin, and the recommendation
  could go any of those three ways.
anchor_type: quote
anchor_text: "Type-system depth. Rich, expressive static typing that catches errors at edit-time"
evidence_required: false
> quote: "Type-system depth. Rich, expressive static typing that catches errors at edit-time"

### RAISE
kind: disagreement
body: |
  The brief's "Risk shapes by candidate" section characterises Rust as carrying "development-
  velocity-vs-iteration-speed risk for AI agents (compile times, lifetime errors)." This framing
  may be 6–12 months stale: AI coding agents (Claude Code in particular) have meaningfully
  improved at Rust borrow-checker reasoning in 2025, and incremental compilation in Rust has
  improved substantially. The brief states this as context rather than a criterion, but it
  influences how analysts weight Rust — especially if an analyst treats the risk-shapes section
  as an authoritative prior. If the research finds that AI-agent Rust velocity in 2025–2026 is
  materially better than the brief implies, this prior should be updated rather than carried
  forward into the scoring.

  How this would change the final document: if Rust's AI-coding risk is lower than briefed,
  Rust may move from a Tier 1 pass / Tier 2 weak candidate to a credible contender, changing
  the ranked list and possibly the recommendation.
anchor_type: quote
anchor_text: "Rust carries development-velocity-vs-iteration-speed risk for AI agents (compile times, lifetime errors)"
evidence_required: false
> quote: "Rust carries development-velocity-vs-iteration-speed risk for AI agents (compile times, lifetime errors)"