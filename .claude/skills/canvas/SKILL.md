---
name: canvas
description: |
  Spin up a pane-iteration workshop for an existing UI surface in dual-research.
  Pulls a verbatim live-HTML snapshot via the Claude Preview MCP, extracts a
  verbatim Design System v2 section, drops them alongside an iteration sandbox
  in prototypes/<pane>-iteration/, and reports a clickable workshop URL.

  Triggers: "/canvas <pane>", "load the <pane> canvas", "spin up the <pane>
  workshop", "open the <pane> iteration sandbox". <pane> is one of the keys in
  prototypes/_canvas/registry.yml (currently: timeline, critique). New panes
  are added by appending to the registry — no code changes required.
allowed-tools: Bash, Read, Write, Edit, mcp__Claude_Preview__*
---

# canvas — workshop scaffolding

`/canvas <pane>` rebuilds a pane-iteration workshop under
`prototypes/<pane>-iteration/`. Re-runs refresh `live.html` + `ds.html` +
`mockup.html`; `proposed.html` and `NOTES.md` are preserved (iteration work is
never overwritten unless the user passes `--force-overwrite-proposed`).

See [`prototypes/_canvas/README.md`](../../../prototypes/_canvas/README.md) for
the registry contract and how to add a new pane.

## When to invoke this skill

The user says:

- `/canvas <pane>` (e.g. `/canvas timeline`)
- "spin up the timeline workshop"
- "load the critique canvas"
- "open the <pane> iteration sandbox"

If `<pane>` is missing or not in the registry, surface the list of available
panes from `prototypes/_canvas/registry.yml`.

## Steps

1. **Read the registry.** Parse `prototypes/_canvas/registry.yml`. Verify
   `<pane>` exists. If not, list available pane keys and stop.

2. **Resolve the anchor run.** Use `--anchor-run` from the user if given; else
   the pane's `default_anchor_run`; else the most recent run id under `runs/`.

3. **Ensure the live app is up.** Use
   `mcp__Claude_Preview__preview_list` to check whether the live app server
   is running. If not, run `uv run dual-research serve` in the background
   (via Bash) and wait until `http://localhost:6173` responds.

4. **Dump live HTML via the Claude Preview MCP.**
   - For single-state panes (`states: []` in registry): one dump.
   - For multi-state panes: one dump per state in order. Between dumps, use
     `mcp__Claude_Preview__preview_click` against the registry's `click`
     selector to activate the next state.
   - The dump value is
     `document.querySelector('<live_selector>').outerHTML`, captured via
     `mcp__Claude_Preview__preview_eval`. Wrap in `JSON.stringify` so the
     return value is a plain string with no DOM serialization quirks.
   - Write each dump to a tempfile under `/tmp/` named
     `canvas-<pane>-<state-or-default>-<short-ts>.html`.

5. **Run the scaffold.**

   Single-state:
   ```bash
   uv run python prototypes/_canvas/spin-up.py <pane> \
     --anchor-run <anchor> \
     --live-html-file <tempfile>
   ```

   Multi-state:
   ```bash
   uv run python prototypes/_canvas/spin-up.py <pane> \
     --anchor-run <anchor> \
     --live-html-state P0:<tempfile-p0> \
     --live-html-state P2:<tempfile-p2> \
     ...
   ```

   The script prints a summary block ending in `url: http://localhost:<port>/prototypes/<pane>-iteration/mockup.html`.

6. **Start the workshop preview server.** Use
   `mcp__Claude_Preview__preview_start` with the repo root as `rootDir` and
   the pane's `port` from the registry. If a server is already running on
   that port, reuse it; if a different workshop is using the same port, ask
   the user to free it.

7. **Report.** Surface to the user as a clickable link:
   - Workshop URL (full http://localhost:PORT/... path)
   - Pane name, anchor run id, port
   - Number of `<style id="iter-N-…">` blocks already in `proposed.html`
     (0 on first scaffold; the running count after subsequent re-runs)
   - One-line reminder that iterating happens in `proposed.html` and
     `NOTES.md`, neither of which the skill will overwrite.

## What this skill does NOT do

- It does not iterate on the pane itself — only scaffolds.
- It does not edit `src/dual_research/`, `design-system/SPEC.md`, or the
  composed-components CSS. Production locks land via `/dev-next`, not here.
- It does not save iter blocks back into the live CSS. The user transcribes
  locked iters into a `/spec-draft` and ships through `/dev-next`.

## Failure modes

- **Unknown pane:** list registry keys + stop.
- **Live app server down and `uv run dual-research serve` fails:** surface the
  error + stop.
- **Live selector doesn't match anything in the dumped DOM:** the
  `preview_eval` returns `null`. Surface "live selector `<sel>` matched
  nothing — check the anchor run loaded correctly" + stop.
- **DS section id not found:** the scaffold script exits non-zero with a clear
  message — surface verbatim.
- **Port collision on workshop start:** surface the error + ask the user.
