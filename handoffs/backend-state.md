# Backend state — handoff to frontend

Snapshot of the `dual-research` backend at **v0.9.0**, written for an agent picking up frontend work in a new session. Read this first; then read the Claude Design output bundle at `~/Trimble/handoff/`.

---

## 1 · Project at a glance

- **What it is:** A fully-autonomous orchestrator that runs two AI agents (Claude Sonnet 4.6 1M + GPT-5.5) through a 5-phase convergence protocol and produces a single converged research document.
- **Repo:** `Lexiz/dual-research` on GitHub — private, personal account. Local at `~/dual-research`.
- **Branch model:** linear `main` via squash-merges of `spec/NNNN-<slug>` branches. Every change comes from a spec. No work-in-progress on `main`.
- **Current version:** `0.9.0` (this handoff is spec 0008; next code spec is 0009).
- **Tests:** 104 pytest cases, all green. `uv run pytest tests/ -q`.
- **Backend status:** feature-complete. Phases 0→1→2→3→4→`final.md` runs end-to-end (verified on test tier — APPROVED in Phase 4 round 3, $0.79 total).
- **Frontend status:** NOT STARTED. Claude Design output is in `~/Trimble/handoff/`. The event bus is the integration point.
- **Engineering workflow:** spec-first; see `CONTRIBUTING.md` and `specs/0001-engineering-workflow.md`.

---

## 2 · What the orchestrator does

`dual-research --prompt "..."` runs:

```
Phase 0 — preflight (parallel; both agents critique the brief)
Phase 1 — independent research (parallel; both produce a Phase 1 draft)
Phase 2 — plan negotiation (turn-based until both AGREED with hash-matched plan)
Phase 3 — drafting (single-shot by the agreed drafter)
Phase 4 — review (turn-based until both APPROVED)
final.md emitted (metadata header + draft body)
```

All four CLI input modes work: `--prompt`, `--brief <md-file>`, `--notion <url>` (recursive Notion-tree fetch), `--resume <session-dir>` (recover an interrupted run).

Caps: `--soft-cap` (default 6) = logged warning + continue; `--hard-cap` (default 12) = exit 51 with deadlock-appendix `final.md`.

Models: `--models {prod,test}`. Prod = `claude-sonnet-4-6` (1M-context beta) + `gpt-5.5`. Test = `claude-haiku-4-5` + `gpt-5-mini`.

---

## 3 · Repo layout

```
dual-research/
├── CHANGELOG.md            Keep-a-Changelog; one section per spec
├── CONTRIBUTING.md         Engineering workflow rules
├── README.md               Project README (light)
├── pyproject.toml          uv-managed Python package
├── uv.lock
├── .github/PULL_REQUEST_TEMPLATE.md
├── handoffs/               THIS DIRECTORY
│   ├── backend-state.md    you are here
│   └── frontend-kickoff.md launch prompt for new session
├── specs/                  one .md per spec, plus TEMPLATE.md
│   ├── 0001-engineering-workflow.md
│   ├── 0002-orchestrator-phase01.md
│   ├── 0003-phase2-negotiation.md
│   ├── 0004-phases-3-4-final.md
│   ├── 0005-web-search.md
│   ├── 0006-prompt-caching.md
│   ├── 0007-resume-and-backoff.md
│   └── 0008-frontend-handoff.md
├── src/dual_research/
│   ├── __init__.py         __version__
│   ├── __main__.py         python -m dual_research entry
│   ├── cli.py              argparse + orchestrator dispatch + --resume
│   ├── config.py           ModelTier registry, Paths, Credentials, env loading
│   ├── ingest/             input ingest (prompt | brief | notion-recursive)
│   ├── protocol/           prompts (verbatim from original) + parsers + convergence
│   ├── agents/             ClaudeAgent + GptAgent (async streaming + retry + cache)
│   ├── events/             EventBus + ~17 event types  ← UI INTEGRATION POINT
│   ├── persistence/        SessionDirectory, SessionState, Transcript, Metrics
│   └── orchestrator/       per-phase drivers + run.py state machine + finalize.py
├── tests/
│   ├── agents/             retry, cache wiring, search flag
│   ├── events/             bus pub/sub
│   ├── orchestrator/       per-phase logic with stub agents + resume + turns
│   ├── persistence/        state round-trip, atomic writes, transcript, metrics
│   └── protocol/           parsers, convergence, tiebreak, cache markers
└── runs/                   gitignored — session artifacts (one subdir per run)
```

---

## 4 · Architecture

### 4.1 Session-dir-as-source-of-truth

Every run gets a directory under `runs/<YYYYMMDD-HHMMSS>-<slug>/`. Everything the run produces lives there:

```
runs/<id>/
├── brief.md                        ingested input (prompt | markdown | notion-tree)
├── state.json                      phase, drafter, agreed_plan, FSDs, draft_round
├── transcript.jsonl                append-only event log (one JSON / line)
├── metrics.json                    per-call + per-agent + total cost/tokens
├── phase0/
│   ├── preflight-claude.md
│   └── preflight-openai.md
├── phase1/
│   ├── draft-claude.md
│   └── draft-openai.md
├── phase2/
│   ├── round-01-claude.md
│   ├── round-01-openai.md
│   ├── round-NN-...
│   └── round-NN-{agent}.malformed-N.md   audit trail on repair-turn-invoked
├── phase3/
│   └── draft-v1.md                 initial converged draft
├── phase4/
│   ├── round-NN-{agent}.md
│   ├── draft-v2.md, draft-v3.md…   revisions emitted by drafter
└── final.md                        metadata header + final draft body
```

State writes are atomic (tmp → fsync → rename). Transcript is append-only JSONL. A crashed run is reconstructable from disk.

### 4.2 Async event bus

`src/dual_research/events/bus.py` is an in-memory async pub/sub:

```python
bus = EventBus()
bus.subscribe(callback)                  # callback can be sync or async
unsub = bus.subscribe(callback)          # returns unsubscribe fn
await bus.publish(SomeEvent(...))        # all subscribers called; failures isolated
```

A failing subscriber does NOT propagate to publisher or other subscribers — one bad UI consumer cannot break a run.

The orchestrator already publishes every meaningful state transition. **The transcript writer is itself a subscriber** (kind of — the orchestrator writes both publish-event and append-transcript inline; same data lands in both places). For the frontend, attaching another subscriber to the same bus is the natural integration path.

### 4.3 Phase orchestration

Each phase has its own module under `src/dual_research/orchestrator/`:

| Phase | Module | Shape |
|---|---|---|
| 0 | `phase0.py` | parallel preflight; both agents critique brief |
| 1 | `phase1.py` | parallel research; both write Phase 1 drafts |
| 2 | `phase2.py` | turn loop; convergence via `is_plan_agreed`; tiebreak via `pick_drafter`; repair via `parse_with_repair` |
| 3 | `phase3.py` | single-shot drafting by `state.drafter`; receives hash-verified `agreed_plan` + canonical FSDs |
| 4 | `phase4.py` | turn loop; convergence via `is_review_approved`; drafter can emit `## Revised draft` → orchestrator detects + writes `draft-vN.md` |
| – | `finalize.py` | metadata header + `final.md` emission; copies to `--out` if set |

`run.py` is the state machine. It loads `state.json`, runs only the phases that haven't completed yet, and propagates the appropriate exit code (0 / 51 / 52 / 2).

### 4.4 Agents

`agents/anthropic_agent.py` and `agents/openai_agent.py` share an `AgentCall` protocol from `agents/base.py`. Both:

- Stream output via async iterator (text deltas as they arrive)
- Capture per-call usage (input/output/cache_read/cache_write tokens)
- Compute USD cost from `agents/pricing.py`
- Wrap the SDK call in `with_rate_limit_retry` (max 3 attempts, Retry-After honoured, exponential backoff fallback)
- Detect a `CACHE_BREAKPOINT` sentinel and apply Anthropic `cache_control` (1h TTL via `extended-cache-ttl-2025-04-11` beta) — OpenAI's Responses API caches prefixes ≥1024 tokens automatically
- Take a `web_search` tool by default (disable via `DUAL_RESEARCH_NO_WEB_SEARCH=1`)

Anthropic uses Messages API streaming; OpenAI uses the Responses API (the Chat Completions API doesn't expose `web_search`). Both return a `AgentResult` with `text`, `usage`, `cost_usd`, `duration_ms`, `extras={searches: N, stop_reason/finish_reason}`.

### 4.5 Protocol module (the IP)

`src/dual_research/protocol/` contains the prompts (preserved byte-for-byte from the original protocol.mjs) plus parsers and convergence gates:

- `prompts.py` — `preflight_prompt`, `research_prompt`, `negotiation_round1_prompt`, `negotiation_turn_prompt`, `drafting_prompt`, `review_turn_prompt`, `repair_prompt`. `COMMON_PREAMBLE` covers the epistemic-duty paragraph, V/U source-tagging, freshness rule, anti-sycophancy. `CACHE_BREAKPOINT = "<<<CACHE_BREAKPOINT>>>"` sentinel is inserted between stable prefix and dynamic suffix in every phase prompt except `repair`.
- `parse.py` — regex set + `parse_turn`, `parse_preflight_turn`, `extract_fenced_section`, `extract_revised_draft`. Tolerant of leading list markers / backticks / emphasis / blockquote prefixes.
- `convergence.py` — `normalized_hash`, `assert_well_formed_plan_turn`, `assert_well_formed_round1_turn`, `assert_well_formed_review_turn`, `is_plan_agreed`, `is_review_approved`, `all_substantive_gates_pass_except_drafter`, `extract_canonical_fsd_items`.
- `tiebreak.py` — `pick_drafter` (three-step chain: matching → domain-fit → plan-alignment → hash-of-brief).
- `errors.py` — `Status` StrEnum, `ProtocolParseError`.

---

## 5 · Event bus contract (the UI integration surface)

The orchestrator publishes the following event types to its EventBus. All defined in `src/dual_research/events/types.py` as frozen `kw_only` dataclasses. Every event has a `kind` string (already shown in the table below); all fields shown are non-`kind`.

### 5.1 Run-level

| Event | Fields | When |
|---|---|---|
| `RunStarted` | session_dir, slug, model_tier, claude_model, openai_model, soft_cap, hard_cap | At the start of `run_session` |
| `RunCompleted` | phase_reached, exit_code, total_cost_usd, duration_ms | At the end of `run_session` (success or graceful failure) |
| `RunFailed` | phase_reached, error_type, message | On unhandled exception |
| `CostUpdate` | total_usd, by_agent (dict) | After every `TurnEnded` |
| `FinalEmitted` | session_final_path, out_path, char_count, confidence | After `final.md` is written |

### 5.2 Phase-level

| Event | Fields | When |
|---|---|---|
| `PhaseEntered` | phase | Start of each phase |
| `PhaseExited` | phase, duration_ms | End of each phase |
| `Phase0Complete` | claude_status, openai_status, claude_brief_issues, openai_brief_issues, brief_needs_input | After Phase 0 preflight parsed |
| `Phase1Complete` | claude_chars, openai_chars | After Phase 1 drafts written |
| `Phase2RoundComplete` | round, agreed, claude_status, openai_status, claude_drafter, openai_drafter, claude_open_questions, openai_open_questions, claude_blocking, openai_blocking, claude_fsd, openai_fsd | After each Phase 2 round |
| `Phase2Complete` | rounds, converged, drafter, fsd_count, via_tiebreak | At end of Phase 2 |
| `Phase3Complete` | drafter, draft_chars | After Phase 3 single-shot |
| `Phase4RoundComplete` | round, approved, claude_status, openai_status, claude_open_issues, openai_open_issues, draft_round | After each Phase 4 round |
| `Phase4DraftRevised` | round, new_draft_round, new_draft_chars | When drafter emits a revised draft |
| `Phase4Complete` | rounds, approved, final_draft_round, revisions | At end of Phase 4 |
| `DrafterTiebreakResolved` | round, selected_drafter, reason, claude_proposed, openai_proposed | When orchestrator-side `pick_drafter` resolves |

### 5.3 Turn-level

| Event | Fields | When |
|---|---|---|
| `TurnStarted` | agent, phase, label | Before each agent call |
| `TurnEnded` | agent, phase, label, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, cost_usd, duration_ms, finish_reason, model_id | After each agent call |
| `RepairInvoked` | agent, phase, round, errors, budget_remaining | When `parse_with_repair` runs a repair turn |
| `SoftCapHit` | phase, round, cap | When soft cap is crossed (logged, run continues) |
| `HardCapHit` | phase, round, cap | When hard cap is crossed (run aborts after this round) |

### 5.4 Transcript

Every event is also written to `runs/<id>/transcript.jsonl` as a JSON object with the same fields plus a `ts` ISO timestamp. The transcript is the authoritative replayable log; events are the live stream.

The frontend can EITHER:

- **Subscribe to the live bus** for an in-flight run (requires the orchestrator to expose an SSE endpoint that adapts events to whatever shape the UI wants). No such endpoint exists yet — building it is part of the frontend work.
- **Tail `transcript.jsonl`** for in-flight runs (file changes via fs-watch).
- **Read `transcript.jsonl` once + `state.json` + `metrics.json`** for completed runs.

The Claude Design output (in `~/Trimble/handoff/README.md` §5) describes a different shape: a single nested `Run` object with `agents.{claude,gpt}` substructures, a `disagreements` array, and an `errors` array. A small adapter layer will convert our event stream + persistence files into that shape.

---

## 6 · CLI surface

```bash
# Three mutually-exclusive input modes (one required):
dual-research --prompt "Inline brief text..."
dual-research --brief path/to/brief.md
dual-research --notion https://www.notion.so/Workspace/Page-abc123

# Or resume an existing session:
dual-research --resume runs/20260515-124552-cache-multi-round [--extend-caps N]

# Common flags (all valid alongside any input mode):
--out PATH               copy final.md to user-chosen path
--name SLUG              run-id slug (default: derived from input)
--models {prod,test}     model tier (default: prod)
--soft-cap N             default 6
--hard-cap N             default 12
--runs-dir PATH          default <project>/runs/
--notion-max-depth N     default 5 (Notion ingest)
--notion-max-pages N     default 100 (Notion ingest)
--ingest-only            build brief and stop (debug)
--extend-caps N          (resume only) add N to both caps
--version
--help

# Exit codes:
0   success — APPROVED final emitted (or completed-already on --resume)
1   preflight failure (missing creds, missing brief path, etc.)
2   runtime failure (unhandled agent / IO error)
51  hard cap hit (deadlock-appendix final emitted)
52  protocol parse failure (agent emitted malformed turn twice consecutively)
```

Required env vars: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`. `NOTION_TOKEN` only required for `--notion`.

---

## 7 · Engineering workflow

Documented in [`CONTRIBUTING.md`](../CONTRIBUTING.md). Key rules:

1. Every code/schema/prompt/infra change starts with a `specs/NNNN-<slug>.md` file (front-matter labels: `new-feature` | `bug` | `refactoring` | `test` | `breaking`).
2. Branch off `main` as `spec/NNNN-<slug>`. One spec ↔ one branch ↔ one PR.
3. Bump `pyproject.toml` + `src/dual_research/__init__.py` per label (breaking=MAJOR, new-feature=MINOR, others=PATCH).
4. Update `CHANGELOG.md` under the new version.
5. Open PR with title = spec title, apply matching `spec/*` GitHub label.
6. Flip spec front-matter `status: merged` and fill `pr:` field with PR URL.
7. `gh pr merge <N> --admin --squash --delete-branch` (transient "Pull Request is not mergeable" can happen — wait 5s and retry).

The template lives at `specs/TEMPLATE.md`. The full design doc is `specs/0001-engineering-workflow.md`.

---

## 8 · Verified behaviour

End-to-end runs that actually completed:

- **Spec 0003 verification (Phase 2 only):** asyncio-vs-goroutines brief, test tier, $0.29, 4 rounds, drafter=openai via matching recommendations.
- **Spec 0006 verification (full Phase 0→4):** TypeScript-vs-JavaScript brief, test tier, **APPROVED in Phase 4 round 3**, 23 model calls, $0.79, 14 min. Final document emitted with all six required sections + metadata header (MODERATE confidence).
- **Spec 0007 verification (resume):** completed session re-loaded, all phases correctly skipped, exit 0, $0 cost.

Verified independently:

- Anthropic web_search returned current-information citations
- Anthropic prompt caching: 76.6% cost reduction on a duplicate call
- Notion recursive ingest: 30 Partner Vetting pages fetched cleanly
- All 6 phase-prompt builders produce valid markdown with required machine-parseable fields

---

## 9 · Known limitations

- **Anthropic 30K-tokens/min rate limit on the current account tier.** Hits at Phase 2 round 6+ with prod-tier `claude-sonnet-4-6`. Cache reads are free against this quota, but cache writes (the growing dynamic suffix in each negotiation round) are not. Mitigations available:
  - `--resume <session>` to recover after the limit lifts
  - Anthropic SDK + `with_rate_limit_retry` already handles transient 429s
  - Sales-contact tier upgrade is the structural fix
  - Test tier (Haiku 4.5 + GPT-5-mini) has higher limits; unaffected
- **Test-tier convergence is somewhat flaky.** Less capable models (Haiku 4.5, GPT-5-mini) sometimes emit `STATUS: AGREED` without a populated `AGREED_PLAN` block, or with hash-mismatched plans between agents. The protocol's strictness rejects these and they're either repaired or hit the cap. This is intended behaviour — false convergence would be worse.
- **Cost-tracking precision.** Web search costs ($10/1k Anthropic searches, OpenAI's is unspecified at 2026 prices) are not currently rolled into the per-call `cost_usd`. The `extras["searches"]` count is logged but the dollar value is undercount by the search cost. Material delta is small (~$0.01–$0.10 per run).
- **`OPEN_ISSUES: 0` mid-document.** Some agent outputs include protocol-marker lines (`STATUS: AGREED`, `OPEN_QUESTIONS: 0`) inside their `## Revised draft` body. The orchestrator extracts the body as-is; final.md may show those markers. Cosmetic, not a correctness issue.

---

## 10 · What the frontend needs to do

The Claude Design output is a complete React + Babel-via-CDN prototype with mock data. The frontend integration work, in rough order:

1. **State aggregator** — subscribe to the EventBus (server-side) and maintain a `Run` object matching the shape in `~/Trimble/handoff/README.md` §5.1. Field-by-field translation from our events (`agents.claude.tokens` ← rolling sum of `TurnEnded.input_tokens+output_tokens` for that agent; `phase` ← latest `PhaseEntered`; etc.). Some derived state requires computation: the disagreement `progression` array is not currently emitted; it has to be reconstructed by parsing Phase 2 turn files (D-N status taxonomy) into the `raised/restated/conceded/resolved` taxonomy the UI uses.
2. **SSE endpoint** — `/runs/:id/stream` emitting incremental `Run` snapshots or smaller deltas (`turn-appended`, `disagreement-opened`, etc.). The simplest path is the snapshot-on-every-event one.
3. **Runs list endpoint** — `/runs` that scans `runs/<id>/` directories on disk and returns `RUN_LIST` rows.
4. **Static frontend** — adapt `~/Trimble/handoff/` JSX bundle: replace `data.jsx` mock data with fetch-from-SSE, wire `connected · localhost:6173` indicator to actual SSE state, wire row-click in `RunListView` to navigation, decide on production build (Vite + esbuild vs the no-build CDN approach the prototype uses).
5. **Agent label translation.** The UI uses `claude` / `gpt` (matching the design palette tokens `--agent-a` / `--agent-b`). The backend uses `claude` / `openai`. Pick one; translate at the adapter.

The Claude Design output explicitly lists 9 open questions in its README §9 — work through those with the user before writing code.

Recommended starting place: the new session decides whether the frontend lives at `dual-research/ui/` (alongside the backend) or as a separate repo. Both are viable. The orchestrator-side event-bus integration is necessarily in the same Python package either way.
