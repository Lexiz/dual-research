# Frontend state — handoff to integration

Snapshot of the `dual-research` frontend at **v0.15.0**, written for an agent picking up live-integration work in a new session. Read this AFTER `handoffs/backend-state.md` (which is still accurate at v0.9.0; backend hasn't changed since).

---

## 1 · Project at a glance

- **What it is:** A read-only observability dashboard for the `dual-research` orchestrator, served from `dual-research serve` at `http://127.0.0.1:6173/` by default. Reads session directories on disk and live-tails in-flight runs over SSE.
- **Branch model:** linear `main` via squash-merges of `spec/NNNN-<slug>` branches. Same workflow as the backend (see `CONTRIBUTING.md`).
- **Current version:** `0.15.0`. This handoff is spec 0015; the next code spec is 0016.
- **Tests:** 214 pytest cases, all green. `uv run pytest tests/ -q`.
- **Backend status:** unchanged since v0.9.0. The frontend was built **explicitly with no backend changes**; gaps surface as "we infer this from disk" or "the chip doesn't render".
- **Integration status:** NOT yet tested concurrently. Aggregator + server + UI bundle have been tested independently against the nine historical fixture runs under `runs/`. The next session's job is to spin up a live `dual-research --prompt ...` while the UI is open and verify the live data path end-to-end.

---

## 2 · Specs shipped (v0.10.0 → v0.15.0)

| Spec | Version | What it added |
|---|---|---|
| [0009](../specs/0009-ui-run-aggregator.md) | 0.10.0 | UI run aggregator — `src/dual_research/ui/` package. Reads a session dir, returns a UI-shaped `Run`. |
| [0010](../specs/0010-ui-server.md) | 0.11.0 | FastAPI server + SSE — `dual_research.ui.server`, `dual-research serve` CLI subcommand. |
| [0011](../specs/0011-ui-bundle-integration.md) | 0.12.0 | UI bundle integration — JSX prototype wired to the live API; hash router; lazy markdown fetch. |
| [0012](../specs/0012-ui-polish-and-navigation.md) | 0.13.0 | UI polish & navigation — JetBrains Mono, real Claude/OpenAI brand icons, new top bar, single-tab nav. |
| [0013](../specs/0013-run-id-pill-and-card-stats.md) | 0.14.0 | Run-id pill + timeline card stats — protocol marker fields surfaced as inline chips. |
| [0014](../specs/0014-clearer-card-stats.md) | 0.15.0 | Clearer card stats — Phase 1 chips via section-counting; plain-English labels (`5 questions · 2 disagreements`). |

---

## 3 · Repo layout (frontend-relevant additions)

```
dual-research/
├── src/dual_research/
│   ├── cli.py                          ← short-circuits `serve` to ui.server.main
│   ├── ui/                              ← NEW (spec 0009)
│   │   ├── __init__.py                 exports load_run_snapshot, apply_event, etc.
│   │   ├── aggregator.py               read session dir → Run
│   │   ├── disagreements.py            parse Phase 2/4 ## Substantive disagreements
│   │   ├── errors.py                   map transcript events → RunError list
│   │   ├── labels.py                   backend↔UI label translation, status state machine
│   │   ├── models.py                   Run, AgentState, Disagreement, RunError, TurnStats, PhaseStats
│   │   ├── server.py                   FastAPI app + dual-research serve CLI
│   │   ├── turn_stats.py               per-turn protocol-stat parsing (spec 0013/0014)
│   │   └── static/                     UI bundle, served at /
│   │       ├── index.html              CDN React + Babel + marked
│   │       ├── theme.css               design tokens, JetBrains Mono + Geist
│   │       ├── shared.jsx              primitives, AgentIcon (real brand SVGs), Markdown
│   │       ├── live-data.jsx           hooks: useLiveRun, useRunList, useFileBody
│   │       ├── router.jsx              #/ hash routing
│   │       ├── app.jsx                 ChromeBar, RightCluster, detail/list/language screens
│   │       ├── run-list.jsx            All-runs view + run-id pill
│   │       ├── run-detail.jsx          Timeline + Disagreement explorer + chips
│   │       ├── errors.jsx              run-scoped errors view
│   │       ├── design-language.jsx     palette / type / brand marks reference
│   │       └── tweaks-panel.jsx        dev knobs (stream speed only in live build)
├── tests/ui/                            ← NEW (specs 0009/0013/0014)
│   ├── test_aggregator.py
│   ├── test_disagreements.py
│   ├── test_errors.py
│   ├── test_labels.py
│   ├── test_server.py
│   └── test_turn_stats.py
└── handoffs/
    ├── backend-state.md                from spec 0008
    ├── frontend-kickoff.md             from spec 0008
    ├── frontend-state.md               THIS DOCUMENT (spec 0015)
    └── integration-kickoff.md          paste-ready prompt (spec 0015)
```

---

## 4 · How to run the UI locally

```bash
uv run dual-research serve [--port 6173] [--host 127.0.0.1] [--runs-dir PATH]
```

Defaults serve `http://127.0.0.1:6173/` against `<project>/runs/`. Open in any modern browser (Chrome, Safari, Firefox). React 18 + Babel-standalone + marked load from CDN — no build step.

The server uses `watchfiles.awatch(session_dir)` to tail each open run's `transcript.jsonl`. A snapshot SSE frame is emitted on every transcript-file change.

---

## 5 · HTTP endpoints (spec 0010)

| Method | Path | Returns |
|---|---|---|
| `GET` | `/api/health` | `{ok, version, runsDir}` |
| `GET` | `/api/runs` | List of `RunListRow` (newest first) |
| `GET` | `/api/runs/{run_id}` | Full `Run` snapshot |
| `GET` | `/api/runs/{run_id}/stream` | SSE; emits `snapshot` events whenever `transcript.jsonl` changes |
| `GET` | `/api/runs/{run_id}/files/{path:path}` | Markdown file body as `text/plain` (allowed: `.md`, `.json`, `.jsonl`, `.txt`; path-scoped to the session dir) |
| `GET` | `/`, `/static/*` | UI bundle |

JSON payloads use **camelCase at the wire**; Python stays snake_case. Translation is a recursive helper in `server.py::_to_camel`. Int dict keys (e.g. `phase_timings[0]`) are coerced to strings.

---

## 6 · Run shape (over the wire)

Matches `~/Trimble/handoff/README.md` §5.1 verbatim. Abbreviated:

```ts
Run {
  id: string                       // full session-dir name
  displayId: string                // sha1(id)[:4]
  topic: string                    // brief.md H1
  status: 'running' | 'completed' | 'deadlocked' | 'errored' | 'converged' | 'idle'
  phase: 0..5                      // 5 = done
  startedAt: string                // ISO-8601 from first transcript event
  startedAtAgo: number             // seconds (server fills at serialize time)
  drafter: 'claude' | 'gpt' | null
  phaseTimings: {[k: '0'..'4']: number | null}
  round: { current, soft, hard }
  budget: null                     // client-side preference; not threaded
  agents: {
    claude: AgentState
    gpt:    AgentState             // backend "openai" → UI "gpt"
  }
  disagreements: Disagreement[]    // reconstructed from ## Substantive disagreements
  errors: RunError[]               // mapped from repair_invoked / soft|hard_cap_hit / run_failed
  error: TopLevelError | null
  phaseStats: PhaseStats           // spec 0013/0014 — drives chip data
}

AgentState {
  status: 'idle'|'thinking'|'drafting'|'responding'|'reviewing'|'waiting'
  currentTurn: { kind, index, body }
  lastTurn:    { kind, index } | null
  tokens: { in, out }
  cost: number
  modelId: string                  // from RunStarted.claude_model / openai_model
}

PhaseStats {
  phase0: {[ui_agent]: TurnStats}            // BRIEF_OK + BRIEF_ISSUES
  phase1: {[ui_agent]: TurnStats}            // counts from "Open questions" + "...dispute" sections
  phase2: {[round: string]: {[ui_agent]: TurnStats}}
  phase4: {[round: string]: {[ui_agent]: TurnStats}}
}

TurnStats {
  status, openQuestions, openIssues, blocking, fsd, briefIssues
}
```

The aggregator is the single seam where backend vocabulary (`openai`, `phase2`) becomes UI vocabulary (`gpt`, `2`). Every downstream consumer speaks UI vocabulary.

---

## 7 · UI screens

Three top-level routes (URL hash):

- `#/` — **All runs** (default landing). Filter chips by status. Rows: run-id pill, status, topic (clamped to first sentence), phase mini-strip, started, duration, cost. Click row → detail.
- `#/runs/<run_id>` — **Run detail**. Two-row top bar (back chip · brand · displayId pill · cost · status; topic + meta line). Phase strip. Two-pane body: Timeline (left, artifact cards with inline chips), Disagreement explorer (right, tabbed Phase 2 / Phase 4).
- `#/language` — **Design language**. Tokens, brand marks, typography, motion principles.

Top-right chrome carries three equal-weight controls: connection-state pill, segmented light/dark toggle, Design button. Theme persists to `localStorage`.

---

## 8 · Timeline chip data

Each turn card carries chips derived from the structured marker fields in the corresponding round/draft file:

| Phase | Source | Chips |
|---|---|---|
| 0 (Input) | `phase0/preflight-{agent}.md` → STATUS + BRIEF_ISSUES | `ok` or `needs input · N` |
| 1 (plan drafts) | `phase1/draft-{agent}.md` → count items in `Open questions` / `...dispute` sections | `N questions · M disagreements` |
| 2 (turns) | `phase2/round-NN-{agent}.md` → parse_turn | `N questions · M disagreements`, `agreed` pill on STATUS=AGREED |
| 4 (review turns) | `phase4/round-NN-{agent}.md` → parse_turn | `N issues`, `approved` / `not approved` pill |
| 3, 5 (drafter / final) | — | no chips |

The Phase 1 chip extraction (spec 0014) handles two format variants the agents use in practice:

- **H2 form** (Claude-style): `## Open questions`
- **Numbered top-level form** (GPT-style): `5. **Open questions** — ...`

Format choice is per-file: if the file has any `##` headings, only those are anchors; otherwise fall back to numbered sections.

---

## 9 · Disagreement reconstruction

`src/dual_research/ui/disagreements.py` parses each Phase 2 / Phase 4 round file's `## Substantive disagreements I'm holding` section, groups entries by the protocol's stable `D-N` identifiers, and builds a `Disagreement` per id with a per-round progression timeline. Tolerates two line formats:

- Open form: `- D-3: Compiler performance — status: open` (numbered (a)–(e) sub-items follow)
- Resolved form: `- **D-1 (label):** \`resolved\` — note`

Attribution: whoever marks a disagreement terminal first is the conceder; `resolved-claude` means "claude's position prevailed" (so gpt conceded), and vice-versa.

The right-pane Disagreement explorer's tabs (`PHASE 2 Negotiate`, `PHASE 4 Review`) consume this list and group by `status`.

---

## 10 · Error taxonomy (sparse by design)

Only four backend events map to UI errors today; the other UI codes are placeholders that don't fire.

| Backend event | UI code | Severity | Resolved |
|---|---|---|---|
| `repair_invoked` | `INVALID_TURN_FORMAT` | error | recovered |
| `soft_cap_hit` | `SOFT_CAP_HIT` | warning | recovered |
| `hard_cap_hit` | `HARD_CAP_HIT` | warning | halted |
| `run_failed` | `ORCHESTRATOR_PANIC` | critical | halted |

Rate-limit retries happen silently inside `with_rate_limit_retry`; they don't surface. Stream-disconnects, timeouts, context-overflow are not currently emitted by the backend.

---

## 11 · Known limitations (load-bearing for integration testing)

These are the gaps a live-integration session is most likely to hit:

1. **No per-token streaming inside turn bodies.** A turn's `currentTurn.body` only populates when the round file lands on disk (after `TurnEnded`). For ~10–30 s of every active turn, the live card shows agent status (`responding` / `drafting`) but no body.
2. **`phaseStats.phase1` only populates if the draft file has the expected section names.** Some agents may emit drafts without `Open questions` / `Claims I expect ... dispute` sections; the chip just doesn't render. Graceful degradation.
3. **Disagreement parser tolerates two line formats** but a deviant agent (numbered list with bolded sub-items, e.g. `1. (a) D-3 — ...`) may be missed. Cross-merging from the other agent's view usually fills the gap.
4. **`Run.budget` is always `null`** in v1. The UI's budget meter hides when budget is null. To enable it, set `window.localStorage["dr.budget"] = 4.00` and either (a) thread that through the UI or (b) build a tweak. Either is a follow-up spec, not v1.
5. **SSE reconnect cadence is browser-default.** EventSource auto-reconnects on disconnect with ~1–3 s backoff. If the server restarts mid-run, the indicator briefly flips to `idle`.
6. **The All-runs list polls every 3 s.** No global SSE feed. A run that appears mid-session won't show up for up to 3 s.
7. **Concurrent orchestrator + UI server** has never been tested end-to-end. The aggregator's incremental `apply_event` path is well-unit-tested, but the file-watch path (watchfiles) hasn't been exercised against a real orchestrator writing transcript lines as the run progresses.
8. **Brand-mark trademarks.** The official Claude (Anthropic) and OpenAI marks are used under hobby-project posture. If the UI is ever distributed publicly, revisit.

---

## 12 · Verified at v0.15.0

- **All 214 tests green.** `uv run pytest tests/ -q`.
- **Live preview at 1440 × 900** against the 9 fixture session directories in `runs/`. Verified screenshots for: list view, run detail (`cache-multi-round`), design language.
- **Endpoints respond correctly.** `/api/health`, `/api/runs`, `/api/runs/{id}`, file fetches all return the expected shapes.
- **SSE wire format.** `event: snapshot\ndata: {...json...}\n\n` confirmed via curl.

NOT verified:

- **Live concurrent run.** Run the orchestrator and the UI server at the same time and watch the timeline populate in real time.
- **Mid-run SSE deltas.** Whether watchfiles fires reliably as transcript lines append while the page is open.
- **In-flight error rendering.** All current errors in the UI come from completed runs. A run currently failing has not been observed.
- **Long-running phase 2/4 round display.** The current turn body lazy-fetch was tested on completed turns, not on a turn that hasn't finished writing.

---

## 13 · Engineering workflow (unchanged from spec 0008)

Same `spec/NNNN-<slug>.md` → branch → PR → admin squash-merge flow documented in `CONTRIBUTING.md`. The next spec is **0016**.

---

*Generated 2026-05-15 at v0.15.0. Spec 0015.*
