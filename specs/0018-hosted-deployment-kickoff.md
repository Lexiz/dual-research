---
spec: 0018
title: Hosted deployment kickoff handoff package
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.17.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/18"
---

# Spec 0018 — Hosted deployment kickoff handoff package

## Context

Through specs 0001–0017 the project went from empty repo to a complete
local tool: orchestrator + observability UI, integration-verified end-to-end
on the live data path, 223 tests green, v0.16.2 on `main`.

The product goal has now expanded: a **publicly accessible, Google-auth-gated,
DB-backed dual-research UI** so the user can show research results to
approved collaborators at a real URL. The orchestrator stays local for
now (kicked off from the user's laptop); a new CLI subcommand pushes
session data to a hosted database; the hosted UI reads from that
database; access is gated by a Google-OAuth login + an admin-managed
email allowlist.

This is multi-session work — roughly five specs (0019–0023). It will
not all land in one session. This spec ships **only handoff
documents** so a fresh Claude Code session can pick up cleanly and
start spec 0019 with full context. Same pattern as spec 0015.

## Proposed change

Two documents under `handoffs/`:

- **`handoffs/hosted-deployment-kickoff.md`** — comprehensive briefing
  for the new track. Architectural decisions locked in (Fly.io for
  hosting, Supabase for Postgres + Google OAuth, orchestrator stays
  local, push CLI mirrors session data), why-Fly-over-Vercel summary,
  spec roadmap (0019–0023), pre-work the user must do (Supabase
  account, Fly.io account, env vars), open design questions for spec
  0019, and a paste-ready session-kickoff prompt at the bottom.
- (The existing `handoffs/integration-state.md` from spec 0017 stays
  as the integration-track snapshot; this new doc complements it.)

No code changes. CHANGELOG entry + version bump per workflow
(`new-feature` → MINOR → 0.16.2 → 0.17.0).

## Out of scope

- Any actual deployment work. That starts in spec 0019 in a fresh
  session.
- Closing the P2 cosmetic cluster (I6, I8, I9, I10) and the I11
  ErrorCard crash from the integration session. They remain orthogonal
  follow-ups, flagged in the briefing as carryovers but not blocking.

## Test plan

- [ ] `uv run pytest tests/ -q` → 223 passed (no code change, no test
      regression).
- [ ] Manually re-read both new handoff docs end-to-end; verify the
      paste-ready prompt is self-contained.

## Risks

Documentation only. Risks are limited to the briefing being incomplete
or wrong about a tool's capability (e.g., Fly.io free-tier limits,
Supabase Google-OAuth shape). Mitigation: the briefing flags
architectural decisions as locked-in but design details for spec 0019
as open, so the next session validates them against current vendor
docs before committing.
