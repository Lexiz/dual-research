---
kind: draft
draft_id: "003"
slug: dev-next-skill-filter-queue-on-disposition-ship
title: "`/dev-next` skill: filter the queue head on `disposition: ship` so backfilled-as-`archive` carve-outs are no longer picked"
status: draft
created: 2026-05-27
source_session: deferred-from-0229.1
parent_spec: "0229.1"
disposition: archive
disposition_reason: "Auto-captured deferral; disposition to be re-triaged on promotion."
---

# Draft 003 — `/dev-next` skill filters on `disposition: ship`

> **Source:** spec 0229.1 handoff, "Deferred during implementation" item 1 — [handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:29](handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:29).

## Context

Spec 0229.1 §2.4 explicitly notes: *"This change does NOT touch `/dev-next` itself — the skill at [`~/.claude/skills/dev-next/SKILL.md`](~/.claude/skills/dev-next/SKILL.md) (out of repo) will read the new field after `current_queue()` in [`scripts/spec_lifecycle/pick_next_number.py:131-160`](scripts/spec_lifecycle/pick_next_number.py:131) returns it."* The handoff at [`handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:29`](handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:29) names this as the natural follow-up: *"Until the skill change ships, every backfilled-as-`archive` spec is still picked by `current_queue()` and the queue-head consumer doesn't yet honour the field."*

The skill file lives at `~/.claude/skills/dev-next/SKILL.md` — out of repo per CLAUDE.md's two-worktree split: *"Two-worktree split: Authoring worktree at `/Users/alexlisitzky/dual-research-author/` — where `/spec-draft`, `/spec-queue`, `/spec-promote` run."* and the `/dev-next` skill itself is implemented in the user's `~/.claude/skills/` directory, not under spec governance.

This is captured as a draft (rather than a dev spec) for that exact reason: spec governance covers code under this repo, and the SKILL.md change has no in-repo surface to land. The change itself is small: after the `current_queue()` call in the skill's queue-iteration step, filter `[(spec_id, fm) for spec_id, fm in current_queue(...) if fm.get("disposition") == "ship"]`.

## Proposed change (out-of-repo, for record)

In `~/.claude/skills/dev-next/SKILL.md`, the step that consumes `current_queue(...)` (the pre-flight queue-head determination, exact step number depends on the skill's current structure) gains a one-line filter:

```python
queue = current_queue("specs")
shippable = [(spec_id, fm) for spec_id, fm in queue if fm.get("disposition") == "ship"]
if not shippable:
    # report empty actionable queue; halt
```

The corresponding `/dev-queue-run` skill at `~/.claude/skills/dev-queue-run/SKILL.md` consumes the same `current_queue()` indirectly and would inherit the filter via a shared helper, or duplicate the one-line filter — exact factoring decided at implementation.

## Unresolved questions

This draft is captured as a record. Because the change lives entirely in out-of-repo SKILL.md files, it has no canonical dev-spec target and will not be promoted into `/dev-next` via this draft. The promotion path, if any, would be a "skill maintenance" pass on the user's `~/.claude/skills/` tree, not a code spec.

Open items (to be re-triaged on any future promotion):

- Should the empty-actionable-queue case (every queued spec is `defer` / `archive`) halt with a clear message, or print the deferred cohort and exit non-zero? Spec 0229.1 doesn't legislate this.
- Does `/dev-queue-run` use a shared helper for the filter, or inline the logic in both skills?
- The dashboard's queue-head display (spec 0236, queued separately) should match whatever the skill filter does, to avoid drift between "what the dashboard shows next" and "what `/dev-next` actually picks."

## Pointer

Out-of-repo: `~/.claude/skills/dev-next/SKILL.md`, `~/.claude/skills/dev-queue-run/SKILL.md`.

This draft is informational; resolve via direct SKILL.md edits, not via `/dev-next` cycle.
