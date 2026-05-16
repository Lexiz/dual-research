---
spec: 0033
title: Inputs foundation — universal Input view, Phase 0 split, two-row live header
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.31.0
created: 2026-05-16
pr: "https://github.com/Lexiz/dual-research/pull/35"
---

# Spec 0033 — Inputs foundation + two-row live header

## Context

The first full end-to-end test run (post spec 0032) surfaced one
unifying gap: **what actually went into each model at each step is
invisible to the user.** The Consumption tab tells them how much
token mass went in; the timeline tells them what came out; nothing
tells them what the model was actually shown. That makes the whole
pipeline feel like a black box at exactly the place where the user
most wants to audit it — before forming an opinion on a turn's
output.

The same run also showed two adjacent gaps that share the "make
the input legible" theme and are cheapest to land together:

1. **Phase 0 is rendered as a single card.** It shows "Both agents
   found brief OK to proceed" or an issue count, but the user
   cannot see the actual brief response from each model. The
   compact card collapses two distinct artefacts (input + per-model
   critique) into one slot.

2. **The header's second row is empty of operational signal.** The
   top row carries `topic + cost + status`; the second row carries
   metadata (`started · drafter · elapsed · round`) and a phase-dot
   strip. Live activity — *who is on turn, doing what, against
   whom* — lives in a tiny "N live" chip in the pane toolbar below.
   At a glance the user cannot answer "what is each model doing
   right now?" without reading the timeline.

This spec is the foundation for the two specs that follow (0034
critique navigation, 0035 consumption rework). It establishes the
data flow for **what every model saw at every step**, exposes it
through a universal **Input** view that plugs into every full-view
modal, splits Phase 0 into the three cards it conceptually is, and
elevates per-agent live status into the run header so the chrome
itself answers "where are we right now?"

Prior context: spec 0030 already piped per-piece *sizes* through
`TurnEnded.prompt_pieces` for the Consumption tab. The actual prompt
*text* never flowed — only the integer token counts per piece. This
spec is the natural extension: emit the strings too, indexed by the
same Tk-vocab keys, so the UI can render them as the inputs to each
turn.

## Design decisions

| # | Decision | One-liner |
|---|----------|-----------|
| D1 | **Per-turn input bundles are emitted on a new `TurnInputs` event, not bolted onto `TurnEnded`.** | `TurnEnded` already carries `prompt_pieces` (sizes). Adding the *full text* of every piece to every `TurnEnded` would balloon the event payload by ~the size of the prompt itself. A separate `TurnInputs` event lets the aggregator persist input bundles only when the UI is going to render them, and lets retention/replay treat them differently from cost-of-record `TurnEnded` data. |
| D2 | **Input bundles use the same Tk-vocab keys as spec 0030 (`brief`, `d1`, `d2`, `plan`, `hist`, `draft`, `histp`) plus a fixed `system` key for the system/instruction prompt.** | Same vocabulary across sizes + text means no key-mapping logic anywhere. `system` is added because spec 0030's pieces never included the instruction text itself (it was implicitly part of the prompt total but not labelled). The Input view needs to surface it as its own section. |
| D3 | **Bundles are persisted to disk under `session_dir/inputs/<turn-key>.json`, not held in memory.** | An aggregator that holds every prompt's full text in RAM across a long run is wasteful and breaks `--push-while-running` resume semantics. The aggregator records *paths* on `TurnTokenUsage.input_path`; the UI server resolves the file on demand via a new `/api/runs/<id>/inputs/<turn-key>` endpoint. Same lazy-load pattern as markdown bodies (`LazyMarkdownBody`). |
| D4 | **Phase 0 splits into three timeline items: `input` (shared brief), `p0-claude` (Claude's critique), `p0-gpt` (GPT's critique).** | Today's single Phase 0 card conflates "what went in" with "what came back from each model." The split lets each card open its own modal: the input modal shows the brief + system prompts; the per-model modals show that model's BRIEF_OK/BRIEF_NEEDS_INPUT critique. The existing `phase0_<agent>` summaries already populate per-agent — there's no new parsing. |
| D5 | **Every full-view modal gains an Input tab. The tab's content shape varies by phase but its placement and label are uniform.** | Cards conceptually fall into two families: **one-pane** (Phase 0 input, Phase 1 drafts, Phase 3 doc, Phase 5 final) and **side-by-side** (Phase 2 turns, Phase 4 turns — currently `NegotiateReviewModal`). The Input tab lives on the modal's tab strip in both families: as a sibling of Content/Sources/Files in one-pane modals, and as a new tab on the left-pane tab strip in side-by-side modals. Same component (`InputTabContent`); the modal frame decides where it slots. |
| D6 | **`InputTabContent` renders ordered, collapsible sections — one per Tk-key — in protocol-order.** | Order: `system → brief → d1 → d2 → plan → hist → draft → histp`. Each section is independently collapsible (initial state: `system` collapsed because it's the long boilerplate; everything else expanded so the audit-trail content is immediately visible). The section header shows the key's friendly label (same map as `KIND_COLORS.label` from spec 0030) and the byte / token size. Empty pieces render with a "(not used in this turn)" stub instead of being hidden — the user wants to see that, e.g., `plan` had no value in Phase 1, not that it's missing. |
| D7 | **Phase 0 input modal has no "turn key" — its bundle is synthesised, not emitted.** | The brief is loaded from `session_dir/brief.md` (already done by `_read_brief_summary`); the preflight system prompt comes from `protocol/prompts.py::preflight_prompt(brief_content="", agent_name="<placeholder>")` (called with a placeholder to extract the static template, then rendered as the `system` section). One synthesised bundle serves both Phase 0 cards on the Input tab; the per-model critique modals share it. |
| D8 | **Header row 2 is rebuilt around two per-agent status strips.** | Today's row 2: `started · drafter · elapsed · round` (metadata) + `PhaseDots` (state). New row 2: a single agent strip — Claude on top, GPT below — each carrying `[agent icon] [model name] · [tokens·cost badge] │ [status badge with sentence]`. Metadata (started/elapsed/round) moves into a tooltip on the strip's hover. PhaseDots move to a third row, full-width below the agent strips, so the run-level state is still visible at a glance. |
| D9 | **The status badge sentence is a 3–6-word activity phrase, synthesised from `AgentState.status` + `current_turn.kind` + phase context.** | A composer (`composeAgentActivity(agent, run)`) maps `(status, phase, turn.kind, round)` to phrases like `"drafting parallel plan"`, `"responding · round 3"`, `"reviewing Claude's plan"`, `"waiting for GPT"`. When `status === "idle"` and the other agent is live, the phrase becomes `"waiting for <other>"`. When the run is between phases, both go to `"waiting · phase N done"`. No LLM; deterministic switch. |
| D10 | **Conversation / Consumption tabs move from the pane toolbar to the run header's right edge of row 1.** | Promotes them from a secondary control into chrome. Visual treatment matches the existing `AgentLegendChip` border-radius / contrast so they read as siblings of the cost badge. Slight size bump (font 12 → 12.5, padding 3px 12px → 4px 14px) and a 1px accent underline on the active tab. |
| D11 | **Spec 0033 ships behind no flag.** | The Input data flow is new but additive — pre-0033 transcripts simply have no `inputs/` folder and the Input tab renders an empty-state. The header rework is a layout change; no opt-out toggle. We've been shipping layout passes (0023, 0024, 0030) without flags and that pattern has worked. |

## Proposed change

### 1. Emit per-turn input bundles — orchestrator + agents

#### 1a. New `TurnInputs` event

`src/dual_research/events/types.py`:

```python
@dataclass(frozen=True, kw_only=True)
class TurnInputs(Event):
    """Spec 0033 — full per-piece prompt text for a turn.

    Emitted alongside ``TurnStarted`` (NOT ``TurnEnded``) so the UI can
    show what's about to be sent even while the call is in flight. Keys
    match the Tk-vocab from spec 0030; ``system`` is added for the
    static instruction template.

    Empty pieces are present-with-empty-string, not omitted, so the UI
    can render a "not used in this turn" stub uniformly.
    """
    agent: str           # "claude" | "openai" (backend vocab)
    phase: str           # "phase0" | "phase1" | "phase2_round1" | ...
    label: str           # same label as TurnStarted/TurnEnded
    pieces: dict[str, str] = field(default_factory=dict)
    kind: str = "turn_inputs"
```

The seven Tk keys plus `system` — `{"system", "brief", "d1", "d2",
"plan", "hist", "draft", "histp"}` — are the canonical vocabulary.
Phases populate the subset that's actually inlined into their
prompt (matches `prompt_pieces.py`'s `pieces_for_*` functions).

#### 1b. Prompt builders return text bundles

`src/dual_research/protocol/prompts.py` — refactor each
`*_prompt` function to ALSO expose the per-piece source strings. Two
viable shapes; the spec picks (b):

- (a) Function returns a `(text, bundle)` tuple. Breaks every call
  site. Big diff.
- (b) **Add a sibling function** `*_input_bundle(...)` next to
  each `*_prompt(...)`. Returns a `dict[str, str]` with the eight
  Tk-vocab keys (empty string for unused pieces). The
  prompt-building call sites in the orchestrator add one extra
  line: build the bundle, emit `TurnInputs(pieces=bundle)` just
  before invoking the agent.

Picked: **(b)**, because it leaves the prompt-text path
byte-identical to today (no regression risk on agent behaviour)
and makes the bundle composition a separate, individually testable
unit. Bundles for the six existing phases:

| Function | Bundle keys with content |
|----------|-------------------------|
| `preflight_input_bundle(brief)` | `system`, `brief` |
| `research_input_bundle(brief)` | `system`, `brief` |
| `negotiation_round1_input_bundle(brief, own_draft, other_draft)` | `system`, `brief`, `d1`, `d2` |
| `negotiation_turn_input_bundle(brief, own_draft, other_draft, prior_turns)` | `system`, `brief`, `d1`, `d2`, `hist` |
| `drafting_input_bundle(brief, claude_draft, openai_draft, plan, prior_turns)` | `system`, `brief`, `d1`, `d2`, `plan`, `hist` |
| `review_input_bundle(brief, draft, prior_turns)` | `system`, `brief`, `draft`, `histp` |
| `repair_input_bundle(...)` | `system`, plus whatever the repair-prompt actually inlined |
| `force_verbatim_copy_input_bundle(...)` | `system`, `plan` |

The `system` value is the static template portion of each prompt —
everything emitted by the function with the inline-section bodies
substituted out (i.e. `COMMON_PREAMBLE` + the phase's task
instructions + `_OUTPUT_INSTRUCTION`, with placeholders for the
substitutable parts). For Phase 0 the synthesised "input modal"
bundle (D7) uses `preflight_input_bundle(brief)` directly.

#### 1c. Orchestrator emits `TurnInputs` before each agent call

`src/dual_research/orchestrator/` (find all call sites — see the
"Files touched" section below). At each point that today builds a
prompt string and dispatches to an agent, add:

```python
bundle = build_input_bundle(...)  # phase-specific builder
emit(TurnInputs(agent=agent, phase=phase, label=label, pieces=bundle))
prompt = build_prompt(...)
result = await agent.run(prompt)
emit(TurnEnded(..., prompt_pieces=size_bundle, ...))
```

Both bundle builders are pure functions of the same inputs, so
divergence between sizes (spec 0030) and text (this spec) is
impossible by construction. A unit test (`tests/protocol/
test_input_bundle_matches_pieces.py`) asserts that
`set(input_bundle.keys()) == set(pieces.keys()) ∪ {"system"}` for
every phase fixture.

### 2. Persist bundles to disk — aggregator

`src/dual_research/ui/aggregator.py`:

- New `_on_turn_inputs(event, run, session_dir)` handler. Writes
  the bundle to `session_dir/inputs/<turn-key>.json` where
  `turn-key` matches the Consumption tab's snake_case key
  (`phase0_claude`, `phase2_round3_claude`, …). The JSON shape:
  ```json
  {
    "agent": "claude",
    "phase": "phase2_round3",
    "label": "P2 R3 critique",
    "pieces": {
      "system": "…",
      "brief": "…",
      "d1": "…",
      "d2": "…",
      "plan": "",
      "hist": "…",
      "draft": "",
      "histp": ""
    },
    "emitted_at": "2026-05-16T14:23:11Z"
  }
  ```

- `TurnTokenUsage` (`models.py:232`) gains
  `input_path: str | None = None`. Stamped by the
  `_on_turn_inputs` handler via the same turn-key the
  `_on_turn_ended` handler uses. (Inputs arrive before Ended, so
  the handler may have to attach the path retroactively in
  `_on_turn_ended` if the row didn't exist yet — easy.)

- For the **Phase 0 input modal**, the aggregator synthesises one
  bundle from `brief.md` + the preflight system template and stores
  it at `session_dir/inputs/input.json`. Done lazily on first
  request via a new helper `_build_phase0_input_bundle(session_dir)`.

- Replay-safety: when loading a pre-0033 transcript (no `inputs/`
  folder), every `TurnTokenUsage.input_path` stays `None` and the
  UI's Input tab renders an empty-state.

### 3. New HTTP endpoint — UI server

`src/dual_research/ui/server.py`:

```python
@app.get("/api/runs/{run_id}/inputs/{turn_key}")
async def get_run_inputs(run_id: str, turn_key: str) -> JSONResponse:
    """Spec 0033 — fetch the per-turn input bundle.

    `turn_key` matches the camelized Consumption-tab key
    (`phase2Round3Claude`) OR the snake_case file name
    (`phase2_round3_claude`); the server accepts both for
    convenience. `input` is a valid key for the Phase 0 shared
    input bundle.
    """
```

Implementation:
- Validate `run_id` is one the server can see (existing auth /
  authz path).
- Normalise the key: camel → snake.
- Resolve `session_dir/inputs/<key>.json`; 404 if missing.
- Return the JSON verbatim (no transformation; the frontend reads
  the dict directly).

A second endpoint `/api/runs/{run_id}/inputs/index` returns the
list of available turn-keys so the UI can detect pre-0033 runs
without probing.

### 4. Phase 0 timeline split — `live-data.jsx`

`src/dual_research/ui/static/live-data.jsx::buildLiveTimeline` (and
the snapshot-mode equivalent `buildTimeline`):

Phase 0 today emits one item with `id: 'input', kind: 'input'`.
Replace with three items in order:

```js
{ id: 'input',    kind: 'input',    filePath: 'brief.md',          ... },
{ id: 'p0-claude', kind: 'preflight', agent: 'claude',
  filePath: 'phase0/preflight-claude.md',
  stats: run.phaseStats?.phase0?.claude,
  summary: run.phaseSummaries?.phase0_claude || '' },
{ id: 'p0-gpt',    kind: 'preflight', agent: 'gpt',
  filePath: 'phase0/preflight-openai.md',
  stats: run.phaseStats?.phase0?.gpt,
  summary: run.phaseSummaries?.phase0_gpt || '' },
```

`kind: 'preflight'` is new. Routing in `ArtifactModal` (line 1487)
sends `kind === 'input'` to `PreflightModal` (rebadged to
`InputBriefModal`, see §5), and `kind === 'preflight'` to a new
`PreflightResponseModal` — a one-pane modal with the per-agent
critique as `Content` and the same shared brief as `Input`.

`ArtifactHeader` for `kind: 'preflight'` (analogous to lines 1388 /
1425): `[agent icon] [agent name] · brief critique [PreflightChip]`.
`composeGist` learns a `preflight` case: "approved the brief" /
"flagged N issues with the brief".

### 5. Universal Input view + modal-frame plumbing

`src/dual_research/ui/static/run-detail.jsx`:

- New component `InputTabContent({ runId, turnKey })`:
  - Fetches `/api/runs/<runId>/inputs/<turnKey>` once via
    `React.useEffect` (memoise per runId+turnKey).
  - Renders an ordered list of `<InputSection>` — one per Tk-vocab
    key — collapsible. `system` collapsed by default; all others
    expanded. Friendly labels come from a shared
    `INPUT_PIECE_LABEL` map (`brief → "Brief"`, `d1 → "Claude P1
    draft"`, …) — same labels as `KIND_COLORS.label` from spec
    0030's `run-detail.jsx`. Empty pieces render a "(not used in
    this turn)" stub.
  - Each section's body renders the piece text as
    monospace-collapsible content with a copy button + a "View as
    markdown" toggle. Token-size badge in the header (from the
    Tk-piece map already known to the aggregator).

- `InputBriefModal` (replaces `PreflightModal`) — kind `input` tab
  set: `Input | Content | Sources | Files` where `Input` is the
  same `InputTabContent` rendered with `turnKey="input"` and
  `Content` is today's brief.md render. Default tab: `Input`
  (the user's intent is to audit what went in; the brief itself
  is reachable in one click).

- `PreflightResponseModal` — kind `preflight` tab set: `Content |
  Input | Sources | Files`. `Content` is the per-agent critique
  markdown; `Input` shows the same Phase 0 bundle as the brief
  modal (deliberately repeated — D5's general pattern is that
  every output's modal shows that output's input).

- `DocumentModal` (one-pane plan / doc) — add `Input` tab:
  `Content | Input` where `turnKey` is the Consumption-tab key
  for that artefact's emitting turn. The aggregator's
  `phaseTokenUsage` already knows this key per turn; the timeline
  item just needs to carry it. Add `item.turnKey` in
  `buildLiveTimeline` for `plan`, `plan-live`, `doc`, `doc-live`,
  `final`.

- `NegotiateReviewModal` (side-by-side, Phase 2/4) — add `Input` as
  a third tab on the **left pane's** tab strip. The left pane
  today is bare markdown of the prior agent's content; add a tab
  switcher: `Original | Input`. `Original` is today's content;
  `Input` is the `InputTabContent` for this turn. Right-pane
  critique view unchanged.

### 6. Two-row live header — `run-detail.jsx`

Replace `RunDetailHeader` (lines 12–65). New structure:

```jsx
<header style={...}>
  {/* Row 1: topic + cost + status + tabs */}
  <div className="header-row-1">
    <Topic text={run.topic} />
    <CostBadge cost={total} tokens={totalTokens} />
    <StatusErrorsBadge ... />
    <span style={{ flex: 1 }} />
    <TimelineTabs active={tab} onChange={setTab} />  {/* hoisted from PaneToolbar */}
  </div>
  {/* Row 2: Claude agent strip */}
  <AgentStrip agent="claude" run={run} />
  {/* Row 3: GPT agent strip */}
  <AgentStrip agent="gpt" run={run} />
  {/* Row 4: phase dots, full width, centred */}
  <PhaseDotsRow run={run} />
</header>
```

`AgentStrip` shape:

```
[icon] Claude (claude-sonnet-4-7)   ░░░░░░░░ 142,318t · $0.84 │ ●drafting parallel plan
                                    └────────token+cost badge─┘ └───status badge w/ phrase─┘
```

- The token+cost badge reuses today's `CostBadge` styling, scoped
  to the agent (not the run total).
- The status badge: same pulsing-dot pattern as
  `StatusErrorsBadge`, sentence after the dot. Color: agent's own
  color when live; `var(--fg-3)` (grey) when idle/waiting. Pulse
  on `live === true`; static otherwise.
- The status sentence is `composeAgentActivity(agent, run)` (D9).
- Metadata (`started · elapsed · round`) moves into the strip's
  hover-tooltip; no visible bar.

`PhaseDotsRow` is the existing `PhaseDots` rendered full-width,
left-aligned, with a one-line legend strip beneath it
(`Pre-flight · Parallel drafts · Negotiate · Drafting · Review`)
so the dots have labels for first-time users. The metadata line
(started/drafter/elapsed/round) moves to a single right-aligned
muted-mono line on the same row as the dots.

`TimelineTabs` move out of `PaneToolbar` (it can keep the
`AgentLegendChip` + live-count chip). Per D10, give them an
accent underline on the active tab and a slight padding bump.

### 7. `composeAgentActivity` — same file

New helper at the top of the agent-strip section:

```js
function composeAgentActivity(agent, run) {
  const ag = run.agents[agent];
  const other = agent === 'claude' ? 'gpt' : 'claude';
  const otherAg = run.agents[other];

  // Terminal phrasing
  if (run.status === 'completed') return { live: false, phrase: 'done' };
  if (run.status === 'errored')   return { live: false, phrase: 'errored' };
  if (run.status === 'deadlocked')return { live: false, phrase: 'deadlocked' };

  // Idle handling — point at the live counterpart if any
  if (ag.status === 'idle' || ag.status === 'waiting') {
    if (otherAg.status !== 'idle' && otherAg.status !== 'waiting') {
      return { live: false, phrase: `waiting for ${AGENT_META[other].name}` };
    }
    return { live: false, phrase: `waiting · phase ${run.phase}` };
  }

  // Live phrases keyed on (phase, status, turn.kind)
  const round = run.round?.current;
  switch (run.phase) {
    case 0: return { live: true, phrase: 'critiquing the brief' };
    case 1: return { live: true, phrase: 'drafting parallel plan' };
    case 2: return { live: true, phrase: round ? `negotiating · round ${round}` : 'negotiating' };
    case 3: return { live: true, phrase: 'drafting converged doc' };
    case 4: return { live: true, phrase: round ? `reviewing · round ${round}` : 'reviewing' };
    case 5: return { live: true, phrase: 'finalising' };
    default: return { live: true, phrase: ag.status };
  }
}
```

The component renders `phrase` after the pulse dot; `live` controls
the dot color and the pulse animation.

### 8. Tests

- `tests/protocol/test_input_bundles.py` (new) — each
  `*_input_bundle` returns the right keys with non-empty strings
  for the inlined pieces and empty strings for the others. Keys
  exactly match (modulo `system`) the corresponding `pieces_for_*`
  function in `prompt_pieces.py`. **This is the cross-check that
  prevents sizes-vs-text drift.**
- `tests/events/test_turn_inputs.py` (new) — `TurnInputs` event
  round-trips through the event bus; payload schema matches the
  dataclass.
- `tests/ui/test_aggregator_input_persistence.py` (new) — feeding
  a `TurnInputs` event to the aggregator writes
  `inputs/<key>.json` to the session dir with the expected
  contents. The corresponding `TurnTokenUsage.input_path` is set.
- `tests/ui/test_aggregator_phase0_input_synthesis.py` (new) —
  loading a run that has `brief.md` but no `phase0_claude` turn
  yet still produces a valid `inputs/input.json` on first request
  (the synthesised Phase 0 bundle).
- `tests/ui/test_server.py` — extend with
  `/api/runs/<id>/inputs/<key>` returning 200 + JSON for a
  fixture run; 404 for missing keys; both camel and snake key
  forms accepted.
- `tests/ui/test_aggregator.py` — extend with the Phase 0 timeline
  splitting into three items (`input`, `p0-claude`, `p0-gpt`);
  each `p0-<agent>` carries the right `summary` and `stats`.
- `tests/ui/test_disagreements.py` — no changes (unaffected).
- Frontend: manual only. Verify Input tabs render, sections
  collapse, empty-state surfaces on pre-0033 runs.

### 9. Files touched (non-exhaustive — for reviewer orientation)

Backend:
- `src/dual_research/events/types.py` — add `TurnInputs`.
- `src/dual_research/protocol/prompts.py` — add seven
  `*_input_bundle()` siblings.
- `src/dual_research/orchestrator/` — emit `TurnInputs` at every
  agent-dispatch site (grep `agent.run`; ~6 call sites).
- `src/dual_research/ui/models.py` — `TurnTokenUsage.input_path`.
- `src/dual_research/ui/aggregator.py` — `_on_turn_inputs`,
  Phase 0 bundle synthesis, replay-safety paths.
- `src/dual_research/ui/server.py` — two new endpoints.

Frontend:
- `src/dual_research/ui/static/run-detail.jsx`:
  - `RunDetailHeader` rebuilt (rows 1–4).
  - `AgentStrip`, `PhaseDotsRow`, `composeAgentActivity` added.
  - `TimelineTabs` hoisted out of `PaneToolbar`.
  - `InputTabContent` + `INPUT_PIECE_LABEL` + `useInputBundle`
    hook added.
  - `PreflightModal` → `InputBriefModal` (Input tab default).
  - `PreflightResponseModal` added.
  - `DocumentModal` gains `Input` tab.
  - `NegotiateReviewModal` left pane gains `Original | Input`
    sub-tabs.
  - `ArtifactCard` for `kind === 'preflight'` (new header +
    gist case).
- `src/dual_research/ui/static/live-data.jsx`:
  - Phase 0 timeline split (3 items instead of 1).
  - `item.turnKey` carried on plan / doc / turn items.

### 10. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.30.0 → 0.31.0.
- `CHANGELOG.md`: new `## [0.31.0] — YYYY-MM-DD` entry covering
  the four user-visible deltas: input view, Phase 0 split, two-row
  header, tab placement.
- `VERSION_NOTES` entry at the top of `how-it-works.jsx`.

## Out of scope

- **Critique navigation (questions/disagreements as first-class
  objects, side-by-side cross-references).** Spec 0034.
- **Consumption tab rework (dynamic scale, per-phase stacked
  sub-bars, color rework).** Spec 0035.
- **Editing or re-running with a modified input.** The Input view
  is read-only audit.
- **Diffing input bundles between rounds.** Tempting (you could
  show that Phase 2 R3's `hist` grew from R2's), but a separate
  visualisation and a future spec.
- **Live streaming of `TurnInputs` to the browser via SSE.**
  Bundles are persisted to disk and fetched on modal open via
  REST. SSE remains the path for turn lifecycle + per-turn token
  deltas only.
- **Highlight / cross-reference between Input sections and the
  output content.** That's the critique-navigation work in 0034.
- **A precise system-prompt-as-rendered renderer.** The `system`
  piece for each `*_input_bundle` is the static template *with
  placeholders left visible* (e.g. `{agent_name}`). The user
  reading the Input tab wants to see the template, not the
  substituted form (which is redundant once they've read the
  pieces below). A future spec could add a "rendered view"
  toggle if anyone asks.
- **Repair-turn input bundles for already-merged runs.** Spec
  0030 already left repair-turn `prompt_pieces` empty for repair
  invocations that pre-date 0030; same applies here. Repair
  turns from 0033 onwards do emit bundles.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec 0033 adds at
      least 8 new tests (input-bundle key parity per phase,
      `TurnInputs` event shape, aggregator persistence, server
      endpoint, Phase 0 timeline split, Phase 0 bundle synthesis,
      `input_path` round-trip through `_to_camel`).
- [ ] Manual: fire a fresh prod-tier run. As Phase 0 enters, the
      timeline shows three cards: `Input — brief`, `Claude · brief
      critique`, `GPT · brief critique`. Each opens its own modal.
- [ ] Manual: click `View in full mode` on the Phase 1 Claude
      draft card. Modal opens with two tabs: `Content` (today's
      markdown) and `Input`. The Input tab shows two sections —
      `system` (collapsed) and `brief` (expanded) — both with
      non-empty content and a token-count badge.
- [ ] Manual: click `View in full mode` on a Phase 2 round 3
      Claude turn. The side-by-side modal's left pane has two
      sub-tabs: `Original` (GPT's prior plan) and `Input`. The
      Input tab shows five sections — `system`, `brief`, `d1`,
      `d2`, `hist` — with `hist` visibly larger than in round 1
      (continuous with the Consumption tab's growth signal).
- [ ] Manual: the run header shows two agent strips. Claude's
      strip shows `[icon] Claude · 12k t · $0.04 │ ● drafting
      parallel plan` with a pulsing dot during Phase 1; GPT's
      shows the same, in green. On idle, the dot goes grey and
      the phrase becomes `waiting for <other>`.
- [ ] Manual: Conversation / Consumption tabs sit at the right of
      header row 1 with the active tab underlined; clicking
      Consumption swaps the body unchanged.
- [ ] Manual: phase-dot row sits below both agent strips with the
      five phase labels visible underneath.
- [ ] Manual: pre-0033 transcript (load any spec-0032 run from
      disk). Header shows the new layout. Card modals all open
      and render Content fine. The Input tab on any output modal
      shows an empty-state ("Input bundle not recorded — this run
      pre-dates spec 0033") and no error.
- [ ] Manual: hosted UI deploy — verify
      `/api/runs/<id>/inputs/<key>` returns valid JSON; verify
      the Input tab loads remotely over the hosted CDN.

## Risks

- **`TurnInputs` event doubles the I/O per turn.** Every turn now
  emits one extra event whose payload contains the full prompt
  text. For a 1M-context-window run, that's ~3.5MB per round on
  the wire. Mitigation: the event is consumed only by the
  aggregator (writes to disk) and not pushed over SSE to the
  browser; the browser fetches bundles on demand. Disk usage is
  bounded by the number of turns × the prompt size — same order
  of magnitude as the round transcripts that already exist in
  `phase{N}/`. Captured the size implication in D3.
- **Synthesised Phase 0 input bundle drifts from the actual
  preflight prompt.** If `preflight_input_bundle` is implemented
  as a separate function from `preflight_prompt`, they could
  diverge silently. Mitigation: the test
  `test_input_bundle_matches_pieces.py` asserts that the keys
  emitted by `*_input_bundle` match the keys emitted by the
  corresponding `pieces_for_*` function in `prompt_pieces.py` —
  drift in the key set fails CI. Drift in the values within a
  key is harder to catch automatically; mitigation is the same
  refactor discipline as spec 0030.
- **Two-row header is too tall on small screens.** Four rows
  (topic strip + Claude + GPT + phase dots) is ~3× today's
  header height. Mitigation: the agent strips collapse to a
  single line on width < 720px, with the status sentence
  truncating with `…` and full phrase available on hover.
  Captured in §6 (responsive); test manually at 640px / 1280px.
- **`composeAgentActivity` mis-states the live agent during phase
  transitions.** Between `PhaseExited` and the next
  `PhaseEntered`, both agents are `idle`; the phrase becomes
  `waiting · phase N done` for both. That's accurate (the run
  *is* between phases) but reads slightly weirdly. Mitigation:
  acceptable — phase transitions are sub-second in practice.
- **The `system` piece is verbose enough that users skip the
  Input tab entirely.** Mitigation: D6 starts `system` collapsed
  by default. If post-ship feedback says users still skip it, a
  future spec can add an outline view.
- **`InputTabContent` fetch latency on slow networks.** Bundles
  can be hundreds of KB; first open shows a brief loading state.
  Mitigation: the fetch is fire-and-forget on modal open with a
  `loading…` placeholder per section; the rest of the modal
  (Content tab) is interactive immediately.

## Open questions

- Whether the Input tab should be the **default tab** on every
  modal, or stay second to `Content`. D5 picks default `Input`
  for the brief modal only (the audit intent there is primary);
  every other modal defaults to `Content`. Easy to flip if the
  test run says otherwise.
- Whether the **phase-dot row** belongs above or below the agent
  strips. v1 puts it below (the run-level state reads as a
  footer to the per-agent rows). Alternative: above (the
  pipeline shape framing the per-agent live signal). Easy to
  swap; gut says below.
- Whether `composeAgentActivity` should surface **token deltas
  since last update** as a "speed" indicator ("drafting parallel
  plan · 1.2k t/s"). Tempting; v1 doesn't, since the data flow
  for delta-rate is its own small thing. Future spec.
- Whether to keep `PreflightModal` as a thin alias of
  `InputBriefModal` for one release to give external bookmarks /
  deep links time to migrate. v1 just renames; if anyone reports
  a broken link we'll add an alias in a follow-up.
