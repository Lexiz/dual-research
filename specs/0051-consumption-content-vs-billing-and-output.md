---
spec: 0051
title: Consumption tab — content-vs-billing split + output bar + cross-turn lineage
label: new-feature
version-bump: MINOR
status: proposed
target-version: 0.49.0
created: 2026-05-17
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0051 — Consumption tab: content-vs-billing split + output bar + cross-turn lineage

## Context

The 0.47.1 hotfix (PR [#52](https://github.com/Lexiz/dual-research/pull/52),
commit `4068351`) fixed the Consumption tab so Claude's "what the model saw"
numbers include cached tokens (`in + cache_read + cache_write`). Before the
fix, `Claude P0 = 400t` vs `GPT P0 = 59.6kt` made it look like the brief
wasn't reaching Claude. After the fix the two preflight bars sit at 71kt vs
64kt — close enough that the "same content, both agents" story is visible.

That fix surfaced two new questions which this spec resolves.

### Question 1 — Why does Claude's "Brief" sub-bar stay 3–4× GPT's in P1 and P2?

Cross-checked against the Partner Vetting — Architecture Proposal (Proposal 2)
run (live on prod after the hotfix):

| Phase | Searches | Claude "Brief" | GPT "Brief" | Predicted (~60kt × N reads + write) |
| --- | --- | --- | --- | --- |
| P0 Preflight | 0 | 71.0kt | 63.8kt | ~60kt — ✓ |
| P1 Research | 6 | 411.9kt | 92.2kt | 60kt + (6 × ~60kt) = ~420kt — ✓ |
| P2 R1 | 4 | 268.0kt | 86.6kt | brief + drafts + (4 × ~70kt) — ✓ |
| P2 R2 | 2 | 157.4kt | 80.1kt | brief + drafts + history + (2 × ~50kt) — ✓ |

The Anthropic Messages API runs a **multi-turn internal loop** when web
search is enabled (think → search → results → think → … → final). The final
response's `usage.cache_read_input_tokens` is the **sum across every internal
turn**. With prompt caching, the cached prefix (brief + drafts + plan) is
re-read on every internal turn — 6 searches ≈ 7 cache reads × ~60kt prefix =
~420kt of cache_read. OpenAI's Responses API tool-call loop bills cache
differently (`input_tokens_details.cached_tokens` doesn't multiply the same
way per internal turn), so GPT's "Brief" bar stays near the brief's actual
size.

**The content is identical — both agents see the same brief.** What differs
is per-provider billing semantics for cache reuse inside a single API call.
The hotfix made the asymmetry visible (which is honest); this spec makes it
**legible** (which is the missing step).

### Question 2 — Are output tokens visualised?

Partially.

- **Visible today:** card headline numbers (`Claude 411.9kt in · 7.2kt
  out`), the dim output tail in the collapsed-row segmented bar, output is
  fully accounted for in the per-turn `cost` field (output is priced at ~5×
  input on most models — not negligible).
- **Not visible today:** the expanded
  [`ConsumptionCard`](../src/dual_research/ui/static/run-detail.jsx)
  (line 1367) shows a "total input" bar + sub-bars for input pieces, but **no
  output bar**. Output is "off the visual scale" of the breakdown panel.

Partner Vetting — Architecture Proposal 2 total cost: $9.86. Output tokens
are a meaningful fraction of that. Hiding them visually under-represents one
of the two cost drivers.

### Question 3 — Outputs should be **named** so you can trace them as inputs to later turns

The protocol already has a vocabulary for input pieces (the `Tk` palette
from [`how-it-works.jsx`](../src/dual_research/ui/static/how-it-works.jsx)
mirrored by `KIND_COLORS` and `KIND_ORDER` in
[`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx)):

| Kind | Content |
| --- | --- |
| `brief` | the research brief |
| `d1` | Claude's Phase 1 draft |
| `d2` | GPT's Phase 1 draft |
| `plan` | the AGREED_PLAN block carried into Phase 3 |
| `hist` | accumulated Phase 2 negotiation turns |
| `draft` | the converged draft in Phase 4 |
| `histp` | accumulated Phase 4 review turns |

Each turn's **output** lands in exactly one of these slots in some later
turn's input. The mapping:

| Turn | Output slot in subsequent turns' inputs |
| --- | --- |
| P0 Claude/GPT | (no slot — preflight critique consumed by orchestrator for go/no-go) |
| P1 Claude | `d1` (read by P2 R1+ and P3) |
| P1 GPT | `d2` (read by P2 R1+ and P3) |
| P2 Rn turn | part of `hist` for P2 R(n+1)+ and `hist` for P3 |
| P3 (drafter) | `draft` (read by P4 R1+) |
| P4 Rn turn | part of `histp` for P4 R(n+1)+ |

**The visualisation should make this lineage trivially traceable.** When you
look at a P2 R2 card and see `d1: 19.0kt` in the input breakdown, you should
be able to scroll up to the P1 Claude card and see its output labelled `→
d1` at the same size, in the same colour. The bar on top of the next round
IS the same bar from the bottom of the previous round. Conservation of
artifacts becomes visible.

## Design decisions

### Bucket A — Content-vs-billing split for input (resolves Q1)

| #   | Decision | One-liner |
| --- | --- | --- |
| A1  | **Two parallel numbers per turn, not one.** Card headline reads `Claude 71kt seen · 411kt billed (× 6 cache reuse)` for high-reuse turns; collapses to one number when `cache_read == 0`. | Honest about the content vs. cost gap; cost reconciliation still ties to `billed`. |
| A2  | **Pieces breakdown anchored to content size (raw `prompt_pieces`), not billed total.** The "User prompt: Brief" sub-bar shows ~60kt for both providers in P1, matching reality. | The breakdown answers "what did the model see"; cost answers "what did we pay". They are different questions and should look different. |
| A3  | **A small `× N reused` chip on the total bar** when `cache_read > prefix_size` (the prefix was re-read at least once). Chip shows the multiplier; tooltip explains "Anthropic's web-search loop re-reads the cached prefix per internal turn." | Makes the amplification visible without polluting the content bars. |
| A4  | **Drop the renormalisation step that scales pieces up to match `tokensIn`** ([`run-detail.jsx:1389-1399`](../src/dual_research/ui/static/run-detail.jsx) and similar block in `TokenBar` around 1710). Pieces sum to their raw heuristic estimate (char ÷ 3.5); the difference between piece-sum and total-billed becomes the visible "reuse" segment on the total bar. | Today the renormaliser inflates the brief sub-bar to absorb cache reads, which is what made the bar look wrong. |

### Bucket B — Output bar + naming (resolves Q2 + Q3)

| #   | Decision | One-liner |
| --- | --- | --- |
| B1  | **Add a "total output" bar to the expanded `ConsumptionCard`,** sized on the same shared `scale` as the input bar. Position: directly below the input panel, with a thin dashed divider. New `OutputBar` component mirrors the existing `SubInputBar` shape. | One glance shows input vs. output at the same scale, including the relative cost. |
| B2  | **Label the output bar with its protocol slot.** P1 Claude card → `→ d1 · Claude's Phase 1 draft`. P2 R1 Claude card → `→ hist contribution · Claude R1 turn`. P3 drafter → `→ draft`. P0 critique → `→ preflight critique (consumed by orchestrator; not an input slot)`. | Makes lineage visible. |
| B3  | **Colour the output bar in the destination kind's colour** (reuse `SUBINPUT_COLORS[k]` already used for input pieces). So the `→ d1` output bar on P1 Claude uses the same ochre as the `d1` input chip on P2 R1+. Visual continuity = visible lineage. | A user can scroll-trace an artifact through the run by colour alone. |
| B4  | **Output cost is surfaced on the card alongside input cost.** Today `Tokens: $0.7143 · Web search: $0.0600` is the breakdown — extend to `Input: $A · Output: $B · Web search: $C` (when output is non-zero, which is always except for silent-lane turns). | Output is the bigger per-token cost driver; hiding it makes the total feel mysterious. |
| B5  | **Tooltip on the output bar shows the per-MTok rate and dollar amount** for that turn's output, plus the model_id. | The "why is Claude expensive" question gets a direct answer. |

### Bucket C — Cross-turn lineage (extends B2, nice-to-have)

| #   | Decision | One-liner |
| --- | --- | --- |
| C1  | **Hover on an input piece highlights the originating output bar.** Hover on `d1` in the P2 R1 input → the P1 Claude output bar pulses / highlights. Click optionally scrolls to it. | Makes the conservation visible interactively. |
| C2  | **Hover on an output bar highlights all downstream input pieces it feeds.** Hover on P1 Claude's `→ d1` → every later card's `d1` segment highlights. | Reverse direction of C1. |
| C3  | C1/C2 ship together if cheap; can defer to a follow-up if implementation grows. B1–B4 are load-bearing for this spec; C1–C2 are sliceable. | Keeps the spec sliceable. |

## Slot-identity source

The frontend already has enough information to compute the output slot
without a wire change:

```
outputSlotFor(phase, round, agent, drafter):
  phase === 0 → null
  phase === 1 && agent === 'claude' → 'd1'
  phase === 1 && agent === 'gpt'    → 'd2'
  phase === 2                       → 'hist'   // every P2 round contributes
  phase === 3 && agent === drafter  → 'draft'  // the drafter's output; the other agent is silent
  phase === 4                       → 'histp'  // every P4 round contributes
```

This lives in `run-detail.jsx` as a pure helper. If a future surface needs
the same mapping server-side (e.g., transcript replay, search indexing), a
follow-up can lift it into `protocol/prompt_pieces.py` and stamp the slot on
`TurnTokenUsage`. Not required for this spec.

## Files touched

- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx)
  — primary: `ConsumptionCard` (line 1367), `TokenBar` (line ~1700),
  `computeConsumptionScale` (line ~985), `SubInputBar`, new `OutputBar`
  component, new `outputSlotFor` helper, new `ReuseChip` component (or extend
  an existing chip), renormalisation logic in `ConsumptionCard` and
  `TokenBar` either removed (A4) or restructured (kept for visual segment
  proportions but the bar total comes from raw piece-sum, not billed total).
  Tooltip strings on the headline cluster + on the segmented bar updated to
  match the new content-vs-billing semantics.
- [`pyproject.toml`](../pyproject.toml) +
  [`src/dual_research/__init__.py`](../src/dual_research/__init__.py) +
  [`CHANGELOG.md`](../CHANGELOG.md) — 0.48.0 → 0.49.0.

**No changes to:**

- [`src/dual_research/agents/anthropic_agent.py`](../src/dual_research/agents/anthropic_agent.py)
  / [`openai_agent.py`](../src/dual_research/agents/openai_agent.py) — the
  asymmetry is downstream of the API response; agent code is correct.
- [`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py)
  — already stores `cache_read` / `cache_write` / output tokens on
  `TurnTokenUsage`; the UI just doesn't render them all yet.
- [`src/dual_research/agents/pricing.py`](../src/dual_research/agents/pricing.py)
  — output cost is already computed correctly; this spec just exposes it.
- [`src/dual_research/protocol/prompt_pieces.py`](../src/dual_research/protocol/prompt_pieces.py)
  — slot identity is computed frontend-side (see § Slot-identity source).
- `ReconcileChip` / `ProviderBilledLine` / Critique panel / Summary tab —
  out of scope.

## Out of scope

- **Changing how Anthropic bills cache reads.** Provider-side semantics are
  what they are; this spec is about display.
- **Reducing the number of internal cache reads.** That would mean changing
  how the orchestrator structures prompts to reduce tool-loop turns —
  separate engineering question, not worth chasing for a one-shot research
  orchestrator.
- **Wire-level slot identity on `TurnTokenUsage`.** Frontend helper is
  enough for this spec; lift to backend in a follow-up if a second surface
  needs it.
- **Backend cost reconciliation against output tokens.** Spec 0048 covers
  this end-to-end; this spec doesn't touch it.
- **C1/C2 may slip to a follow-up spec** if implementation work on B1–B4 +
  A1–A4 already grows large. Document the cut in the PR description if so.

## Open questions to resolve during implementation

1. **A1 headline format.** Three candidates:
   - `71kt seen · 411kt billed (× 6 reuse)` — terse, three facts inline.
   - `71kt input · 411kt with cache reuse` — friendlier; "with" cues that the second number is a superset.
   - Two stacked rows — more visual weight, may be too heavy for the existing card density.

   Default: option 1. Revisit during preview-verify on a representative run.

2. **A3 chip styling.** Existing chip patterns in the codebase: `RepairChip`
   (warn tinted), `ReconcileChip` (status-coloured). The reuse chip is
   informational not warning, so a neutral fg-3 tone fits. Confirm against
   the spec-0050 design tokens (`--info-bg` may be appropriate).

3. **A4 renormalisation removal — collapsed-row segmented bar.** The
   `TokenBar` (collapsed view) also renormalises pieces against
   `effectiveTokensIn`. If we strip renormalisation there too, the segmented
   bar's per-kind colour segments will sum to less than the total bar
   width when cache_read is high. Solution: render the "reuse" overlay as a
   striped fill in the remaining width of the collapsed bar so the bar still
   fills end-to-end but the striped portion communicates "cache reuse, same
   content."

4. **B2 phrasing for P0.** P0's preflight critique isn't an input slot in
   any later turn (the orchestrator reads it for go/no-go but never inlines
   it). Phrasing options: `→ preflight critique` (terse, accurate), `→ go/no-go
   signal` (semantic, hints at protocol role). Default: option 1.

5. **C1/C2 implementation.** Hover/highlight across rows in a long
   Consumption tab needs a shared highlight state. Choices: lift state to
   `ConsumptionView`; CSS-only via `data-slot` attributes + `:has` selectors
   (modern browsers only). Verify CSS-only approach works in Safari 17+; if
   not, lift state.

## Test plan

- [ ] `uv run pytest tests/ -q` — baseline green. No Python changes
  expected; only run-detail.jsx + version files.
- [ ] Manual preview-verify on `localhost:6173` (or 6174 if multiple
  worktrees running):
  - [ ] Partner Vetting — Architecture Proposal (Proposal 2) run,
    Consumption tab.
  - [ ] P1 Research / Claude card: "Brief" sub-bar shows ~60kt (down from
    411.9kt), `× 6 reuse` chip appears on the total bar.
  - [ ] P0 Preflight / Claude card: still shows ~71kt; no reuse chip
    (cache_read == 0).
  - [ ] Output bar present on every card (except silent lanes); labelled `→
    d1 / d2 / hist / draft / histp` per the protocol map; P0 cards labelled
    `→ preflight critique`.
  - [ ] Output bar colour matches the same kind's colour in later turns'
    input pieces (e.g., P1 Claude's `→ d1` bar same ochre as P2 R1 Claude's
    `d1` input segment).
  - [ ] Card cost cluster reads `Input: $A · Output: $B · Web search: $C ·
    Total: $T`. Sum invariant: `A + B + C == T`.
  - [ ] Tooltip on output bar shows model's output $/MTok rate + dollar
    amount.
  - [ ] If C1/C2 ship: hover on a `d1` input piece highlights the
    originating P1 Claude output bar (and vice versa from output → all
    downstream `d1` segments).
- [ ] **Cross-check conservation of artifacts on at least one run:**
  P1 Claude output bar size === P2 R1 `d1` input piece size === P2 R2 `d1`
  input piece size === P3 `d1` input piece size. Exact numerical match (the
  pieces estimator is deterministic — char ÷ 3.5 of the same string).
- [ ] Theme toggle still works in both light and dark mode (spec 0050
  tokens cascade through the new bar + chip).
- [ ] Reduced-motion contract honoured (no animated reuse chip, no
  highlight animations under `prefers-reduced-motion: reduce`).
- [ ] Pre-0030 transcripts (no `prompt_pieces` on `TurnTokenUsage`) render
  gracefully — total input bar + output bar still draw, sub-bar breakdown
  simply doesn't render. Match existing fallback behaviour.

## Coordination notes

- Spec 0050 (design-system foundation) merged as commit `6a047a1` / PR
  [#53](https://github.com/Lexiz/dual-research/pull/53). This spec builds on
  the new token palette; no token references introduced here that don't
  already exist in `tokens.css`.
- The 0.47.1 hotfix (`effectiveTokensIn` helper at
  [run-detail.jsx:957](../src/dual_research/ui/static/run-detail.jsx)) is
  the foundation A4 builds on — A4 either keeps the helper but stops
  renormalising pieces against it, or replaces `effectiveTokensIn` with a
  per-kind decomposition (`freshIn + cacheRead + cacheWrite` summed across
  pieces). Decide during implementation.
- CI tests workflow currently red on main due to four tests in
  [`tests/ui/test_aggregator_ledger.py`](../tests/ui/test_aggregator_ledger.py)
  that load a gitignored runs fixture — see branch
  `fix/ci-aggregator-ledger-fixture` (in flight at the time of writing).
  Spec 0051 doesn't depend on that fix landing first, but the test plan's
  baseline green will be cleaner once it's merged.
