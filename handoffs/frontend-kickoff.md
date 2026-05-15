# Frontend kickoff — launch prompt

**How to use:** start a fresh Claude Code session in `~/dual-research/`, then paste the prompt block below as your first message.

---

## The prompt to paste

```
You are picking up frontend work on the dual-research orchestrator. The backend
is feature-complete and merged on `main` at v0.9.0. The Claude Design output
for the monitoring UI is sitting on disk as a complete hi-fi React prototype.
Your job is to wire that prototype to the real orchestrator and produce a
working frontend.

Before writing any code:

1. Read the backend handoff at `handoffs/backend-state.md` (in this repo).
   It covers: what the orchestrator does, repo layout, session-dir-as-source-
   of-truth pattern, the async event bus + every event type the orchestrator
   emits, CLI surface, engineering workflow conventions, and known limitations.

2. Read the Claude Design output bundle at `/Users/alexlisitzky/Trimble/handoff/`.
   Start with its `README.md` — sections 5 (data shapes the UI expects), 7
   (how to wire it up), and 9 (questions to ask before coding) are the
   load-bearing ones. Then skim `theme.css`, `shared.jsx`, `run-detail.jsx`,
   and `data.jsx` to internalize the component vocabulary and the mock data
   shape. You do NOT need to read every line of every JSX file — the README
   is the canonical reference.

3. Notice that the data shape the UI expects is NOT what the backend currently
   emits. The UI wants a single nested `Run` object (with `agents.claude/gpt`
   substructures, `disagreements[]` with progression timelines, `errors[]`,
   `phaseTimings`, `round.{current,soft,hard}`, `budget`). The backend
   currently emits granular events on its EventBus and persists artifacts to
   `runs/<id>/`. A state-aggregator + SSE endpoint is the bridge.

4. Also notice the agent label mismatch: the UI uses `claude` / `gpt`; the
   backend uses `claude` / `openai`. Translate at the adapter, not in the
   UI components (the design tokens `--agent-a` / `--agent-b` and the
   AgentIcon SVGs are already named after the UI's convention).

5. Then ASK QUESTIONS before writing code. The Claude Design README §9 lists
   seven questions explicitly (run id format, streaming transport, who
   computes the disagreement progression, error taxonomy, budget cap mode,
   markdown sanitization, brand icons). Surface those plus any of your own,
   then propose a build plan.

6. Once we agree on the plan, follow the engineering workflow rigorously:
   spec-first, branch `spec/NNNN-<slug>`, version bump per label, PR with
   `spec/*` label, admin squash-merge, delete branch. The next spec is 0009.
   `CONTRIBUTING.md` and `specs/0001-engineering-workflow.md` document the
   workflow in full.

Working directory: `/Users/alexlisitzky/dual-research` (this repo, on `main`)
Claude Design bundle: `/Users/alexlisitzky/Trimble/handoff/`

Required env vars are already set (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`NOTION_TOKEN`). The backend test suite runs clean: `uv run pytest tests/ -q`
should show 104 passed.

Start by reading the two handoff documents, then ask your questions.
```

---

## Hints for the new session (read these AFTER the agent has digested the two handoff documents)

These aren't part of the prompt — they're notes for you, the user, in case the new agent gets stuck or asks for guidance.

### Likely first decisions

- **Where does the frontend live?** Recommend `dual-research/ui/` so it ships with the backend. Alternative: separate repo (more boilerplate; rarely worth it for a single-user tool).
- **Build tooling.** The Claude Design prototype uses React + Babel + marked from CDNs (no build step). For production, a Vite + TypeScript setup is the cheapest upgrade — same component code (rename `.jsx` → `.tsx` later if/when), real bundling, fast HMR. The new session can decide.
- **State-aggregator placement.** A new module at `src/dual_research/ui_backend/` (or `src/dual_research/web/`) that:
  - Imports the orchestrator's EventBus
  - Maintains a Run-shaped dict per active run-id
  - Serves SSE at `/runs/:id/stream`
  - Serves a runs list at `/runs`
  - Probably FastAPI (already in the original briefing's defaults; aligns with Python ecosystem)
- **Live vs. completed runs.** The aggregator should ALSO be able to reconstruct a completed run from disk (`transcript.jsonl` + `state.json` + `metrics.json`). The Claude Design "All runs" view shows historical runs, not just live ones.

### Tricky bits

- **Disagreement progression.** The UI wants an array of `{round, agent, action, note}` where `action ∈ {raised, rejected, pushed back, restated, conceded, aligned}`. The backend tracks D-N IDs with status taxonomy `{open, resolved, non_blocking_limitation, final_surfaced, dropped_as_immaterial}`. The mapping isn't 1-to-1 — `aligned` is a UI synonym, `pushed back` doesn't have a direct backend state. The new session needs to either:
  - Parse the Phase 2 turn files (`runs/<id>/phase2/round-NN-{agent}.md`) to extract the D-N progression themselves
  - OR augment the orchestrator to emit `Disagreement{Raised,StatusChanged,Resolved}` events (more correct; bigger change). Sequence this carefully — backend changes happen via specs too.

- **Concurrency.** Multiple runs can happen at once (the user might run two `dual-research` invocations in parallel). The aggregator should key state by run-id, not assume a singleton.

- **Markdown trust.** The UI uses `marked` without DOMPurify. For local, single-user, agent-authored content this is fine. If anything external ever gets rendered (e.g., user-supplied notes), add sanitization.

### Spec roadmap I'd suggest for the new session

| Spec | Label | Headline |
|---|---|---|
| 0009 | `new-feature` | UI backend: FastAPI server + state aggregator + SSE per-run endpoint + runs-list endpoint |
| 0010 | `new-feature` | Frontend wiring: adapt Claude Design bundle (Vite + TS), replace mock data with SSE fetch, navigation |
| 0011 | `new-feature` | Disagreement progression — parse Phase 2 turn files into the UI's progression shape |
| 0012 | maybe | Production polish — brand icons (once licensed), accessibility pass, error chip filters in run-scoped view |

But the new session should propose its own breakdown once it's read the handoffs and asked clarifying questions.
