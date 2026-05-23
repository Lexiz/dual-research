---
kind: dev
spec: "0158"
slug: deferred-spec-subagent
title: Deferred-spec subagent in /dev-next — auto-capture in-flight deferrals as queued specs or drafts
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.22.0
status: deployed
queue_position: 0
depends_on: []
complexity: M
created: 2026-05-22
queued_at: 2026-05-22T13:29:58Z
started_at: "2026-05-22T14:00:54Z"
merged_at: "2026-05-22T14:05:02Z"
deployed_at: "2026-05-22T14:07:02Z"
pr: "https://github.com/Lexiz/dual-research/pull/181"
handover: "handoffs/2026-05-22-spec-0158-deferred-spec-subagent.md"
failure_step: ""
source_session: orchestrator-hardening-2026-05-22
promoted_from_draft: ""
---

# Spec 0158 — Deferred-spec subagent in /dev-next — auto-capture in-flight deferrals as queued specs or drafts

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — adds a new handoff section convention, a new `/dev-next` step (25.5), and a background subagent that authors follow-up specs from deferred work items. No breaking changes.
> **Evidence:** user-stated need: "when a development is being executed, some functionality I've come across is being deferred because it can't be made. If that happens after the development session is done and completed, there should be a way to create a development specification for the deferred item." Today nothing systematic captures these — they live in commit messages, PR comments, or memory.

---

## 1. Context

`/dev-next` cycles end with a written handoff doc and a stamped session title. Anything the implementing agent deferred *during* the cycle — work that was in scope at start but got dropped because of complexity, missing context, blocking dependency, or risk — currently has no systematic capture path. It lives in commit messages, scattered TODOs, or the implementer's memory. By the time the next cycle starts, those deferrals are easy to lose.

The user's framing: "every time a session finishes and there is deferred functionality, it would say, 'There was deferred functionality. A subagent has kicked in to create a spec to cover for the gap.'" Automatic, low-friction, no extra invocation.

Constraint from ideation: **smart fallback**. Try to author a real dev spec when the deferral is well-bounded (cited files, clear scope). Fall back to a draft when the deferral is vague or under-specified. Background invocation so `/dev-next` doesn't block.

## 2. Proposed change

Three coordinated additions: a new handoff convention, a new `/dev-next` step, and the subagent itself.

### 2.1 — New handoff convention: `## Deferred during implementation`

Add an instruction to [`~/.claude/skills/dev-next/SKILL.md`](/Users/alexlisitzky/.claude/skills/dev-next/SKILL.md) step 23 (write handoff). The handoff body gains a new optional section:

```markdown
## Deferred during implementation

- **<short title>** — <one paragraph of context: what was in scope, why it got
  dropped, what artifacts already exist (file:line citations preferred).>
- **<short title>** — ...
```

Populated by the implementing agent during the cycle. Distinct from the spec's `## Out of scope` (intentional exclusions decided up front). If nothing was deferred, the section is omitted entirely — its absence is the signal that no subagent should fire.

The implementing agent decides what counts as "deferred":
- Work that was in the spec body but got cut for complexity/risk reasons.
- TODO comments added to the codebase during implementation that point at real follow-up work.
- "Should but didn't" items observed during reconcile or implementation that aren't strictly in scope but are obvious next steps.

NOT deferred (don't capture here):
- Items explicitly in `## Out of scope` of the original spec.
- Speculative ideas unrelated to the spec.
- Fixes for things the spec didn't claim to touch.

### 2.2 — New `/dev-next` step 25.5

Inserted between current step 25 (session title restamp) and step 26 (report to chat). Pseudocode:

```
25.5. **Spawn deferred-spec subagent (if applicable).**

   - Read the just-written handoff at handoffs/YYYY-MM-DD-spec-NNNN-<slug>.md.
   - Check for `## Deferred during implementation` section.
   - If absent or empty: skip this step entirely. No subagent.
   - If non-empty: spawn a background subagent via Agent tool with:
       subagent_type: "general-purpose"
       run_in_background: true
       description: "Deferrals from spec NNNN"
       prompt: <see § 2.3 below>
   - Do NOT wait for the subagent. Continue to step 26.
   - Note in the chat report (step 26) that a deferral subagent was spawned.
```

The subagent runs to completion in the background. Its output appears as a notification when complete (per the Agent tool's notification model).

### 2.3 — Subagent prompt template

The subagent is invoked from the queue session but must operate against the author worktree. The prompt template (substituted at spawn time):

```
You are a deferred-spec authoring subagent for the dual-research project.

Spec NNNN just shipped. The implementer noted deferred work in the handoff.
Your job: for each deferred item, author a follow-up artifact.

CONTEXT:
- Original spec: specs/NNNN-<slug>.md
- Handoff: handoffs/YYYY-MM-DD-spec-NNNN-<slug>.md
- PR diff: <inline the relevant changes the implementer made>
- Author worktree to use: /Users/alexlisitzky/dual-research-author/

PROCESS (per deferred item):

1. Read the deferral entry from the handoff's `## Deferred during implementation`
   section. Extract the short title and the context paragraph.

2. Attempt to author a queued dev spec (/spec-queue flow):
   a. Classify the type (new-feature / bug / refactoring / test / breaking)
      from the deferral text.
   b. Pick next dev number via:
        cd /Users/alexlisitzky/dual-research-author
        git fetch origin && git checkout --detach origin/main
        uv run python -c "from scripts.spec_lifecycle.pick_next_number import \
          next_dev_number, next_queue_position; print(next_dev_number('specs'), \
          next_queue_position('specs'))"
   c. Populate specs/_templates/<type>.md. Body must cite ≥ 2 file:line
      locations (or ≥ 3 plain repo paths). Use citations from the deferral
      context plus any files the implementer touched.
   d. Run the validator at scripts/spec_lifecycle/validator.py.
   e. If validator passes: commit + push as `Spec NNNN — <title> (queued)`.
      Append queued event. Stamp NOT required (subagent has no session title).
   f. If validator fails: fall back to /spec-draft flow (step 3 below).
      Do NOT retry the dev spec.

3. Fallback: author a draft.
   a. Pick next draft id via next_draft_id('specs/drafts').
   b. Write specs/drafts/draft-NNN-<slug>.md with frontmatter kind:draft.
   c. Body includes the deferral context AND an `## Unresolved questions`
      section listing what the validator complained about (so the user knows
      what's missing for promotion).
   d. Commit + push as `draft(NNN): auto-captured from spec NNNN deferrals`.

4. Move to the next deferred item.

REPORT (when done):
   Emit a final summary message:
   "Auto-created from spec NNNN deferrals: <list of specs/drafts created
   with their numbers, types, and validator outcomes>."

CONSTRAINTS:
- You cannot ask the user clarifying questions. If you don't have enough
  context for any judgment, fall back to draft.
- Do NOT modify the original spec NNNN file or its handoff.
- Do NOT invoke /dev-next.
- Stay in author worktree throughout. Refuse if cwd accidentally becomes
  /Users/alexlisitzky/dual-research/.
```

### 2.4 — Chat report changes (step 26)

When the subagent was spawned, append one line to the step 26 chat report:

> Deferral subagent spawned (background). It will report when complete.

When not (empty/absent section):

> No deferred items in handoff. No follow-up subagent.

## 3. UX / Behavior

- Implementing agent populates `## Deferred during implementation` in the handoff as part of normal cycle close.
- Subagent kicks off automatically when handoff has non-empty deferrals.
- User sees subagent's report when it completes — usually within a minute or two for typical deferrals.
- New specs/drafts appear on the dashboard via the normal `/spec-queue`/`/spec-draft` paths.
- User can ignore or promote drafts at leisure.
- No new explicit commands needed.

## 4. Data / Schema deltas

- New optional section convention in handoff body: `## Deferred during implementation`. No frontmatter changes. Renderer at [`scripts/spec_lifecycle/render_dashboard.py`](/Users/alexlisitzky/dual-research-author/scripts/spec_lifecycle/render_dashboard.py) doesn't need changes (it indexes by frontmatter, not body sections).
- Subagent's commits go through the same `/spec-queue` or `/spec-draft` paths and produce the same artifacts. No new file types.

## 5. Out of scope

- **SessionEnd hook trigger** (subagent fires from a settings.json hook on session end instead of from `/dev-next` step 25.5). Explicitly rejected during ideation — would fire on every session end, not just `/dev-next` cycles, adding noise.
- **Manual `/spec-from-deferrals` skill** (user invokes the subagent flow explicitly). Explicitly rejected — defeats the "automatic" intent.
- **Always-draft fallback** (subagent never auto-queues a dev spec). Explicitly rejected — would under-utilize well-bounded deferrals.
- **Always-dev-spec fallback** (subagent always queues, even for vague items). Explicitly rejected — would create noise from validator failures the user has to clean up.
- **Capturing TODOs from PR diffs automatically.** Out of scope for this spec — implementer-curated `## Deferred during implementation` section is the only input. Auto-scanning diffs for TODO comments could be a follow-up.
- **Subagent for `/dev-queue-run`.** The deferral subagent fires per `/dev-next` cycle. When `/dev-queue-run` runs N cycles, it implicitly fires N subagents (one per cycle). No separate `/dev-queue-run`-level deferral capture.
- **Modifying the cancelled-cycle path.** If `/dev-next` fails mid-cycle (`status: failed`), no handoff is written, so no subagent fires. Failure-recovery deferrals aren't captured automatically; user handles manually.
- **Updating `/spec-promote` to walk auto-captured drafts differently.** Drafts written by the subagent follow the same promotion flow as user-written drafts. No special handling.

## 6. Test plan

- [ ] Test: `tests/spec_lifecycle/test_handoff_deferred_section_parser.py` — given a handoff fixture with `## Deferred during implementation` containing 2 items, assert the parser (new helper in `scripts/spec_lifecycle/`) returns a list of 2 deferral dicts with title + context. Given a handoff fixture without the section, assert empty list. Given a handoff with an empty section, assert empty list.
- [ ] Test: `tests/spec_lifecycle/test_dev_next_handoff_template.py` — update existing tests (or add new) that assert `/dev-next`'s handoff template now mentions the `## Deferred during implementation` section as an optional addition. (Skill text test — string match.)
- [ ] Manual: end-to-end. Queue a spec via `/spec-queue` that the implementer intentionally defers part of. Run `/dev-next`. After cycle finishes, verify (a) handoff contains `## Deferred during implementation`, (b) subagent was spawned, (c) subagent's report shows one or more new specs/drafts created with correct frontmatter.
- [ ] Manual: end-to-end negative case. Queue a spec where nothing is deferred. Run `/dev-next`. Verify handoff omits the deferred section, no subagent fires, step 26 report explicitly notes "no deferrals."
- [ ] Manual: subagent fallback. Author a handoff with a deliberately vague deferral (no file:line citations possible). Confirm subagent attempts dev spec, validator fails, falls back to draft, and the draft contains `## Unresolved questions` listing what was missing.

## 7. Risks

- **Implementing agent forgets to populate the section.** Failure mode: real deferrals exist but no subagent fires. Mitigation: add explicit instruction in `/dev-next` step 15 (implementation) reminding the agent to track deferrals as it works, and step 23 (handoff write) to surface them. The skill update enforces this via prompt; no machine check.
- **Subagent quality.** Auto-authored dev specs may have weak file:line citations, may misclassify type, may set `version_bump` wrong. Mitigation: smart fallback routes anything that doesn't pass the validator to draft (with unresolved-questions surface). User can adjust before promotion.
- **Subagent push race.** If subagent is queuing while a parallel `/spec-queue` is also queuing, push races may occur. Mitigation: the existing 3-retry recompute logic in `/spec-queue` step 6 handles this. Subagent inherits.
- **Subagent runs cost.** Background subagent uses tokens. Per-deferral cost is small (one spec authoring per item, maybe 1-3 deferrals per cycle). Acceptable overhead.
- **Subagent can't ask clarifying questions.** Mitigated by always-draft-if-vague fallback. Drafts are explicitly allowed to carry unresolved questions, so the subagent's "I don't know" surfaces as the draft's `## Unresolved questions`.
- **Subagent might pick up false positives** (sees TODO-shaped text in handoff but it wasn't actually a deferral). Mitigated by the structured `## Deferred during implementation` heading — the subagent only reads that section, not the whole handoff body.
- **Subagent operates from author worktree, but `/dev-next` runs from queue worktree.** Cross-worktree spawning is supported by the Agent tool (cwd in prompt). Mitigation: prompt explicitly states the cwd and asks the subagent to refuse if it lands in the wrong worktree.
- **Spec 0157 (auto-decomposition) interaction.** If a single deferral is itself decomposable, the subagent's `/spec-queue` invocation would trigger 0157's decomposition logic. Acceptable — recursion is bounded (no infinite loop) and the conservative posture rarely splits.
