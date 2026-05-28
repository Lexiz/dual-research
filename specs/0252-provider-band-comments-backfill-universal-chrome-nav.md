---
kind: dev
spec: "0252"
slug: provider-band-comments-backfill-universal-chrome-nav
title: All Runs Comments tally + critique backfill CLI, universal chrome, and nav-label wrap fix
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.62.0
status: queued
depends_on: []
complexity: L
created: 2026-05-29
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "Directly authored from a verified, browser-confirmed prototype; ships on its own merits, not a deferred carve-out."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0252 — All Runs Comments tally + critique backfill CLI, universal chrome, and nav-label wrap fix

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** —
> **Bump:** MINOR — adds `comments` as a first-class category in the `critique_by_agent` write-time tally (a contract change to the spec-0248 tally shape) and a new `backfill-critique` maintenance subcommand.
> **Evidence:** spec 0248 (provider metric band, DS §4.9); DS §9.3 (fixed Q→D→I→C category tones); verified browser prototype (local `serve`, 6 real runs); fixture `tests/fixtures/anchor-runs/20260528-094743-backend-language-choice` proves `compute_critique_by_agent` is correct (Claude Q 5/5, D 5/5, I 3/3; GPT Q 4/4, D 6/6, I 5/5). The reference patch (`design-system/.../composed-components.css`, `aggregator.py`, `critique_tally.py`, `app.jsx`, `components.css`, `how-it-works.jsx`, `run-list.jsx`) was confirmed end-to-end; existing tests pass (`tests/test_spec_0248_all_runs.py` 12/12; 160 critique/aggregator tests).

---

## 1. Context

Three independent defects converge on one user-visible surface — the All Runs page and the global chrome that frames every route — so they ship as one coherent UI-consistency pass. **(P1)** The provider metric band (DS §4.9, spec 0248) shows all critique counters as `0` because every run currently displayed in production **predates** spec 0248's write-time tally, so their `metrics.json` carries `critique_by_agent: null`; the read path ([`aggregator.derive_agent_breakdowns`](src/dual_research/ui/aggregator.py:369)) correctly renders `0` when the payload is absent (spec 0248 §7), and new runs populate fine — so this is a **data-backfill** problem, not a compute bug. The same band also never rendered the **Comments** category: the canonical order is Q→D→I→**C** (DS §9.3) and `_CATEGORIES` in [`critique_tally.py`](src/dual_research/ui/critique_tally.py:27) stops at three. **(P2)** Only the list route renders the `.ar-chrome` bar (`AllRunsChrome`); every other route ([`app.jsx`](src/dual_research/ui/static/app.jsx:159) `ChromeBar` branch) renders a different 44 px `.md-appbar` with a different theme toggle — the top bar changes shape as you click between tabs. **(P3)** The How-it-works / Changelog left-nav anchor is `display:block` with an `inline-block` number, so a wrapped label's second line falls under the *number* column instead of the label, and the changelog summary is hard-sliced to 30 chars mid-word ([`how-it-works.jsx`](src/dual_research/ui/static/how-it-works.jsx:1081)).

**Source traceability (spec 0198)** — every atomic item from `/tmp/allruns-howitworks-fixes-NOTES.md`:

| source item | source quote / ref | spec section |
|---|---|---|
| P1a counters read 0 (root cause = runs predate 0248 tally) | NOTES §1a "runs shown in production predate spec 0248's write-time tally" | §2.1 |
| P1a backfill module `audit/backfill_critique.py` | NOTES §"backfill CLI — NOT in the patch" | §2.1 |
| P1a `cli.py` `backfill-critique` subcommand + flags | NOTES §backfill "CLI wiring …, with flags --run / --all …" | §2.1 |
| P1a `--push` upserts Supabase `runs.metrics` JSONB | NOTES §backfill "--push is what actually fixes the deployed cards" | §2.1, §4 |
| P1a preserve `/api/runs` cheap-path-never-replays | NOTES §1a "the list path MUST stay cheap … Keep that guarantee" | §2.1, §5 |
| P1b Comments badge, Q→D→I→C, C=idle, single count | NOTES §1b | §2.2 |
| P1b backend `critique_tally` (`_CATEGORIES`/`_empty_agent`/`_typed_lists` 4-tuple incl. `reconstruct_comments` legacy fallback/compute) | NOTES §"Files in the patch for Problem 1" | §2.2 |
| P1b read path `aggregator.derive_agent_breakdowns` reads `comments` | NOTES §Files P1 | §2.2 |
| P1b frontend ProviderCard badge + explicit `.rc-rs--q/d/i/c` tone classes replacing `:nth-child` | NOTES §Files P1 | §2.2 |
| P2 universal `.ar-chrome` on every route (app.jsx + run-list.jsx, `route` prop, list-only Active/Archived gate, connected-poll fallback, segmented toggle, `#main` calc(100vh-60px)) | NOTES §"Files in the patch for Problem 2" | §2.3 |
| P2 dead-code removal (ChromeBar/RightCluster/ChromeTab/ConnectionPill/AppVersionChip) | NOTES §"Cleanup the spec should call out (NOT yet in patch)" | §2.3 |
| P3 nav two-column flex anchor + removed 30-char changelog slice (how-it-works.jsx + both CSS files) | NOTES §"Files in the patch for Problem 3" | §2.4 |

## 2. Proposed change

### 2.1 — Backfill CLI for `critique_by_agent` (the only piece NOT in the reference patch)

The fix for the zero counters is a one-shot maintenance command that computes and persists `critique_by_agent` into existing runs, mirroring the existing `recompute-costs` / `reconcile-costs` pattern exactly.

- **New module** `src/dual_research/audit/backfill_critique.py`, mirroring [`audit/recompute.py`](src/dual_research/audit/recompute.py):
  - `backfill_critique_run(session_dir: Path, *, write: bool = True) -> BackfillReport` — load `Metrics` from `session_dir/metrics.json`, set `metrics.critique_by_agent = compute_critique_by_agent(session_dir, metrics.totals_by_agent())`, call `metrics.save(...)` when `write`, and return a small report dataclass (run id, before/after non-empty flag, per-category counts).
  - `backfill_all(runs_dir: Path, *, write: bool = True) -> list[BackfillReport]` — iterate run dirs that contain a `metrics.json`.
- **CLI wiring** in [`src/dual_research/cli.py`](src/dual_research/cli.py:569) — add a `backfill-critique` subcommand next to `recompute-costs` (mirror `_run_recompute`), with: `--run` / `--all` (mutually exclusive, **one required**), `--runs-dir`, `--dry-run`, `--push`. `--dry-run` implies `write=False` and prints the would-write report. `--push` loads Supabase creds (`load_supabase_credentials`) and, for each rewritten run, calls `RemoteSession.from_credentials(...).push_session_dir(session_dir)` — which upserts the `metrics` JSONB column on the `runs` table.
- **Operational step** (document in the CHANGELOG / PR): `uv run dual-research backfill-critique --all --push` is what fixes the **deployed** cards, because the hosted app reads metrics from the Supabase `metrics` column (`server.py` `_supabase_list_runs` → `derive_agent_breakdowns(r.get("metrics"))`).
- **Cheap-path guarantee preserved:** the backfill is an explicit out-of-band command. The `/api/runs` list path MUST continue to never replay transcripts (spec 0248 §1/§7); the existing `summarize_run` cheap-path guard test stays green. The persistence shape already supports this — `persistence/metrics.py` `Metrics` has the `critique_by_agent` field, `to_json()` emits it, and the loader reads it; **no schema migration** (`runs.metrics` is already JSONB).
- The orchestrator terminal write path (`orchestrator/run.py` `_populate_critique_tally`) is already correct; adding `comments` to the tally (§2.2) flows through automatically for **new** runs.

### 2.2 — Comments category in the band (backend + read path + frontend)

Comments have **no closure protocol** (the `Comment` dataclass in `src/dual_research/ui/models.py` has no `status` field — they stay raised), so the band renders Comments as a **single idle-toned count** (raised only; the persisted "solved" half is always 0), distinct from the raised/solved **pair** Q/D/I get.

- **Backend** [`critique_tally.py`](src/dual_research/ui/critique_tally.py:27): `_CATEGORIES += "comments"`; `_empty_agent()` += `"comments": [0, 0]`; `_typed_lists()` returns a **4-tuple** — `comments` from `project_typed_lists(bundle)` for current v2 runs and from a new `reconstruct_comments(session_dir, phase=2)+phase=4` legacy fallback ([`comments.reconstruct_comments`](src/dual_research/ui/comments.py:43)) for pre-0114 runs; `compute_critique_by_agent()` calls `_tally_into(out, "comments", comments)`. `_tally_into` leaves the "solved" half at 0 because `Comment` has no `status` attr (getattr default).
- **Read path** [`aggregator.derive_agent_breakdowns`](src/dual_research/ui/aggregator.py:372): iterate `("questions", "disagreements", "issues", "comments")`.
- **Frontend** [`run-list.jsx`](src/dual_research/ui/static/run-list.jsx) `ProviderCard`: each `RC_PROV_GROUPS` entry gains a `tone` (`q`/`d`/`i`) and each Q/D/I badge carries `rc-rs rc-rs--<tone>`; a new single-count Comments badge (`<span class="rc-rs rc-rs--c">` with cat letter `C` + `.rc-rs--count rc-rs--count-cmt` value) renders after I, before the searches count.
- **CSS** (both [`components.css`](src/dual_research/ui/static/components.css) AND [`design-system/assets/styles/composed-components.css`](design-system/assets/styles/composed-components.css), one commit): retire the fragile `.rc-rs:nth-child(1|2|3)` tone selectors for explicit `.rc-rs--q/d/i/c .rc-rs__cat` classes; add `.rc-rs--count-cmt { color: var(--p-idle); background: color-mix(in srgb, var(--p-idle) 16%, transparent); }`.

**DS citations:** DS §9.3 — category order Q→D→I→C and tones Q=info · D=warn · I=err · **C=idle** (the idle tone is canonical for the no-closure Comments badge); DS §4.9 + spec 0248 §2.5 — the provider metric band anatomy and the raised→neutral / solved→ok / searches→info tone mapping the new badge composes with. "Comments" is the canonical category label per DS §9.5.

### 2.3 — Universal chrome on every route

Promote `.ar-chrome` (`AllRunsChrome`) from the All Runs route to the single app bar for **every** route, with the segmented `ThemeToggleSegmented` everywhere.

- [`run-list.jsx`](src/dual_research/ui/static/run-list.jsx) — `AllRunsChrome` generalized with a new `route = 'list'` prop driving tab active states (All runs / Compare / Search / How it works), gating the list-only **Active/Archived** admin toggle to `route === 'list'`, falling back to polling `window.__lastSseConnected` (the source `ConnectionPill` reads) for the connected pill on non-list routes, swapping the `md-icon-btn`/`contrast` toggle for `<ThemeToggleSegmented theme onToggle>`, and passing `route={{ view: route }}` to `AvatarMenu`.
- [`app.jsx`](src/dual_research/ui/static/app.jsx:159) — render `<AllRunsChrome route={route.view} …>` for every non-list route (list still renders its own inside `ListScreen`); remove the detail-only `ChromeBar` branch; set `#main` height to `calc(100vh - 60px)` for all non-list routes (was 44 px).
- **Dead-code removal (in scope):** delete the now-unused `ChromeBar`, `RightCluster`, `ChromeTab` and their now-orphaned children `ConnectionPill`, `AppVersionChip` from `app.jsx`. **Keep** `AvatarMenu` and `ThemeToggleSegmented` — both are still referenced by `AllRunsChrome`. Verify `AvatarDisc` / `MenuItem` ownership before deleting (spec 0248 lifted copies into `run-list.jsx`; confirm `app.jsx` holds no live references).
- The How-it-works page's own `hiw-page__header` sub-toggle is **page content, not chrome**, and stays unchanged.

**DS citation:** DS §2.2 / §2.12.1 (top chrome), §4.9 (the `.ar-chrome` host). No new primitive — this consolidates onto the existing one.

### 2.4 — How-it-works / Changelog nav-label wrap

- [`how-it-works.jsx`](src/dual_research/ui/static/how-it-works.jsx:1081) — wrap both the How-it-works and Changelog nav-item labels in `<span class="menu-section-lbl">…</span>`; remove the changelog `(e.summary||'').slice(0, 30)` hard-slice (CSS line-clamp handles length).
- **CSS** (both files): make the anchor a two-column flex row — both `.hiw-overlay__menu-list li a` (higher specificity, the controlling rule) and `.hiw-overlay__menu-list a` → `display:flex; align-items:flex-start; gap`. `.menu-section-num` → `flex:0 0 auto; width:48px; line-height:1.4`. New `.menu-section-lbl` → `flex:1 1 auto; min-width:0; line-height:1.4;` with a 2-line `-webkit-line-clamp`. Wrapped lines then align under the label column, not the number.

## 3. User stories & acceptance criteria

### 3.1 — User stories

> As a `viewer`, I want the All Runs provider band to show real Question / Disagreement / Issue / Comment counts for older runs, so that the cards aren't misleadingly all-zero.
> As a `viewer`, I want a Comments count in the band, so that I can see how much each agent annotated without claiming an open issue.
> As an `admin`, I want one `backfill-critique --all --push` command, so that I can repair the deployed cards in one out-of-band step without touching the cheap list path.
> As a `viewer`, I want the top bar to look identical on every route, so that navigation doesn't reshape the chrome under me.
> As a `viewer`, I want wrapped left-nav labels to align under the label, so that the How-it-works / Changelog index reads cleanly.

### 3.2 — Acceptance scenarios (BDD)

> **Scenario 1:** Comments badge renders in canonical order
> GIVEN an All Runs card whose run has a populated `critique_by_agent` including `comments`
> WHEN the provider band renders
> THEN a `.rc-rs--c` badge with cat letter `C` and a single `.rc-rs--count-cmt` value appears after the Issues (`.rc-rs--i`) badge and before the web-searches count, with no `solved` half.

> **Scenario 2:** Backfill repairs a pre-0248 run
> GIVEN a fixture run with items and `critique_by_agent: null` in its `metrics.json`
> WHEN `backfill-critique --run <dir>` is invoked (no `--dry-run`)
> THEN `metrics.json` is rewritten with a non-empty `critique_by_agent` whose `comments` pair is `[N, 0]` for an agent that raised N comments.

> **Scenario 3:** Chrome is identical across routes
> GIVEN the app is loaded on the run-detail route
> WHEN the top bar renders
> THEN it is the `.ar-chrome` header with the segmented `ThemeToggleSegmented` (no `.md-appbar`, no `md-icon-btn` contrast button), and the Active/Archived admin toggle is absent (list-only).

> **Scenario 4:** Wrapped nav label aligns under the label column
> GIVEN the How-it-works left nav with a label long enough to wrap
> WHEN the anchor renders
> THEN the anchor is `display:flex`, the number is a fixed 48 px column (`.menu-section-num`), and the wrapped second line of `.menu-section-lbl` aligns under the first line of the label, not under the number.

## 4. Data / Schema deltas

- **No migration.** `runs.metrics` is already a JSONB column (`supabase/migrations/0001_initial.sql`); `comments` is an added key inside the existing `critique_by_agent` object.
- **Tally contract delta:** `critique_by_agent[agent]` gains a `comments: [raised, 0]` pair. New runs populate it at terminal write; old runs populate it via §2.1's backfill. The "solved" half is structurally always `0` for comments (no closure protocol).
- **Backfill:** `backfill-critique --all` rewrites filesystem `metrics.json`; `--push` additionally upserts the Supabase `metrics` JSONB so the hosted/deployed cards reflect the recomputed tally.

## 5. Out of scope

- **No read-path recompute.** The `/api/runs` list path must never replay transcripts (spec 0248 §1/§7); the backfill is the only mechanism that writes the tally. The cheap-path guard test stays green.
- **No closure protocol for Comments.** Comments remain status-less; this spec does not add a raised/solved lifecycle for them — the badge is intentionally a single count.
- **The How-it-works `hiw-page__header` sub-toggle** is page content and is untouched.
- **No DS extension.** All elements map to existing DS sections (§4.9, §9.3, §2.2); no new primitive is introduced.

## 6. Test plan

- [ ] **UI source-pattern tests** (spec 0206, via [`tests/_ui_pattern_helpers.py`](tests/_ui_pattern_helpers.py)) at `tests/test_spec_0252_provider_band.py`, `tests/test_spec_0252_chrome.py`, `tests/test_spec_0252_nav.py` — each a positive post-fix regex + an antipodal-absence pre-fix regex:
  - [ ] ProviderCard Comments badge present (`rc-rs--c` + `rc-rs--count-cmt`) AND `.rc-rs:nth-child(` tone selectors absent from both CSS files.
  - [ ] `AllRunsChrome` carries a `route` prop and `app.jsx` renders it for non-list routes AND `ChromeBar`/`RightCluster`/`ChromeTab`/`ConnectionPill`/`AppVersionChip` are absent from `app.jsx`.
  - [ ] Nav anchor `.menu-section-lbl` present and anchor is `display:flex` AND the `(e.summary||'').slice(0, 30)` literal is absent from `how-it-works.jsx`.
- [ ] **Backend pytest** — `compute_critique_by_agent` returns a 4th `comments` pair `[N, 0]` for a fixture with comments; `_typed_lists` returns a 4-tuple; `derive_agent_breakdowns` surfaces `comments`.
- [ ] **Backfill pytest** — `backfill_critique_run` on a fixture WITH items rewrites `metrics.json` so `critique_by_agent` is non-empty and includes a non-zero `comments` raised count; `--dry-run` writes nothing.
- [ ] **Cheap-path guard** — the existing spec-0248 `summarize_run` cheap-path test still passes (no transcript replay on the list path).
- [ ] **PR description** — spec 0179's mandatory 8-capture parity grid (ProviderCard is touched), plus a Claude Preview screenshot of the universal chrome on a non-list route and the wrapped nav label.

## 7. Risks

- **`--push` writes production data.** Mitigation: `--dry-run` previews the report; `--push` is opt-in and idempotent (recompute is deterministic from the transcript); the upsert only touches the `metrics` column.
- **Dead-code removal breaks a stray reference.** Mitigation: the usage scan that motivated removal is encoded as an antipodal-absence test; `AvatarDisc`/`MenuItem` ownership is verified before deletion. If a hidden reference surfaces, revert the deletion (the chrome consolidation in §2.3 stands independently).
- **`-webkit-line-clamp` clamp differs across engines.** Low impact (cosmetic two-line cap); the flex two-column alignment — the actual fix — does not depend on the clamp. Revert the clamp alone if it misbehaves.
- **Legacy `reconstruct_comments` fallback raises on a malformed pre-0114 run.** Mitigation: `compute_critique_by_agent` already wraps the whole computation in a best-effort `try/except` that persists nothing on failure rather than risking the metrics write.
