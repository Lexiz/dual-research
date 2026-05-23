---
spec: "0157"
date: 2026-05-22
version: 1.21.0
pr: "https://github.com/Lexiz/dual-research/pull/180"
---

# Handover — Spec 0157 — `/spec-queue` auto-decomposition (v1.21.0)

- **Date:** 2026-05-22
- **PR:** [Lexiz/dual-research#180](https://github.com/Lexiz/dual-research/pull/180)
- **Merge commit:** `4ea93e6`
- **Cycle time:** ~5 minutes (started 13:50:28Z, deployed 13:55:47Z)

## What landed

### Host-side (NOT in the PR — lives at `~/.claude/skills/spec-queue/SKILL.md`)

The actual behavior change is host-side: `/spec-queue` now decomposes large multi-domain conversations into N chained sub-specs when the conservative heuristic in step 1d fires.

- **Step 1d — Decomposition check.** Inserted between 1c (DS check) and Step 2. Prose-only — the LLM following the skill applies the heuristic. **Splitting fires only when all three signals hold:** 3+ independent file/domain surfaces with no implementation overlap; no shared unifying purpose; bundled complexity > L (> 250 body lines, > 5 file edits, or > 3 distinct `## 2.N` sub-entries). **Any single override wins back to bundle:** sequential dependencies, shared test plan, user-named-as-one-initiative.
- **Decomposed path sub-flow.** When 1d says split: identify N sub-specs by natural cleavage points → determine `depends_on` chains (chain / fork / independent) → topologically sort with complexity-ascending tie-break → run steps 3–7 once per sub-spec → populate inter-spec `depends_on` from the analysis. Bundle commits into one push if possible, otherwise accept N pushes.
- **Push-race handling on split.** Existing per-sub-spec retry logic (3 retries with `next_dev_number` recompute) applies independently. No automatic rollback of already-pushed sub-specs — partial-state surfaces at step 9 with clear next-step instructions.
- **Step 9 report branches three ways:**
  - Single-spec (today's format, unchanged path, classification + reasoning printed inline).
  - Multi-spec (lists each sub-spec with its `depends_on`, decomposition rationale, "run `/dev-next` or `/dev-queue-run`").
  - Partial-state (push race surfaced cleanly).

### In-repo (this PR)

- `tests/spec_lifecycle/test_pick_next_number_sequential.py` — locks in the per-sub-spec numbering contract. Two cases: from-empty (`0001 → 0002 → 0003`) and seeded (`0100 → 0101 → 0102 → 0103`). Asserts strictly increasing and no collisions when intermediate spec files are materialized between calls.
- `tests/spec_lifecycle/test_depends_on_frontmatter.py` — locks in the validator's acceptance of `depends_on` as `[]`, `["0154"]`, and `["0154", "0156"]` so the new flow's inter-spec chains can't regress the field contract.
- `pyproject.toml`, `src/dual_research/__init__.py` → **1.21.0**.
- `CHANGELOG.md` `## [1.21.0] — 2026-05-22` section.

## Tests

`uv run pytest tests/ -q` — **1490 passed** (1485 prior + 5 new across the two new test files).

## Deploy notes

Clean rolling deploy on the first attempt — no Fly machines-API timeout this round. Both machines on `deployment-...` running v1.21.0. Smoke: `https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.21.0","backend":"supabase"}`.

## How to verify the new behavior

The hard part — LLM judgment on when to split — can't be unit-tested. Real-world verification happens in future `/spec-queue` invocations:

- **Single-concept thread** ("fix this one bug at file:line") → bundles into one spec, no decomposition, single-spec step 9 format.
- **Synthetic multi-concept thread** (3+ independent surfaces, no shared purpose) → N specs with sequential queue positions, correct `depends_on` chain, multi-spec step 9 format listing all N.
- **0154-shaped thread** (7 sub-changes, shared "orchestrator hardening" purpose) → bundles into one spec; the unifying-purpose override fires.
- **Push race during decomposition** → partial-state report surfaces, no automatic rollback, user-driven cleanup.

## Queue at handoff

- **0158** — deferred-spec subagent in `/dev-next`. Queue position 1 (will be decremented from 2 by my final commit's re-rank step).

Per `feedback_pause_between_specs`: stopping here. Invoke `/dev-next` for 0158 (or `/dev-queue-run` if anything new gets queued in parallel and you want to drain).

## File map

```
# In-repo (this PR)
tests/spec_lifecycle/test_pick_next_number_sequential.py  # new
tests/spec_lifecycle/test_depends_on_frontmatter.py        # new
CHANGELOG.md                                               # [1.21.0] section
pyproject.toml, src/dual_research/__init__.py              # 1.21.0
specs/0157-spec-queue-auto-decomposition.md                # status: deployed
dashboard/events/0157.jsonl                                # event stream
handoffs/2026-05-22-spec-0157-...md                        # this file

# Host-side (not in repo)
~/.claude/skills/spec-queue/SKILL.md                       # step 1d + decomposed path + step 9 branches
```
