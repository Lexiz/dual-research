---
spec: "0248"
date: 2026-05-28
version: "1.61.0"
pr: "https://github.com/Lexiz/dual-research/pull/286"
kind: post-deploy
---

# Spec 0248 — All Runs card refinements + rich provider metric bands

New-feature (MINOR, 1.60.3 → 1.61.0). Five All Runs card refinements
following [spec 0246](specs/0246-all-runs-card-layout-rewrite.md) (card
layout) and [spec 0245](specs/0245-archive-runs.md) (archive). All
landed in one PR; the only non-trivial piece is §2.5's write-time
critique tally.

## What landed

- **§2.1 Chrome cleanup** — removed the `ProjectStrip` wordmark component
  + render from `run-list.jsx`; dropped `.ar-project*` from both CSS
  files; tightened `.ar-page` top padding 24 → 18 px.
- **§2.2 Avatar menu restored** — `AvatarMenu` / `AvatarDisc` / `MenuItem`
  physically moved from `app.jsx` into `run-list.jsx` (which loads first,
  so `app.jsx`'s `RightCluster` still references them as globals — the
  same cross-`<script type=text/babel>` global-scope behaviour that lets
  `run-list.jsx` use `Icon` / `Modal` from earlier-loaded files). Mounted
  in `AllRunsChrome` in place of the bare `.ar-avatar` initial span
  (`.ar-avatar` CSS removed); `client` / `session` threaded
  `App → ListScreen → AllRunsPage → AllRunsChrome`. Session-gated, so it
  renders only in hosted mode.
- **§2.3 Inline archive tray** — replaced the floating `.rc-archive-btn`
  icon button + full-screen `ConfirmArchiveDialog` / `ConfirmUnarchiveDialog`
  `Modal`s with a hover `.rc-tray` (grid-area `tray`). Prompt → in-place
  confirm; `.is-confirming` keeps it expanded through a mid-confirm
  pointer-leave. The page-level archive/restore handlers were refactored
  from shared `archiveTarget` state to take the run directly
  (`handleArchive(target)` / `handleUnarchive(target)`); endpoints
  unchanged (`POST` / `DELETE /api/runs/{id}/archive`).
- **§2.4 Note width** — `.run-card` grid template changed to
  `"head head" / "phases agents" / "note agents" / "tray tray"` with
  `align-items: start`, `.rc-phases { align-self: start }`,
  `.rc-note { align-self: end }`, so the terminal note occupies only the
  left (phase-strip) column and the provider bands span the reclaimed
  vertical space.
- **§2.5 Rich provider metric bands** — `AgentRow` → `ProviderCard`:
  brand logo (`BrandMark`) in a brand-tinted square + spine, provider
  name with total tokens, cost with a divider, then Questions /
  Disagreements / Issues `raised` / `solved` badge pairs (Q→D→I, DS §9.3
  category tones as tinted leading letters) + a searches count. Tone
  mapping per spec: raised → neutral, solved → ok, searches → info.
  - Backend: `AgentBreakdown` gains `tokens` / `searches` / `critique`;
    `Metrics` gains `critique_by_agent` (serialised in `to_json`,
    rehydrated in `load`). New helper
    `src/dual_research/ui/critique_tally.py::compute_critique_by_agent`
    replays the item pipeline (preferred) with a `reconstruct_*` fallback
    and tallies per-agent `(raised, solved)` where solved = `status != "open"`.
    The orchestrator calls `_populate_critique_tally` before each of the
    three terminal `metrics.save()` sites in `run.py` (not the per-turn
    cost ticker — once per run). `derive_agent_breakdowns` reads tokens /
    searches from `totals_by_agent` (cheap, universal) and the tallies
    from `critique_by_agent`; `summarize_run` never replays transcripts (a
    cheap-path guard test enforces this). Both fs and supabase list paths
    funnel through `derive_agent_breakdowns`, so one change covers both.
- DS: new composed components documented at `design-system/SPEC.md`
  §4.9 (provider band) / §4.10 (archive tray); CSS mirrored verbatim in
  `components.css` + `composed-components.css`.
- Tests: `tests/test_spec_0248_all_runs.py` (12 tests — source-pattern
  anatomy + antipodal absence, both-CSS sync, the tally helper against a
  synthetic fixture session dir through the real item pipeline,
  `derive_agent_breakdowns` reads + old-run zero-degradation, cheap-path
  guard). Superseded prior-spec tests updated to the new contract
  (`test_spec_0245_run_row_archive_button.py`,
  `test_spec_0246_all_runs.py`). Version + CHANGELOG + version-notes
  sidecar (235 entries).

## Verification this cycle

- Full suite **2376 passed**.
- Runtime verified via Claude Preview MCP in light + dark, no console
  errors: chrome cleanup (§2.1), note-left-column alignment (§2.4), and
  the provider bands (§2.5) all render. DOM probe:
  `CLAUDE | 1.7M tokens | $6.86 | Q 6 6 | D 5 5 | I 6 2 | search 32`.
  The avatar menu (§2.2) and tray (§2.3) are auth-gated → hosted-mode
  only; locked here by source-pattern tests.
- The tally helper was also run directly against real run
  `20260526-000758` and produced non-zero per-agent tallies (Claude
  Q 6/6 · D 5/5 · I 6/2; GPT Q 7/6 · D 10/10 · I 16/4), confirming the
  item-pipeline path works on a live v2 run.

## Deploy note (transient fly health-check flake)

The first `deploy.yml` run for merge commit `f706f1d` **failed** — but
not on code: the `test` job passed and the image built + pushed fine.
The fly.io rolling deploy timed out waiting for the machine health check
(`net/http: request canceled` — a fly machines-API flake; the machine
had reached `started`). The live app stayed healthy on 1.60.3 (no
outage). A `gh run rerun --failed` on the same commit succeeded; the
live app now reports **1.61.0** / HTTP 200. No code change was needed —
this was infrastructure, not a spec-0248 defect.

## Deferred during implementation

- **Live provider-band tallies for new runs only.** The persisted
  `critique_by_agent` is written by the orchestrator's terminal saves, so
  the rich Q/D/I tallies populate only for runs created after this deploy.
  Existing runs render `0`/`0` (documented §7 degradation). A one-off
  backfill that recomputes `critique_by_agent` for historical
  `metrics.json` files (running `compute_critique_by_agent` over the runs
  dir) would light up the bands for the current corpus, but spec 0248 §5
  explicitly scoped that out ("not worth a one-off migration"). Captured
  here as a noticed-during-implementation follow-up; default disposition
  archive unless the empty bands on old runs prove annoying in practice.
