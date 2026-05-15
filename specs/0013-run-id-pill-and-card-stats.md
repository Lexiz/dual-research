---
spec: 0013
title: Run-id pill and timeline card stats
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.14.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/13"
---

# Spec 0013 — Run-id pill and timeline card stats

## Context

Two final polish items after spec 0012:

1. **Run-id cell in the All-runs list is still visually noisy.** The current two-line stack (4-char id on top, `HH:MM · slug-suffix…` below) makes the leftmost column dominate the row even though the secondary info is rarely consulted. The user wants a compact pill — same visual weight as the `StatusBadge` next to it — that shows just the 4-char id and surfaces the rest in a hover tooltip.

2. **Timeline cards are visually thin.** Each Phase 1 plan-draft row, Phase 2 negotiation turn, and Phase 4 review turn currently shows `agent / kind-label / round-tag` and lots of empty space on the right. The protocol already produces structured fields (`OPEN_QUESTIONS`, `BLOCKING_DISAGREEMENTS`, `FINAL_SURFACED_DISAGREEMENTS`, `OPEN_ISSUES`, `STATUS`) on every turn — these are exactly the "what came out of this conversation step" data points the user wants surfaced inline. Adding small mono chips for the meaningful subset makes the timeline tell a story at a glance without sending the reader into the body.

## Proposed change

### Part 1 — Run-id pill

Replace the two-line stacked cell in `run-list.jsx::RunRow` with a single pill chip that mirrors `StatusBadge`'s shape:

```
┌────────┐
│  009f  │   <- mono, 11.5px, fg-1, JetBrains Mono, pill background bg-2 / border-1
└────────┘
```

- 4-char `displayId` only on screen.
- Hover tooltip (browser `title=`) carries the structured detail: `full session-dir name · started HH:MM · slug`.
- Column width drops from 110px to 80px (the pill needs much less room than the stack).
- No secondary line, no slug truncation, no clipped time — those just disappear from the visual; nothing is lost (the tooltip + the run-detail top bar both still expose the full id).
- Apply the same pill style to the `RunIdChip` already in `run-detail.jsx::TopBar` so the two surfaces are visually consistent (the detail-view chip stays clickable-to-copy; the list-view chip is decorative because the whole row is the clickable affordance).

### Part 2 — Inline stats on timeline cards

Surface per-turn protocol fields on the relevant timeline rows. Both Phase 1 (plan drafts) and Phase 2/4 (negotiation / review turns) are enriched. Phase 0 (preflight) gets a minimal `OK` / `needs input · N` chip. Phase 3 single-shot draft and Phase 5 final stay as-is.

#### Server side

New module `src/dual_research/ui/turn_stats.py`:

```python
@dataclass
class TurnStats:
    """Parsed protocol fields surfaced on the row header."""
    status: str | None             # NEGOTIATING / AGREED / APPROVED / NOT_APPROVED / etc
    open_questions: int | None     # phase 1 / 2 turns
    open_issues: int | None        # phase 4 turns
    blocking: int | None           # phase 2 BLOCKING_DISAGREEMENTS
    fsd: int | None                # phase 2/4 FINAL_SURFACED_DISAGREEMENTS
    brief_issues: int | None       # phase 0 preflight only

def stats_for(session_dir: Path, kind: str, **kw) -> TurnStats | None:
    """Read the appropriate round/draft/preflight file and parse via
    protocol.parse.parse_turn (or parse_preflight_turn). Returns None
    if the file is absent."""
```

Lookup paths by kind:

| kind | path |
|---|---|
| `phase0` (agent) | `phase0/preflight-{agent}.md` |
| `phase1` (agent) | `phase1/draft-{agent}.md` |
| `phase2` (round, agent) | `phase2/round-{NN}-{agent}.md` |
| `phase4` (round, agent) | `phase4/round-{NN}-{agent}.md` |

The aggregator (`load_run_snapshot`) now also builds `Run.phase_stats`:

```python
@dataclass
class Run:
    ...existing fields...
    phase_stats: PhaseStats = field(default_factory=PhaseStats)

@dataclass
class PhaseStats:
    phase0: dict[str, TurnStats]               # {ui_agent: stats}
    phase1: dict[str, TurnStats]               # {ui_agent: stats}
    phase2: dict[int, dict[str, TurnStats]]    # {round: {ui_agent: stats}}
    phase4: dict[int, dict[str, TurnStats]]    # {round: {ui_agent: stats}}
```

The server's snake_case → camelCase translator already in `server.py` covers this without changes.

#### Client side

`live-data.jsx::buildLiveTimeline` enriches each Phase 0/1/2/4 timeline item with a `stats` field pulled from `run.phaseStats`. For Phase 1 items, `stats = run.phaseStats.phase1[agent]`; for Phase 2/4 items, `stats = run.phaseStats.phase{N}[round][agent]`.

`run-detail.jsx::ArtifactHeader` renders a small inline `<StatsChips stats={item.stats}/>` next to the right-aligned round tag (replacing the current `r3`-only placeholder for live data). The chip set is phase-aware:

| Card kind | Chips |
|---|---|
| `plan` / `plan-live` (Phase 1) | `OQ {open_questions}` · `BD {blocking}` if > 0 |
| `turn` / `turn-live` (Phase 2) | `OQ {open_questions}` · `BD {blocking}` · status-pill if `AGREED` / `NOT_AGREED` |
| `turn` / `turn-live` (Phase 4) | `OI {open_issues}` · status-pill `APPROVED` / `NOT_APPROVED` |
| `input` (Phase 0) | preflight chips: `OK` or `needs input · {brief_issues}` |
| `doc` / `doc-live` (Phase 3 / final) | unchanged |

Each chip is a tiny mono span — fg-3 by default; the status-pill uses the ok/warn/info palette. Numeric chips render `OQ 0` (not `OQ —`) when the file was parsed and the value is zero; missing chips render nothing.

Compact visual budget: the chip row is at most ~140 px wide; it sits between the kind label and the existing right-side `r{N}` tag. Cards stay one line tall.

### Files touched

Backend:

- `src/dual_research/ui/models.py` — new `TurnStats`, `PhaseStats` dataclasses, attach to `Run`.
- `src/dual_research/ui/turn_stats.py` (new) — file-aware parse wrapper around `protocol.parse`.
- `src/dual_research/ui/aggregator.py` — call `turn_stats.build_phase_stats(session_dir)` inside `load_run_snapshot`.
- `tests/ui/test_turn_stats.py` (new) — synthetic + fixture goldens.
- `tests/ui/test_aggregator.py` — assert `phaseStats` populated on the fixture run.

UI:

- `src/dual_research/ui/static/run-list.jsx` — RunRow id-pill replacement; column 110→80px.
- `src/dual_research/ui/static/run-detail.jsx` — `StatsChips` component, `ArtifactHeader` integration, `RunIdChip` style tightened to match the list-view pill.
- `src/dual_research/ui/static/live-data.jsx` — `buildLiveTimeline` reads `phaseStats` and attaches `item.stats` per item.

### CHANGELOG + version bump

`0.13.0 → 0.14.0` (MINOR — new data surfaced + small UX redesign).

## Out of scope

- Backend changes to the orchestrator. `parse_turn` is reused as-is.
- New event types. The aggregator continues to read from disk (transcript + round files).
- A "story view" that strings the chips into a sentence — chips for now; iterate later if useful.
- Phase 3 / Phase 5 stats. Single-shot drafts don't surface conversational metadata.
- Per-card cost or token counts (still unavailable; need a backend change to thread per-turn cost through to the aggregator).
- Mobile-width row collapse — same posture as spec 0012.

## Test plan

- [ ] All 200 existing Python tests still pass
- [ ] New tests under `tests/ui/test_turn_stats.py` (~8 cases) pass — parse open-questions / blocking / fsd from synthetic and fixture round files; gracefully return `None` when a file is missing
- [ ] `tests/ui/test_aggregator.py` extended — fixture run `cache-multi-round` populates `phase_stats.phase1.claude.open_questions` to a non-None number; `phase_stats.phase2[1].claude.status == "NEGOTIATING"` (or similar)
- [ ] Live verification at 1440 × 900:
  - All-runs list shows compact id pills (e.g. `009f`, `48b1`) with hover tooltips
  - Run detail Phase 1 cards show `OQ N` chips
  - Phase 2 turn cards show `OQ N · BD M` chips with the status pill on `AGREED` rounds
  - Phase 4 turn cards show `OI N` chip + `APPROVED` pill on the final review round
  - Phase 0 Input row shows `OK` or the `needs input` chip
- [ ] Screenshots of: list with id pills, detail view at Phase 1 (showing chips), detail view at Phase 2 mid-round, detail view at Phase 4 final approval

## Risks

- **Parse misses on deviant agent output.** `parse_turn` already tolerates a lot of leading punctuation / emphasis; if a model omits a marker entirely we surface `None` for that field and the chip just doesn't render. Worst case: a row shows fewer chips than its neighbours — degrades gracefully.
- **Visual crowding on narrow viewports.** Mitigated by capping the chip row at ~140 px and using mono 10.5 px — same size class as the existing `r3` tag. If a row still overflows at 1024 px the chips will wrap below; acceptable.
- **`phase_stats` cost.** Reads up to ~12 small markdown files per run snapshot. Each file parse is sub-millisecond. The aggregator's snapshot build stays well under 50 ms even on the largest fixture runs.

## Open questions

None.
