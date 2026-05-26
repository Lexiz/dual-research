## Stance

The brief asks us to rank seven backend language candidates for a Document Verification Service's server-side modular monolith, with one clear winner named. The task is heavily weighted toward AI-coding-automation fitness (Tier 2.1) as the dominant ordering criterion, with concurrency model, ecosystem maturity, and observability as secondary Tier 2 axes. My posture is to accept the framework largely as written — it is carefully constructed to suppress known biases — but to challenge two specific framings before we commit to them, since they could materially affect the final ranking.

## Addressing items raised against me

*(None — first round.)*

## Ratifying my own items

*(None — first round.)*

## New items I'm raising

---

### RAISE
kind: disagreement
body: |
  The brief lists "Convention-over-configuration" as a sub-attribute of Tier 2.1 (AI-coding-automation fitness), described as "There is one obvious way to do it languages score higher." This framing systematically advantages Go (famous for its single idiomatic style) and disadvantages languages with rich type-system expressiveness like Kotlin and C#, where multiple equally-valid idiomatic patterns co-exist (coroutines vs reactive, data classes vs records, etc.). The problem is that the attribute conflates two distinct things: (a) idiomatic consistency — does the community converge on one style? — and (b) expressive power — can the type system enforce domain invariants? For AI-coding-automation fitness, (b) arguably matters more than (a): a rich type system lets the LLM encode business rules in types, making errors compile-time rather than test-time. If we score Kotlin/C# low on "convention-over-configuration" because they offer multiple idioms, we may inadvertently penalise them on the criterion that should most reward them (type-system depth).

  Concretely: resolving this one way (treating "one obvious way" as genuinely load-bearing within 2.1) would push Go upward relative to Kotlin/C# even though Go's type system is materially weaker. Resolving it the other way (treating "expressive static typing" as the dominant sub-attribute within 2.1, with convention as a secondary sub-attribute) could reorder the top-3. This is not a cosmetic distinction.

  Proposed resolution: Treat type-system depth as the dominant sub-attribute within 2.1, convention-over-configuration as a secondary sub-attribute (acts as a tiebreaker within similar type-system tiers), and be explicit in the final document about that weighting.
anchor_type: quote
anchor_text: "Convention-over-configuration. Idiomatic patterns that are widely shared"
evidence_required: false
> quote: "Convention-over-configuration. Idiomatic patterns that are widely shared across the ecosystem"

---

### RAISE
kind: question
body: |
  The brief states that "AI agents invoke the Document Verification Service as an MCP skill on behalf of users" and lists "Mature MCP server library available (or feasible to implement without significant effort)" as a hard constraint (1.4). However, the MCP SDK landscape is still rapidly evolving (official SDKs from Anthropic exist for Python and TypeScript; community SDKs exist for others). 

  Specifically: does "feasible to implement without significant effort" mean (a) a maintained community port exists, or (b) the MCP protocol spec is simple enough that a minimal server can be hand-rolled in a weekend? The answer materially affects whether Go and Rust pass Tier 1 constraint 1.4 or are eliminated. If "feasible" is interpreted strictly (requiring a maintained library), Go and Rust may face real Tier 1 risk. If loosely (spec is approachable), all seven candidates pass easily and the constraint becomes non-differentiating.

  I intend to research the current MCP SDK landscape this run. Flagging as a question so the other agent can coordinate and avoid duplicate research.
anchor_type: quote
anchor_text: "Mature MCP server library available (or feasible to implement without significant effort)"
evidence_required: false
> quote: "Mature MCP server library available (or feasible to implement without significant effort)"

---

### RAISE
kind: disagreement
body: |
  The brief frames the "Risk shapes by candidate" section as "context, not a prescription." But the listed risks for Python and TypeScript are notably softer than those for Go, Rust, and JVM languages. Specifically:

  - Python/TypeScript: "type-system-depth risk under heavy AI-driven refactoring" — this is precisely what Tier 2.1 measures, so it's redundant with the criteria.
  - Go: "ecosystem-gap risk for MCP server libraries and schema-validation codegen" — this is a Tier 1 hard-constraint risk, which if true would eliminate Go, not just penalise it.
  - Rust: "development-velocity-vs-iteration-speed risk for AI agents (compile times, lifetime errors)" — this is a legitimate Tier 2.1 concern, but the framing of "lifetime errors" could be read as prejudging how AI agents handle Rust.

  My concern: the asymmetric specificity of these risk descriptions could anchor both agents toward treating Python/TypeScript as "the middle ground with soft risks" and Go/Rust/JVM as "the risky choices." This is a framing effect, not an analytical conclusion. The criteria framework should produce the ranking, not the risk-shapes prose.

  Proposed resolution: Acknowledge that the risk-shapes section is intentionally asymmetric (Python/TypeScript risks are listed as criteria-level, Go/Rust/JVM risks are listed as operational/ecosystem-level) but explicitly note this asymmetry in the analysis so it doesn't silently bias the Tier 2 scoring. Both agent should independently verify the Go MCP ecosystem claim before treating it as a Tier 1 risk.
anchor_type: quote
anchor_text: "Go carries ecosystem-gap risk for MCP server libraries and schema-validation codegen"
evidence_required: false
> quote: "Go carries ecosystem-gap risk for MCP server libraries and schema-validation codegen"

---

### RAISE
kind: question
body: |
  The brief specifies "Modular monolith deployed as a single service" with four processes sharing one codebase and running as separate processes inside the same container image. The Tier 2.2 criterion evaluates concurrency model fit, but the architectural choice of "separate processes inside the same container image" is unusual — it means each language needs not just goroutines/async but actual OS-process management within a container (e.g., a process supervisor like s6-overlay or supervisord, or the language's own subprocess spawning).

  This may differentially affect languages: Go's model (single binary, multiple goroutines) would need to be run as multiple separate binaries or use internal process separation. JVM languages may have high per-process memory overhead if four JVM instances run in one container. Python with asyncio runs fine in one process but the "separate processes" requirement may require multiple Python interpreter instances.

  Question: Is the "separate processes inside the same container image" requirement firm? Or is it "separate logical units that could be deployed as separate processes if needed"? The answer affects how we score JVM languages on Tier 2.4 (memory footprint) and how we score all languages on Tier 2.2 (concurrency model).
anchor_type: quote
anchor_text: "run as separate processes inside the same container image"
evidence_required: false
> quote: "run as separate processes inside the same container image"

---

## Status

STATUS: IN_PROGRESS
RAISED_THIS_TURN: [Q-plan-c-01, Q-plan-c-02, D-input-g-01, D-input-g-02]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 2
OPEN_DISAGREEMENTS: 2
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0