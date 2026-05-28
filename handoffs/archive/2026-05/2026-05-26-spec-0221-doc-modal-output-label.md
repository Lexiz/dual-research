---
spec: "0221"
date: 2026-05-26
version: 1.45.2
pr: https://github.com/Lexiz/dual-research/pull/259
---

# Spec 0221 handoff — Fix: DocumentModal labels doc/doc-live body tab "Output" instead of "Content"

Ships v1.45.2. Single-line surgical fix to the Phase 3 converged-draft and Phase 5 final-draft full-view modals so the body tab reads "Output" instead of the generic "Content" — readers were misreading the old label as prompt/spec content and missing the actual phase output sitting one tab away from "Agent Input".

## What landed

- `src/dual_research/ui/static/run-detail.jsx` — `DocumentModal` (around line 5063) gains `const isDocItem = item.kind === 'doc' || item.kind === 'doc-live'` and gates the body-tab descriptor's label as `isDocItem ? 'Output' : 'Content'`. The tab `id` stays `'content'` so `TABS_CANON` ordering at line 4962 continues to position the body tab second on Phase 3 (after "Agent Input") and as the only tab on Phase 5 (no `turnKey` → no input tab). Out-of-scope per spec §7: `NegotiateReviewModal` / `DraftReviewModal` (turn / plan modals) are untouched and continue to render their "Content" tab.
- `src/dual_research/ui/static/index.html` — cache-bust query for `run-detail.jsx` bumped from `?v=0209a` to `?v=0221a` so production browsers with the stale JSX cached pick up the new label. Other JSX files keep their existing cache-bust strings (`?v=0209a` / `?v=0220c`).
- `tests/test_spec_0221_doc_modal_output_label.py` — three source-pattern tests per the spec 0206 doctrine: positive regex for the `isDocItem ? 'Output' : 'Content'` ternary, positive regex for the `isDocItem` predicate definition, and antipodal-absence regex for the pre-fix unconditional `label: 'Content'` block. Full suite 2021 passed.
- `CHANGELOG.md` — new `## [1.45.2] — 2026-05-26` section under `## [Unreleased]`. Bumps `pyproject.toml` + `src/dual_research/__init__.py` + `uv.lock` mirror to 1.45.2 (PATCH).
- `src/dual_research/ui/static/version-notes.json` — regenerated via `scripts/build_version_notes.py` per the dev-next step 15b rule, now 210 entries (was 209), with v1.45.2 at the top.

## Decisions made during implementation

- **Antipodal-absence regex scoped to DocumentModal.** The spec's literal antipodal `id:\s*'content',\s*\n\s*label:\s*'Content',\s*\n\s*content:\s*<LazyMarkdownBody` also matches an unrelated modal at ~line 7000 (a turn-modal path that uses `LazyMarkdownBody` with a `User prompt` input tab). That modal is out of scope per spec §7. Tightened the regex to require the trailing `\},\s*\n\s*item\.turnKey\s*&&` line — which is DocumentModal's unique signature (the conditional Agent Input tab) — so the test only enforces the post-fix shape in DocumentModal and the unrelated turn modal at line 7000 remains correctly green.
- **Cache-bust query bumped on JSX edit.** The project convention surfaced in spec 0220 (PR #257) bumps the `?v=…` query on JSX files when their content changes (`how-it-works.jsx` and `app.jsx` went `0209a` → `0220c`). Applied the same pattern: `run-detail.jsx` went `0209a` → `0221a`. Without it, returning users with the stale JSX cached at the old query key would still see "Content".
- **PR description carries prose verification, not an embedded screenshot.** Followed PR #258 / #257 conventions — cited the `preview_eval` output enumerating the tab strip as `["Agent Input", "Output", "Web Search"]` plus the `aria-selected="true"` confirmation on the Output tab. The Claude Preview MCP screenshot was captured locally for orchestrator verification (Phase 3 converged-draft modal on the completed `20260519-132908-backend-language-choice` run, dark mode); it does not need to be hosted to satisfy spec §5's runtime cross-check.

## Verification

- **Local pytest:** `uv run pytest tests/ -q` → 2021 passed in 26.05s on the merge commit.
- **Runtime cross-check:** after the deploy.yml run (run id `26462717454`) completed cleanly, `curl https://dual-research-alex.fly.dev/api/health` returns `{"ok":true,"version":"1.45.2","backend":"supabase"}`. Pre-deploy, on the local dev server with `?v=0221a` active, the Phase 3 converged-draft modal enumerated tabs as `["Agent Input", "Output", "Web Search"]` (was `["Agent Input", "Content", "Web Search"]` pre-fix); the Output tab content rendered the converged draft body (`# Backend Language Choice for Partner Vetting — Final Research Document` / `## 1. Summary` …). Acceptance scenarios 1 and 2 of the spec verified.

## Operational notes

- **Stale .git/index.lock found during the cycle.** Mid-cycle the `git add` step failed with `Unable to create .git/index.lock`. No git process was active; the lock was empty (0 bytes) and timestamped at the moment of an earlier `queue_state push-files-to-main` call — likely a crashed or interrupted subprocess from a prior session. Removed manually (`rm .git/index.lock`) and proceeded. If this recurs, file a follow-up to harden `scripts/spec_lifecycle/queue_state.py` against partial-write exits that leave the index locked.
- **Pre-flight stash recovered the dirty tree.** The cycle opened on a dirty working tree (four orchestrator files + a `cowork/` untracked directory). Stashed via `git stash push -u -m "dev-next pre-flight stash …"` per the pre-flight step 2 contract; recoverable via `git stash pop` from this checkout.
