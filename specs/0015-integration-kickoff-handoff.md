---
spec: 0015
title: Integration kickoff handoff package
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.16.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/15"
---

# Spec 0015 — Integration kickoff handoff package

## Context

The frontend is feature-complete at v0.15.0 (specs 0009–0014). The aggregator reads session directories on disk, the FastAPI server exposes them over REST + SSE, the UI bundle (live-data hooks, hash router, brand icons, run-id pill, card stats) renders the result. Every screen has been visually verified against the nine historical fixture runs under `runs/`.

What has **not** yet been done: running the orchestrator concurrently with the UI server and watching a live run flow through to the browser. The two halves were built and tested independently. The next session's job is to fire `dual-research --prompt "..."` against the test tier, point the UI at it, and validate that SSE deltas, body files, agent statuses, and the chip stack all populate correctly in real time.

The current chat is approaching its context budget. We're moving the integration session into a fresh chat the same way spec 0008 split backend from frontend work.

## Proposed change

Add two documents under `handoffs/`:

- `handoffs/frontend-state.md` — comprehensive snapshot of what was built between v0.10.0 and v0.15.0 (modules added, endpoints, UI surfaces, data contracts, known limitations). Written for an agent reading cold.
- `handoffs/integration-kickoff.md` — paste-ready prompt the user pastes into a fresh Claude Code session. Frames the live-integration goal, points the agent at both handoff docs, and lists what should be tested concurrently.

No code changes. No backend changes. No UI changes. Version bump anyway per the workflow rules (the repo's effective surface grew with the new docs).

### Files added

- `handoffs/frontend-state.md`
- `handoffs/integration-kickoff.md`
- `specs/0015-integration-kickoff-handoff.md` (this file)
- `CHANGELOG.md`, `pyproject.toml`, `__init__.py` — 0.15.0 → 0.16.0

### Files modified

- None.

## Out of scope

- The actual live integration test. That's the new session's job.
- Any backend or UI change. v0.15.0 ships unchanged.
- Bug fixes anticipated from live integration — those are spec 0016+ in the new session.

## Test plan

- [ ] `handoffs/frontend-state.md` exists and covers: modules added per spec, endpoint table, UI screens, data contracts (Run shape over the wire), known limitations, how to run the server
- [ ] `handoffs/integration-kickoff.md` exists and is paste-ready (no fill-in-the-blanks)
- [ ] All 214 existing tests still pass (no code touched)
- [ ] Version is 0.16.0 in `pyproject.toml`, `__init__.py`, `CHANGELOG.md`

## Risks

- **Handoff drift.** Same risk as spec 0008 — the frontend-state.md is a "what was true at v0.15.0" snapshot. If a future spec touches the affected surfaces the new agent can update the doc when they touch it. Not a living source of truth.

## Open questions

None.
