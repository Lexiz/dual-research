# Handover — design-system arc complete (v0.59.1) → ready for tweak/fix cycle

**Date:** 2026-05-18
**Hosted:** [`dual-research-alex.fly.dev/api/health`](https://dual-research-alex.fly.dev/api/health) → `{"ok":true,"version":"0.59.1","backend":"supabase"}`
**Branch:** `main` (clean)
**Last commit on `main`:** `946a456 0.59.1 hotfix — expose AgentDuoVisual on window for onboarding consumption (#66)`
**Tests:** 735 green
**Working tree:** clean
**Open PRs:** 0
**Active automation:** none (orchestrator finished, all processes killed)

---

## 0 · Bottom line for the new session

You are picking up an **interactive review + tweak cycle** on a shipped design-system migration. The entire 11-spec Claude Design migration arc shipped yesterday (2026-05-17, GMT+2) — SPEC-0050 through SPEC-0061, plus four hotfixes. The user is now interactively using the deployed UI at [dual-research-alex.fly.dev](https://dual-research-alex.fly.dev) and has a list of things to fix / adjust / tweak.

Your job, in order:

1. **Read this handover end-to-end** before doing anything else.
2. **Read the actual code shipped** across the 14 PRs listed in §3 (focus on the JSX surface files + CHANGELOG + each spec doc in `specs/`). The handover tells you what to look at; the code tells you what shipped. The handover may have minor inaccuracies — the code is ground truth.
3. **Spin up the dev server** (`uv run dual-research serve --host 127.0.0.1 --port 6173`) and open the deployed hosted version side-by-side. Familiarize yourself with the live UI before receiving feedback. The partner-vetting run (`runs/20260516-035048-partner-vetting-arch-critique/`, ID `3a4a`) is the canonical fixture with every kind of artifact.
4. **Confirm readiness.** When you have read this doc + read the code + understood the system, say literally: **"I'm ready to receive your briefing."** Then stop and wait. The user will then dump their full list of issues / tweaks / adjustments.
5. **Process the briefing.** Receive whatever the user pastes (which may be unstructured — a flat list, a screenshot, a stream of consciousness). Your job: **read · structure · review · assess · cluster into specs**.
6. **Pre-draft all specs exhaustively** into `~/dual-research-automation/drafts/NNNN-<slug>.md` (numbering starts from `0067` — next available, since `0061` was the last shipped). One spec per coherent change cluster (~50–500 LOC of work each). Use the same draft format and rigor as the existing drafts at `~/dual-research-automation/drafts/0053-*.md` … `0061-*.md`. **Drafts are starting templates the implementing session refines** — they are not contracts.
7. **Reset the automation state** (see §4.4 for exact commands). Updates: `state/queue.txt` with the new numbers, clear `state/current.txt` + `state/phase.txt` + `state/halt.flag`, optionally archive the old `state/history.jsonl`. Update `~/dual-research-automation/arc.md` to describe this new tweak-cycle arc.
8. **Hand the user a single kickoff command** (`~/dual-research-automation/start.sh`) that will, when run from a fresh Mac Terminal tab, kick off the same orchestrator + tmux dashboard cycle that ran tonight. The user does not want to write any code or run any other commands — just paste one line, hit `y`, and walk away.

Throughout: **do not start implementing any of the new specs yourself.** Your job is to spec + pre-draft + hand off. The autonomous orchestrator implements them, one at a time, in fresh sessions per spec.

---

## 1 · Fresh-session bootstrap prompt (the user will paste this into a new Claude Code session)

```
You are picking up the dual-research design-system implementation
work — interactive tweak/fix cycle on a shipped 11-spec arc.

Read the handover at
/Users/alexlisitzky/dual-research/handoffs/2026-05-18-design-system-arc-complete-tweak-cycle-kickoff.md
cover-to-cover before doing anything else. It explains exhaustively
what we built, how we built it, the automation system we used, and
what I want you to do next.

After reading the handover, also read the actual production code
the handover points you at (the JSX surface files + each shipped
spec doc + CHANGELOG entries) so you understand current state of
main. Spin up the dev server and look at the live UI in a browser
side-by-side with the hosted version at
https://dual-research-alex.fly.dev.

When you have read everything and feel oriented, say literally:
"I'm ready to receive your briefing."  Then stop.

I will then paste my list of tweaks/issues. You'll process and
structure it into N specs, pre-draft all of them in exhaustive
detail into ~/dual-research-automation/drafts/, reset the
automation state, and hand me a single kickoff command for the
orchestrator. Do NOT start implementing any of the specs yourself;
the orchestrator does that autonomously, one spec at a time.
```

That's it. Copy verbatim into the new session.

---

## 2 · Production state right now

The user is using the live hosted app at [dual-research-alex.fly.dev](https://dual-research-alex.fly.dev). Reload with `Cmd+Shift+R` to bypass cache after every deploy — every spec bumps the `?v=NNNN` cache-bust on local CSS/JSX in `index.html`. Current cache-bust value: `?v=0591`.

What's live (high level):
- **Foundation** — IBM Plex Sans + IBM Plex Serif fonts; tokenized color/spacing/radius/elevation/motion system; global `:focus-visible` ring; reduced-motion contract; MDI icon set (~60 icons via `<Mdi>`).
- **Primitives** — `Button`, `StatusBadge` (legacy + new `SB`), `Chip`, `RunIDChip`, `Card` (base/expandable/live), `AgentStrip`, segmented `ThemeToggle`, `Tab` (3 variants: default/line/solid), `QuestionThread`, `QuestionRef`, `Modal` (single/split), `ChipCluster`, `PhaseRail`, plus various inline composites.
- **Run list** — sortable columns, URL-persisted sort/filter/search state, `/`-bound search focus, "Needs attention" attention-first row promotion (errored/deadlocked rows get colored left border + lift to top group), filter Tabs.
- **Run detail** — restructured two-row header with drafter pill + blocking-item callout; chrome bar unified into single `TabGroup`; `ActiveRunChip` for one-click back-to-list; sticky `PhaseRail` down timeline pane; `Card.expandable`/`Card.live` everywhere; three-axis critique filter (kind/agent/status); `DriftCluster` group above OPEN/RESOLVED; Σ Summary panel; `QuestionThread` embedded in expanded critique cards.
- **Modals** — single + split variants with 3 px agent-color left border; sub-tabs use `tabs-line` variant; `RoundScrubber` walks turns without closing; provider-symmetric `SourceCard`.
- **Keyboard** — global keydown handler, `↑/↓` + `j/k` walks rows, `Enter` opens, `Esc` closes, `?` opens shortcuts overlay, `⌘K`/`Ctrl+K` opens search palette, `/` focuses run-list search.
- **Cross-run dashboards** — `/compare` (two-run side-by-side with synced scroll + δ markers) and `/search` (cross-run search dashboard with new server endpoint).
- **Onboarding + landing** — 3-screen onboarding carousel on first hosted-mode sign-in; auth-free landing with `DemoRunCapsule` showing the partner-vetting run.
- **Consumption tab rework** (parallel to design-system arc) — content vs. billing split, output bar colored by destination input slot, `× N reuse` chip, input/output cost split, `effectiveTokensIn` helper.

---

## 3 · What shipped today and yesterday (chronological PR list)

Fourteen PRs merged to `main` between 16:59 UTC (2026-05-17) and 00:04 UTC (2026-05-18). All squash-merged via `gh pr merge --admin --squash`.

| PR  | Spec     | Version       | Merged (UTC)  | Title |
|-----|----------|---------------|---------------|-------|
| [#51](https://github.com/Lexiz/dual-research/pull/51) | 0049 | 0.46.1 → 0.47.0 | 16:59         | Reconcile-costs reads from Supabase + daily cron re-enabled |
| [#52](https://github.com/Lexiz/dual-research/pull/52) | 0.47.1 hotfix | 0.47.0 → 0.47.1 | 18:03 | Consumption tab counts cached tokens |
| [#53](https://github.com/Lexiz/dual-research/pull/53) | 0050 | 0.47.1 → 0.48.0 | 18:15 | Design-system foundation — tokens, base, a11y, MDI, no emoji |
| [#54](https://github.com/Lexiz/dual-research/pull/54) | 0.48.1 hotfix | 0.48.0 → 0.48.1 | 18:33 | Check in partner-vetting fixture so CI tests.yml passes |
| [#55](https://github.com/Lexiz/dual-research/pull/55) | 0051 | 0.48.1 → 0.49.0 | 18:59 | Consumption tab — content-vs-billing split + output bar + cross-turn lineage |
| [#56](https://github.com/Lexiz/dual-research/pull/56) | 0052 | 0.49.0 → 0.50.0 | 19:06 | Primitive vocabulary (Button, Chip, SB, RunIDChip, Card, AgentStrip, segmented ThemeToggle) |
| [#57](https://github.com/Lexiz/dual-research/pull/57) | 0053 | 0.50.0 → 0.51.0 | ~20:00 | Tab system (3 variants) + table header |
| [#58](https://github.com/Lexiz/dual-research/pull/58) | 0054 | 0.51.0 → 0.52.0 | ~20:15 | QuestionThread + QuestionRef + AP-01 enforcement |
| [#59](https://github.com/Lexiz/dual-research/pull/59) | 0055 | 0.52.0 → 0.53.0 | ~20:30 | Run list sort + attention + filters + search |
| [#60](https://github.com/Lexiz/dual-research/pull/60) | 0056 | 0.53.0 → 0.54.0 | 20:42 | Run detail header + chrome restructure + ActiveRunChip |
| [#61](https://github.com/Lexiz/dual-research/pull/61) | 0057 | 0.54.0 → 0.55.0 | 20:55 | Timeline + critique restructure |
| [#62](https://github.com/Lexiz/dual-research/pull/62) | 0058 | 0.55.0 → 0.56.0 | 21:05 | Modal primitive + RoundScrubber + provider-symmetric SourceCard |
| [#63](https://github.com/Lexiz/dual-research/pull/63) | 0059 | 0.56.0 → 0.57.0 | 21:22 | Keyboard contract + shortcuts overlay + search palette |
| [#64](https://github.com/Lexiz/dual-research/pull/64) | 0060 | 0.57.0 → 0.58.0 | 21:34 | Cross-run dashboards: `/compare` + `/search` |
| [#65](https://github.com/Lexiz/dual-research/pull/65) | 0061 | 0.58.0 → 0.59.0 | 21:38 | Onboarding (3-screen flow) + landing demo capsule |
| [#66](https://github.com/Lexiz/dual-research/pull/66) | 0.59.1 hotfix | 0.59.0 → 0.59.1 | ~23:55 | Expose `AgentDuoVisual` on window for onboarding consumption |

**Per-spec handover docs** live in `handoffs/2026-05-17-spec-NNNN.md` (one per shipped arc spec; the orchestrator wrote each automatically as part of the per-spec pipeline). Each handover documents: what shipped vs draft, files touched, mid-flight refinements, downstream invalidations, verification snapshot. **Read these for the actual state of each shipped surface** — they're more detailed than the PR descriptions.

`handoffs/latest-arc.md` is a symlink to the most recent (currently `2026-05-17-spec-0061.md`).

---

## 4 · The automation system (this is how everything shipped autonomously)

### 4.1 · What it is

A small bash orchestrator + tmux dashboard + pre-drafted spec templates, all sitting **outside the repo** at `~/dual-research-automation/`. The directory is not committed; it's the user's local workspace for autonomous-arc execution. The orchestrator fires one headless `claude --print` session per spec sequentially, with full pipeline (draft → branch → implement → test → preview-verify → version bump → CHANGELOG → PR → admin-squash merge → fly deploy → `/api/health` verify → write handover → exit). It advances on success and halts on failure.

This was built tonight, used to ship SPEC-0053..0061 fully unattended (the user kicked it off at ~21:42 UTC and walked away; arc finished at 23:38). It works. **Reuse it as-is for the tweak cycle.**

### 4.2 · Directory layout

```
~/dual-research-automation/
├── README.md                   ← detailed usage doc
├── arc.md                      ← arc-wide context loaded by every per-spec session
├── start.sh                    ← kick-off entry point (the one command the user runs)
├── orchestrator.sh             ← queue loop (you don't run this directly)
├── monitor.sh                  ← tmux dashboard setup
├── dashboard-specs.sh          ← left pane of dashboard (spec list + status)
├── dashboard-current.sh        ← right pane (current spec phases + ETA)
├── dashboard.sh                ← legacy single-pane dashboard (unused after rebuild)
├── tail-current.sh             ← live tail helper for log pane
├── phase-detector.sh           ← background daemon inferring current phase from external state
├── resume.sh                   ← halt-recovery helper (--status, --skip, --requeue NNNN)
├── prompts/
│   ├── per-spec.md             ← template prompt fed to each `claude -p` session
│   └── handover.md             ← template handover format each session must fill
├── drafts/                     ← pre-drafted spec templates (one per spec; the implementing session refines)
│   └── 00NN-<slug>.md  × 9     ← (these are leftover from the shipped arc — overwrite for the new arc)
├── state/
│   ├── queue.txt               ← remaining spec numbers, one per line
│   ├── current.txt             ← spec in flight + pid + start timestamp
│   ├── history.jsonl           ← one line per completed spec (status, ts, version, PR#)
│   ├── phase.txt               ← currently-detected phase for current spec
│   ├── phase-history.jsonl     ← phase transitions with durations
│   └── halt.flag               ← exists only when orchestrator stopped (failure)
└── logs/
    ├── orchestrator.log        ← orchestrator's own log (▶ Starting / ✓ succeeded / ✗ halted lines)
    ├── phase-detector.log      ← phase detector's log
    └── 00NN-YYYYMMDD-HHMMSS.log ← per-spec claude session output (silent until session ends in --print text mode)
```

### 4.3 · How it actually runs (the user's perspective)

User opens a fresh Mac terminal tab (not inside any other tmux session and not inside Claude Code), runs:

```bash
~/dual-research-automation/start.sh
```

`start.sh` prompts `Proceed? [y/N]`. User types `y`. Then:

- `start.sh` creates a tmux session called `dr-arc` with one window (`orchestrator`) and kicks off `orchestrator.sh` inside it.
- `start.sh` then calls `monitor.sh` which creates a second window (`monitor`) with 3 panes: spec list (top-left), current-spec phase pipeline (top-right, with phase highlight + Typical and Elapsed columns + ETA), orchestrator log tail (bottom).
- The user is attached to the `monitor` window; switch to `orchestrator` with `Ctrl+B 0`, back to `monitor` with `Ctrl+B 1`.
- User can detach (`Ctrl+B d`), close the terminal, walk away. Re-attach later with `tmux attach -t dr-arc:monitor` **from a fresh Mac terminal tab** (not from inside another tmux session).

The `phase-detector.sh` daemon (auto-spawned by `monitor.sh` idempotently) polls every 3 s for: branch existence, PR existence, PR state, `/api/health` version, handover file existence. It writes the current phase (one of: `read` / `implement` / `pr` / `deploy` / `handover` / `done`) to `state/phase.txt` and appends transitions with duration to `state/phase-history.jsonl`. The dashboard reads these files.

For each spec, the orchestrator builds a prompt from `prompts/per-spec.md` (with `{{SPEC}}` substituted), then runs:

```bash
claude --print \
  --dangerously-skip-permissions \
  --max-budget-usd 50 \
  --name spec-NNNN \
  --model opus \
  --add-dir ~/dual-research-automation \
  --add-dir "~/Downloads/Dual-research dashboard" \
  --append-system-prompt "<reminder it's headless>" \
  "$prompt" > logs/NNNN-<ts>.log 2>&1
```

When that session exits, the orchestrator parses the handover at `handoffs/2026-MM-DD-spec-NNNN.md` for `**Status:** succeeded`, cross-checks `/api/health` reports the version the handover claimed to ship, then either advances the queue (deletes head line of `queue.txt`) or writes `state/halt.flag` and exits.

### 4.4 · What you need to do to use it for the tweak cycle

After you've processed the user's briefing and have N concrete spec drafts ready:

1. **Write your drafts** to `~/dual-research-automation/drafts/0067-<slug>.md`, `0068-<slug>.md`, etc. Use the same Markdown format as `0053-tab-system.md` (read one of the existing drafts as a template — they have front-matter, Context, Design decisions table, Files touched, Out of scope, Test plan, Risks, Brief mapping, Pre-draft notes for the implementing session). Be **exhaustive** — these drafts are read by autonomous sessions with no other context. The richer the draft, the lower the chance of mid-flight scope drift.
2. **Reset state:**
   ```bash
   # archive old history (optional but recommended for clean per-arc dashboards)
   mv ~/dual-research-automation/state/history.jsonl ~/dual-research-automation/state/history-arc1.jsonl
   mv ~/dual-research-automation/state/phase-history.jsonl ~/dual-research-automation/state/phase-history-arc1.jsonl

   # clear in-flight + halt state
   > ~/dual-research-automation/state/current.txt
   > ~/dual-research-automation/state/phase.txt
   rm -f ~/dual-research-automation/state/halt.flag

   # initialise the new queue (replace with your spec numbers, one per line)
   printf "0067\n0068\n0069\n…\n" > ~/dual-research-automation/state/queue.txt

   # initialise new history files (empty)
   touch ~/dual-research-automation/state/history.jsonl
   touch ~/dual-research-automation/state/phase-history.jsonl

   # delete the previous arc's drafts so they don't appear in the dashboard list
   rm ~/dual-research-automation/drafts/005*.md ~/dual-research-automation/drafts/006*.md
   ```
3. **Rewrite `arc.md`** to describe this new tweak-cycle arc — at minimum, replace the "Remaining specs (queue)" table with your new spec numbers + titles + brief one-line scopes + dependencies. Keep "Foundation already shipped" + "Naming conventions" + "Hard constraints" + "Orchestrator" + "Monitor" + "Failure recovery" sections as-is (or update if anything's changed).
4. **Test the kickoff path** (don't actually kick anything — just sanity-check the file you'll hand the user):
   ```bash
   # Verify state is sane
   ~/dual-research-automation/resume.sh --status
   # Verify draft files exist and parse:
   for f in ~/dual-research-automation/drafts/006[7-9]-*.md ~/dual-research-automation/drafts/007*.md; do
     [ -f "$f" ] && echo "✓ $f" || echo "✗ MISSING $f"
   done
   ```
5. **Hand the user the kickoff command verbatim:**
   ```bash
   ~/dual-research-automation/start.sh
   ```
   That's the one line. Tell them: open a fresh Mac terminal tab, paste, type `y` when prompted, leave it running. Then `tmux attach -t dr-arc:monitor` in another fresh tab to watch progress.

### 4.5 · Failure modes the orchestrator catches (already battle-tested tonight)

- Session exits non-zero → halt.
- Handover file missing → halt.
- Handover `status:` not `succeeded` → halt.
- `/api/health` doesn't report expected version after deploy → halt (caught the 0.59.0 → 0.59.1 white-screen issue's cousin: SPEC-0061 succeeded but a follow-up bug emerged; the orchestrator can't catch every kind of regression — preview-verify discipline + post-arc human testing is still required).

If a halt fires, `~/dual-research-automation/resume.sh --status` shows what stopped. Options:
- `resume.sh` (default) → clears halt, retries head spec.
- `resume.sh --skip` → drops head spec from queue, continues.
- `resume.sh --requeue NNNN` → prepends spec NNNN to queue (re-do something).

### 4.6 · Known coordination gotchas (from tonight's run)

- **Hotfixes mid-arc.** Two non-arc PRs landed during the design-system shipping window (#52, #54). Each caused a `gh pr merge` conflict for the next arc spec — the orchestrator's `per-spec.md` workflow says "if conflicting, fetch + merge + resolve + re-test + retry merge", and the sessions handled it correctly each time. Expect similar if any tweak-cycle spec collides with a hotfix.
- **Version collisions.** When two specs target the same MINOR (e.g. spec 0050 and 0.47.1 both targeted 0.48.x via different paths), the conflict resolution requires bumping. Document in the per-spec prompt that "your target-version is the next MINOR available — check `pyproject.toml` at start of work, not the draft's stale value."
- **Browser cache.** Every spec bumps `?v=NNNN` in `index.html` so users get fresh CSS/JSX after deploy. The hotfix at PR #66 used `?v=0591` — your new arc should use unique values (`?v=0067a`, `?v=0068a`, etc. or `?v=NNNN` matching spec number).
- **`tmux attach` from inside another tmux session silently fails.** Always tell the user to open a NEW Mac terminal tab.
- **`watch` is not installed on macOS by default.** Don't use it; the existing dashboard scripts use `while sleep 3; do clear; …; done` instead.

---

## 5 · The brief (source of truth for "the design system")

The original Claude Design brief lives at `/Users/alexlisitzky/Downloads/Dual-research dashboard/`. This is a zip the user got from Claude Design with the full design system + 9 pre-drafted-by-Claude-Design specs (which were the original 11-spec plan; renumbered to 9 after collisions with parallel work tonight).

Key files inside that directory:
- `CLAUDE-CODE-BRIEFING.md` — the original cover-to-cover briefing.
- `exports/DESIGN-SYSTEM.md` — canonical unified design system (~50k chars). §15 is the changelog with every brief-ID (CMP-NN / SUR-NN / A11Y-NN / NEW-NN / TYPE-NN / etc.) implemented across the arc.
- `exports/DESIGN-SYSTEM-V1.md` + `exports/DUAL-RESEARCH-V2.md` — historical V1 + V2 drafts; superseded by DESIGN-SYSTEM.md.
- `styles/tokens.css` — authoritative tokens (already copied verbatim into `src/dual_research/ui/static/tokens.css` in SPEC-0050).
- `styles/base.css` — body + reset + type utilities + focus + motion + markdown (copied in SPEC-0050).
- `styles/components.css` — every component class (selectively copied across specs 0050, 0052, 0053, 0054, 0058 as needed).
- `scripts/primitives.jsx` — React components mirroring components.css (referenced when implementing primitives).
- `scripts/icons.jsx` — MDI icon dictionary + `<Mdi>` (copied in SPEC-0050).
- `final.html` — canonical interactive spec (open in a browser to see every component in both themes; live tokens; segmented theme toggle).
- `handoff/` — the design-side snapshot of production code at the time the brief was packaged. **Stale; don't use as reference for current state.**

When the user's tweak briefing references a design-system concept (e.g., "the QuestionThread should be doing X" or "the chip cluster needs more spacing"), consult `DESIGN-SYSTEM.md` and the per-section `styles/*.css` for the authoritative behavior.

---

## 6 · State of the codebase

### 6.1 · Where things live (production paths, post-arc)

| Surface / concern               | File |
|----------------------------------|------|
| App shell + auth gate + chrome   | [`src/dual_research/ui/static/app.jsx`](../src/dual_research/ui/static/app.jsx) |
| Routing (hash-based)             | [`src/dual_research/ui/static/router.jsx`](../src/dual_research/ui/static/router.jsx) |
| Auth (Supabase wiring)           | [`src/dual_research/ui/static/auth.jsx`](../src/dual_research/ui/static/auth.jsx) |
| Run list                         | [`src/dual_research/ui/static/run-list.jsx`](../src/dual_research/ui/static/run-list.jsx) |
| Run detail (largest file)        | [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) |
| Cross-run /compare               | [`src/dual_research/ui/static/compare.jsx`](../src/dual_research/ui/static/compare.jsx) |
| Cross-run /search                | [`src/dual_research/ui/static/search.jsx`](../src/dual_research/ui/static/search.jsx) |
| Shortcuts overlay (`?`)          | [`src/dual_research/ui/static/shortcuts-overlay.jsx`](../src/dual_research/ui/static/shortcuts-overlay.jsx) |
| Search palette (`⌘K`)            | [`src/dual_research/ui/static/search-palette.jsx`](../src/dual_research/ui/static/search-palette.jsx) |
| Onboarding (3-screen carousel)   | [`src/dual_research/ui/static/onboarding.jsx`](../src/dual_research/ui/static/onboarding.jsx) |
| Errors view                      | [`src/dual_research/ui/static/errors.jsx`](../src/dual_research/ui/static/errors.jsx) |
| Settings                         | [`src/dual_research/ui/static/settings.jsx`](../src/dual_research/ui/static/settings.jsx) |
| Design Language reference page   | [`src/dual_research/ui/static/design-language.jsx`](../src/dual_research/ui/static/design-language.jsx) |
| How it works (in-app changelog)  | [`src/dual_research/ui/static/how-it-works.jsx`](../src/dual_research/ui/static/how-it-works.jsx) |
| Live data builders (timeline)    | [`src/dual_research/ui/static/live-data.jsx`](../src/dual_research/ui/static/live-data.jsx) |
| Shared primitives + helpers      | [`src/dual_research/ui/static/shared.jsx`](../src/dual_research/ui/static/shared.jsx) |
| MDI icon dict + `<Mdi>`          | [`src/dual_research/ui/static/icons.jsx`](../src/dual_research/ui/static/icons.jsx) |
| Tokens (authoritative)           | [`src/dual_research/ui/static/tokens.css`](../src/dual_research/ui/static/tokens.css) |
| Base + reset + animations + md   | [`src/dual_research/ui/static/base.css`](../src/dual_research/ui/static/base.css) |
| Component classes                | [`src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) |
| Legacy class sheet (draining)    | [`src/dual_research/ui/static/theme.css`](../src/dual_research/ui/static/theme.css) |
| Index (script + CSS load order)  | [`src/dual_research/ui/static/index.html`](../src/dual_research/ui/static/index.html) |
| **Off-brand dev panel**          | `src/dual_research/ui/static/tweaks-panel.jsx` ← **DO NOT MODIFY** (intentionally off-brand per brief) |
| Server                           | [`src/dual_research/ui/server.py`](../src/dual_research/ui/server.py) |
| Aggregator (transcript → UI)     | [`src/dual_research/ui/aggregator.py`](../src/dual_research/ui/aggregator.py) |

### 6.2 · Primitives currently exposed on `window` (you can reference these in your specs)

From `shared.jsx`: `COLORS`, `AGENT_META`, `Dot`, `AgentIcon`, `StatusBadge` (legacy), `Pill` (legacy), `MetricRow`, `PanelHeader`, `StreamingText`, `Markdown`, `Modal`, `Icon` (MDI shim with 14 legacy keys), `fmt`, `scrollAndFlash`, `Button`, `SB` (new StatusBadge), `Chip`, `RunIDChip`, `Card`, `CardBody`, `AgentStrip`, `ThemeToggleSegmented`, `Tab`, `TabGroup`, `QuestionThread`, `QuestionRef`, `parseQId`, `ChipCluster`, `PhaseRail`, `Modal*`, `RoundScrubber`, `SourceCard`, …

From `auth.jsx`: `useSupabaseClient`, `useSession`, `useMe`, `authedFetch`, `SignInScreen`, `LandingScreen`, `NotApprovedScreen`, `DemoRunCapsule`, `AgentDuoVisual` (the latter added in the 0.59.1 hotfix).

From `icons.jsx`: `Mdi`, `ICONS`.

From `onboarding.jsx`: `OnboardingScreen`.

From `router.jsx`: `useRoute`, `navigate`, `parseHash`.

### 6.3 · Key conventions

- **All component CSS reads from tokens** — no hex codes in components.
- **Stack:** React UMD + Babel-standalone + marked + Supabase JS. **No build step.** Each JSX file is `<script type="text/babel">`.
- **Theme:** `body.dark` / `body.light` class on `<body>`.
- **Cache-bust:** `?v=NNNN` query string on every local `<link>` and `<script src>` in `index.html`. Bump every spec.
- **Branch naming:** `spec/NNNN-<slug>` (per-spec workflow) or `hotfix/<slug>` (for hotfixes between specs).
- **PR labels:** `spec/new-feature` for new behaviour, `spec/bug` for hotfixes, `spec/refactoring` for internal cleanup with no behaviour change, `spec/breaking` for API breaks.
- **Version semantics:** `breaking` → MAJOR, `new-feature` → MINOR, `bug`/`refactoring`/`test` → PATCH.
- **Merge:** always `gh pr merge <#> --admin --squash --delete-branch`. Never `--auto`. Never amend published commits. Never force-push.

---

## 7 · What the user wants to do next (the workflow you are bootstrapping)

The user has spent the last few hours getting the whole arc deployed autonomously. **They've now opened the live UI and have a list of things that need adjusting** — visual bugs, layout issues, missing edge cases, copy tweaks, behaviour fixes, polish, anything. They have not yet told you what those are; they will dump the list in the next message after you confirm readiness.

The workflow they want, end-to-end:

1. **They paste the bootstrap prompt (from §1) into a fresh Claude Code session.**
2. **You read this handover + read the code + open the live UI** to orient yourself. This may take 10–20 minutes of reading.
3. **You say:** "I'm ready to receive your briefing." (Exact phrasing. Then stop.)
4. **They paste an unstructured dump** of everything they want changed. Could be 5 things or 50. Could be a screenshot. Could be a stream-of-consciousness paragraph. Whatever.
5. **You process the dump.** Read it carefully. Ask clarifying questions if there's true ambiguity (but err on the side of inference + documenting your inference in the spec, vs. asking — the user prefers low-friction).
6. **You cluster the items into specs.** One spec per coherent change cluster. Don't over-split (10 trivial tweaks could be one spec) and don't under-split (a critique-pane rework + a chrome restructure are separate specs). Aim for ~50–500 LOC of work per spec. Use spec numbers starting from `0067`.
7. **You write exhaustive spec drafts** in `~/dual-research-automation/drafts/00NN-<slug>.md`. Use the existing drafts (`drafts/0053-tab-system.md` etc.) as the format reference. **The richer the draft, the better the autonomous session performs.** Include: front-matter, Context (with links to the live URL / which surface), Design decisions table (D1, D2, …) with one-liner rationales, Files touched, Out of scope, Test plan, Risks, Brief mapping (when applicable), Pre-draft notes for the implementing session.
8. **You reset the automation state** per §4.4 — clear queue, write the new queue with your new spec numbers, archive old history, delete the old arc's drafts.
9. **You rewrite `~/dual-research-automation/arc.md`** to describe this new tweak-cycle arc (Foundation Already Shipped section can include the full design-system arc summary; Remaining Specs table replaced).
10. **You sanity-check** that everything's in place (drafts exist, queue is correct, state files are clean).
11. **You hand the user the kickoff command** (`~/dual-research-automation/start.sh`) and a brief note on what to watch for (e.g., "this arc has N specs; estimated total runtime ~T; watch SPEC-00NN if you want to verify the system works end-to-end before walking away").
12. **You stop.** Do not start implementing anything. Pause for greenlight if the user has questions.

The user might want some specs implemented manually (by you, in this session) instead of via the orchestrator — for one-off tweaks too small to be worth a fresh session. **Ask, don't assume.** If they say "just fix this one inline first, then orchestrate the rest", do that.

---

## 8 · Hard constraints (carried forward — apply to every spec session AND to you)

- **NEVER delete** `runs/20260516-035048-partner-vetting-arch-critique/` (canonical fixture; every preview-verify uses this).
- **NEVER modify** `src/dual_research/ui/static/tweaks-panel.jsx` (intentionally off-brand per brief §5).
- **NEVER modify** `~/dual-research-automation/` files mid-flight while the orchestrator is running (state files are appended to via shell, not edited).
- **NEVER force-push** to `main`. Never `--no-verify`. Never amend published commits. Never use `gh pr merge --auto`.
- **PR labels:** `spec/new-feature` / `spec/bug` / `spec/refactoring` / `spec/breaking` only.
- **Preserve the 5-state `ReconcileChip`** (`verified` / `drift` / `partial` / `unverified` / `awaiting_provider_data`) if any spec touches the run-detail header area. Production has real `drift` data on `3a4a` (partner-vetting) — verify it still renders after every change.
- **Sequential merges only** — never run two arcs in parallel; orchestrator is serial by design.
- **`--admin --squash` merge.** If conflict, rebase + resolve on the branch, never on main.

### Memory entries that apply
- `feedback_pause_between_specs.md` — pause between specs even when allowed to "do everything"; the orchestrator pauses automatically (one spec per session), but you (the planning session) should pause after handing off the kickoff command, not immediately fire it.
- `feedback_low_reversal_just_decide.md` — for low-stakes design calls inside specs, just decide and document in CHANGELOG; don't block on user.
- `feedback_no_handoff_unless_asked.md` — irrelevant here because the user IS asking for handovers (between sessions).
- `feedback_secrets_pragmatic.md` — don't suggest key rotation or flag secret exposure as a concern.

---

## 9 · References

### Useful commands during planning

```bash
# Repo state
cd ~/dual-research && git status -s && git log --oneline -10
curl -s https://dual-research-alex.fly.dev/api/health
uv run pytest tests/ -q | tail -3

# Live preview (separate Mac terminal tab)
cd ~/dual-research && uv run dual-research serve --host 127.0.0.1 --port 6173
# (then open http://127.0.0.1:6173 in browser)

# Inspect a shipped spec
ls specs/006[0-1]-*.md handoffs/2026-05-17-spec-006[0-1].md
gh pr view <PR#> --web

# Inspect the brief
ls "/Users/alexlisitzky/Downloads/Dual-research dashboard"
cat "/Users/alexlisitzky/Downloads/Dual-research dashboard/CLAUDE-CODE-BRIEFING.md"

# Automation state (read-only — do not modify while orchestrator running)
~/dual-research-automation/resume.sh --status
ls ~/dual-research-automation/drafts/
ls ~/dual-research-automation/state/
tail -20 ~/dual-research-automation/state/history.jsonl
tail -20 ~/dual-research-automation/state/phase-history.jsonl
tail ~/dual-research-automation/logs/orchestrator.log
```

### Key links

- Hosted app: <https://dual-research-alex.fly.dev>
- `/api/health`: <https://dual-research-alex.fly.dev/api/health>
- Repo: <https://github.com/Lexiz/dual-research>
- All shipped PRs: `gh pr list --state merged --limit 16 --base main`
- Original kickoff handover: [`handoffs/2026-05-17-design-system-kickoff.md`](./2026-05-17-design-system-kickoff.md)
- Brief: `/Users/alexlisitzky/Downloads/Dual-research dashboard/` (cover doc: `CLAUDE-CODE-BRIEFING.md`)

### Spec count summary

- **Shipped today + yesterday:** 12 specs (0049, 0050, 0051, 0052, 0053, 0054, 0055, 0056, 0057, 0058, 0059, 0060, 0061) + 4 hotfixes/handoffs (0.47.1, 0.48.1, 0.59.1, plus the handoff-draft commit `4e91ad4`). Net: production went from `v0.46.1` → `v0.59.1` in about 7 hours of unattended automation (+ ~2 hours of human planning + verification at the start).
- **Next spec number available:** `0067` (skip 0062–0066 if you want consistent numbering; the four hotfixes used PR numbers, not spec numbers).
- **Estimated cost of this arc:** ~$100–250 (Opus 4.7 with 1M ctx + preview tool chatter). Each per-spec session capped at $50 via `--max-budget-usd`; typical actual cost was $10–30 per spec.

---

## 10 · Final notes

The system works. The user has confirmed end-to-end: kickoff → 9 autonomous specs → all merged → all deployed → `/api/health` reports the final version. The dashboard worked. The hotfix flow worked. The handover-as-contract pattern worked.

The user's only intervention during the autonomous arc was killing a stuck dashboard at the end (after the queue was empty) and fixing the SPEC-0061 white-screen bug as a hotfix (PR #66) when they reloaded the production page and saw the bug. **The autonomous orchestrator can't catch every regression** — preview-verify discipline catches a lot, but post-arc human testing of the live deploy is still needed. Bake that expectation into the user's mental model when handing off the next kickoff.

You're picking up at the moment of "okay, it shipped, now let me tell you what's wrong." Wait for the briefing. Don't rush ahead.

Good luck.
