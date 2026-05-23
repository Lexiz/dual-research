---
kind: dev
spec: "0153"
slug: dashboard-redesign-staged-hero-and-activity-feed
title: Dashboard redesign — design-system primitives, expandable in-flight hero with stage timeline, activity feed
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.18.0
status: deployed
depends_on: []
complexity: M
created: 2026-05-22
queued_at: 2026-05-22T11:25:00Z
started_at: "2026-05-22T11:52:51Z"
merged_at: "2026-05-22T12:04:29Z"
deployed_at: "2026-05-22T12:13:34Z"
pr: "https://github.com/Lexiz/dual-research/pull/176"
handover: "handoffs/2026-05-22-spec-0153-dashboard-redesign-staged-hero-and-activity-feed.md"
failure_step: ""
source_session: lifecycle-bootstrap-2026-05-22
promoted_from_draft: ""
---

# Spec 0153 — Dashboard redesign — design-system primitives, expandable in-flight hero with stage timeline, activity feed

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — visual + structural redesign of the spec dashboard. No breaking changes to data sources (spec frontmatter, handoff frontmatter, event sidecars); the renderer entrypoint stays at `python -m scripts.spec_lifecycle.render_dashboard`; output is still static HTML for Cloudflare Pages.
> **Evidence:** Visual mockup committed alongside this spec at `prototypes/dashboard-redesign/mockup.html` (with `?state=idle` / `?state=inflight` toggle). Design-system principles per `design-system/SPEC.md:21`. Tokens + primitives from `design-system/assets/styles/tokens-and-primitives.css` and `design-system/assets/styles/composed-components.css` — the same files the live app consumes.

---

## 1. Context

Spec 0152 shipped the spec lifecycle system, including a static dashboard at `https://dual-research.pages.dev` rendered by `scripts/spec_lifecycle/render_dashboard.py:141`. The first rendering pass was deliberately plain (raw HTML tables, ad-hoc inline CSS) to validate data plumbing — frontmatter → renderer → Cloudflare Pages → live URL. With that pipeline confirmed working, this spec gives the dashboard a coherent visual identity that:

1. Uses the canonical dual-research design system (sable/sage palette, Material 3 tokens, calm motion, read-only discipline) per `design-system/SPEC.md:21`.
2. Establishes a clear top-down information hierarchy: *what is happening now* → *queue health* → *throughput* → *queue contents* → *recent activity* → *backlog* → *catalog*. The current dashboard treats each section as equal weight, which buries the live state.
3. Makes the active dev-cycle stage visible while `/dev-next` is mid-flight. Currently the only signal that a cycle is running is the spec's `status: in_progress` flag — there is no way to tell from the dashboard whether the cycle is reconciling, implementing, testing, or deploying.
4. Replaces flat tables with composed cards built from the existing design-system primitives (`bcard`, `seg-track`, `chip`, callout patterns) so the dashboard reads as a first-class dual-research surface rather than scaffold.

## 2. Proposed change

Rewrite `scripts/spec_lifecycle/render_dashboard.py` to emit a new index layout. The script's CLI, inputs, output directory, and asset filenames stay identical — only the HTML structure and styling change, plus a new helper for stage computation. All visual decisions read from existing design tokens; no new tokens are introduced.

### 2.1 Header

A page-chrome block at the top: brand-serif title "dual-research · spec dashboard", subtitle naming the data sources (`specs/`, `handoffs/`, `dashboard/events/`), and a right-aligned meta row containing:

- A live-app version chip ("v1.X.Y live" — read from `pyproject.toml`).
- "Updated <ISO timestamp>" — emitted at render time.
- A "repo ↗" link to `https://github.com/Lexiz/dual-research`.

### 2.2 Hero — two states driven by data

The hero is one section that renders differently based on how many specs have `status: in_progress`.

**Idle state** (no in-flight spec) — compact three-column hero card:

- Left: pause-circle icon (Material Symbols Outlined) on a neutral surface tile.
- Middle: kicker "Queue · idle"; title "Nothing in flight" with a hint pointing at `/dev-next`; a row of status chips (`<N> in flight`, `<N> queued`, `last shipped <X> ago`).
- Right: a big number "X ago" with label "last deploy · NNNN".

**In-flight state** (one or more in-flight specs) — expanded hero card:

- The same three-column top row, but the icon is `play_circle` with a 2.2s soft halo pulse per the design system's "loud" state rule (`design-system/SPEC.md:42`). The middle column carries the kicker ("In flight · step N of 11 — <stage>"), the spec title linked to `spec-NNNN.html`, and a chip row (type · branch name · most-recent reconcile note). The right column shows elapsed time + ETA.
- A hair-rule divider (`var(--md-outline-hair)`) separates the top row from the timeline below.
- A vertical **stage timeline** lists all eleven canonical dev-cycle stages.

If two or more specs are simultaneously in-flight, the hero renders a stacked layout — one expanded card per active spec. This is parallel-ready but not used in v1 (the `/dev-next` pre-flight enforces serial execution per `specs/0152-spec-lifecycle-system-v1.md:215`).

### 2.3 The eleven canonical stages

The `/dev-next` flow defined in `specs/0152-spec-lifecycle-system-v1.md:215` has eleven natural breakpoints. Each maps to a stage row carrying: status mark · stage name · sub-info note · duration.

| # | Stage | Event step (in `dashboard/events/NNNN.jsonl`) | Sub-info template |
|---|---|---|---|
| 1 | Pre-flight | `preflight_ok` | "main clean · no open spec/* PRs · no in-flight specs" |
| 2 | Read handoff | `handoff_read` | "handoffs/YYYY-MM-DD-spec-NNNN-….md" |
| 3 | Read spec | `spec_read` | "specs/NNNN-….md · `<lines>` lines · `<type>`" |
| 4 | Reconcile | `reconcile_complete` (or `_failed`) | "`<N>` mechanical patches · `<N>` semantic drift · `<verdict>`" |
| 5 | Branch | `branched` | "spec/NNNN-… from main@`<shortsha>`" |
| 6 | Implement | `implement_complete` | "`<N>` lines changed across `<N>` files · `<N>` commits on branch" |
| 7 | Test | `tests_green` (or `tests_failed`) | "`<N>` passed · `<N>` failed" |
| 8 | PR | `pr_opened` | "`<PR URL>`" |
| 9 | Merge | `merged` | "admin squash + delete branch" |
| 10 | Deploy | `deployed` | "fly deploy · v`<X.Y.Z>` live" |
| 11 | Handoff | `handoff_written` | "handoffs/YYYY-MM-DD-spec-NNNN-….md" |

A new helper `scripts/spec_lifecycle/stages.py` exposes:

```python
def compute_stages(spec_id: str, events: list[dict]) -> list[StageState]:
    """Return one StageState per canonical stage. Status: done|curr|queued|fail."""
```

Algorithm: walk the eleven stages in order. The current stage is the lowest-indexed stage whose event hasn't fired yet, *provided* the previous stage's event has fired. Earlier stages are `done`. Later stages are `queued`. If the spec's frontmatter has `failure_step: <name>`, that stage becomes `fail` and all later stages stay `queued`.

For the existing `/dev-next` skill (defined in `~/.claude/skills/dev-next/SKILL.md`), the implementation of this spec also adds inline event emissions at the canonical step names listed above. Today the skill emits only `queued`, `in_progress`, `merged`, `deployed`, `handoff_written`. The implementer of this spec updates the skill instructions (the SKILL.md file in the user's `~/.claude/skills/` directory) to call `append_event.py` at each of the eleven stages so the timeline has data to render.

### 2.4 Pipeline strip

Five-column section beneath the hero showing per-stage counts: Drafts · Queued · In progress · Merged today · Deployed all-time. Each column has an uppercase 11px label, a tabular-figure count (faint when zero), and a colored progress bar at the bottom — width is the count relative to the largest column, colors derived from `--p-idle`, `--p-info`, `--p-ok`, and `--md-on-surface-faint`.

### 2.5 Metrics row

Four equal tiles in a CSS grid: avg cycle time (rolling 10, with delta vs prior 10), throughput (per day + per week count), reconcile patches (% needing fix in rolling 10), failed cycles (count in last 30 days). Each tile uses the `.metric` card primitive defined in the mockup; values are computed by extending `render_dashboard.py`'s aggregate calculations.

### 2.6 Queue table

A `.qtable` card containing rows: position (#), spec number (linked to `spec-NNNN.html`), title (single-line ellipsis), type chip, waiting time. Empty-state row when the queue has no items, with a hint pointing at `/spec-promote <id>` and `/spec-queue`.

### 2.7 Recent activity feed

Reverse-chronological event log built from a `changelog`-derived row pattern: timestamp · step icon · "`<kicker>` `<spec>` · `<detail>`" · duration. Reads from all `dashboard/events/*.jsonl` files; window is the last 24 hours by default (configurable later).

Step → icon mapping (Material Symbols Outlined):

- `queued` → `add_task`
- `in_progress` / `branched` → `flag_circle`
- `reconcile_complete` → `rule`
- `tests_green` → `task_alt`
- `pr_opened` / `merged` → `merge`
- `deployed` → `check_circle`
- `handoff_written` → `bookmark`
- `failed` / `reconcile_failed` / `tests_failed` → `error`

Step icons inherit color from `--p-ok` / `--p-info` / `--p-warn` / `--p-err` per the tone palette.

### 2.8 Drafts

Secondary surface (darker `--md-surface-container-low` background): one row per file in `specs/drafts/`. Columns: id · title (linked) · type chip · age. Section heading explains promotion via `/spec-promote <id>`.

### 2.9 All specs

Full table of every spec with `kind: dev`, in descending number order. Same `.qtable` row pattern as Queue but with extra columns for status chip and target version. Static for v1 (no sort/filter JS).

### 2.10 Footer

A one-line attribution at the bottom: "generated by `scripts/spec_lifecycle/render_dashboard.py` · regenerated on every push to `main`" plus a link to the live Cloudflare-served URL.

### 2.11 Stylesheet strategy

The new renderer copies the canonical design-system stylesheets into the output `dist/` directory at build time:

- `design-system/assets/styles/tokens-and-primitives.css` → `dist/tokens.css`
- `design-system/assets/styles/composed-components.css` → `dist/components.css`

Plus a small dashboard-specific stylesheet `dist/dashboard.css` (around 300 lines) containing only the page-chrome layout (`.dh`, `.hero`, `.pipe`, `.metrics`, `.qtable`, `.feed`, `.drafts`, `.foot`) and the stage-timeline component (`.stages`, `.stage`, `.stage__mark`). Every color, font, spacing, and elevation rule in `dashboard.css` reads from `--md-*` / `--p-*` tokens; no hex codes.

Inline `<style>` blocks in the HTML are eliminated.

## 3. UX / Behavior

### 3.1 Information hierarchy

Reading the page top-to-bottom:

1. **Hero** — answers "is something running?" in 0.5 seconds. If yes, "what stage?" answers in another 0.5 seconds via the timeline.
2. **Pipeline strip** — answers "how full is the system?" without scrolling.
3. **Metrics** — answers "are we shipping at a healthy pace?".
4. **Queue** — answers "what's next?".
5. **Recent activity** — answers "what just happened?".
6. **Drafts** — backlog of ideas, secondary visual weight.
7. **All specs** — full catalog, lowest visual priority.

### 3.2 In-flight expansion behavior

The hero is one component that switches layouts based on data. No JavaScript toggle in production — the renderer decides at build time based on `status: in_progress` in any spec's frontmatter:

- 0 in-flight → idle layout.
- 1 in-flight → expanded layout with timeline.
- 2+ in-flight → stacked expanded layouts (renderer iterates).

The preview mockup at `prototypes/dashboard-redesign/mockup.html` includes a small JS toggle (`?state=idle|inflight` hash) for iterating on the visual; that toggle is removed from the production renderer's output.

### 3.3 Stage timeline detail

The timeline is **always vertical**, never horizontal. A horizontal strip with eleven segments collapses the sub-info notes that are essential to understanding why a stage took its time. Vertical lets each row carry: status mark · stage name · sub-info note · duration.

Each row's height stays uniform (around 42 px) so the timeline reads as a rhythm. Done and queued stages get muted text; the current stage uses full-weight `--md-on-surface` with a blue dot mark + halo pulse.

### 3.4 Motion

Two animations only, both 2.2s `ease-in-out infinite` halo pulses:

1. The hero icon's halo (in-flight state only).
2. The current stage's mark halo.

Both respect `prefers-reduced-motion: reduce` and disable when the user has it set. No other transitions, no scroll-triggered animations, no hover effects beyond M3's standard 8% state-layer overlay on links.

### 3.5 Refresh model

The dashboard is static HTML regenerated by `.github/workflows/dashboard.yml` on every push to `main`. No client-side polling, no SSE, no JS-driven freshness. Users get updates by reloading the bookmarked tab. The Cloudflare Pages build pipeline adds ~30s of lag between push and live page.

### 3.6 Per-spec page

The existing per-spec `spec-NNNN.html` page (frontmatter dump + event timeline + repo links) keeps its current minimal shape. It picks up the new stylesheets so its links and chips inherit the system tones, but no layout changes. Out of scope for this spec to redesign the per-spec subpage.

## 4. Out of scope

This spec does NOT:

- Make the dashboard interactive — no sort, no filter, no drill-down JS in production. The preview mockup's idle/in-flight toggle is removed from the renderer's output.
- Poll for live updates. Refresh-on-tab-focus only.
- Add a "failed cycle" hero variant. The CSS exposes `.stage--fail` for marks but no full failed-hero layout. We design that variant against a real failure when one occurs.
- Modify the dashboard's hosting (Cloudflare Pages) or its build workflow (`.github/workflows/dashboard.yml`). The output directory and asset filenames stay the same.
- Add new design tokens. Every color, font, spacing, and elevation reads from existing `--md-*` and `--p-*` tokens in `design-system/assets/styles/tokens-and-primitives.css`.
- Add navigation between pages. Existing per-spec link pattern stays — clicks on a spec ID go to `spec-NNNN.html`, clicks on a draft go to `draft-NNN.html`.
- Redesign the per-spec subpage (`spec-NNNN.html`) or the per-draft subpage (`draft-NNN.html`).
- Backfill richer event histories on already-deployed specs (0149/0150/0151/0152). Their activity-feed rows show whatever frontmatter timestamps exist; missing events stay missing.
- Touch the DR app (`src/dual_research/`) for any reason. All changes are under `scripts/spec_lifecycle/`, `prototypes/dashboard-redesign/`, `tests/spec_lifecycle/`, and the host-side `~/.claude/skills/dev-next/SKILL.md` (event emission additions).

## 5. Test plan

- [ ] `tests/spec_lifecycle/test_render_dashboard.py` — extend existing tests to assert the rendered index contains the new section anchors: `.hero--idle` or `.hero--inflight`, `.pipe`, `.metrics`, `.qtable`, `.feed`, `.drafts`, `.foot`. Existing "all sections present" test continues to pass.
- [ ] `tests/spec_lifecycle/test_stages.py` (new) — for `compute_stages(spec_id, events)`: given a fixture event stream, returns the expected `StageState` list (done/current/queued/fail). Test all eleven stages, plus the `failure_step` path.
- [ ] `tests/spec_lifecycle/test_render_dashboard.py::test_idle_vs_inflight_hero` (new) — render with zero in-progress specs → assert `hero--idle` class present, `hero--inflight` absent. Render with one in-progress spec → assert `hero--inflight` present with all 11 `.stage` rows.
- [ ] `tests/spec_lifecycle/test_render_dashboard.py::test_assets_copied` (new) — after `main(['--out', tmp_path])`, both `tokens.css` and `components.css` exist in the output dir alongside `index.html`.
- [ ] Manual — render against the live repo state (`uv run python -m scripts.spec_lifecycle.render_dashboard --repo-root . --out /tmp/dr-dash`) and compare side-by-side with `prototypes/dashboard-redesign/mockup.html`. Visual diff acceptable.
- [ ] Manual — after deploy, edit spec 0154's (or the then-next queued spec's) frontmatter to `status: in_progress` temporarily and observe the Cloudflare-built dashboard render the in-flight hero. Revert. Confirms in-flight data path works against real Cloudflare builds.
- [ ] Full `uv run pytest tests/ -q` suite passes.

## 6. Risks

- **CSS asset copying under Cloudflare's build environment.** The renderer must `shutil.copy` two stylesheets from `design-system/assets/styles/` into `dist/`. The Cloudflare build clones the repo with both directories present, so the copy succeeds in CI. Risk: if a future restructure moves `design-system/` the renderer breaks. Mitigation: the asset-copy step raises `FileNotFoundError` with a clear message and the `test_assets_copied` test catches the regression locally before push.
- **Event-step naming churn.** If a future spec adds new event step names that `stages.py` doesn't map, the timeline silently skips them. Mitigation: `compute_stages()` returns an `unknown_events: list[str]` field; the renderer prints them as a build-log warning in CI so they're visible without breaking the page.
- **Font loading.** The mockup uses Google Fonts (Roboto Flex + Roboto Serif + Material Symbols Outlined). If Cloudflare's edge fails to fetch them, the page falls back via the existing `system-ui` + `serif` chain in tokens. Visually acceptable degraded state. No mitigation needed.
- **Event sidecar gaps for older specs.** Backfilled specs (0149/0150/0151/0152) have either no event sidecar or only a sparse one. The activity feed for them shows whatever exists; missing events are not synthesized from frontmatter timestamps. Documented as expected. Going forward, every spec going through `/dev-next` after this spec ships has full event coverage.
- **SKILL.md updates require manual install.** The `~/.claude/skills/dev-next/SKILL.md` file is a user-side artifact, not part of the DR repo. The implementer of this spec must update both the in-repo documentation (CONTRIBUTING.md mentions of the dev cycle stages) AND the SKILL.md file in the user's home directory. The post-ship handoff file lists this as a manual step.
- **Two in-progress specs at once.** Renderer handles N≥1 with stacked layout but the underlying invariant ("one cycle at a time") is enforced by `/dev-next` pre-flight (`specs/0152-spec-lifecycle-system-v1.md:215`). If the invariant breaks, the renderer doesn't crash — it just shows both. Accepted.
