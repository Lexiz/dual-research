---
spec: "0259"
date: 2026-05-31
version: 1.67.1
pr: https://github.com/Lexiz/dual-research/pull/301
kind: post-deploy
---

# Spec 0259 — delete the dead legacy phase3 runner

Deployed **v1.67.1** via [PR #301](https://github.com/Lexiz/dual-research/pull/301). Pure dead-code deletion — no live behavior change.

## What landed

- **Deleted `orchestrator/phase3.py:run_phase3`** — the legacy single-shot phase-3 runner, unreachable from the live entry point since the spec-0118 v2 rewrite. The live driver is `dr_run.run_dr_phase3`, aliased as `run_phase3` in `run.py` (so `run.py:482` resolves to `run_dr_phase3`, never the deleted def). This finishes the parallel cleanup [spec 0257.1](../specs/0257.1-delete-dead-legacy-standing-items-surface.md) did for the legacy phase2/phase4 runners.
- **Preserved `Phase3Outcome` and `current_draft_path`** — both still live-imported (`run.py:41`, `dr_run.py:80`/`:1367`, `finalize.py:9`/`:150`). After deletion `phase3.py` is just those two symbols plus the two imports they need (`dataclass`, `Path`); the 7 module-level imports used only by `run_phase3` (`time`, `AgentCall`, the `events` quartet, `run_one_call`, `list_turns`, `SessionContext`, `write_atomic`, `FsdItem`, `drafting_prompt`, `drafting_input_bundle`) were removed.
- **Test surgery** in `tests/orchestrator/test_phase3_4_final.py`: dropped `run_phase3` from the import, deleted `test_phase3_writes_draft_and_advances_state` + `test_phase3_raises_without_drafter`, and removed the `ScriptedAgent` helper + the `AgentResult`/`TokenUsage` module-level import left orphaned *solely* by that deletion. Every live-surface test in the file is kept (`current_draft_path` routing, `confidence_tag` / `render_metadata_header` / `emit_final`, the `Phase2Outcome` / `Phase4Outcome` contracts).
- PATCH bump 1.67.0 → 1.67.1; CHANGELOG `### Removed` entry + version-notes sidecar regenerated.

## Verification

- `grep -rn "def run_phase3\|async def run_phase3" src/` → nothing; `grep -rn run_phase3 src/` → only the `run.py` alias/call pair (both → `run_dr_phase3`).
- Clean import of `run` / `dr_run` / `finalize` / `phase3`; `Phase3Outcome` + `current_draft_path` resolve.
- `uv run pytest tests/ -q` → **2449 passed**.
- deploy.yml run `26706680637` → success; live app responds at v1.67.1.

## Reconcile note

One mechanical drift fixed at reconcile time: §2 cited `finalize.py:150` (bare filename) — qualified to `src/dual_research/orchestrator/finalize.py:150` to match the spec's other full-path citations. No semantic drift; all `## 2` citations pointed at live surfaces.

## Merge hygiene note

`dashboard/queue-state.json` was accidentally swept into the first branch commit by `git add -A`, which conflicted with the Flush-2 copy on `origin/main`. Resolved by a second branch commit restoring the branch copy to `origin/main` before the squash merge. The squash collapses both commits, so the merged history is clean. Going forward, queue-state.json should be excluded from feature-branch `git add` — it is managed solely on `origin/main` via `push-files-to-main`.
