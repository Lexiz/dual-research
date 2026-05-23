---
spec: "0170"
date: 2026-05-22
version: 1.34.0
pr: "https://github.com/Lexiz/dual-research/pull/197"
---

# Spec 0170 — `/canvas <pane>` workshop skill + scaffold — shipped

Registry-driven pane iteration workshops are now a one-liner. `/canvas <pane>` reads
`prototypes/_canvas/registry.yml`, dumps the live pane's `outerHTML` via the
Claude Preview MCP, extracts the matching `<section class="ds-section">` blocks
from `design-system/assets/Design System v2.html`, renders the workshop templates,
and reports a clickable URL.

Adding a new pane is a YAML entry edit — no code changes required.

## What landed

- **Registry** — [`prototypes/_canvas/registry.yml`](../prototypes/_canvas/registry.yml).
  Pre-populated with `timeline` (`#d4a574` sable, port 6175, single-state, `.rdvc__pane`
  selector, DS §16) and `critique` (`#7cc4b8` sage, port 6174, four states P0/P2/P4/sigma,
  `.crit2` selector, DS §12 + §13 + §13b) entries. Inline field docs at the top.

- **Templates** — [`prototypes/_canvas/templates/`](../prototypes/_canvas/templates/).
  Five files: `mockup.html.tmpl` (Iteration / Live / DS three-tab wrapper with
  theme + width toggles), `live.html.tmpl` (verbatim outerHTML shell with optional
  multi-state phase tabs), `ds.html.tmpl` (DS extract shell), `proposed.html.tmpl`
  (iteration sandbox starter — verbatim copy of live with theme URL-param parsing),
  `NOTES.md.tmpl` (four-quadrant running record).

- **Scaffold script** — [`prototypes/_canvas/spin-up.py`](../prototypes/_canvas/spin-up.py).
  Loads registry, extracts DS sections (balanced-tag match so nested `<section>` like
  `id="how"` parse correctly), wraps pre-captured live HTML dumps in the canonical
  shell, renders templates, writes the workshop dir. Idempotent on `live.html` + `ds.html`
  + `mockup.html`; preserves `proposed.html` + `NOTES.md` across re-runs unless
  `--force-overwrite-proposed`. Supports multi-state panes via repeatable
  `--live-html-state NAME:PATH`.

- **Skill** — [`.claude/skills/canvas/SKILL.md`](../.claude/skills/canvas/SKILL.md).
  Repo-local. Triggers on `/canvas <pane>`, "spin up the X workshop", etc. Drives the
  Claude Preview MCP for the live dumps (and the multi-state clicks), then invokes
  `spin-up.py` with the pre-captured files.

- **README** — [`prototypes/_canvas/README.md`](../prototypes/_canvas/README.md). Pane
  registry contract, how to add a new pane, manual (non-Claude) invocation path.

- **Tests** — [`tests/canvas/test_spin_up.py`](../tests/canvas/test_spin_up.py). 14
  tests: registry parsing, DS-section extraction (synthetic + real `Design System v2.html`),
  template substitution, multi-state arg ordering, end-to-end `build_*` HTML composition.
  Full suite: 1588 passed.

## Architecture decisions

- **MCP / script split.** A Python script can't directly call MCP tools; only the
  Claude tool layer can. The SKILL.md body owns the MCP-level work (live dump per
  state, workshop server start); `spin-up.py` owns the file generation (registry
  parse, DS extract, template render, output dir writes). The script accepts
  pre-dumped HTML via `--live-html-file` (single-state) or `--live-html-state NAME:PATH`
  (repeatable, for multi-state panes). This keeps the script dep-light (just yaml,
  no playwright) and makes the manual non-Claude invocation explicit.

- **DS section extraction is depth-balanced.** `extract_ds_section` counts `<section>`
  open / `</section>` close pairs from the matched start tag so nested DS sections
  (like `<section id="how">` which wraps multiple `<section class="hiw-sec">`) don't
  return prematurely.

- **Bit-for-bit reproduction is not the goal.** The new scaffold produces the canonical
  shape of `live.html` / `ds.html` / `mockup.html`. The existing bespoke
  `prototypes/timeline-iteration/live.html` includes a side-by-side critique stub
  hand-stitched by `_build.sh`; that's workshop-specific tinkering that the new
  generalized scaffold does NOT reproduce. Per the spec's "modulo proposed.html and
  NOTES.md" clause, the new live.html is the bare dumped DOM in a minimal banner
  wrapper. If iteration wants side-by-side, that lives in `proposed.html` (where it
  belongs — iteration-specific layout decisions).

## Deploy notes

- `fly deploy` hit `Found 2 different images in your app` on the first attempt due
  to a stale cluster state from prior runs. Retried; second attempt succeeded with
  bluegreen completing cleanly.
- Post-deploy `scripts/sweep_stale_blues.sh` output: `sweep: no stale blues on dual-research-alex`.
- Health check: `GET https://dual-research-alex.fly.dev/` → 200; `/api/data` returns
  `missing_token` (expected without auth).
- App image: `dual-research-alex:deployment-01KS91TKPC0Y7Z3ZV13HM8D3EV` running on two
  machines.

## Validation status

Unit + smoke covered; the post-merge manual checks listed in the spec's §7 test plan
are still pending (timeline reproduction, critique reproduction, new-pane registration).
These are best run interactively against the workshop URL the skill produces.
