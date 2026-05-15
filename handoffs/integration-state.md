# Integration state — handoff after spec 0016

Snapshot of the `dual-research` project at **v0.16.1**, written for an agent
picking up where the integration session left off. Read this AFTER
`handoffs/backend-state.md` (v0.9.0, still accurate) and
`handoffs/frontend-state.md` (v0.15.0, still mostly accurate — see "Drift
since" below).

---

## 1 · Project at a glance

- **What it is:** unchanged from spec 0015 — two-agent research orchestrator + local read-only observability dashboard.
- **Current version:** `0.16.1`. This handoff is spec 0017 (or wherever this lands).
- **Tests:** 223 pytest cases, all green. `uv run pytest tests/ -q`.
- **Backend status:** unchanged since v0.9.0 except for one surgical prompt addition in spec 0016 (`negotiation_turn_prompt` now includes a canonical D-N anchor example so the parser-broadening lands).
- **Frontend status:** stable at v0.15.0 + the spec-0016 fixes layered on top in v0.16.1.
- **Integration status:** ✓ **end-to-end live path verified**. Spec 0016 closed the P0/P1 catalogue from the previous session. P2 cosmetic cluster is open; one pre-existing crash (ErrorCard on `errored` runs) is logged.

---

## 2 · What changed in spec 0016 (v0.16.1)

Five interpretation-layer fixes triggered by the first concurrent live run
(test-tier `Compare SQLite vs Postgres`, 13 min, $0.42, APPROVED). The
SSE / file-watch mechanics worked end-to-end; what was wrong was how the
snapshot was read into the timeline.

| ID | What | File |
|---|---|---|
| I1 | Per-phase round counts now from `phaseStats` keys, not the global `run.round.current` | `ui/static/live-data.jsx::buildLiveTimeline` |
| I2 | Disagreement parser accepts `### D-N`, `N.`, `N)` anchors + bare `<label> — <state>` tails; reads `## Final-surfaced` and `## Resolved or non-blocking differences` sibling sections; merges per-id across sections | `ui/disagreements.py` |
| I2 (prompt) | `negotiation_turn_prompt` includes canonical open-form + terminal-form examples so agents emit a parseable shape | `protocol/prompts.py::negotiation_turn_prompt` |
| I3 | `StatusInline` renders a pill for every protocol status (NEGOTIATING / REVIEWING / DISAGREED in addition to AGREED / APPROVED / NOT_APPROVED) | `ui/static/run-detail.jsx::StatsChips`, `::StatusInline` |
| I4 | Phase 0 "needs input" chip uses `max(claude, gpt)` instead of `claude + gpt` | `ui/static/live-data.jsx::attachItemStats` |
| I5 | New `Run.disagreements_parse_suspected_miss` flag (set when parser returns empty but round files contain literal `D-<digit>`); UI shows a one-line muted footer in the Disagreement Explorer | `ui/models.py`, `ui/aggregator.py`, `ui/static/run-detail.jsx` |

The first live-test run rendered as expected after the fixes: 4 Phase 2
rounds shown (was 3), 6 disagreements reconstructed (was 0), every turn
card has a status pill, `needs input · 12` (was `· 16`).

---

## 3 · Drift since `frontend-state.md`

Specifically the v0.15.0 frontend handoff has these items that no longer apply (or apply less):

- **Section 11 / I1**: "phase 2/4 round enumeration overwrites" — **fixed in 0016.**
- **Section 11 / I2**: "disagreement parser tolerates two line formats" — **broadened in 0016**; now five formats + three sibling sections.
- **Section 11**: "in-flight error rendering has not been observed" — **partially observed**: the live test surfaced `INVALID_TURN_FORMAT` + `SOFT_CAP_HIT` in the top-right errors counter as expected.
- **New `Run` field**: `disagreements_parse_suspected_miss: bool` (camelCased `disagreementsParseSuspectedMiss` at the wire).

Everything else in `frontend-state.md` is still load-bearing.

---

## 4 · What is still open

### P2 cosmetic cluster (intentionally deferred from spec 0016)

| # | Issue | Surface |
|---|---|---|
| I6 | Old fixture runs show as `running` forever; no liveness probe in the status state machine | `ui/labels.py` |
| I8 | `agents.{agent}.currentTurn.body` keeps the full final-doc text (~10 KB) in every SSE snapshot after run completion — wasteful but cosmetic | `ui/aggregator.py` |
| I9 | "connected · localhost · 6173" pill renders on the All-runs view where there is no SSE, only 3 s polling | `ui/static/app.jsx` |
| I10 | `final.md` metadata header reports a duration that doesn't match `metrics.json` (17m 51s shown vs ~13 min actual). Backend artifact only. | `orchestrator/finalize.py` |

All four are non-overlapping. Could be one PATCH spec ("Live-run polish")
or four tiny specs. None block normal use.

### Pre-existing bug spun off

- **I11. `ErrorCard` crashes on `errored` runs.** Opening
  `#/runs/20260515-120623-prod-postgres-vs-sqlite` (a rate-limit-aborted
  Phase 2 run) blanks the entire detail view. React error boundary fires
  inside `ErrorCard` at `run-detail.jsx:827`. The run's `error` field is
  well-formed; the bug is in the rendering. Confirmed pre-existing on
  `main` during 0016 implementation — not introduced by 0016. Already
  spun off as a follow-up task (a chip should be visible in the
  user-facing session UI). One-line fix, likely.

### Larger structural items (not changed since v0.15.0)

- Per-token streaming inside `currentTurn.body` — still file-watch-only.
- All-runs list still polls every 3 s; no global SSE feed.

---

## 5 · How to spot-check the v0.16.1 fixes

Fast: open the historical run `20260515-163105-live-integration-test`
in the UI (`#/runs/...`) and confirm:

- Phase 2 divider says "4 rounds" (was "3 rounds" pre-fix).
- All 6 disagreements appear under the Phase 2 Negotiate tab (was empty).
- Every Phase 2 turn card has a status pill: `negotiating` (grey) or `agreed` (green).
- Phase 0 input chip reads `needs input · 12` (was `· 16`).

Or fire a fresh test-tier run and watch the same things populate live.

---

## 6 · Engineering workflow

Unchanged from `CONTRIBUTING.md`. Next spec number is **0017**.

---

*Generated 2026-05-15 at v0.16.1. Companion to `handoffs/integration-observations.md` (raw observations from the first concurrent run).*
