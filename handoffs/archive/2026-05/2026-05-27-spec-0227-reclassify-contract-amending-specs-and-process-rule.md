---
spec: "0227"
date: 2026-05-27
kind: post-deploy
version: 1.46.1
pr: https://github.com/Lexiz/dual-research/pull/265
---

# Spec 0227 — Reclassify 4 contract-amending specs + add CLAUDE.md contract-change rule

## What landed

- Reclassified four contract-amending specs from `bug` per Cowork synthesis §4 + 0226 debrief §5. Final frontmatter labels and bumps:
  - [`specs/0137-substantive-convergence-escape-valve.md`](../specs/0137-substantive-convergence-escape-valve.md) — `type: new-feature`, `label: new-feature`, `version_bump: MINOR` (older schema also migrated: `version-bump` hyphen → `version_bump` underscore; added previously-missing `type:` field).
  - [`specs/0140-phase4-deadlock-extractor-and-escape-valve.md`](../specs/0140-phase4-deadlock-extractor-and-escape-valve.md) — `type: new-feature`, `label: new-feature`, `version_bump: MINOR` (same schema migration as 0137).
  - [`specs/0218-phase4-status-survives-truncation.md`](../specs/0218-phase4-status-survives-truncation.md) — `type: breaking`, `label: breaking`, `version_bump: MAJOR`.
  - [`specs/0219-phase4-section-delta-contract-v2.md`](../specs/0219-phase4-section-delta-contract-v2.md) — `type: new-feature`, `label: new-feature`, `version_bump: MINOR`.
  All four spec bodies are byte-identical below the closing `---` (verified via `git diff --stat` showing only frontmatter-line changes).
- Added new `### Contract-changing specs are not `bug`s` subsection to [`CLAUDE.md`](../CLAUDE.md) under `## Spec workflow` — six bullets enumerating the categories of behaviour-change that may not ship under a `bug` label (phase mechanics, convergence rules, lifecycle state machine, categorisation taxonomy, first-class event types, **verifier invariants — gating or reporting, implementation-time additions included**). The sixth bullet closes the implementation-cycle drift gap the 0226 debrief surfaced (spec 0225 shipped 22 invariants vs. 19 agreed at v3 sign-off — same drift class one cycle inward from spec authoring).
- CHANGELOG entry under `## [1.46.1] — 2026-05-27`; in-app changelog sidecar regenerated at [`src/dual_research/ui/static/version-notes.json`](../src/dual_research/ui/static/version-notes.json).
- Version bumped 1.46.0 → 1.46.1 in [`pyproject.toml`](../pyproject.toml) and [`src/dual_research/__init__.py`](../src/dual_research/__init__.py).

## Verification

- `uv run pytest tests/ -q` — **2088 passed in 27.00s**. No new failures vs. pre-change baseline (no source-code touches; PATCH bump is docs/metadata only).
- GH Actions deploy.yml run [26477702837](https://github.com/Lexiz/dual-research/actions/runs/26477702837) — `success`.
- Live fly app at `https://dual-research-alex.fly.dev/` returns HTTP 200.

## Deferred during implementation

- **Reconciler false-positives external citations under markdown-link display text.** [`scripts/spec_lifecycle/reconcile.py:25-27`](../scripts/spec_lifecycle/reconcile.py:25) compiles a citation regex over the spec body but does not model markdown link syntax. Citations of the shape `[basename.md:line-range](../cowork/full-path.md)` — used heavily for external Cowork evidence references that legitimately live outside the repo per `CLAUDE.md` memory — get matched as `basename.md:line` from the display text, then fail the in-tree existence check at [`reconcile.py:62-87`](../scripts/spec_lifecycle/reconcile.py:62), producing spurious "semantic drift" exit-3 returns. Spec 0227's reconcile produced 9 such false positives (all internal in-tree citations were clean); this was overridden manually after `ls -la ../cowork/...` confirmed the cited files exist. The reliable fix is either (a) skip-match inside markdown link display text by tracking bracket nesting, or (b) require the canonical file:line citation to live in the link's href rather than its display text. Worth a refactoring spec — the workaround today is "operator inspects, overrides if all external-citation false positives".

## Next in queue

`uv run python -c "from scripts.spec_lifecycle.pick_next_number import current_queue; q = current_queue('specs'); print(q[0][1] if q else 'EMPTY')"` to identify, or check the dashboard.
