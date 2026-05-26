## Stance

The brief asks for a decision-grade recommendation on which backend language (from seven candidates) the Document Verification Service should use for its server-side modular monolith. The task is fundamentally an evidence-gathering and structured reasoning exercise: confirm each candidate's Tier 1 status, score Tier 2 criteria (especially 2.1 AI-coding-automation fitness, which is explicitly the highest-weight criterion), and produce a ranked output with flip criteria and stated confidence. My posture is to take the criteria hierarchy seriously as written — not to let the named biases (TypeScript familiarity, training-data prevalence) substitute for rigorous Tier 2 analysis — and to push hard on 2.1 since it is load-bearing for the final ordering.

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
  The brief states the service will be "developed and maintained substantially by AI coding agents
  (Claude Code, GitHub Copilot, future agents on top of capable models)." It does not state the
  *ratio* of AI-to-human coding effort, nor the level of human oversight on AI-generated changes
  (e.g., every PR reviewed by a senior engineer vs. near-autonomous merge). This matters for
  scoring 2.1: if a human expert reviews every AI-generated commit, the review burden and
  refactoring-safety concerns are partially mitigated; if the loop is mostly autonomous, they
  become the dominant risk. The score for Python and TypeScript on "type-system depth" changes
  meaningfully depending on which regime applies.

  How autonomous is the AI coding workflow expected to be? Is there a human-in-the-loop for
  every merge, or is the expectation closer to continuous autonomous iteration?
anchor_type: quote
anchor_text: "developed and maintained substantially by AI coding agents"
evidence_required: false
> quote: "developed and maintained substantially by AI coding agents"

---

### RAISE
kind: question
body: |
  The brief lists four bounded contexts and four worker processes. The MCP server is called out
  as the "external programmatic surface." It is not specified whether the MCP server must
  implement a particular MCP protocol version (e.g., 2024-11-05, 2025-03-26), and the candidate
  ecosystem support for MCP SDKs varies *sharply* by protocol version — some languages have
  only community implementations covering earlier versions. This materially affects Tier 1.4
  (mature MCP server library). Which MCP spec version must the implementation target?
anchor_type: quote
anchor_text: "External programmatic surface: MCP server"
evidence_required: false
> quote: "External programmatic surface: MCP server"

---

### RAISE
kind: question
body: |
  The brief names Azure Postgres with RLS (Row-Level Security) as the tenant boundary mechanism.
  RLS in Postgres relies on session-local `SET app.tenant_id = ...` or `SET ROLE` patterns that
  must be correctly set per connection/transaction and correctly reset before a connection is
  returned to the pool. This is a non-trivial integration constraint: some language ORM/DB
  layers handle this cleanly, others require manual workarounds or have known bugs with
  PgBouncer-style pooling in transaction mode. Is the expectation that the service will use
  PgBouncer / pgpool in transaction mode, session mode, or direct connections? This affects
  which candidates score best on 1.2 and 2.2.
anchor_type: quote
anchor_text: "Azure Postgres (connection pooling, RLS-aware sessions)"
evidence_required: false
> quote: "Azure Postgres (connection pooling, RLS-aware sessions)"

---

### RAISE
kind: question
body: |
  The brief mentions "GDPR crypto-erasure mechanism" using per-profile envelope keys with AEAD
  and key wrapping (under 2.3 ecosystem maturity). This is a non-standard cryptographic workflow
  that requires fine-grained key management — typically wrapping per-profile DEKs with a KEK
  stored in Azure Key Vault, then encrypting stored document data with the DEK. The correct
  implementation requires low-level AES-GCM or ChaCha20-Poly1305 primitives and secure key
  handling that some language standard libraries or crypto crates handle better than others.
  Is this crypto-erasure mechanism required at launch (v1) or deferred to a later phase?
  If it is v1, it should factor into Tier 1.3 / 2.3 scoring more heavily.
anchor_type: quote
anchor_text: "Cryptographic primitives for per-profile envelope keys (GDPR crypto-erasure mechanism)"
evidence_required: false
> quote: "Cryptographic primitives for per-profile envelope keys (GDPR crypto-erasure mechanism)"

---

### RAISE
kind: disagreement
body: |
  The brief frames "convention-over-configuration" as a sub-criterion of 2.1 AI-coding fitness,
  with higher scores for "one obvious way to do it" languages. This framing disadvantages
  TypeScript (multiple equivalent patterns for async, DI, validation, ORM) and Go (sparse but
  opinionated) differently from how it should. More critically, it implicitly advantages C# and
  Java — both of which have very strong "one canonical way" traditions (ASP.NET conventions,
  Spring Boot auto-configuration) — but those conventions are *framework-specific* rather than
  language-level, and AI agents must learn them per-framework, not per-language.

  The disagreement: "convention-over-configuration" as written could be misread to favor
  framework-heavy languages (Java/Spring, C#/ASP.NET) over languages where the *language itself*
  is explicit and convention-light (Go). The final document should clarify that this sub-criterion
  measures *language + de-facto ecosystem* conventions, not framework verbosity, and that
  explicitness (Go, C#) is not the same as "no obvious way" (TypeScript with 4 competing DI
  frameworks). If this is not clarified, the scoring could systematically misrank Go vs.
  Java/Kotlin on 2.1.
anchor_type: quote
anchor_text: "Convention-over-configuration. Idiomatic patterns that are widely shared across the ecosystem"
evidence_required: false
> quote: "Convention-over-configuration. Idiomatic patterns that are widely shared across the ecosystem"

---

### RAISE
kind: disagreement
body: |
  The brief places "Training-data adequacy" as a sub-criterion of 2.1 but explicitly instructs
  that it must not become a "more training data = better choice" argument, calling it only a
  "floor requirement." However, in practice, training-data *quality* (not just quantity) for
  AI coding agents differs meaningfully across candidates: Go and Rust have a higher ratio of
  high-quality, type-safe, idiomatic examples in open-source training corpora compared to
  Python (which has large volumes of low-quality, untyped legacy code) and TypeScript (which
  has both typed and untyped JavaScript conflated). Dismissing this entirely as "every mainstream
  language clears the floor" may lead to under-weighting a real differentiation at Tier 2.1.

  The disagreement: training-data *quality and idiomaticity* (not raw quantity) is a legitimate
  differentiator above the floor, and the analysis should treat it as such — while still not
  using raw training-data volume as a proxy for overall fitness. The final document should
  either include training-data quality as a named sub-factor in 2.1 or explicitly justify why
  it is excluded.
anchor_type: quote
anchor_text: "Training-data adequacy. A floor requirement — every mainstream language clears it."
evidence_required: false
> quote: "Training-data adequacy. A floor requirement — every mainstream language clears it."

---

### RAISE
kind: disagreement
body: |
  The "Risk shapes by candidate" section characterizes Rust as carrying "development-velocity-vs-
  iteration-speed risk for AI agents (compile times, lifetime errors)." This framing conflates
  two distinct risks: (a) compile time (a Tier 3.2 build-speed concern) and (b) the borrow
  checker / lifetime system generating AI-agent errors that require human intervention to resolve.
  These have different material weights: compile time is a minor friction; borrow-checker
  correction loops are a fundamental Tier 2.1 concern. By lumping them, the brief under-states
  Rust's Tier 2.1 AI-fitness risk and may cause the final analysis to under-score this risk
  relative to, say, Python's type-system risk.

  The disagreement: the final document must treat Rust's borrow-checker/lifetime complexity
  as a distinct, first-class Tier 2.1 AI-coding-fitness concern (not bundled with compile speed),
  and score it accordingly. If Rust's borrow-checker is not separately scored under 2.1, the
  analysis is internally inconsistent with how it treats Python's typing weaknesses.
anchor_type: quote
anchor_text: "Rust carries development-velocity-vs-iteration-speed risk for AI agents (compile times, lifetime errors)"
evidence_required: false
> quote: "Rust carries development-velocity-vs-iteration-speed risk for AI agents (compile times, lifetime errors)"

---

## Status

STATUS: IN_PROGRESS
RAISED_THIS_TURN: [Q-input-c-01, Q-input-c-02, Q-input-c-03, Q-input-c-04, D-input-c-01, D-input-c-02, D-input-c-03]
ADDRESSED_THIS_TURN: []
RESOLVED_THIS_TURN: []
ACKNOWLEDGED_THIS_TURN: []
WITHDRAWN_THIS_TURN: []
OPEN_QUESTIONS: 4
OPEN_DISAGREEMENTS: 3
ADDRESSED_QUESTIONS: 0
ADDRESSED_DISAGREEMENTS: 0