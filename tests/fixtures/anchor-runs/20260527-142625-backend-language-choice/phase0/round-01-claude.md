## Stance

This brief asks for a structured, evidence-backed decision on which backend language to use for a Document Verification Service modular monolith. My job in this round is to read the brief carefully, interpret the scope and criteria framework correctly, and flag any questions or framings I believe need clarification before research begins — not to jump to a recommendation. I am taking a skeptical posture: the brief is well-structured but contains a few framings that could distort the analysis if left unexamined, and I want to surface those now rather than let them silently shape the final document.

## Status

STATUS: IN_PROGRESS
RAISED_THIS_TURN: [Q-input-a-01, Q-input-a-02, Q-input-a-03, D-input-a-01, D-input-a-02, D-input-a-03]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 3
OPEN_DISAGREEMENTS: 3
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

---

### RAISE
kind: question
body: |
  The brief states the team will be "substantially" developed and maintained by AI coding agents, and criterion 2.1 is labelled HIGHEST WEIGHT. But the brief gives no quantitative weighting scheme across the Tier 2 criteria (2.1–2.4). Should the final document treat 2.1 as lexicographically dominant (i.e., a candidate that wins on 2.1 wins overall unless eliminated by Tier 1), or should 2.1 be strongly weighted but still capable of being overridden by an overwhelming advantage in 2.2–2.4 combined? The answer changes the final ranking if two candidates score closely on 2.1 but diverge sharply on concurrency fit or cold-start latency.
anchor_type: quote
anchor_text: "AI-coding-automation fitness (HIGHEST WEIGHT)"
evidence_required: false
> quote: "AI-coding-automation fitness (HIGHEST WEIGHT)"

---

### RAISE
kind: question
body: |
  The brief lists "AI agents: invoke the Document Verification Service as an MCP skill on behalf of users" as a primary user type, and MCP server library maturity appears in both the hard constraints (1.4) and implicitly in 2.3. The MCP protocol is relatively new (released late 2024). What is the current state of MCP server SDKs across the candidate languages — specifically Go, Rust, and Kotlin — where the brief's own risk notes flag "ecosystem-gap risk"? This is empirically checkable and material to whether those candidates survive Tier 1 at all. We should agree to research this before scoring.
anchor_type: quote
anchor_text: "Mature MCP server library available (or feasible to implement without significant effort)"
evidence_required: false
> quote: "Mature MCP server library available (or feasible to implement without significant effort)"

---

### RAISE
kind: question
body: |
  The brief states the architecture uses "Azure Postgres Flexible Server, OLTP primary" with Row Level Security as the tenant boundary, and notes criterion 1.2 requires "RLS-compatible session management." This is a non-trivial requirement: RLS requires the connection pool to set `SET LOCAL role` or `SET app.current_tenant` within a transaction, which is incompatible with naive connection pooling (e.g., PgBouncer in transaction mode, or an ORM that doesn't support per-request session variable injection). Does the team have a specific pooling topology in mind (e.g., Pgpool, PgBouncer in session mode, application-level pooling only), and does this materially differentiate candidates? Some languages/ORMs handle this much more cleanly than others.
anchor_type: quote
anchor_text: "RLS as tenant boundary"
evidence_required: false
> quote: "RLS as tenant boundary"

---

### RAISE
kind: disagreement
body: |
  The brief frames the risk for Python and TypeScript under 2.1 as "type-system-depth risk under heavy AI-driven refactoring" — treating both languages identically. This is a material oversimplification. TypeScript's type system (structural typing, generics, conditional types, discriminated unions, strict null checking) is substantively richer and more enforceable than Python's type-hint system (which remains optional, partially enforced by mypy/pyright, and undermined by runtime duck-typing and the large body of untyped third-party libraries). Grouping them together in the risk register misrepresents how they compare on criterion 2.1, which lists "Type-system depth" as the first sub-criterion. The final document should score TypeScript meaningfully higher than Python on 2.1 type-system depth, not treat them as co-equal risks.
anchor_type: quote
anchor_text: "Python or TypeScript carries type-system-depth risk under heavy AI-driven refactoring"
evidence_required: false
> quote: "Python or TypeScript carries type-system-depth risk under heavy AI-driven refactoring"

---

### RAISE
kind: disagreement
body: |
  The brief states that "C#/.NET carries over-reliance-on-Microsoft-conventions risk that may not match the internal platform's broader Azure-on-non-Microsoft-stack norms." This risk framing is misleading for a system explicitly deployed on Azure (mandated), using Azure Postgres, Azure Blob, Azure Cache for Redis, Azure Key Vault, and Azure API Management. The internal platform IS a Microsoft stack. The stated risk — that .NET conventions might not match "broader Azure-on-non-Microsoft-stack norms" — is internally inconsistent: if the platform is Azure, .NET's first-class Azure SDK support, Azure Monitor integration, and the fact that Azure's own tooling is .NET-native are advantages, not risks. The final document should not penalize .NET for a "convention mismatch" risk that the described environment does not support.
anchor_type: quote
anchor_text: "C# / .NET carries over-reliance-on-Microsoft-conventions risk"
evidence_required: false
> quote: "C# / .NET carries over-reliance-on-Microsoft-conventions risk"

---

### RAISE
kind: disagreement
body: |
  The brief explicitly names "Performance benchmarks unless load-bearing" as an argument that "should not order candidates above the floor," on the grounds that "document AI calls and Postgres roundtrips dominate latency." However, criterion 2.4 specifically calls out "Memory footprint compatible with Azure Container Apps scaling (small min-replica memory)" and "Acceptable cold-start latency for the API process." These are operational characteristics that differ substantially between JVM languages (Java, Kotlin — known for high baseline heap and slow cold starts), Go/Rust (very low memory/cold-start), and .NET (intermediate). The brief's own risk register flags this for JVM candidates. Treating memory footprint and cold-start latency as "not load-bearing" while simultaneously listing them as explicit 2.4 criteria is contradictory. The final document should evaluate these characteristics as genuine 2.4 differentiators, not wave them away as irrelevant performance benchmarks.
anchor_type: quote
anchor_text: "Performance benchmarks unless load-bearing. The Document Verification Service is not a hot-path latency-sensitive system."
evidence_required: false
> quote: "Performance benchmarks unless load-bearing. The Document Verification Service is not a hot-path latency-sensitive system."

---

## Interpretation

**What the brief is asking for:** A structured, criteria-driven recommendation of a single backend language for a B2B Document Verification Service modular monolith, with explicit Tier 1 pass/fail assessment, Tier 2 scored comparison (with 2.1 AI-coding fitness as highest weight), and a ranked output including flip criteria. The seven candidates are Go, Rust, Python, TypeScript/Node, C#/.NET, Kotlin, and Java.

**My reading of scope:**
- The decision covers all four process types (API, outbox worker, analysis worker, scheduled-task worker) sharing one codebase.
- The output must be decision-grade per the six-bullet contract in the brief: ranked recommendation, confidence level, Tier 1 table, Tier 2 scoring, flip criteria, and any unresolved disagreements surfaced.
- The criteria framework deliberately downweights frontend-alignment, performance (with the tension I flagged above), and team familiarity to prevent known bias patterns from dominating.

**Key research tasks I anticipate:**
1. Verify MCP server SDK maturity across all seven candidates (especially Go, Rust, Kotlin). [Q-input-a-02]
2. Assess current state of OpenTelemetry SDK completeness (traces + metrics + logs with OTLP) across candidates.
3. Assess AI-coding fitness (2.1) using evidence — IDE/LSP tooling quality, type system enforcement, codebase navigability — not just training data prevalence.
4. Assess Container Apps cold-start and memory footprint data for JVM vs. non-JVM candidates. [D-input-a-03]
5. Assess RLS-compatible Postgres pooling library support per candidate. [Q-input-a-03]