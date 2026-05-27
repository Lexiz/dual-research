## Stance

This brief asks for a decision-grade recommendation on backend language for a Document Verification Service modular monolith, choosing from seven candidates (Go, Rust, Python, TypeScript/Node.js, C#/.NET, Kotlin, Java) against a tiered criteria framework. The highest-weight criterion is AI-coding-automation fitness (2.1), which must be load-bearing in the final ordering. My posture is to take the criteria hierarchy seriously and resist the two named biases (TypeScript familiarity, training-data prevalence), while also interrogating whether any Tier 1 constraints actually eliminate candidates before Tier 2 scoring begins. I'll raise questions where the brief leaves material gaps that could change the ranking, and flag framing concerns where the criteria as written could be gamed or misapplied.

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

*(None — first round)*

## Ratifying my own items

*(None — first round)*

---

## New items I'm raising

---

### RAISE
kind: question
body: |
  The brief names Tier 1 constraint 1.4 as "Mature MCP server library available (or feasible to implement without significant effort)." The word "feasible" introduces a judgment call that could rescue or sink a candidate depending on how it's applied — Go in particular is flagged in the risk shapes as carrying "ecosystem-gap risk for MCP server libraries." Before Tier 2 scoring, we need an agreed operational definition: does a language pass 1.4 if (a) an official MCP SDK exists for it, (b) a community SDK with active maintenance exists, or (c) the MCP protocol is simple enough that a thin adapter could be written in < N days? The Model Context Protocol is a published spec, so option (c) could in principle apply to all candidates. Getting this wrong would either wrongly eliminate Go/Rust or wrongly pass candidates with genuinely immature tooling. What is the current state of official and community MCP SDKs across all seven candidates?
anchor_type: quote
anchor_text: "Mature MCP server library available (or feasible to implement without significant effort)"
evidence_required: false
> quote: "Mature MCP server library available (or feasible to implement without significant effort)"

---

### RAISE
kind: question
body: |
  Criterion 2.1 (AI-coding-automation fitness) is the highest-weight criterion and is described through five sub-dimensions (type-system depth, convention-over-configuration, test scaffolding/determinism, refactoring safety, codebase comprehensibility for LLMs). The brief does not provide weights among these sub-dimensions, nor does it specify how they aggregate to a single 2.1 score — is it a simple average, a minimum (worst-dimension dominates), or a weighted sum? This matters materially: Python scores poorly on type-system depth but well on convention-over-configuration; TypeScript scores better on types but has real implicit-semantics issues (decorators, meta-programming frameworks); Go scores highest on convention and comprehensibility but has less expressive types. Without an agreed aggregation method, two analysts can rank the same candidates differently on 2.1 and both be internally consistent. Should we agree on an aggregation rule before scoring?
anchor_type: quote
anchor_text: "AI-coding-automation fitness (HIGHEST WEIGHT)"
evidence_required: false
> quote: "AI-coding-automation fitness (HIGHEST WEIGHT)"

---

### RAISE
kind: question
body: |
  The brief states the team will develop "substantially by AI coding agents (Claude Code, GitHub Copilot, future agents on top of capable models)." This framing implies the human engineering team is small or that AI-agent throughput is the primary bottleneck. However, the brief also mentions "Tier 3 — 3.1 Hiring market depth" as a tiebreaker. These two assumptions could conflict: if the system is primarily AI-agent-maintained, hiring depth is near-irrelevant; if there's a meaningful human team, their existing skills and preferences matter more than the brief acknowledges. What is the actual human team composition — are there existing engineers with strong preferences for specific languages that should be treated as a soft constraint? This affects whether 3.1 is truly a distant tiebreaker or whether it should receive more weight.
anchor_type: quote
anchor_text: "developed and maintained substantially by AI coding agents"
evidence_required: false
> quote: "developed and maintained substantially by AI coding agents"

---

### RAISE
kind: question
body: |
  The brief mentions "Azure Postgres Flexible Server, OLTP primary" with "RLS as tenant boundary." RLS (Row-Level Security) implementation requires that the application set a session-level parameter (typically `SET app.current_tenant = X`) before each query, which interacts non-trivially with connection pooling — poolers like PgBouncer in transaction mode strip session state, requiring either session-mode pooling (less efficient) or explicit SET on every connection checkout. This is a real engineering risk that varies by language ecosystem: some ORMs/drivers handle this transparently, others require custom middleware. Has the team assessed whether each candidate language's primary Postgres library supports this pattern cleanly, and does that assessment affect any Tier 1 (1.2) pass/fail decisions?
anchor_type: quote
anchor_text: "RLS as tenant boundary"
evidence_required: false
> quote: "RLS as tenant boundary"

---

### RAISE
kind: disagreement
body: |
  The brief frames criterion 2.1 sub-dimension "Training-data adequacy" as "a floor requirement — every mainstream language clears it" and explicitly warns against using training-data prevalence to order candidates. I agree this prevents TypeScript from winning solely on that basis. However, the brief goes further and says "it does not order candidates above the floor" — implying training-data prevalence has zero ordering power once the floor is cleared. This is too strong. There is a meaningful qualitative difference between: (a) a language that is heavily represented in AI training data *specifically in the patterns most relevant to this stack* (async workers, connection pool middleware, Postgres RLS session management, MCP-style protocol adapters) versus (b) a language that is generally well-represented but where the specific patterns are sparse. The brief's current framing would prevent analysts from distinguishing Go (where idiomatic patterns for this stack are well-represented) from, say, Kotlin (where the relevant patterns may be thinner in agent training sets). The fix is not to promote training-data prevalence to a primary criterion, but to allow it as a *secondary ordering signal within the floor* when the specific patterns diverge significantly between candidates.
anchor_type: quote
anchor_text: "Training-data adequacy. A floor requirement — every mainstream language clears it"
evidence_required: false
> quote: "Training-data adequacy. A floor requirement — every mainstream language clears it"

---

### RAISE
kind: disagreement
body: |
  The brief's risk-shapes section describes Python as carrying "type-system-depth risk under heavy AI-driven refactoring." The brief also states, under 2.1, that "Weak or optional typing imposes a much heavier review burden." Python's typing situation is nuanced: mypy/pyright with modern Python (3.10+) provide structural static typing that is optional but increasingly idiomatic, and major frameworks (FastAPI, SQLModel) are built around Pydantic v2 which provides runtime-enforced schemas. The brief's framing could lead analysts to treat Python as categorically weaker on type-system depth than it actually is in modern practice. I would argue Python should be assessed against its *actual modern typing story* (pyright strict mode, Pydantic v2, typed async patterns) rather than its reputation for optional typing — but the brief as written primes analysts toward the categorical weakness framing. This affects whether Python makes it to Tier 2 competitive scoring or is soft-eliminated early. The disagreement is: should the scoring framework assess Python's type-system depth as of 2025 idiom (pyright strict + Pydantic v2) or as of its historical reputation?
anchor_type: quote
anchor_text: "Python carries type-system-depth risk under heavy AI-driven refactoring"
evidence_required: false
> quote: "Python carries type-system-depth risk under heavy AI-driven refactoring"