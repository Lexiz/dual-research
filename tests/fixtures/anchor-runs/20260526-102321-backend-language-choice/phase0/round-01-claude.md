## Stance

This brief asks for a decision-grade analysis of seven candidate backend languages for a B2B Document Verification Service's modular monolith, with a heavily weighted criterion of AI-coding-automation fitness (2.1). My job this round is to interrogate the brief's framing, identify ambiguities that would materially affect the research or final recommendation, and flag any disagreements with how the task is scoped or structured — not to begin the actual language analysis yet. I'm taking a critical posture: the brief is well-structured but contains several underspecified inputs that could change the recommendation if resolved differently.

## Status
STATUS: IN_PROGRESS
RAISED_THIS_TURN: [Q-plan-c-01, Q-plan-c-02, Q-plan-c-03, Q-plan-c-04, D-input-g-01, D-input-g-02]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 4
OPEN_DISAGREEMENTS: 2
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0

## Addressing items raised against me
*(none — first round)*

## Ratifying my own items
*(none — first round)*

---

## New items I'm raising

### RAISE
kind: question
body: |
  The brief states that AI coding agents (Claude Code, GitHub Copilot) will
  develop and maintain this service "substantially," and criterion 2.1
  is marked as HIGHEST WEIGHT. But "substantially" is doing a lot of work.
  There is a spectrum from "AI suggests completions while humans drive
  architecture" to "AI agents autonomously write full features with humans
  reviewing diffs." These two modes weight the sub-criteria very differently:
  autonomous agents are bottlenecked on type-system safety and refactoring
  tooling; copilot-style assistance is bottlenecked more on training-data
  prevalence and IDE integration.

  What is the intended operating model for AI coding automation on this
  service? Specifically: will human engineers be authoring at the module
  and architecture level with AI assistance on implementation details, or
  are AI agents expected to own full bounded-context implementations
  autonomously with humans in a review/approval role?

  This materially affects how the 2.1 sub-criteria should be weighted
  relative to each other (especially type-system depth vs. convention-
  over-configuration vs. training-data floor).
anchor_type: quote
anchor_text: "will be developed and maintained substantially by AI coding agents"
evidence_required: false
> quote: "will be developed and maintained substantially by AI coding agents"

---

### RAISE
kind: question
body: |
  The brief is explicit that MCP server library maturity is a Tier 1 hard
  requirement (1.4), and states that Go "carries ecosystem-gap risk for MCP
  server libraries." But the MCP ecosystem is evolving rapidly (Anthropic
  released the MCP spec in late 2024). The brief does not state whether
  "feasible to implement without significant effort" in 1.4 means:
  (a) an official or community SDK already exists and is stable, or
  (b) it's acceptable to write a thin adapter against the raw MCP protocol
      spec if the language has a good HTTP/JSON foundation.

  This matters because Go and Rust may fail Tier 1 under interpretation (a)
  but pass under interpretation (b), while TypeScript and Python have
  official Anthropic SDKs that trivially satisfy (a). The threshold
  interpretation directly controls which candidates survive to Tier 2.
anchor_type: quote
anchor_text: "Mature MCP server library available (or feasible to implement without significant effort)"
evidence_required: false
> quote: "Mature MCP server library available (or feasible to implement without significant effort)"

---

### RAISE
kind: question
body: |
  The brief mentions "internal platform support" (Tier 1, constraint 1.1)
  referencing "Azure App Service / Container Apps" as the vetted catalog.
  All seven candidates run on Azure Container Apps in practice, so this
  constraint as written would pass all candidates trivially. The brief also
  mentions the platform is "Azure, West Europe v1" with an "internal
  platform" that has a "vetted catalog."

  Does the internal platform's vetted catalog impose any additional
  constraints beyond generic Azure Container Apps support — for example,
  approved base images, specific runtime versions, a preference for
  Microsoft-supported runtimes, or build pipeline toolchain requirements?
  If the vetted catalog is effectively "anything that runs in a container,"
  this constraint is non-discriminating. If it actually has an allowlist of
  runtimes or base images, some candidates might fail or have significantly
  different operational friction.
anchor_type: quote
anchor_text: "internal platform's vetted catalog (Azure App Service / Container Apps)"
evidence_required: false
> quote: "internal platform's vetted catalog (Azure App Service / Container Apps)"

---

### RAISE
kind: question
body: |
  The brief's expected output shape requires a "Tier 2 scoring per
  candidate" that includes per-candidate scoring on 2.1, 2.2, 2.3, 2.4,
  but does not specify a scoring method: are these scored on a numeric
  scale (e.g., 1–5), a qualitative tier (Strong/Adequate/Weak), or
  purely comparative rank ordering? Additionally, 2.1 is called "HIGHEST
  WEIGHT" but no explicit weights are given for 2.2, 2.3, 2.4 relative
  to each other.

  Agreeing on a scoring rubric and relative weights (even roughly) before
  the research phase will prevent us from reaching different orderings
  using incomparable methods and then disagreeing about whose ordering
  is correct.
anchor_type: quote
anchor_text: "2.1 (AI-coding-automation fitness) load-bearing in the final ordering"
evidence_required: false
> quote: "2.1 (AI-coding-automation fitness) load-bearing in the final ordering"

---

### RAISE
kind: disagreement
body: |
  The brief's "Known biases" section warns against "TypeScript on both sides"
  and "more training data" arguments, which is appropriate. However, framing
  these as the *only* two named biases creates an implicit asymmetry: it
  suggests TypeScript specifically needs to be guarded against, while other
  candidates get no analogous warning.

  The brief itself names risk shapes for all candidates (JVM cold-start,
  Go ecosystem gaps, Rust velocity, Python/TS type-system depth, C# vendor
  alignment). But the "Known biases" section singles out TypeScript by name.
  This framing may itself introduce a counter-bias against TypeScript — a
  researcher reading the brief is primed to be skeptical of TypeScript in
  ways they won't be primed for other candidates.

  The disagreement: the "Known biases" framing is subtly unfair to
  TypeScript as a candidate and should either be extended to name
  analogous biases for other candidates (e.g., "Go is fast so it must
  be better," "Rust is memory-safe so it's the responsible choice,"
  ".NET is from Microsoft so it must match Azure best") or the section
  should be renamed and reframed as "Observed informal arguments that
  don't map to the criteria" without singling out TypeScript.

  Resolving this one way versus the other changes whether our final
  document's framing section treats TypeScript as a candidate that needs
  special skepticism applied to it vs. a candidate evaluated on equal footing.
anchor_type: quote
anchor_text: "TypeScript on both sides. Because the frontend uses TypeScript"
evidence_required: false
> quote: "TypeScript on both sides. Because the frontend uses TypeScript"

---

### RAISE
kind: disagreement
body: |
  The brief lists Python among the candidates without any Tier 1
  disqualifying flag, but the criteria framework's risk-shape section
  notes "Python or TypeScript carries type-system-depth risk under heavy
  AI-driven refactoring." Given that criterion 2.1 is explicitly marked
  HIGHEST WEIGHT and one of its sub-criteria is "Type-system depth: Rich,
  expressive static typing that catches errors at edit-time," Python's
  optional typing (via mypy/pyright) is architecturally weaker than the
  static typing of Go, Rust, C#, Kotlin, or Java — and substantially
  weaker than TypeScript's structural type system.

  My disagreement: Python should be flagged as a near-elimination candidate
  at the Tier 2 stage rather than being evaluated on equal footing through
  all sub-criteria, because its structural weakness on the HIGHEST WEIGHT
  criterion (2.1 type-system depth) is so significant that it is unlikely
  to overtake stronger candidates regardless of its scores on 2.2–2.4.
  Including Python as a full co-equal candidate through the entire Tier 2
  analysis risks giving it false parity.

  Resolving this one way versus the other changes whether the final
  document eliminates Python early with a brief rationale or scores it
  fully through all four Tier 2 criteria — a material difference in
  document structure and length.
anchor_type: quote
anchor_text: "Python or TypeScript carries type-system-depth risk under heavy AI-driven refactoring"
evidence_required: false
> quote: "Python or TypeScript carries type-system-depth risk under heavy AI-driven refactoring"