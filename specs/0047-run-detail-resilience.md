---
spec: 0047
title: Run-detail resilience + Phase 4 sibling-key separation for repair turns
label: bug
version-bump: MINOR
status: in-progress
target-version: 0.45.0
created: 2026-05-17
pr: ""
---

# Spec 0047 — Run-detail resilience + Phase 4 sibling-key separation for repair turns

## Context

Three defensive defects identified during the 2026-05-17 audit
([`handoffs/2026-05-17-gaps-and-next-three-specs.md`](../handoffs/2026-05-17-gaps-and-next-three-specs.md)).
All three are bugs on `main` that surface on real local runs; none is
a new feature. They sit in three different layers (frontend artifact
rendering, orchestrator finalize, UI aggregator) but the testing
motion is identical — open the partner-vetting fixture + a
`drafter=null` historical run + a synthetic transcript with a repair
sibling, verify nothing crashes, verify the Consumption tab now
shows the repair turns as their own cards.

The version bump is **MINOR** (0.44.0 → 0.45.0) because **F5** changes
the per-turn key shape on the wire (`phase4_round1_claude` →
`phase4_round1_claude_repair` for repair siblings). The other two
items are pure defensive fixes that would otherwise be PATCH.

### F1 — Drafter-null run-detail crash

**Symptom.** Run-detail page renders blank with React error
`Cannot read properties of null (reading 'name')` for runs where
`drafter=null` + `status=completed`. Five historical local runs in
the working tree hit this shape (anything killed before Phase 3 but
marked complete by an old orchestrator path), e.g.
`runs/20260515-111151-asyncio-vs-goroutines/`.

**Root cause.**
[`live-data.jsx:660`](../src/dual_research/ui/static/live-data.jsx)
emits `{ id: 'doc-final', kind: 'doc', agent: run.drafter, ... }`
when `status === 'completed'`. When `drafter` is null, `agent === null`,
so the downstream `meta = item.agent ? AGENT_META[item.agent] : null`
in `ArtifactCard` produces `meta = null`. Then
[`run-detail.jsx:2679`](../src/dual_research/ui/static/run-detail.jsx:2679)
(the `item.kind === 'doc'` branch of `ArtifactHeader`) does
`<span>by {meta.name}</span>` without a guard, and the React render
throws. The sibling `item.kind === 'doc-live'` branch
([`run-detail.jsx:2688`](../src/dual_research/ui/static/run-detail.jsx:2688),
[`:2704`](../src/dual_research/ui/static/run-detail.jsx:2704)) has the
same unguarded `meta.name` access. The pattern elsewhere
([`run-detail.jsx:2812-2814`](../src/dual_research/ui/static/run-detail.jsx:2812))
already uses the guarded form `meta ? \`by ${meta.name}\` : null`.

### F2 — Post-finalize `'NoneType' object has no attribute 'rounds'`

**Symptom.** Partner-vetting transcript carries a `critical · halted`
`ORCHESTRATOR_PANIC` at 2026-05-16T09:21:55Z with
`error_type: AttributeError`, `message: 'NoneType' object has no
attribute 'rounds'`, recorded AFTER `phase: done`. Traceback in the
transcript:

```
File "src/dual_research/orchestrator/finalize.py", line 26, in confidence_tag
  p2_clean = phase2_outcome.rounds <= soft_cap and not phase2_outcome.via_tiebreak
AttributeError: 'NoneType' object has no attribute 'rounds'
```

**Current state on `main`.** Since that run,
[`finalize.py:32`](../src/dual_research/orchestrator/finalize.py:32)
has gained the guard
`if phase2_outcome is None: return "MODERATE"` ahead of the access at
line 34, and `render_metadata_header` has a sibling guard at line 92.
So the specific crash is fixed — but the audit flags it because (a)
there's no regression test that exercises the None-finalize path and
(b) other finalize paths in `emit_final.py` / `finalize.py` haven't
been swept for the same shape. F2 in this spec is therefore: audit
+ harden + add the regression test.

### F5 — Phase 4 sibling-key collapse on Consumption tab

**Symptom.** Phase 4 had 3 `INVALID_TURN_FORMAT` recoveries in the
partner-vetting run. The transcript carries 3 sibling
`turn_ended` events with labels `phase4-r1-claude-repair`,
`phase4-r2-claude-repair`, `phase4-r3-claude-repair` adjacent to the
originals `phase4-r{1,2,3}-claude`. Each repair is a real extra LLM
call (input ~20k tokens, output 6144, cost ~$0.15 — see
[partner-vetting transcript:64-65 and 94-95](../runs/20260516-035048-partner-vetting-arch-critique/transcript.jsonl)).

The Consumption tab today shows one card per `(phase, round, agent)`,
and the per-card detail under-reports the repair cost. Phase 2 has
the same shape via `phase2-r4-gpt-hashdrift-repair` from
[`phase2.py:539`](../src/dual_research/orchestrator/phase2.py:539).

**Root cause.** The per-turn key derivation in
[`aggregator.py::_on_turn_ended`](../src/dual_research/ui/aggregator.py)
(line 393 and friends) is `phase{N}_round{R}_{agent}`. Repair siblings
collide on the same key. The comment block at
[`aggregator.py:432-440`](../src/dual_research/ui/aggregator.py:432)
acknowledges this explicitly: BOTH events contribute to the agent-level
totals (correct — matches billing) but the per-turn dict overwrites,
so the LAST sibling wins on the Consumption tab card.

The transcript-level same-label dedup `_dedup_turn_ended_by_label`
(spec 0039) is a different mechanism — it handles pre-0039 transcripts
where literal duplicate labels appeared. That logic is unaffected by
this spec.

### Why these three are grouped

- Same testing motion (one fixture, one historical run, one synthetic).
- All three are defensive — no behaviour change on the happy path.
- Total surface is small (~30 lines of frontend, ~15 lines of orchestrator
  audit + 1 guard if anything's found, ~25 lines of aggregator + frontend
  for the per-turn key + Consumption / Summary plumbing).
- Sequencing them as one spec lets the per-turn key change ride a
  single MINOR bump rather than landing a PATCH and then a MINOR for
  separate fixes.

Prior context:

- [Spec 0036](./0036-web-search-audit-foundation.md) — original None-guards in `emit_final` / `confidence_tag` after the resume scenario surfaced.
- [Spec 0039](./0039-cost-pipeline-integrity.md) — `_dedup_turn_ended_by_label` (same-label dedup) and the per-turn dict's later-wins overwrite that this spec addresses for sibling labels.
- [Spec 0035](./0035-consumption-rework.md) — current Consumption tab card layout.
- [Spec 0046](./0046-critique-summary-consumption-rework.md) — Consumption inline-expand card + Summary per-round × per-model table that this spec extends with repair-row support.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **`ArtifactHeader` for `kind === 'doc'` / `kind === 'doc-live'` accesses `meta` defensively.** | All four unguarded `meta.name` / `meta.color` reads in `run-detail.jsx:2672-2705` use the `meta ? … : null` (or `meta?.name`) shape already established at line 2812. Matches existing convention; no behaviour change when `meta` is non-null. |
| D2  | **`buildLiveTimeline` skips `doc-final` emission when `drafter` is null.** | Defence in depth at the data layer. The "doc-final" item only makes sense if there's a drafter to attribute it to; emitting it with `agent: null` is a malformed timeline item. Combined with D1, two independent guards. |
| D3  | **Audit + harden every `phase{N}_outcome.<attr>` access in `finalize.py` + `emit_final.py`.** | Walk every read of `phase1_outcome`, `phase2_outcome`, `phase3_outcome`, `phase4_outcome` in both files. For each, check the function signature's type — if it's `Foo \| None`, the access must be inside a None-guard. Today the audit shows `confidence_tag` + `render_metadata_header` are safe; the spec's contribution is to make this explicit + caught by a test. |
| D4  | **Per-turn key gains a `_repair` suffix for sibling labels.** | When the transcript label carries `-repair` or `-hashdrift`, the aggregator's `_on_turn_ended` derives `phase{N}_round{R}_{agent}_repair` instead of overwriting the parent key. Matches the convention already established by `_on_turn_inputs` and `_on_turn_searches` (which write the per-turn input bundle + search audit stubs under the same suffix). Both `-repair` (Phase 4 parse-recovery) and `-hashdrift-repair` (Phase 2 hash-drift recovery) collapse to the single `_repair` suffix — they never collide on the same `(phase, round, agent)` triple, so disambiguation isn't required. Single-shot phases (0, 1, 3) and regular round-loop turns keep their current key shape. |
| D5  | **Agent-level rollups continue to accumulate every event (no behaviour change).** | The change in D4 only adds new per-turn entries; the `state.tokens.in_ += in_tokens` / `state.cost += cost` accumulators at `aggregator.py:425-428` keep firing on every event. This preserves the "agent total matches the bill" invariant. |
| D6  | **Consumption tab renders repair cards adjacent to the parent turn, with a `repair` chip.** | Enumeration of `run.phase_token_usage` keys already drives card rendering. Cards whose key matches `phase{N}_round{R}_{agent}_{suffix}` sort immediately after their parent `phase{N}_round{R}_{agent}` and render with a small `repair` (or `hashdrift repair`) chip on the header. Visually grouped, not nested — flat list, same indent, just adjacent and labelled. |
| D7  | **Summary tab includes repair turns in the per-round × per-model breakdown.** | The Summary table built in spec 0046 D5 reads ledger entries, not per-turn keys, so the table content itself doesn't change. The per-round token / cost totals at the bottom of each section already sum across all keys via `phase_token_usage`, so they pick up the repair entries automatically once D4 lands. No new UI for the Summary tab; just verify the totals add up. |
| D8  | **Timeline view (`buildLiveTimeline`) is unchanged — repair turns don't get their own timeline cards.** | The timeline pane shows the conversation flow; repair is an internal protocol-recovery mechanism, not a conversational step. Surfacing it as a separate timeline card would inflate every long-run timeline. Instead, the parent turn's `StatsChips` gains a small `+repair` decoration when a sibling repair key exists for that turn (so the user knows to look at the Consumption tab for the breakdown). |
| D9  | **No transcript / on-disk schema changes.** | Labels stay as-is; the change is in how the aggregator derives keys from those labels. Existing transcripts replay correctly — the same helper applies to historical events. |
| D10 | **Regression tests at each layer.** | (a) Synthetic timeline with `drafter=null, status='completed'` → `buildLiveTimeline` either skips `doc-final` or emits it without crashing downstream; React render snapshot succeeds. (b) Synthetic `emit_final` call with `phase2_outcome=None` → `confidence_tag` returns `"MODERATE"`, `render_metadata_header` produces the "(replayed from prior run)" placeholder line, no AttributeError. (c) Synthetic transcript with `phase4-r1-claude` + `phase4-r1-claude-repair` sibling events → aggregator produces two distinct `phase_token_usage` entries; Phase 2 hashdrift variant produces `phase2_round4_gpt_hashdrift_repair`. |

## Proposed change

### 1. Defensive `meta` access in `ArtifactHeader` — D1

[`run-detail.jsx:2672-2705`](../src/dual_research/ui/static/run-detail.jsx:2672)
currently:

```jsx
if (item.kind === 'doc') {
  return (
    <div ...>
      <Icon.Check style={{ color: COLORS.ok }} />
      <span ...>{item.completed ? 'Final document' : 'Converged document'}</span>
      <span className="mono" ...>by {meta.name}</span>          {/* unguarded */}
      <span style={{ flex: 1 }} />
    </div>
  );
}
if (item.kind === 'doc-live') {
  return (
    <div ...>
      <AgentIcon agent={item.agent} size={14} />
      <span ...>{meta.name}</span>                              {/* unguarded */}
      <span ...>drafting converged document</span>
      <span style={{ flex: 1 }} />
      <span className="mono" style={{ color: meta.color, ... }}>DRAFTER</span>  {/* unguarded */}
    </div>
  );
}
```

After spec 0047:

```jsx
if (item.kind === 'doc') {
  return (
    <div ...>
      <Icon.Check style={{ color: COLORS.ok }} />
      <span ...>{item.completed ? 'Final document' : 'Converged document'}</span>
      {meta && <span className="mono" ...>by {meta.name}</span>}
      <span style={{ flex: 1 }} />
    </div>
  );
}
if (item.kind === 'doc-live') {
  if (!meta) return null;                       // doc-live without a drafter is meaningless
  return (
    <div ...>
      <AgentIcon agent={item.agent} size={14} />
      <span ...>{meta.name}</span>
      <span ...>drafting converged document</span>
      <span style={{ flex: 1 }} />
      <span className="mono" style={{ color: meta.color, ... }}>DRAFTER</span>
    </div>
  );
}
```

The `doc-live` branch returns `null` rather than rendering an
unguarded chain — that branch only fires while a drafter is actively
writing the converged document, so absence of `meta` means the state
is corrupt and there's nothing meaningful to show. The `doc` (final)
branch survives `meta == null` by suppressing the byline; the "Final
document" / "Converged document" headline is still useful.

### 2. `buildLiveTimeline` defensive `doc-final` emission — D2

[`live-data.jsx:658-664`](../src/dual_research/ui/static/live-data.jsx)
currently:

```js
items.push({
  id: 'doc-final', kind: 'doc', agent: run.drafter, completed: true,
  ...
});
```

After spec 0047:

```js
if (run.drafter) {
  items.push({
    id: 'doc-final', kind: 'doc', agent: run.drafter, completed: true,
    ...
  });
}
```

A run that reached `status: completed` without a drafter is a
historical anomaly (orchestrator versions that marked the run complete
before Phase 3 ran). Don't synthesise a "final document by null"
artifact for it; the artifact strip just doesn't include the final
card for those runs.

Same guard applies to the matching `doc-live` push at
[`live-data.jsx:590`](../src/dual_research/ui/static/live-data.jsx:590) —
already gated by `run.drafter` upstream of the push (the live branch
only fires during Phase 3, which only starts after a drafter is set),
but worth a defensive `if (run.drafter)` for symmetry.

### 3. Finalize-path audit + regression — D3, D10b

Sweep every `phase{1,2,3,4}_outcome.<attr>` access in
[`src/dual_research/orchestrator/finalize.py`](../src/dual_research/orchestrator/finalize.py)
(which is where `emit_final` lives — there's no separate `emit_final.py`).
For each, confirm:

- The function signature types the outcome as `Foo | None` ⇒ the
  access is inside a None-guard branch.
- The function signature types the outcome as `Foo` (no None) ⇒ the
  access is unguarded and the caller is responsible.

Today's known-safe accesses on `main`:

- `confidence_tag` — line 32 None-guard, line 34+ access. **Safe.**
- `render_metadata_header` — line 92 None-guard for the
  `p2_rounds_line` / `p2_drafter_line` / `p2_fsd_line` block,
  line 97+ access inside the else branch. **Safe.**
- `phase4_outcome.<attr>` accesses (lines 30, 35, 88, 119, 163, 166,
  171) — typed as `Phase4Outcome` (no None). **Safe.**

If the sweep finds an unguarded access on a `Foo | None` parameter,
add the guard following the spec-0036 pattern (degrade rather than
crash; emit a placeholder line if it's in `render_metadata_header`).

Regression test (regardless of whether new bugs are found):

```python
# tests/orchestrator/test_finalize_resilience.py (new)
def test_confidence_tag_returns_moderate_when_phase2_outcome_is_none():
    tag = confidence_tag(
        phase2_outcome=None,
        phase4_outcome=Phase4Outcome(approved=True, rounds=1, revisions=0, final_draft_round=1),
        soft_cap=4, hard_cap=8, repair_count=0,
    )
    assert tag == "MODERATE"

def test_render_metadata_header_when_phase2_outcome_is_none():
    header = render_metadata_header(
        ctx=_synthetic_ctx(),
        phase2_outcome=None,
        phase4_outcome=Phase4Outcome(approved=True, rounds=2, revisions=0, final_draft_round=1),
        soft_cap=4, hard_cap=8,
        claude_model="claude-sonnet-4-6",
        openai_model="gpt-5.5-2026-04-23",
    )
    assert "(replayed from prior run — Phase 2 details unavailable)" in header

def test_emit_final_when_phase2_outcome_is_none(tmp_path):
    # Synthetic resume scenario: Phase 2 outcome is None because Phase 2
    # completed in a prior invocation. emit_final must not raise.
    ...
```

### 4. Aggregator per-turn key handles repair suffix — D4, D5, D9, D10c

New helper in
[`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py):

```python
# Spec 0047: separate per-turn entries for repair siblings so the
# Consumption tab shows each LLM call individually instead of
# collapsing the original turn and its repair into one card.
def _turn_key_suffix_from_label(label: str, agent_ui: str, *, phase_int: int, round_idx: int) -> str | None:
    """Return the trailing label segment that follows the canonical
    `phase{N}-r{R}-{agent}` prefix, normalised for use as a key suffix.

    Examples:
      'phase4-r1-claude'                 -> None
      'phase4-r1-claude-repair'          -> 'repair'
      'phase2-r4-gpt-hashdrift-repair'   -> 'hashdrift_repair'

    The agent token in the label uses the backend name (`claude`, `gpt`
    — or `openai` for older transcripts); accept either.
    """
    if not label:
        return None
    backend_agent = {'claude': 'claude', 'gpt': 'gpt'}.get(agent_ui, agent_ui)
    # Labels historically used `openai` instead of `gpt`; accept both.
    for tok in (backend_agent, 'openai' if backend_agent == 'gpt' else None):
        if not tok:
            continue
        prefix = f"phase{phase_int}-r{round_idx}-{tok}"
        if label.startswith(prefix):
            tail = label[len(prefix):]
            if tail.startswith('-'):
                tail = tail[1:]
            return tail.replace('-', '_') if tail else None
    return None
```

Patch `_on_turn_ended` at
[`aggregator.py:391-395`](../src/dual_research/ui/aggregator.py:391):

```python
if phase_int in (2, 4) and idx > 0:
    key = f"phase{phase_int}_round{idx}_{ag}"
    suffix = _turn_key_suffix_from_label(label, ag, phase_int=phase_int, round_idx=idx)
    if suffix:
        key = f"{key}_{suffix}"
else:
    key = f"phase{phase_int}_{ag}"
```

Apply the same change at the parallel constructions in
[`aggregator.py:503`](../src/dual_research/ui/aggregator.py:503),
[`aggregator.py:568`](../src/dual_research/ui/aggregator.py:568),
and
[`aggregator.py:1063`](../src/dual_research/ui/aggregator.py:1063),
[`aggregator.py:1201`](../src/dual_research/ui/aggregator.py:1201),
[`aggregator.py:1278`](../src/dual_research/ui/aggregator.py:1278),
[`aggregator.py:1289`](../src/dual_research/ui/aggregator.py:1289) —
any site that derives a `phase{N}_round{R}_{agent}` key from a
transcript label. (Sites that construct the key from non-label state —
e.g. ledger entries that already know the round — keep the base key
without a suffix, because ledger entries don't have repair siblings.)

Update the comment block at
[`aggregator.py:432-440`](../src/dual_research/ui/aggregator.py:432) to
reflect the new behaviour:

```python
# Spec 0039 → Spec 0047 — same-label dedup (pre-0039 transcripts) is
# handled upstream by ``_dedup_turn_ended_by_label``. Sibling labels
# (the original turn + its `-repair` or `-hashdrift-repair` sibling)
# now derive DIFFERENT per-turn keys via `_turn_key_suffix_from_label`,
# so each LLM call gets its own Consumption-tab card. The agent-level
# totals (state.tokens.*, state.cost) still accumulate every event
# unconditionally — they match the billing aggregate.
```

### 5. Consumption tab: repair cards adjacent to parent — D6

[`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx)
Consumption tab today enumerates `phase_token_usage` keys and renders
one card per key. Two changes:

(a) Sort comparator: cards whose key matches the pattern
`phase{N}_round{R}_{agent}` followed by `_<suffix>` sort immediately
after the matching parent key. Within a `(phase, round, agent)` group:
parent first, then repair siblings in the order they appeared.

(b) `ConsumptionRow` (introduced in spec 0046 D6) renders a small
`repair` chip on the header when the key carries a suffix. Chip
label derives from the suffix (`repair` → "repair", `hashdrift_repair`
→ "hashdrift repair") with a tooltip explaining "Re-prompted turn
after the original failed protocol parse" or similar.

```jsx
function ConsumptionRow({ keyName, row }) {
  const suffix = parseRepairSuffix(keyName);     // null | 'repair' | 'hashdrift_repair'
  return (
    <div className="card" style={{ paddingLeft: suffix ? 22 : 14, ... }}>
      <ConsumptionRowTopBar
        row={row}
        suffixChip={suffix && <RepairChip label={suffix.replace('_', ' ')} />}
        ...
      />
      ...
    </div>
  );
}
```

`paddingLeft: suffix ? 22 : 14` is the only nesting cue — flat list,
slight indent on repair siblings so the eye groups them with their
parent.

### 6. Summary tab — D7

No template change; the per-round × per-model table built in spec
0046 D5 reads ledger entries which don't have repair siblings. The
per-section totals at the bottom of each Summary section (which read
`phase_token_usage`) pick up repair entries automatically via
existing summation.

Manual verification step: open the partner-vetting run, navigate to
Critique → Summary tab. The "Phase 4 — Review" section's total
token / cost row should match the sum of the per-card totals on the
Consumption tab — including the three repair siblings.

### 7. Timeline `StatsChips` `+repair` decoration — D8

The timeline pane's per-turn `StatsChips` (rendered for `kind: 'turn'`
items in [`run-detail.jsx:2700+`](../src/dual_research/ui/static/run-detail.jsx))
gains a small `+repair` chip when a sibling repair key exists for
that turn's parent key. Implementation:

```jsx
function StatsChips({ phase, run, item }) {
  const parentKey = item.turnKey;
  const hasRepairSibling = run.phaseTokenUsage &&
    Object.keys(run.phaseTokenUsage).some(
      (k) => k !== parentKey && k.startsWith(`${parentKey}_`)
    );
  return (
    <>
      ...existing chips...
      {hasRepairSibling && <RepairSiblingHint />}
    </>
  );
}
```

`<RepairSiblingHint />` is a small `+repair` chip with a tooltip
"This turn was re-prompted after a protocol-parse failure — see
Consumption tab for the breakdown." Tiny addition; helps
discoverability without inflating the timeline.

### 8. Versioning + release notes

- `pyproject.toml`, `src/dual_research/__init__.py`: 0.44.0 → 0.45.0.
- `CHANGELOG.md`: move `[Unreleased]` to `## [0.45.0]` heading.
  Sub-headings: `### Fixed` for F1 / F2; `### Changed` for F5 (per-turn
  key shape on the wire).
- `VERSION_NOTES` entry at the top of `how-it-works.jsx`:
  > **0.45.0 — Run-detail resilience + repair-turn visibility.** Run-
  > detail page no longer crashes on historical runs that were marked
  > complete without a drafter (defensive guards on the artifact-card
  > byline). Finalize path hardened against the resume scenario where
  > Phase 2 outcome is None on disk. Phase 4 (and Phase 2) protocol-
  > repair turns now appear as their own cards on the Consumption tab,
  > adjacent to the original turn with a `repair` chip, instead of
  > being collapsed into the parent card. Per-turn key on the wire
  > gains a `_repair` / `_hashdrift_repair` suffix for repair siblings;
  > agent-level rollups unchanged.

### 9. Files touched

Frontend:

- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) —
  D1 (four `meta.name` / `meta.color` accesses in the `doc` / `doc-live`
  branches of `ArtifactHeader`), D6 (Consumption tab sort + repair
  chip), D8 (`StatsChips` `+repair` decoration).
- [`src/dual_research/ui/static/live-data.jsx`](../src/dual_research/ui/static/live-data.jsx) —
  D2 (`doc-final` + `doc-live` emission gated on `run.drafter`).
- [`src/dual_research/ui/static/how-it-works.jsx`](../src/dual_research/ui/static/how-it-works.jsx) —
  `VERSION_NOTES` entry.

Backend:

- [`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py) —
  D4 (`_turn_key_suffix_from_label` helper + 6–7 call sites updated +
  D9 comment block update).
- [`src/dual_research/orchestrator/finalize.py`](../src/dual_research/orchestrator/finalize.py) —
  D3 (sweep; add guards only if the sweep finds an unguarded access).
- [`src/dual_research/orchestrator/emit_final.py`](../src/dual_research/orchestrator/emit_final.py) —
  D3 (sweep; same).

Tests:

- `tests/orchestrator/test_finalize_resilience.py` (new) — D10b.
- `tests/ui/test_aggregator_repair_siblings.py` (new) — D10c.
- `tests/ui/test_live_data_drafter_null.py` (new, lightweight) — D10a;
  Python-level assertion that `load_run_snapshot` succeeds on a synthetic
  `drafter=null, status='completed'` run.

Pyproject + version:

- [`pyproject.toml`](../pyproject.toml) — version bump.
- [`src/dual_research/__init__.py`](../src/dual_research/__init__.py) —
  version bump.
- [`CHANGELOG.md`](../CHANGELOG.md) — `[Unreleased]` → `[0.45.0]`.

## Out of scope

- **A dedicated "repair turn" inspector view.** v1 surfaces the
  repair as its own Consumption card with a chip + tooltip; a full
  side-by-side "original vs repaired" view (showing what was malformed
  and what the repair fixed) is a future spec if real-run usage shows
  it's needed.
- **Filtering the Consumption tab by repair / non-repair.** v1 shows
  all cards; the chip makes repairs visually distinguishable. A toggle
  is a future spec.
- **Surfacing repair turns as separate timeline cards.** The timeline
  pane stays conversational (D8); repair is mechanism, not message.
- **Backfill of historical runs to "explode" any collapsed metrics.**
  The aggregator already accumulates the agent rollups correctly via
  spec 0039's same-label dedup; per-turn details for old runs are not
  recoverable without re-reading the original transcripts, which the
  aggregator does on every load anyway, so this happens for free.
- **Cost reconciliation against provider invoices (spec 0048 territory).**
- **`pricing_version` snapshot on `metrics.json` (spec 0048 territory).**
- **Citation `[V]`/`[U]` inline rendering (spec 0049 territory).**
- **Server-side cited-URL refetch (spec 0049 territory).**

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec adds 3 new test files
      (~10 new tests total).
- [ ] New test: `confidence_tag(phase2_outcome=None, ...)` returns
      `"MODERATE"` rather than raising `AttributeError`.
- [ ] New test: `render_metadata_header(phase2_outcome=None, ...)`
      emits the "(replayed from prior run — Phase 2 details
      unavailable)" placeholder.
- [ ] New test: full `emit_final` call with a synthetic
      `phase2_outcome=None` context completes without raising.
- [ ] New test: synthetic transcript with adjacent `phase4-r1-claude`
      + `phase4-r1-claude-repair` events produces two distinct keys
      `phase4_round1_claude` + `phase4_round1_claude_repair` in
      `run.phase_token_usage`, with the per-key tokens / cost matching
      the per-event payload.
- [ ] New test: synthetic transcript with `phase2-r4-gpt-hashdrift-repair`
      produces key `phase2_round4_gpt_hashdrift_repair`.
- [ ] New test: agent-level rollup (`state.tokens.in_` / `state.cost`)
      after the synthetic transcript equals the sum of original + repair
      event payloads (invariant from D5).
- [ ] New test: `load_run_snapshot` succeeds on a synthetic
      `drafter=null, status='completed'` run; the resulting `Run`
      passes JSON round-trip.
- [ ] Manual / preview: open
      [`runs/20260515-111151-asyncio-vs-goroutines/`](../runs/20260515-111151-asyncio-vs-goroutines/)
      (or another `drafter=null` local run) at `localhost:6173` —
      run-detail page renders without React errors; the artifact strip
      shows phase cards but no "Final document by null".
- [ ] Manual / preview: open
      [`runs/20260516-035048-partner-vetting-arch-critique/`](../runs/20260516-035048-partner-vetting-arch-critique/)
      Phase 4 Consumption tab — sees 5 original cards (`phase4_round{1..5}_claude`)
      plus 3 repair sibling cards (`phase4_round{1,2,3}_claude_repair`)
      each labelled with a `repair` chip, sorted adjacent to their
      parent.
- [ ] Manual / preview: same run, hover the `+repair` chip on a
      timeline turn whose parent has a repair sibling — tooltip
      explains the relationship.
- [ ] Manual / preview: Summary tab "Phase 4 — Review" section's
      total cost matches the sum of all 8 cards on the Consumption tab.
- [ ] CHANGELOG entry under `## [0.45.0]` with `### Fixed` + `### Changed`
      sub-headings.
- [ ] VERSION_NOTES entry at the top of `how-it-works.jsx`.
- [ ] Spec front-matter `status: merged` + `pr:` populated before final push.

## Risks

- **D4's per-turn key suffix is a wire-format change.** Downstream
  consumers of `phase_token_usage` keys (the Consumption tab and the
  Summary tab) need updating in the same spec; any other consumer
  that hardcodes the `phase{N}_round{R}_{agent}` shape would silently
  drop the repair entries. Mitigation: grep for `phase\d+_round` and
  `phase_token_usage` across the codebase; verify every consumer
  either handles the suffix (Consumption + Summary) or is provably
  fine to ignore it (e.g. agent-rollup checks that sum `state.tokens`
  which is already correct via D5).
- **D6's adjacent-card sort could surprise users who expect a strict
  chronological order on the Consumption tab.** The repair turn IS
  chronologically adjacent to its parent (it fires immediately after
  the parse fails), so the visual order matches reality — but
  documenting it in the chip tooltip removes ambiguity. Mitigation:
  the tooltip on the `repair` chip says "Re-prompted after the
  original turn failed protocol parse".
- **D1's "return null for `doc-live` without `meta`" hides the live
  draft entirely if there's a state corruption mid-Phase-3.** That's
  a deliberate trade-off — rendering with a half-broken header
  produces a confused UI; rendering nothing at all means the next
  legitimate event will populate the cell. Mitigation: this only
  fires on the malformed `drafter=null` + `kind=doc-live` combination,
  which the orchestrator doesn't produce on the happy path.
- **D3's sweep might find a new latent crash path.** If so, add the
  guard; document it in the CHANGELOG `### Fixed` section alongside F2.
- **The synthetic transcript fixtures need to mirror the real shape
  closely** — partial event ordering matters for the aggregator's
  state machine. Mitigation: copy the relevant lines verbatim from
  the partner-vetting transcript and trim only the unrelated events.

## Open questions

- Should the `repair` chip on the Consumption tab card carry the
  malformed-attempt count (`repair (1)` vs just `repair`)? Today the
  repair budget is 1 per phase per agent so the count is always 1;
  surfacing it adds noise. **Default: no count chip; revisit if the
  budget ever increases.**
- Should `_turn_key_suffix_from_label` accept future suffix flavours
  (e.g. `-resume`, `-retry`) by being fully generic, or be restricted
  to a known allowlist (`repair`, `hashdrift-repair`)? **Default:
  fully generic — the function strips whatever comes after the
  canonical prefix; if an unknown suffix appears, it shows up as a
  card with an unfamiliar chip label, which is louder than silently
  dropping the entry.**
