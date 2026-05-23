---
kind: dev
spec: "0170"
slug: canvas-workshop-skill-and-scaffold
title: /canvas workshop skill — registry-driven pane iteration sandbox with verbatim live + DS snapshots
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: deployed
queue_position: 0
depends_on: []
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T17:08:41Z"
started_at: "2026-05-22T23:30:37Z"
merged_at: "2026-05-22T23:49:40Z"
deployed_at: "2026-05-22T23:58:57Z"
pr: "https://github.com/Lexiz/dual-research/pull/197"
handover: "handoffs/2026-05-22-spec-0170-canvas-workshop-skill-and-scaffold.md"
failure_step: ""
source_session: canvas-skill-design-2026-05-22
promoted_from_draft: ""
---

# Spec 0170 — `/canvas <pane>` workshop skill + scaffold

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — new repo-local skill + scaffolding tooling. No live-app code changes. No design-system contract changes.

---

## 1. Context

Two pane-iteration workshops exist in the repo today and have proven their value:

- `prototypes/timeline-iteration/` — the workshop used to lock specs 0164 / 0165 / 0166.
- `prototypes/critique-iteration/` — the workshop used to lock specs 0167 / 0168.

Both workshops follow the same architecture:

1. **A 3-tab mockup wrapper** (`mockup.html`) — Iteration / Live / DS tabs, a Dark / Light theme toggle, and a Narrow / Wide width toggle. Loads `live.html`, `ds.html`, and `proposed.html` into iframes.
2. **A verbatim live-HTML dump** (`live.html`) — `outerHTML` of a real DOM selector (`.rdvc__pane` for timeline, `.crit2` for critique) captured from the running app at a real anchor run. The iframe loads the actual live CSS (`src/dual_research/ui/static/{tokens,base,components,theme}.css`) via `<link>` tags so edits to those files are immediately visible in the iframe.
3. **A verbatim DS extract** (`ds.html`) — `<section id="X">…</section>` copied from `design-system/assets/Design System v2.html`. Loads the actual DS CSS (`design-system/assets/styles/v2-m3.css`, `v2-m3-page.css`) so the iframe shows the canonical rendered reference.
4. **An iteration sandbox** (`proposed.html`) — starts as a verbatim copy of `live.html` and accumulates stacked `<style id="iter-N-…">` blocks at the top of the document. Theme and width controllable via URL params / data attributes.
5. **A running record** (`NOTES.md`) — one row per iter using the locked four-quadrant format: Now / After / DS change / Live change.
6. **A Claude Preview server** rooted at the repo root, running on a pane-specific port (`:6174` for critique, `:6175` for timeline), so iframes resolve `/src/...` and `/design-system/...` paths to the real files.

The pattern is proven but not abstracted. Every new pane today requires:

- Manual `outerHTML` dump via the browser dev tools or Claude Preview
- Manual `<section id="X">` copy from `design-system/assets/Design System v2.html`
- Manual mockup wrapper assembly with the right tab labels, CSS includes, theme + width controls
- Manual server-port allocation

This spec formalises the pattern into a single invocation: **`/canvas <pane>`**. The skill reads a registry entry for the pane, performs the dumps, renders the templates, starts the workshop server, and reports a clickable localhost URL.

## 2. Proposed change

Four deliverables, all repo-local. Nothing under `src/dual_research/` is touched.

### 2.1 Registry — `prototypes/_canvas/registry.yml`

Single source of truth for what panes are workshoppable and how to capture them.

```yaml
# prototypes/_canvas/registry.yml
panes:
  timeline:
    name: "Timeline pane"
    description: "Run-detail timeline (left column of .rdvc__split)"
    live_url: "http://localhost:6173/#/runs/{anchor_run}"
    live_selector: ".rdvc__pane"
    ds_sections: ["timeline"]
    port: 6175
    states: []                              # single-state surface
    live_css:
      - /src/dual_research/ui/static/tokens.css
      - /src/dual_research/ui/static/base.css
      - /src/dual_research/ui/static/components.css
      - /src/dual_research/ui/static/theme.css
    ds_css:
      - /design-system/assets/styles/v2-m3.css
      - /design-system/assets/styles/v2-m3-page.css
    default_anchor_run: "20260521-010637-dvs-backend-language-choice"

  critique:
    name: "Critique pane"
    description: "Run-detail critique (right column of .rdvc__split)"
    live_url: "http://localhost:6173/#/runs/{anchor_run}"
    live_selector: ".crit2"
    ds_sections: ["critique", "itemcard", "thread"]
    port: 6174
    states:                                  # multi-state — capture each phase tab
      - { name: "P0",    click: "[data-phase-tab='P0']" }
      - { name: "P2",    click: "[data-phase-tab='P2']" }
      - { name: "P4",    click: "[data-phase-tab='P4']" }
      - { name: "sigma", click: "[data-phase-tab='sigma']" }
    live_css:
      - /src/dual_research/ui/static/tokens.css
      - /src/dual_research/ui/static/base.css
      - /src/dual_research/ui/static/components.css
      - /src/dual_research/ui/static/theme.css
    ds_css:
      - /design-system/assets/styles/v2-m3.css
      - /design-system/assets/styles/v2-m3-page.css
    default_anchor_run: "20260521-010637-dvs-backend-language-choice"
```

The two pre-populated entries (`timeline`, `critique`) must reproduce the existing workshops bit-for-bit. Validation: a `/canvas timeline` run from a clean state produces a workshop indistinguishable from the existing `prototypes/timeline-iteration/` (modulo `proposed.html` and `NOTES.md`, which the skill never overwrites).

Adding a new pane = add a registry entry. No code changes required.

### 2.2 Templates — `prototypes/_canvas/templates/`

Three template files. Placeholders use `{{double-brace}}` syntax for substitution. Substitutions are simple string replace — no Jinja, no templating library.

**`mockup.html.tmpl`** — the workshop wrapper. Renders the three-tab switcher, the Dark / Light toggle, the Narrow / Wide toggle, and the iframes. Substituted strings:

- `{{pane_name}}` — display name from registry (e.g. "Timeline pane")
- `{{anchor_run}}` — anchor run id badge
- `{{ds_tab_label}}` — typically "DS" but can carry section ids for multi-section panes (e.g. "DS §critique + §itemcard + §thread")
- `{{port}}` — for self-reference if needed in JS
- `{{narrow_width_px}}` — default 1280
- `{{wide_width_px}}` — default 1920

Template structure mirrors the existing `prototypes/timeline-iteration/mockup.html` — extract the diffs against `prototypes/critique-iteration/mockup.html` to identify the variable surface.

**`proposed.html.tmpl`** — the iteration sandbox starter. Initial content is a verbatim copy of `live.html` (no `<style id="iter-N-…">` blocks yet) with theme/width URL-param parsing and a `#iter-banner` element ready to receive iter labels.

**`NOTES.md.tmpl`** — pre-populated with the four-quadrant table header (`| Iter | One-line change | Element touched |`) and section anchors for the per-element specification + drift fixes.

### 2.3 Scaffold script — `prototypes/_canvas/spin-up.py`

Single Python entry point. Argv: `python spin-up.py <pane> [--anchor-run <id>] [--force-overwrite-proposed]`.

Behaviour:

1. **Load registry.** Parse `prototypes/_canvas/registry.yml`. Validate `<pane>` exists; print usage if not.
2. **Resolve anchor run.** Use `--anchor-run` if provided; else `default_anchor_run` from the registry; else fall back to the most recent run id under `runs/` if neither is available locally.
3. **Confirm live server is up.** Probe `http://localhost:6173/`. If down, run `uv run dual-research serve` in the background and wait until the port responds (timeout 30 s).
4. **Dump live HTML.** Use the Claude Preview MCP (or an equivalent headless-Chrome wrapper) to:
   - Navigate to the pane's `live_url` with the anchor run id substituted.
   - For each state in `states`: click the state's selector if present, then dump `document.querySelector(<live_selector>).outerHTML`. For single-state panes (`states: []`), dump once.
   - Concatenate the dumps into a single `live.html` with `<section class="phase-state" data-state="X">…</section>` wrappers (when multiple states) and the `live_css` `<link>` tags pre-wired in `<head>`.
5. **Extract DS sections.** For each id in `ds_sections`: read `design-system/assets/Design System v2.html`, find `<section id="X">…</section>` (matching the closing tag at the correct nesting depth), copy verbatim. Concatenate into a single `ds.html` with the `ds_css` `<link>` tags pre-wired in `<head>`.
6. **Render mockup.html** from the template with the substituted strings.
7. **Render proposed.html** from the template IF the file doesn't already exist. If it does, leave it untouched (preserves iteration work).
8. **Render NOTES.md** from the template IF the file doesn't already exist. If it does, leave it untouched.
9. **Start the Claude Preview server** on the pane's port, rooted at the repo root. If the port is already in use, check whether it's already serving this workshop (compare against the workshop dir name) — if yes, reuse; if no, report a port collision and exit.
10. **Print the workshop URL.** `http://localhost:{port}/prototypes/{pane}-iteration/mockup.html`. This is the clickable link the user opens.

The script is idempotent. Re-running refreshes `live.html` + `ds.html` (always canonical snapshots). `proposed.html` and `NOTES.md` are preserved unless `--force-overwrite-proposed` is passed.

Output dir convention: `prototypes/{pane}-iteration/` (e.g. `prototypes/timeline-iteration/`). The dir is created if it doesn't exist.

### 2.4 Skill — `.claude/skills/canvas/SKILL.md`

Repo-local skill so it auto-loads in every Claude Code session opened against this repo.

Frontmatter:

```yaml
---
name: canvas
description: |
  Spin up a pane-iteration workshop for an existing UI surface in dual-research.
  Pulls a verbatim live-HTML snapshot + a verbatim Design System section, drops
  them alongside an iteration sandbox in prototypes/<pane>-iteration/, and starts
  a local Claude Preview server. Reports a clickable workshop URL.

  Triggers: "/canvas <pane>", "load the <pane> canvas", "spin up the <pane>
  workshop", "open the <pane> iteration sandbox". <pane> is one of the keys
  in prototypes/_canvas/registry.yml (currently: timeline, critique).
allowed-tools: Bash, Read, Write, Edit, mcp__Claude_Preview__*
---
```

Body steps (codified in markdown):

1. Read `prototypes/_canvas/registry.yml`; show the user the available panes if `<pane>` is missing or invalid.
2. Invoke `uv run python prototypes/_canvas/spin-up.py <pane>` and stream the output.
3. When the script reports the workshop URL, surface it to the user as a clickable link plus a one-line summary: pane name, anchor run id, port, number of `<style id="iter-N">` blocks present in `proposed.html`.

The skill does NOT iterate on the pane itself — it only sets up the workshop. The user then iterates manually in conversation (the existing pattern).

## 3. UX / behaviour

Invocation in a fresh session:

```
User: /canvas timeline
Claude: [runs spin-up.py timeline]
        Workshop ready → http://localhost:6175/prototypes/timeline-iteration/mockup.html
        Pane: Timeline pane · Anchor run: 20260521-010637-dvs-backend-language-choice · 0 iter blocks in proposed.html
```

The user clicks the link and starts iterating. Subsequent invocations of `/canvas timeline` refresh the live + DS snapshots without disturbing the iteration sandbox.

Adding a new workshoppable pane (e.g. summary or login) is a yaml entry edit. No code changes; the existing scaffold + skill handle it.

## 4. Data / schema deltas

None. The skill is purely tooling; it doesn't touch the event store, run-detail JSON, or any persisted state.

## 5. Out of scope

- **Iteration freeze / lock command** (`/canvas freeze` to snapshot the current `proposed.html` into a numbered iter block + update `NOTES.md` automatically). The manual workflow today is workable; deferred.
- **Non-pane surfaces** (full-page screens, multi-step flows, modal sequences). The pattern is specifically for "iterate on a single pane's visual chrome."
- **Production code changes.** No edits to `src/dual_research/` or `design-system/` source files. The skill reads from them.
- **Workshop CSS edits feeding back into live code.** The user manually transcribes locked iter styles into the live CSS via the dev-spec workflow (`/spec-draft` → `/spec-promote` → `/dev-next`). The canvas skill does NOT cross that line.
- **Multi-user collaboration on a running workshop.** Single-user, single-machine.

## 6. Design-system gate

This spec adds tooling, not UI. No `design-system/SPEC.md` section is changed. No `design-system/assets/Design System v2.html` re-render. No `composed-components.css` rule additions.

Files touched in the same commit:

- `.claude/skills/canvas/SKILL.md` (new)
- `prototypes/_canvas/registry.yml` (new)
- `prototypes/_canvas/templates/mockup.html.tmpl` (new)
- `prototypes/_canvas/templates/proposed.html.tmpl` (new)
- `prototypes/_canvas/templates/NOTES.md.tmpl` (new)
- `prototypes/_canvas/spin-up.py` (new)
- `prototypes/_canvas/README.md` (new — explains the registry + how to add a pane)
- `CHANGELOG.md` (MINOR section)
- `pyproject.toml` (version bump)
- `src/dual_research/__init__.py` (version bump)

## 7. Test plan

- [ ] **Timeline reproduction.** Stash + delete `prototypes/timeline-iteration/` (back up `proposed.html` + `NOTES.md` first if they hold work). Run `/canvas timeline`. The skill rebuilds `live.html`, `ds.html`, `mockup.html`. Open the reported URL — the workshop renders correctly in both themes at both widths. Restore the saved `proposed.html` + `NOTES.md`; the iteration work is intact (skill didn't overwrite).
- [ ] **Critique reproduction.** Same drill for `prototypes/critique-iteration/`. The four phase states (P0 / P2 / P4 / Σ) are captured separately. The workshop's phase-tab handler swaps `.phase-state` visibility correctly.
- [ ] **Idempotent refresh.** Run `/canvas timeline` twice. `live.html` + `ds.html` are re-dumped both times. `proposed.html` + `NOTES.md` are byte-identical before and after the second run (file mtimes change but content doesn't, OR mtimes don't change because the script skipped writes).
- [ ] **Anchor-run override.** Run `/canvas timeline --anchor-run <other-run-id>`. The dumped `live.html` reflects the other run's data.
- [ ] **New pane registration.** Add a third entry to `registry.yml` for a real pane (e.g. `summary` targeting `.run-summary` and DS §summary). Run `/canvas summary`. Workshop spins up with no code changes — only the yaml entry.
- [ ] **Live server bootstrap.** Kill `uv run dual-research serve`. Run `/canvas timeline`. The script detects the down server, starts it in the background, waits for `:6173`, then proceeds with the dump.
- [ ] **Port collision.** Manually occupy port 6175. Run `/canvas timeline`. The script reports the collision and exits with a non-zero code.
- [ ] **Verbatim contracts.** Pick one card in the dumped `live.html`. Confirm it is byte-identical to the same card in the running app's DOM (`outerHTML` comparison). Pick one DS section in the dumped `ds.html`. Confirm it is byte-identical to the corresponding `<section id="X">…</section>` in `design-system/assets/Design System v2.html`.
- [ ] **CSS live-edit pass-through.** With the workshop open, edit a rule in `src/dual_research/ui/static/components.css`. Reload the Live tab in the workshop. The change is visible (confirming the iframe links to the real file, not a copy).
- [ ] **Tests pass.** `uv run pytest tests/ -q` exits 0. (The skill is tooling; tests cover the registry parsing + DS-section extraction if exposed as importable functions.)

## 8. Implementation steps (suggested order)

1. Diff `prototypes/timeline-iteration/mockup.html` against `prototypes/critique-iteration/mockup.html` to identify the common skeleton and the per-pane variable surface. Lift the common skeleton into `prototypes/_canvas/templates/mockup.html.tmpl`.
2. Do the same for the workshop wrapper styles, the inline-script (phase-tab handlers, collapse affordances), and any other shared HTML.
3. Write `prototypes/_canvas/registry.yml` with `timeline` and `critique` entries populated to match the existing workshops.
4. Write `prototypes/_canvas/spin-up.py` with:
   - `argparse` for `<pane>` + `--anchor-run` + `--force-overwrite-proposed`
   - registry loader (`yaml.safe_load`)
   - DS section extractor (simple regex or BeautifulSoup against `design-system/assets/Design System v2.html`)
   - Live-server probe + bootstrap (subprocess.Popen against `uv run dual-research serve`)
   - Live-HTML dumper using the Claude Preview MCP — for non-Claude-session runs, fall back to a `playwright` import (lazy import; if unavailable, print install instructions and exit)
   - Template renderer (simple `str.replace` on placeholders)
   - Claude Preview server starter on the registered port
5. Write `.claude/skills/canvas/SKILL.md` with frontmatter + body steps.
6. Write `prototypes/_canvas/README.md` explaining the registry, the template fields, how to add a new pane.
7. Test against both pre-populated panes (test plan §7 items 1–3).
8. CHANGELOG entry under a new `## [X.Y.Z] — YYYY-MM-DD` section. Bump `pyproject.toml` + `src/dual_research/__init__.py` per MINOR.
