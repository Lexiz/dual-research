---
spec: 0042
title: Critique data integrity — parser coverage, badge wiring, modal load paths, count reconciliation
label: bug
version-bump: MINOR
status: merged
target-version: 0.40.0
created: 2026-05-17
pr: "https://github.com/Lexiz/dual-research/pull/43"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0042 — Critique data integrity

## Context

A review pass over the timeline + critique surface surfaced six
data-correctness defects whose common thread is "the UI shows a
number or a section that doesn't match what the underlying transcript
actually contains." None of them are visual polish — each is a real
mismatch between the parsed protocol artefacts and what gets
rendered.

The defects are grouped because they share infrastructure
([`protocol/parse.py::extract_review_items`](../src/dual_research/protocol/parse.py#L481),
[`ui/aggregator.py::_read_phase_review_items`](../src/dual_research/ui/aggregator.py#L1074),
[`ui/static/run-detail.jsx::StatsChips`](../src/dual_research/ui/static/run-detail.jsx#L2165),
[`reviewItemsFor`](../src/dual_research/ui/static/run-detail.jsx#L3201),
[`NegotiateReviewModal`](../src/dual_research/ui/static/run-detail.jsx#L2531),
[`CritiqueExplorer`](../src/dual_research/ui/static/run-detail.jsx#L4161))
and fixing them piecemeal would mean three round-trips through the
same parser/aggregator/wire-format layer.

The visible symptoms on the canonical partner-vetting fixture:

1. **Phase 1 plan-draft cards show `0 questions` and a
   `disagreements` tag.** Both wrong. The Phase 1 draft file
   `phase1/draft-claude.md` actually contains two structured
   sections — `## 4. Claims I Expect the Other Agent Might Dispute`
   (6 items) and `## 5. Open Questions` (5 items) — neither of
   which is parsed by
   [`extract_review_items`](../src/dual_research/protocol/parse.py#L481).
   The parser looks for `## Open questions for <other>` with the
   "for X" suffix that Phase 2 uses; it doesn't recognise the Phase 1
   variants. And Phase 1 never emits anything with the
   `## Substantive disagreements I'm holding` or
   `## Diff vs … Phase 1` headings either — so a `disagreements`
   tag on a Phase 1 card is structurally impossible to be honest.
2. **Phase 2 turn-card badges read a self-reported counter, not
   parsed-item counts.** The `6 questions` chip on Claude turn 1 is
   the value of the agent's own `OPEN_QUESTIONS: 6` machine-readable
   line at the bottom of the turn file. On the partner-vetting run
   this matches reality, but the chip is decoupled from the actual
   items the parser would extract from `## Open questions for X` —
   so a future drift between what the agent self-reports and what
   it actually wrote is invisible. The same disconnect explains why
   no `disagreements` chip appears on Claude turn 1 despite 10 D-N
   items in `## Diff vs openai's Phase 1`: the chip reads
   `BLOCKING_DISAGREEMENTS:` which the agent leaves at 0 in round 1
   (it only counts "blocking" not "differences").
3. **Phase 2 turn full-view right pane reports `No structured
   questions or disagreements were anchored in this turn`.** Even
   when the underlying turn file has 6 questions + 10 differences,
   the side-by-side modal's right pane is empty. The pane reads
   `run.phaseReviewItems[phase2_round1_claude]` via
   [`reviewItemsFor`](../src/dual_research/ui/static/run-detail.jsx#L3201);
   that bucket comes from
   [`_read_phase_review_items`](../src/dual_research/ui/aggregator.py#L1074)
   which calls `resolve_review_items` (= `extract_review_items` +
   anchor resolution). The parser DOES recognise `## Diff vs …
   Phase 1` (line 509) and `## Open questions for …` (line 503), so
   the items should be there. Three candidate root causes to
   investigate: (a) `_read_phase_review_items` filters items with
   `if not items: continue` — if anchor-resolution drops items to
   zero, the bucket key isn't populated; (b) the aggregator
   snapshot is being read from a stale cache on Supabase that
   pre-dates the spec-0041 parser changes; (c) a wire-format
   field-name mismatch between Python `phase_review_items` and the
   camelCased frontend `phaseReviewItems`.
4. **Negotiation full-view markdown renders section headings as
   continuous ordered-list items.** Source: `## 1. Summary`, `## 2.
   My Thesis`, `## 3. Detailed Findings`, `## 4. Claims I Expect…`,
   `## 5. Open Questions`. The user sees claims numbered 5–10 below
   the "4. Claims…" heading — i.e. the rendered ordered list
   continues from where the H2 numbering left off, instead of
   restarting at 1 inside each section. The renderer is
   [`Markdown` in `shared.jsx`](../src/dual_research/ui/static/shared.jsx#L276)
   using `marked@14.1.4` with `{gfm: true, breaks: false}`. Marked
   v14 should treat `## N. Title` as `<h2>` not `<li>`. Probable
   cause: `_extractBackendBlockIds` / `_applyBackendBlockIds`
   leaves residual HTML that breaks marked's heading tokenisation.
   To verify in implementation.
5. **Brief content renders with its first paragraph styled bold.**
   Source: `**Purpose:** This document is a faithful, exhaustive
   capture…`. Only `Purpose:` should be bold; the rest is normal
   prose. The full paragraph rendering bold is a marked / inline-
   strong-tokenisation quirk on this content. Same `Markdown`
   helper as (4).
6. **Phase 4 "View full mode" loads nothing.** The card list on the
   right pane (`Issues raised` etc.) renders fine on the timeline;
   the side-by-side modal opens with an empty left pane (no
   markdown body) and no review items on the right. The modal
   routes to `NegotiateReviewModal` (shared with Phase 2) which
   reads
   [`priorContentPathFor`](../src/dual_research/ui/static/run-detail.jsx#L3189)
   → for Phase 4 returns `run.currentDraftPath || null`. If
   `currentDraftPath` is null (or the aggregator didn't surface
   it), the left pane has nothing to render. Right pane reads
   `phase_review_items[phase4_roundN_agent]` — empty if the parser
   never bucketed the issues/comments/disagreements as
   `kind="issue"` / `"comment"` / `"disagreement"` on the wire.
   Need to trace which path is actually broken on the canonical
   fixture.
7. **`99 introduced` in the Critique header doesn't reconcile with
   `15 open / 21 resolved`.** Confirmed in
   [`run-detail.jsx:4236`](../src/dual_research/ui/static/run-detail.jsx#L4236):
   `totalIntroduced = issues.length + questions.length +
   disagreements.length + comments.length` — a workspace-total
   across ALL phases and ALL kinds. `totalOpen` / `totalResolved`
   at lines 4205-4206 are phase-filtered (only the currently
   selected `Phase 2` or `Phase 4` tab). Two scopes, same header.
   The math can never reconcile; the user reads it as
   "introduced − open − resolved = 63 unaccounted" which is the
   *other phase's* items.

Prior context:
- [Spec 0028](./0028-review-inline-comments.md) — established the
  Phase 4 section taxonomy (`Issue ledger`, `Open questions for X`,
  `Comments on the current draft`).
- [Spec 0034](./0034-critique-navigation.md) — introduced
  `resolve_review_items` (anchor pre-resolution at parse time).
- [Spec 0040](./0040-critique-rework.md) — compact cards, Summary
  tab, click-to-highlight wiring.
- [Spec 0041](./0041-critique-classification-and-resilience.md) —
  split `kind="issue"` / `"comment"` / `"question"`, added
  `Run.issues` / `Run.comments`, fixed Phase 4 question linkage.
- [Handover 2026-05-16](../handoffs/2026-05-16-specs-0038-0041-handover.md)
  notes (item 4 in "Validated but unresolved") the
  Phase 4 sibling-label collapse — orthogonal but in the same
  surface; this spec doesn't touch it.

**Scope note — closure semantics.** This spec fixes how the UI
*displays* taxonomy + counts and extends the parser to cover Phase
1's structured sections. The deeper question of how the system
*enforces* closure across rounds (today: agent self-counter;
target: an orchestrator-maintained cross-round ledger that the
LLM also reads as input, plus a conservative convergence
cross-check) is split into Spec 0043 — Cross-round ledger +
standing-items input + conservative convergence. Spec 0042's
wire-format additions (`Run.claims`, `kind="claim"`,
`current_draft_path`) are the foundation 0043 builds on; 0042
itself does NOT change protocol prompts, orchestrator state, or
convergence logic.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Parser recognises Phase 1 section variants.** | `extract_review_items` adds two new section patterns: `## <N>. Claims I Expect the Other Agent Might Dispute` (extracts items as `kind="claim"`) and `## <N>. Open Questions` (extracts items as `kind="question"`; the leading-numeric prefix is matched optionally so the existing `## Open questions for X` still works). The numeric prefix is captured but discarded — the parser is name-only. |
| D2  | **New `kind="claim"` on the wire.** | Mirrors `disagreement` shape — `id`, `body`, `quote`, `after`, `block_id`. Lives on `ReviewItem` like the other kinds. The frontend gets a new `Run.claims` array populated by `reconstruct_claims(session_dir, phase=1)`. The aggregator no-ops cleanly on transcripts that don't have a `Claims…` section (returns `[]`). |
| D3  | **`_read_phase_review_items` walks Phase 1 draft files too.** | Today the loop is `for phase_n in (2, 4)`. Extend to `(1, 2, 4)` with Phase 1 reading `phase1/draft-<agent>.md` instead of `phase{N}/round-NN-<agent>.md`. The bucket key for Phase 1 becomes `phase1_<agent>` (no round — Phase 1 has exactly one draft per agent). Frontend `reviewItemsFor` updated to drop the round component when `phase === 1`. |
| D4  | **Timeline `StatsChips` reads from parsed-item counts, not from self-reported counters.** | Today `stats.openQuestions` comes from the `OPEN_QUESTIONS:` line of the turn file (`protocol/parse.py:OPEN_QUESTIONS_RE`). After this spec, the badge layer derives counts from `run.questions` / `run.disagreements` / `run.issues` / `run.claims` filtered to the turn's `raised_turn_key`. The self-counter is kept as a sanity-check (logged when mismatched) but is NOT the source of truth for the chip. *Forward-compatibility note: when Spec 0043's cross-round ledger lands, the chip source swaps from `run.<kind>` to `ledger.items_for(turnKey)` — a one-function-call migration.* |
| D5  | **Phase 1 plan-draft cards display `claims` and `questions` chips, never `disagreements`.** | The chip set is per-phase: P0 = none. P1 = `claims` + `questions`. P2 = `questions` + `disagreements` (+ optional `claims` if the parser extends to P2's `Diff vs … Phase 1` section — see D6). P3 = none (silent drafter). P4 = `issues` + `comments` + `disagreements`. P5 = none. The `disagreements` tag never appears on a Phase 1 card; the chip layer enforces this with a per-phase allowlist. |
| D6  | **`## Diff vs … Phase 1` parses as `kind="claim"` for round-1 turns, not `kind="disagreement"`.** | Today line 509-512 of `parse.py` buckets these as `disagreement`. But semantically the round-1 difference inventory enumerates the *contested points* (with each agent's position) — they're claims-being-made, not yet held disagreements. The agent's own "currently held" disagreements appear in `## Substantive disagreements I'm holding` (R≥2). Re-bucketing makes the timeline + critique-pane counts match the agent's mental model: R1 = claims, R≥2 = disagreements that survived. **Net effect on badges**: Claude turn 1 (today: `6 questions · negotiating · r1`) renders as `6 questions · 10 claims · r1`. *Forward-compatibility note: a R1 `claim` may "escalate" in R≥2 when the same D-N ID appears in `## Substantive disagreements I'm holding`. Spec 0043's ledger tracks that transition explicitly; Spec 0042 captures the R1 claim correctly so the ledger has a defensible starting point.* |
| D7  | **Phase 2 turn full-view right pane: aggregator key + frontend key reconciled.** | Audit the path: Python writes `out[f"phase{phase_n}_round{round_n}_{_ui_agent(agent)}"]`. Server camelCases to `phaseReviewItems[…]`. Frontend reads `run.phaseReviewItems[\`phase${phase}_round${item.round}_${item.agent}\`]`. The compound key string passes through unchanged — verify with a unit test that walks a synthetic phase2/round-01-claude.md fixture and asserts the resulting frontend-shaped bucket is non-empty. If `_read_phase_review_items`'s `if not items: continue` is hiding non-empty bucket creation, replace with always-create-on-walk so an empty list is still a valid "we looked and there's nothing" signal. |
| D8  | **Phase 4 `currentDraftPath` always non-null when a converged document exists.** | The aggregator already runs `_find_current_draft_path(session_dir)` in `_read_phase_review_items` (line 1105) but doesn't surface the result on `Run` itself. Add `Run.current_draft_path = _find_current_draft_path(session_dir)` populated in `load_run_snapshot`, camelCased to `currentDraftPath` on the wire. Phase 4 modal's left pane now resolves a path on every run that has reached Phase 3+. Falls back to `phase3/draft-v1.md` server-side if no Phase 4 draft exists yet. |
| D9  | **Marked v14 numbered-heading bug — root-cause fix.** | The likely culprit is `_extractBackendBlockIds` stripping `<!-- block-id: … -->` comments and re-inserting them in a way that interrupts marked's heading tokenizer. The fix is to run `marked.parse` on a STRIPPED source (no backend block-id comments at all) and apply block IDs in a post-pass on the HTML output via `_applyBackendBlockIds`. This path already exists for the ID-application; the bug is that the strip-then-parse path may still leak HTML if the source has both backend IDs AND inline HTML elsewhere. Validate by adding a snapshot test for `## 4. Claims I Expect…` followed by `1. **First claim.**` and asserting the rendered HTML is `<h2>4. Claims I Expect…</h2><ol><li>` not `<ol start="4"><li>` or similar. |
| D10 | **Bold-paragraph rendering bug — investigate marked tokenizer for `**Purpose:**` followed by inline prose.** | Reproduce on the brief content in isolation. If marked is genuinely mis-tokenising, the fix may be a pre-pass that normalises `**Word:**` to `<strong>Word:</strong>` before marked sees it. If it's a CSS issue (no actual `<strong>` wrapping the paragraph, only the inline word, but the `<h2>` heading style is bleeding into the next paragraph), the fix is CSS scoping. **Implementation note**: the root cause will be obvious on inspection of the generated HTML; the decision here is just "this is in scope and gets fixed." |
| D11 | **`totalIntroduced` becomes phase-scoped (matches `open` + `resolved`).** | Replace [line 4236](../src/dual_research/ui/static/run-detail.jsx#L4236)'s global sum with the existing per-phase `introduced` variable from line 4207. Header now reads `Critique · N introduced · X open · Y resolved` where `N = X + Y + (filtered-out-by-kind-toggles)`. Math reconciles cleanly. The header text shifts the count from the "Critique" left label to the right-side number cluster (per user feedback) but the *visual layout* change is deferred to spec 0046; spec 0042 fixes the math and labels in place. |

## Proposed change

### 1. Parser — `src/dual_research/protocol/parse.py`

```python
# extract_review_items() — add two new section recognisers.

# Phase 1 — Claims I Expect the Other Agent Might Dispute.
# Accept an optional leading-numeric prefix ("## 4. Claims I Expect…").
claims_match = re.search(
    r"^##\s+(?:\d+\.\s+)?Claims I Expect the Other Agent Might Dispute\s*$",
    turn_text, re.MULTILINE,
)
if claims_match:
    body = _section_body_at(turn_text, claims_match.end())
    out.extend(_walk_section_items(body, kind="claim"))

# Phase 1 — Open Questions (without "for X" suffix; tolerates leading number).
open_q_p1 = re.search(
    r"^##\s+(?:\d+\.\s+)?Open Questions\s*$",
    turn_text, re.MULTILINE,
)
if open_q_p1 and not open_q_match:  # avoid double-extracting if P2 form present
    body = _section_body_at(turn_text, open_q_p1.end())
    out.extend(_walk_section_items(body, kind="question"))

# D6 — round-1 difference inventory bucketed as claims, not disagreements.
diff_match = re.search(r"^##\s+Diff vs .+?Phase 1\s*$", turn_text, re.MULTILINE)
if diff_match:
    body = _section_body_at(turn_text, diff_match.end())
    out.extend(_walk_section_items(body, kind="claim"))
    # Was: kind="disagreement"
```

Also: `_walk_section_items` already accepts an arbitrary `kind`
string, so the `kind="claim"` calls work without further changes.
The existing `## Substantive disagreements I'm holding` section
remains `kind="disagreement"` (R≥2 only).

### 2. Run model — `src/dual_research/ui/models.py`

```python
@dataclass
class Claim:
    id: str               # stable "C-{agent}-r{round}-{idx}" or "C-p1-{agent}-{idx}"
    phase: int            # 1 or 2 (round-1 difference inventory)
    agent: str            # "claude" | "gpt"
    body: str
    quote: str | None
    after: str | None
    block_id: str | None
    raised_turn_key: str | None   # e.g. "phase1_claude" or "phase2_round1_claude"
    status: str = "open"          # "open" | "resolved" — see reconstructor

@dataclass
class Run:
    # …existing fields…
    claims: list[Claim] = field(default_factory=list)
    current_draft_path: str | None = None   # D8 — surfaces _find_current_draft_path on the wire
```

### 3. Reconstructor — `src/dual_research/ui/claims.py` (new)

```python
def reconstruct_claims(session_dir: Path) -> list[Claim]:
    """Walk Phase 1 draft files + Phase 2 R1 turn files and bucket
    `## Claims I Expect…` (P1) and `## Diff vs … Phase 1` (P2 R1)
    items as Claim objects.

    Status reconstruction:
    - A P1 claim is `open` if the same body-prefix appears in the
      agent's R2+ turn `## Substantive disagreements I'm holding`
      section. Otherwise `resolved` (the other agent either
      addressed it in their R1 draft already, or it was dropped).
    - A P2 R1 difference is `open` if it carries D-N anchor and the
      D-N appears in any later round's `Substantive disagreements`.
      Otherwise `resolved`.
    """
```

### 4. Aggregator — `src/dual_research/ui/aggregator.py`

```python
# load_run_snapshot:
run.claims = reconstruct_claims(session_dir)
run.current_draft_path = _find_current_draft_path(session_dir)

# _read_phase_review_items — extend phase loop:
for phase_n in (1, 2, 4):
    if phase_n == 1:
        # Phase 1 has one draft file per agent, no rounds.
        for agent_be in ("claude", "openai"):
            draft = session_dir / "phase1" / f"draft-{agent_be}.md"
            if not draft.is_file():
                continue
            text = draft.read_text(encoding="utf-8")
            prior_blocks = _resolve_prior_blocks(1, 1, agent_be)  # brief
            items = resolve_review_items(text, prior_blocks)
            key = f"phase1_{_ui_agent(agent_be)}"
            out[key] = [asdict(i) for i in items]  # always create, even if empty
        continue
    # …existing phase 2 / 4 loop, with `if not items: continue` removed…
```

Anchor-resolution for Phase 1 uses the brief as prior content
(claims and Phase-1 questions reference the brief, not the other
agent's draft — that's Phase 2's job).

### 5. Frontend — `src/dual_research/ui/static/run-detail.jsx`

5a. **`reviewItemsFor`** (line 3201) — handle the no-round Phase 1
key shape:

```js
function reviewItemsFor(run, item) {
  const phase = item.statsPhase || 2;
  const key = phase === 1
    ? `phase1_${item.agent}`
    : `phase${phase}_round${item.round}_${item.agent}`;
  const bucket = (run.phaseReviewItems || {})[key];
  return Array.isArray(bucket) ? bucket : [];
}
```

5b. **`priorContentPathFor`** (line 3189) — Phase 1 maps to the
brief:

```js
if (phase === 1) {
  return 'brief.md';   // claims/questions anchor against the brief
}
```

5c. **`StatsChips`** (line 2165) — derive counts from parsed items,
gated by phase allowlist (D5):

```js
function StatsChips({ stats, phase, prevStats, run, turnKey }) {
  // Phase allowlist for chip kinds — D5.
  const ALLOW = {
    0: [],
    1: ['claims', 'questions'],
    2: ['questions', 'disagreements', 'claims'],
    3: [],
    4: ['issues', 'comments', 'disagreements'],
    5: [],
  };
  const allowed = ALLOW[phase] || [];
  const counts = {
    questions:     allowed.includes('questions')     ? (run.questions     || []).filter(q => q.raisedTurnKey === turnKey).length : 0,
    disagreements: allowed.includes('disagreements') ? (run.disagreements || []).filter(d => d.raisedTurnKey === turnKey).length : 0,
    claims:        allowed.includes('claims')        ? (run.claims        || []).filter(c => c.raisedTurnKey === turnKey).length : 0,
    issues:        allowed.includes('issues')        ? (run.issues        || []).filter(i => i.raisedTurnKey === turnKey).length : 0,
    comments:      allowed.includes('comments')      ? (run.comments      || []).filter(c => c.raisedTurnKey === turnKey).length : 0,
  };
  // …render chip-per-kind only when count > 0; status pill unchanged
  // (the "drop negotiating + redesign deltas" rework is spec 0044).
}
```

The `turnKey` plumbing already exists on the artefact item
(`item.turnKey`); pass it through where `StatsChips` is rendered.

5d. **`CritiquePhaseContent` / `CritiqueExplorer`** — `totalIntroduced`
phase-filtered:

```js
// Was (line 4236):
const totalIntroduced = issues.length + questions.length + disagreements.length + comments.length;
// Becomes:
const totalIntroduced = introduced;   // already phase-scoped at line 4207
```

`introduced` is the variable already computed from
`phaseIssues.length + phaseQuestions.length + …` filtered to the
selected phase. Header math now reconciles.

5e. **`NegotiateReviewModal`** — emptied right-pane copy stops
lying:

The current `ReviewKeyboardHint hasItems={false}` message reads:
`No structured questions or disagreements were anchored in this turn`.
After D4/D6/D7 land, this is rarely hit. When it IS hit
(genuinely empty turn — e.g. a malformed file), replace with: `No
structured items in this turn — open the document modal from the
card header to read the full markdown body.`

### 6. Markdown renderer — `src/dual_research/ui/static/shared.jsx`

6a. **Numbered-heading numbering bleed (D9).** Investigate
`_extractBackendBlockIds` + `_applyBackendBlockIds` + `marked.parse`
interaction. Likely fix: ensure the source passed to `marked.parse`
has zero residual HTML (the strip step is complete) and the post-
pass applies IDs without touching the heading/list structure.

If `marked` itself is the problem (e.g. v14 has an issue with
`## N. Title` patterns), add a pre-pass that normalises the number
prefix: `## 4. Claims …` → `## Claims …` (with a CSS counter-reset
on H2 to display the number). Defer the CSS counter solution as a
spec-0046 visual concern; spec 0042 just needs the *content* to
render correctly.

6b. **All-bold first paragraph (D10).** Reproduce on
`**Purpose:** This document is…` in isolation. Generate the marked
HTML and inspect: if `<strong>` wraps only `Purpose:`, it's a CSS
bleed and CSS-scoping fixes it; if `<strong>` wraps the whole
paragraph, it's a tokenizer issue and a pre-pass normaliser fixes
it.

### 7. Tests

- `tests/protocol/test_parse.py`:
  - `## 4. Claims I Expect the Other Agent Might Dispute` body with
    6 numbered items → 6 `ReviewItem` with `kind="claim"`.
  - `## 5. Open Questions` (no "for X") with 5 `**Q1:**`-style
    items → 5 `ReviewItem` with `kind="question"`.
  - `## Diff vs openai's Phase 1` with 10 D-N items → 10
    `ReviewItem` with `kind="claim"` (D6 — previously
    `disagreement`).
  - `## Substantive disagreements I'm holding` still produces
    `kind="disagreement"` (unchanged).
- `tests/ui/test_claims.py` (new):
  - `reconstruct_claims` walks `phase1/draft-claude.md` and returns
    claims with `phase=1`, `agent="claude"`, stable IDs.
  - Round-1 difference inventory parsed as claims with
    `phase=2`, `raised_turn_key="phase2_round1_<agent>"`.
- `tests/ui/test_aggregator.py`:
  - `Run.claims` populated for the partner-vetting fixture.
  - `Run.current_draft_path` populated when `phase4/draft-v*.md`
    exists.
  - `phase_review_items` has `phase1_claude` / `phase1_gpt` keys
    on a fixture that has both Phase 1 drafts.
- `tests/protocol/test_markdown.py` (new):
  - Render `## 4. Claims …\n\n1. **First**\n2. **Second**\n` and
    assert the resulting HTML has `<h2>` + `<ol start="1">` (or
    `<ol>` without `start`). The list does NOT continue from a
    prior heading's number.
  - Render `**Purpose:** prose body without further bold.` and
    assert only `<strong>Purpose:</strong>` is emitted (not a
    paragraph-wrapping `<strong>`).
- Manual: load the partner-vetting Phase 2 Claude turn 1 full-view
  modal — right pane shows 6 questions + 10 claims; the keyboard
  `j/k` walk crosses both groups.
- Manual: load any Phase 4 turn card → full-view → left pane shows
  the converged draft, right pane shows the issues/comments/
  disagreements for that round.
- Manual: critique header math — pick the phase tab and verify
  `N introduced = X open + Y resolved + (kinds toggled off)`.

### 8. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.39.0 → 0.40.0.
- `CHANGELOG.md`: `## [0.40.0]` heading; new `[Unreleased]`
  placeholder.
- `VERSION_NOTES` at the top of `how-it-works.jsx`:
  > **0.40.0 — Critique data integrity.** Phase 1 draft cards now
  > surface Claims and Open Questions correctly; Phase 2 round-1
  > difference inventory parses as Claims (the agent's "held"
  > disagreements only appear from R2 onward); Phase 2 / Phase 4
  > full-view modals load their side-by-side content reliably;
  > critique header counts reconcile within a single phase scope.

### 9. Files touched

Backend:
- `src/dual_research/protocol/parse.py` — D1, D6.
- `src/dual_research/ui/models.py` — D2, D8.
- `src/dual_research/ui/claims.py` (new) — D3.
- `src/dual_research/ui/aggregator.py` — D3, D8.
- `src/dual_research/ui/server.py` — auto camelCase (no code change).

Frontend:
- `src/dual_research/ui/static/run-detail.jsx` — D4, D5, D7, D11.
- `src/dual_research/ui/static/shared.jsx` — D9, D10.
- `src/dual_research/ui/static/how-it-works.jsx` — VERSION_NOTES.

Tests:
- `tests/protocol/test_parse.py` — extend.
- `tests/protocol/test_markdown.py` (new).
- `tests/ui/test_claims.py` (new).
- `tests/ui/test_aggregator.py` — extend.

## Out of scope

- **Authoritative cross-round ledger + LLM-visible standing-items
  input + conservative convergence cross-check.** Spec 0043.
  That spec adds: (a) an orchestrator-side ledger module that
  derives item state across rounds from existing parsed sections
  (`## Answers to:`, `## Resolved or non-blocking differences`,
  the Phase 4 issue ledger), (b) a `## Standing items` section
  appended to round-N (N≥2) prompts so the LLM has structured
  prior-state as input, and (c) a convergence check that requires
  both agent self-counters AND the ledger open-set to agree
  before terminating a phase. Spec 0042 stops short of all of
  that — it reads parsed-item counts per turn and the system
  still trusts agent-self-managed closure between rounds. 0042's
  wire-format additions (`Run.claims`, `kind="claim"`,
  `current_draft_path`) are the foundation 0043 builds on.
- **Per-turn badge redesign** (drop "negotiating" status pill;
  show `+raised/-resolved/open` deltas; "agreed" only at
  phase-wide closure). Spec 0044. Spec 0042 only fixes the count
  *source* and the per-phase allowlist; the visual chip language
  is unchanged. The badge deltas in 0044 read from 0043's ledger,
  not from per-turn parsed counts.
- **Side-by-side framing** (defining what each turn "responds
  to"; making the left pane explicitly the "thing being reviewed"
  with phase-aware tabs for brief / own draft / other's draft /
  prior turn). Spec 0044.
- **Critique panel header layout rework** (P2 / P4 / Summary
  buttons; counts moved out of "Critique" label). Spec 0046. Spec
  0042 fixes the math (D11) in place — the visual rearrangement
  comes later.
- **Phase 4 card cryptic IDs** (`I-c-r1-01`, `R1→R2`, `**C-1**`).
  Spec 0046 visual cleanup. The IDs are honest, just ugly.
- **Click-to-highlight wiring on Phase 1 `brief` chips.** Spec
  0044 — that's part of the side-by-side framing.
- **Backfilling claims into Supabase JSONB on existing hosted
  runs.** The aggregator reconstructs from disk on every read; no
  migration needed. On the canonical partner-vetting fixture the
  values appear on next page-load.
- **Restructuring protocol prompts** to use cleaner section names
  (e.g. unify `## Open Questions` between Phase 1 and Phase 2).
  Future spec — the parser tolerates both today.
- **`Run.current_draft_path` exposure to other surfaces.** Only
  the Phase 4 full-view modal needs it for D8; broader surfacing
  (e.g. on the timeline header) is out of scope.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec adds at least 8
      new tests across parse / claims / aggregator / markdown.
- [ ] Manual: open Phase 1 plan-draft card (Claude or GPT). Chip
      row reads `N claims · M questions`. No `disagreements` chip.
- [ ] Manual: open the Phase 2 Claude turn 1 full-view modal.
      Right pane shows 6 Open questions + 10 Claims (was
      "round-1 difference inventory"; D6 re-bucketed). Keyboard
      `j/k` walks all 16 items. Left pane renders openai's Phase 1
      draft correctly (no numbering bleed).
- [ ] Manual: open any Phase 4 turn full-view modal on the
      partner-vetting fixture. Left pane shows the converged
      draft `phase4/draft-v2.md`. Right pane shows the round's
      issues / comments / disagreements grouped.
- [ ] Manual: critique header on partner-vetting. Switch between
      Phase 2 / Phase 4 tabs. `N introduced · X open · Y resolved`
      reconciles within each tab. The Phase 2 tab no longer
      counts Phase 4 items toward `introduced`.
- [ ] Manual: brief content (left pane of any side-by-side modal).
      The "Purpose:" word is bold; the rest of the paragraph is
      not. Section headings `## 1. Origin and Context` render as
      H2 with their numeric prefix in the heading text. The body
      ordered lists below each heading start at 1.
- [ ] Preview-verified against the partner-vetting fixture at
      `localhost:6173`.

## Risks

- **D6 changes the wire-format kind of round-1 difference items
  from `disagreement` to `claim`.** Any frontend code that filters
  on `kind === "disagreement"` will silently miss these. The
  CritiqueExplorer's `Disagreements` filter chip will report a
  lower count after this spec lands; the `Claims` filter (new)
  picks them up. Acceptable trade — the semantic split matches
  the protocol intent more faithfully.
- **D4's parsed-item count can disagree with the agent's
  self-counter.** When `OPEN_QUESTIONS: 6` but the parser only
  extracts 5 (because the agent miscounted, or one item got
  malformed), the badge will read `5 questions`. The discrepancy
  is logged (`console.warn` on the frontend; aggregator-side
  metric on the backend). Net: the badge becomes more honest —
  it reflects what the UI can actually surface, not what the
  agent claimed.
- **D7 always-populates Phase 1 / Phase 2 keys even when items are
  empty.** This is a wire-format size increase per run (a few
  dozen empty arrays). Negligible (<1 KB JSON per run); the
  alternative is the current "absence-as-empty" ambiguity which
  is what hides the bug.
- **D8's `currentDraftPath` falls back to `phase3/draft-v1.md`
  when no Phase 4 draft exists.** On runs killed before Phase 4
  the Phase 4 full-view modal would never open anyway (no Phase 4
  cards on the timeline), so the fallback is defensive. No
  user-visible regression expected.
- **D9 / D10's marked fixes may not be one-line.** If marked v14
  has a genuine tokenizer issue with `## N. Title` patterns, the
  fallback is the pre-pass normaliser + CSS counter. That's
  invasive on the rendering layer. Mitigation: time-box the
  root-cause investigation; if the fix isn't found in 90 minutes,
  ship the pre-pass + CSS counter and move on.

## Open questions

- Whether Phase 1's `## 5. Open Questions` items should anchor
  against the brief (current design) or be marked as
  un-anchorable (since the brief is the input, not the
  predecessor in a negotiation chain). v1 anchors against the
  brief — same as Phase 2 R1 anchors against the other agent's
  Phase 1 draft. Cross-link from claim to brief block lights up
  the existing scrollAndFlash plumbing for free.
- Whether `Run.claims` should split into `claims_p1` /
  `claims_p2_r1` arrays or stay as one list with a `phase` field.
  v1 keeps one list; the `phase` field is enough for the UI to
  filter. A later spec can split if needed.
- Whether the "drop `disagreements` chip from Phase 1" rule
  should also apply to the *Critique panel's filter chips* (i.e.
  hide `Disagreements` when the selected phase has zero of
  them). v1 keeps the chip visible with a `0` badge — better for
  visual consistency across phase tabs. Spec 0046's "filter
  labels context-aware per phase" can revisit.
