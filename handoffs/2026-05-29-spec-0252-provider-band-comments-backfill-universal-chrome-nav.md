---
spec: "0252"
date: 2026-05-29
version: 1.63.0
pr: https://github.com/Lexiz/dual-research/pull/290
kind: post-deploy
---

# Spec 0252 — All Runs Comments tally + critique backfill CLI, universal chrome, and nav-label wrap fix

Shipped v1.63.0 via [PR #290](https://github.com/Lexiz/dual-research/pull/290). Three independent All-Runs / chrome defects landed as one UI-consistency pass; 2420 tests pass; deploy.yml green; live app HTTP 200 at v1.63.0.

## What landed

- **§2.1 — `backfill-critique` CLI.** New [`audit/backfill_critique.py`](../src/dual_research/audit/backfill_critique.py) (`backfill_critique_run` / `backfill_all` / `BackfillReport`) + `cli.py` subcommand `backfill-critique [--run | --all] [--push] [--runs-dir] [--dry-run]`, mirroring `recompute-costs`. Recomputes `critique_by_agent` for pre-0248 runs (those whose `metrics.json` carries `critique_by_agent: null`) and rewrites `metrics.json`; `--push` upserts the Supabase `metrics` JSONB so the **deployed** cards repair. Registered in `main()` before the argparse build, so it's exempt from the spec-0243 Claude-Code host guard like the other read-only maintenance subcommands.
- **§2.2 — Comments category.** Q→D→I→**C** (DS §9.3). `critique_tally._typed_lists` returns a 4-tuple (with a `reconstruct_comments` phase-2+4 legacy fallback for pre-0114 runs); `_empty_agent` / `_CATEGORIES` carry `comments`; `compute_critique_by_agent` tallies it (solved half structurally 0 — `Comment` has no `status`). `aggregator.derive_agent_breakdowns` surfaces `comments`. `ProviderCard` (run-list.jsx) renders a single idle-toned Comments badge (`.rc-rs--c` + `.rc-rs--count-cmt`) after Issues. CSS (both files) retired `.rc-rs:nth-child(1|2|3)` for explicit `.rc-rs--q/d/i/c .rc-rs__cat` (C=idle).
- **§2.3 — Universal chrome.** `.ar-chrome` (60 px) is now the single app bar for every route. `AllRunsChrome` gained a `route` prop (active-tab state, list-only Active/Archived gate, `window.__lastSseConnected` poll for the connected pill on non-list routes, `ThemeToggleSegmented` everywhere). `app.jsx` renders it for non-list routes (`#main` → `calc(100vh - 60px)`); deleted `ChromeBar` / `RightCluster` / `ChromeTab` / `ConnectionPill` / `AppVersionChip`.
- **§2.4 — Nav-label wrap.** How-it-works / Changelog nav anchor is a two-column flex row (`.menu-section-num` fixed column + new `.menu-section-lbl`) in both CSS files; the 30-char changelog summary slice is removed (CSS line-clamp caps length).

## Verification

- `uv run pytest tests/ -q` → 2420 pass. UI source-pattern tests at `test_spec_0252_{provider_band,chrome,nav}.py`; backend at `test_spec_0252_backend.py`.
- **Runtime (Claude Preview MCP, local `serve`):** ran `backfill-critique --all` (no `--push`) on the local runs dir → 34 runs repaired (empty → non-empty). The All Runs band then rendered `Q 5 5 · D 6 6 · I 4 0 · C 2 · 🔍 32` — the single-count Comments `C` badge after Issues, before searches. `:nth-child` selectors confirmed absent from the live stylesheet; all four tone classes live. How-it-works route showed the identical `.ar-chrome` (no `.md-appbar`); nav anchors `display:flex; align-items:flex-start` with wrapped labels aligned under the label column.

## Operational note (deployed cards still show zeros until backfilled)

The code fix alone does **not** repair the *deployed* All Runs cards — production runs still carry `critique_by_agent: null`. To repair them, run **`uv run dual-research backfill-critique --all --push`** from a plain Terminal (sources Supabase creds; `--push` upserts the `metrics` JSONB). New runs populate the 4-category tally at terminal write automatically. The local-only backfill done during verification already repaired the laptop runs dir but did NOT push.

## Adjacent-spec test adjustments

- **spec 0220.1** (`menu-section-num`): kept `min-width: 48px` rather than the spec's literal `width: 48px` — `min-width` satisfies 0252's two-column flex AND preserves 0220.1's 6-char-version overlap fix, leaving its tests green untouched.
- **spec 0245** (archived toggle): reordered the condition to `route === 'list' && isAdmin && (` so the `isAdmin && (` adjacency the 0245 test locks stays intact while adding the list-route gate.
- **spec 0220** (`AppVersionChip`): the chip was deleted in §2.3; updated `test_app_version_chip_deep_links` to follow the deep-link capability to its new `.ar-pill__v` home in `AllRunsChrome`.

## Deferred during implementation

- **`DesignLanguageButton` is now orphaned in app.jsx** — it was rendered only inside the deleted `RightCluster` (the logged-out branch), so removing `RightCluster` left its declaration (`src/dual_research/ui/static/app.jsx`, the `function DesignLanguageButton` near the old right-cluster block) with zero references. The `/language` route stays reachable via the avatar menu's "Design language" item, so nothing functional is lost. Spec 0252 §2.3 enumerated exactly five components to delete and did not name `DesignLanguageButton`, so it was left in place to stay within the spec's explicit scope; `ActiveRunChip` was likewise already-dead pre-0252 and out of the named set. A small follow-up could sweep both now-dead declarations.
