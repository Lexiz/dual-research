---
spec: 0118
title: Deep Research consumption & cost tracking — collapsed/unfolded redesign, canonical piece aggregation
label: refactoring
version-bump: MINOR
status: implemented
target-version: 1.3.0
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0118 — Deep Research consumption & cost tracking

## Context

The Consumption tab today (`src/dual_research/ui/static/run-detail.jsx:1252+`) renders per-turn token bars using a coarse 7-key piece vocabulary defined in `src/dual_research/protocol/prompt_pieces.py`: `brief, d1, d2, plan, hist, draft, histp`. The vocabulary predates the Deep Research protocol (spec 0114), the new UI overhaul (spec 0115), and the canonical artifact registry (spec 0117). After those three land:

- The `brief` key conflates system prompt, user prompt, and the new `agreed_interpretation` artifact into a single segment — exactly the granularity we now want to break apart.
- Display names elsewhere in the UI resolve through spec 0117's registry (`Preflight instructions`, `User prompt`, `Agreed interpretation`, `Claude's research plan`, etc.), but the Consumption tab still labels segments with short `brief / d1 / d2` codes.
- The collapsed card UI has two parallel bars (`total in`, `total out`) plus a redundant total-tokens line in the header, making it noisy.
- The unfolded card UI puts numbers on the left and descriptions on the right, which is the opposite of the natural reading direction the rest of the redesigned UI follows.

This spec rebuilds the Consumption tab around three principles:

1. **One total bar in the collapsed view** (with cost + context-window-% at the bar's right edge), replacing the dual-bar layout.
2. **Per-phase canonical aggregation in the unfolded view**, with `user_prompt` always its own row, `system_prompt` always an aggregate row (tooltip-expandable), and a small, opinionated set of additional rows per phase.
3. **Display names from spec 0117's artifact registry everywhere** — including segment labels, row labels, and tooltip detail rows.

Cost attribution stays honest about what the API gives us vs what we estimate (provider APIs return call-level totals, not per-section breakdowns).

## Goals

1. **Collapsed-card redesign**: single total bar, total tokens + cost shown at the bar's right edge, context-window-% in a small bracketed indicator. Remove the `total in` and `total out` separate bars.
2. **Unfolded-card redesign**: total bar on top, divider, then per-canonical-artifact input rows, divider, then output row. Descriptions on left, numeric tokens + cost on right. Cache-reuse stripe stays as a small, subtle overlay.
3. **Per-phase aggregation rules**: define exactly which artifacts appear as separate rows per phase, and which collapse into the `System prompt` aggregate (with tooltip-revealed breakdown).
4. **Canonical piece vocabulary**: update `prompt_pieces.py` to emit keys aligned with spec 0117's artifact registry, replacing the legacy 7-key vocabulary.
5. **Display-name resolution**: all labels (row, segment, tooltip) call `display_name(artifact_id)` from spec 0117's registry. No hardcoded display strings on the Consumption tab.
6. **Cost honesty**: total cost is exact (API-billed); per-piece cost is proportional (heuristic share of billed input). Tooltip language reflects the distinction.

## Non-goals

- New cost-tracking primitives beyond what providers expose. We do not synthesize finer per-message tokenization than the API returns.
- Cross-run cost analytics (per-run, per-day rollups). This spec is per-turn only.
- Replacing the metrics persistence (`metrics.json`) — that's a backend concern out of scope here.
- New animation on the bars.
- Removing the spec-0030 backward-compat path for legacy runs (pre-0114 runs continue to render via legacy keys; see "Legacy compatibility" below).

## Vocabulary alignment

This spec uses spec 0117's canonical artifact IDs everywhere. The piece-key vocabulary in `prompt_pieces.py` is replaced wholesale.

### Old vs new piece keys

| Legacy key (deprecated) | New canonical artifact ID (from spec 0117) |
|---|---|
| `brief` | Split into `system.task.<phase>` + `user_prompt` |
| `d1` | `phase1.claude` |
| `d2` | `phase1.openai` |
| `plan` | `phase2.agreement.plan` |
| `hist` | `prior_turns.phase2` (when used in P2) / `all_p2_turns` (when used in P3) |
| `draft` | `current_draft` (= the latest `phase{3,4}.draft.v<N>` for the round) |
| `histp` | `prior_turns.phase4` |
| — (new) | `phase0.agreement.interpretation` |
| — (new) | `ledger.standing_items` |
| — (new) | `closeout.request` |
| — (new) | `carry_forward.phase2` (when used in P3) |

The new keys ARE the canonical artifact IDs from spec 0117. There's no second naming layer — the event payload's `promptPieces` field maps directly to registry IDs.

## Visual design

### Collapsed card

```
┌──────────────────────────────────────────────────────────────┐
│ [C] Claude                                       (0.7% of 1M)│   ← small font, bracketed, top-right
│                                                              │
│ Total tokens  ████████░░░░░░░░░░░░░░░░░░░░  8.0kt · $0.0556 │   ← one bar; tokens + cost at right edge
└──────────────────────────────────────────────────────────────┘
```

Components:

- **Header row**: provider badge (C orange / G green) + agent name on the left. **No total / cost in the header anymore.** Only the context-window percentage indicator appears on the right, in 11px font, parenthesized, right-aligned with the end of the bar below.
- **Single bar**: labeled "Total tokens" on the left. The bar represents *total tokens* = `input_tokens` + `output_tokens` (billed). Bar fill is proportional to context-window capacity. At the bar's right edge, two numbers separated by `·`:
  - `<total>t` (e.g. `8.0kt`)
  - `<cost>` (e.g. `$0.0556`)
- **Cache-reuse stripe**: when `cache_read_tokens > 0`, the cached portion renders as a 45° striped overlay over the proportion it represents (existing behavior, retained).
- **No "total in" / "total out" bars** on the collapsed card. Those move into the unfolded view.

### Unfolded card

```
┌──────────────────────────────────────────────────────────────┐
│ [C] Claude                                       (0.7% of 1M)│
│                                                              │
│ Total tokens   ████████░░░░░░░░░░░░░░░░░░  8.0kt · $0.0556  │
│ ─────────────────────── divider ─────────────────────────── │
│ User prompt    ████░░░░░░░░░░░░░░░░░░░░░░  3.5kt · $0.0200  │   ← description left, numbers right
│ System prompt  ██░░░░░░░░░░░░░░░░░░░░░░░░  2.0kt · $0.0114  │     (hover → tooltip with breakdown)
│ Claude's research plan █░░░░░░░░░░░░░░░░░  1.5kt · $0.0086  │
│ GPT's research plan    █░░░░░░░░░░░░░░░░░  1.0kt · $0.0057  │
│ ─────────────────────── divider ─────────────────────────── │
│ Output         ░░░░░░░░░░░░░░░░░░░░░░░░░░    980t · $0.0147 │
└──────────────────────────────────────────────────────────────┘
```

Layout rules:

- **Total bar at top** (identical to the collapsed view).
- **Divider** (1px hairline using `--rule` token).
- **Input rows** (per-phase set; see "Per-phase grouping" below). Each row is a 3-column grid:
  - Column 1 (left): description text (registry display name, e.g. "User prompt", "System prompt", "Claude's research plan")
  - Column 2 (middle): proportional bar (scaled against the per-turn denominator, same as the total bar)
  - Column 3 (right): `<tokens>t · $<cost>`
- **Divider** between inputs and output.
- **Output row** (same 3-column grid; label is "Output").
- **Number/description orientation** is flipped compared to today: **description on the left, numbers on the right.**
- **Cache-reuse stripe** in the unfolded view stays small and subtle. The TOTAL bar carries the stripe overlay (same as collapsed). Per-input-row bars do NOT get their own stripes — adding a stripe to every row would clutter the design. The total bar's stripe is enough signal; the unfolded row tooltips spell out the cache split numerically.

### Per-phase grouping rules (NORMATIVE)

| Phase | Input rows shown (in order) | Aggregated into "System prompt" |
|---|---|---|
| **P0 Preflight** | User prompt · System prompt · Output | `system.task.input` · `prior_turns.phase0` · `ledger.standing_items` · `closeout.request` |
| **P1 Research plan** | User prompt · System prompt · Output | `system.task.research_plan` · `phase0.agreement.interpretation` |
| **P2 Negotiate plan** | User prompt · Claude's research plan · GPT's research plan · System prompt · Output | `system.task.plan_negotiation` · `phase0.agreement.interpretation` · `prior_turns.phase2` · `ledger.standing_items` · `closeout.request` |
| **P3 Drafting** | User prompt · Claude's research plan · GPT's research plan · All negotiation turns · System prompt · Output | `system.task.drafting` · `phase0.agreement.interpretation` · `phase2.agreement.plan` · `carry_forward.phase2` |
| **P4 Review draft** | User prompt · Current draft · Prior review turns · System prompt · Output | `system.task.review` · `ledger.standing_items` · `closeout.request` |
| **Finalize** | (no card — Finalize has no LLM call, no token usage to display) | n/a |

Always-separate rows (across every interaction phase):

- `user_prompt` — its own row, every phase. Reason: user-supplied content can be massive (attached documents).
- The `System prompt` aggregate — its own row, every phase. Reason: this is what the orchestrator controls; lumping it visibly clarifies what the user vs system contributes.

Phase-specific separate rows (significant inputs worth surfacing):

- P2/P3: `phase1.claude` and `phase1.openai` — the agents are negotiating over these; they deserve visibility.
- P3: `all_p2_turns` — the cumulative phase 2 conversation can be a substantial fraction of P3's input.
- P4: `current_draft` — the document being reviewed.
- P4: `prior_turns.phase4` — cumulative review history.

### Tooltip on the "System prompt" row

When the user hovers over the System prompt row, a tooltip appears with the breakdown:

```
System prompt · 2.0kt · $0.0114 (proportional)

  Plan-negotiation instructions    420t
  Agreed interpretation            380t
  Prior negotiation turns          750t
  Ledger (standing items)          280t
  Closeout request                 170t
```

Tooltip rules:

- One row per aggregated sub-artifact, labeled with the registry display name.
- Numbers aligned right (monospaced).
- Indented under the System prompt header for clarity.
- "(proportional)" note next to the cost emphasizes that per-piece cost is a proportional estimate, not an exact API-billed number.

### Cache-reuse indicator placement

Today the total bar shows a 45° striped overlay covering `cache_read_tokens` proportion. This is kept exactly as is, in both collapsed and unfolded views, at 0.5 opacity so it stays subtle.

**No per-input-row stripes.** Adding a stripe to each row in the unfolded view would visually fragment the display. The total bar's stripe + the tooltip numerical detail (showing `2.4kt seen · 1.0kt billed`) are sufficient.

The collapsed card's text under the bar surfaces the reuse signal:

```
3.5kt seen · 1.0kt billed (× 3.5 token reuse) · 980t out
```

This stays from spec 0051.

## Backend changes

### Update `src/dual_research/protocol/prompt_pieces.py`

Replace the 7-key legacy vocabulary with the new canonical keys. Each `pieces_for_*` function emits a richer dict aligned with spec 0117's registry.

```python
# NEW vocabulary — keys ARE the canonical artifact IDs from spec 0117

def pieces_for_preflight(*, system_task: str, user_prompt: str,
                         prior_turns: Iterable | None = None,
                         ledger: str | None = None,
                         closeout_request: str | None = None) -> dict[str, int]:
    """Phase 0 — preflight critique."""
    out = {
        "system.task.input":   estimate_tokens(system_task),
        "user_prompt":         estimate_tokens(user_prompt),
    }
    if prior_turns:
        out["prior_turns.phase0"] = estimate_tokens_iter(prior_turns)
    if ledger:
        out["ledger.standing_items"] = estimate_tokens(ledger)
    if closeout_request:
        out["closeout.request"] = estimate_tokens(closeout_request)
    return out

def pieces_for_research_plan(*, system_task: str, user_prompt: str,
                              agreed_interpretation: str) -> dict[str, int]:
    """Phase 1 — research plan."""
    return {
        "system.task.research_plan":       estimate_tokens(system_task),
        "user_prompt":                     estimate_tokens(user_prompt),
        "phase0.agreement.interpretation": estimate_tokens(agreed_interpretation),
    }

def pieces_for_plan_negotiation(*, system_task: str, user_prompt: str,
                                 agreed_interpretation: str,
                                 phase1_claude: str, phase1_openai: str,
                                 prior_turns: Iterable | None = None,
                                 ledger: str | None = None,
                                 closeout_request: str | None = None) -> dict[str, int]:
    """Phase 2 — plan negotiation."""
    out = {
        "system.task.plan_negotiation":    estimate_tokens(system_task),
        "user_prompt":                     estimate_tokens(user_prompt),
        "phase0.agreement.interpretation": estimate_tokens(agreed_interpretation),
        "phase1.claude":                   estimate_tokens(phase1_claude),
        "phase1.openai":                   estimate_tokens(phase1_openai),
    }
    if prior_turns:
        out["prior_turns.phase2"] = estimate_tokens_iter(prior_turns)
    if ledger:
        out["ledger.standing_items"] = estimate_tokens(ledger)
    if closeout_request:
        out["closeout.request"] = estimate_tokens(closeout_request)
    return out

# pieces_for_drafting, pieces_for_review follow the same pattern,
# emitting the registry IDs that match each phase's input set.
```

Each phase orchestrator (`phase0.py` … `phase4.py`) is updated to call the new functions with the new parameter names.

### Aggregator changes (`src/dual_research/ui/aggregator.py`)

The aggregator builds `phaseTokenUsage` from `TurnEnded` events. Its job is unchanged in shape — it just propagates the new key vocabulary through to the frontend. The `promptPieces` dict on each entry now contains canonical artifact IDs as keys.

### Backward compatibility for legacy runs

Pre-spec-0118 runs on disk contain the legacy 7-key piece keys (`brief, d1, d2, hist, plan, draft, histp`). The frontend's `KIND_ORDER` / `KIND_COLORS` mapping retains a legacy code path that handles old keys (mapping each to a sensible display name via a small static map). New runs use new keys directly. The mapping table:

| Legacy key | Legacy display name (fallback) | Maps to (in new model) |
|---|---|---|
| `brief` | "Brief" | (treated as `system + user_prompt` lump; rendered as one segment in legacy mode) |
| `d1` | "Claude's Phase 1 draft" | `phase1.claude` |
| `d2` | "GPT's Phase 1 draft" | `phase1.openai` |
| `plan` | "Agreed plan" | `phase2.agreement.plan` |
| `hist` | "Prior Phase 2 turns" | `prior_turns.phase2` or `all_p2_turns` |
| `draft` | "Current draft" | `current_draft` |
| `histp` | "Prior Phase 4 turns" | `prior_turns.phase4` |

The UI auto-detects which set of keys is present (legacy vs new) and renders accordingly.

## Frontend changes

### `run-detail.jsx` updates

The Consumption tab components (`TokenBar`, `SubInputBar`, `TotalInputBar`, `OutputBar`, `ConsumptionView`, etc.) are updated:

1. **`KIND_ORDER` and `KIND_COLORS`** maps are rebuilt around the new canonical keys. Each entry includes:
   - The canonical key (artifact ID)
   - A color/gradient
   - The display name (resolved from spec 0117 registry, not hardcoded)
2. **Per-phase grouping logic** — a new function `groupPiecesForPhase(piecesRaw, phase)` returns the structured rows for the unfolded view:
   ```js
   {
     user_prompt: { tokens: N, cost: ... },
     phase1_claude: { tokens: ..., cost: ... },  // P2/P3 only
     phase1_openai: { tokens: ..., cost: ... },  // P2/P3 only
     all_p2_turns: { tokens: ..., cost: ... },   // P3 only
     current_draft: { tokens: ..., cost: ... },  // P4 only
     prior_turns_p4: { tokens: ..., cost: ... }, // P4 only
     system_prompt: {
       tokens: N,          // sum of aggregated sub-pieces
       cost: ...,          // proportional cost
       breakdown: [        // for the tooltip
         { id: 'system.task.plan_negotiation', tokens: 420, label: 'Plan-negotiation instructions' },
         { id: 'phase0.agreement.interpretation', tokens: 380, label: 'Agreed interpretation' },
         // ...
       ],
     },
     output: { tokens: N, cost: ... },
   }
   ```
3. **`CollapsedCard` component**: renders the new single-bar layout with the bracketed context-window-% indicator at top-right.
4. **`UnfoldedCard` component**: renders the new 3-column grid (description · bar · numbers) per row, with the System prompt row carrying the tooltip-expandable breakdown.
5. **Labels resolve through `display_name(artifact_id)`** from spec 0117's registry.

### Cost computation

Per-piece cost is computed proportionally:

```js
function pieceCost(pieceTokens, billedInputTokens, totalInputCost) {
  if (billedInputTokens <= 0) return 0;
  return (pieceTokens / billedInputTokens) * totalInputCost;
}
```

For aggregated rows (System prompt), sum the sub-piece tokens, then apply the same formula. The "(proportional)" annotation on the tooltip signals the heuristic.

For the **total bar**, both numbers (tokens, cost) are exact API-billed values.

## Alignment with specs 0114, 0115, 0117

| This spec depends on | Why |
|---|---|
| **0114** | Defines the new phase prompt construction (separate system instructions, agreed_interpretation, ledger, closeout). The new piece keys correspond 1:1 to artifacts that spec 0114 introduces. |
| **0115** | Defines the broader UI overhaul; the Consumption tab redesign in this spec is consistent with 0115's visual conventions (chips, registry-driven names). |
| **0117** | Defines `display_name(artifact_id)`. This spec's row/segment/tooltip labels all resolve through the registry; **this spec adds no new display strings outside the registry**. |

Ordering: this spec can land after 0114 (new prompts) and 0117 (registry). It does not block 0115 — 0115 ships its UI overhaul without touching the Consumption tab in detail, and 0118 picks it up afterward.

## Cost API capability (validation)

Both Anthropic and OpenAI APIs return:

- `input_tokens` (billed input total per call) ✓
- `output_tokens` (billed output total per call) ✓
- `cache_read_tokens` (Anthropic) / `cached_tokens` in `prompt_tokens_details` (OpenAI) — billed at the discounted cache rate ✓
- `cache_write_tokens` (Anthropic only) — billed at the premium write rate ✓

They do NOT return:
- Per-section input tokens (no system/user/messages split)
- Per-attached-document tokens
- Per-message tokens for multi-message conversations

**Implication for this spec**: per-piece breakdown stays heuristic (char ÷ 3.5 estimate, renormalized so pieces sum to billed `input_tokens`). The total cost is exact, the per-piece costs are proportional shares of the exact total. The UI's "(proportional)" annotation on the tooltip and the design language (segment "weights" rather than "exact tokens") communicate this distinction honestly.

**Cache reuse** is fully trackable per the API responses. Cache write tokens are priced at 2× input rate (Anthropic); cache reads at 0.1× input rate (Anthropic). OpenAI's cached input is priced at 0.5× input rate. The existing pricing module (`src/dual_research/agents/pricing.py`) already accounts for this — no changes needed.

## Test plan

- [ ] Unit tests for the new `pieces_for_*` functions in `prompt_pieces.py`: feed sample inputs, assert correct keys + estimated token counts.
- [ ] Unit tests for `groupPiecesForPhase(piecesRaw, phase)` in JS: for each phase, feed a known piece dict, assert the grouped output matches the per-phase table above (correct rows, correct System prompt aggregation, correct breakdown).
- [ ] Snapshot test for the new collapsed card layout (one bar + bracketed indicator). Compare visual rendering against a fixture run's expected output.
- [ ] Snapshot test for the new unfolded card layout per phase (P0, P1, P2, P3, P4). Verify row order, labels (resolved from registry), and number/description orientation.
- [ ] Tooltip test: hover over System prompt row; verify the breakdown lists every aggregated sub-artifact with its registry display name and token count.
- [ ] Cache reuse rendering: feed a turn with `cache_read_tokens > 0`; verify the total bar has the striped overlay; verify no per-input-row stripes appear in the unfolded view; verify the collapsed card's "X seen · Y billed (× N token reuse)" line renders correctly.
- [ ] Legacy compatibility: load a pre-spec-0118 run (legacy 7-key piece vocab) into the new UI; verify the legacy code path renders correctly with the fallback display names from the legacy mapping table.
- [ ] Cost honesty: confirm the total cost shown on the bar matches what `metrics.json` reports; confirm per-piece cost rows show the proportional share with the "(proportional)" annotation on tooltip.
- [ ] Accessibility: keyboard-navigable card unfolding; tooltip on System prompt row reachable via focus.
- [ ] End-to-end: fire a real production run via the `dual-research-run` skill; open the Consumption tab; verify every phase's card uses the new vocabulary and layout.

## Risks

- **Backend orchestrator coordination**: New `pieces_for_*` signatures require coordinated updates across `phase0.py` … `phase4.py`. Mitigation: required parameters raise explicit errors; unit tests assert each phase invokes the function fully.
- **Heuristic drift**: Per-piece estimates can drift from billed totals. Mitigation: "(proportional)" annotation in tooltips + total bar always shows exact cost.
- **Legacy detection edge cases**: If a new run accidentally emits a legacy key, the wrong renderer applies. Mitigation: detection is key-presence check; regression test on both vocab sets.
- **Information density**: Removing total in/total out from the collapsed card might feel like losing data. Mitigation: detail moves to the unfolded view (one click away).

## Open questions (NORMATIVE — verbatim)

- **OQ-1**: Should the bar's right-edge numbers (`8.0kt · $0.0556`) wrap when the card is narrow, or always stay on one line (relying on the bar to shrink)? **Spec's current default: one line, bar shrinks.** If cards on small viewports need different behavior, file a follow-up.
- **OQ-2**: The legacy-mode auto-detection logic only looks at piece keys. If a new run accidentally emits a legacy key, the new renderer might break. Should we add a version field to event payloads to disambiguate? **Spec's current default: no — key-presence detection is enough**, and the regression test catches developer slip-ups.
- **OQ-3**: For P4, the `current_draft` row is the latest revision the round consumed. As the drafter revises mid-phase, `current_draft` advances (v1 → v2 → ... → vN). Should the Consumption row label include the version? **Spec's current default: include the version** (e.g. "Current draft (v3)") for clarity, matching the SVG diagram's "Current draft (latest version)" wording.
- **OQ-4**: Cache reuse is shown on the total bar but not per-input-row. **Spec's current default: keep per-row stripes out of scope for v1.** If a future need surfaces ("which piece is the cached prefix actually attributable to?"), we can add a small reuse glyph per row.
