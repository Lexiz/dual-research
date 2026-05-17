# Follow-up to 0.47.1 hotfix — Consumption tab: content-vs-billing split + output visibility

**Status:** Draft. Not yet numbered. Promote to `specs/00NN-*.md` when ready to pick up.
**Target version:** PATCH or MINOR (PATCH if the change is purely visual; MINOR if any new wire fields are added on `TurnTokenUsage`).
**Coordination:** Land **after** spec 0050 (design-system foundation) merges — both touch `run-detail.jsx` in the Consumption-tab region. Spec 0050's edits are emoji-to-MDI substitutions; this spec's edits are bar-rendering math + new output bar. Disjoint in intent but adjacent in the file.
**Origin:** Conversation 2026-05-17 after the 0.47.1 hotfix landed. Two open questions surfaced that the hotfix didn't address. See § Context.

---

## Context

The 0.47.1 hotfix (PR [#52](https://github.com/Lexiz/dual-research/pull/52), commit `4068351`) fixed the Consumption tab so that Claude's "what the model saw" numbers include cached tokens (`in + cache_read + cache_write`). Before the fix, `Claude P0 = 400t` vs `GPT P0 = 59.6kt` looked like the brief wasn't reaching Claude. After the fix the two preflight bars sit at 71kt vs 64kt — close enough that the "same content, both agents" story is visible.

But the fix surfaced two new questions:

### Question 1 — Why is Claude's "Brief" bar 3–4× GPT's in P1 and P2?

Cross-checked against the Partner Vetting — Architecture Proposal (Proposal 2) run:

| Phase | Searches | Claude "Brief" | GPT "Brief" | Predicted (~60kt × N reads + write) |
| --- | --- | --- | --- | --- |
| P0 Preflight | 0 | 71.0kt | 63.8kt | ~60kt — ✓ |
| P1 Research | 6 | 411.9kt | 92.2kt | 60kt + (6 × ~60kt) = ~420kt — ✓ |
| P2 R1 | 4 | 268.0kt | 86.6kt | brief + drafts + (4 × ~70kt) — ✓ |
| P2 R2 | 2 | 157.4kt | 80.1kt | brief + drafts + history + (2 × ~50kt) — ✓ |

The Anthropic Messages API runs a **multi-turn internal loop** when web search is enabled (think → search → results → think → … → final). The final response's `usage.cache_read_input_tokens` is the **sum across every internal turn**. With prompt caching, the cached prefix (the brief + drafts + plan) is re-read on every internal turn. So 6 searches = ~7 cache reads of the ~60kt prefix = ~420kt of cache_read.

OpenAI's Responses API tool-call loop bills cache differently — `input_tokens_details.cached_tokens` doesn't multiply the same way per internal turn, so GPT's "Brief" bar stays near the brief's actual size.

**The content is identical — both agents see the same brief.** What differs is the per-provider billing semantics for cache reuse inside a single API call. The 0.47.1 fix made this asymmetry visible (which is honest); the spec needs to make it **legible** (which is the missing step).

### Question 2 — Are output tokens visualised?

Partially.

- **Visible:** card headline numbers (`Claude 411.9kt in · 7.2kt out`), the dim output tail in the collapsed-row segmented bar, output is fully accounted for in the per-turn `cost` field (output is priced at ~5× input on most models — not negligible).
- **Not visible:** the expanded `ConsumptionCard` shows a "total input" bar + sub-bars for input pieces, but **no output bar**. Output is "off the visual scale" of the breakdown panel.

User's read on Architecture Proposal 2 totals: `$9.86` total run cost. Output tokens are a meaningful fraction of that. Hiding them visually under-represents one of the two cost drivers.

### Question 3 (user's reframing) — Outputs should be **named** so you can trace them as inputs to later turns

The user's key insight: each turn's output is an artifact that becomes input for a later turn. The protocol already has a vocabulary for input pieces:

| Kind | Content |
| --- | --- |
| `brief` | the research brief |
| `d1` | Claude's Phase 1 draft |
| `d2` | GPT's Phase 1 draft |
| `plan` | the AGREED_PLAN block carried into Phase 3 |
| `hist` | accumulated Phase 2 negotiation turns |
| `draft` | the converged draft in Phase 4 |
| `histp` | accumulated Phase 4 review turns |

Each turn's **output** lands in exactly one of these slots in some later turn's input:

| Turn | Output slot in next turn's input |
| --- | --- |
| P1 Claude | `d1` (read by P2 R1+ and P3) |
| P1 GPT | `d2` (read by P2 R1+ and P3) |
| P2 Rn turn | part of `hist` for P2 R(n+1)+ and `hist` for P3 |
| P3 (drafter) | `draft` (read by P4 R1+) |
| P4 Rn turn | part of `histp` for P4 R(n+1)+ |

**The visualisation should make this lineage trivially traceable.** When you look at a P2 R2 card and see `d1: 19.0kt` in the input breakdown, you should be able to scroll up to the P1 Claude card and see its output labelled `→ d1` at the same size, in the same color. The bar on top of the next round IS the same bar from the bottom of the previous round. Conservation of artifacts becomes visible.

## Design decisions (draft)

These are the candidates to lock in when the spec gets numbered. Open to revision; the user explicitly invited iteration.

### Bucket A — Content-vs-billing split for input (addresses Q1)

| #   | Decision | One-liner |
| --- | --- | --- |
| A1  | **Two parallel numbers per turn, not one.** Headline reads `Claude 71kt seen · 411kt billed (6× cache amplification)` for high-reuse turns; collapses to one number when `cache_read == 0`. | Honest about the content vs. cost gap; cost reconciliation still ties to `billed`. |
| A2  | **Pieces breakdown stays anchored to content size (raw `prompt_pieces`), not billed total.** The "User prompt: Brief" sub-bar shows ~60kt for both providers in P1, matching reality. | The breakdown answers "what did the model see"; cost answers "what did we pay". They're different questions and should look different. |
| A3  | **A small "× N reused" chip on the total bar** when `cache_read > prefix_size` (i.e., the prefix was re-read at least once). Chip shows the multiplier; tooltip explains "Anthropic's web-search loop re-reads the cached prefix per internal turn." | Makes the amplification visible without polluting the content bars. |
| A4  | **Drop the renormalisation step that scales pieces up to match `tokensIn`.** Pieces sum to their raw heuristic estimate (char ÷ 3.5); the difference between piece-sum and total-billed becomes the visible "reuse" segment. | Today the renormaliser inflates the brief sub-bar to absorb cache reads, which is what made the bar look wrong. |

### Bucket B — Output bar + naming (addresses Q2 + Q3)

| #   | Decision | One-liner |
| --- | --- | --- |
| B1  | **Add a "total output" bar to the expanded ConsumptionCard,** sized on the same shared `scale` as the input bar. Position: directly below the input panel, with a thin dashed divider. | One glance shows in vs. out at the same scale, including the relative cost. |
| B2  | **Label the output bar with its protocol slot.** P1 Claude card → output bar reads `→ d1 · Claude's Phase 1 draft`. P2 R1 Claude card → `→ hist contribution · Claude R1 turn`. P3 drafter → `→ draft`. P0 critique → `→ preflight critique (consumed by orchestrator; not an input slot)`. | Makes lineage visible. |
| B3  | **Color the output bar in the destination kind's color** (the same `SUBINPUT_COLORS[k]` palette already used for input pieces). So the `→ d1` bar on P1 Claude uses the same ochre as the `d1` input chip on P2 R1+. Visual continuity = visible lineage. | A user can scroll-trace an artifact through the run by colour alone. |
| B4  | **Output cost is surfaced on the card alongside input cost.** Today `Tokens: $0.7143 · Web search: $0.0600` is the breakdown — extend to `Input: $A · Output: $B · Web search: $C` (when output is non-zero). | Output is the bigger per-token cost driver; hiding it makes the total feel mysterious. |
| B5  | **Tooltip on the output bar shows the per-MTok rate and dollar amount** for that turn's output, plus the model_id. | The "why is Claude expensive" question gets a direct answer. |

### Bucket C — Cross-turn lineage (extends B2)

| #   | Decision | One-liner |
| --- | --- | --- |
| C1  | **Hover on an input piece highlights the originating output bar.** Hover on `d1` in the P2 R1 input → the P1 Claude output bar pulses / highlights. Click optionally scrolls to it. | Makes the conservation visible interactively. |
| C2  | **Hover on an output bar highlights all downstream input pieces it feeds.** Hover on P1 Claude's `→ d1` → every later card's `d1` segment highlights. | Reverse direction of C1. |
| C3  | C1/C2 are nice-to-have. The spec can ship without them if scope creeps; B1–B4 are load-bearing. | Keeps the spec sliceable. |

## Files touched (estimated)

- `src/dual_research/ui/static/run-detail.jsx` — primary: `ConsumptionCard`, `TokenBar`, `computeConsumptionScale`, `SubInputBar`, new `OutputBar` component. Renormalisation step in `ConsumptionCard` and `TokenBar` either removed (A4) or restructured (kept for visual segment proportions but the bar total comes from raw piece-sum, not billed total).
- `src/dual_research/ui/static/run-detail.jsx` — KIND vocabulary or a new OUTPUT_SLOT_LABELS table: `{ p1Claude: 'd1', p1Gpt: 'd2', p2Round: 'hist', p3Drafter: 'draft', p4Round: 'histp', p0: null }`. Pure-frontend lookup; no wire change needed if we can derive the slot from `(phase, round, agent, drafter)`.
- `src/dual_research/protocol/prompt_pieces.py` — possibly extend with `output_slot_for(phase, round, agent, drafter)` if we want the slot identity computed server-side and shipped on `TurnTokenUsage`. Cleaner than recomputing on the frontend, but adds a wire field. Decide during spec write-up.
- `pyproject.toml` + `src/dual_research/__init__.py` + `CHANGELOG.md` — version bump.

**No changes to:**
- Anthropic / OpenAI agent code (the bug is downstream of the API response).
- Aggregator (already stores `cache_read` / `cache_write` / output tokens — fields are present, the UI just doesn't render them all).
- Cost / pricing modules.
- ReconcileChip / ProviderBilledLine.

## Out of scope

- **Changing how Anthropic bills cache reads.** The provider-side semantics are what they are; this spec is about display.
- **Reducing the number of internal cache reads.** That would mean changing how the orchestrator structures prompts to reduce tool-loop turns — separate engineering question, probably not worth chasing for a one-shot research orchestrator.
- **P0 preflight output naming as an input slot.** The preflight critique isn't an input piece in any subsequent turn (the orchestrator consumes it for go/no-go but doesn't inline it). The output bar on P0 cards should be labelled neutrally (`→ preflight critique`) — see B2 for wording.
- **Backend cost reconciliation against output tokens.** Spec 0048 already covers this end-to-end; this spec doesn't touch it.
- **Spec 0050 design-system tokens.** This spec inherits whatever palette spec 0050 lands. No new tokens introduced here unless the output-bar color needs one (probably reuses existing kind palette).

## Test plan (draft)

- [ ] `uv run pytest tests/ -q` — baseline green (725 today). No Python changes unless C-bucket lineage requires a server-side slot lookup; in that case 1–2 new tests around `output_slot_for`.
- [ ] Manual preview-verify on `localhost:6173`:
  - [ ] Partner Vetting — Architecture Proposal (Proposal 2) run, Consumption tab.
  - [ ] P1 Research / Claude card: "Brief" sub-bar shows ~60kt (was 411.9kt), not the cache-amplified number. A `× 6 reused` chip appears on the total bar.
  - [ ] Output bar present on every card; labelled `→ d1 / d2 / hist / draft / histp` per the protocol map.
  - [ ] Output bar color matches the same kind's color in later turns' input pieces.
  - [ ] Card breakdown reads `Input: $A · Output: $B · Web search: $C · Total: $T`.
  - [ ] Tooltip on output bar shows model's output $/MTok rate.
  - [ ] If C1/C2 ship: hover on a `d1` input piece highlights the originating P1 Claude output bar.
- [ ] Cross-check at least one run end-to-end: P1 Claude output bar size === P2 R1 `d1` input piece size === P2 R2 `d1` input piece size === P3 `d1` input piece size. Conservation of artifacts visible by number.

## Open questions for the spec-write-up session

1. **Naming**. "× 6 reused" works for a chip; alternatives: "cache reuse 6×", "billed: 411kt (content: 60kt × 7 reads)". Pick one.
2. **A1 headline format.** `71kt seen · 411kt billed` vs `71kt input (411kt with cache reuse)` vs two stacked numbers. Sketch in the spec.
3. **Color for the "reuse" overlay/chip** — a tertiary accent (not in the agent palette) or a striped fill on the existing total bar? Affects how A1 reads.
4. **Where does the slot identity live** — frontend lookup table or wire field on `TurnTokenUsage`? Frontend is simpler; wire field is more durable and reusable for future surfaces.
5. **C-bucket (interactive lineage)** in this spec or a follow-up? Ship together if cheap; defer if scope grows.

## Promotion checklist (when ready to start the spec)

1. Pick the next spec number (next free after spec 0050 — likely 0051 unless something else got proposed in the meantime).
2. Rename this file → `specs/00NN-consumption-content-vs-billing-and-output.md`.
3. Replace this front-matter with the canonical spec front-matter (`spec: 00NN`, `title:`, `label:`, `version-bump:`, `status: proposed`, `target-version:`, `created:`, `pr: ""`).
4. Resolve the four open questions above; lock decisions in the D-table.
5. Sanity-check spec 0050 has merged (or schedule this for after).
