---
kind: draft
draft_id: "004"
slug: author-skills-prompt-for-disposition-at-queue-time
title: "`/spec-queue` + `/spec-promote` + `/spec-draft` skills: prompt for `disposition` interactively rather than relying on the validator error to surface omissions after the fact"
status: draft
created: 2026-05-27
source_session: deferred-from-0229.1
parent_spec: "0229.1"
disposition: archive
disposition_reason: "Auto-captured deferral; disposition to be re-triaged on promotion."
---

# Draft 004 — author skills prompt for `disposition`

> **Source:** spec 0229.1 handoff, "Deferred during implementation" item 2 — [handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:30](handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:30).

## Context

Spec 0229.1 added a hard validator gate at [`scripts/spec_lifecycle/validator.py:32-58`](scripts/spec_lifecycle/validator.py:32) requiring `disposition` and `disposition_reason` on every dev spec and draft. The gate fires at the close of every `/spec-queue` / `/spec-promote` / `/spec-draft` invocation — but the author only sees the error after they've drafted the entire spec body. The better UX is to ask up-front, mid-conversation, so the author makes the triage call deliberately rather than retroactively.

The handoff at [`handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:30`](handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:30) frames it: *"the validator currently catches omissions with a hard error, but the UX could ask up-front instead of after-the-fact."*

The skill files live out of repo per CLAUDE.md's two-worktree split:

- `~/.claude/skills/spec-queue/SKILL.md`
- `~/.claude/skills/spec-promote/SKILL.md`
- `~/.claude/skills/spec-draft/SKILL.md`

Like draft 003, this is captured as a draft for record, not as a dev spec — the change has no in-repo surface to land.

## Proposed change (out-of-repo, for record)

Each of the three SKILL.md files gains a new step before the final commit: explicitly prompt the user for `disposition` and `disposition_reason`. The prompt names the three valid values and asks for the rationale in one sentence. The skill then writes those values into the frontmatter before the validator runs.

For `/spec-draft`, the default disposition is `archive` per spec 0229 §2.5 (drafts are scratch; the disposition assignment is informational). For `/spec-queue` and `/spec-promote`, no default — the author must pick consciously since these reach a `/dev-next` cycle if picked as `ship`.

## Unresolved questions

- Should the skill suggest a default based on the spec's `type` field — e.g. a `bug` defaults to `ship` because bug fixes typically should reach the queue, while a `refactoring` defaults to `defer` because refactors are often low-priority?
- Should the skill round-trip the disposition through a single `/spec-queue` step, or split into "draft skeleton → user picks disposition → finalize"? The former is one screen of UX; the latter is two.
- Should the prompt be a structured choice (a, b, c) or freeform with validation? Structured is harder to typo; freeform is faster.

These questions resolve at implementation time against the user's preference. The draft is captured as a record.

## Pointer

Out-of-repo: `~/.claude/skills/spec-queue/SKILL.md`, `~/.claude/skills/spec-promote/SKILL.md`, `~/.claude/skills/spec-draft/SKILL.md`.

This draft is informational; resolve via direct SKILL.md edits, not via `/dev-next` cycle.
