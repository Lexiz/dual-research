---
spec: 0135
title: Phase 0 round cards + side-by-side critique modal — close the round-by-round visibility gap for the brief negotiation
label: new-feature
version-bump: MINOR
status: ready
target-version: 1.8.0
created: 2026-05-21
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0135 — Phase 0 round cards + side-by-side critique modal

> Ship bucket: **Round-by-round surface parity between Phase 0 and Phase 2 / Phase 4.**
> Depends on: **0114** (Deep-Research protocol — introduced multi-round Phase 0 negotiation), **0115** (UI + items model that consumes the new `ItemRaised` / `ItemTransitioned` stream), **0027** (`NegotiateReviewModal` — the side-by-side modal), **0033** (Phase 0 brief-critique split into per-agent cards + Input tab), **0042** (Phase 1 plan-draft modal which extended `priorContentPathFor` to a non-Phase-2/4 phase — same shape we'll extend now), **0119/0120** (badge + chip governance on review cards that Phase 0 will now reuse verbatim).
> Complexity: **M** — four narrow backend touch points + three narrow frontend touch points. No new protocol, no new prompts, no new on-disk artefacts. Existing `_drive_interaction_phase` already produces every byte the new surfaces need; this spec just unlocks them downstream.
> Targeted version bump: **MINOR (1.7.1 → 1.8.0)** — `PhaseStats.phase0` wire-shape changes from per-agent to round-keyed-per-agent, and a new `phase0_round_complete` event joins the legacy event schema. No protocol or contract changes.

---

## 1. Context

Spec 0114 made Phase 0 a full multi-round negotiation: both agents critique the brief, raise questions / disagreements / comments anchored against `brief.md`, and converge over `1..N` rounds via the exact same `_drive_interaction_phase` coroutine that drives Phase 2 (plan negotiation) and Phase 4 (draft review). The ledger captures every raise + transition; rounds are written to disk as `phase0/round-NN-<agent>.md`; convergence + closeout flow through the same `DeepResearchPhase` machinery.

But the **downstream surfaces never caught up**. The Phase 0 negotiation collapses back to a two-card "preflight" view on the timeline — one card per agent, no per-round breakdown — and the per-card full-view opens a single-pane modal with no side-by-side critique pane. Phase 2 and Phase 4 already render the canonical pattern the user expects:

- **One card per round per agent** on the timeline (e.g. for a 4-round Phase 2: 8 cards — `round 1 Claude`, `round 1 GPT`, `round 2 Claude`, … `round 4 GPT`).
- **Full-view modal is side-by-side** ([`NegotiateReviewModal`](src/dual_research/ui/static/run-detail.jsx)) — left pane shows the artefact being critiqued (other agent's prior turn for round ≥ 2, other agent's Phase 1 draft for round 1 of Phase 2, current converged draft for Phase 4); right pane stacks `ReviewGroup`s of questions, disagreements, issues, and comments raised by this agent in this round, with anchored jumps to the left pane and the progression (raise → push back → restate → align / concede) on each card.
- **Cross-round ledger** powers the chip deltas and the cross-round "DRIFT / OPEN" tallies in the critique pane.

The data needed to render the same surface for Phase 0 already exists — every item raised in Phase 0 is in `AggregatedItems.items` with `item.phase == 0`; every round has its `phase0/round-NN-<agent>.md` file on disk; every transition is in the event stream. Six small wiring gaps prevent the downstream code from picking it up:

| # | Layer | File | Gap |
|---|---|---|---|
| G1 | Events | [`dr_run.py:412-442`](src/dual_research/orchestrator/dr_run.py) | `_publish_legacy_round_complete` explicitly comments *"Phase 0 has no per-round event in the legacy schema"* — emits `Phase2RoundComplete` / `Phase4RoundComplete` only. |
| G2 | Models | [`models.py:496`](src/dual_research/ui/models.py) | `PhaseStats.phase0: dict[str, TurnStats]` is per-agent only; `phase2` and `phase4` are `dict[int, dict[str, TurnStats]]` (round-keyed). |
| G3 | Aggregator: stats | [`aggregator.py:_on_turn_ended` + `_attach_*`](src/dual_research/ui/aggregator.py) | Per-turn stats for Phase 0 land in the single per-agent slot; round dimension is dropped on the floor. |
| G4 | Aggregator: review items | [`aggregator.py:1450`](src/dual_research/ui/aggregator.py) | `_read_phase_review_items` walks `for phase_n in (2, 4):` — no phase 0 pass, so no `phase0_round{R}_<agent>` bucket. |
| G5 | Projection: ledger | [`item_projection.py:358`](src/dual_research/ui/item_projection.py) | `project_phase_ledgers` is `out = {2: [], 4: []}` with the comment *"Phase 0 ledger is not yet surfaced on the timeline cards"*. |
| G6 | Frontend: timeline + modal | [`live-data.jsx:486-508`](src/dual_research/ui/static/live-data.jsx) + [`run-detail.jsx:3762-3767` + `4756-4818`](src/dual_research/ui/static/run-detail.jsx) | `buildLiveTimeline` emits exactly **two** preflight cards regardless of round count, pointing at the legacy `phase0/preflight-{agent}.md` filenames (which the new `run_dr_phase0` doesn't write). `ArtifactModal` routes `preflight` cards to the single-pane `PreflightResponseModal`. `priorContentPathFor` + `leftPaneTabsFor` have no phase-0 case. |
| G7 | Aggregator: summaries | [`aggregator.py:1258-1261`](src/dual_research/ui/aggregator.py) | `_read_phase_summaries` reads Phase 0 only from the legacy `phase0/preflight-{agent}.md` files. New-protocol Phase 0 has no summary entries in `run.phase_summaries`, so the round-card collapsed surface gets no TL;DR. |
| G8 | Aggregator: token usage | [`aggregator.py:428`](src/dual_research/ui/aggregator.py) | `_on_turn_ended` keys Phase 0 token usage as `phase0_<agent>` regardless of round (`if phase_int in (2, 4) and idx > 0`). Multi-round Phase 0 collapses into one Consumption-tab card per agent. |
| G9 | Aggregator: live body | [`aggregator.py:1175-1178`](src/dual_research/ui/aggregator.py) | `_populate_current_bodies` for `run.phase == 0` reads `preflight-{agent}.md` — those files don't exist under the new protocol, so the live-streaming card for in-flight Phase 0 rounds shows an empty body. |

This spec closes all nine gaps with surgical, structurally-mirrored changes — every new code path is a direct copy of the existing phase-2/phase-4 path with the phase number swapped and the left-pane source pointed at `brief.md` (for round 1) or the other agent's prior phase-0 turn (round ≥ 2).

The `artifactIdFromItem` helper at [`run-detail.jsx:3740`](src/dual_research/ui/static/run-detail.jsx) already mints `phase0.${agent}.r${round}` IDs and `displayNameForItem` already resolves them through the artifact registry — both are forward-compatible. The artifact registry's `phase0.{agent}.r{N}` display names will pick up automatically.

---

## 2. Proposed change

### 2.1 Backend — events (G1)

**Add `Phase0RoundComplete` event** in [`src/dual_research/events/types.py`](src/dual_research/events/types.py) mirroring `Phase2RoundComplete`'s minimal-marker shape (the per-category counter fields default to `None` per spec 0115's new-protocol convention — counters flow via `ItemRaised` / `ItemTransitioned`):

```python
@dataclass(frozen=True, kw_only=True)
class Phase0RoundComplete(Event):
    """Phase 0 round marker event (spec 0135).

    Mirrors the Phase 2 / Phase 4 round-complete shape. Counter fields
    default to ``None`` and are not populated on new-protocol runs — the
    UI reads per-category data from ``ItemRaised`` / ``ItemTransitioned``
    just like phases 2 and 4 do since spec 0115.
    """

    round: int
    agreed: bool
    claude_status: str | None = None
    openai_status: str | None = None
    kind: str = "phase0_round_complete"
```

Export it from [`events/__init__.py`](src/dual_research/events/__init__.py).

**Emit it from `_publish_legacy_round_complete`** at [`dr_run.py:412-442`](src/dual_research/orchestrator/dr_run.py): add a `phase_int == 0` branch that publishes `Phase0RoundComplete(round=..., agreed=..., claude_status=..., openai_status=...)`. Remove the `# Phase 0 has no per-round event in the legacy schema.` comment.

### 2.2 Backend — round-keyed Phase 0 stats + review items (G2 + G3 + G4)

**Change `PhaseStats.phase0` shape** in [`src/dual_research/ui/models.py:496`](src/dual_research/ui/models.py) from:

```python
phase0: dict[str, TurnStats] = field(default_factory=dict)
```

to:

```python
phase0: dict[int, dict[str, TurnStats]] = field(default_factory=dict)
```

Update the docstring above (`phase0 and phase1 are single-shot per-agent`) to reflect that phase 0 is now round-keyed under the new protocol.

**Aggregator changes** in [`src/dual_research/ui/aggregator.py`](src/dual_research/ui/aggregator.py):
- `_on_round_complete` (line 817): the existing handler already updates `run.round.current` and ignores the rest; no change needed there for the phase-0 case beyond ensuring the dispatch at line 242 catches `phase0_round_complete` too.
- Dispatch table at line 242: change `if kind in ("phase2_round_complete", "phase4_round_complete"):` to include `phase0_round_complete`.
- Wherever per-turn stats land on `run.phase_stats.phase0` (search for `phase_stats.phase0` writes), key them by `(round, agent_ui)` — same shape used for phase 2/4. The round is available on the `turn_ended` event's `label` (`phase0-r{N}-{agent}`) or via the in-flight round counter.
- `_read_phase_review_items` (line 1317): change the loop on line 1450 from `for phase_n in (2, 4):` to `for phase_n in (0, 2, 4):`. The `_resolve_prior_blocks` helper (line 1391) needs a `phase_n == 0` branch: round 1 → `brief.md`; round ≥ 2 → `phase0/round-{R-1:02d}-{other_be}.md`. Bucket key becomes `phase0_round{R}_<agent>` (same convention as phase 2/4).

**Backward compat (legacy `preflight-{agent}.md` runs)**: pre-0114 runs only have `phase0/preflight-claude.md` + `phase0/preflight-openai.md` and no `round-NN-*.md` files. The new `_read_phase_review_items` loop won't match those (the regex `_ROUND_FILE_RE` only matches `round-NN-*.md`), so legacy transcripts simply contribute no `phase0_round*` buckets and the FE falls back to the legacy two-card layout (see § 2.5). Per-agent legacy `phase_stats.phase0` reads need to remain readable; expose a small migration helper that returns `phase0.get(round) or phase0.get(round_string) or _legacy_per_agent_shape(phase0)` so the camelCased wire payload is robust to both shapes during the version transition.

### 2.3 Backend — phase-summary, token-usage, and live-body wiring (G7 / G8 / G9)

These three gaps live in [`aggregator.py`](src/dual_research/ui/aggregator.py) and each is a one-line predicate change with a small fallback branch.

**G7 — `_read_phase_summaries` (line 1246)**. After the existing `preflight-{agent}.md` block at lines 1258-1261, extend the Phase 0 pass so it also enumerates `phase0/round-NN-*.md` files using `_ROUND_FILE_RE`:

```python
# Phase 0 — preflight critiques (legacy single-shot, one per agent).
for agent in ("claude", "openai"):
    path = session_dir / "phase0" / f"preflight-{agent}.md"
    _maybe_set_summary(out, f"phase0_{_ui_agent(agent)}", path)

# Phase 0 — multi-round critiques (new protocol, spec 0114). Same loop
# shape as Phase 2 / Phase 4 below — extracted into the (0, 2, 4) loop
# in the refactor or repeated inline if that loop is left untouched.
for phase in (0, 2, 4):
    phase_dir = session_dir / f"phase{phase}"
    if not phase_dir.exists():
        continue
    for entry in sorted(phase_dir.iterdir()):
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        if ".malformed" in entry.name:
            continue
        m = _ROUND_FILE_RE.match(entry.name)
        if not m:
            continue
        round_n = int(m.group(1))
        agent = m.group(2)
        key = f"phase{phase}_round{round_n}_{_ui_agent(agent)}"
        _maybe_set_summary(out, key, entry)
```

The collapsed-round-card TL;DR now picks up automatically through `attachItemStats`'s existing `sums[`phase${phase}_round${item.round}_${item.agent}`]` lookup at [`live-data.jsx:779`](src/dual_research/ui/static/live-data.jsx#L779) — no FE change needed.

**G8 — `_on_turn_ended` (line 428)**. Change the round-keying predicate from:

```python
if phase_int in (2, 4) and idx > 0:
    key = f"phase{phase_int}_round{idx}_{ag}"
else:
    key = f"phase{phase_int}_{ag}"
```

to:

```python
if phase_int in (0, 2, 4) and idx > 0:
    key = f"phase{phase_int}_round{idx}_{ag}"
else:
    key = f"phase{phase_int}_{ag}"
```

`_round_index_from_label` at line 1137 already extracts the round from new-protocol labels (`phase0-r{N}-{agent}`) and returns 0 for legacy labels (`phase0-{agent}`) — so legacy single-shot runs continue to land in the `phase0_<agent>` key (no change in behaviour); new-protocol multi-round runs land in `phase0_round{R}_<agent>` keys, which the Consumption tab consumes through the same join it already runs for Phase 2 / Phase 4.

**G9 — `_populate_current_bodies` (line 1175-1178)**. Replace the Phase 0 branch:

```python
if run.phase == 0:
    # Phase 0: each agent's preflight critique.
    _set_body_if_present(run, "claude", session_dir / "phase0" / "preflight-claude.md", kind="thinking")
    _set_body_if_present(run, "gpt", session_dir / "phase0" / "preflight-openai.md", kind="thinking")
```

with the round-aware version (same shape as the existing Phase 2 / Phase 4 branches at lines 1182-1185 / 1197-1200):

```python
if run.phase == 0:
    rnd = _latest_round_for(session_dir, 0)
    if rnd is not None and rnd > 0:
        _set_body_if_present(run, "claude", session_dir / "phase0" / f"round-{rnd:02d}-claude.md", kind="thinking", index=rnd)
        _set_body_if_present(run, "gpt", session_dir / "phase0" / f"round-{rnd:02d}-openai.md", kind="thinking", index=rnd)
    else:
        # Legacy single-shot fallback (pre-0114 transcripts).
        _set_body_if_present(run, "claude", session_dir / "phase0" / "preflight-claude.md", kind="thinking")
        _set_body_if_present(run, "gpt", session_dir / "phase0" / "preflight-openai.md", kind="thinking")
```

`_latest_round_for` (line 1107) is phase-agnostic and works for phase 0 without modification. `Turn.kind = "thinking"` stays the same — that's the `AgentStrip`'s status pill, independent of the timeline card kind (which is `turn` / `turn-live` set in `buildLiveTimeline`).

### 2.4 Backend — Phase 0 ledger projection (G5)

In [`src/dual_research/ui/item_projection.py:358`](src/dual_research/ui/item_projection.py), change:

```python
out: dict[int, list[dict]] = {2: [], 4: []}
```

to:

```python
out: dict[int, list[dict]] = {0: [], 2: [], 4: []}
```

Drop the stale "Phase 0 ledger is not yet surfaced" comment. Update the docstring to say phase 0 is now surfaced.

Every `Item` with `item.phase == 0` already projects through `_item_to_ledger_entry` correctly (the helper doesn't gate on phase). The FE's `phase_ledgers[0]` will then carry the Phase-0 ledger entries in the same shape as `phase_ledgers[2]` / `phase_ledgers[4]`, and `computeChipDeltas` picks them up automatically.

### 2.5 Frontend — multi-round timeline cards (G6)

In [`src/dual_research/ui/static/live-data.jsx:486-508`](src/dual_research/ui/static/live-data.jsx), replace the current static two-card Phase 0 block with a **round-enumerating** branch shaped identically to the Phase 2 branch at lines 537-601. Sketch (final exact form modelled on the Phase 2 code at lines 537-601 — same `cur` / `p0StatsCount` / live-vs-completed branch logic):

```jsx
items.push({ id: 'phase-0', kind: 'phase-divider', phaseId: 0, duration: run.phaseTimings?.['0'] });
items.push({ id: 'input', kind: 'input', filePath: 'brief.md', topic: run.topic, turnKey: 'input' });

const p0StatsCount = Object.keys(run.phaseStats?.phase0 || {}).length;
const hasRoundFiles = p0StatsCount > 0;

if (hasRoundFiles) {
  // ── New-protocol multi-round timeline ────────────────────────────
  const cur = ph === 0 ? (run.round?.current ?? 0) : 0;
  const p0Rounds = ph === 0
    ? (st === 'running' ? cur : Math.max(cur, p0StatsCount))
    : p0StatsCount;

  // phase divider gains a round count, exact same shape as Phase 2/4
  items[items.length - 2].extra = `${p0Rounds} round${p0Rounds === 1 ? '' : 's'}`;

  if (ph === 0 && (st === 'running' || st === 'deadlocked' || st === 'errored')) {
    const completedThrough = st === 'running'
      ? Math.max(0, cur - 1)
      : Math.max(cur, p0StatsCount);
    for (let r = 1; r <= completedThrough; r++) {
      items.push({ id: `p0-r${r}-claude`, kind: 'turn', agent: 'claude', round: r, index: r,
                   filePath: fileForRound(0, r, 'claude'),
                   turnKey: `phase0_round${r}_claude` });
      items.push({ id: `p0-r${r}-gpt`,    kind: 'turn', agent: 'gpt',    round: r, index: r,
                   filePath: fileForRound(0, r, 'gpt'),
                   turnKey: `phase0_round${r}_gpt` });
    }
    if (cur > 0 && st === 'running') {
      items.push({ id: `p0-r${cur}-claude-live`, kind: 'turn-live', agent: 'claude',
                   round: cur, index: cur, live: true,
                   status: run.agents?.claude?.status,
                   body: run.agents?.claude?.currentTurn?.body || '',
                   filePath: fileForRound(0, cur, 'claude'),
                   turnKey: `phase0_round${cur}_claude` });
      items.push({ id: `p0-r${cur}-gpt-live`, kind: 'turn-live', agent: 'gpt',
                   round: cur, index: cur, live: true,
                   status: run.agents?.gpt?.status,
                   body: run.agents?.gpt?.currentTurn?.body || '',
                   filePath: fileForRound(0, cur, 'gpt'),
                   turnKey: `phase0_round${cur}_gpt` });
    }
  } else if (ph >= 1) {
    for (let r = 1; r <= p0Rounds; r++) {
      items.push({ id: `p0-r${r}-claude`, kind: 'turn', agent: 'claude', round: r, index: r,
                   filePath: fileForRound(0, r, 'claude'),
                   turnKey: `phase0_round${r}_claude` });
      items.push({ id: `p0-r${r}-gpt`,    kind: 'turn', agent: 'gpt',    round: r, index: r,
                   filePath: fileForRound(0, r, 'gpt'),
                   turnKey: `phase0_round${r}_gpt` });
    }
  }
} else if (ph >= 1) {
  // ── Legacy fallback (pre-0114 runs with only preflight-{agent}.md) ──
  items.push({ id: 'p0-claude', kind: 'preflight', agent: 'claude',
               filePath: 'phase0/preflight-claude.md',
               stats: run.phaseStats?.phase0?.claude || null,
               statsPhase: 0,
               summary: run.phaseSummaries?.phase0_claude || '',
               turnKey: 'phase0_claude' });
  items.push({ id: 'p0-gpt', kind: 'preflight', agent: 'gpt',
               filePath: 'phase0/preflight-openai.md',
               stats: run.phaseStats?.phase0?.gpt || null,
               statsPhase: 0,
               summary: run.phaseSummaries?.phase0_gpt || '',
               turnKey: 'phase0_gpt' });
}
```

**`fileForRound(0, r, ui_agent)`** already produces `phase0/round-NN-<be>.md` correctly — no change needed (the helper is phase-agnostic).

**`attachItemStats`** at [`live-data.jsx:733`](src/dual_research/ui/static/live-data.jsx#L733): the existing `turn` / `turn-live` branch at lines 771-786 derives `statsPhase` by inspecting `item.index` (`rev-*` prefix → 4 else 2). Add a phase-0 disambiguator: if `item.id` matches `^p0-r` (or equivalently `item.statsPhase === 0` already set by the timeline builder), bucket lookup goes to `ps.phase0?.[round]?.[agent]`. The cleanest form is to stamp `statsPhase: 0` directly on the item in the builder (already done in the sketch above via the implicit `kind: 'turn'` cards — we'll add `statsPhase: 0` explicitly so the existing `phase = (item.round && String(item.index).startsWith('rev-')) ? 4 : 2` ternary doesn't misclassify them as phase 2).

**Mid-spec correction to the sketch above:** stamp `statsPhase: 0` on every emitted Phase-0 turn card so `attachItemStats` routes correctly. The Phase 2 cards above don't stamp it because the ternary derives 2 from the `rev-*`-absence; we need the explicit stamp on Phase 0 to override that default.

### 2.6 Frontend — side-by-side modal routing (G6)

In [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx):

**`ArtifactModal`** at line 3755-3775: extend the `NegotiateReviewModal` route from `statsPhase === 2 || statsPhase === 4` to `statsPhase === 0 || statsPhase === 2 || statsPhase === 4`. The `preflight` route stays as the legacy fallback path for pre-0114 runs.

**`priorContentPathFor`** at line 4756: add a `phase === 0` case at the top:

```js
if (phase === 0) {
  if (round <= 1) return 'brief.md';
  const beAgent = otherUiAgent === 'gpt' ? 'openai' : otherUiAgent;
  const rr = String(round - 1).padStart(2, '0');
  return `phase0/round-${rr}-${beAgent}.md`;
}
```

**`leftPaneTabsFor`** at line 4781: add a `phase === 0` branch:

```js
if (phase === 0) {
  const tabs = [];
  if (round >= 2) {
    const rr = String(round - 1).padStart(2, '0');
    tabs.push({ id: 'priorTurn', label: "Other's prior turn",
                path: `phase0/round-${rr}-${otherBe}.md` });
  }
  tabs.push({ id: 'brief', label: 'Brief', path: 'brief.md' });
  return tabs;
}
```

**`reviewItemsFor`** at line 4821: already keys generically off `item.statsPhase` + `item.round` + `item.agent` — `phase${phase}Round${item.round}${cap(item.agent)}` → `phase0Round{R}Claude` / `phase0Round{R}Gpt`. Picks up the new `phase0_round*` buckets the aggregator now produces automatically once § 2.2 lands. No change.

### 2.7 Frontend — sentiment + chip composers for multi-round Phase 0

**`composeGist`** at [`run-detail.jsx:3205`](src/dual_research/ui/static/run-detail.jsx#L3205): the existing `item.kind === 'preflight'` branch (3228-3242) stays for the legacy fallback. Add a `statsPhase === 0` branch (matching the `phase === 2` pattern at 3250-3273) that reports `STATUS`, `openQuestions`, `blocking`, `fsd` chips for multi-round Phase 0 turns. The protocol's Phase 0 turn schema emits the same `Stats` block shape (`BRIEF_OK` / `BRIEF_NEEDS_INPUT` / `NEGOTIATING` / `AGREED`), so the chip composer can reuse the Phase 2 sentence-builder verbatim with a Phase-0 status vocabulary.

**`composeSentiment`** at line 3328: same surgical addition — a `statsPhase === 0 && item.round` branch that pulls from `run.questions`, `run.disagreements`, `run.issues`, `run.comments` filtered to `(phase=0, raised_by=agent, raised_round=round)` and assembles the two-to-three-sentence paragraph in the same shape as the existing Phase 2 branch.

The existing per-agent preflight branch at lines 3346-3367 stays unchanged for the legacy fallback (legacy items still arrive as `kind === 'preflight'`; new items arrive as `kind === 'turn'` with `statsPhase: 0`).

### 2.8 Chip rendering / critique pane

The chip rendering on each timeline card and the critique pane's per-phase filters already use `item.statsPhase` + `phase_ledgers[phase]` as their source of truth (verified in [`run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) chip pipelines and the critique pane around line 6086). With § 2.3 making `phase_ledgers[0]` non-empty and § 2.4 stamping `statsPhase: 0` on the new cards, the chip system picks up Phase 0 automatically. **No changes required** — verify in § 4.

### 2.9 Subtitle copy for the side-by-side modal

[`NegotiateReviewModal`](src/dual_research/ui/static/run-detail.jsx#L3971) has a hard-coded subtitle ternary:

```js
const subtitle = item.statsPhase === 4
  ? `reviewing the converged document`
  : `reviewing ${otherAgent === 'claude' ? 'Claude' : 'GPT'}'s prior content`;
```

Extend to a three-way ternary so Phase 0 reads correctly — *"critiquing the brief"* (R1) or *"responding to ${other}'s prior critique"* (R≥2). Concretely:

```js
let subtitle;
if (item.statsPhase === 4) subtitle = 'reviewing the converged document';
else if (item.statsPhase === 0) {
  subtitle = (Number(item.round) || 1) === 1
    ? 'critiquing the brief'
    : `responding to ${otherAgent === 'claude' ? 'Claude' : 'GPT'}'s prior critique`;
} else subtitle = `reviewing ${otherAgent === 'claude' ? 'Claude' : 'GPT'}'s prior content`;
```

---

## 3. Out of scope

- **Protocol changes.** No new prompt sections, no new turn-schema sections, no new ledger states. Every byte the new surfaces need is already emitted by spec 0114's protocol — this is pure downstream wiring.
- **Removal of the legacy `PreflightResponseModal` codepath.** Pre-0114 runs (legacy `phase0/preflight-{agent}.md` files, single-keyed `PhaseStats.phase0`) continue to render via the existing two-card + single-pane modal layout. The new round-card path activates only when `run.phaseStats.phase0` is round-keyed (i.e. has integer keys). A future spec can decide to retire the legacy path once all hosted-deployment transcripts are post-0114; that's a deletion-only follow-up, not part of this scope.
- **The brief "input" card.** Stays exactly as today — the leftmost card in the Phase 0 section, opening `InputBriefModal` on click. The new round cards sit to the right of it.
- **Phase 1 plan-draft cards.** Phase 1 also goes through `_drive_interaction_phase`-free (it's not an interaction phase — agents write independently). Stays single-shot. Unrelated to this spec.
- **Critique-pane Phase 0 filter chip** — already exists (the critique pane's filter row carries every phase the items came from). Spec 0119 / 0120 plumbing handles it.
- **Cross-phase carry-forward**. The `agreed_interpretation` artefact + `carry_forward_phase0` payload already flow through `ctx.state` correctly — no change. The new cards make the round-by-round path **visible**; the carry-forward semantics are unchanged.
- **Onboarding tour / How-it-works copy.** May want a follow-up to reflect the new Phase 0 surface; out of scope here.

---

## 4. Test plan

**Backend unit tests:**
- [ ] New `Phase0RoundComplete` event class — `dataclass-asdict` round-trip + dict keys match the expected shape.
- [ ] `_publish_legacy_round_complete` emits `Phase0RoundComplete` when `phase_int == 0` with correct `round` / `agreed` / `claude_status` / `openai_status` payload (extend existing tests for the phase 2/4 cases).
- [ ] `_read_phase_review_items` produces `phase0_round{R}_<agent>` buckets when given a session dir with `phase0/round-NN-<agent>.md` files. Empty-bucket case (file exists but contains no RAISE blocks) and populated-bucket case both covered.
- [ ] `_resolve_prior_blocks(phase_n=0, round_n=1, agent_be="claude")` returns blocks from `brief.md`; `round_n=2` returns blocks from `phase0/round-01-openai.md` (other agent's prior turn).
- [ ] `project_phase_ledgers` returns a 3-key dict (`{0, 2, 4}`) and `out[0]` contains LedgerEntry-shaped dicts for every Phase 0 item in the input bundle.
- [ ] `_read_phase_summaries` populates `phase0_round{R}_<agent>` keys for every `phase0/round-NN-*.md` that carries a `## Summary` section; legacy `phase0_<agent>` keys still populate from `preflight-{agent}.md` files when present.
- [ ] `_on_turn_ended` keys multi-round Phase 0 token usage as `phase0_round{R}_<agent>` (new fixture) while legacy single-shot Phase 0 transcripts continue to key as `phase0_<agent>` (legacy fixture).
- [ ] `_populate_current_bodies(run, session_dir)` for `run.phase == 0` reads the latest `phase0/round-NN-{agent}.md` body when round files exist; falls back to `preflight-{agent}.md` otherwise.

**Backend integration tests:**
- [ ] End-to-end `run_dr_phase0` run with `tests/integration/test_phase0_*` fixtures: assert the transcript contains one `phase0_round_complete` event per round, that `run.phase_stats.phase0` is round-keyed (`{1: {claude: ..., gpt: ...}, 2: {...}, ...}`), and that `_read_phase_review_items` populates the expected buckets.
- [ ] Legacy single-shot Phase 0 transcript (pre-0114 fixture) replays without errors and produces no `phase0_round*` buckets — the `_legacy_per_agent_shape` fallback keeps `run.phase_stats.phase0` as a per-agent dict consumable by the legacy FE branch.

**Frontend manual + Playwright (where present):**
- [ ] Load a multi-round Phase 0 run; timeline shows `1 + 2N` Phase 0 cards (1 brief + 2 per round) with a phase divider reading e.g. `"3 rounds"`.
- [ ] Click any Phase 0 round card → `NegotiateReviewModal` opens with:
  - Left pane: `brief.md` (R1) or other agent's prior round file (R≥2). Tabs row offers `Brief` (always) + `Other's prior turn` (R≥2).
  - Right pane: review-card stacks for questions / disagreements / issues / comments raised by this agent in this round; clicking a card scrolls + flashes the left pane.
  - Subtitle reads *"critiquing the brief"* (R1) or *"responding to {other}'s prior critique"* (R≥2).
- [ ] Live in-flight Phase 0 round: while phase=0 + status=running, the in-flight round renders as `turn-live` cards with streaming body; previous rounds render as completed `turn` cards.
- [ ] Round scrubber inside the modal walks through `1..N` Phase 0 rounds for the same agent (the `roundsForPhase` builder reuses `buildTimeline` + filters on `statsPhase === item.statsPhase` — already correct, just needs Phase 0 cards on the timeline to populate).
- [ ] Critique pane Phase 0 filter chip surfaces items raised in any Phase 0 round and clicking a chip jumps to the corresponding timeline card.
- [ ] Consumption tab shows one card per `(round, agent)` for Phase 0 (matching the Phase 2 / Phase 4 layout) instead of two collapsed per-agent cards.
- [ ] Live in-flight Phase 0 round: the in-flight round's body streams into `agents.{agent}.currentTurn.body` and renders inside the live timeline card (covers G9).
- [ ] Per-round Phase 0 round cards show TL;DR text from each turn's `## Summary` (covers G7).
- [ ] Legacy single-shot Phase 0 fixture (pre-0114 transcript): timeline falls back to the two `preflight` cards; clicking opens the existing single-pane `PreflightResponseModal`. Consumption tab keeps the two per-agent cards. `currentTurn.body` populates from `preflight-{agent}.md`. No regression on legacy display.

**Wire-format compat:**
- [ ] `live-data` / aggregator handles both shapes of `phaseStats.phase0` (legacy per-agent + new round-keyed) for at least one minor version. Old hosted-deployment transcripts must continue to render in the new UI build during a rollover window.

---

## 5. Risks

- **`PhaseStats.phase0` shape change is a wire-format break.** Mitigated by the `_legacy_per_agent_shape` fallback in `attachItemStats` and the aggregator: if `phase0` carries string keys (legacy: `"claude"`, `"gpt"`), treat as the single per-agent shape and fall through to the legacy two-card layout. If `phase0` carries integer keys (new: `1`, `2`, …), treat as round-keyed. The migration window is one minor version — after 1.8.0 ships, the next major / minor can drop the legacy shape if hosted-deployment transcripts have rotated past spec 0114 (planned spec note in the eventual deletion follow-up).
- **The camelCased server pass on the wire.** `_to_camel` walks every string dict key; integer keys are left intact. New round-keyed `phase0` carries integer keys exactly like `phase2` / `phase4` already do — same machinery, no new risk.
- **`statsPhase: 0` collisions with falsy-check guards.** A handful of FE branches treat `item.statsPhase` as truthy (`if (statsPhase) {…}`). Audit and migrate to explicit `statsPhase != null` checks where `statsPhase === 0` is a valid value. The candidate list is small (the `composeGist` / `composeSentiment` switches above; the chip composer; `artifactIdFromItem`).
- **Side-by-side modal performance with multi-round Phase 0.** The modal pre-resolves anchors against the left-pane document. For R≥2 the left pane is a prior-round Phase 0 file, which is bounded (~12 KB max under current cap policy). No new perf risk — same as Phase 2.
- **Mid-flight rollback.** If the new round-card surface ships broken, the legacy two-card path is gated on the absence of round-keyed `phaseStats.phase0` and the absence of `phase0/round-NN-*.md` files. Reverting the FE alone (server still emits the new shape) renders the legacy view; reverting the backend alone (FE still expects round-keyed shape) renders an empty Phase 0 section. We'll deploy backend first, verify, then FE — same order spec 0115 used.

---

## 6. Open questions

- **Should the brief "input" card grow a counter chip** showing total Phase 0 items raised across all rounds? The phase divider already exposes round count; the input card is the natural anchor for an aggregate items count. **Default: defer to a follow-up** — out of scope for this spec since it changes the input-card visual and not the round-card surface.
- **Do we want a Phase 0 closeout-round indicator on the round divider?** Phase 2 / Phase 4 don't have one today (the closeout is visible via the `CloseoutUrged` event log in the inspector). **Default: match Phase 2 / Phase 4 behaviour — no closeout indicator on the divider.**
- **Should the legacy `PreflightResponseModal` be retired in the same spec?** Could simplify the FE by dropping the dual code path. **Default: keep for one version (1.8.0); schedule retirement once hosted transcripts confirm zero pre-0114 runs in production.**
