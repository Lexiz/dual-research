---
spec: 0008
title: Frontend handoff package
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.9.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/8"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0008 — Frontend handoff package

## Context

The backend is feature-complete at v0.8.0 (specs 0001–0007). The Claude Design output for the monitoring UI is sitting in `~/Trimble/handoff/` as a complete hi-fi React prototype (theme tokens, components, data shape, integration notes). The current chat session has accumulated a lot of context and is getting unwieldy; the user wants to move frontend work into a fresh session.

This spec sets up the handoff package so a new session can pick up cleanly: a comprehensive backend state document and a launch prompt that points the new agent at both this handoff and the Claude Design output, with explicit instructions to ask clarifying questions before writing code.

## Proposed change

Add a top-level `handoffs/` directory with:

- `handoffs/backend-state.md` — comprehensive snapshot of what's built, where it lives, how to run it, what the event bus emits, what the session-dir contains, engineering-workflow conventions, and known limitations. Written for an agent reading cold.
- `handoffs/frontend-kickoff.md` — the prompt the user pastes into a new Claude Code session. Instructs the agent to read the backend handoff first, then the Claude Design bundle at `~/Trimble/handoff/`, then ask clarifying questions before writing code.

These are documentation artifacts. No source code changes; no behaviour change. Version bumps anyway per the engineering-workflow rules (the repo's effective surface grew).

### Files added

- `handoffs/backend-state.md`
- `handoffs/frontend-kickoff.md`
- `specs/0008-frontend-handoff.md` (this file)
- `CHANGELOG.md`, `pyproject.toml`, `__init__.py` — 0.8.0 → 0.9.0

### Files modified

- None.

## Out of scope

- **Writing the frontend itself.** That's the next session's spec(s) — likely spec 0009 (SSE endpoint + state aggregator) and spec 0010 (UI wiring + frontend assets).
- **Choosing the frontend stack.** The Claude Design output is plain JSX + Babel-CDN + React from CDN. The new session will decide whether to keep that no-build setup or move to Vite/build-tooling.
- **Modifying the Claude Design output.** It lives in `~/Trimble/handoff/` outside this repo; the new session decides whether to copy it into `dual-research/ui/` or reference it in place.

## Test plan

- [ ] `handoffs/backend-state.md` exists and covers: project state, architecture, event bus contract, session-dir layout, CLI surface, engineering workflow, known limitations
- [ ] `handoffs/frontend-kickoff.md` exists and is paste-ready (no fill-in-the-blanks for the user)
- [ ] All 104 existing tests still pass (no code touched)
- [ ] Version is 0.9.0 in `pyproject.toml`, `__init__.py`, and `CHANGELOG.md`

## Risks

- **Handoff drift.** Once frontend work begins, the backend may evolve (small bug fixes, etc.) and the handoff doc becomes slightly stale. Mitigation: this is normal — new specs in the frontend session can update the doc when they touch the backend. The handoff is a "what was true at v0.9.0" snapshot, not a living source of truth.
- **The launch prompt under-specifies.** Mitigation: the prompt explicitly tells the new agent to ask questions, and the Claude Design README also lists 9 questions to ask. Between the two, the new session should know what to confirm before coding.
