---
kind: dev
spec: "0157"
slug: spec-queue-auto-decomposition
title: "/spec-queue auto-decomposition — conservative bundle-by-default, auto-chained sub-specs"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.21.0
status: in_progress
queue_position: 1
depends_on: []
complexity: S
created: 2026-05-22
queued_at: 2026-05-22T13:26:06Z
started_at: "2026-05-22T13:50:28Z"
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: orchestrator-hardening-2026-05-22
promoted_from_draft: ""
---

# Spec 0157 — /spec-queue auto-decomposition — conservative bundle-by-default, auto-chained sub-specs

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** MINOR — adds a new capability (`/spec-queue` decomposes large conversations into N chained sub-specs) without changing existing single-spec behavior.
> **Evidence:** spec 0154 (this conversation) bundled 7 sub-changes — arguably should have been 3 specs. User explicitly asked for `/spec-queue` to handle this automatically when invoked.

---

## 1. Context

`/spec-queue` today takes one conversation and writes one spec. When the conversation contains multiple unrelated work items, they all bundle into one spec, one branch, one PR. Live evidence: spec 0154 in this session bundled seven sub-changes across four skill files + one new skill + a new CLAUDE.md + settings + memory updates. Reasonable as one initiative ("orchestrator hardening"), but the PR was harder to review and impossible to revert one piece without the others.

The user's framing: "if I say 'create a development spec' and the analysis turns out that multiple need to be created, they will just be created and all of them will just get queued in the right sequence." Single invocation, automatic decomposition, chained `depends_on`.

Constraint from ideation: **conservative posture**. Default is bundle. Splitting is the exception, triggered only by strong multi-domain signals. The goal is not to maximize spec count — it's to catch cases where bundling actively obscures review or revert.

## 2. Proposed change

A new sub-step `1d` added to [`~/.claude/skills/spec-queue/SKILL.md`](/Users/alexlisitzky/.claude/skills/spec-queue/SKILL.md) (currently structured with 1a/1b/1c per spec 0154). Plus minor adjustments to steps 3–9 to handle the N-spec case.

### 2.1 — New step 1d in `/spec-queue`

After 1a (classify), 1b (scope scan), 1c (DS check), and before step 2 (resolve unresolved questions):

```
### Step 1d — Decomposition check

Identify whether the conversation describes ONE coherent change or N independent
concerns. Apply the conservative bundle-by-default heuristic.

**Signals favoring split** — ALL must hold:

- Three or more independent file/domain surfaces with no implementation overlap
  (one chunk touches skill files, another touches a renderer, another touches a
  workflow YAML — three separate surfaces).
- No shared unifying purpose. If you can name the work in one phrase
  ("orchestrator hardening", "dashboard live-ness"), the pieces share a purpose
  and belong together.
- Bundled complexity would exceed L (large) — typically > 250 body lines, > 5
  file edits, or > 3 distinct "## 2.N" sub-entries.

**Signals favoring bundle** — any one overrides the split:

- Strong sequential dependencies where splitting just creates a linear chain
  with no parallelism gain.
- Different chunks share one test plan that would have to be duplicated.
- The user named the work as one initiative in the conversation.

If signals favor split: decompose (§ split flow below). Otherwise: bundle
(proceed as today, single spec).
```

### 2.2 — Split flow (executed only when 1d says split)

1. Identify N sub-specs by their natural cleavage points (typically by file/domain surface).
2. Determine `depends_on` chains. Three common shapes:
   - **Chain**: A → B → C (B depends on A, C depends on B).
   - **Fork**: A → {B, C} (B and C depend on A, no dep between B and C — can run in parallel).
   - **Independent**: {A, B, C} (no inter-dependencies).
3. Topologically sort. Break ties by complexity ascending (smaller specs first).
4. For each sub-spec in sorted order: repeat steps 3–7 of `/spec-queue`. Each sub-spec gets its own dev number (from [`pick_next_number.next_dev_number`](/Users/alexlisitzky/dual-research-author/scripts/spec_lifecycle/pick_next_number.py)), own queue_position (sequential), own frontmatter, own commit, own dashboard event.
5. Inter-spec `depends_on` populated from the dependency analysis in step 2.
6. Bundle the sub-specs' commits in a single push if possible (one network round-trip), or accept N pushes if not.

### 2.3 — Step 9 report changes

Single-spec case (today's behavior, unchanged):

> Queued spec NNNN at position M. Run `/dev-next` to start.

Multi-spec case (new):

> Decomposed into N specs:
> - NNN1 (pos M, type X)
> - NNN2 (pos M+1, type Y) — depends on NNN1
> - NNN3 (pos M+2, type Z) — depends on NNN1
>
> Run `/dev-next` or `/dev-queue-run` when ready.

### 2.4 — Push-race handling on split

The existing single-spec retry logic at [`spec-queue/SKILL.md:90`](/Users/alexlisitzky/.claude/skills/spec-queue/SKILL.md) (3 retries, recompute next number on push failure) applies per sub-spec independently. If sub-spec 1 of 3 pushes successfully but sub-spec 2 fails after retries, surface a partial-state report to the user:

> Decomposed into 3 sub-specs. Pushed NNN1; NNN2 failed after 3 retries. NNN3
> not attempted. Re-invoke `/spec-queue` for the remaining work, OR manually
> resolve NNN2 and re-run.

No automatic rollback (deleting NNN1) — that's destructive and might lose work. User-driven cleanup if needed.

## 3. UX / Behavior

- Single invocation, multiple specs created — matches user's stated preference.
- Default behavior preserved: most conversations still produce one spec.
- Queue order respects `depends_on` topology so `/dev-next` and `/dev-queue-run` process in correct sequence.
- Step 9 report makes it visible when decomposition fired (so the user isn't surprised).
- Bad decomposition recoverable via standard frontmatter edits (`status: cancelled`, queue_position adjustments).

## 4. Data / Schema deltas

None. The existing `depends_on` field in dev-spec frontmatter (used by spec 0155 today: `depends_on: ["0154"]`) already supports inter-spec chains. No validator changes needed.

## 5. Out of scope

- **Aggressive splitting** (split any 2+ concerns). Explicitly rejected during ideation as too noisy. Conservative posture only.
- **User-flagged splitting** (skill never auto-decides; user signals via phrasing like "split this into multiple"). Explicitly rejected — defeats the "automatic" intent. If a user wants explicit control, they can invoke `/spec-queue` multiple times in separate conversations.
- **Retroactive decomposition of already-queued specs.** This is a `/spec-queue`-time judgment only. A queued bloated spec stays as-is unless the user manually splits.
- **Multi-spec decomposition in `/spec-promote`.** Drafts are usually single-concept; if a draft bundles too much, the user splits manually before promoting. Different concern, different spec.
- **Multi-spec decomposition in `/spec-draft`.** Drafts are scratch; can carry unresolved questions. Splitting them is the user's call at draft time.
- **`depends_on` cycle detection in the validator.** Out of scope here. If the LLM mis-derives a cycle, the validator currently won't catch it. Can be added in a follow-up spec if cycles become a real problem.
- **Auto-spec for deferred functionality** (Item 2 from this conversation). Covered by separately-queued spec 0158.

## 6. Test plan

The hard part — LLM judgment on when to split — can't be unit-tested. The mechanics around it can:

- [ ] Test: `tests/spec_lifecycle/test_pick_next_number_sequential.py` — call `next_dev_number('specs')` three times with intermediate filesystem materializations (write a stub spec file with each returned number); assert numbers are strictly sequential with no collisions. Locks in the per-sub-spec numbering contract the split flow depends on.
- [ ] Test: `tests/spec_lifecycle/test_depends_on_frontmatter.py` — given a fixture spec with `depends_on: ["0154", "0156"]`, assert the validator at [`scripts/spec_lifecycle/validator.py`](/Users/alexlisitzky/dual-research-author/scripts/spec_lifecycle/validator.py) accepts it (verifies the field is unchanged contract, no regression from this spec).
- [ ] Manual: invoke `/spec-queue` on a clearly single-concept thread ("fix this one bug at file:line"). Assert: single spec, no decomposition, step 9 report is single-spec format.
- [ ] Manual: invoke `/spec-queue` on a synthetic multi-concept thread (3+ unrelated surfaces, no shared purpose). Assert: N specs created with sequential queue positions, correct `depends_on` chain, step 9 lists all N.
- [ ] Manual: invoke `/spec-queue` on a conversation shaped like 0154's (7 sub-changes, shared "orchestrator hardening" purpose). Assert: bundles into one spec — the unifying-purpose override fires, no decomposition.
- [ ] Manual: trigger a push race during decomposition (e.g. queue another spec from a parallel session mid-decomposition). Assert: partial-state report from step 9 with clear next-step instructions.

## 7. Risks

- **LLM mis-judges decomposition.** Two failure modes:
  - **Over-split** (3 trivial specs where 1 was fine) — creates queue noise. Mitigation: conservative posture makes this rare; user can manually re-bundle by cancelling N-1 specs and editing the remaining one, OR by treating them as a single cycle via `/dev-queue-run`.
  - **Under-split** (still bundles when it shouldn't) — preserves today's status quo, not worse. No regression risk.
- **Mid-split push race.** Addressed in §2.4 — partial-state surfaced, no automatic rollback (would risk losing work).
- **`depends_on` cycle from LLM mis-derivation.** Validator currently doesn't cycle-check. If a cycle ships, `/dev-next` would refuse to start any spec in the cycle (each waits for the next). Mitigation: out-of-scope for this spec, but documented as a known gap. Quick follow-up if it surfaces in practice.
- **Topological sort tie-breaker by complexity may surprise.** If A and B are independent peers, B might run before A despite A being mentioned first in conversation. Acceptable — tie-breaker is deterministic and small specs first usually means lower-risk first.
- **Conservative threshold is itself a judgment call.** The "> 3 sub-entries OR > 250 lines OR > 5 file edits" rule is heuristic. Real-world calibration may need adjustment after several decompositions. Acceptable — easy to tune in a one-line follow-up.
