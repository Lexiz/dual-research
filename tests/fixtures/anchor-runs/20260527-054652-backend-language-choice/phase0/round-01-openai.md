## Stance

My reading is that this phase is **not** to choose a backend language yet, but to align on how we will interpret the brief, what must be researched, and where the brief leaves ambiguity. [U] The final decision document must be evidence-led, candidate-by-candidate, and must preserve the brief’s weighting: Tier 1 eliminates, Tier 2 orders, and 2.1 AI-coding-automation fitness is especially load-bearing. [U] My posture is to protect the decision from hidden assumptions, especially around internal platform support, MCP maturity, and how to score AI-agent fitness without collapsing into popularity or personal preference. [U]

## Status

STATUS: IN_PROGRESS  
RAISED_THIS_TURN: [Q-internal-platform-catalog, Q-scoring-rubric, Q-company-context, D-mcp-tier1-framing, D-ai-fitness-operationalization]  
ADDRESSED_THIS_TURN: []  
RESOLVED_THIS_TURN: []  
ACKNOWLEDGED_THIS_TURN: []  
WITHDRAWN_THIS_TURN: []  
OPEN_QUESTIONS: 3  
OPEN_DISAGREEMENTS: 2  
ADDRESSED_QUESTIONS: 0  
ADDRESSED_DISAGREEMENTS: 0

## Addressing items raised against me

(none — first round)

## Ratifying my own items

(none — first round)

## New items I'm raising

### RAISE Q-internal-platform-catalog
kind: question
body: |
  The brief makes internal platform support a Tier 1 hard constraint, but the actual vetted catalog is not included. Should the final research treat Azure App Service / Container Apps public runtime support as a proxy for internal catalog support, or should we mark internal-platform pass/fail as "requires company confirmation" unless the brief provides the catalog? This matters because a Tier 1 failure eliminates a candidate, and we should not eliminate based on an internal artifact we cannot see. [U]
anchor_type: quote
anchor_text: Internal platform support.
evidence_required: false
> quote: Internal platform support.

### RAISE Q-scoring-rubric
kind: question
body: |
  The expected output requires Tier 2 scoring on 2.1 through 2.4, but the brief does not define a numeric scale, weights, or aggregation method beyond saying 2.1 is highest weight. Should we create an explicit scoring rubric during research, for example 1–5 per criterion with 2.1 treated as the dominant criterion, or keep the scoring qualitative? This affects whether the final ranking is reproducible or primarily narrative. [U]
anchor_type: quote
anchor_text: Tier 2 scoring per candidate.
evidence_required: false
> quote: Tier 2 scoring per candidate.

### RAISE Q-company-context
kind: question
body: |
  Several criteria depend on company-specific context: recruitment markets, internal platform norms, existing engineering strengths, and support expectations. Should we ignore unavailable company-specific context except where the brief states it, or should we include assumptions and sensitivity analysis? This affects Tier 3 use and any confidence statement about long-term maintainability. [U]
anchor_type: quote
anchor_text: primarily Europe
evidence_required: false
> quote: primarily Europe

### RAISE D-mcp-tier1-framing
kind: disagreement
body: |
  I am uneasy with treating "mature MCP server library" as a strict Tier 1 eliminator unless we interpret the parenthetical "or feasible to implement without significant friction" broadly. MCP is only one external surface, while the core service is a modular monolith with HTTP, workers, Postgres, Blob, Redis, Key Vault, OIDC, and OpenTelemetry. If a candidate has strong Tier 2 fit and can implement MCP over ordinary protocol primitives without material risk, the final document should record a Tier 1 pass-with-risk rather than eliminate it solely for weaker MCP library maturity. Resolving this one way or the other changes whether languages such as Go or C# could remain viable if their MCP ecosystem is less mature than TypeScript/Python. [U]
anchor_type: quote
anchor_text: Mature MCP server SDK available
evidence_required: false
> quote: Mature MCP server SDK available

### RAISE D-ai-fitness-operationalization
kind: disagreement
body: |
  The brief rightly says training-data prevalence should not order candidates above the floor, but 2.1 still needs a concrete operational interpretation or it risks becoming subjective. I think the final document should decompose 2.1 into observable subclaims — static typing strength, idiom uniformity, test/refactor tooling, explicitness, and agent failure modes — rather than giving each language a vague "AI-friendly" score. Resolving this changes the final document by making the highest-weight criterion auditable instead of impressionistic. [U]
anchor_type: quote
anchor_text: AI-coding-automation fitness
evidence_required: false
> quote: AI-coding-automation fitness