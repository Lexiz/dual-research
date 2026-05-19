# Queue v2 — Phase 1 discovery: current state of the repo

> Audited 2026-05-19 against `main` at `7a21deb` (v0.72.0). The audit
> looked for an existing autonomous queue + dashboard system that
> would shipped specs 0078–0091, and documents what was actually
> found vs. what the v2 brief assumed.

## Bottom line

**There is no pre-existing autonomous queue or queue-dashboard in
this repo.** Specs 0078 → 0091 were shipped manually one-spec-at-a-
time using the workflow documented in `CONTRIBUTING.md`. The
hand-off log explicitly reinforces this: `handoffs/2026-05-19-data-
integrity-arc-complete.md` § 5 lists `Pause between specs, even when
blanket-greenlit` as a workflow lesson, and the user's auto-memory
carries a matching `feedback_pause_between_specs.md` entry.

That makes Phase 2 a **build** rather than an **extend**: the queue
infrastructure does not exist on `main` and we are creating it net-
new on `queue-v2-orchestration`.

## What was searched

```
ls scripts/ .claude/ orchestration/ queue/ tui/
find . -type f -name "*queue*" -o -name "*orchestrat*" -o -name "*dashboard*"
grep -rE "(next.spec|spec.next|auto.merge|spec.queue|queue.next)"
git log --all --since=2026-05-17 --until=2026-05-19 --oneline
```

Concrete findings:

| Location | What's there | Relevance to a spec queue |
|---|---|---|
| `scripts/setup-stable-worktree.sh` | Bootstraps a stable worktree at `~/dual-research-stable` for parallel CLI invocations. | None — it's the dual-research **runtime** isolation tool, not a spec orchestrator. |
| `src/dual_research/orchestrator/` | `phase0.py` … `phase4.py`, `run.py`, `finalize.py`, `repair.py`. | This is the **AI-agent-negotiation orchestrator** (Phase 0 critique through Phase 4 review). Nothing here speaks to spec lifecycle or queue mechanics. |
| `tests/orchestrator/` | 10 pytest modules covering the run-time orchestrator. | Same scope as above. |
| `.claude/` | `launch.json`, `settings.local.json` (permission allow-list), `skills/dual-research-run/SKILL.md`. | Permission allow-list pre-approves git/gh/uv commands. The `dual-research-run` skill triggers a research run, not a spec implementation. |
| `.github/workflows/` | `tests.yml` (pytest on push/PR), `reconcile-costs.yml` (daily cron). | CI for spec PRs; no queue trigger. |
| `Makefile` | One target: `stable-worktree`. | Not a queue entrypoint. |
| `CONTRIBUTING.md` | Documents `spec → branch → implement → PR → admin squash-merge → next spec` as the **human** flow. | This *is* the workflow the queue will automate. |
| `handoffs/` | 39 files, one per spec or per arc — `2026-05-16-…` through `2026-05-19-data-integrity-arc-complete.md`. | Confirms the prior workflow was per-spec manual + per-spec handover, not autonomous. Queue v2 reuses this directory and naming convention for Step 8 Handover output. |

## What does exist that the queue must integrate with

Even though no queue exists, the queue's eight steps lean on a set
of stable repo conventions and outside services. Each is locked in
on `main`:

### Branch / PR / merge cadence
`CONTRIBUTING.md` §§ 2-6 fix the cadence the queue must replicate:

- Branch off `main`, naming `spec/NNNN-<slug>` (the queue uses the
  spec's filename as the source of truth).
- One spec ↔ one branch ↔ one PR.
- Apply exactly one `spec/<label>` GitHub label per PR. Label =
  spec front-matter `label:` value (`new-feature` · `bug` ·
  `refactoring` · `test` · `breaking`).
- Bump `pyproject.toml` and `src/dual_research/__init__.py`
  `__version__` per the label → semver table at
  `CONTRIBUTING.md:95-101`.
- Squash-merge with admin (`gh pr merge --admin --squash --delete-
  branch`) — the squash subject becomes the merge commit on `main`.
- After merge: `git checkout main && git pull` before the next
  spec begins.

### PR template
`.github/PULL_REQUEST_TEMPLATE.md` defines the body shape. Step 6
PR script renders the same sections (Spec link · Summary · Changes
· Version · Checklist) with the queue's data filled in.

### Hosted deploy
`fly.toml` deploys to `dual-research-alex.fly.dev` with a
`/api/health` probe. Step 7 Deploy waits for CI green, then
`fly deploy`, then polls `https://dual-research-alex.fly.dev/api/
health` until the returned `version` field matches the post-bump
version.

### Static-asset cache-bust
The existing UI bumps a `?v=NNNN` cache-bust on every `<link>`
and `<script>` in `src/dual_research/ui/static/index.html`. The
arc handover (§ "Static-asset cache-bust: v=0089 → v=0093") shows
this pattern. Spec 0092 explicitly bumps to `v=0094`. The queue
does NOT touch this file (`src/dual_research/ui/static/` is reserved
for spec runs), but Step 7 Deploy must still verify the cache-bust
landed in the merged commit so the deployed page picks up new CSS.

### CHANGELOG
Per-version sections under `## [X.Y.Z] — YYYY-MM-DD`. The spec
implementer writes its entry inside Step 4 Implement.

### Live preview MCP
The `preview_*` MCP tools (preview_start, preview_resize,
preview_screenshot, …) are wired in the user's Claude Code config
and were the canonical UI verification surface in the 2026-05-18
tweak cycle and the 2026-05-19 data-integrity arc (referenced in
`handoffs/2026-05-19-data-integrity-arc-complete.md` § 6 Fresh-
session bootstrap prompt). Step 5 Verify uses these tools directly.

### Briefing bundle (lives on a separate branch)
`docs/design-system-v2/` is on `origin/design-system-v2-briefing`,
not yet merged to `main` at the time of this audit. Step 5 Verify
reads:
- `docs/design-system-v2/notion-issues/ISSUES.md` (17 issues
  verbatim);
- `docs/design-system-v2/notion-issues/screenshots/01-*.png …
  17-*.png` (21 reference shots of the *broken* state);
- `docs/design-system-v2/assets/Design System v2.html` (M3
  canonical visual reference);
- `docs/design-system-v2/README.md` (the briefing; § 11 is the
  validation checklist).

The queue's trigger command in Phase 4 includes a precondition
check that these files exist on the working `main` (after the
briefing PR also merges).

### Spec drafts (lives on a separate branch)
The 13 spec files at `specs/0092-*.md` … `specs/0104-*.md` are on
`origin/specs-v2-draft`, not yet merged. Each spec follows a fixed
template with these queue-relevant section headers:

```
## 1. Goal
## 2. Files touched
## 3. Material 3 anatomy
## 4. Notion issues addressed
## 5. Acceptance criteria
## 6. Visual verification matrix
## 7. Anti-pattern checks
## 8. Handover read
## 9. Spec rewrite mandate
## 10. Backend touched?
## 11. CSS class anchor list
```

Step 1 Read parses these section headers and operates on the
lists inside them. The queue does **not** care about the prose.

## What needs to be built (preview into Phase 2)

A net-new directory tree on `queue-v2-orchestration`:

```
queue/                              # new
  __init__.py
  cli.py                            # `python -m queue.cli <step> [args]` entrypoint
  parse_spec.py                     # Step 1 — section header parser
  reason.py                         # Step 2 — alignment-note generator
  rewrite.py                        # Step 3 — in-place spec edits
  implement.py                      # Step 4 — branch + scope guard
  verify.py                         # Step 5 — preview_* orchestration + diff
  pr.py                             # Step 6 — gh pr create
  deploy.py                         # Step 7 — CI wait + fly deploy + health probe
  handover.py                       # Step 8 — handoffs/<date>-spec-<NNNN>-<slug>.md
  state.py                          # shared queue state (queue/state.json, queue/runs/<NNNN>/*)
  timings.py                        # queue/timings.json append + median read
  dashboard/                        # Phase 3
    server.py                       # FastAPI-served HTML/JS (mirrors dual-research ui server)
    static/
      index.html
      dashboard.css
      dashboard.js
    state_feed.py                   # SSE stream of (left-panel, right-panel) state
tests/queue/                        # new
  test_parse_spec.py
  test_reason.py
  test_verify_compare.py
  test_state.py
scripts/
  run-queue-v2.sh                   # Phase 4 trigger entrypoint
docs/queue-v2/
  CURRENT-STATE.md                  # this file
  RUNBOOK.md                        # Phase 4 runbook
```

Run-time state lives at:

```
queue/
  state.json                        # which spec is in-flight, queue index, last-completed
  timings.json                      # accumulated step durations per step id
  runs/
    <NNNN>/
      spec-parsed.json              # Step 1 output
      reason-notes.md               # Step 2 output
      rewrite-log.md                # Step 3 output (if any)
      implement-log.md              # Step 4 diff stats
      verify-report.md              # Step 5 verdicts
      screenshots/                  # Step 5 PNGs
      pr-url.txt                    # Step 6 output
      deploy-log.md                 # Step 7 output
      handover-path.txt             # Step 8 output pointer
```

`queue/` is git-ignored except for the tracked source code under
`queue/<module>.py` and `queue/dashboard/`. Runtime artifacts under
`queue/runs/`, `queue/state.json`, and `queue/timings.json` are
local-only.

## Constraints the build will honour

- No edits to `specs/`. Step 3 Rewrite is the only step that writes
  to that directory, and only while a spec is mid-flight — the
  queue infrastructure does not pre-commit spec files.
- No edits to `src/dual_research/ui/static/`. Step 4 Implement runs
  spec code; the queue infrastructure does not.
- No edits to `docs/design-system-v2/`. Step 5 Verify reads from
  it; nothing else.
- The Read → Reason → Rewrite triad is mandatory at the start of
  every spec — it is the cross-spec drift safety net.
- All queue scripts are independently invocable so each step can
  be unit-tested and re-run in isolation when an operator goes back
  to fix a failed Verify.

## Open questions surfaced by discovery

None blocking. The brief's premise that "a previous session built
an autonomous queue that shipped specs 0078–0091" is **not borne
out** by the repo state. The phrasing appears to be a forward-
looking description of what *should* exist after this PR lands —
or a paraphrase of the manual workflow the human + assistant pair
used over 2026-05-17 → 2026-05-19. Either way, the build proceeds
unchanged: the queue is the deliverable, the 13 design-system
specs are its first workload, and Phase 1's job is just to set the
baseline honestly. Done.
